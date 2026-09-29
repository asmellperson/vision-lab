import { imageRecipe as add, referenceImage, contourSetup, featureMatching } from './pythonShared'

add('pixels', `# 图像数组使用 [行 y, 列 x]；OpenCV 默认 BGR 顺序。
x, y = map(int, params.get("points", [[params["x"], params["y"]]])[-1][:2])
if not (0 <= x < w and 0 <= y < h):
    raise ValueError("采样点超出原图")
print("RGB:", image[y, x, ::-1].tolist())
print("HSV:", cv2.cvtColor(image, cv2.COLOR_BGR2HSV)[y, x].tolist())
print("灰度:", int(gray[y, x]))
cv2.drawMarker(output, (x, y), (0, 255, 255))`)
add('gray', `# 将三个颜色分量加权合成单通道亮度图。
output = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
print("灰度图尺寸:", output.shape)`)
add('color rgb hsv lab ycrcb', `codes = {"RGB": cv2.COLOR_BGR2RGB, "HSV": cv2.COLOR_BGR2HSV,
         "Lab": cv2.COLOR_BGR2LAB, "YCrCb": cv2.COLOR_BGR2YCrCb}
encoded = cv2.cvtColor(image, codes[params["space"]])
# 每个通道单独显示为灰度图，避免把编码误当成 BGR 彩照。
output = np.hstack(cv2.split(encoded))
np.save("channels.npy", encoded)
print("各通道范围:", [(int(c.min()), int(c.max())) for c in cv2.split(encoded)])`)
add('channel', `# BGR 的索引分别为 0、1、2。
index = {"B": 0, "G": 1, "R": 2}[params["channel"]]
output = image[:, :, index]`)
add('merge', `gains = np.array([params["B"], params["G"], params["R"]])
# 先转换到浮点，计算后截断；不要直接在 uint8 上做可能溢出的乘法。
output = np.clip(image.astype(float) * gains, 0, 255).astype(np.uint8)`)
for (const [id, call, explanation] of [
  ['add', 'cv2.add(image, reference)', '饱和加法：180 + 100 得到 255。'],
  ['subtract', 'cv2.subtract(image, reference)', '饱和减法：负数截为 0；交换两图会改变结果。'],
  ['blend', 'cv2.addWeighted(image, params["alpha"], reference, 1 - params["alpha"], 0)', '两张图的权重之和为 1。'],
  ['bit_and', 'cv2.bitwise_and(image, reference)', '对于 0/255 掩膜，按位与相当于取交集。'],
  ['bit_or', 'cv2.bitwise_or(image, reference)', '对于 0/255 掩膜，按位或相当于取并集。'],
  ['bit_xor', 'cv2.bitwise_xor(image, reference)', '对于 0/255 掩膜，异或找出不一致的位置。'],
]) add(id, `${referenceImage}\n# ${explanation}\noutput = ${call}`)
add('bit_not', '# 对 8 位图像等价于 255 - image。\noutput = cv2.bitwise_not(image)')
add('histogram', `output = np.full((300, 512, 3), 20, np.uint8)
histograms = {}
for channel, name, color in [(0, "B", (255, 0, 0)), (1, "G", (0, 255, 0)), (2, "R", (0, 0, 255))]:
    hist = cv2.calcHist([image], [channel], None, [256], [0, 256]).ravel()
    histograms[name] = hist
    points = np.int32([[i * 2, 290 - count / max(hist.max(), 1) * 270]
                       for i, count in enumerate(hist)])
    cv2.polylines(output, [points], False, color, 2)
# 曲线独立缩放高度；精确计数保存在这里。
np.savez("histograms.npz", **histograms)`)
add('brightness', `# 不用 convertScaleAbs，避免负值被取绝对值后变亮。
output = np.clip(image.astype(float) * params["alpha"] + params["beta"], 0, 255).astype(np.uint8)`)
add('gamma', `table = np.clip(255 * (np.arange(256) / 255.0) ** params["gamma"], 0, 255).astype(np.uint8)
# γ < 1 提亮，γ > 1 压暗。
output = cv2.LUT(image, table)`)
add('equalize', `lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
# 只均衡亮度，避免对三个颜色通道独立均衡导致严重色偏。
lab[:, :, 0] = cv2.equalizeHist(lab[:, :, 0])
output = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)`)
add('clahe', `lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
clahe = cv2.createCLAHE(clipLimit=params["clip"],
                       tileGridSize=(int(params["grid"]), int(params["grid"])))
lab[:, :, 0] = clahe.apply(lab[:, :, 0])
output = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)`)
for (const [id, call, comment] of [
  ['mean', 'cv2.blur(image, (k, k))', '所有邻居等权平均。'],
  ['gaussian', 'cv2.GaussianBlur(image, (k, k), sigmaX=0)', 'sigmaX=0 时由核尺寸推导高斯尺度。'],
  ['median', 'cv2.medianBlur(image, k)', '用邻域的中位数替代中心值，常用于椒盐噪声。'],
  ['bilateral', 'cv2.bilateralFilter(image, k, params["sigma"], params["sigma"])', '同时限制空间距离和颜色差；两种 sigma 在此设为相同值。'],
]) add(id, `k = max(1, int(params["kernel"])) | 1  # 调整为奇数\n# ${comment}\noutput = ${call}`)
add('nlm', `# h 控制亮度去噪，hColor 控制颜色去噪；后两项是模板块与搜索窗。
output = cv2.fastNlMeansDenoisingColored(image, None, params["strength"], params["strength"], 7, 21)`)
add('convolution', `kernel = np.asarray(params["matrix"], dtype=np.float32)
if kernel.ndim != 2 or kernel.shape[0] != kernel.shape[1] or kernel.shape[0] % 2 != 1:
    raise ValueError("需要奇数边长的方形卷积核")
# ddepth=-1 保持 8 位输出；改为 CV_32F 可观察负响应。
output = cv2.filter2D(image, ddepth=-1, kernel=kernel)`)
add('sharpen', `k = max(1, int(params["kernel"])) | 1
blurred = cv2.GaussianBlur(image, (k, k), 0)
# 原图 + amount * (原图 - 模糊图)
output = cv2.addWeighted(image, 1 + params["amount"], blurred, -params["amount"], 0)`)
const spectrum = 'spectrum = np.fft.fftshift(np.fft.fft2(gray))'
add('fft', `${spectrum}
display = np.log1p(np.abs(spectrum))
output = cv2.normalize(display, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
np.save("spectrum.npy", np.abs(spectrum))`)
for (const id of ['lowpass', 'highpass']) add(id, `${spectrum}
yy, xx = np.ogrid[:h, :w]
mask = (xx - w // 2) ** 2 + (yy - h // 2) ** 2 <= (min(h, w) * params["radius"]) ** 2
${id === 'highpass' ? 'mask = ~mask  # 高通：去掉中心低频' : '# 低通：保留中心低频'}
filtered = np.abs(np.fft.ifft2(np.fft.ifftshift(spectrum * mask)))
output = cv2.normalize(filtered, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
np.save("filtered.npy", filtered)`)
add('threshold', `# 大于阈值设为白色，其余为黑色。
_, output = cv2.threshold(gray, params["threshold"], 255, cv2.THRESH_BINARY)`)
add('adaptive', `block = max(3, int(params["block"])) | 1
# 每个位置使用“局部高斯加权均值 - C”作为阈值。
output = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, block, params["constant"])`)
add('otsu', `# 第二个参数 0 不参与手工设阈值，Otsu 会自动选择。
threshold, output = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
print("本次自动阈值:", threshold)`)
for (const [id, operator, comment] of [
  ['erode', 'ERODE', '腐蚀：取邻域最小值，白区收缩。'],
  ['dilate', 'DILATE', '膨胀：取邻域最大值，白区扩张。'],
  ['open', 'OPEN', '先腐蚀后膨胀，去掉较小的亮结构。'],
  ['close', 'CLOSE', '先膨胀后腐蚀，填掉较小的暗结构。'],
  ['morph_gradient', 'GRADIENT', '膨胀减腐蚀，得到边界带。'],
  ['tophat', 'TOPHAT', '原图减开运算，突出细小亮结构。'],
  ['blackhat', 'BLACKHAT', '闭运算减原图，突出细小暗结构。'],
]) add(id, `k = max(1, int(params["kernel"])) | 1
shape = {"ellipse": cv2.MORPH_ELLIPSE, "rect": cv2.MORPH_RECT, "cross": cv2.MORPH_CROSS}[params["shape"]]
kernel = cv2.getStructuringElement(shape, (k, k))
# ${comment} 输入二值掩膜时最容易观察。
output = cv2.morphologyEx(image, cv2.MORPH_${operator}, kernel, iterations=int(params["iterations"]))`)
add('skeleton', `_, remaining = cv2.threshold(gray, params["threshold"], 255, cv2.THRESH_BINARY)
output = np.zeros_like(gray)
kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
for _ in range(max(h, w)):
    eroded = cv2.erode(remaining, kernel, borderType=cv2.BORDER_CONSTANT, borderValue=0)
    rim = cv2.subtract(remaining, cv2.dilate(eroded, kernel))
    output = cv2.bitwise_or(output, rim)
    remaining = eroded
    if cv2.countNonZero(remaining) == 0:
        break`)
