# 测试指南

测试分为后端、模型与视频、前端构建、学习内容和浏览器交互。安装方法见 [README](../README.md#安装与启动)；涉及模型的测试需要先准备对应权重。

## 后端测试

在项目根目录执行：

```bash
conda run --no-capture-output -n vision-lab python -m pytest backend/tests -q
conda run -n vision-lab python -m pip check
```

后端用例覆盖算法参数、输入校验、ROI、标签指标、流水线类型、任务状态、模型文件校验和视频编码。完整依赖版本见 `backend/requirements*.lock.txt`，Conda 环境定义见项目根目录的两个 `environment*.yml`。

## 模型与视频测试

```bash
conda run --no-capture-output -n vision-lab python scripts/smoke_models.py
conda run --no-capture-output -n vision-lab python scripts/smoke_video_geometry.py
```

脚本使用示例素材和本地模型文件，运行期间禁止 Python 进程建立网络连接。MediaPipe 通过独立环境读取本地 `.task` 文件。报告包含模型任务、视频处理、相机标定、配准和三维实验的结果。

## 前端构建与学习内容

在 `frontend/` 目录执行：

```bash
npm run build
conda run --no-capture-output -n vision-lab node tests/learning-content.mjs
RUN_PYTHON_EXAMPLES=1 conda run --no-capture-output -n vision-lab node tests/learning-content.mjs
```

构建包含 TypeScript 检查。学习内容测试核对 140 个算法的讲解与 Python 示例覆盖，检查 Python 语法和参数序列化。设置 `RUN_PYTHON_EXAMPLES=1` 后，会在合成图片上执行 81 个无需模型的示例，并对部分基础算子核对输出。

## 浏览器测试

需要 Chromium 和前后端服务。先在 `frontend/` 执行 `npm run build`，确保后端托管的静态页面为当前版本；随后在项目根目录运行 `bash scripts/dev.sh`，另开终端进入 `frontend/` 执行：

```bash
node tests/browser-smoke.mjs
node tests/browser-interactions.mjs
node tests/browser-final.mjs
node tests/browser-workbench.mjs
node tests/browser-learning.mjs
node tests/browser-visual-lab.mjs
```

默认浏览器路径为 `/usr/bin/chromium-browser`。除 `browser-interactions.mjs` 外，其余脚本可通过 `CHROMIUM_PATH` 指定路径；交互脚本的路径需在文件中设置。工作台、学习内容和界面脚本默认访问 `http://127.0.0.1:5178`，也支持 `BASE_URL`；其余脚本访问 `http://127.0.0.1:8018`。

浏览器测试会创建上传素材、实验和历史记录，并更新相应截图与报告。建议在独立的测试数据目录运行服务。

| 脚本 | 主要覆盖 |
| --- | --- |
| `browser-smoke.mjs` | 首页、上传、分割、视频、下载入口、流水线、模型、历史与移动端 |
| `browser-interactions.mjs` | ROI、透视、画笔、预览、参数方案、正常参考库与点云 |
| `browser-final.mjs` | CLIP 图文检索、流水线历史恢复、视频事件跳转 |
| `browser-workbench.mjs` | Canny 运行与导出、比较模式、缩放、参数折叠、图片比例和任务状态 |
| `browser-learning.mjs` | 算法讲解、代码切换、参数同步、复制、加载与错误提示 |
| `browser-visual-lab.mjs` | 首页搜索、算法目录、Canny 布局与响应式显示 |

## 报告与截图

以下文件记录对应测试运行的输出，可用于检查测试覆盖和复现结果。

| 内容 | 报告 |
| --- | --- |
| 单图模型任务 | [model-validation.json](model-validation.json) |
| 视频与几何 | [video-geometry-validation.json](video-geometry-validation.json) |
| 模型文件完整性 | [model-file-validation.json](model-file-validation.json) |
| 浏览器主要流程 | [browser-validation.json](browser-validation.json) |
| 浏览器交互流程 | [browser-interactions.json](browser-interactions.json) |
| 浏览器补充流程 | [browser-final.json](browser-final.json) |
| Canny 工作台 | [workbench-browser-validation.json](workbench-browser-validation.json) |
| 学习内容交互 | [learning-browser-validation.json](learning-browser-validation.json) |
| 首页与 Canny 布局 | [measurements.json](screenshots/visual-lab/measurements.json) |

界面截图：[首页](screenshots/visual-lab/home-1920.png)、[Canny](screenshots/visual-lab/canny-1920.png)、[移动端](screenshots/visual-lab/canny-390.png)、[视频](screenshots/video.png)。

## 覆盖范围

现有报告基于 Python 3.11、CPU PyTorch、OpenCV 4.13、Node.js 20 和 Chromium。它们用于验证功能行为与数据格式，不构成 GPU 性能或模型准确率基准。

单图模型冒烟测试使用 320×240 的示例图片；工业正常与异常素材包含合成教学图。浏览器中的慢任务和服务错误通过模拟请求验证，相关截图以 `simulated` 标记。报告未覆盖全部输入尺寸、参数组合、浏览器和硬件环境，模型 Python 示例也未逐一完成推理测试。
