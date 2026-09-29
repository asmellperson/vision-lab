import { scriptRecipe } from './pythonShared'

const indent = (text: string, spaces: number) => text.split('\n').map(line => ' '.repeat(spaces) + line).join('\n')
function videoRecipe(id: string, setup: string, body: string, imports = '', dependencies = 'opencv-contrib-python numpy', note = '') {
  scriptRecipe(id, `import cv2
import numpy as np
${imports}
params = {{params}}
capture = cv2.VideoCapture("input.mp4")
ok, first = capture.read()
if not ok:
    capture.release()
    raise ValueError("无法读取 input.mp4")
h, w = first.shape[:2]
fps = capture.get(cv2.CAP_PROP_FPS) or 25
capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
writer = cv2.VideoWriter("result.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w,h))
if not writer.isOpened():
    capture.release()
    raise RuntimeError("无法创建输出视频")
previous, index = None, 0
try:
${indent(setup, 4)}
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        output = frame.copy()
        time_seconds = index / fps
${indent(body, 8)}
        if output.ndim == 2:
            output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)
        writer.write(output)
        previous = gray
        index += 1
finally:
    capture.release()
    writer.release()
`, dependencies, '用本地 input.mp4 演示连续逐帧处理，输出不含音轨的 result.mp4。' + note)
}

videoRecipe('frame_diff', 'pass', `# 第一帧没有前帧可比，显示为黑色。
output = cv2.absdiff(gray, previous) if previous is not None else np.zeros_like(gray)`)
videoRecipe('mog2', 'background = cv2.createBackgroundSubtractorMOG2(detectShadows=True)', `# 模型持续更新：0 背景、127 阴影、255 前景。
output = background.apply(frame)`)
videoRecipe('flow_sparse', 'points = None', `if previous is not None and points is not None and len(points):
    next_points, status, error = cv2.calcOpticalFlowPyrLK(previous, gray, points, None)
    if next_points is not None:
        good = status.ravel() == 1
        for old, new in zip(points[good,0], next_points[good,0]):
            cv2.arrowedLine(output, tuple(old.astype(int)), tuple(new.astype(int)), (0,255,0), 2)
        points = next_points[good].reshape(-1,1,2)
        print(time_seconds, "跟踪点数:", len(points))
if points is None or len(points) < 30:
    points = cv2.goodFeaturesToTrack(gray, 200, 0.01, 8)`)
videoRecipe('flow_dense', 'pass', `if previous is not None:
    flow = cv2.calcOpticalFlowFarneback(previous, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    magnitude, angle = cv2.cartToPolar(flow[:,:,0], flow[:,:,1])
    hsv = np.zeros_like(frame)
    hsv[:,:,0] = angle * 90 / np.pi
    hsv[:,:,1] = 255
    hsv[:,:,2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
    output = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    print(time_seconds, "平均每帧位移 px:", float(magnitude.mean()))`)
videoRecipe('single_track', `# 未设置 ROI 时用中央区域演示；应替换为真实目标框。
roi = tuple(map(int, params.get("roi", [w//4,h//4,w//2,h//2])))
tracker = cv2.TrackerCSRT_create()
tracker.init(first, roi)`, `success, box = (True, roi) if index == 0 else tracker.update(frame)
if success:
    x, y, bw, bh = map(int, box)
    cv2.rectangle(output, (x,y), (x+bw,y+bh), (0,255,0), 2)
print(time_seconds, "tracked:", success, "box:", box if success else None)`)

const trackingSetup = `weights = Path("models/yolov8n/yolov8n.pt")
if not weights.is_file():
    raise FileNotFoundError(weights)
model = YOLO(str(weights))
tracks, next_id = {}, 1

def iou(a, b):
    intersection = max(0,min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / max(union, 1e-9)`
