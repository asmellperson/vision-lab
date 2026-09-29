# 第三方模型、代码和素材

项目模型清单保留官方来源与许可证，不对第三方模型或素材重新授予许可。使用和分发时应查看相应来源的完整许可；代码仓库的许可未必覆盖每个数据集中的原始照片。

- 完整模型版本、来源、许可、文件列表和 SHA256：[docs/MODELS.md](docs/MODELS.md)，以及各 `models/<id>/inventory.json`。
- OpenCV、TorchVision、Transformers、Ultralytics、RapidOCR、MediaPipe、DocLayout-YOLO 等依赖的许可证由各发行包携带。
- Ultralytics 与 DocLayout-YOLO 代码/模型涉及 AGPL-3.0 或相应商业许可。SAM2 原实现为 Apache-2.0，本项目使用的 Ultralytics 适配器仍有自己的许可要求。
- Restormer 官方源码、LICENSE 和任务 YAML 与权重一起下载并纳入文件校验。
- 示例照片/视频的来源与标识：[assets/examples/manifest.json](assets/examples/manifest.json)。OpenCV 视频样例源自 PETS；航拍样例来自 DOTA8，使用需遵循 DOTA 条款。程序生成的零件、棋盘、正常/异常和点云教学素材以 CC0 提供。
- 浏览器截图只展示本地平台与上述样例；预训练模型的置信度或任务输出不构成特定行业性能认证。
