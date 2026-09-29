import { scriptRecipe as add } from './pythonShared'

const localNote = '在项目根目录运行以复用 models/ 中的本地权重；把 input.jpg 换成本地图片。缺少权重时先在模型管理中准备。'
const resnet = `import cv2
import numpy as np
import torch
from PIL import Image
from torchvision.models import resnet18, ResNet18_Weights

torch.set_num_threads(4)
params = {{params}}
weights = ResNet18_Weights.DEFAULT
model = resnet18(weights=None)
model.load_state_dict(torch.load("models/resnet18/resnet18.pth", map_location="cpu", weights_only=True))
model.eval()
image = Image.open("input.jpg").convert("RGB")`
add('classify', `${resnet}
x = weights.transforms()(image).unsqueeze(0)
with torch.inference_mode():
    probabilities = model(x).softmax(dim=1)[0]
values, indices = probabilities.topk(5)
for value, index in zip(values, indices):
    print(weights.meta["categories"][int(index)], float(value))
`, 'torch torchvision pillow opencv-python numpy', localNote)
const directTensor = `# 热图和特征图使用直接缩放，避免中心裁剪后的坐标错位。
rgb = np.asarray(image.resize((224, 224))).astype(np.float32) / 255
x = torch.from_numpy(rgb).permute(2, 0, 1)
x = ((x - torch.tensor([0.485,0.456,0.406])[:,None,None]) /
     torch.tensor([0.229,0.224,0.225])[:,None,None]).unsqueeze(0)
activations = []
handle = model.layer4.register_forward_hook(lambda module, inputs, output: activations.append(output))`
add('gradcam', `${resnet}
${directTensor}
try:
    logits = model(x)  # 这里需要梯度，不使用 inference_mode
    target = int(logits.argmax(1))
    features = activations[0]
    gradients = torch.autograd.grad(logits[0, target], features)[0]
    channel_weights = gradients.mean((2, 3), keepdim=True)
    cam = (channel_weights * features).sum(1).relu()[0].detach().numpy()
    cam = cv2.resize(cam, image.size)
    display = cv2.normalize(cam, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heat = cv2.applyColorMap(display, cv2.COLORMAP_TURBO)
    original = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    cv2.imwrite("gradcam.png", cv2.addWeighted(original, 0.45, heat, 0.55, 0))
    print("解释的类别:", weights.meta["categories"][target])
finally:
    handle.remove()
`, 'torch torchvision opencv-contrib-python numpy pillow', localNote)
add('feature_maps', `${resnet}
${directTensor}
try:
    with torch.inference_mode():
        model(x)
    features = activations[0][0].numpy()
    np.save("layer4_features.npy", features)
    tiles = []
    for channel in features[:16]:
        normalized = cv2.normalize(channel, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        tiles.append(cv2.applyColorMap(cv2.resize(normalized, (128,128)), cv2.COLORMAP_VIRIDIS))
    cv2.imwrite("feature_maps.png", np.vstack([np.hstack(tiles[i:i+4]) for i in range(0,16,4)]))
    print("全部通道形状:", features.shape)
finally:
    handle.remove()
`, 'torch torchvision opencv-contrib-python numpy pillow', localNote)
add('benchmark', `${resnet}
import time
import onnxruntime as ort

x = weights.transforms()(image).unsqueeze(0)
with torch.inference_mode():
    model(x)  # 预热
    times = []
    for _ in range(int(params["repeats"])):
        start = time.perf_counter()
        pytorch_output = model(x)
        times.append((time.perf_counter() - start) * 1000)
print("PyTorch CPU 中位毫秒:", float(np.median(times)))
torch.onnx.export(model, x, "benchmark.onnx", input_names=["image"], output_names=["logits"],
                  opset_version=17, dynamo=False)
options = ort.SessionOptions()
options.intra_op_num_threads = 4
session = ort.InferenceSession("benchmark.onnx", sess_options=options, providers=["CPUExecutionProvider"])
feed = {"image": x.numpy()}
session.run(None, feed)
times = []
for _ in range(int(params["repeats"])):
    start = time.perf_counter()
    onnx_output = session.run(None, feed)[0]
    times.append((time.perf_counter() - start) * 1000)
print("ONNX CPU 中位毫秒:", float(np.median(times)))
print("最大绝对误差:", float(np.abs(onnx_output - pytorch_output.numpy()).max()))
# 本例固定 CPU 与 4 线程；平台若使用 GPU，不应直接比较两次耗时。
`, 'torch torchvision pillow numpy opencv-contrib-python onnx onnxruntime', localNote)