add('distance', `_, mask = cv2.threshold(gray, params["threshold"], 255, cv2.THRESH_BINARY)
distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
print("最大距离，单位 px:", float(distance.max()))
np.save("distance_pixels.npy", distance)
# 归一化只为了显示，不用于读取真实距离。
output = cv2.normalize(distance, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)`)
for (const id of ['sobel', 'scharr']) add(id, `# 浮点类型保留梯度的正负号。
gx = cv2.${id === 'sobel' ? 'Sobel' : 'Scharr'}(gray, cv2.CV_32F, 1, 0)
gy = cv2.${id === 'sobel' ? 'Sobel' : 'Scharr'}(gray, cv2.CV_32F, 0, 1)
magnitude = cv2.magnitude(gx, gy)
output = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
np.savez("gradients.npz", gx=gx, gy=gy)`)
add('laplacian', `signed = cv2.Laplacian(gray, cv2.CV_32F)
np.save("laplacian_signed.npy", signed)
# 显示取绝对值；研究零交叉时应使用上面的 signed 数组。
output = cv2.convertScaleAbs(signed)`)
add('canny', `low, high = params["low"], params["high"]
if high < low:
    raise ValueError("高阈值不能低于低阈值")
# 与平台一致：灰度图直接进入 Canny，不额外添加平滑。
# 高阈值确定强边缘，低阈值决定可与强边缘连接的弱边缘。
output = cv2.Canny(gray, threshold1=low, threshold2=high)
print("边缘像素数量:", int(np.count_nonzero(output)))`)
const objectMeasurements = `objects = []
for index, contour in enumerate(contours, 1):
    moments = cv2.moments(contour)
    x, y, bw, bh = cv2.boundingRect(contour)
    center = [moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]] if moments["m00"] else [x, y]
    rect = cv2.minAreaRect(contour)
    objects.append({"id": index, "area_px2": cv2.contourArea(contour),
                    "perimeter_px": cv2.arcLength(contour, True), "centroid": center,
                    "box": [x, y, bw, bh], "oriented_box": cv2.boxPoints(rect).tolist(),
                    "width_px": rect[1][0], "height_px": rect[1][1], "angle_deg": rect[2]})
    cv2.drawContours(output, [contour], -1, (0, 255, 0), 2)`
