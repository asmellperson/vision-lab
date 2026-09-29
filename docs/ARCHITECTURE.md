# 架构说明

Vision Lab 使用 React 前端和 FastAPI 后端，算法执行、模型推理与数据存储均在本地完成。

## 目录结构

- `frontend/`：React + TypeScript + Vite，算法搜索、统一实验页、模型管理、实验历史和流水线。参数和输入要求来自后端元数据。
- `backend/app/algorithms/`：注册表、传统算子、工业与三维算法。统一返回底图、独立图层、数据和下载产物。
- `backend/app/video.py`：视频逐帧处理、跟踪、事件规则与结果编码。
- `backend/app/models.py`：版本化模型清单、文件校验、按需加载、单设备互斥与缓存释放。
- `backend/app/jobs.py`：SQLite 持久任务与后台工作线程，排队、进度、取消、错误、重启恢复。
- `backend/app/main.py`：上传、素材、实验、预览、模型下载、参数方案、流水线 REST API。
- `data/`：运行时上传、SQLite、实验产物；`models/`：本地权重与配置；`assets/examples/`：可复现示例素材。

前端主要文件：

| 文件 | 职责 |
| --- | --- |
| `App.tsx` | 应用导航、分类搜索和路由 |
| `Experiment.tsx` | 实验输入、参数、任务状态、结果及学习标签页 |
| `Viewer.tsx` | 图片、视频、点云、图层与坐标交互 |
| `Controls.tsx` | 参数表单与素材上传 |
| `Pages.tsx` | 首页、模型管理、历史记录和流水线 |
| `learning/` | 按算法组织的原理、结果解读和 Python 示例 |

## 实验执行

1. 前端读取算法注册信息，生成输入区、参数表单和交互控件。
2. 素材上传后保存到 `data/`，请求使用素材 ID 引用输入。
3. 实验请求进入后台队列，由执行器调用传统算子或本地模型适配器。
4. 任务状态、参数和结果写入 SQLite；产物以图片、视频、JSON、NPZ 等格式保存。
5. 前端展示进度和结果，支持取消任务、下载产物与历史对比。

后台工作线程串行处理实验，等待队列上限为 32，轻量预览最多并发两份。模型推理加锁，默认缓存一个模型。服务应使用单个 Uvicorn worker，避免多个进程各自创建模型缓存和任务队列。

MediaPipe 使用独立的 `vision-lab-mediapipe` Conda 环境与本地工作进程。其他实验在 `vision-lab` 主环境中运行。

## 数据约定

- 坐标对应 EXIF 方向修正后的原图，前端通过 SVG `viewBox` 映射显示坐标。
- 算法底图采用 BGR `uint8`，叠加图层采用同尺寸 BGRA。原始标签与彩色可视化分别保存。
- 视频输入由 FFmpeg 规范化为恒定帧率，结果按相同帧率输出 H.264/AAC。逐帧图像算法与时序算法分别声明能力。
- 长度默认使用 px；提供有效尺度后才输出 mm。单目深度和两视图重建使用相对尺度。
- 有真值时计算评估指标；无真值时提供预测结果与耗时。
- 模型下载与推理分离，推理阶段只读取本地文件。

输入格式、单位与导出约定见 [实验输入与结果说明](EXPERIMENTS.md)。

## 添加算法

1. 在 `backend/app/algorithms/` 的注册表中声明 `id/category/inputs/params/interaction/model/output_kind`。
2. 实现执行器，返回 `Result(image, data, layers, arrays)`。
3. 在 `backend/app/recipes.py` 中提供与算法输入要求匹配的示例。
4. 在 `frontend/src/learning/` 中补充原理、结果解读与直接调用算法库的 Python 示例。
5. 验证参数生效、输入校验、结果格式和示例运行，测试方法见 [测试指南](VALIDATION.md)。

通用输入、参数和结果组件可从注册信息生成界面；只有需要新交互方式或新结果类型时，才需要扩展相应前端组件。

## 添加模型

在 `backend/app/model_manifest.py` 登记模型任务、官方来源、许可、设备和所需文件，在 `models.py` 与 `inference.py` 中实现本地加载及推理适配。模型资源应包含权重、配置、词表等完整依赖，并通过 `inventory.json` 记录版本与文件哈希。

Hugging Face 模型固定到下载时的提交 SHA，文件修复沿用该版本。其他来源记录发布版本与文件 SHA256。运行时的完整性校验与来源许可分别见 [模型清单](MODELS.md) 和 [第三方来源](../THIRD_PARTY.md)。

## 流水线

流水线支持最多 15 步，可排序、启停、保存和复用。步骤限于无需额外输入的图像算子；形态学步骤要求灰度图或掩膜，轮廓、计数和测量步骤放在末端。执行前检查步骤连接的类型，运行后保留逐步产物。
