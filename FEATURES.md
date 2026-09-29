# 功能清单

平台提供 **140 个算法实验、13 个模块**。每个实验包含输入要求、参数设置、示例素材、原理与结果解读，以及 Python 调用示例。

| 模块 | 独立入口 |
| --- | --- |
| 图像基础 | 21 |
| 滤波与增强 | 10 |
| 阈值与形态学 | 12 |
| 边缘与形状 | 14 |
| 几何与传统分割 | 10 |
| 特征与匹配 | 13 |
| 工业视觉 | 11 |
| 文字与图文理解 | 9 |
| 深度学习识别 | 10 |
| 标定与三维 | 7 |
| 图像恢复 | 6 |
| 视频与时序 | 10 |
| 模型学习与评估 | 7 |

## 平台体验

- 中文分类与用途搜索、常用实验入口、图片/视频/点云上传、完整示例。
- 自动参数表单、重置/方案、轻量预览、后台排队/进度/取消/失败。
- 并排/滑动对比、同步缩放/平移、原图局部放大、独立图层。
- 原图坐标矩形、多边形、前景/背景点、修复画笔。
- 视频同步播放/定位/单帧实验、触发缩略图/事件依据。
- 正常样本建库、特征库复用、异常连续分数/用户阈值。
- SQLite 历史、同素材最多四结果对比、PNG/MP4/NPZ/JSON/ZIP 下载。
- 可排序/启停/保存流水线、类型校验、逐步产物、历史恢复。
- 模型下载进度、完整文件校验、缺文件/加载失败提示、缓存释放。
- 本地模型离线推理、CPU 与适用模型的 CUDA 支持、独立 MediaPipe 工作进程。

## 算法入口

“参数”是数值/枚举/JSON 字段数，ROI 等画布交互单独列出。每项实验默认与主输入配套输出图片/视频及适用结构化数据，具体输出可在结果页和下载包中检查。

### 图像基础

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 像素与取色 | `pixels` | image | 2 / points | OpenCV / 数值计算 |
| 灰度化 | `gray` | image | 0 / 无 | OpenCV / 数值计算 |
| 颜色空间转换 | `color` | image | 1 / 无 | OpenCV / 数值计算 |
| 通道分离 | `channel` | image | 1 / 无 | OpenCV / 数值计算 |
| 通道合并 | `merge` | image | 3 / 无 | OpenCV / 数值计算 |
| 加法 | `add` | image, reference | 0 / 无 | OpenCV / 数值计算 |
| 减法 | `subtract` | image, reference | 0 / 无 | OpenCV / 数值计算 |
| 加权融合 | `blend` | image, reference | 1 / 无 | OpenCV / 数值计算 |
| 按位与 | `bit_and` | image, reference | 0 / 无 | OpenCV / 数值计算 |
| 按位或 | `bit_or` | image, reference | 0 / 无 | OpenCV / 数值计算 |
| 按位异或 | `bit_xor` | image, reference | 0 / 无 | OpenCV / 数值计算 |
| 按位非 | `bit_not` | image | 0 / 无 | OpenCV / 数值计算 |
| 直方图 | `histogram` | image | 0 / 无 | OpenCV / 数值计算 |
| 亮度与对比度 | `brightness` | image | 2 / 无 | OpenCV / 数值计算 |
| 伽马校正 | `gamma` | image | 1 / 无 | OpenCV / 数值计算 |
| 直方图均衡 | `equalize` | image | 0 / 无 | OpenCV / 数值计算 |
| CLAHE 局部均衡 | `clahe` | image | 2 / 无 | OpenCV / 数值计算 |
| RGB 颜色空间 | `rgb` | image | 1 / 无 | OpenCV / 数值计算 |
| HSV 颜色空间 | `hsv` | image | 1 / 无 | OpenCV / 数值计算 |
| Lab 颜色空间 | `lab` | image | 1 / 无 | OpenCV / 数值计算 |
| YCrCb 颜色空间 | `ycrcb` | image | 1 / 无 | OpenCV / 数值计算 |