add('contours', `${contourSetup}\n${objectMeasurements}\nprint(objects)`)
add('contour_area', `${contourSetup}
for index, contour in enumerate(contours, 1):
    print(index, "轮廓面积 px²:", cv2.contourArea(contour))
    cv2.drawContours(output, [contour], -1, (0, 255, 0), 2)`)
add('contour_perimeter', `${contourSetup}
for index, contour in enumerate(contours, 1):
    print(index, "闭合轮廓周长 px:", cv2.arcLength(contour, closed=True))
    cv2.drawContours(output, [contour], -1, (0, 255, 0), 2)`)
add('centroid', `${contourSetup}
for contour in contours:
    moments = cv2.moments(contour)
    if moments["m00"] == 0:
        continue
    cx, cy = moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]
    print("质心 x, y:", cx, cy)
    cv2.circle(output, (round(cx), round(cy)), 4, (0, 0, 255), -1)`)
add('bounding_box', `${contourSetup}
for contour in contours:
    x, y, bw, bh = cv2.boundingRect(contour)
    corners = cv2.boxPoints(cv2.minAreaRect(contour))
    print("轴对齐框 [x,y,w,h]:", [x, y, bw, bh], "旋转框顶点:", corners.tolist())
    cv2.rectangle(output, (x, y), (x + bw, y + bh), (255, 0, 0), 2)
    cv2.polylines(output, [corners.astype(np.int32)], True, (0, 255, 0), 2)`)
