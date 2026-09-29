"""有界内存视频执行与基于真实检测轨迹的事件规则。"""
import collections
import json
import subprocess
import time
import zipfile
import cv2
import numpy as np
from .algorithms.common import gray, color, roi_of
from .algorithms.special import box_iou
from .config import DEVICE
from .models import LOCK, load_model, require

class Cancelled(Exception):pass

def probe(path):
    result=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,timeout=30)
    if result.returncode:raise ValueError('FFprobe 无法读取视频：'+result.stderr[-500:])
    info=json.loads(result.stdout);stream=next((x for x in info['streams'] if x['codec_type']=='video'),None)
    if not stream:raise ValueError('文件没有视频轨道')
    numerator,denominator=map(float,stream.get('avg_frame_rate','25/1').split('/'));fps=numerator/denominator if denominator else 25
    return {'width':stream['width'],'height':stream['height'],'fps':fps or 25,'duration':float(info.get('format',{}).get('duration',0)),'audio':any(x['codec_type']=='audio' for x in info['streams'])}

def ffmpeg(args,cancel=lambda:False):
    import tempfile
    with tempfile.TemporaryFile() as log:
        process=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)],stdout=subprocess.DEVNULL,stderr=log)
        while process.poll() is None:
            if cancel():
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                raise Cancelled('任务已取消')
            time.sleep(.1)
        if process.returncode:
            log.seek(0);raise ValueError('视频编码失败：'+log.read().decode(errors='replace')[-1500:])

def normalize_video(source,target):
    info=probe(source)
    if info['duration']>300:raise ValueError('教学实验视频最长 5 分钟，请先裁剪')
    if info['width']*info['height']>3840*2160:raise ValueError('视频最大支持 4K')
    fps=min(60,max(1,info['fps']))
    ffmpeg(['-i',source,'-map','0:v:0','-map','0:a?','-vf',f'fps={fps},scale=trunc(iw/2)*2:trunc(ih/2)*2','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',target])
    return probe(target)

class Tracker:
    """按类别、IoU 进行一对一关联；不是带重识别的 ByteTrack。"""
    def __init__(self):self.tracks={};self.next_id=1
    def update(self,detections,frame):
        used=set();active=[]
        for detection in sorted(detections,key=lambda x:-x['confidence']):
            candidates=[(box_iou(detection['box'],track['box']),id) for id,track in self.tracks.items() if id not in used and track['class_id']==detection['class_id'] and frame-track['last']<=15]
            score,id=max(candidates,default=(0,0))
            if score<.2:id=self.next_id;self.next_id+=1;self.tracks[id]={'history':collections.deque(maxlen=90)}
            track=self.tracks[id];track.update(detection,last=frame,id=id);box=detection['box'];track['history'].append([(box[0]+box[2])/2,(box[1]+box[3])/2]);used.add(id);active.append(track)
        self.tracks={id:track for id,track in self.tracks.items() if frame-track['last']<=30}
        return active