### 滤波与增强

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 均值滤波 | `mean` | image | 1 / 无 | OpenCV / 数值计算 |
| 高斯滤波 | `gaussian` | image | 1 / 无 | OpenCV / 数值计算 |
| 中值滤波 | `median` | image | 1 / 无 | OpenCV / 数值计算 |
| 双边滤波 | `bilateral` | image | 2 / 无 | OpenCV / 数值计算 |
| 非局部均值去噪 | `nlm` | image | 1 / 无 | OpenCV / 数值计算 |
| 自定义卷积核 | `convolution` | image | 1 / 无 | OpenCV / 数值计算 |
| 锐化 | `sharpen` | image | 2 / 无 | OpenCV / 数值计算 |
| 傅里叶频谱 | `fft` | image | 0 / 无 | OpenCV / 数值计算 |
| 频域低通 | `lowpass` | image | 1 / 无 | OpenCV / 数值计算 |
| 频域高通 | `highpass` | image | 1 / 无 | OpenCV / 数值计算 |

### 阈值与形态学

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 固定阈值 | `threshold` | image | 1 / 无 | OpenCV / 数值计算 |
| 自适应阈值 | `adaptive` | image | 2 / 无 | OpenCV / 数值计算 |
| Otsu 自动阈值 | `otsu` | image | 0 / 无 | OpenCV / 数值计算 |
| 腐蚀 | `erode` | image | 3 / 无 | OpenCV / 数值计算 |
| 膨胀 | `dilate` | image | 3 / 无 | OpenCV / 数值计算 |
| 开运算 | `open` | image | 3 / 无 | OpenCV / 数值计算 |
| 闭运算 | `close` | image | 3 / 无 | OpenCV / 数值计算 |
| 形态学梯度 | `morph_gradient` | image | 3 / 无 | OpenCV / 数值计算 |
| 顶帽 | `tophat` | image | 3 / 无 | OpenCV / 数值计算 |
| 黑帽 | `blackhat` | image | 3 / 无 | OpenCV / 数值计算 |
| 骨架提取 | `skeleton` | image | 1 / 无 | OpenCV / 数值计算 |
| 距离变换 | `distance` | image | 1 / 无 | OpenCV / 数值计算 |

### 边缘与形状

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| Sobel | `sobel` | image | 0 / 无 | OpenCV / 数值计算 |
| Scharr | `scharr` | image | 0 / 无 | OpenCV / 数值计算 |
| Laplacian | `laplacian` | image | 0 / 无 | OpenCV / 数值计算 |
| Canny | `canny` | image | 2 / 无 | OpenCV / 数值计算 |
| 轮廓、面积与周长 | `contours` | image | 2 / 无 | OpenCV / 数值计算 |
| 连通域与质心 | `components` | image | 2 / 无 | OpenCV / 数值计算 |
| 凸包 | `hull` | image | 2 / 无 | OpenCV / 数值计算 |
| 形状匹配 | `shape_match` | image, reference | 2 / 无 | OpenCV / 数值计算 |
| 霍夫直线 | `hough_lines` | image | 3 / 无 | OpenCV / 数值计算 |
| 霍夫圆 | `hough_circles` | image | 3 / 无 | OpenCV / 数值计算 |
| 轮廓面积 | `contour_area` | image | 2 / 无 | OpenCV / 数值计算 |
| 轮廓周长 | `contour_perimeter` | image | 2 / 无 | OpenCV / 数值计算 |
| 图像矩与质心 | `centroid` | image | 2 / 无 | OpenCV / 数值计算 |
| 外接框 | `bounding_box` | image | 2 / 无 | OpenCV / 数值计算 |

### 几何与传统分割

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| ROI 裁剪 | `crop` | image | 0 / rectangle | OpenCV / 数值计算 |
| 缩放与插值 | `resize` | image | 2 / 无 | OpenCV / 数值计算 |
| 旋转 | `rotate` | image | 1 / 无 | OpenCV / 数值计算 |
| 仿射变换 | `affine` | image | 1 / 无 | OpenCV / 数值计算 |
| 透视变换 | `perspective` | image | 0 / polygon | OpenCV / 数值计算 |
| 图像配准 | `register` | image, reference | 0 / 无 | OpenCV / 数值计算 |
| 区域生长 | `region_grow` | image | 1 / points | OpenCV / 数值计算 |
| 分水岭 | `watershed` | image | 1 / 无 | OpenCV / 数值计算 |
| GrabCut 前景分割 | `grabcut` | image | 1 / rectangle | OpenCV / 数值计算 |
| 颜色聚类分割 | `kmeans_segment` | image | 1 / 无 | OpenCV / 数值计算 |

