import { imageRecipe as add, scriptRecipe, referenceImage, featureMatching } from './pythonShared'

for (const id of ['difference', 'color_check', 'assembly', 'defects']) {
  const extras: Record<string, string> = {
    difference: '# 绝对差同时保留“变亮”和“变暗”的差异。',
    defects: '# reference 是局部平滑背景；残差候选不等于已确认的缺陷。',
    color_check: `# 用浮点 Lab 计算 ΔE76，不能直接使用 8 位编码算真实色差。
a = cv2.cvtColor(image.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
b = cv2.cvtColor(reference.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
delta = np.linalg.norm(a - b, axis=2)
print("平均 ΔE76:", float(delta.mean()))
np.save("deltaE76.npy", delta)`,
    assembly: `regions = params["regions"] or [params.get("roi", [0, 0, w, h])]
checks = []
for x, y, rw, rh in regions:
    x, y, rw, rh = map(int, (x, y, rw, rh))
    if min(x, y) < 0 or min(rw, rh) <= 0 or x+rw > w or y+rh > h:
        raise ValueError("检测区域超出图片")
    value = float(score[y:y+rh, x:x+rw].mean())
    checks.append({"roi": [x,y,rw,rh], "difference": value, "pass": value <= params["sensitivity"]})
print("各区域:", checks, "整体通过:", all(c["pass"] for c in checks))`,
  }
  add(id, `${id === 'defects' ? 'reference = cv2.GaussianBlur(image, (0, 0), 7)' : referenceImage}
diff = cv2.absdiff(image, reference)
score = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
mask = score > params["sensitivity"]
output[mask] = (0.5 * output[mask] + 0.5 * np.array([0, 0, 255])).astype(np.uint8)
print("超阈值比例:", float(mask.mean()), "平均像素差:", float(diff.mean()))
cv2.imwrite("difference.png", diff)
${extras[id]}`)
}

add('calibrate', `# calibration/ 下需至少 5 张同相机、同分辨率、不同角度的棋盘格图。
cols, rows = int(params["cols"]), int(params["rows"])
object_points = np.zeros((rows * cols, 3), np.float32)
object_points[:, :2] = np.mgrid[:cols, :rows].T.reshape(-1, 2) * params["square_mm"]
world, pixels = [], []
for path in sorted(Path("calibration").glob("*")):
    sample = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if sample is None:
        continue
    if sample.shape != (h, w):
        raise ValueError("所有标定图应与主图同分辨率")
    found, corners = cv2.findChessboardCornersSB(sample, (cols, rows))
    if found:
        world.append(object_points)
        pixels.append(corners)
if len(pixels) < 5:
    raise ValueError("成功检测棋盘角点的图片少于 5 张")
error, camera, distortion, _, _ = cv2.calibrateCamera(world, pixels, (w, h), None, None)
output = cv2.undistort(image, camera, distortion)
print("重投影 RMS / px:", error, "内参:", camera, "畸变:", distortion)
np.savez("calibration.npz", camera=camera, distortion=distortion)`, 'from pathlib import Path')
add('undistort', `camera = np.asarray(params["camera"], dtype=float)
distortion = np.asarray(params["distortion"], dtype=float)
if camera.shape != (3, 3) or distortion.size not in (4, 5, 8, 12, 14):
    raise ValueError("内参或畸变参数格式错误")
# 参数应来自同一相机和对应分辨率的标定。
output = cv2.undistort(image, camera, distortion)`)
add('stereo', `${referenceImage}
disparities = int(np.ceil(params["disparities"] / 16)) * 16
block = int(params["block"]) | 1
if w <= disparities + block:
    raise ValueError("图像宽度必须大于视差搜索范围")
matcher = cv2.StereoSGBM_create(minDisparity=0, numDisparities=disparities, blockSize=block,
                              P1=8*block*block, P2=32*block*block, uniquenessRatio=10,
                              speckleWindowSize=50, speckleRange=2)
# 输入应为极线校正后的左右图；OpenCV 定点结果需除以 16。
disparity = matcher.compute(gray, cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)).astype(np.float32) / 16
valid = disparity > 0
np.save("disparity_px.npy", disparity)
print("有效视差比例:", float(valid.mean()))
if params["focal"] > 0 and params["baseline"] > 0:
    depth = np.full_like(disparity, np.nan)
    depth[valid] = params["focal"] * params["baseline"] / disparity[valid]
    np.save("depth_mm.npy", depth)
display = cv2.normalize(np.maximum(disparity, 0), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
output = cv2.applyColorMap(display, cv2.COLORMAP_TURBO)`)
add('stereo_rectify', `${referenceImage}
calibration = params["calibration"]
required = ["K1", "D1", "K2", "D2", "R", "T"]
if any(key not in calibration for key in required):
    raise ValueError("请先填写真实双目标定数据 K1,D1,K2,D2,R,T")
K1, D1, K2, D2, R, T = [np.asarray(calibration[key], dtype=float) for key in required]
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K1, D1, K2, D2, (w,h), R, T)
map1 = cv2.initUndistortRectifyMap(K1, D1, R1, P1, (w,h), cv2.CV_32FC1)
map2 = cv2.initUndistortRectifyMap(K2, D2, R2, P2, (w,h), cv2.CV_32FC1)
left = cv2.remap(image, *map1, cv2.INTER_LINEAR)
right = cv2.remap(reference, *map2, cv2.INTER_LINEAR)
output = np.hstack([left, right])
cv2.imwrite("left_rectified.png", left)
cv2.imwrite("right_rectified.png", right)
np.save("Q.npy", Q)`)
add('reconstruct', `${featureMatching}
K1, K2 = np.asarray(params["camera"], float), np.asarray(params["camera_reference"], float)
points1 = cv2.undistortPoints(src[:,None], K1, None)[:,0]
points2 = cv2.undistortPoints(dst[:,None], K2, None)[:,0]
E, mask = cv2.findEssentialMat(points1, points2, np.eye(3), method=cv2.RANSAC,
                              threshold=1 / max(K1[0,0], K2[0,0]))
if E is None:
    raise ValueError("无法估计本质矩阵")
count, R, T, mask = cv2.recoverPose(E[:3], points1, points2, np.eye(3), mask=mask)
if count < 8:
    raise ValueError("正深度对应点不足；检查视差和场景退化")
valid = mask.ravel() > 0
homogeneous = cv2.triangulatePoints(np.hstack([np.eye(3), np.zeros((3,1))]),
                                  np.hstack([R, T]), points1[valid].T, points2[valid].T)
xyz = (homogeneous[:3] / homogeneous[3]).T
xyz = xyz[np.isfinite(xyz).all(1) & (xyz[:,2] > 0)]
np.savetxt("points.xyz", xyz)
print("相对平移:", T.ravel(), "点数:", len(xyz), "注意：没有毫米尺度")`)