const yoloTasks: [string, string, string][] = [
  ['detect', 'yolov8n', `for box in result.boxes:
    print(result.names[int(box.cls[0])], float(box.conf[0]), box.xyxy[0].tolist())`],
  ['obb', 'yolov8n-obb', `if result.obb is not None:
    for corners, score, cls in zip(result.obb.xyxyxyxy, result.obb.conf, result.obb.cls):
        print(result.names[int(cls)], float(score), corners.tolist())`],
  ['instance', 'yolov8n-seg', `from ultralytics.utils.ops import scale_masks
if result.masks is not None:
    height, width = result.orig_shape
    masks = result.masks.data
    if tuple(masks.shape[-2:]) != (height, width):
        masks = scale_masks(masks[None].float(), (height, width))[0]
    np.save("instance_masks.npy", masks.cpu().numpy() > 0.5)
    print("实例掩膜数:", len(masks))`],
  ['pose', 'yolov8n-pose', `if result.keypoints is not None:
    print("原图关键点坐标:", result.keypoints.xy.tolist())
    print("关键点置信度:", result.keypoints.conf.tolist())`],
]
for (const [id, model, body] of yoloTasks) add(id, `from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO

params = {{params}}
model_id = params.get("model_id", "${model}")
weights = Path("models") / model_id / (model_id + ".pt")
if not weights.is_file():
    raise FileNotFoundError(f"请先准备本地权重：{weights}")
model = YOLO(str(weights))
result = model.predict(source="input.jpg", conf=params["confidence"], device="cpu", verbose=False)[0]
${body}
cv2.imwrite("result.png", result.plot())
`, 'ultralytics opencv-contrib-python numpy', localNote)

add('sam', `from pathlib import Path
import cv2
import numpy as np
from ultralytics import SAM
from ultralytics.utils.ops import scale_masks

params = {{params}}
weights = Path("models/sam2/sam2_t.pt")
if not weights.is_file():
    raise FileNotFoundError(weights)
model = SAM(str(weights))
prompt = {}
if params.get("points"):
    prompt["points"] = [[point[:2] for point in params["points"]]]
    prompt["labels"] = [[int(point[2]) for point in params["points"]]]
elif params.get("roi"):
    x, y, w, h = params["roi"]
    prompt["bboxes"] = [x, y, x+w, y+h]
else:
    raise ValueError("请先在页面选点或框选，或在 params 中填写 points / roi")
result = model.predict(source="input.jpg", device="cpu", verbose=False, **prompt)[0]
if result.masks is not None:
    height, width = result.orig_shape
    masks = result.masks.data
    if tuple(masks.shape[-2:]) != (height, width):
        masks = scale_masks(masks[None].float(), (height,width))[0]
    np.save("masks.npy", masks.cpu().numpy() > 0.5)
cv2.imwrite("result.png", result.plot())
`, 'ultralytics opencv-contrib-python numpy', localNote + ' 点和框坐标均使用原图像素。')
add('layout', `from pathlib import Path
import cv2
from doclayout_yolo import YOLOv10

params = {{params}}
path = Path("models/layout/doclayout.pt")
if not path.is_file():
    raise FileNotFoundError(path)
model = YOLOv10(str(path))
result = model.predict("input.jpg", imgsz=1024, conf=params["confidence"], device="cpu", verbose=False)[0]
for box in result.boxes:
    print(result.names[int(box.cls[0])], box.xyxy[0].tolist(), float(box.conf[0]))
cv2.imwrite("layout.png", result.plot())
`, 'doclayout-yolo opencv-contrib-python', localNote)
add('semantic', `import torch
import numpy as np
from PIL import Image
from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large, DeepLabV3_MobileNet_V3_Large_Weights

weights = DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT
model = deeplabv3_mobilenet_v3_large(weights=None, weights_backbone=None, aux_loss=True)
model.load_state_dict(torch.load("models/deeplab/deeplab.pth", map_location="cpu", weights_only=True))
model.eval()
image = Image.open("input.jpg").convert("RGB")
x = weights.transforms()(image).unsqueeze(0)
with torch.inference_mode():
    logits = model(x)["out"]
    logits = torch.nn.functional.interpolate(logits, size=(image.height,image.width), mode="bilinear", align_corners=False)
    labels = logits.argmax(1)[0].numpy().astype(np.uint8)
Image.fromarray(labels).save("class_labels.png")  # 保存类别编号，而不是随意上色的图
for cls in np.unique(labels):
    print(int(cls), weights.meta["categories"][int(cls)], "像素数:", int((labels == cls).sum()))
`, 'torch torchvision pillow numpy', localNote)