const trackingFrame = `result = model.predict(frame, conf=0.3, device="cpu", verbose=False)[0]
detections = sorted([{"box": box.xyxy[0].tolist(), "class": int(box.cls[0]), "confidence": float(box.conf[0])}
                     for box in result.boxes], key=lambda item: -item["confidence"])
used, active = set(), []
for detection in detections:
    candidates = [(iou(detection["box"], track["box"]), tid) for tid, track in tracks.items()
                  if tid not in used and detection["class"] == track["class"] and index-track["last"] <= 15]
    overlap, tid = max(candidates, default=(0,0))
    if overlap < 0.2:
        tid, next_id = next_id, next_id+1
        tracks[tid] = {"history": deque(maxlen=90)}
    track = tracks[tid]
    track.update(detection, last=index, id=tid)
    x1,y1,x2,y2 = detection["box"]
    track["history"].append([(x1+x2)/2, (y1+y2)/2])
    used.add(tid)
    active.append(track)
    cv2.rectangle(output, (int(x1),int(y1)), (int(x2),int(y2)), (0,255,0), 2)
    cv2.putText(output, f"#{tid}", (int(x1),max(16,int(y1))), 0, 0.6, (0,255,0), 1)
    cv2.polylines(output, [np.int32(track["history"])], False, (0,180,255), 2)
tracks = {tid: track for tid, track in tracks.items() if index-track["last"] <= 30}`
const trackingImports = 'from pathlib import Path\nfrom collections import deque\nfrom ultralytics import YOLO'
videoRecipe('multi_track', trackingSetup, `${trackingFrame}
print(time_seconds, [{"id": t["id"], "box": t["box"]} for t in active])`, trackingImports, 'ultralytics numpy opencv-contrib-python', ' 在项目根目录运行；示例与平台一样使用简化 IoU 关联，不冒充 ByteTrack。')

const eventsSetup = `${trackingSetup}
state, sequences = {}, {}
roi = params.get("roi", [0,0,w,h])
line = params["line_x"] * w
unique_crossings = set()`
const eventFrame = `${trackingFrame}
present = {track["id"] for track in active}
for tid in list(state):
    if tid not in present:
        state[tid].update(inside=False, since=None, dwelled=False)
    if time_seconds-state[tid].get("last", time_seconds) > 60:
        state.pop(tid, None)
        sequences.pop(tid, None)
for track in active:
    tid, (cx,cy) = track["id"], track["history"][-1]
    rx,ry,rw,rh = roi
    inside = rx <= cx <= rx+rw and ry <= cy <= ry+rh
    old = state.get(tid, {"inside":False, "cx":cx, "since":None, "dwelled":False})
    kinds = []
    if inside and not old["inside"]:
        kinds.append("enter")
        old.update(since=time_seconds, dwelled=False)
    if not inside and old["inside"]:
        kinds.append("exit")
        old["since"] = None
    if (old["cx"]-line)*(cx-line) < 0:
        kinds.append("cross")
        unique_crossings.add(tid)
    if inside and old["since"] is not None and not old["dwelled"] and time_seconds-old["since"] >= params["dwell"]:
        kinds.append("dwell")
        old["dwelled"] = True
    for kind in kinds:
        print({"kind":kind, "time":time_seconds, "track_id":tid, "center":[cx,cy]})
        SEQUENCE_HOOK
    state[tid] = {**old, "inside":inside, "cx":cx, "last":time_seconds}
rx,ry,rw,rh = map(int, roi)
cv2.rectangle(output, (rx,ry), (rx+rw,ry+rh), (255,180,0), 2)
cv2.line(output, (int(line),0), (int(line),h), (0,255,255), 2)`
videoRecipe('events', eventsSetup, eventFrame.replace('SEQUENCE_HOOK', 'pass'), trackingImports, 'ultralytics numpy opencv-contrib-python', ' 进入、离开、越线和停留事件打印在终端；区域和线使用当前参数。')
const sequence = `order = params["event_order"]
if not order or any(item not in ["enter","cross","dwell","exit"] for item in order):
    raise ValueError("事件序列必须非空且使用支持的事件名称")
sequence = sequences.get(tid, {"index":0, "start":time_seconds, "evidence":[]})
if time_seconds-sequence["start"] > params["window"]:
    sequence = {"index":0, "start":time_seconds, "evidence":[]}
if kind == order[sequence["index"]]:
    if sequence["index"] == 0:
        sequence["start"] = time_seconds
    sequence["evidence"].append({"kind":kind, "time":time_seconds})
    sequence["index"] += 1
    if sequence["index"] == len(order):
        print({"kind":"sequence_complete", "track_id":tid, "evidence":sequence["evidence"]})
        sequence = {"index":0, "start":time_seconds, "evidence":[]}
sequences[tid] = sequence`
videoRecipe('sequence', eventsSetup, eventFrame.replace('        SEQUENCE_HOOK', indent(sequence, 8)), trackingImports, 'ultralytics numpy opencv-contrib-python', ' 使用同一 ID 的事件状态机；终端打印完成序列及证据。')

