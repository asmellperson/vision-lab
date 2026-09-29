# 实际验收记录

环境：Python 3.11 Conda `vision-lab`、CPU 版 PyTorch 2.11.0、OpenCV 4.13.0、Node 20、Chromium。NVIDIA 驱动不可用，未做 GPU/TensorRT 性能或精度验收。

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 后端算法、API、视频、资源 | 112 项通过 | `python -m pytest backend/tests -q`；包含参数生效、空目标、ROI、标签指标、类型校验、文件修复 |
| 预训练单图任务 | 27 项通过 | [model-validation.json](model-validation.json)，真实图片，本地权重，禁止 Python 网络连接 |
| 连续视频及单图逐帧 | 11 项通过 | [video-geometry-validation.json](video-geometry-validation.json)，真实行人片段、20 帧、10 fps、2 秒 |
| 音频与时间轴 | 通过 | pytest 给真实短视频加音轨，再上传规范化/处理，验证 H.264 结果音轨和时长误差 < 0.15 秒 |
| 原始视频掩膜 | 通过 | 逐帧 PNG ZIP，uint16 标签与孔洞保持、帧数一致；真实 SAM2 传播也通过 |
| 相机标定 | 通过 | 11 张有效真实棋盘照片，重投影 RMS 约 0.248 px |
| 配准/拼接 | 通过 | 水果图及其平移参考，1667 个 RANSAC 内点；派生参考明确标识 |
| 双目校正/基础重建 | 通过 | pytest 使用真实左右棋盘、各自内参和实测计算的外参；尺度为相对尺度 |
| 浏览器主要流程 | 9 项通过 | [browser-validation.json](browser-validation.json)：真实上传/分割/播放/下载入口/流水线/模型/历史/移动端 |
| 浏览器交互流程 | 6 项通过 | [browser-interactions.json](browser-interactions.json)：ROI/透视/掩膜/预览/方案/正常库/点云 |
| 浏览器补充流程 | 3 项通过 | [browser-final.json](browser-final.json)：CLIP 文本检索图片、流水线历史恢复、真实视频事件跳转 |
| 模型文件 SHA256 | 22 套全部通过 | [model-file-validation.json](model-file-validation.json) |
| TypeScript + Vite 生产构建 | 通过 | `cd frontend && npm run build` |
| Conda 依赖一致性 | 通过 | `conda run -n vision-lab python -m pip check`；完整安装版本见 requirements lock 文件 |

浏览器截图：[首页](screenshots/home.png)、[实验](screenshots/experiment.png)、[视频](screenshots/video.png)、[移动端](screenshots/mobile.png)。完整示例配方通过 API 遍历 140 个入口检查；传统算子在真实水果图片上逐项运行，特定任务使用零件教学图、多图、真实棋盘等合适输入。

验收覆盖真实执行与数据契约，不代表每个参数组合、所有输入大小、每个浏览器或全部 GPU。27 项单图冒烟使用缩放到 320×240 的真实示例控制 CPU 验收成本；浏览器实例分割额外使用原始真实上传。工业正常/异常示例是明确标识的合成教学图，不能作为实际产线准确率证明。图文模型可能输出错误内容，置信度不等于工业可靠性。

测试中发现并修复：Restormer 去噪需要 BiasFree 官方 YAML；Ultralytics 掩膜恢复需去除 letterbox；参考库必须通过 POST 创建并等待后再更新状态；Conda 中普通/无界面 OpenCV 覆盖 contrib 会丢失 CSRT；视频输出需恢复音轨；校验失败的文件必须重新下载而不能重新登记错误哈希。

唯一现存测试警告为 Starlette 提示未来测试客户端迁移到 httpx2，当前 API 用例通过。浏览器控制台没有未捕获异常。测试输出与下载模型保留在各自目录，临时测试媒体不作为交付素材。
