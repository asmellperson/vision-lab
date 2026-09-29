export type PythonRecipe = { code: string; dependencies: string; note: string }
export const recipes: Record<string, PythonRecipe> = {}

export function imageRecipe(ids: string, body: string, imports = '', note = '', dependencies = 'opencv-contrib-python numpy') {
  for (const id of ids.split(' ')) recipes[id] = {
    dependencies,
    note: note || '把 input.jpg 换成本地图片路径。结果保存为 result.png；数值结果打印到终端或保存为数组。',
    code: `import cv2
import numpy as np
${imports}
params = {{params}}
image = cv2.imread("input.jpg")
if image is None:
    raise FileNotFoundError("请将 input.jpg 替换为有效的本地图片路径")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
h, w = gray.shape
output = image.copy()

${body.trim()}

cv2.imwrite("result.png", output)
`,
  }
}

export function scriptRecipe(ids: string, code: string, dependencies: string, note: string) {
  for (const id of ids.split(' ')) recipes[id] = { code: code.trim() + '\n', dependencies, note }
}

export const referenceImage = `reference = cv2.imread("reference.jpg")
if reference is None:
    raise FileNotFoundError("请提供 reference.jpg")
if reference.shape != image.shape:
    raise ValueError("两张图片需要同尺寸并事先对齐")`

export const contourSetup = `_, mask = cv2.threshold(gray, params["threshold"], 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted((c for c in contours if cv2.contourArea(c) >= params["min_area"]),
                  key=cv2.contourArea, reverse=True)
cv2.imwrite("mask.png", mask)`

export const featureMatching = `reference = cv2.imread("reference.jpg")
if reference is None:
    raise FileNotFoundError("请提供有真实重叠的 reference.jpg")
orb = cv2.ORB_create(nfeatures=2500)
k1, d1 = orb.detectAndCompute(gray, None)
k2, d2 = orb.detectAndCompute(cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY), None)
if d1 is None or d2 is None:
    raise ValueError("纹理不足，无法提取描述子")
pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1, d2, k=2)
good = [pair[0] for pair in pairs if len(pair) == 2
        and pair[0].distance < params.get("ratio", 0.75) * pair[1].distance]
if len(good) < 8:
    raise ValueError("可靠匹配不足，请使用有重叠且纹理清楚的两张图")
src = np.float32([k1[m.queryIdx].pt for m in good])
dst = np.float32([k2[m.trainIdx].pt for m in good])`