for (const [id, kind, field, count] of [
  ['face', 'Face', 'face', 'num_faces=5'], ['hand', 'Hand', 'hand', 'num_hands=4'],
]) add(id, `import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 与主平台的 NumPy 版本隔离：在 vision-lab-mediapipe 环境运行。
options = vision.${kind}LandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path="models/${field}_landmarker/${field}_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE, ${count})
image = mp.Image.create_from_file("input.jpg")
with vision.${kind}Landmarker.create_from_options(options) as detector:
    result = detector.detect(image)
    for entity in result.${field}_landmarks:
        print([{"x_px": point.x * image.width, "y_px": point.y * image.height,
                "z_relative": point.z} for point in entity])
`, 'mediapipe（使用 vision-lab-mediapipe 独立环境）', localNote + ' 本例用 MediaPipe 图片接口；z 是相对坐标。')
const ocr = `from pathlib import Path
from rapidocr_onnxruntime import RapidOCR

params = {{params}}
files = list(Path("models/rapidocr").rglob("*.onnx"))
def find_model(hint):
    matches = [path for path in files if hint in path.name]
    if not matches:
        raise FileNotFoundError(f"缺少 OCR {hint} 模型")
    return str(matches[0])
ocr = RapidOCR(det_model_path=find_model("det"), rec_model_path=find_model("rec"),
               cls_model_path=find_model("cls"), intra_op_num_threads=2, inter_op_num_threads=2)
lines, timing = ocr("input.jpg")`
add('ocr', `${ocr}
for polygon, text, score in lines or []:
    print("文字:", text, "置信度:", score, "位置:", polygon)
`, 'rapidocr-onnxruntime', localNote)
add('char_check', `${ocr}
import regex
pattern = regex.compile(params["pattern"])
for polygon, text, score in lines or []:
    try:
        valid = bool(pattern.fullmatch(text, timeout=0.05))
    except TimeoutError:
        valid = False
        print("正则匹配超时，请简化表达式")
    print({"text": text, "confidence": score, "valid": valid})
# 格式通过只说明符合规则；仍需核对 OCR 是否读对了实际文字。
`, 'rapidocr-onnxruntime regex', localNote)

