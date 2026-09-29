"""统一像素约定：输入/底图 BGR uint8，独立图层 BGRA，坐标均为原图。"""
from dataclasses import dataclass, field
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps
from ..config import MAX_PIXELS

@dataclass
class Result:
    image: np.ndarray
    data: dict = field(default_factory=dict)
    layers: dict[str, np.ndarray] = field(default_factory=dict)
    arrays: dict[str, np.ndarray] = field(default_factory=dict)

def read_image(path):
    with Image.open(path) as src:
        if src.width * src.height > MAX_PIXELS:
            raise ValueError('图片超过 2400 万像素上限，请缩小后上传')
        rgb = np.array(ImageOps.exif_transpose(src).convert('RGB'))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

def gray(im):
    return im if im.ndim == 2 else cv2.cvtColor(im[:, :, :3], cv2.COLOR_BGR2GRAY)

def color(im):
    return cv2.cvtColor(im, cv2.COLOR_GRAY2BGR) if im.ndim == 2 else im[:, :, :3]

def binary(im, threshold=127):
    return cv2.threshold(gray(im), threshold, 255, cv2.THRESH_BINARY)[1]

def odd(n):
    return int(n) | 1

def normalize(im):
    return cv2.normalize(im, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

def require_image(extra, key, im=None):
    paths = extra.get(key, [])
    if not paths:
        raise ValueError(f'请上传专用输入：{key}')
    result = read_image(paths[0])
    if im is not None and result.shape != im.shape:
        raise ValueError(f'{key} 与原图尺寸必须一致：{result.shape} ≠ {im.shape}')
    return result

def roi_of(params, im, required=True):
    h,w=im.shape[:2]
    roi = params.get('roi')
    if not roi:
        if required: raise ValueError('请先在原图绘制矩形 ROI')
        return 0,0,w,h
    if len(roi)!=4: raise ValueError('ROI 必须是 [x,y,w,h]')
    x,y,rw,rh=map(int,roi)
    x,y=max(0,x),max(0,y)
    rw,rh=min(rw,w-x),min(rh,h-y)
    if rw<2 or rh<2:raise ValueError('ROI 宽高至少为 2 像素且必须在图像内')
    return x,y,rw,rh

def blank_layer(im):
    return np.zeros((*im.shape[:2],4),np.uint8)

def mask_layer(mask, bgr=(80,210,50), alpha=130):
    layer=np.zeros((*mask.shape[:2],4),np.uint8)
    layer[mask>0]=(*bgr,alpha)
    return layer

def contours(im, threshold=127, min_area=0):
    mask=binary(im,threshold)
    cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    return mask,sorted([q for q in cs if cv2.contourArea(q)>=min_area],key=cv2.contourArea,reverse=True)

def match_pair(im, ref, ratio=.75):
    orb=cv2.ORB_create(2500)
    k1,d1=orb.detectAndCompute(gray(im),None)
    k2,d2=orb.detectAndCompute(gray(ref),None)
    if d1 is None or d2 is None:raise ValueError('纹理不足，无法提取描述子')
    pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1,d2,k=2)
    good=[a for pair in pairs if len(pair)==2 for a,b in [pair] if a.distance<ratio*b.distance]
    if len(good)<4:raise ValueError(f'有效匹配只有 {len(good)} 个，至少需要 4 个')
    p1=np.float32([k1[m.queryIdx].pt for m in good])
    p2=np.float32([k2[m.trainIdx].pt for m in good])
    H,inliers=cv2.findHomography(p1,p2,cv2.RANSAC,4)
    if H is None or int(inliers.sum())<4:raise ValueError('RANSAC 无法建立可靠的平面映射')
    return k1,k2,good,H,inliers,p1,p2
