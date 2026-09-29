"""统一图像执行、结果落盘与类型安全流水线。"""
import json
from pathlib import Path
import cv2
import numpy as np
from .algorithms.registry import load, REGISTRY, ALIASES
from .algorithms.common import read_image, color
from .algorithms.classical import run as classical
load()

def execute(id,im,params,extra=None):
    algorithm=REGISTRY[id];p=algorithm.validate(params);extra=extra or {}
    if algorithm.model:
        from .inference import infer
        from .model_manifest import MODELS
        model=p.get('model_id') or algorithm.model
        if model not in MODELS or id not in MODELS[model]['tasks']:raise ValueError('所选模型不支持当前任务')
        return infer(id,model,im,p,extra)
    return classical(ALIASES.get(id,id),im,p,extra)

def composite(result):
    image=color(result.image).astype('float32')
    for layer in result.layers.values():
        if layer.shape[:2]!=image.shape[:2]:raise ValueError('结果图层与底图坐标不一致')
        alpha=layer[:,:,3:4].astype('float32')/255;image=image*(1-alpha)+layer[:,:,:3]*alpha
    return image.astype('uint8')

def json_default(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,Path):return str(value)
    raise TypeError(type(value).__name__)

def save_result(result,directory):
    directory.mkdir(parents=True,exist_ok=True);cv2.imwrite(str(directory/'base.png'),result.image);cv2.imwrite(str(directory/'result.png'),composite(result));layer_files=[];downloads=['result.png','data.json']
    for i,(name,layer) in enumerate(result.layers.items()):
        filename=f'layer-{i}.png';cv2.imwrite(str(directory/filename),layer);layer_files.append({'name':name,'file':filename});downloads.append(filename)
    for name,array in result.arrays.items():
        filename=name+'.npz';np.savez_compressed(directory/filename,**{name:array});downloads.append(filename)
        if array.dtype in [np.uint8,np.uint16] and array.ndim in [2,3] and (array.ndim==2 or array.shape[2] in [3,4]):cv2.imwrite(str(directory/(name+'.png')),array);downloads.append(name+'.png')
        if name=='points' and array.ndim==2 and array.shape[1]==3:np.savetxt(directory/'points.xyz',array,fmt='%.7g');downloads.append('points.xyz')
    (directory/'data.json').write_text(json.dumps(result.data,ensure_ascii=False,indent=2,default=json_default))
    return {'image_file':'base.png','composite_file':'result.png','width':result.image.shape[1],'height':result.image.shape[0],'layers':layer_files,'data':result.data,'downloads':downloads}

PIPELINE_ALLOWED={'gray','channel','merge','bit_not','brightness','gamma','equalize','clahe','mean','gaussian','median','bilateral','nlm','convolution','sharpen','fft','lowpass','highpass','threshold','adaptive','otsu','erode','dilate','open','close','morph_gradient','tophat','blackhat','skeleton','distance','sobel','scharr','laplacian','canny','contours','components','hull','count','measure','resize','rotate','affine','kmeans_segment','augmentation','lowlight'}

def validate_pipeline(steps):
    if not 1<=len(steps)<=15:raise ValueError('流水线需要 1–15 个步骤')
    kind='image';enabled=0
    for step in steps:
        if not step.get('enabled',True):continue
        id=step.get('algorithm')
        if id not in PIPELINE_ALLOWED:raise ValueError(f'{id} 需要专用输入/模型，不能直接接入当前图像流水线')
        if kind=='overlay':raise ValueError('轮廓/计数/测量产生结构化结果，必须位于流水线最后一步')
        if id in ['erode','dilate','open','close','morph_gradient','tophat','blackhat'] and kind not in ['mask','gray']:raise ValueError('流水线形态学输入应先经过灰度或阈值步骤')
        REGISTRY[id].validate(step.get('params',{}));kind=REGISTRY[id].output_kind;enabled+=1
    if not enabled:raise ValueError('至少启用一个步骤')

def run_pipeline(im,steps,directory,progress,cancel):
    from .video import Cancelled
    validate_pipeline(steps);results=[]
    for i,step in enumerate(steps):
        if cancel():raise Cancelled('流水线已取消')
        if not step.get('enabled',True):continue
        result=execute(step['algorithm'],im,step.get('params',{}));folder=directory/f'step-{i}';saved=save_result(result,folder);results.append({'step':i,'algorithm':step['algorithm'],'folder':folder.name,**saved});im=result.image;progress((i+1)/len(steps)*.9,f'步骤 {i+1} 完成')
    final=save_result(result,directory);final['steps']=results;return final