class EventRules:
    def __init__(self,p,width,height):
        self.p=p;self.width=width;self.roi=roi_of(p,np.zeros((height,width,3),np.uint8),required=False);self.state={};self.sequence={};self.crossings=set()
    def update(self,tracks,t):
        events=[];present={track['id'] for track in tracks}
        for track in tracks:
            id=track['id'];cx,cy=track['history'][-1];x,y,w,h=self.roi;inside=x<=cx<=x+w and y<=cy<=y+h
            old=self.state.get(id,{'inside':False,'cx':cx,'since':None,'dwelled':False})
            kinds=[]
            if inside and not old['inside']:kinds.append('enter');old['since']=t;old['dwelled']=False
            if not inside and old['inside']:kinds.append('exit');old['since']=None
            line=self.p['line_x']*self.width
            if (old['cx']-line)*(cx-line)<0:kinds.append('cross');self.crossings.add(id)
            if inside and old['since'] is not None and not old['dwelled'] and t-old['since']>=self.p['dwell']:kinds.append('dwell');old['dwelled']=True
            for kind in kinds:
                event={'kind':kind,'time':round(t,3),'track_id':id,'class_id':track['class_id'],'box_xyxy':track['box'],'evidence':{'previous_x':old['cx'],'center':[cx,cy],'line_x':line,'roi':list(self.roi),'inside_since':old['since']}}
                events.append(event)
                order=self.p.get('event_order',[])
                if order:
                    if not isinstance(order,list) or not order or any(q not in ['enter','exit','cross','dwell'] for q in order):raise ValueError('事件顺序仅支持 enter、exit、cross、dwell')
                    state=self.sequence.get(id,{'index':0,'start':t,'evidence':[]})
                    if t-state['start']>self.p['window']:state={'index':0,'start':t,'evidence':[]}
                    if kind==order[state['index']]:
                        if state['index']==0:state['start']=t
                        state['evidence'].append({'kind':kind,'time':t});state['index']+=1
                        if state['index']==len(order):events.append({'kind':'sequence_complete','time':round(t,3),'track_id':id,'evidence':state['evidence']});state={'index':0,'start':t,'evidence':[]}
                    self.sequence[id]=state
            self.state[id]={**old,'inside':inside,'cx':cx,'last':t}
        # 检测缺失会中断连续停留，不把遮挡时间累加成停留。
        for id,old in list(self.state.items()):
            if id not in present:old['since']=None;old['inside']=False;old['dwelled']=False
            if t-old.get('last',t)>60:self.state.pop(id,None);self.sequence.pop(id,None)
        return events