add('components', `${contourSetup}
count, labels, stats, centers = cv2.connectedComponentsWithStats(mask, connectivity=8)
objects = []
for label in range(1, count):  # 0 是背景
    x, y, bw, bh, area = stats[label]
    if area < params["min_area"]:
        continue
    objects.append({"label": label, "area_px2": int(area), "centroid": centers[label].tolist()})
    cv2.rectangle(output, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
print("连通域数量:", len(objects), objects)
np.save("labels.npy", labels)`)
add('hull', `${contourSetup}
for contour in contours:
    hull = cv2.convexHull(contour)
    cv2.drawContours(output, [hull], -1, (0, 255, 0), 2)
    print("原轮廓面积:", cv2.contourArea(contour), "凸包面积:", cv2.contourArea(hull))`)
add('shape_match', `${contourSetup}
reference = cv2.imread("reference.jpg", cv2.IMREAD_GRAYSCALE)
if reference is None:
    raise FileNotFoundError("请提供参考形状图片 reference.jpg")
_, reference_mask = cv2.threshold(reference, params["threshold"], 255, cv2.THRESH_BINARY)
reference_contours, _ = cv2.findContours(reference_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
reference_contours = [c for c in reference_contours if cv2.contourArea(c) >= params["min_area"]]
if not reference_contours:
    raise ValueError("参考图没有有效轮廓")
target = max(reference_contours, key=cv2.contourArea)
for contour in contours:
    distance = cv2.matchShapes(contour, target, cv2.CONTOURS_MATCH_I1, 0)
    print("形状距离，越小越相似:", distance)
    cv2.drawContours(output, [contour], -1, (0, 255, 0), 2)`)
add('count', `${contourSetup}
print("保留的外轮廓数:", len(contours))
for index, contour in enumerate(contours, 1):
    x, y, _, _ = cv2.boundingRect(contour)
    cv2.drawContours(output, [contour], -1, (0, 255, 0), 2)
    cv2.putText(output, str(index), (x, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)`)
add('measure', `${contourSetup}\n${objectMeasurements}
scale = params["pixels_per_mm"]
for item in objects:
    if scale > 0:
        item.update(width_mm=item["width_px"] / scale, height_mm=item["height_px"] / scale)
    cv2.polylines(output, [np.int32(item["oriented_box"])], True, (255, 180, 60), 2)
print(objects)
for i, a in enumerate(contours):
    for j in range(i + 1, len(contours)):
        gap = float(cKDTree(a[:, 0]).query(contours[j][:, 0])[0].min())
        print("目标对:", i + 1, j + 1, "间隙 px:", gap, "间隙 mm:", gap / scale if scale > 0 else None)`, 'from scipy.spatial import cKDTree', '', 'opencv-contrib-python numpy scipy')