videoRecipe('action', `weights = R3D_18_Weights.DEFAULT
model = r3d_18(weights=None)
model.load_state_dict(torch.load("models/r3d/r3d.pth", map_location="cpu", weights_only=True))
model.eval()
clip = deque(maxlen=16)
latest = None`, `clip.append(cv2.cvtColor(cv2.resize(frame,(171,128)), cv2.COLOR_BGR2RGB))
if len(clip) == 16 and (index % 16 == 15 or latest is None):
    tensor = torch.from_numpy(np.stack(clip)).permute(0,3,1,2)  # T,C,H,W
    tensor = weights.transforms()(tensor).unsqueeze(0)       # B,C,T,H,W
    with torch.inference_mode():
        probabilities = model(tensor).softmax(1)[0]
    values, classes = probabilities.topk(5)
    latest = [(weights.meta["categories"][int(cls)], float(score)) for cls,score in zip(classes,values)]
    print("片段:", (index-15)/fps, time_seconds, "top5:", latest)
if latest:
    cv2.putText(output, latest[0][0], (15,30), 0, 0.7, (0,255,0), 2)`, 'from collections import deque\nimport torch\nfrom torchvision.models.video import r3d_18, R3D_18_Weights', 'torch torchvision opencv-contrib-python numpy', ' 至少准备连续 16 帧；在项目根目录复用 models/r3d 权重。')

scriptRecipe('video_segment', `from pathlib import Path
import cv2
import numpy as np
from ultralytics.models.sam import SAM2VideoPredictor
from ultralytics.utils.ops import scale_masks

params = {{params}}
if not params.get("roi"):
    raise ValueError("请先填写首帧 ROI [x,y,宽,高]")
weights = Path("models/sam2/sam2_t.pt")
if not weights.is_file():
    raise FileNotFoundError(weights)
x,y,w,h = params["roi"]
predictor = SAM2VideoPredictor(overrides={"model":str(weights), "task":"segment", "mode":"predict",
                                         "imgsz":512, "device":"cpu", "verbose":False, "save":False})
directory = Path("video_masks")
directory.mkdir(exist_ok=True)
stream = predictor(source="input.mp4", stream=True, bboxes=[x,y,x+w,y+h])
try:
    for index, result in enumerate(stream):
        height, width = result.orig_shape
        labels = np.zeros((height,width), np.uint16)
        if result.masks is not None:
            masks = result.masks.data
            if tuple(masks.shape[-2:]) != (height,width):
                masks = scale_masks(masks[None].float(), (height,width))[0]
            for instance, mask in enumerate(masks):
                labels[mask.cpu().numpy() > 0.5] = instance+1
        cv2.imwrite(str(directory / f"{index:06d}.png"), labels)
        if index >= 149:
            break  # 教学示例最多 150 帧，控制记忆开销
finally:
    stream.close()
`, 'ultralytics numpy opencv-contrib-python', '在项目根目录运行，准备短视频 input.mp4 和首帧 ROI；输出逐帧实例编号 PNG，0 为背景。')
