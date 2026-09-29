"""联网仅发生在 download；推理始终使用经过盘点的本地文件。"""
import hashlib
import json
import os
import shutil
import threading
import time
import urllib.request
from pathlib import Path
from .config import MODELS as MODEL_DIR, DEVICE
from .model_manifest import MODELS

LOCK=threading.RLock()
CACHE={}
ERRORS={}
DOWNLOADS={}

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def status(id, verify=False):
    if id not in MODELS:raise ValueError('未知模型')
    meta=MODELS[id];root=MODEL_DIR/id;inventory=root/'inventory.json';files=[];missing=[];reason=meta.get('blocked','');info={}
    if inventory.exists():
        try:
            info=json.loads(inventory.read_text());files=info['files']
            for f in files:
                path=root/f['path']
                if not path.is_file() or path.stat().st_size!=f['size'] or (verify and sha256(path)!=f['sha256']):missing.append(f['path'])
            if verify and missing:ERRORS[id]='文件校验失败，请重新准备模型：'+', '.join(missing)
        except (ValueError,KeyError,OSError) as exc:missing=['inventory.json 无效'];reason=str(exc)
    else:missing=list(meta.get('files',{})) or ['inventory.json（尚未准备权重和配置）']
    for filename in meta.get('files',{}):
        if filename not in {f['path'] for f in files} or not (root/filename).is_file():
            if filename not in missing:missing.append(filename)
    state='blocked' if meta.get('blocked') else 'loading_failed' if id in ERRORS else 'missing' if missing else 'ready'
    if id in DOWNLOADS and DOWNLOADS[id]['state']=='downloading':state='downloading'
    return {**meta,'revision':info.get('revision',meta['version']),'state':state,'reason':ERRORS.get(id,reason),'missing':missing,'local_path':str(root),'files':files,'loaded':id in CACHE,'download':DOWNLOADS.get(id), 'device':DEVICE if 'cuda' in meta['devices'] else 'cpu'}

def list_models():return [status(id) for id in MODELS]