add('angle_measure', `${contourSetup}
for contour in contours:
    center, size, angle = cv2.minAreaRect(contour)
    corners = cv2.boxPoints((center, size, angle))
    cv2.polylines(output, [corners.astype(np.int32)], True, (0, 255, 0), 2)
    print("框宽高:", size, "OpenCV 矩形角度:", angle)
# 连续角度跟踪需自行处理宽高交换、180 度对称和角度归一化。`)
add('gap_measure', `${contourSetup}
scale = params["pixels_per_mm"]
for i, a in enumerate(contours):
    for j in range(i + 1, len(contours)):
        # 查询边界点之间的最近距离，不是质心之间的距离。
        gap = float(cKDTree(a[:, 0]).query(contours[j][:, 0])[0].min())
        print({"pair": [i + 1, j + 1], "gap_px": gap,
               "gap_mm": gap / scale if scale > 0 else None})
cv2.drawContours(output, contours, -1, (0, 255, 0), 2)`, 'from scipy.spatial import cKDTree', '', 'opencv-contrib-python numpy scipy')
add('hough_lines', `edges = cv2.Canny(gray, 50, 150)
lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=int(params["votes"]),
                        minLineLength=params["length"], maxLineGap=params["gap"])
for x1, y1, x2, y2 in ([] if lines is None else lines[:, 0]):
    cv2.line(output, (x1, y1), (x2, y2), (0, 255, 255), 2)
    print("线段端点:", x1, y1, x2, y2)`)
add('hough_circles', `if params["max_radius"] <= params["min_radius"]:
    raise ValueError("最大半径需大于最小半径")
circles = cv2.HoughCircles(cv2.GaussianBlur(gray, (5, 5), 0), cv2.HOUGH_GRADIENT,
                         dp=1, minDist=30, param1=100, param2=params["votes"],
                         minRadius=int(params["min_radius"]), maxRadius=int(params["max_radius"]))
for x, y, r in ([] if circles is None else circles[0]):
    print("圆心与半径:", float(x), float(y), float(r))
    cv2.circle(output, (round(x), round(y)), round(r), (0, 255, 255), 2)`)
