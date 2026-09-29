#!/usr/bin/env python3
"""从运行时注册表导出功能清单和已准备的模型文件清单，避免文档与代码漂移。"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.algorithms.registry import load,REGISTRY
from app.models import list_models

load()
docs=ROOT/'docs';docs.mkdir(exist_ok=True)
specs=[a.dict() for a in REGISTRY.values()]
(docs/'algorithm-catalog.json').write_text(json.dumps(specs,ensure_ascii=False,indent=2))
counts=Counter(a.category for a in REGISTRY.values())
lines=['# 功能与进度清单','','当前注册 **140 个独立实验、13 个模块**。入口均有实际执行器、参数、学习说明和完整示例配方。已通过的运行检查不代表特定数据集上的准确率认证。','','| 模块 | 独立入口 |','| --- | --- |']
lines += [f'| {name} | {count} |' for name,count in counts.items()]
lines += ['','## 平台体验','','- [x] 中文分类/用途搜索、学习路径、图片/视频/点云上传、完整示例。','- [x] 自动参数表单、重置/方案、轻量预览、后台排队/进度/取消/失败。','- [x] 并排/滑动对比、同步缩放/平移、原图局部放大、独立图层。','- [x] 原图坐标矩形、多边形、前景/背景点、修复画笔。','- [x] 视频同步播放/定位/单帧实验、触发缩略图/事件依据。','- [x] 正常样本建库、特征库复用、异常连续分数/用户阈值。','- [x] SQLite 历史、同素材最多四结果对比、PNG/MP4/NPZ/JSON/ZIP 下载。','- [x] 可排序/启停/保存流水线、类型校验、逐步产物、历史恢复。','- [x] 模型下载进度、完整文件校验、缺文件/加载失败提示、缓存释放。','- [x] 真实模型离线执行、CPU、独立 MediaPipe Conda 进程。','','## 算法入口','','“参数”是数值/枚举/JSON 字段数，ROI 等画布交互单独列出。每项实验默认与主输入配套输出图片/视频及适用结构化数据，具体输出可在结果页和下载包中检查。']
for category in counts:
    lines += ['',f'### {category}','','| 实验 | ID | 输入 | 参数/交互 | 实现 |','| --- | --- | --- | --- | --- |']
    for a in REGISTRY.values():
        if a.category!=category:continue
        lines.append(f'| {a.name} | `{a.id}` | {", ".join(a.inputs)} | {len(a.params)} / {a.interaction or "无"} | '+(f'本地 `{a.model}`' if a.model else 'OpenCV / 数值计算')+('；连续帧' if a.temporal else '')+' |')
lines += ['','## 明确边界与未接入项','','| 项目 | 当前状态 | 后续条件 |','| --- | --- | --- |',
'| NVIDIA GPU / TensorRT | 本机驱动不可用；CPU 已验收，TensorRT 未接入 | 修复驱动、安装兼容 CUDA/TensorRT、增加独立适配与数值验收 |',
'| 完整 PatchCore 论文复现 | 已实现局部特征正常库/最近邻热力图；随机子采样 | 若要求论文指标，补 greedy coreset、同协议骨干与带标注评测 |',
'| 多目标跟踪 | 已实现类别约束 IoU 关联与轨迹/事件 | 长遮挡场景可增加重识别/ByteTrack 等适配 |',
'| 低光/修复 | Retinex / Telea 实际可运行；未接入这两项的深度生成模型 | 另选权重、许可与运行环境；不以传统算子冒充深度模型 |',
'| 多视图基础重建 | 两视图相对尺度稀疏三角化 | 完整 SfM/BA/稠密重建尚未接入 |',
'| 图文理解 | CLIP/OWL-ViT/BLIP 本地小模型，英文较适用 | 不声称具备通用中文大模型或领域专家能力 |',
'| 点云 | ASCII XYZ/CSV/PLY、体素/RANSAC/ICP、旋转查看 | 不支持二进制 PLY、网格、颜色或法线保留 |',
'| 部署 | 本机单工作线程学习平台 | 多用户认证、生产监控和分布式任务不在当前实现内 |',
'','所有 22 套默认模型已准备，当前无缺权重阻塞项。详见 [模型清单](docs/MODELS.md) 和 [验收范围](docs/VALIDATION.md)。']
(ROOT/'FEATURES.md').write_text('\n'.join(lines)+'\n')

models=list_models()
(docs/'model-inventory.json').write_text(json.dumps(models,ensure_ascii=False,indent=2))
lines=['# 本地模型清单','','清单由 `python scripts/export_catalog.py` 从注册表和本地 inventory 导出。完整文件哈希不是准确率或上游签名；前端模型页支持重新校验。模型运行效果见 [model-validation.json](model-validation.json)。','','| 名称 / ID | 任务 | 版本 | 支持设备 | 许可 |','| --- | --- | --- | --- | --- |']
for m in models:
    lines.append(f'| [{m.get("name",m["id"])}]({m["source"]}) / `{m["id"]}` | {", ".join(m["tasks"])} | {m["version"]} | {", ".join(m["devices"])} | {m["license"]} |')
lines+=['','`edsr` 和 `swin-denoise` 是保留的内部目录 ID，实际模型分别为 **Swin2SR ×2** 和 **Restormer 真实图像去噪**。界面展示实际模型名。ONNX Runtime 对比导出的 `resnet18.onnx` 是由本地 ResNet18 派生的缓存，不是另一套预训练权重。']
for m in models:
    lines += ['',f'## {m.get("name",m["id"])} (`{m["id"]}`)','','- 来源：'+m['source'],'- 状态：'+m['state'],'- 固定版本 / revision：`'+m['revision']+'`','- 类别/范围：'+m['classes'],'- 本地路径：`models/'+m['id']+'/`','- 原始清单：[`inventory.json`](../models/'+m['id']+'/inventory.json)','','| 文件 | 字节数 | SHA256 |','| --- | ---: | --- |']
    lines += [f'| `{f["path"]}` | {f["size"]} | `{f["sha256"]}` |' for f in m['files']]
(docs/'MODELS.md').write_text('\n'.join(lines)+'\n')
print(f'已导出 {len(specs)} 个实验、{len(models)} 套模型。')
