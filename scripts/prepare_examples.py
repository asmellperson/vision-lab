#!/usr/bin/env python3
"""官方真实素材加可复现的工业/标定教学素材；不伪称合成图为真实相机数据。"""
import json
import urllib.request
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'assets/examples';DEST.mkdir(parents=True,exist_ok=True);manifest=[]

def add(file,name,kind='image',**kwargs):manifest.append(dict(file=file,name=name,kind=kind,**kwargs))

sources=[('bus.jpg','街景公交 · 真实照片','https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/assets/bus.jpg','Ultralytics AGPL-3.0'),('zidane.jpg','人物姿态 · 真实照片','https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/assets/zidane.jpg','Ultralytics AGPL-3.0'),('sudoku.png','数独与透视 · 真实照片','https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/sudoku.png','OpenCV Apache-2.0'),('fruits.jpg','水果与颜色 · 真实照片','https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/fruits.jpg','OpenCV Apache-2.0')]
for file,name,url,license in sources:
    try:
        target=DEST/file
        if not target.exists():
            with urllib.request.urlopen(url,timeout=60) as response:target.write_bytes(response.read())
        add(file,name,source=url,license=license)
    except Exception as exc:print(file,exc)
canvas=np.full((480,640,3),28,np.uint8)
for x,y,r in [(130,130,55),(320,120,45),(510,140,60),(170,340,65),(440,340,70)]:
    cv2.circle(canvas,(x,y),r,(220,220,220),-1);cv2.circle(canvas,(x,y),r//3,(28,28,28),-1)
cv2.imwrite(str(DEST/'parts.png'),canvas);add('parts.png','零件轮廓 · 合成教学图',source='本项目程序生成',license='CC0')
for i in range(4):
    image=canvas.copy();noise=np.random.default_rng(i).normal(0,2,image.shape);image=np.clip(image+noise,0,255).astype('uint8');cv2.imwrite(str(DEST/f'normal-{i}.png'),image);add(f'normal-{i}.png',f'正常样本 {i+1} · 合成教学图',role='normal_samples',source='本项目程序生成',license='CC0')
damaged=canvas.copy();cv2.line(damaged,(400,310),(475,355),(15,15,15),8);cv2.rectangle(damaged,(275,70),(365,170),(28,28,28),-1);cv2.imwrite(str(DEST/'defect.png'),damaged);add('defect.png','缺件与划痕 · 合成教学图',source='本项目程序生成',license='CC0')
text=np.full((300,700,3),255,np.uint8);cv2.putText(text,'VISION LAB 2026',(35,110),0,1.8,(20,20,20),3);cv2.putText(text,'PART AB12345  PASS',(35,220),0,1.4,(20,20,20),2);cv2.imwrite(str(DEST/'text.png'),text);add('text.png','英文标签 · 合成教学图',source='本项目程序生成',license='CC0')
chess=np.zeros((350,500,3),np.uint8)
for y in range(7):
    for x in range(10):
        if (x+y)%2==0:chess[y*50:(y+1)*50,x*50:(x+1)*50]=255
cv2.imwrite(str(DEST/'chessboard.png'),chess);add('chessboard.png','9×6 内角点棋盘 · 需打印后拍摄多视角',source='本项目程序生成',license='CC0')
if (DEST/'fruits.jpg').exists():
    im=cv2.imread(str(DEST/'fruits.jpg'));h,w=im.shape[:2];ref=cv2.warpAffine(im,np.float32([[1,0,20],[0,1,10]]),(w,h));cv2.imwrite(str(DEST/'fruits-shift.png'),ref);add('fruits-shift.png','水果平移参考 · 配准与匹配',source='OpenCV fruits 派生')
    cv2.imwrite(str(DEST/'template.png'),im[h//3:h//3+80,w//3:w//3+100]);add('template.png','水果局部模板',role='template',source='OpenCV fruits 派生')
points=np.random.default_rng(42).normal(0,.5,(4000,3));points[:3000,2]*=.03;np.savetxt(DEST/'plane.xyz',points,fmt='%.6f');add('plane.xyz','平面与离群点 · 合成点云',kind='pointcloud',source='本项目程序生成',license='CC0')
try:
    import subprocess
    raw=DEST/'vtest.avi';target=DEST/'pedestrians.mp4'
    if not target.exists():
        with urllib.request.urlopen('https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/vtest.avi',timeout=90) as response:raw.write_bytes(response.read())
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-t','5','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True);raw.unlink()
    add('pedestrians.mp4','行人运动 · 真实视频 5 秒',kind='video',source='https://github.com/opencv/opencv/blob/4.x/samples/data/vtest.avi',license='OpenCV sample / original source PETS',width=768,height=576,duration=5,fps=10)
except Exception as exc:print('video',exc)
(DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(f'Prepared {len(manifest)} examples')