add('crop', `# 未画 ROI 时，用中央一半区域演示；格式为 x、y、宽、高。
x, y, rw, rh = map(int, params.get("roi", [w // 4, h // 4, w // 2, h // 2]))
if rw <= 0 or rh <= 0 or x < 0 or y < 0 or x + rw > w or y + rh > h:
    raise ValueError("ROI 必须位于图片内")
output = image[y:y + rh, x:x + rw].copy()
print("原图坐标偏移:", [x, y])`)
add('resize', `methods = {"nearest": cv2.INTER_NEAREST, "linear": cv2.INTER_LINEAR,
           "cubic": cv2.INTER_CUBIC, "area": cv2.INTER_AREA, "lanczos": cv2.INTER_LANCZOS4}
output = cv2.resize(image, None, fx=params["scale"], fy=params["scale"],
                    interpolation=methods[params["method"]])
print("输出宽高:", output.shape[1], output.shape[0])`)
add('rotate', `matrix = cv2.getRotationMatrix2D((w / 2, h / 2), params["angle"], 1)
# 沿用原画布大小：空白处填黑，超出边界的内容被裁掉。
output = cv2.warpAffine(image, matrix, (w, h))`)
add('affine', `matrix = np.asarray(params["matrix"], dtype=np.float64)
if matrix.shape != (2, 3):
    raise ValueError("仿射矩阵必须为 2×3")
output = cv2.warpAffine(image, matrix, (w, h))`)
add('perspective', `# 四点顺序：左上、右上、右下、左下。默认用四角演示恒等变换。
points = np.float32(params.get("polygon", [[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]]))
if points.shape != (4, 2) or not cv2.isContourConvex(points.astype(np.int32)):
    raise ValueError("请选择不自交的凸四边形")
target = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]])
matrix = cv2.getPerspectiveTransform(points, target)
output = cv2.warpPerspective(image, matrix, (w, h))
print("单应矩阵:", matrix)`)
add('region_grow', `# 未点选时用中心点演示，实际请选在目标内部。
x, y = map(int, params.get("points", [[w // 2, h // 2]])[0][:2])
mask = np.zeros((h + 2, w + 2), np.uint8)
tolerance = params["tolerance"]
flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8)
cv2.floodFill(image.copy(), mask, (x, y), (0, 0, 0),
              (tolerance,) * 3, (tolerance,) * 3, flags)
output = mask[1:-1, 1:-1]`)
add('watershed', `_, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
seeds = np.uint8(distance > distance.max() * params["seed_ratio"])
_, markers = cv2.connectedComponents(seeds)
markers += 1  # 背景为 1，未知区必须留作 0
markers[(cv2.dilate(mask, None) > 0) & (seeds == 0)] = 0
labels = cv2.watershed(image, markers)
output[labels == -1] = (0, 0, 255)
np.save("watershed_labels.npy", labels)
print("区域数:", max(0, int(labels.max()) - 1))`)
add('grabcut', `rect = tuple(map(int, params.get("roi", [w // 4, h // 4, w // 2, h // 2])))
mask = np.zeros((h, w), np.uint8)
cv2.grabCut(image, mask, rect, np.zeros((1, 65)), np.zeros((1, 65)),
            int(params["iterations"]), cv2.GC_INIT_WITH_RECT)
foreground = np.uint8((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)) * 255
cv2.imwrite("foreground_mask.png", foreground)
output = cv2.bitwise_and(image, image, mask=foreground)`)
add('kmeans_segment', `samples = image.reshape(-1, 3).astype(np.float32)
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1)
cv2.setRNGSeed(7)
_, labels, centers = cv2.kmeans(samples, int(params["clusters"]), None, criteria, 3, cv2.KMEANS_PP_CENTERS)
output = centers.astype(np.uint8)[labels.ravel()].reshape(image.shape)
np.save("color_labels.npy", labels.reshape(h, w))
print("代表色 BGR:", centers)`)
for (const [id, harris] of [['harris', 'True'], ['shi', 'False']]) add(id, `points = cv2.goodFeaturesToTrack(gray, maxCorners=int(params["max_features"]),
                                 qualityLevel=0.01, minDistance=8, useHarrisDetector=${harris})
for x, y in ([] if points is None else points[:, 0]):
    cv2.circle(output, (round(x), round(y)), 3, (0, 255, 0), 1)
print("角点数:", 0 if points is None else len(points))`)
for (const [id, detector] of [['sift', 'SIFT'], ['orb', 'ORB']]) add(id, `detector = cv2.${detector}_create(nfeatures=int(params["max_features"]))
keypoints, descriptors = detector.detectAndCompute(gray, None)
output = cv2.drawKeypoints(image, keypoints, None, color=(0, 255, 0))
print("特征点数:", len(keypoints))
if descriptors is not None:
    np.save("descriptors.npy", descriptors)`)
