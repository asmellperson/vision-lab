#!/usr/bin/env python3
"""真实预训练模型离线冒烟：禁止网络连接，记录成功/失败，不把失败标为就绪。"""
import argparse
import json
import socket
import sys
import time
import traceback
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.engine import execute,save_result
from app.algorithms.registry import REGISTRY
from app.algorithms.common import read_image
from app.models import release,status

parser=argparse.ArgumentParser();parser.add_argument('--tasks',nargs='*');parser.add_argument('--output',default=str(ROOT/'docs/model-validation.json'));args=parser.parse_args()
def blocked(*args,**kwargs):raise RuntimeError('离线验证禁止网络连接')
socket.socket.connect=blocked
tasks=args.tasks or [id for id,a in REGISTRY.items() if a.model and not a.temporal]
report=json.loads(Path(args.output).read_text()) if args.tasks and Path(args.output).exists() else {}
for id in tasks:
    start=time.perf_counter();a=REGISTRY[id];file='hands.jpg' if id=='hand' else 'document.jpg' if id=='layout' else 'aerial.png' if id=='obb' else 'zidane.jpg' if id in ['face','pose'] else 'text.png' if id in ['ocr','char_check'] else 'defect.png' if id=='anomaly' else 'bus.jpg'
    im=read_image(ROOT/'assets/examples'/file);im=cv2.resize(im,(320,240));p={};extra={}
    if id=='sam':p={'roi':[40,40,200,180]}
    if id in ['similarity','text_retrieval']:extra={'gallery':[ROOT/'assets/examples/bus.jpg',ROOT/'assets/examples/fruits.jpg']}
    if id=='text_retrieval':p={'prompt':'a bus, a cat, a person'}
    if id=='anomaly':extra={'normal_samples':[ROOT/'assets/examples/normal-0.png',ROOT/'assets/examples/normal-1.png']}
    try:
        result=execute(id,im,p,extra);assert result.image.size>0
        for layer in result.layers.values():assert layer.shape[:2]==result.image.shape[:2]
        report[id]={'status':'passed','elapsed_seconds':round(time.perf_counter()-start,3),'model':a.model,'image_shape':list(result.image.shape),'layers':list(result.layers),'output_keys':list(result.data),'offline':True}
        if 'count' in result.data:report[id]['count']=result.data['count']
        if 'texts' in result.data:report[id]['texts']=[q['text'] for q in result.data['texts']]
        if 'landmarks' in result.data:report[id]['landmark_entities']=len(result.data['landmarks'])
        if id=='benchmark':report[id]['benchmark']=result.data
        if id=='detect':
            empty=execute('detect',np.zeros((240,320,3),np.uint8),{},{});assert empty.data['count']==0;report[id]['empty_image_count']=0
        print(f'PASS {id} {report[id]["elapsed_seconds"]:.2f}s',flush=True)
    except Exception as exc:report[id]={'status':'failed','error':str(exc),'model':a.model};print(f'FAIL {id}: {exc}',flush=True);traceback.print_exc()
    release()
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v['status'] for k,v in report.items()},ensure_ascii=False,indent=2))
raise SystemExit(int(any(v['status']!='passed' for v in report.values())))