def download(id, progress=lambda value,message:None):
    if id not in MODELS:raise ValueError('未知模型')
    meta=MODELS[id]
    if meta.get('blocked'):raise ValueError(meta['blocked'])
    if status(id,verify=True)['state']=='ready':return status(id)
    root=MODEL_DIR/id;root.mkdir(parents=True,exist_ok=True);DOWNLOADS[id]={'state':'downloading','progress':0,'message':'准备下载'}
    previous={}
    if (root/'inventory.json').exists():
        try:previous=json.loads((root/'inventory.json').read_text())
        except (ValueError,OSError):pass
    expected={f['path']:f for f in previous.get('files',[])}
    def intact(dest):
        record=expected.get(str(dest.relative_to(root)))
        return bool(record and dest.is_file() and dest.stat().st_size==record['size'] and sha256(dest)==record['sha256'])
    revision=meta['version']
    def report(value,message):
        DOWNLOADS[id].update(progress=value,message=message);progress(value,message)
    try:
        if meta['kind']=='hf':
            # 使用官方 HTTPS 直接 GET，兼容不返回 Content-Length 的代理；固定仓库 commit。
            api=f'https://huggingface.co/api/models/{meta["repo"]}'
            if previous.get('revision') and len(previous['revision'])==40:api+='/revision/'+previous['revision']
            with urllib.request.urlopen(api,timeout=90) as response:info=json.load(response)
            revision=info['sha'];names=[f['rfilename'] for f in info['siblings']]
            has_safe=any(x.endswith('.safetensors') for x in names)
            selected=[x for x in names if x.endswith(('.json','.txt','.model','.safetensors','.md')) or (x.endswith('.bin') and not has_safe and '/' not in x)]
            for i,name in enumerate(selected):
                report(i/len(selected)*.95,f'{i+1}/{len(selected)} {name}')
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
                if intact(dest):continue
                url=f'https://huggingface.co/{meta["repo"]}/resolve/{revision}/{name}?download=true'
                temp=dest.with_suffix(dest.suffix+'.part')
                with urllib.request.urlopen(url,timeout=120) as response,open(temp,'wb') as output:
                    total=int(response.headers.get('Content-Length',0));done=0
                    while chunk:=response.read(1024*1024):
                        output.write(chunk);done+=len(chunk);report((i+(done/total if total else .5))/len(selected)*.95,f'{name}: {done/1024/1024:.1f} MB')
                temp.replace(dest)
        elif meta['kind']=='rapidocr':
            import rapidocr_onnxruntime
            src=Path(rapidocr_onnxruntime.__file__).parent
            for f in src.rglob('*'):
                if f.is_file() and f.suffix in ['.onnx','.yaml','.txt']:
                    dest=root/f.relative_to(src);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
            if len(list(root.rglob('*.onnx')))<3:raise ValueError('RapidOCR 包未包含检测/方向/识别三个 ONNX 文件')
        else:
            for i,(name,url) in enumerate(meta.get('files',{}).items()):
                dest=root/name
                if intact(dest):continue
                temp=dest.with_suffix(dest.suffix+'.part')
                req=urllib.request.Request(url,headers={'User-Agent':'vision-lab/1.0'})
                with urllib.request.urlopen(req,timeout=90) as response,open(temp,'wb') as output:
                    total=int(response.headers.get('Content-Length',0));done=0
                    while True:
                        chunk=response.read(1024*1024)
                        if not chunk:break
                        output.write(chunk);done+=len(chunk)
                        report((i+(done/total if total else .5))/len(meta['files'])*.95,f'{name}: {done/1024/1024:.1f} MB')
                if temp.stat().st_size==0:raise ValueError(f'{name} 下载为空')
                temp.replace(dest)
        files=[{'path':str(f.relative_to(root)),'size':f.stat().st_size,'sha256':sha256(f)} for f in sorted(root.rglob('*')) if f.is_file() and f.name!='inventory.json' and '.cache' not in f.parts and '__pycache__' not in f.parts and f.suffix!='.part']
        if not files:raise ValueError('下载后未找到任何模型文件')
        (root/'inventory.json').write_text(json.dumps({'revision':revision,'source':meta['source'],'downloaded_at':time.time(),'checksum_note':'下载时实测 SHA256；不冒充上游签名','files':files},ensure_ascii=False,indent=2))
        DOWNLOADS[id]={'state':'ready','progress':1,'message':'全部文件已校验'};ERRORS.pop(id,None);report(1,'就绪')
    except Exception as exc:
        DOWNLOADS[id]={'state':'failed','progress':0,'message':str(exc)};ERRORS[id]=str(exc);raise
    return status(id)

def release(id=None):
    with LOCK:
        for key in list(CACHE):
            if id is None or id==key:CACHE.pop(key,None)
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():torch.cuda.empty_cache()
        except ImportError:pass

def require(id):
    s=status(id)
    if s['state'] not in ['ready','loading_failed'] or s['missing']:
        raise ValueError(f'模型 {id} 未就绪：{s["reason"] or ", ".join(s["missing"])}。运行 scripts/download_models.py --model {id}')
    return MODEL_DIR/id