add('hog', `gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
magnitude, angle = cv2.cartToPolar(gx, gy)
cell = max(8, min(h, w) // 30)
output = np.zeros_like(image)
for y in range(0, h - cell, cell):
    for x in range(0, w - cell, cell):
        hist, _ = np.histogram(angle[y:y+cell, x:x+cell] % np.pi, bins=9,
                               range=(0, np.pi), weights=magnitude[y:y+cell, x:x+cell])
        cx, cy = x + cell // 2, y + cell // 2
        for index, value in enumerate(hist):
            theta = (index + 0.5) * np.pi / 9
            radius = cell * 0.45 * value / (hist.max() + 1e-9)
            dx, dy = int(np.cos(theta) * radius), int(np.sin(theta) * radius)
            cv2.line(output, (cx-dx, cy-dy), (cx+dx, cy+dy), (120, 220, 180), 1)
# 这是方向统计可视化；标准 HOG 描述子还包含块归一化。`)
add('lbp', `output = np.zeros_like(gray)
neighbors = [(-1,-1), (-1,0), (-1,1), (0,1), (1,1), (1,0), (1,-1), (0,-1)]
for bit, (dy, dx) in enumerate(neighbors):
    output |= (np.uint8(np.roll(gray, (dy, dx), (0, 1)) >= gray) << bit)
# 边界不使用周期绕回的邻居。
output[[0, -1], :] = 0
output[:, [0, -1]] = 0`)
add('matching', `${featureMatching}
output = cv2.drawMatches(image, k1, reference, k2, good, None, flags=2)
print("通过描述子比率筛选的匹配数:", len(good))`)
const homography = `${featureMatching}
matrix, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
if matrix is None or inliers is None or int(inliers.sum()) < 4:
    raise ValueError("无法找到稳定的单应矩阵")
print("匹配数:", len(good), "内点数:", int(inliers.sum()))`
add('ransac', `${homography}
output = cv2.drawMatches(image, k1, reference, k2, good, None,
                         matchesMask=inliers.ravel().tolist(), flags=2)`)
