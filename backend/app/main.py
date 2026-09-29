"""统一实验 REST API 与生产前端静态服务。"""
import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import cv2
from fastapi import FastAPI,UploadFile,HTTPException
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .config import ROOT,DATA,MAX_UPLOAD,DEVICE
from . import storage,jobs
from .algorithms.registry import REGISTRY
from .algorithms.common import read_image
from .engine import execute,composite,PIPELINE_ALLOWED
from .video import normalize_video

@asynccontextmanager
async def lifespan(app):
    storage.init();import_examples();jobs.start();yield

app=FastAPI(title='计算机视觉实验平台',version='1.0.0',lifespan=lifespan)

@app.exception_handler(ValueError)
async def value_error(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422,content={'detail':str(exc)})

class Experiment(BaseModel):
    algorithm:str
    asset_id:str=''
    params:dict=Field(default_factory=dict)
    extra:dict[str,list[str]]=Field(default_factory=dict)
    steps:list[dict]=Field(default_factory=list)

class Preset(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    algorithm:str
    content:dict

def present_asset(row):
    return {k:v for k,v in row.items() if k!='path'}|{'url':f'/api/assets/{row["id"]}/content','poster':f'/api/assets/{row["id"]}/poster' if row['kind']=='video' else None}

def import_examples():
    manifest=ROOT/'assets/examples/manifest.json'
    if not manifest.exists():return
    for item in json.loads(manifest.read_text()):
        path=ROOT/'assets/examples'/item['file'];id='example-'+path.stem
        if not path.exists():continue
        metadata={**item,'example':True}
        if item['kind']=='image':
            im=read_image(path);metadata.update(width=im.shape[1],height=im.shape[0])
        storage.execute('INSERT OR IGNORE INTO assets VALUES (?,?,?,?,?,?)',(id,item['name'],item['kind'],str(path),json.dumps(metadata,ensure_ascii=False),time.time()))

@app.get('/api/health')
def health():return {'status':'ok','device':DEVICE,'algorithms':len(REGISTRY),'queue':jobs.QUEUE.qsize()}

@app.get('/api/algorithms')
def algorithms():return [a.dict()|{'pipeline_compatible':a.id in PIPELINE_ALLOWED} for a in REGISTRY.values()]

@app.get('/api/algorithms/{id}/example')
def recipe(id:str):
    from .recipes import example_for
    return example_for(id)

@app.get('/api/assets')
def assets(examples:bool=False):
    rows=storage.rows('SELECT * FROM assets ORDER BY created DESC LIMIT 500')
    for row in rows:row['metadata']=json.loads(row['metadata'])
    return [present_asset(row) for row in rows if not examples or row['metadata'].get('example')]

@app.post('/api/assets')
async def upload(file:UploadFile):
    suffix=Path(file.filename or '').suffix.lower();image_ext={'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'};video_ext={'.mp4','.avi','.mov','.mkv','.webm'};cloud_ext={'.ply','.xyz','.csv'}
    if suffix not in image_ext|video_ext|cloud_ext|{'.npz'}:raise ValueError('支持图片、视频、XYZ/ASCII PLY/CSV 点云和参考库 NPZ')
    id=uuid.uuid4().hex;path=DATA/'uploads'/(id+suffix);size=0
    try:
        with open(path,'wb') as output:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>MAX_UPLOAD:raise ValueError(f'文件超过 {MAX_UPLOAD//1024//1024} MB 限制')
                output.write(chunk)
        if not size:raise ValueError('文件为空')
        kind='image' if suffix in image_ext else 'video' if suffix in video_ext else 'pointcloud' if suffix in cloud_ext else 'bank';metadata={'size':size}
        if kind=='image':
            im=await asyncio.to_thread(read_image,path);normalized=path.with_suffix('.png');cv2.imwrite(str(normalized),im)
            if path!=normalized:path.unlink();path=normalized
            metadata.update(width=im.shape[1],height=im.shape[0],orientation='EXIF 已归一化')
        elif kind=='video':
            normalized=path.with_name(id+'-normalized.mp4');metadata.update(await asyncio.to_thread(normalize_video,path,normalized));path.unlink();path=normalized
        elif kind=='pointcloud':
            from .algorithms.special import read_cloud
            points=await asyncio.to_thread(read_cloud,path);metadata['points']=len(points)
        else:
            import numpy as np
            with np.load(path,allow_pickle=False) as bank:
                if 'features' not in bank or bank['features'].ndim!=2 or bank['features'].shape[1]!=384 or bank['features'].shape[0]>10000:raise ValueError('无效参考库，需要 features 矩阵，维度 N×384 且 N≤10000')
        storage.execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',(id,Path(file.filename or '上传素材').name,kind,str(path),json.dumps(metadata,ensure_ascii=False),time.time()));return present_asset(storage.asset(id))
    except Exception as exc:
        path.unlink(missing_ok=True)
        for leftover in (DATA/'uploads').glob(id+'-*'):leftover.unlink(missing_ok=True)
        if isinstance(exc,ValueError):raise
        raise ValueError('素材解析失败：'+str(exc)) from exc
    finally:await file.close()

@app.get('/api/assets/{id}/content')
def asset_content(id:str):return FileResponse(storage.asset(id)['path'])

@app.get('/api/assets/{id}/poster')
def poster(id:str,time_seconds:float=0):
    item=storage.asset(id)
    if item['kind']!='video':raise ValueError('素材不是视频')
    cap=cv2.VideoCapture(item['path'])
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC,max(0,time_seconds)*1000);ok,frame=cap.read()
        if not ok:raise ValueError('该时间没有可解码帧')
        return Response(cv2.imencode('.jpg',frame)[1].tobytes(),media_type='image/jpeg')
    finally:cap.release()