### 特征与匹配

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| Harris 角点 | `harris` | image | 1 / 无 | OpenCV / 数值计算 |
| Shi-Tomasi 角点 | `shi` | image | 1 / 无 | OpenCV / 数值计算 |
| SIFT 特征 | `sift` | image | 1 / 无 | OpenCV / 数值计算 |
| ORB 特征 | `orb` | image | 1 / 无 | OpenCV / 数值计算 |
| HOG 方向梯度 | `hog` | image | 0 / 无 | OpenCV / 数值计算 |
| LBP 局部纹理 | `lbp` | image | 0 / 无 | OpenCV / 数值计算 |
| 特征匹配 | `matching` | image, reference | 1 / 无 | OpenCV / 数值计算 |
| RANSAC 鲁棒匹配 | `ransac` | image, reference | 1 / 无 | OpenCV / 数值计算 |
| 图像拼接 | `stitch` | image, reference | 1 / 无 | OpenCV / 数值计算 |
| 模板匹配 | `template` | image, template | 0 / rectangle | OpenCV / 数值计算 |
| KNN 小型学习 | `knn` | image | 1 / 无 | OpenCV / 数值计算 |
| SVM 小型学习 | `svm` | image | 1 / 无 | OpenCV / 数值计算 |
| K-means 小型学习 | `kmeans_demo` | image | 1 / 无 | OpenCV / 数值计算 |

### 工业视觉

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 零件计数 | `count` | image | 2 / 无 | OpenCV / 数值计算 |
| 尺寸、角度与间隙 | `measure` | image | 3 / 无 | OpenCV / 数值计算 |
| 颜色一致性 | `color_check` | image, reference | 1 / 无 | OpenCV / 数值计算 |
| 参考图差异 | `difference` | image, reference | 1 / 无 | OpenCV / 数值计算 |
| 表面缺陷规则 | `defects` | image | 1 / 无 | OpenCV / 数值计算 |
| 缺件与错装规则 | `assembly` | image, reference | 2 / rectangle | OpenCV / 数值计算 |
| 工业异常热力图 | `anomaly` | image, normal_samples | 1 / 无 | 本地 `resnet18` |
| 字符校验 | `char_check` | image | 1 / 无 | 本地 `rapidocr` |
| 工业模板定位 | `industrial_template` | image, template | 0 / rectangle | OpenCV / 数值计算 |
| 角度测量 | `angle_measure` | image | 3 / 无 | OpenCV / 数值计算 |
| 间隙测量 | `gap_measure` | image | 3 / 无 | OpenCV / 数值计算 |

### 文字与图文理解

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 二维码识别 | `qr` | image | 0 / 无 | OpenCV / 数值计算 |
| 条码识别 | `barcode` | image | 0 / 无 | OpenCV / 数值计算 |
| 文字检测与识别 | `ocr` | image | 0 / 无 | 本地 `rapidocr` |
| 版面分析 | `layout` | image | 1 / 无 | 本地 `layout` |
| 图像相似度检索 | `similarity` | image, gallery | 0 / 无 | 本地 `clip` |
| 图文检索 | `text_retrieval` | image, gallery | 1 / 无 | 本地 `clip` |
| 文字提示目标检测 | `grounding` | image | 2 / 无 | 本地 `owlvit` |
| 图像描述 | `caption` | image | 0 / 无 | 本地 `blip` |
| 视觉问答 | `vqa` | image | 1 / 无 | 本地 `blip-vqa` |

### 深度学习识别

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 图像分类 | `classify` | image | 0 / 无 | 本地 `resnet18` |
| 目标检测 | `detect` | image | 1 / 无 | 本地 `yolov8n` |
| 旋转框检测 | `obb` | image | 1 / 无 | 本地 `yolov8n-obb` |
| 实例分割 | `instance` | image | 1 / 无 | 本地 `yolov8n-seg` |
| 人体姿态 | `pose` | image | 1 / 无 | 本地 `yolov8n-pose` |
| 语义分割 | `semantic` | image | 0 / 无 | 本地 `deeplab` |
| 全景分割 | `panoptic` | image | 0 / 无 | 本地 `detr-panoptic` |
| 交互式分割 | `sam` | image | 0 / prompts | 本地 `sam2` |
| 人脸关键点 | `face` | image | 0 / 无 | 本地 `face_landmarker` |
| 手部关键点 | `hand` | image | 0 / 无 | 本地 `hand_landmarker` |

### 标定与三维

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 单目相对深度 | `depth` | image | 0 / 无 | 本地 `depth-anything` |
| 相机标定 | `calibrate` | image, calibration_images | 3 / 无 | OpenCV / 数值计算 |
| 畸变校正 | `undistort` | image | 2 / 无 | OpenCV / 数值计算 |
| 双目视差与深度 | `stereo` | image, reference | 4 / 无 | OpenCV / 数值计算 |
| 双目校正 | `stereo_rectify` | image, reference | 1 / 无 | OpenCV / 数值计算 |
| 双视图基础重建 | `reconstruct` | image, reference | 2 / 无 | OpenCV / 数值计算 |
| 点云查看、滤波与配准 | `pointcloud` | pointcloud | 3 / 无 | OpenCV / 数值计算 |

