"""模型适配器统一输出：底图、可开关图层、原始数组、结构化坐标。"""
import json
import os
import re
import subprocess
import time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from .algorithms.common import Result, blank_layer, mask_layer, normalize, read_image, roi_of
from .config import DEVICE, ROOT, MODELS as MODEL_DIR
from .models import LOCK, load_model

def image_tensor(im, size=224):
    import torch
    rgb=cv2.cvtColor(cv2.resize(im,(size,size)),cv2.COLOR_BGR2RGB).astype('float32')/255
    return ((torch.from_numpy(rgb).permute(2,0,1)-torch.tensor([.485,.456,.406])[:,None,None])/torch.tensor([.229,.224,.225])[:,None,None]).unsqueeze(0).to(DEVICE)

def local_features(model,im):
    """PatchCore 风格局部特征：ResNet layer2+layer3；固定 224×224 网格。"""
    import torch
    x=image_tensor(im)
    with torch.inference_mode():
        for layer in [model.conv1,model.bn1,model.relu,model.maxpool,model.layer1]:x=layer(x)
        a=model.layer2(x);b=model.layer3(a);b=torch.nn.functional.interpolate(b,size=a.shape[-2:],mode='bilinear',align_corners=False)
        f=torch.cat([a,b],1);f=torch.nn.functional.avg_pool2d(f,3,1,1)
    return f[0].permute(1,2,0).cpu().numpy()

def infer(id,model_id,im,p,extra):
    with LOCK:
        return _infer(id,model_id,im,p,extra)