function hfSetup(model: string, modelClass: string, processorClass: string, extra = '') {
  return `import torch
import numpy as np
import cv2
from PIL import Image
from transformers import ${modelClass}, ${processorClass}${extra ? ', AutoConfig' : ''}

torch.set_num_threads(4)
params = {{params}}
path = "models/${model}"
processor = ${processorClass}.from_pretrained(path, local_files_only=True)
${extra}
model = ${modelClass}.from_pretrained(path, local_files_only=True${extra ? ', config=config' : ''}).eval()
image = Image.open("input.jpg").convert("RGB")`
}
const clip = hfSetup('clip', 'CLIPModel', 'CLIPProcessor')
add('similarity', `${clip}
from pathlib import Path

paths = sorted(path for path in Path("gallery").glob("*") if path.suffix.lower() in (".jpg", ".jpeg", ".png"))
if not paths:
    raise ValueError("请将候选图片放入 gallery/ 文件夹")
with torch.inference_mode():
    query = model.get_image_features(**processor(images=image, return_tensors="pt"))
    gallery = []
    for path in paths:
        sample = Image.open(path).convert("RGB")
        gallery.append(model.get_image_features(**processor(images=sample, return_tensors="pt")))
    features = torch.cat(gallery)
    query = query / query.norm(dim=-1, keepdim=True)
    features = features / features.norm(dim=-1, keepdim=True)
    scores = (query @ features.T)[0].numpy()
for index in np.argsort(-scores):
    print(paths[index].name, float(scores[index]))
`, 'transformers torch pillow numpy opencv-contrib-python', localNote + ' 图库放入 gallery/。')
add('text_retrieval', `${clip}
from pathlib import Path

texts = [text.strip() for text in params["prompt"].split(",") if text.strip()]
if not texts:
    raise ValueError("请填写至少一个文本候选")
with torch.inference_mode():
    result = model(**processor(text=texts, images=image, return_tensors="pt", padding=True))
    scores = (result.image_embeds @ result.text_embeds.T)[0].numpy()
    for index in np.argsort(-scores):
        print("当前图像与文本:", texts[index], float(scores[index]))
    paths = sorted(path for path in Path("gallery").glob("*") if path.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if paths:
        features = []
        for path in paths:
            features.append(model.get_image_features(**processor(images=Image.open(path).convert("RGB"), return_tensors="pt")))
        features = torch.cat(features)
        features /= features.norm(dim=-1, keepdim=True)
        similarities = (result.text_embeds @ features.T).numpy()
        for text, scores in zip(texts, similarities):
            print("文本查图库:", text, [(paths[i].name, float(scores[i])) for i in np.argsort(-scores)])
`, 'transformers torch pillow numpy opencv-contrib-python', localNote + ' 多条提示用英文逗号分隔；可选图库放入 gallery/。')
add('grounding', `${hfSetup('owlvit', 'OwlViTForObjectDetection', 'AutoProcessor')}
texts = [text.strip() for text in params["prompt"].split(",") if text.strip()]
if not texts:
    raise ValueError("请填写检测类别")
inputs = processor(text=[texts], images=image, return_tensors="pt")
with torch.inference_mode():
    outputs = model(**inputs)
result = processor.post_process_object_detection(outputs, threshold=params["confidence"],
                                                 target_sizes=torch.tensor([[image.height,image.width]]))[0]
for box, score, label in zip(result["boxes"], result["scores"], result["labels"]):
    print(texts[int(label)], float(score), box.tolist())
`, 'transformers torch pillow numpy opencv-contrib-python', localNote)
for (const [id, directory, cls] of [['caption', 'blip', 'BlipForConditionalGeneration'], ['vqa', 'blip-vqa', 'BlipForQuestionAnswering']]) add(id, `${hfSetup(directory, cls, 'AutoProcessor')}
inputs = processor(images=image${id === 'vqa' ? ', text=params["prompt"]' : ''}, return_tensors="pt")
with torch.inference_mode():
    tokens = model.generate(**inputs, max_new_tokens=70)
print(processor.decode(tokens[0], skip_special_tokens=True))
# 生成文字需要与原图核对，不能替代测量、计数或 OCR。
`, 'transformers torch pillow numpy opencv-contrib-python', localNote)
add('depth', `${hfSetup('depth-anything', 'AutoModelForDepthEstimation', 'AutoImageProcessor')}
with torch.inference_mode():
    depth = model(**processor(images=image, return_tensors="pt")).predicted_depth
    depth = torch.nn.functional.interpolate(depth[:,None], size=(image.height,image.width), mode="bicubic", align_corners=False)[0,0].numpy()
np.save("relative_inverse_depth.npy", depth)
display = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
cv2.imwrite("relative_depth.png", cv2.applyColorMap(display, cv2.COLORMAP_TURBO))
print("这是相对逆深度，没有米或毫米尺度")
`, 'transformers torch pillow numpy opencv-contrib-python', localNote)
add('panoptic', `${hfSetup('detr-panoptic', 'DetrForSegmentation', 'AutoImageProcessor', 'config = AutoConfig.from_pretrained(path, local_files_only=True)\nconfig.use_pretrained_backbone = False')}
with torch.inference_mode():
    logits = model(**processor(images=image, return_tensors="pt"))
result = processor.post_process_panoptic_segmentation(logits, target_sizes=[(image.height,image.width)],
             label_ids_to_fuse={int(i) for i in model.config.id2label if int(i) >= 91})[0]
np.save("segment_ids.npy", result["segmentation"].numpy())
for segment in result["segments_info"]:
    print("区域 ID:", segment["id"], "类别:", model.config.id2label[segment["label_id"]], segment)
`, 'transformers torch pillow numpy opencv-contrib-python timm', localNote)
add('superres', `${hfSetup('edsr', 'AutoModelForImageToImage', 'AutoImageProcessor')}
# 本项目 edsr 目录实际配置 Swin2SR ×2；分块重叠平均控制内存。
h, w, scale = image.height, image.width, 2
accumulator = np.zeros((h*scale,w*scale,3), np.float32)
counts = np.zeros((h*scale,w*scale,1), np.float32)
with torch.inference_mode():
    for y in range(0, h, 112):
        for x in range(0, w, 112):
            tile = image.crop((x,y,min(x+128,w),min(y+128,h)))
            result = model(**processor(images=tile, return_tensors="pt")).reconstruction
            rgb = result[0].clamp(0,1).permute(1,2,0).numpy()
            th, tw = tile.height*scale, tile.width*scale
            accumulator[y*scale:y*scale+th,x*scale:x*scale+tw] += rgb[:th,:tw]
            counts[y*scale:y*scale+th,x*scale:x*scale+tw] += 1
output = np.uint8(np.clip(accumulator / np.maximum(counts,1) * 255, 0, 255))
Image.fromarray(output).save("superres_x2.png")
`, 'transformers torch pillow numpy opencv-contrib-python', localNote)
add('matting', `import cv2
import numpy as np
import onnxruntime as ort

params = {{params}}
image = cv2.imread("input.jpg")
if image is None:
    raise FileNotFoundError("input.jpg")
h, w = image.shape[:2]
session = ort.InferenceSession("models/rmbg/u2netp.onnx", providers=["CPUExecutionProvider"])
rgb = cv2.cvtColor(cv2.resize(image, (320,320)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
x = ((rgb-[0.485,0.456,0.406])/[0.229,0.224,0.225]).transpose(2,0,1)[None].astype(np.float32)
prediction = session.run(None, {session.get_inputs()[0].name: x})[0][0,0]
mask = cv2.normalize(prediction, None, 0, 1, cv2.NORM_MINMAX)
alpha = np.clip(cv2.resize(mask, (w,h)), 0, 1)
color = params["background"]
background = np.array([int(color[i:i+2],16) for i in (5,3,1)])  # RGB 文本转 BGR
output = np.uint8(image*alpha[:,:,None] + background*(1-alpha[:,:,None]))
cv2.imwrite("new_background.png", output)
cv2.imwrite("foreground.png", np.dstack([image, np.uint8(alpha*255)]))
`, 'onnxruntime numpy opencv-contrib-python', localNote)
for (const [id, directory] of [['denoise_dl', 'swin-denoise'], ['deblur', 'restormer']]) add(id, `from pathlib import Path
import importlib.util
import yaml
import torch
import cv2
import numpy as np

# ${id === 'denoise_dl' ? '真实相机去噪' : '运动去模糊'}：源码、配置和权重必须使用同一套。
path = Path("models/${directory}")
spec = importlib.util.spec_from_file_location("restormer_arch", path / "restormer_arch.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
options = yaml.safe_load((path / "config.yml").read_text())["network_g"]
options.pop("type", None)
model = module.Restormer(**options)
model.load_state_dict(torch.load(path / "weights.pth", map_location="cpu", weights_only=True)["params"])
model.eval()
image = cv2.imread("input.jpg")
if image is None:
    raise FileNotFoundError("input.jpg")
h, w = image.shape[:2]
accumulator, counts = np.zeros_like(image, np.float32), np.zeros((h,w,1), np.float32)
with torch.inference_mode():
    for y in range(0, h, 224):
        for x in range(0, w, 224):
            tile = image[y:y+256,x:x+256]
            th, tw = tile.shape[:2]
            tensor = torch.from_numpy(cv2.cvtColor(tile, cv2.COLOR_BGR2RGB).copy()).permute(2,0,1)[None].float()/255
            tensor = torch.nn.functional.pad(tensor, (0,(-tw)%8,0,(-th)%8), mode="replicate")
            restored = model(tensor)[0,:,:th,:tw].clamp(0,1).permute(1,2,0).numpy()[:,:,::-1]
            accumulator[y:y+th,x:x+tw] += restored*255
            counts[y:y+th,x:x+tw] += 1
cv2.imwrite("restored.png", np.uint8(accumulator / np.maximum(counts,1)))
`, 'torch einops pyyaml numpy opencv-contrib-python', localNote)