scriptRecipe('pointcloud', `import numpy as np
from scipy.spatial import cKDTree

params = {{params}}
# 示例采用 XYZ 文本，每行三个坐标；CSV 可先将逗号转换为空格。
xyz = np.loadtxt("input.xyz", usecols=(0, 1, 2), ndmin=2)
if not len(xyz) or not np.isfinite(xyz).all():
    raise ValueError("点云需包含有限的三维坐标")
if params["voxel"] > 0:
    _, index = np.unique(np.floor(xyz / params["voxel"]), axis=0, return_index=True)
    xyz = xyz[index]

if params["operation"] == "plane":
    if len(xyz) < 3:
        raise ValueError("平面拟合至少需要 3 点")
    best, plane = np.zeros(len(xyz), bool), None
    rng = np.random.default_rng(42)
    for _ in range(100):
        a, b, c = xyz[rng.choice(len(xyz), 3, replace=False)]
        normal = np.cross(b-a, c-a)
        length = np.linalg.norm(normal)
        if length < 1e-9:
            continue
        normal /= length
        offset = -normal @ a
        inliers = np.abs(xyz @ normal + offset) < params["distance"]
        if inliers.sum() > best.sum():
            best, plane = inliers, [*normal.tolist(), float(offset)]
    print("平面 ax+by+cz+d=0:", plane, "内点数:", int(best.sum()))
elif params["operation"] == "register":
    target = np.loadtxt("reference.xyz", usecols=(0,1,2), ndmin=2)
    tree = cKDTree(target)
    transform = np.eye(4)
    for _ in range(30):
        distances, indices = tree.query(xyz)
        keep = distances <= np.quantile(distances, 0.8)
        a, b = xyz[keep], target[indices[keep]]
        if len(a) < 3:
            raise ValueError("有效对应点不足")
        ac, bc = a.mean(0), b.mean(0)
        u, _, vt = np.linalg.svd((a-ac).T @ (b-bc))
        R = vt.T @ u.T
        if np.linalg.det(R) < 0:
            vt[-1] *= -1
            R = vt.T @ u.T
        t = bc - R @ ac
        xyz = xyz @ R.T + t
        step = np.eye(4)
        step[:3,:3], step[:3,3] = R, t
        transform = step @ transform
    print("变换矩阵:", transform, "RMSE:", np.sqrt(np.mean(tree.query(xyz)[0] ** 2)))
else:
    print("点数:", len(xyz), "坐标范围:", xyz.min(0), xyz.max(0))
np.savetxt("result.xyz", xyz)
`, 'numpy scipy', '准备 input.xyz；配准还需 reference.xyz 和近似初始对齐。结果单位沿用输入，可用点云软件打开 result.xyz。')

