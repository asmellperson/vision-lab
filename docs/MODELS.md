# 本地模型清单

清单由 `python scripts/export_catalog.py` 从注册表和本地 inventory 导出。完整文件哈希不是准确率或上游签名；前端模型页支持重新校验。模型运行效果见 [model-validation.json](model-validation.json)。

| 名称 / ID | 任务 | 版本 | 支持设备 | 许可 |
| --- | --- | --- | --- | --- |
| [resnet18](https://pytorch.org/vision/stable/models/resnet.html) / `resnet18` | classify, anomaly, gradcam, feature_maps, benchmark | IMAGENET1K_V1 | cpu, cuda | BSD-3-Clause (torchvision) |
| [deeplab](https://pytorch.org/vision/stable/models/deeplabv3.html) / `deeplab` | semantic | COCO_WITH_VOC_LABELS_V1 | cpu, cuda | BSD-3-Clause (torchvision) |
| [r3d](https://pytorch.org/vision/stable/models/video.html) / `r3d` | action | KINETICS400_V1 | cpu, cuda | BSD-3-Clause (torchvision) |
| [yolov8n](https://docs.ultralytics.com/models/yolov8/) / `yolov8n` | detect, multi_track, events, sequence | YOLOv8 / assets v8.3.0 | cpu, cuda | AGPL-3.0 / Ultralytics Enterprise |
| [yolov8n-seg](https://docs.ultralytics.com/models/yolov8/) / `yolov8n-seg` | instance | YOLOv8 / assets v8.3.0 | cpu, cuda | AGPL-3.0 / Ultralytics Enterprise |
| [yolov8n-pose](https://docs.ultralytics.com/models/yolov8/) / `yolov8n-pose` | pose | YOLOv8 / assets v8.3.0 | cpu, cuda | AGPL-3.0 / Ultralytics Enterprise |
| [yolov8n-obb](https://docs.ultralytics.com/models/yolov8/) / `yolov8n-obb` | obb | YOLOv8 / assets v8.3.0 | cpu, cuda | AGPL-3.0 / Ultralytics Enterprise |
| [sam2](https://github.com/facebookresearch/sam2) / `sam2` | sam, video_segment | SAM2 Hiera tiny / Ultralytics packaged | cpu, cuda | Apache-2.0 (Meta); Ultralytics adapter AGPL-3.0 |
| [PP-OCRv4 / RapidOCR](https://github.com/RapidAI/RapidOCR) / `rapidocr` | ocr, char_check | rapidocr-onnxruntime 1.4.4 | cpu | Apache-2.0 |
| [depth-anything](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf) / `depth-anything` | depth | download revision locked in inventory.json | cpu, cuda | Apache-2.0 |
| [clip](https://huggingface.co/openai/clip-vit-base-patch32) / `clip` | similarity, text_retrieval | download revision locked in inventory.json | cpu, cuda | MIT |
| [owlvit](https://huggingface.co/google/owlvit-base-patch32) / `owlvit` | grounding | download revision locked in inventory.json | cpu, cuda | Apache-2.0 |
| [blip](https://huggingface.co/Salesforce/blip-image-captioning-base) / `blip` | caption | download revision locked in inventory.json | cpu, cuda | BSD-3-Clause |
| [blip-vqa](https://huggingface.co/Salesforce/blip-vqa-base) / `blip-vqa` | vqa | download revision locked in inventory.json | cpu, cuda | BSD-3-Clause |
| [detr-panoptic](https://huggingface.co/facebook/detr-resnet-50-panoptic) / `detr-panoptic` | panoptic | download revision locked in inventory.json | cpu, cuda | Apache-2.0 |
| [DocLayout-YOLO](https://github.com/opendatalab/DocLayout-YOLO) / `layout` | layout | DocStructBench imgsz1024 / DocLayout-YOLO 0.0.4 | cpu, cuda | AGPL-3.0 |
| [Swin2SR ×2](https://huggingface.co/caidas/swin2SR-classical-sr-x2-64) / `edsr` | superres | download revision locked in inventory.json | cpu, cuda | Apache-2.0 |
| [Restormer 真实去噪](https://github.com/swz30/Restormer) / `swin-denoise` | denoise_dl | Restormer official weights v1.0; configuration/source SHA256 in inventory | cpu, cuda | MIT |
| [restormer](https://github.com/swz30/Restormer) / `restormer` | deblur | Restormer official weights v1.0; configuration/source SHA256 in inventory | cpu, cuda | MIT |
| [U2NetP 前景提取](https://github.com/danielgatis/rembg) / `rmbg` | matting | U2NetP | cpu | MIT (rembg); Apache-2.0 (U2-Net) |
| [face_landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) / `face_landmarker` | face | float16/1 | cpu | Apache-2.0 |
| [hand_landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) / `hand_landmarker` | hand | float16/1 | cpu | Apache-2.0 |

`edsr` 和 `swin-denoise` 是保留的内部目录 ID，实际模型分别为 **Swin2SR ×2** 和 **Restormer 真实图像去噪**。界面展示实际模型名。ONNX Runtime 对比导出的 `resnet18.onnx` 是由本地 ResNet18 派生的缓存，不是另一套预训练权重。

## resnet18 (`resnet18`)

- 来源：https://pytorch.org/vision/stable/models/resnet.html
- 状态：ready
- 固定版本 / revision：`IMAGENET1K_V1`
- 类别/范围：ImageNet-1K
- 本地路径：`models/resnet18/`
- 原始清单：[`inventory.json`](../models/resnet18/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `resnet18.pth` | 46830571 | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` |

## deeplab (`deeplab`)

- 来源：https://pytorch.org/vision/stable/models/deeplabv3.html
- 状态：ready
- 固定版本 / revision：`COCO_WITH_VOC_LABELS_V1`
- 类别/范围：VOC: background, aeroplane, bicycle, bird, boat, bottle, bus, car, cat, chair, cow, diningtable, dog, horse, motorbike, person, pottedplant, sheep, sofa, train, tvmonitor
- 本地路径：`models/deeplab/`
- 原始清单：[`inventory.json`](../models/deeplab/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `deeplab.pth` | 44356159 | `fc3c493d68e89cc31ef488c803d5d7dd2f3190fb570598faa49fef69be8e5e70` |

## r3d (`r3d`)

- 来源：https://pytorch.org/vision/stable/models/video.html
- 状态：ready
- 固定版本 / revision：`KINETICS400_V1`
- 类别/范围：Kinetics-400，运行时导出全部类别
- 本地路径：`models/r3d/`
- 原始清单：[`inventory.json`](../models/r3d/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `r3d.pth` | 133546016 | `b3b3357ead25631ec9c57362ff2128a92d0427e01e2cd184951a44380c3f2e9d` |

## yolov8n (`yolov8n`)

- 来源：https://docs.ultralytics.com/models/yolov8/
- 状态：ready
- 固定版本 / revision：`YOLOv8 / assets v8.3.0`
- 类别/范围：COCO 80 类
- 本地路径：`models/yolov8n/`
- 原始清单：[`inventory.json`](../models/yolov8n/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `yolov8n.pt` | 6549796 | `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36` |

## yolov8n-seg (`yolov8n-seg`)

- 来源：https://docs.ultralytics.com/models/yolov8/
- 状态：ready
- 固定版本 / revision：`YOLOv8 / assets v8.3.0`
- 类别/范围：COCO 80 类
- 本地路径：`models/yolov8n-seg/`
- 原始清单：[`inventory.json`](../models/yolov8n-seg/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `yolov8n-seg.pt` | 7071756 | `a7cd8f929e1903d78a12a48efecab430209f18dc46cb96c3599a5980c63c423c` |

## yolov8n-pose (`yolov8n-pose`)

- 来源：https://docs.ultralytics.com/models/yolov8/
- 状态：ready
- 固定版本 / revision：`YOLOv8 / assets v8.3.0`
- 类别/范围：person / COCO 17 关键点
- 本地路径：`models/yolov8n-pose/`
- 原始清单：[`inventory.json`](../models/yolov8n-pose/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `yolov8n-pose.pt` | 6832633 | `c6fa93dd1ee4a2c18c900a45c1d864a1c6f7aba75d84f91648a30b7fb641d212` |

## yolov8n-obb (`yolov8n-obb`)

- 来源：https://docs.ultralytics.com/models/yolov8/
- 状态：ready
- 固定版本 / revision：`YOLOv8 / assets v8.3.0`
- 类别/范围：DOTA 15 类：plane, ship, storage tank, baseball diamond, tennis court, basketball court, ground track field, harbor, bridge, large vehicle, small vehicle, helicopter, roundabout, soccer ball field, swimming pool
- 本地路径：`models/yolov8n-obb/`
- 原始清单：[`inventory.json`](../models/yolov8n-obb/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `yolov8n-obb.pt` | 6567590 | `fa6e4cd2691f132875c143135affaa66b5d89394ebb1d07d19770a9b6382c1b8` |

## sam2 (`sam2`)

- 来源：https://github.com/facebookresearch/sam2
- 状态：ready
- 固定版本 / revision：`SAM2 Hiera tiny / Ultralytics packaged`
- 类别/范围：类别无关
- 本地路径：`models/sam2/`
- 原始清单：[`inventory.json`](../models/sam2/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `sam2_t.pt` | 78064050 | `94375f988270836169320bd901960c67b5770e8bef3867d70102f01a8b5ca501` |

## PP-OCRv4 / RapidOCR (`rapidocr`)

- 来源：https://github.com/RapidAI/RapidOCR
- 状态：ready
- 固定版本 / revision：`rapidocr-onnxruntime 1.4.4`
- 类别/范围：PP-OCRv4 中文英文；ONNX 内嵌词表
- 本地路径：`models/rapidocr/`
- 原始清单：[`inventory.json`](../models/rapidocr/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `config.yaml` | 1221 | `bf94a1da4cba828e67b1d61e27cee14d9e7da27c9f272e04048a17e41ae97332` |
| `models/ch_PP-OCRv4_det_infer.onnx` | 4745517 | `d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9` |
| `models/ch_PP-OCRv4_rec_infer.onnx` | 10857958 | `48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b` |
| `models/ch_ppocr_mobile_v2.0_cls_infer.onnx` | 585532 | `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c` |

## depth-anything (`depth-anything`)

- 来源：https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf
- 状态：ready
- 固定版本 / revision：`5426e4f0f36572d16453bbda7a8389317b1bef99`
- 类别/范围：相对逆深度
- 本地路径：`models/depth-anything/`
- 原始清单：[`inventory.json`](../models/depth-anything/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 4400 | `319566441daaac0c5ed83e75a8fd19bae0863f3275e23f147c06fe0906edf6fb` |
| `config.json` | 950 | `c56698d3643dde1f83ea2212759e6b31a22b8f827246a36dd007ee8a22b3ff75` |
| `model.safetensors` | 99173660 | `3152477ce0d8d6978d76b995120de97cb5b928701fd0f817769f59e249a16b70` |
| `preprocessor_config.json` | 775 | `d41175c0d889477ca8fc67191e540faef14baf6275157b3fdecf78469e6bbf84` |

## clip (`clip`)

- 来源：https://huggingface.co/openai/clip-vit-base-patch32
- 状态：ready
- 固定版本 / revision：`3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`
- 类别/范围：开放词汇英文图文相似度
- 本地路径：`models/clip/`
- 原始清单：[`inventory.json`](../models/clip/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 7942 | `8f0e8c678e0afe5f384f3bf8a6694c1cb53c41e52f86277967b6c5354cb0f9f4` |
| `config.json` | 4186 | `b575ef3c36f2a057fa19e221650105052d61cc9c1a972ec15019c6261ec98770` |
| `merges.txt` | 524657 | `f526393189112391ce6f9795d4695f704121ce452c3aad1f5335cc41337eba85` |
| `preprocessor_config.json` | 316 | `910e70b3956ac9879ebc90b22fb3bc8a75b6a0677814500101a4c072bd7857bd` |
| `pytorch_model.bin` | 605247071 | `a63082132ba4f97a80bea76823f544493bffa8082296d62d71581a4feff1576f` |
| `special_tokens_map.json` | 389 | `f8c0d6c39aee3f8431078ef6646567b0aba7f2246e9c54b8b99d55c22b707cbf` |
| `tokenizer.json` | 2224041 | `b556ac8c99757ffb677208af34bc8c6721572114111a6e0aaf5fa69ff0b8d842` |
| `tokenizer_config.json` | 592 | `34b7336e4bee12e0a9730eaf5189f582ef3c3eea5027f65730e5717256755aad` |
| `vocab.json` | 862328 | `5047b556ce86ccaf6aa22b3ffccfc52d391ea4accdab9c2f2407da5b742d4363` |

## owlvit (`owlvit`)

- 来源：https://huggingface.co/google/owlvit-base-patch32
- 状态：ready
- 固定版本 / revision：`cbc355fb364588351c5d51c7f74465e8e7ec6f72`
- 类别/范围：开放词汇英文检测
- 本地路径：`models/owlvit/`
- 原始清单：[`inventory.json`](../models/owlvit/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 5146 | `a16c707494da894773e85c1be976ae605a7b3a3ce92cf9ed277623dd25f236bf` |
| `config.json` | 4418 | `b5934e0d2933194b8a85f93674e577feaa1a1ba2dc1d143b2d5e5305ff7a9d7c` |
| `merges.txt` | 524619 | `9fd691f7c8039210e0fced15865466c65820d09b63988b0174bfe25de299051a` |
| `model.safetensors` | 612983940 | `4dbe0399f0b7d7c8dddf1535a98769cc30743bebc877aea681998c8d984ce52b` |
| `preprocessor_config.json` | 392 | `2010d320cd2c68a8bb1de69aaa8f89daf173ef17cc22a30e4baf44b2f0e9bb6e` |
| `special_tokens_map.json` | 460 | `f118ab3a983206e4f32583448de6bd6aae4ee21869135cef1f5848a753cdaab6` |
| `tokenizer_config.json` | 775 | `da35aceebeda2adf44094a5867940b09379323b9390fa9197b57044e106bfb6e` |
| `vocab.json` | 1059962 | `e089ad92ba36837a0d31433e555c8f45fe601ab5c221d4f607ded32d9f7a4349` |

## blip (`blip`)

- 来源：https://huggingface.co/Salesforce/blip-image-captioning-base
- 状态：ready
- 固定版本 / revision：`82a37760796d32b1411fe092ab5d4e227313294b`
- 类别/范围：英文图像描述
- 本地路径：`models/blip/`
- 原始清单：[`inventory.json`](../models/blip/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 6359 | `eae8c14a066e611a51a803cccb35c892bbd78d1ca7db45fbb06f5fb79bff7ad1` |
| `config.json` | 4563 | `f7846f82f4e2c4a2ccbab9ae8b0e44873540a271a76a1288effd078180c13a82` |
| `preprocessor_config.json` | 287 | `065c10ec97edc5081fbd9655b3d9d25e2647ea6d5dab873325e88eed12d80a7d` |
| `pytorch_model.bin` | 989820849 | `d6638651a5526cc2ede56f2b5104d6851b0755816d220e5e046870430180c767` |
| `special_tokens_map.json` | 125 | `b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3` |
| `tokenizer.json` | 711396 | `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66` |
| `tokenizer_config.json` | 506 | `5c7f96096284c55e539eff95f4451c19efc34258ddb975a4400d052b77301e5e` |
| `vocab.txt` | 231508 | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` |

## blip-vqa (`blip-vqa`)

- 来源：https://huggingface.co/Salesforce/blip-vqa-base
- 状态：ready
- 固定版本 / revision：`787b3d35d57e49572baabd22884b3d5a05acf072`
- 类别/范围：英文视觉问答
- 本地路径：`models/blip-vqa/`
- 原始清单：[`inventory.json`](../models/blip-vqa/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 5459 | `03e051ff0a0461a06892f90ac0e10bd2eebc2dd47c3ffa65092b31576aa37e4c` |
| `config.json` | 4559 | `689a09e2a9980b7fcad329271c032254fde23b1ee7a90c67b003e1867dc9c098` |
| `model.safetensors` | 1538800584 | `33786eed34def0c95fa948128cb4386be9b9219aa2c2e25f1c9c744692121bb7` |
| `preprocessor_config.json` | 445 | `0aa66e2e9ac3ea3b5cd4388c35072e22db4e1cc1f96c7872bed07749c712ade1` |
| `special_tokens_map.json` | 125 | `b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3` |
| `tokenizer.json` | 711396 | `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66` |
| `tokenizer_config.json` | 592 | `48d1c9120fe61c9741286050189b030e936f23797a65fd0a179078661e1c43bb` |
| `vocab.txt` | 231508 | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` |

## detr-panoptic (`detr-panoptic`)

- 来源：https://huggingface.co/facebook/detr-resnet-50-panoptic
- 状态：ready
- 固定版本 / revision：`d53b52a799403a8867920f82c869e40732b47037`
- 类别/范围：COCO thing/stuff 类别由模型配置导出
- 本地路径：`models/detr-panoptic/`
- 原始清单：[`inventory.json`](../models/detr-panoptic/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 5851 | `85e8d1dfa657c91be3f6a446d7baac0b786f0806aa6b086ee22236072c8e22f5` |
| `config.json` | 11607 | `626a96c954c61d36157216f8d757d27f1d277bc7e4e8edcbe388acaf43fe443f` |
| `preprocessor_config.json` | 289 | `5cfff969435e7a277dd20a91a8d5b61eed1902d68dbf545a3d7d627e19b354af` |
| `pytorch_model.bin` | 172245279 | `3f8024c4744402adf5ebba3be495c91e5af388d73fb32f1e0a93c053767abeca` |

## DocLayout-YOLO (`layout`)

- 来源：https://github.com/opendatalab/DocLayout-YOLO
- 状态：ready
- 固定版本 / revision：`DocStructBench imgsz1024 / DocLayout-YOLO 0.0.4`
- 类别/范围：title, plain text, abandon, figure, figure_caption, table, table_caption, table_footnote, isolate_formula, formula_caption
- 本地路径：`models/layout/`
- 原始清单：[`inventory.json`](../models/layout/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `doclayout.pt` | 40709302 | `9a2ee0220fe3d9ad31b47e1d9f1282f46959a54e4618fce9cffcc9715b8286e2` |

## Swin2SR ×2 (`edsr`)

- 来源：https://huggingface.co/caidas/swin2SR-classical-sr-x2-64
- 状态：ready
- 固定版本 / revision：`cee1c923c6a37361c6e5650b65dcf4be821e5d52`
- 类别/范围：Swin2SR x2，非 EDSR
- 本地路径：`models/edsr/`
- 原始清单：[`inventory.json`](../models/edsr/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `README.md` | 642 | `9186aaf5bf94b0adb71532ad70368320e8134815fa026827c8f0e4920dc6886c` |
| `config.json` | 772 | `11179bdfd48394977f7fe6177b3a87d9c2c6fa2a67a4b3a7376229ca407f0376` |
| `model.safetensors` | 48460660 | `a515955815ab6dba3a9331d8c75db13a5166a5ffbcebf1a95ab676a5656ac4fb` |
| `preprocessor_config.json` | 152 | `cbc36266fcc93d5bc1e9ca69bcc648ae9d268918ad14cd3507216740f129cc4d` |

## Restormer 真实去噪 (`swin-denoise`)

- 来源：https://github.com/swz30/Restormer
- 状态：ready
- 固定版本 / revision：`download revision locked in inventory.json`
- 类别/范围：真实图像去噪，SIDD
- 本地路径：`models/swin-denoise/`
- 原始清单：[`inventory.json`](../models/swin-denoise/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `LICENSE` | 1090 | `2b93776512924bc095ec5d97a79d76cf1ab401ae641d1ae1f46e94f1c53a2e59` |
| `config.yml` | 2941 | `697bf6402c58d22e1f7314f1f87fbed2a5de6f5f912ae9dcc96bba203b3b5b32` |
| `restormer_arch.py` | 11428 | `3be243fa3c8e2cb2c9459eeac062b04d6084dbcc328292dae1c3e52ba6f7434a` |
| `weights.pth` | 104611957 | `4cae18bed8a291b9a5deeeab48756bbe6f61fcf7f31a4cca0969b24608601387` |

## restormer (`restormer`)

- 来源：https://github.com/swz30/Restormer
- 状态：ready
- 固定版本 / revision：`download revision locked in inventory.json`
- 类别/范围：单图运动去模糊
- 本地路径：`models/restormer/`
- 原始清单：[`inventory.json`](../models/restormer/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `LICENSE` | 1090 | `2b93776512924bc095ec5d97a79d76cf1ab401ae641d1ae1f46e94f1c53a2e59` |
| `config.yml` | 2974 | `8f4403ec761973f1c0677fae07841df3935075cea2f3871932d3cd26d1b16e73` |
| `restormer_arch.py` | 11428 | `3be243fa3c8e2cb2c9459eeac062b04d6084dbcc328292dae1c3e52ba6f7434a` |
| `weights.pth` | 104700429 | `194e38fb5b607c9dc5a5b3e08e65b2e79ee2bf0ef5048e0612f6b2ff2f79da31` |

## U2NetP 前景提取 (`rmbg`)

- 来源：https://github.com/danielgatis/rembg
- 状态：ready
- 固定版本 / revision：`U2NetP`
- 类别/范围：显著前景；非精细发丝抠图
- 本地路径：`models/rmbg/`
- 原始清单：[`inventory.json`](../models/rmbg/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `u2netp.onnx` | 4574861 | `309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8` |

## face_landmarker (`face_landmarker`)

- 来源：https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
- 状态：ready
- 固定版本 / revision：`float16/1`
- 类别/范围：478 面部点
- 本地路径：`models/face_landmarker/`
- 原始清单：[`inventory.json`](../models/face_landmarker/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `face_landmarker.task` | 3758596 | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` |

## hand_landmarker (`hand_landmarker`)

- 来源：https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker
- 状态：ready
- 固定版本 / revision：`float16/1`
- 类别/范围：每手 21 点
- 本地路径：`models/hand_landmarker/`
- 原始清单：[`inventory.json`](../models/hand_landmarker/inventory.json)

| 文件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `hand_landmarker.task` | 7819105 | `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1` |