### 图像恢复

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 深度学习超分辨率 | `superres` | image | 0 / 无 | 本地 `edsr` |
| 深度学习去噪 | `denoise_dl` | image | 0 / 无 | 本地 `swin-denoise` |
| 深度学习去模糊 | `deblur` | image | 0 / 无 | 本地 `restormer` |
| 前景抠图与背景替换 | `matting` | image | 1 / 无 | 本地 `rmbg` |
| 低光增强 Retinex | `lowlight` | image | 1 / 无 | OpenCV / 数值计算 |
| 图像修复 | `inpaint` | image | 1 / brush | OpenCV / 数值计算 |

### 视频与时序

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| 视频动作识别 | `action` | video | 0 / 无 | 本地 `r3d`；连续帧 |
| 帧差 | `frame_diff` | video | 1 / 无 | OpenCV / 数值计算；连续帧 |
| 背景建模 MOG2 | `mog2` | video | 1 / 无 | OpenCV / 数值计算；连续帧 |
| 稀疏光流 | `flow_sparse` | video | 1 / 无 | OpenCV / 数值计算；连续帧 |
| 稠密光流 | `flow_dense` | video | 1 / 无 | OpenCV / 数值计算；连续帧 |
| 单目标跟踪 | `single_track` | video | 1 / rectangle | OpenCV / 数值计算；连续帧 |
| 多目标跟踪与轨迹 | `multi_track` | video | 1 / 无 | 本地 `yolov8n`；连续帧 |
| 计数、越线、区域与停留 | `events` | video | 3 / rectangle | 本地 `yolov8n`；连续帧 |
| 事件顺序规则 | `sequence` | video | 5 / rectangle | 本地 `yolov8n`；连续帧 |
| 视频分割 | `video_segment` | video | 1 / rectangle | 本地 `sam2`；连续帧 |

### 模型学习与评估

| 实验 | ID | 输入 | 参数/交互 | 实现 |
| --- | --- | --- | --- | --- |
| Grad-CAM 类激活图 | `gradcam` | image | 0 / 无 | 本地 `resnet18` |
| 特征图可视化 | `feature_maps` | image | 0 / 无 | 本地 `resnet18` |
| 推理后端对比 | `benchmark` | image | 1 / 无 | 本地 `resnet18` |
| 预处理与数据增强 | `augmentation` | image | 4 / 无 | OpenCV / 数值计算 |
| 分类指标 | `eval_classification` | image | 1 / 无 | OpenCV / 数值计算 |
| 检测 AP / mAP | `eval_detection` | image | 1 / 无 | OpenCV / 数值计算 |
| 分割 IoU / Dice | `eval_segmentation` | image, truth_mask | 2 / 无 | OpenCV / 数值计算 |

## 支持范围

| 项目 | 支持范围与限制 |
| --- | --- |
| 推理设备 | 默认 CPU，部分模型支持 CUDA；TensorRT 尚未接入，设备清单见模型文档 |
| 工业异常检测 | PatchCore 风格教学实现，使用局部特征、随机子采样参考库和最近邻热力图，不含论文中的贪心 coreset |
| 多目标跟踪 | 类别约束的 IoU 关联与轨迹、事件规则；长遮挡或交叉时可能发生 ID 切换 |
| 低光增强与图像修复 | 分别使用 Retinex 与 Telea；暂不支持生成式模型 |
| 三维重建 | 两视图、相对尺度的稀疏三角化；暂不支持完整 SfM、束调整与稠密重建 |
| 图文理解 | CLIP、OWL-ViT、BLIP，主要适用于英文提示与输出 |
| 点云 | 支持 ASCII XYZ/CSV/PLY、体素滤波、RANSAC、ICP 和旋转查看；暂不支持二进制 PLY、网格、颜色或法线保留 |
| 部署 | 面向本地实验，单工作线程处理任务；暂不提供多用户认证、生产监控或分布式任务 |

模型权重需单独准备，详见 [模型清单](docs/MODELS.md) 和 [模型下载与安装](docs/MODEL_RELEASE.md)。各类输入与结果的说明见 [实验指南](docs/EXPERIMENTS.md)。