scriptRecipe('eval_classification', `import numpy as np

params = {{params}}
annotations = params["annotations"]
# 默认演示数据；有真实标注时使用当前输入的数组。
truth = annotations.get("truth", [0, 1, 1, 2])
prediction = annotations.get("prediction", [0, 0, 1, 2])
if not truth or len(truth) != len(prediction):
    raise ValueError("真值和预测必须非空、等长并逐项对应")
classes = sorted(set(map(str, truth + prediction)))
index = {label: i for i, label in enumerate(classes)}
matrix = np.zeros((len(classes), len(classes)), int)
for actual, predicted in zip(truth, prediction):
    matrix[index[str(actual)], index[str(predicted)]] += 1
tp = np.diag(matrix)
precision = np.divide(tp, matrix.sum(0), out=np.zeros(len(classes), float), where=matrix.sum(0)>0)
recall = np.divide(tp, matrix.sum(1), out=np.zeros(len(classes), float), where=matrix.sum(1)>0)
f1 = np.divide(2*precision*recall, precision+recall, out=np.zeros(len(classes), float), where=precision+recall>0)
print("类别:", classes, "混淆矩阵（行真值、列预测）:", matrix)
print("accuracy:", tp.sum()/matrix.sum(), "precision:", precision, "recall:", recall, "macro_F1:", f1.mean())
`, 'numpy', '不需要图片；用独立验证集的真实标签和预测标签替换演示数组。未填写时只演示指标计算，不表示平台准确率。')

scriptRecipe('eval_detection', `import numpy as np

params = {{params}}
annotations = params["annotations"]
truth = annotations.get("truth", [{"image_id":"a", "class_id":0, "box":[10,10,50,50]}])
prediction = annotations.get("prediction", [{"image_id":"a", "class_id":0, "box":[12,10,51,49], "score":0.9}])
if not truth:
    raise ValueError("至少需要一个真实标注目标")

def iou(a, b):
    intersection = max(0, min(a[2],b[2])-max(a[0],b[0])) * max(0, min(a[3],b[3])-max(a[1],b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / max(union, 1e-9)

scores = {}
for threshold in np.arange(0.5, 1, 0.05):
    class_ap = []
    for cls in set(str(item["class_id"]) for item in truth):
        gt = [item for item in truth if str(item["class_id"]) == cls]
        pred = sorted((item for item in prediction if str(item["class_id"]) == cls), key=lambda item: -item["score"])
        matched, hits = set(), []
        for item in pred:
            candidates = [(iou(item["box"], target["box"]), i) for i, target in enumerate(gt)
                          if i not in matched and item["image_id"] == target["image_id"]]
            overlap, index = max(candidates, default=(0, -1))
            hit = overlap >= threshold
            hits.append(int(hit))
            if hit:
                matched.add(index)
        cumulative = np.cumsum(hits)
        recall = cumulative / len(gt)
        precision = cumulative / np.arange(1, len(hits)+1)
        class_ap.append(np.mean([precision[recall >= r].max() if np.any(recall >= r) else 0
                                 for r in np.linspace(0, 1, 101)]))
    scores[f"{threshold:.2f}"] = float(np.mean(class_ap))
print("AP50:", scores["0.50"], "mAP50_95:", np.mean(list(scores.values())), "各门槛:", scores)
# 与平台一样，不包含 COCO crowd / area / maxDets 子集规则。
`, 'numpy', 'box 是 [x1,y1,x2,y2]。默认只有一对演示框；正式评估需填写真实数据，预测还必须包含 score。')

add('eval_segmentation', `# input.jpg 是预测掩膜；truth.png 是同尺寸真值，不是普通自然图片。
truth = cv2.imread("truth.png", cv2.IMREAD_GRAYSCALE)
if truth is None or truth.shape != gray.shape:
    raise ValueError("需要与预测掩膜同尺寸的 truth.png")
if params["mode"] == "multiclass":
    valid = truth != params["ignore_label"]
    if not valid.any():
        raise ValueError("全部真值像素都被忽略")
    classes = np.union1d(truth[valid], gray[valid])
else:
    valid = np.ones_like(truth, dtype=bool)
    truth, gray = truth > 127, gray > 127
    classes = [True]  # 二值指标只评价前景
rows = []
for cls in classes:
    a, b = (truth == cls) & valid, (gray == cls) & valid
    intersection, union = int((a & b).sum()), int((a | b).sum())
    total = int(a.sum() + b.sum())
    rows.append({"class": int(cls), "IoU": intersection/union if union else 1,
                 "Dice": 2*intersection/total if total else 1})
print(rows)
print("平均 IoU:", np.mean([r["IoU"] for r in rows]), "pixel_accuracy:", float((truth[valid] == gray[valid]).mean()))
# 白色显示预测与真值不一致的位置；忽略区不计入。
output = np.uint8((truth != gray) & valid) * 255`)
