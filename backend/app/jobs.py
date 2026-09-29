"""单工作线程保证模型显存和 CPU 内存上界，SQLite 保留所有状态。"""
import json
import queue
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path
from . import storage
from .config import DATA
from .algorithms.registry import REGISTRY
from .algorithms.common import read_image
from .engine import execute,save_result,run_pipeline,composite,json_default,validate_pipeline
from .video import run_video,Cancelled

QUEUE=queue.Queue(maxsize=32)
CANCEL={}
THREAD=None

def public_result(result,id):
    prefix=f'/api/files/{id}/'
    converted={**result}
    for key in ['image_file','composite_file','video_file']:
        if result.get(key):converted[key.replace('_file','_url')]=prefix+result[key]
    converted['layers']=[{**layer,'url':prefix+layer['file']} for layer in result.get('layers',[])]
    converted['downloads']=[{'name':name,'url':prefix+name} for name in result.get('downloads',[])]
    for event in converted.get('events',[]):
        if event.get('frame_file'):event['frame_url']=prefix+event['frame_file']
    converted['steps']=[{**step,'image_url':prefix+step['folder']+'/result.png'} for step in result.get('steps',[])]
    return converted

def submit(request):
    algorithm=request['algorithm'];params=request.get('params',{})
    if algorithm=='pipeline':validate_pipeline(request.get('steps',[]))
    elif algorithm=='model_download':
        from .model_manifest import MODELS
        if params.get('model') not in MODELS:raise ValueError('未知模型')
    else:
        if algorithm not in REGISTRY:raise ValueError('未知算法')
        REGISTRY[algorithm].validate(params)
    if algorithm!='model_download':
        source=storage.asset(request['asset_id'])
        if algorithm=='pipeline' and source['kind']!='image':raise ValueError('当前流水线只接收图片')
        if algorithm not in ['pipeline']:
            spec=REGISTRY[algorithm]
            if spec.inputs[0]=='video' and source['kind']!='video':raise ValueError('该任务需要连续视频输入')
            if spec.inputs[0]=='pointcloud' and source['kind']!='pointcloud':raise ValueError('该任务需要 XYZ / ASCII PLY 点云')
            if source['kind']=='video' and not spec.temporal and (len(spec.inputs)>1 or spec.interaction or spec.output_kind=='overlay' and not spec.model):raise ValueError('该图片实验需要专用输入或交互，请选择图片；视频请使用时序模块或单图滤波/检测')
        for key,ids in request.get('extra',{}).items():
            if key not in ['normal_samples','calibration_images','gallery'] and len(ids)>1:raise ValueError(f'{key} 仅接受一份输入；请移除多余文件')
            for id in ids:storage.asset(id)
    id=uuid.uuid4().hex;now=time.time();storage.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)',(id,algorithm,request.get('asset_id',''),json.dumps(request,ensure_ascii=False),'queued',0,'等待工作线程',None,now,None));CANCEL[id]=threading.Event()
    try:QUEUE.put_nowait(id)
    except queue.Full:storage.execute('DELETE FROM jobs WHERE id=?',(id,));CANCEL.pop(id,None);raise ValueError('队列已满，请等待现有任务完成')
    return storage.job(id)

def cancel(id):
    job=storage.job(id)
    if job['status'] in ['queued','running','cancelling']:
        if id in CANCEL:CANCEL[id].set()
        storage.execute("UPDATE jobs SET status='cancelling',message='正在取消；当前算子结束后停止' WHERE id=?",(id,))
    return storage.job(id)

