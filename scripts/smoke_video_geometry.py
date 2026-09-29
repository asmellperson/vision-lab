#!/usr/bin/env python3
"""真实短视频与标定图片验证；只保留报告，不保留临时视频。"""
import json
import socket
import sys
import tempfile
import time
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.algorithms.registry import REGISTRY
from app.algorithms.common import read_image
from app.engine import execute,composite
from app.video import ffmpeg,run_video,probe
from app.models import release
report={}
def blocked(*args,**kwargs):raise RuntimeError('离线验证禁止网络连接')
socket.socket.connect=blocked
with tempfile.TemporaryDirectory(prefix='vision-video-') as temp:
    folder=Path(temp);source=folder/'short.mp4';ffmpeg(['-i',ROOT/'assets/examples/pedestrians.mp4','-t','2','-vf','scale=384:288','-c:v','libx264','-pix_fmt','yuv420p',source]);duration=probe(source)['duration']
    for id in ['frame_diff','mog2','flow_sparse','flow_dense','single_track','multi_track','events','sequence','action','video_segment','canny']:
        start=time.perf_counter();directory=folder/id;directory.mkdir();a=REGISTRY[id];p={'roi':[90,70,120,170]} if a.interaction else {};p=a.validate(p)
        try:
            result=run_video(a,source,p,{},directory,lambda p,m:None,lambda:False,execute,composite);meta=probe(directory/'result.mp4');assert abs(meta['duration']-duration)<.15;assert result['frame_count']==20
            report[id]={'status':'passed','seconds':round(time.perf_counter()-start,2),'fps':meta['fps'],'duration':meta['duration'],'events':len(result['events']),'offline':True};print('PASS',id,report[id]['seconds'],flush=True)
        except Exception as exc:report[id]={'status':'failed','error':str(exc)};print('FAIL',id,str(exc),flush=True)
        release();(ROOT/'docs/video-geometry-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    samples=sorted((ROOT/'assets/examples').glob('calibration-left*.jpg'));im=read_image(samples[0])
    try:
        result=execute('calibrate',im,{}, {'calibration_images':samples});assert result.data['rms_reprojection_px']<2;report['calibrate']={'status':'passed','rms_reprojection_px':result.data['rms_reprojection_px'],'images':len(result.data['used'])};(ROOT/'assets/examples/calibration-result.json').write_text(json.dumps(result.data,ensure_ascii=False,indent=2))
    except Exception as exc:report['calibrate']={'status':'failed','error':str(exc)}
    im=read_image(ROOT/'assets/examples/fruits.jpg')
    try:
        result=execute('stitch',im,{}, {'reference':[ROOT/'assets/examples/fruits-shift.png']});assert result.image.shape[1]>=im.shape[1];report['stitch']={'status':'passed','inliers':result.data['inliers'],'output_shape':list(result.image.shape)}
    except Exception as exc:report['stitch']={'status':'failed','error':str(exc)}
(ROOT/'docs/video-geometry-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(int(any(v['status']!='passed' for v in report.values())))