add('register', `${homography}
output = cv2.warpPerspective(image, matrix, (reference.shape[1], reference.shape[0]))
np.save("homography.npy", matrix)`)
add('stitch', `${homography}
rh, rw = reference.shape[:2]
corners = np.float32([[0,0], [w,0], [w,h], [0,h]])[:, None]
warped = cv2.perspectiveTransform(corners, matrix)[:, 0]
all_points = np.vstack([warped, [[0,0], [rw,0], [rw,rh], [0,rh]]])
low, high = np.floor(all_points.min(0)).astype(int), np.ceil(all_points.max(0)).astype(int)
size = tuple((high - low).tolist())
if min(size) <= 0 or size[0] * size[1] > 16000000:
    raise ValueError("变换产生异常画布，请检查匹配")
offset = np.float64([[1,0,-low[0]], [0,1,-low[1]], [0,0,1]])
a = cv2.warpPerspective(image, offset @ matrix, size)
b = cv2.warpPerspective(reference, offset, size)
ma = cv2.warpPerspective(np.ones((h,w), np.uint8), offset @ matrix, size)
mb = cv2.warpPerspective(np.ones((rh,rw), np.uint8), offset, size)
wa, wb = cv2.distanceTransform(ma, cv2.DIST_L2, 3), cv2.distanceTransform(mb, cv2.DIST_L2, 3)
weight = wa / (wa + wb + 1e-8)
output = (a * weight[:, :, None] + b * (1-weight[:, :, None])).astype(np.uint8)`)
const template = `template = cv2.imread("template.jpg")
if template is None:
    raise FileNotFoundError("请提供小于原图的 template.jpg")
th, tw = template.shape[:2]
template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
if th > h or tw > w or template_gray.std() < 1:
    raise ValueError("模板必须有纹理且不能大于原图")
scores = cv2.matchTemplate(gray, template_gray, cv2.TM_CCOEFF_NORMED)
_, score, _, location = cv2.minMaxLoc(scores)
x, y = location
cv2.rectangle(output, (x, y), (x+tw, y+th), (0, 255, 0), 2)
print("最佳位置:", location, "相关系数:", score)
np.save("template_scores.npy", scores)`
add('template', template)
add('industrial_template', `${template}
# 工业应用需用实际正负样本确定阈值，并控制光照、角度和尺寸。
# 不把“有一个最佳位置”直接当作检测通过。`)
const samples = `rng = np.random.default_rng(42)
pixels = image.reshape(-1, 3)
samples = pixels[rng.choice(len(pixels), min(2000, len(pixels)), replace=False)].astype(np.float32)
features = samples[:, [2, 1]]  # R、G 作为横纵坐标
labels = np.int32(samples[:, 0] > np.median(samples[:, 0]))
grid = np.float32([[x, y] for y in range(256) for x in range(256)])`
const decisionDisplay = `palette = np.uint8([[70,90,160], [100,160,65], [160,100,65], [120,65,160], [65,160,160]] * 2)
output = palette[prediction.astype(int).ravel()].reshape(256, 256, 3)
for xy, label in zip(features[:300], labels[:300]):
    cv2.circle(output, tuple(xy.astype(int)), 2, (240,240,240) if label else (20,20,20), -1)
print("教学用 R/G 特征空间；没有独立真值，不报告准确率")`
add('knn', `${samples}
if len(np.unique(labels)) < 2:
    raise ValueError("需要蓝通道有变化的图片来构造两类样本")
model = cv2.ml.KNearest_create()
model.train(features, cv2.ml.ROW_SAMPLE, labels)
_, prediction, neighbors, distances = model.findNearest(grid, int(params["complexity"]))
${decisionDisplay}`)
add('svm', `${samples}
if len(np.unique(labels)) < 2:
    raise ValueError("需要蓝通道有变化的图片来构造两类样本")
model = cv2.ml.SVM_create()
model.setKernel(cv2.ml.SVM_RBF)
model.setC(params["complexity"])
model.setGamma(0.0001)
model.train(features, cv2.ml.ROW_SAMPLE, labels)
_, prediction = model.predict(grid)
${decisionDisplay}`)
add('kmeans_demo', `${samples}
cv2.setRNGSeed(42)
_, _, centers = cv2.kmeans(features, max(2, int(params["complexity"])), None,
                         (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.2), 3, cv2.KMEANS_PP_CENTERS)
prediction = np.argmin(((grid[:, None] - centers[None]) ** 2).sum(2), axis=1)
${decisionDisplay}`)
add('lowlight', `floating = image.astype(np.float32) + 1
illumination = cv2.GaussianBlur(floating, (0, 0), params["sigma"])
reflectance = np.log(floating) - np.log(illumination)
output = cv2.normalize(reflectance, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)`)
add('inpaint', `mask = np.zeros((h, w), np.uint8)
# mask_points 每项为原图坐标 x、y 和画笔半径。
points = params.get("mask_points", [])
if not points:
    raise ValueError("请先在页面绘制修复区域，或在 params 中填写 mask_points")
for x, y, radius in points:
    cv2.circle(mask, (int(x), int(y)), max(1, min(int(radius), 100)), 255, -1)
output = cv2.inpaint(image, mask, params["radius"], cv2.INPAINT_TELEA)
cv2.imwrite("mask.png", mask)`)
add('augmentation', `matrix = cv2.getRotationMatrix2D((w / 2, h / 2), params["angle"], 1)
output = cv2.warpAffine(image, matrix, (w, h))
if params["flip"] != "none":
    output = cv2.flip(output, 1 if params["flip"] == "horizontal" else 0)
noise = np.random.default_rng(42).normal(0, params["noise"], output.shape)
output = np.clip(output * params["brightness"] + noise, 0, 255).astype(np.uint8)
# 训练数据的框、关键点和掩膜还需同步变换；本例只演示图像。`)
add('qr', `ok, texts, points, _ = cv2.QRCodeDetector().detectAndDecodeMulti(image)
if ok and points is not None:
    for text, polygon in zip(texts, points):
        print("二维码文本:", text)
        cv2.polylines(output, [polygon.astype(np.int32)], True, (0, 255, 0), 2)
else:
    print("没有成功解码的二维码")`)
add('barcode', `# 需要 opencv-contrib-python 中的 barcode 模块。
detector = cv2.barcode_BarcodeDetector()
ok, texts, types, points = detector.detectAndDecodeWithType(image)
if ok and points is not None:
    for text, kind, polygon in zip(texts, types, points):
        print("码制:", kind, "内容:", text)
        cv2.polylines(output, [np.int32(polygon)], True, (0, 255, 0), 2)
else:
    print("未解码；检查码制支持、清晰度和条纹完整性")`)