add('anomaly', `${resnet}
from pathlib import Path

def local_features(pil):
    rgb = np.asarray(pil.resize((224,224))).astype(np.float32) / 255
    x = torch.from_numpy(rgb).permute(2,0,1)
    x = ((x-torch.tensor([0.485,0.456,0.406])[:,None,None]) / torch.tensor([0.229,0.224,0.225])[:,None,None])[None]
    with torch.inference_mode():
        for layer in [model.conv1,model.bn1,model.relu,model.maxpool,model.layer1]:
            x = layer(x)
        a = model.layer2(x)
        b = torch.nn.functional.interpolate(model.layer3(a), size=a.shape[-2:], mode="bilinear", align_corners=False)
        features = torch.nn.functional.avg_pool2d(torch.cat([a,b], dim=1), 3, 1, 1)
    return features[0].permute(1,2,0).numpy()

# 正常样本放到 normal_samples/；也可加载此前保存的 features.npz。
if Path("features.npz").is_file():
    with np.load("features.npz", allow_pickle=False) as saved:
        bank = saved["features"]
else:
    paths = sorted(p for p in Path("normal_samples").glob("*") if p.suffix.lower() in (".jpg",".png",".jpeg"))
    if len(paths) < 2:
        raise ValueError("至少需要两张正常样本")
    features = np.concatenate([local_features(Image.open(p).convert("RGB")).reshape(-1,384) for p in paths])
    rng = np.random.default_rng(42)
    bank = features[rng.choice(len(features), min(6000,len(features)), replace=False)]
    np.savez_compressed("features.npz", features=bank)
if bank.ndim != 2 or bank.shape[1] != 384 or not len(bank):
    raise ValueError("参考库需为非空的 N×384 特征数组")
query = local_features(image)
distances = []
for chunk in torch.from_numpy(query.reshape(-1,384)).split(128):
    distances.append(torch.cdist(chunk, torch.from_numpy(bank)).min(1).values.numpy())
score = np.concatenate(distances).reshape(query.shape[:2])
score = cv2.GaussianBlur(cv2.resize(score, image.size), (0,0), 3)
np.save("anomaly_score.npy", score)
print("最大异常距离:", float(score.max()), "注意：不是概率")
heat = cv2.normalize(score, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
cv2.imwrite("anomaly_heatmap.png", cv2.applyColorMap(heat, cv2.COLORMAP_TURBO))
if params["score_threshold"] > 0:
    cv2.imwrite("anomaly_mask.png", np.uint8(score > params["score_threshold"]) * 255)
`, 'torch torchvision pillow opencv-contrib-python numpy', localNote + ' 正常样本需覆盖正常外观变化；代码使用随机子采样，不冒充完整 PatchCore 论文实现。')