def run_video(algorithm,path,p,extra,directory,progress,cancel,run_image,composite):
    info=probe(path);capture=cv2.VideoCapture(str(path));fps=capture.get(cv2.CAP_PROP_FPS) or info['fps'];total=int(capture.get(cv2.CAP_PROP_FRAME_COUNT));ok,first=capture.read()
    if not ok:capture.release();raise ValueError('无法解码首帧')
    h,w=first.shape[:2];capture.set(cv2.CAP_PROP_POS_FRAMES,0);writer=None;raw=directory/'silent.mp4';events=[];index=0;prev=None;points=None;bg=cv2.createBackgroundSubtractorMOG2();tracker=Tracker();rules=EventRules(p,w,h) if algorithm.id in ['events','sequence'] else None;single=None;clip=collections.deque(maxlen=16);latest_action=None
    if p.get('sample_every',1)!=1 and algorithm.temporal:raise ValueError('真正时序算法需要连续帧，请将推理间隔设置为 1')
    if algorithm.id=='action' and total<16:capture.release();raise ValueError('动作识别至少需要连续 16 帧；请上传更长的视频')
    if algorithm.id=='single_track':
        rect=roi_of(p,first)
        if not hasattr(cv2,'TrackerCSRT_create'):raise ValueError('CSRT 需要安装 opencv-contrib-python-headless')
        single=cv2.TrackerCSRT_create();single.init(first,rect)
    sam_stream=None
    if algorithm.id=='video_segment':
        if total>150:raise ValueError('SAM2 记忆分割最多 150 帧，防止内部记忆缓存无界增长；请裁剪短视频后运行')
        from ultralytics.models.sam import SAM2VideoPredictor
        model_path=require('sam2')/'sam2_t.pt';rect=roi_of(p,first);x,y,rw,rh=rect
        sam=SAM2VideoPredictor(overrides={'model':str(model_path),'task':'segment','mode':'predict','imgsz':512,'device':DEVICE,'verbose':False,'save':False})
        sam_stream=iter(sam(source=str(path),stream=True,bboxes=[x,y,x+rw,y+rh]))
    timeline=directory/'frames.jsonl';mask_archive=None
    def save_mask(name,array):
        # PNG 逐帧写入 ZIP，不把整段视频的掩膜留在内存中。
        nonlocal mask_archive
        if mask_archive is None:mask_archive=zipfile.ZipFile(directory/'masks.zip','w',zipfile.ZIP_STORED)
        encoded=cv2.imencode('.png',array)[1]
        mask_archive.writestr(f'{name}/{index:06d}.png',encoded.tobytes())
    try:
        with open(timeline,'w') as frames:
            while True:
                if cancel():raise Cancelled('任务已取消')
                ok,frame=capture.read()
                if not ok:break
                t=index/fps;g=gray(frame);out=frame.copy();details={};new_events=[]
                if algorithm.id=='frame_diff':out=cv2.absdiff(g,prev) if prev is not None else np.zeros_like(g)
                elif algorithm.id=='mog2':out=bg.apply(frame)
                elif algorithm.id=='flow_dense':
                    if prev is not None:
                        flow=cv2.calcOpticalFlowFarneback(prev,g,None,.5,3,15,3,5,1.2,0);mag,ang=cv2.cartToPolar(flow[:,:,0],flow[:,:,1]);hsv=np.zeros_like(frame);hsv[:,:,0]=ang*90/np.pi;hsv[:,:,1]=255;hsv[:,:,2]=cv2.normalize(mag,None,0,255,cv2.NORM_MINMAX);out=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR);details['mean_motion_px']=float(mag.mean())
                elif algorithm.id=='flow_sparse':
                    if prev is not None and points is not None and len(points):
                        next_points,status,_=cv2.calcOpticalFlowPyrLK(prev,g,points,None)
                        if next_points is not None:
                            good=next_points[status[:,0]==1];old=points[status[:,0]==1]
                            for a,b in zip(old[:,0],good[:,0]):cv2.arrowedLine(out,tuple(a.astype(int)),tuple(b.astype(int)),(70,220,180),2)
                            points=good.reshape(-1,1,2);details['tracked_points']=len(good)
                    if points is None or len(points)<30:points=cv2.goodFeaturesToTrack(g,200,.01,8)
                elif algorithm.id=='single_track':
                    if index==0:box=roi_of(p,frame);success=True
                    else:success,box=single.update(frame)
                    details={'tracked':bool(success),'box':list(box) if success else None}
                    if success:x,y,rw,rh=map(int,box);cv2.rectangle(out,(x,y),(x+rw,y+rh),(70,220,180),2)
                elif algorithm.id in ['multi_track','events','sequence']:
                    with LOCK:
                        model=load_model('yolov8n');result=model.predict(frame,device=DEVICE,verbose=False,conf=.3,imgsz=640)[0]
                    detections=[{'box':b.xyxy[0].cpu().tolist(),'class_id':int(b.cls[0]),'confidence':float(b.conf[0])} for b in result.boxes];tracks=tracker.update(detections,index)
                    for track in tracks:
                        x1,y1,x2,y2=map(int,track['box']);cv2.rectangle(out,(x1,y1),(x2,y2),(80,220,160),2);cv2.putText(out,f'#{track["id"]} {result.names[track["class_id"]]}',(x1,max(18,y1-5)),0,.5,(240,240,240),1);cv2.polylines(out,[np.array(track['history'],np.int32)],False,(80,180,250),2)
                    details['tracks']=[{k:v for k,v in track.items() if k!='history'} for track in tracks]
                    if rules:
                        new_events=rules.update(tracks,t);x,y,rw,rh=rules.roi;cv2.rectangle(out,(x,y),(x+rw,y+rh),(230,160,60),2);lx=int(p['line_x']*w);cv2.line(out,(lx,0),(lx,h),(100,210,255),2);details['unique_crossings']=len(rules.crossings)
                elif algorithm.id=='action':
                    import torch
                    clip.append(cv2.cvtColor(cv2.resize(frame,(171,128)),cv2.COLOR_BGR2RGB))
                    if len(clip)==16 and (index%16==15 or latest_action is None):
                        with LOCK:
                            model,transform,categories=load_model('r3d');tensor=torch.from_numpy(np.stack(clip)).permute(0,3,1,2);inputs=transform(tensor).unsqueeze(0).to(DEVICE)
                            with torch.inference_mode():probs=model(inputs).softmax(1)[0];vals,ids=probs.topk(5)
                        latest_action=[{'label':categories[int(c)],'probability':float(s)} for s,c in zip(vals,ids)];new_events=[{'kind':'action','time':round(t,3),'window_start':max(0,(index-15)/fps),'top5':latest_action}]
                    if latest_action:cv2.putText(out,latest_action[0]['label'],(15,30),0,.7,(80,230,180),2);details['top5']=latest_action
                elif algorithm.id=='video_segment':
                    with LOCK:result=next(sam_stream)
                    label_map=np.zeros((h,w),np.uint16)
                    if result.masks is not None:
                        from ultralytics.utils.ops import scale_masks
                        raw_masks=result.masks.data
                        aligned=raw_masks if tuple(raw_masks.shape[-2:])==(h,w) else scale_masks(raw_masks[None].float(),(h,w))[0]
                        overlay=out.copy();polygons=[]
                        for i,q in enumerate(result.masks.xy):
                            active=aligned[i].cpu().numpy()>.5;overlay[active]=(80,220,160);label_map[active]=i+1;polygons.append(q.tolist())
                        out=cv2.addWeighted(out,.5,overlay,.5,0);details['mask_polygons']=polygons
                    save_mask('instance_labels',label_map);details['mask_file']=f'instance_labels/{index:06d}.png'
                else:
                    result=run_image(algorithm.id,frame,p,extra);out=composite(result);details=result.data
                    for name,array in result.arrays.items():
                        if array.ndim==2 and array.dtype in [np.uint8,np.uint16] and ('mask' in name or 'labels' in name):
                            save_mask(name,array);details.setdefault('mask_files',[]).append(f'{name}/{index:06d}.png')
                out=color(out)
                if writer is None:
                    oh,ow=out.shape[:2];writer=cv2.VideoWriter(str(raw),cv2.VideoWriter_fourcc(*'mp4v'),fps,(ow,oh))
                    if not writer.isOpened():raise ValueError('无法创建视频编码器')
                writer.write(out)
                for event in new_events:
                    if len(events)<2000:
                        name=f'event-{len(events):04d}.jpg';cv2.imwrite(str(directory/name),out);event['frame_file']=name;events.append(event)
                frames.write(json.dumps({'frame':index,'time':round(t,4),**details},ensure_ascii=False,default=lambda v:v.item() if isinstance(v,np.generic) else str(v))+'\n')
                prev=g;index+=1
                if index%5==0:progress(min(.9,index/max(total,1)*.9),f'处理视频 {index}/{total} 帧')
    finally:
        capture.release()
        if writer:writer.release()
        if mask_archive:mask_archive.close()
        if sam_stream and hasattr(sam_stream,'close'):sam_stream.close()
    if index==0:raise ValueError('视频没有可处理的帧')
    progress(.92,'编码 H.264 与恢复音轨')
    final=directory/'result.mp4'
    ffmpeg(['-i',raw,'-i',path,'-map','0:v:0','-map','1:a?','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:a','aac','-t',str(index/fps),'-movflags','+faststart',final],cancel)
    raw.unlink(missing_ok=True)
    return {'video_file':'result.mp4','fps':fps,'frame_count':index,'duration':index/fps,'audio_preserved':info['audio'],'temporal':algorithm.temporal,'sampling':'逐帧，不丢帧；上传时已规范化为恒定帧率','mask_archive':'masks.zip' if mask_archive else None,'events':events,'classes':load_model('r3d')[2] if algorithm.id=='action' else None}