def load_model(id):
    """调用者持有 LOCK；缓存最多一个模型，切换时自动释放。"""
    if id in CACHE:return CACHE[id]
    path=require(id);release();os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    try:
        import torch
        torch.set_num_threads(min(4,os.cpu_count() or 1))
        if DEVICE!='cpu' and not torch.cuda.is_available():raise ValueError('配置了 CUDA，但当前 PyTorch 无可用 GPU；设置 VISION_DEVICE=cpu')
        if id in ['resnet18','deeplab','r3d']:
            from torchvision.models import resnet18,ResNet18_Weights
            if id=='resnet18':model=resnet18(weights=None);weights=ResNet18_Weights.DEFAULT
            elif id=='deeplab':
                from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large,DeepLabV3_MobileNet_V3_Large_Weights
                model=deeplabv3_mobilenet_v3_large(weights=None,weights_backbone=None,aux_loss=True);weights=DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT
            else:
                from torchvision.models.video import r3d_18,R3D_18_Weights
                model=r3d_18(weights=None);weights=R3D_18_Weights.DEFAULT
            model.load_state_dict(torch.load(path/(id+'.pth'),map_location='cpu',weights_only=True));model=model.eval().to(DEVICE);obj=(model,weights.transforms(),weights.meta['categories'])
        elif id.startswith('yolov8') or id=='sam2':
            from ultralytics import YOLO,SAM
            obj=SAM(str(path/'sam2_t.pt')) if id=='sam2' else YOLO(str(path/(id+'.pt')))
        elif id=='layout':
            from doclayout_yolo import YOLOv10
            obj=YOLOv10(str(path/'doclayout.pt'))
        elif id=='rapidocr':
            from rapidocr_onnxruntime import RapidOCR
            fs=list(path.rglob('*.onnx'));find=lambda hint:str(next(f for f in fs if hint in f.name))
            obj=RapidOCR(det_model_path=find('det'),rec_model_path=find('rec'),cls_model_path=find('cls'),intra_op_num_threads=2,inter_op_num_threads=2)
        elif MODELS[id]['kind']=='hf':
            from transformers import AutoImageProcessor,AutoProcessor,AutoModelForDepthEstimation,CLIPModel,CLIPProcessor,OwlViTForObjectDetection,BlipForConditionalGeneration,BlipForQuestionAnswering,DetrForSegmentation,AutoModelForImageToImage
            kw={'local_files_only':True}
            if id=='clip':processor=CLIPProcessor.from_pretrained(path,**kw);model=CLIPModel.from_pretrained(path,**kw)
            elif id=='owlvit':processor=AutoProcessor.from_pretrained(path,**kw);model=OwlViTForObjectDetection.from_pretrained(path,**kw)
            elif id in ['blip','blip-vqa']:processor=AutoProcessor.from_pretrained(path,**kw);model=(BlipForConditionalGeneration if id=='blip' else BlipForQuestionAnswering).from_pretrained(path,**kw)
            elif id=='detr-panoptic':
                from transformers import AutoConfig
                processor=AutoImageProcessor.from_pretrained(path,**kw);config=AutoConfig.from_pretrained(path,**kw);config.use_pretrained_backbone=False
                model=DetrForSegmentation.from_pretrained(path,config=config,**kw)
            elif id=='depth-anything':processor=AutoImageProcessor.from_pretrained(path,**kw);model=AutoModelForDepthEstimation.from_pretrained(path,**kw)
            elif id=='edsr':processor=AutoImageProcessor.from_pretrained(path,**kw);model=AutoModelForImageToImage.from_pretrained(path,**kw)
            else:raise ValueError('尚未安装该模型独立运行环境')
            obj=(model.eval().to(DEVICE),processor)
        elif id=='rmbg':
            import onnxruntime as ort
            opts=ort.SessionOptions();opts.intra_op_num_threads=2;obj=ort.InferenceSession(str(path/'u2netp.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
        elif id in ['swin-denoise','restormer']:
            # 源码随官方权重下载并纳入 SHA256 文件清单。
            import importlib.util
            spec=importlib.util.spec_from_file_location('vision_restormer',path/'restormer_arch.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            import yaml
            options=yaml.safe_load((path/'config.yml').read_text())['network_g'];options.pop('type',None)
            obj=module.Restormer(**options);checkpoint=torch.load(path/'weights.pth',map_location='cpu',weights_only=True);obj.load_state_dict(checkpoint['params']);obj=obj.eval().to(DEVICE)
        elif MODELS[id]['kind']=='mediapipe':obj=path
        else:raise ValueError('没有已安装的模型适配器')
        CACHE[id]=obj;ERRORS.pop(id,None);return obj
    except Exception as exc:ERRORS[id]=str(exc);raise