def code_example(request):
    """生成基于本项目执行库的可运行 Python，而非与参数脱节的静态代码。"""
    asset=storage.asset(request['asset_id']);params=request.get('params',{});extra={k:[Path(storage.asset(id)['path']) for id in ids] for k,ids in request.get('extra',{}).items()}
    lines=[
        '# 先 conda activate vision-lab，再在项目目录运行：PYTHONPATH=backend python experiment.py',
        '# 使用本项目已安装的执行器；所有推理仅从本地模型目录读取。',
        'import json', 'from pathlib import Path', 'from app.algorithms.common import read_image',
        'from app.engine import execute, save_result',
        f'algorithm = {request["algorithm"]!r}',f'params = json.loads({json.dumps(params,ensure_ascii=False)!r})',
        f'extra = {{k: [Path(p) for p in v] for k,v in json.loads({json.dumps(extra,default=str,ensure_ascii=False)!r}).items()}}',
        f'input_path = Path({asset["path"]!r})',
        'output_dir = Path("experiment-output")', 'output_dir.mkdir(exist_ok=True)',
    ]
    if asset['kind']=='video':
        lines += ['from app.video import run_video','from app.engine import composite','from app.algorithms.registry import REGISTRY',
                  'spec = REGISTRY[algorithm]', 'params = spec.validate(params)',
                  'saved = run_video(spec, input_path, params, extra, output_dir, lambda p,m: print(f"{p:.0%} {m}"), lambda: False, execute, composite)']
    elif request['algorithm']=='pipeline':
        lines += ['from app.engine import run_pipeline',f'steps = json.loads({json.dumps(request.get("steps",[]),ensure_ascii=False)!r})',
                  'saved = run_pipeline(read_image(input_path), steps, output_dir, lambda p,m: print(m), lambda: False)']
    elif request['algorithm']=='pointcloud':
        lines += ['from app.algorithms.special import pointcloud','from app.algorithms.registry import REGISTRY',
                  'result = pointcloud(input_path, REGISTRY[algorithm].validate(params), extra)','saved = save_result(result, output_dir)']
    else:
        lines += ['image = read_image(input_path)','result = execute(algorithm, image, params, extra)','saved = save_result(result, output_dir)']
    return '\n'.join(lines+['print(json.dumps(saved, ensure_ascii=False, indent=2, default=str))',''])

def work():
    while True:
        id=QUEUE.get()
        if id is None:QUEUE.task_done();return
        directory=DATA/'results'/id;event=CANCEL[id]
        def update(progress,message):storage.execute('UPDATE jobs SET progress=?,message=? WHERE id=?',(float(progress),message,id))
        try:
            if event.is_set():raise Cancelled('任务已取消')
            request=storage.job(id)['request'];algorithm=request['algorithm'];storage.execute("UPDATE jobs SET status='running',message='执行中' WHERE id=?",(id,));start=time.perf_counter();directory.mkdir(parents=True,exist_ok=True)
            if algorithm=='model_download':
                from .models import download
                def model_progress(p,m):
                    if event.is_set():raise Cancelled('下载已取消')
                    update(p,m)
                result={'model':download(request['params']['model'],model_progress),'downloads':[]}
            else:
                source=storage.asset(request['asset_id']);path=Path(source['path']);extra={k:[Path(storage.asset(asset_id)['path']) for asset_id in ids] for k,ids in request.get('extra',{}).items()};params=request.get('params',{})
                if algorithm=='pipeline':result=run_pipeline(read_image(path),request['steps'],directory,update,event.is_set)
                elif source['kind']=='video':
                    spec=REGISTRY[algorithm];result=run_video(spec,path,spec.validate(params),extra,directory,update,event.is_set,execute,composite);result['downloads']=['result.mp4','frames.jsonl','data.json']
                    if result.get('mask_archive'):result['downloads'].append(result['mask_archive'])
                    (directory/'data.json').write_text(json.dumps(result,ensure_ascii=False,default=json_default))
                elif algorithm=='pointcloud':
                    from .algorithms.special import pointcloud
                    result=save_result(pointcloud(path,REGISTRY[algorithm].validate(params),extra),directory)
                else:
                    update(.15,'处理图像');result=save_result(execute(algorithm,read_image(path),params,extra),directory)
                (directory/'experiment.py').write_text(code_example(request));result['downloads'].append('experiment.py')
                (directory/'request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2));result['downloads'].append('request.json')
                with zipfile.ZipFile(directory/'experiment.zip','w',zipfile.ZIP_DEFLATED) as z:
                    for file in directory.rglob('*'):
                        if file.is_file() and file.name!='experiment.zip':z.write(file,file.relative_to(directory))
                result['downloads'].append('experiment.zip')
            if event.is_set():raise Cancelled('任务已取消')
            result['elapsed_ms']=round((time.perf_counter()-start)*1000,2);result=public_result(result,id)
            storage.execute("UPDATE jobs SET status='completed',progress=1,message='实验完成',result=?,finished=? WHERE id=?",(json.dumps(result,ensure_ascii=False,default=json_default),time.time(),id))
        except Cancelled as exc:
            shutil.rmtree(directory,ignore_errors=True);storage.execute("UPDATE jobs SET status='cancelled',message=?,finished=? WHERE id=?",(str(exc),time.time(),id))
        except Exception as exc:
            storage.execute("UPDATE jobs SET status='failed',message=?,finished=? WHERE id=?",(f'{type(exc).__name__}: {exc}',time.time(),id))
            import traceback
            traceback.print_exc()
        finally:CANCEL.pop(id,None);QUEUE.task_done()

def start():
    global THREAD
    if THREAD is None or not THREAD.is_alive():THREAD=threading.Thread(target=work,name='vision-worker',daemon=True);THREAD.start()
