#!/usr/bin/env python3
"""补齐需要专用任务输入的官方示例；原始来源写入 manifest。"""
import io
import json
import urllib.request
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'assets/examples';manifest=json.loads((DEST/'manifest.json').read_text())
def download(file,name,url,**kwargs):
    target=DEST/file
    if not target.exists():
        with urllib.request.urlopen(url,timeout=90) as response:target.write_bytes(response.read())
    manifest[:]=[x for x in manifest if x['file']!=file]
    manifest.append(dict(file=file,name=name,kind='image',source=url,**kwargs));print(file,flush=True)
for i in [1,2,3,4,5,6,7,8,9,11,12,13,14]:
    try:
        download(f'calibration-left{i:02d}.jpg',f'真实标定左图 {i:02d} · 9×6 内角点',f'https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/left{i:02d}.jpg',role='calibration_images',license='OpenCV Apache-2.0')
        download(f'calibration-right{i:02d}.jpg',f'真实标定右图 {i:02d}',f'https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/right{i:02d}.jpg',role='stereo_calibration',license='OpenCV Apache-2.0')
    except Exception as exc:print(exc)
for file,name,url in [
    ('calibration-right01.jpg','真实标定右图 01','https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/right01.jpg'),
    ('document.jpg','中英文文档 · 真实版面','https://raw.githubusercontent.com/opendatalab/DocLayout-YOLO/main/assets/example/exam_paper.jpg'),
    ('hands.jpg','手部关键点 · MediaPipe 官方示例','https://storage.googleapis.com/mediapipe-assets/right_hands.jpg'),
]:
    try:download(file,name,url)
    except Exception as exc:print(file,exc)
try:
    url='https://github.com/ultralytics/assets/releases/download/v0.0.0/dota8.zip'
    with urllib.request.urlopen(url,timeout=90) as response:archive=zipfile.ZipFile(io.BytesIO(response.read()))
    member=next(n for n in archive.namelist() if '/images/' in n and n.lower().endswith(('.png','.jpg')))
    (DEST/'aerial.png').write_bytes(archive.read(member));manifest[:]=[x for x in manifest if x['file']!='aerial.png'];manifest.append(dict(file='aerial.png',name='航拍旋转目标 · DOTA8',kind='image',source=url,license='DOTA research dataset; see upstream terms'))
except Exception as exc:print('aerial',exc)
try:
    import cv2
    import numpy as np
    objects=[];left_points=[];right_points=[];obj=np.zeros((54,3),np.float32);obj[:,:2]=np.mgrid[:9,:6].T.reshape(-1,2)
    for left_path in sorted(DEST.glob('calibration-left*.jpg')):
        right_path=DEST/left_path.name.replace('left','right')
        if not right_path.exists():continue
        left=cv2.imread(str(left_path));right=cv2.imread(str(right_path));size=(left.shape[1],left.shape[0]);ok1,pts1=cv2.findChessboardCornersSB(cv2.cvtColor(left,cv2.COLOR_BGR2GRAY),(9,6));ok2,pts2=cv2.findChessboardCornersSB(cv2.cvtColor(right,cv2.COLOR_BGR2GRAY),(9,6))
        if ok1 and ok2:objects.append(obj);left_points.append(pts1);right_points.append(pts2)
    _,K1,D1,_,_=cv2.calibrateCamera(objects,left_points,size,None,None);_,K2,D2,_,_=cv2.calibrateCamera(objects,right_points,size,None,None)
    rms,K1,D1,K2,D2,R,T,E,F=cv2.stereoCalibrate(objects,left_points,right_points,K1,D1,K2,D2,size,flags=cv2.CALIB_FIX_INTRINSIC)
    cal={k:v.tolist() for k,v in dict(K1=K1,D1=D1,K2=K2,D2=D2,R=R,T=T).items()};cal.update(translation_unit='棋盘格边长（实测大小未知）',rms_reprojection_px=float(rms));(DEST/'stereo-calibration.json').write_text(json.dumps(cal,ensure_ascii=False,indent=2))
    (DEST/'calibration-result.json').write_text(json.dumps({'camera':K1.tolist(),'distortion':D1.ravel().tolist(),'rms_reprojection_px':float(rms),'image_size':list(size)},ensure_ascii=False,indent=2))
    R1,R2,P1,P2,Q,_,_=cv2.stereoRectify(K1,D1,K2,D2,size,R,T,alpha=0)
    for side,K,D,rot,projection in [('left',K1,D1,R1,P1),('right',K2,D2,R2,P2)]:
        src=cv2.imread(str(DEST/f'calibration-{side}01.jpg'));maps=cv2.initUndistortRectifyMap(K,D,rot,projection,size,cv2.CV_32FC1);image=cv2.remap(src,*maps,cv2.INTER_LINEAR);file=f'stereo-{side}.png';cv2.imwrite(str(DEST/file),image);manifest[:]=[x for x in manifest if x['file']!=file];manifest.append(dict(file=file,name=f'已极线校正双目 {side}',kind='image',source='OpenCV calibration sample + stereoRectify',license='OpenCV Apache-2.0'))
    print('Stereo calibration RMS',rms,flush=True)
except Exception as exc:print('stereo calibration',exc)
(DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
