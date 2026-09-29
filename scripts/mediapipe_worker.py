"""独立进程隔离 MediaPipe 与主环境 NumPy/OpenCV 版本冲突。"""
import json
import sys
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

kind,model,image,output=sys.argv[1:]
base=python.BaseOptions(model_asset_path=model)
if kind=='face_landmarker':detector=vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=base,num_faces=5))
else:detector=vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(base_options=base,num_hands=4))
with detector:
    result=detector.detect(mp.Image.create_from_file(image));landmarks=result.face_landmarks if kind=='face_landmarker' else result.hand_landmarks
    data={'landmarks':[[{'x':p.x,'y':p.y,'z':p.z} for p in entity] for entity in landmarks]}
    with open(output,'w') as f:json.dump(data,f)