def _infer(id,model_id,im,p,extra):
    import torch
    obj=load_model(model_id);h,w=im.shape[:2];data={};layers={};arrays={};out=im.copy();pil=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB))
    if model_id.startswith('yolov8') or id in ['sam','layout']:
        kw={'source':im,'device':DEVICE,'verbose':False,'save':False}
        if id=='sam':
            pts=p.get('points',[])
            if pts:kw.update(points=[[q[:2] for q in pts]],labels=[[int(q[2]) for q in pts]])
            elif p.get('roi'):
                x,y,rw,rh=roi_of(p,im);kw['bboxes']=[x,y,x+rw,y+rh]
            else:raise ValueError('请点选前景/背景或绘制目标框')
        else:kw.update(conf=p.get('confidence',.25),imgsz=1024 if id=='layout' else 640)
        result=obj.predict(**kw)[0];data={'classes':result.names,'objects':[]};boxes=blank_layer(im);keypoints=blank_layer(im);masks=blank_layer(im);texts=blank_layer(im)
        if result.obb is not None:
            for q,conf,cls in zip(result.obb.xyxyxyxy.cpu().numpy(),result.obb.conf.cpu().numpy(),result.obb.cls.cpu().numpy()):
                cv2.polylines(boxes,[q.astype('int32')],True,(80,220,130,255),2);data['objects'].append({'polygon':q.tolist(),'confidence':float(conf),'class_id':int(cls),'label':result.names[int(cls)]})
        elif result.boxes is not None:
            for box in result.boxes:
                xy=box.xyxy[0].cpu().numpy();conf=float(box.conf[0]);cls=int(box.cls[0]);x1,y1,x2,y2=xy.astype(int)
                cv2.rectangle(boxes,(x1,y1),(x2,y2),(70,220,120,255),2);cv2.putText(texts,f'{result.names.get(cls,cls)} {conf:.2f}',(x1,max(16,y1-6)),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255,255),1)
                data['objects'].append({'box_xyxy':xy.tolist(),'confidence':conf,'class_id':cls,'label':result.names.get(cls,str(cls))})
        if result.masks is not None:
            # 消除 letterbox 填充后再还原原图；保留孔洞与不连通区域。
            from ultralytics.utils.ops import scale_masks
            raw_masks=result.masks.data
            aligned=raw_masks if tuple(raw_masks.shape[-2:])==(h,w) else scale_masks(raw_masks[None].float(),(h,w))[0]
            label_map=np.zeros((h,w),np.uint16)
            for i,polygon in enumerate(result.masks.xy):
                active=aligned[i].cpu().numpy()>.5
                bgr=tuple(int(v) for v in np.random.default_rng(i+3).integers(70,240,3));masks[active]=(*bgr,135);label_map[active]=i+1
                if i<len(data['objects']):data['objects'][i]['mask_polygon']=polygon.tolist()
            arrays['instance_labels']=label_map;layers['掩膜']=masks
        if result.keypoints is not None:
            xy=result.keypoints.xy.cpu().numpy();conf=result.keypoints.conf.cpu().numpy();data['keypoints']=xy.tolist();data['keypoint_confidence']=conf.tolist()
            skeleton=[(5,6),(5,7),(7,9),(6,8),(8,10),(5,11),(6,12),(11,12),(11,13),(13,15),(12,14),(14,16)]
            for person,scores in zip(xy,conf):
                for (x,y),score in zip(person,scores):
                    if score>.3:cv2.circle(keypoints,(int(x),int(y)),3,(80,190,255,255),-1)
                for a,b in skeleton:
                    if scores[a]>.3 and scores[b]>.3:cv2.line(keypoints,tuple(person[a].astype(int)),tuple(person[b].astype(int)),(180,220,80,255),2)
            layers['关键点']=keypoints
        layers['目标框']=boxes;layers['类别文字']=texts;data['count']=len(data['objects'])
    elif model_id=='resnet18':
        model,transform,categories=obj
        data['classes']=categories
        if id=='anomaly':
            normals=extra.get('normal_samples',[]);banks=extra.get('reference_bank',[])
            if banks:
                normals=[]
                with np.load(banks[0],allow_pickle=False) as saved:bank=saved['features']
                if bank.ndim!=2 or bank.shape[1]!=384:raise ValueError('参考库与 ResNet18 layer2+layer3 特征维度不一致')
            else:
                if len(normals)<2:raise ValueError('请上传至少 2 张正常样本建立参考库，或加载已下载的参考库 NPZ')
                if len(normals)>100:raise ValueError('正常样本最多 100 张')
                features=np.concatenate([local_features(model,read_image(path)).reshape(-1,384) for path in normals])
                # 可重复的随机子采样记忆库；明确标注不是论文中的贪心 coreset。
                rng=np.random.default_rng(42);bank=features[rng.choice(len(features),min(6000,len(features)),replace=False)]
            f=local_features(model,im);flat=torch.from_numpy(f.reshape(-1,384));memory=torch.from_numpy(bank)
            distances=[]
            for chunk in flat.split(128):distances.append(torch.cdist(chunk,memory).min(1).values.numpy())
            score=np.concatenate(distances).reshape(f.shape[:2]);score=cv2.resize(score,(w,h));score=cv2.GaussianBlur(score,(0,0),3)
            heat=cv2.applyColorMap(normalize(score),cv2.COLORMAP_TURBO);layers['异常热力图']=np.dstack([heat,np.full((h,w),150,np.uint8)]);arrays.update(anomaly_score=score,features=bank)
            data={'anomaly_score':float(score.max()),'mean_score':float(score.mean()),'reference_vectors':len(bank),'normal_samples':len(normals),'method':'PatchCore 风格 ResNet18 局部特征最近邻；随机记忆库子采样','note':'异常分数非概率；没有带标注验证集时不声明准确率或自动合格阈值','bank_artifact':'features.npz'}
            if p['score_threshold']>0:
                defect=(score>p['score_threshold']).astype('uint8')*255;arrays['anomaly_mask']=defect;layers['超过阈值区域']=mask_layer(defect,(40,40,240));data.update(threshold=p['score_threshold'],is_anomalous=bool(defect.any()),anomaly_fraction=float((defect>0).mean()))
        elif id in ['gradcam','feature_maps']:
            x=image_tensor(im);activations=[];handle=model.layer4.register_forward_hook(lambda m,i,o:activations.append(o))
            try:
                logits=model(x);feature=activations[0]
                if id=='gradcam':
                    target=int(logits.argmax(1));gradient=torch.autograd.grad(logits[0,target],feature)[0];cam=(gradient.mean((2,3),keepdim=True)*feature).sum(1).relu()[0].detach().cpu().numpy();cam=cv2.resize(normalize(cam),(w,h));heat=cv2.applyColorMap(cam,cv2.COLORMAP_TURBO);layers['Grad-CAM']=np.dstack([heat,np.full((h,w),145,np.uint8)]);data={'class':categories[target],'class_id':target,'preprocess':'原图直接缩放到 224×224，热力图按相同比例还原；不使用中心裁剪'}
                else:
                    maps=feature[0,:16].detach().cpu().numpy();tiles=[cv2.applyColorMap(cv2.resize(normalize(a),(128,128)),cv2.COLORMAP_VIRIDIS) for a in maps];out=np.vstack([np.hstack(tiles[i:i+4]) for i in range(0,16,4)]);arrays['features']=feature[0].detach().cpu().numpy();data={'layer':'layer4','channels_shown':16,'total_channels':512}
            finally:handle.remove();model.zero_grad(set_to_none=True)
        elif id=='benchmark':
            x=transform(pil).unsqueeze(0).to(DEVICE);times=[]
            with torch.inference_mode():
                model(x)
                for _ in range(int(p['repeats'])):
                    if DEVICE!='cpu':torch.cuda.synchronize()
                    start=time.perf_counter();pt=model(x)
                    if DEVICE!='cpu':torch.cuda.synchronize()
                    times.append((time.perf_counter()-start)*1000)
            data={'pytorch_median_ms':float(np.median(times)),'device':DEVICE,'TensorRT':'未安装 TensorRT 或无 NVIDIA GPU，未运行'}
            try:
                import onnxruntime as ort
                path=MODEL_DIR/'resnet18'/'resnet18.onnx'
                if not path.exists():torch.onnx.export(model,x,str(path),input_names=['image'],output_names=['logits'],opset_version=17,dynamo=False)
                opts=ort.SessionOptions();opts.intra_op_num_threads=4;session=ort.InferenceSession(str(path),sess_options=opts,providers=['CPUExecutionProvider']);feed={'image':x.cpu().numpy()};session.run(None,feed);times=[]
                for _ in range(int(p['repeats'])):start=time.perf_counter();ot=session.run(None,feed)[0];times.append((time.perf_counter()-start)*1000)
                data.update(onnxruntime_cpu_median_ms=float(np.median(times)),max_abs_error=float(np.max(np.abs(ot-pt.cpu().numpy()))))
            except Exception as exc:data['onnxruntime_error']=str(exc)
        else:
            with torch.inference_mode():probs=model(transform(pil).unsqueeze(0).to(DEVICE)).softmax(1)[0];values,indices=probs.topk(5)
            data['top5']=[{'class_id':int(i),'label':categories[int(i)],'probability':float(v)} for v,i in zip(values,indices)];data['preprocess']='ImageNet resize + center crop + normalize'
    elif model_id=='deeplab':
        model,transform,categories=obj
        with torch.inference_mode():logits=model(transform(pil).unsqueeze(0).to(DEVICE))['out'];labels=torch.nn.functional.interpolate(logits,size=(h,w),mode='bilinear',align_corners=False).argmax(1)[0].cpu().numpy().astype('uint8')
        palette=np.random.default_rng(42).integers(50,240,(256,3),dtype='uint8');layer=np.dstack([palette[labels],np.where(labels>0,145,0).astype('uint8')]);layers['语义标签']=layer;arrays['labels']=labels;data['segments']=[{'class_id':int(i),'label':categories[i],'pixels':int((labels==i).sum())} for i in np.unique(labels)]
    elif model_id=='rapidocr':
        result,timing=obj(im);items=[];l=blank_layer(im)
        pattern=p.get('pattern','')
        if id=='char_check':
            if len(pattern)>200:raise ValueError('正则最长为 200 字符')
            # 使用第三方 regex 的超时能力，避免不受限回溯。
            import regex
            regex.compile(pattern)
        for box,text,score in result or []:
            item={'polygon':box,'text':text,'confidence':float(score)}
            if id=='char_check':item['valid']=bool(regex.fullmatch(pattern,text,timeout=.05))
            items.append(item);cv2.polylines(l,[np.asarray(box,np.int32)],True,(70,210,180,255),2)
        data={'texts':items,'text':'\n'.join(x['text'] for x in items),'timing':timing};layers['文字位置']=l
    elif model_id in ['depth-anything','clip','owlvit','blip','blip-vqa','detr-panoptic','edsr']:
        model,processor=obj
        with torch.inference_mode():
            if model_id=='depth-anything':
                inputs=processor(images=pil,return_tensors='pt').to(DEVICE);depth=model(**inputs).predicted_depth;d=torch.nn.functional.interpolate(depth[:,None],size=(h,w),mode='bicubic',align_corners=False)[0,0].cpu().numpy();out=cv2.applyColorMap(normalize(d),cv2.COLORMAP_TURBO);arrays['relative_inverse_depth']=d;data={'scale':'相对逆深度，数值较大通常更近；不可直接转换毫米'}
            elif model_id=='clip':
                if id=='similarity':
                    paths=extra.get('gallery',[])
                    if not paths:raise ValueError('请上传检索图库图片')
                    if len(paths)>100:raise ValueError('图库最多 100 张')
                    features=[model.get_image_features(**processor(images=pil,return_tensors='pt').to(DEVICE))]
                    for start in range(0,len(paths),4):
                        imgs=[Image.fromarray(cv2.cvtColor(read_image(q),cv2.COLOR_BGR2RGB)) for q in paths[start:start+4]];batch=processor(images=imgs,return_tensors='pt').to(DEVICE);features.append(model.get_image_features(**batch))
                    feat=torch.cat(features);feat=feat/feat.norm(dim=-1,keepdim=True);scores=(feat[:1]@feat[1:].T)[0].cpu().numpy();data['ranking']=sorted([{'gallery_index':i,'file':str(path.name),'similarity':float(score)} for i,(path,score) in enumerate(zip(paths,scores))],key=lambda q:-q['similarity'])
                else:
                    texts=[x.strip() for x in p['prompt'].split(',') if x.strip()]
                    if not texts:raise ValueError('至少需要一个文本候选')
                    inputs=processor(text=texts,images=pil,return_tensors='pt',padding=True).to(DEVICE);result=model(**inputs);scores=(result.image_embeds@result.text_embeds.T)[0].cpu().numpy();data['ranking']=sorted([{'text':t,'similarity':float(s)} for t,s in zip(texts,scores)],key=lambda q:-q['similarity'])
                    paths=extra.get('gallery',[])
                    if len(paths)>100:raise ValueError('图库最多 100 张')
                    if paths:
                        features=[]
                        for start in range(0,len(paths),4):
                            imgs=[Image.fromarray(cv2.cvtColor(read_image(q),cv2.COLOR_BGR2RGB)) for q in paths[start:start+4]]
                            features.append(model.get_image_features(**processor(images=imgs,return_tensors='pt').to(DEVICE)))
                        features=torch.cat(features);features=features/features.norm(dim=-1,keepdim=True);similarities=(result.text_embeds@features.T).cpu().numpy()
                        data['image_text_candidates']=data['ranking'];data['queries']=[{'text':text,'ranking':sorted([{'gallery_index':i,'file':path.name,'similarity':float(score)} for i,(path,score) in enumerate(zip(paths,row))],key=lambda q:-q['similarity'])} for text,row in zip(texts,similarities)];data['ranking']=data['queries'][0]['ranking'];data['query']=texts[0]
            elif model_id=='owlvit':
                texts=[x.strip() for x in p['prompt'].split(',') if x.strip()]
                if not texts:raise ValueError('请输入检测类别')
                inputs=processor(text=[texts],images=pil,return_tensors='pt').to(DEVICE);outputs=model(**inputs);result=processor.post_process_object_detection(outputs,target_sizes=torch.tensor([[h,w]],device=DEVICE),threshold=p['confidence'])[0];items=[];l=blank_layer(im)
                for box,score,cls in zip(result['boxes'],result['scores'],result['labels']):
                    xy=box.cpu().numpy();a,b,c,d=xy.astype(int);cv2.rectangle(l,(a,b),(c,d),(70,220,180,255),2);items.append({'box_xyxy':xy.tolist(),'label':texts[int(cls)],'confidence':float(score)})
                layers['文本目标框']=l;data['objects']=items
            elif model_id in ['blip','blip-vqa']:
                inputs=processor(images=pil,text=p['prompt'] if id=='vqa' else None,return_tensors='pt').to(DEVICE);tokens=model.generate(**inputs,max_new_tokens=70);data['text']=processor.decode(tokens[0],skip_special_tokens=True)
            elif model_id=='detr-panoptic':
                inputs=processor(images=pil,return_tensors='pt').to(DEVICE);result=processor.post_process_panoptic_segmentation(model(**inputs),target_sizes=[(h,w)],label_ids_to_fuse={int(i) for i in model.config.id2label if int(i)>=91})[0];labels=result['segmentation'].cpu().numpy().astype('int32');palette=np.random.default_rng(42).integers(50,240,(max(1,int(labels.max())+1),3),dtype='uint8');heat=palette[np.maximum(labels,0)];layers['全景分割']=np.dstack([heat,np.where(labels>=0,145,0).astype('uint8')]);arrays['labels']=labels;data['segments']=result['segments_info'];data['classes']=model.config.id2label
            else:
                # CPU 上分块限制注意力内存；重叠区加权平均，保持原图 ×2 输出大小。
                scale=2;acc=np.zeros((h*scale,w*scale,3),np.float32);counts=np.zeros((h*scale,w*scale,1),np.float32)
                for y in range(0,h,112):
                    for x in range(0,w,112):
                        tile=pil.crop((x,y,min(x+128,w),min(y+128,h)));inputs=processor(images=tile,return_tensors='pt').to(DEVICE);rec=model(**inputs).reconstruction[0].clamp(0,1).permute(1,2,0).cpu().numpy();th,tw=tile.height*scale,tile.width*scale;acc[y*scale:y*scale+th,x*scale:x*scale+tw]+=rec[:th,:tw,::-1];counts[y*scale:y*scale+th,x*scale:x*scale+tw]+=1
                out=np.clip(acc/np.maximum(counts,1)*255,0,255).astype('uint8');data['scale']=2
    elif model_id=='rmbg':
        rgb=cv2.cvtColor(cv2.resize(im,(320,320)),cv2.COLOR_BGR2RGB).astype('float32')/255;x=((rgb-[.485,.456,.406])/[.229,.224,.225]).transpose(2,0,1)[None].astype('float32');pred=obj.run(None,{obj.get_inputs()[0].name:x})[0][0,0];mask=cv2.resize(normalize(pred),(w,h));alpha=mask.astype('float32')/255
        col=p['background']
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',col):raise ValueError('背景颜色应为 #RRGGBB')
        bg=np.array([int(col[i:i+2],16) for i in [5,3,1]]);out=(im*alpha[:,:,None]+bg*(1-alpha[:,:,None])).astype('uint8');arrays['alpha']=mask;arrays['foreground_rgba']=np.dstack([im,mask]);data['note']='显著性前景 alpha 估计，透明和发丝细节可能不准确'
    elif model_id in ['swin-denoise','restormer']:
        # 256 分块重叠平均，避免高分辨率 CPU 内存峰值。
        acc=np.zeros_like(im,np.float32);counts=np.zeros((h,w,1),np.float32)
        with torch.inference_mode():
            for y in range(0,h,224):
                for x in range(0,w,224):
                    tile=im[y:y+256,x:x+256];th,tw=tile.shape[:2];rgb=cv2.cvtColor(tile,cv2.COLOR_BGR2RGB);t=torch.from_numpy(rgb.copy()).permute(2,0,1)[None].float().to(DEVICE)/255;t=torch.nn.functional.pad(t,(0,(-tw)%8,0,(-th)%8),mode='replicate');r=obj(t)[0,:,:th,:tw].clamp(0,1).permute(1,2,0).cpu().numpy()[:,:,::-1];acc[y:y+th,x:x+tw]+=r*255;counts[y:y+th,x:x+tw]+=1
        out=(acc/np.maximum(counts,1)).astype('uint8')
    elif model_id in ['face_landmarker','hand_landmarker']:
        import sys
        worker=os.getenv('VISION_MEDIAPIPE_PYTHON',str(Path(sys.executable).resolve().parents[2]/'vision-lab-mediapipe/bin/python'))
        if not Path(worker).exists():raise ValueError('MediaPipe 独立环境未安装；运行 scripts/setup_mediapipe.sh')
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT/'data') as temp:
            image=Path(temp)/'input.png';cv2.imwrite(str(image),im);output=Path(temp)/'result.json'
            completed=subprocess.run([worker,str(ROOT/'scripts/mediapipe_worker.py'),model_id,str(obj/(model_id+'.task')),str(image),str(output)],capture_output=True,text=True,timeout=120)
            if completed.returncode:raise ValueError(completed.stderr[-1500:])
            data=json.loads(output.read_text());l=blank_layer(im)
            for entity in data['landmarks']:
                for point in entity:cv2.circle(l,(int(point['x']*w),int(point['y']*h)),2,(80,220,180,255),-1)
            layers['关键点']=l;data['coordinate_space']='normalized，乘原图宽高得到像素坐标'
    else:raise ValueError(f'任务 {id} 未配置适配器')
    data['model']=model_id;data['device']=DEVICE
    return Result(out,data,layers,arrays)