@app.post('/api/experiments')
def run(request:Experiment):return jobs.submit(request.model_dump())

@app.get('/api/experiments')
def history(asset_id:str|None=None):
    found=storage.rows('SELECT id FROM jobs '+('WHERE asset_id=? ' if asset_id else '')+'ORDER BY created DESC LIMIT 100',(asset_id,) if asset_id else ())
    return [storage.job(row['id']) for row in found]

@app.get('/api/experiments/{id}')
def job(id:str):return storage.job(id)

@app.post('/api/experiments/{id}/cancel')
def cancel(id:str):return jobs.cancel(id)

@app.post('/api/code')
def code(request:Experiment):
    if not request.asset_id:raise ValueError('先选择素材即可生成与当前参数一致的示例')
    return {'code':jobs.code_example(request.model_dump())}

PREVIEW=None

@app.post('/api/banks/from-job/{id}')
def bank_from_job(id:str):
    job=storage.job(id)
    if job['status']!='completed' or job['algorithm']!='anomaly':raise ValueError('只有已完成的异常参考库实验可复用')
    path=DATA/'results'/id/'features.npz'
    if not path.is_file():raise ValueError('实验没有生成参考库文件')
    asset_id='bank-'+id
    storage.execute('INSERT OR IGNORE INTO assets VALUES (?,?,?,?,?,?)',(asset_id,'正常参考库 '+id[:8],'bank',str(path),json.dumps({'source_job':id,'backbone':'resnet18','feature_dimension':384}),time.time()))
    return present_asset(storage.asset(asset_id))

@app.post('/api/preview')
def preview(request:Experiment):
    import threading
    global PREVIEW
    if PREVIEW is None:PREVIEW=threading.BoundedSemaphore(2)
    spec=REGISTRY.get(request.algorithm)
    if not spec or not spec.preview or spec.model or spec.interaction:raise ValueError('此任务需要点击运行，不支持轻量预览')
    source=storage.asset(request.asset_id)
    if source['kind']!='image':raise ValueError('预览只支持图片')
    if not PREVIEW.acquire(blocking=False):raise HTTPException(429,'预览繁忙')
    try:
        im=read_image(source['path']);scale=min(1,800/max(im.shape[:2]));im=cv2.resize(im,None,fx=scale,fy=scale)
        extra={k:[Path(storage.asset(id)['path']) for id in ids] for k,ids in request.extra.items()}
        result=execute(request.algorithm,im,request.params,extra);return Response(cv2.imencode('.jpg',composite(result))[1].tobytes(),media_type='image/jpeg',headers={'X-Preview-Scale':str(scale)})
    finally:PREVIEW.release()

@app.get('/api/files/{id}/{filename:path}')
def file(id:str,filename:str):
    root=(DATA/'results'/id).resolve();target=(root/filename).resolve()
    if root.parent!=(DATA/'results').resolve() or not target.is_relative_to(root) or not target.is_file():raise HTTPException(404,'结果文件不存在')
    return FileResponse(target,filename=target.name if target.suffix in ['.zip','.npz','.json','.jsonl','.xyz','.py'] else None)

@app.get('/api/models')
def model_list():
    from .models import list_models
    return list_models()

@app.post('/api/models/{id}/download')
def download_model(id:str):return jobs.submit({'algorithm':'model_download','params':{'model':id}})

@app.post('/api/models/{id}/release')
def release_model(id:str):
    from .models import release
    release(None if id=='all' else id);return {'released':id}

@app.post('/api/models/{id}/verify')
def verify_model(id:str):
    from .models import status
    return status(id,verify=True)

@app.get('/api/presets')
def presets():
    rows=storage.rows('SELECT * FROM presets ORDER BY created DESC')
    for row in rows:row['content']=json.loads(row['content'])
    return rows

@app.post('/api/presets')
def save_preset(body:Preset):
    id=uuid.uuid4().hex;storage.execute('INSERT INTO presets VALUES (?,?,?,?,?)',(id,body.name,body.algorithm,json.dumps(body.content,ensure_ascii=False),time.time()));return {'id':id}

@app.delete('/api/presets/{id}')
def delete_preset(id:str):storage.execute('DELETE FROM presets WHERE id=?',(id,));return {'deleted':id}

dist=ROOT/'frontend/dist'
if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
