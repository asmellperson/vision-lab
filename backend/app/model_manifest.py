"""模型来源与任务契约；下载后 inventory.json 记录固定 revision、文件大小及 SHA256。"""
def entry(id, tasks, kind, source, license, classes, **kw):
    return dict(id=id,tasks=tasks,kind=kind,source=source,license=license,classes=classes,devices=['cpu','cuda'],version=kw.pop('version','download revision locked in inventory.json'),**kw)

YOLO='https://github.com/ultralytics/assets/releases/download/v8.3.0/'
MODEL_LIST=[
    entry('resnet18',['classify','anomaly','gradcam','feature_maps','benchmark'],'torchvision','https://pytorch.org/vision/stable/models/resnet.html','BSD-3-Clause (torchvision)','ImageNet-1K',files={'resnet18.pth':'https://download.pytorch.org/models/resnet18-f37072fd.pth'},version='IMAGENET1K_V1'),
    entry('deeplab',['semantic'],'torchvision','https://pytorch.org/vision/stable/models/deeplabv3.html','BSD-3-Clause (torchvision)','VOC: background, aeroplane, bicycle, bird, boat, bottle, bus, car, cat, chair, cow, diningtable, dog, horse, motorbike, person, pottedplant, sheep, sofa, train, tvmonitor',files={'deeplab.pth':'https://download.pytorch.org/models/deeplabv3_mobilenet_v3_large-fc3c493d.pth'},version='COCO_WITH_VOC_LABELS_V1'),
    entry('r3d',['action'],'torchvision','https://pytorch.org/vision/stable/models/video.html','BSD-3-Clause (torchvision)','Kinetics-400，运行时导出全部类别',files={'r3d.pth':'https://download.pytorch.org/models/r3d_18-b3b3357e.pth'},version='KINETICS400_V1'),
    *[entry(id,tasks,'ultralytics','https://docs.ultralytics.com/models/yolov8/','AGPL-3.0 / Ultralytics Enterprise',classes,files={id+'.pt':YOLO+id+'.pt'},version='YOLOv8 / assets v8.3.0') for id,tasks,classes in [
        ('yolov8n',['detect','multi_track','events','sequence'],'COCO 80 类'),('yolov8n-seg',['instance'],'COCO 80 类'),('yolov8n-pose',['pose'],'person / COCO 17 关键点'),('yolov8n-obb',['obb'],'DOTA 15 类：plane, ship, storage tank, baseball diamond, tennis court, basketball court, ground track field, harbor, bridge, large vehicle, small vehicle, helicopter, roundabout, soccer ball field, swimming pool')]],
    entry('sam2',['sam','video_segment'],'sam','https://github.com/facebookresearch/sam2','Apache-2.0 (Meta); Ultralytics adapter AGPL-3.0','类别无关',files={'sam2_t.pt':YOLO+'sam2_t.pt'},version='SAM2 Hiera tiny / Ultralytics packaged'),
    entry('rapidocr',['ocr','char_check'],'rapidocr','https://github.com/RapidAI/RapidOCR','Apache-2.0','PP-OCRv4 中文英文；ONNX 内嵌词表',version='rapidocr-onnxruntime 1.4.4'),
    entry('depth-anything',['depth'],'hf','https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf','Apache-2.0','相对逆深度',repo='depth-anything/Depth-Anything-V2-Small-hf'),
    entry('clip',['similarity','text_retrieval'],'hf','https://huggingface.co/openai/clip-vit-base-patch32','MIT','开放词汇英文图文相似度',repo='openai/clip-vit-base-patch32'),
    entry('owlvit',['grounding'],'hf','https://huggingface.co/google/owlvit-base-patch32','Apache-2.0','开放词汇英文检测',repo='google/owlvit-base-patch32'),
    entry('blip',['caption'],'hf','https://huggingface.co/Salesforce/blip-image-captioning-base','BSD-3-Clause','英文图像描述',repo='Salesforce/blip-image-captioning-base'),
    entry('blip-vqa',['vqa'],'hf','https://huggingface.co/Salesforce/blip-vqa-base','BSD-3-Clause','英文视觉问答',repo='Salesforce/blip-vqa-base'),
    entry('detr-panoptic',['panoptic'],'hf','https://huggingface.co/facebook/detr-resnet-50-panoptic','Apache-2.0','COCO thing/stuff 类别由模型配置导出',repo='facebook/detr-resnet-50-panoptic'),
    entry('layout',['layout'],'doclayout','https://github.com/opendatalab/DocLayout-YOLO','AGPL-3.0','title, plain text, abandon, figure, figure_caption, table, table_caption, table_footnote, isolate_formula, formula_caption',files={'doclayout.pt':'https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench/resolve/main/doclayout_yolo_docstructbench_imgsz1024.pt'},version='DocStructBench imgsz1024 / DocLayout-YOLO 0.0.4'),
    entry('edsr',['superres'],'hf','https://huggingface.co/caidas/swin2SR-classical-sr-x2-64','Apache-2.0','Swin2SR x2，非 EDSR',repo='caidas/swin2SR-classical-sr-x2-64'),
    entry('swin-denoise',['denoise_dl'],'restormer','https://github.com/swz30/Restormer','MIT','真实图像去噪，SIDD',files={'weights.pth':'https://github.com/swz30/Restormer/releases/download/v1.0/real_denoising.pth','restormer_arch.py':'https://raw.githubusercontent.com/swz30/Restormer/main/basicsr/models/archs/restormer_arch.py','LICENSE':'https://raw.githubusercontent.com/swz30/Restormer/main/LICENSE.md'}),
    entry('restormer',['deblur'],'restormer','https://github.com/swz30/Restormer','MIT','单图运动去模糊',files={'weights.pth':'https://github.com/swz30/Restormer/releases/download/v1.0/motion_deblurring.pth','restormer_arch.py':'https://raw.githubusercontent.com/swz30/Restormer/main/basicsr/models/archs/restormer_arch.py','LICENSE':'https://raw.githubusercontent.com/swz30/Restormer/main/LICENSE.md'}),
    entry('rmbg',['matting'],'onnx','https://github.com/danielgatis/rembg','MIT (rembg); Apache-2.0 (U2-Net)','显著前景；非精细发丝抠图',files={'u2netp.onnx':'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx'},version='U2NetP'),
    *[entry(id,[task],'mediapipe','https://ai.google.dev/edge/mediapipe/solutions/vision/'+id,'Apache-2.0','478 面部点' if task=='face' else '每手 21 点',files={id+'.task':f'https://storage.googleapis.com/mediapipe-models/{id}/{id}/float16/1/{id}.task'},version='float16/1',devices_note='独立 MediaPipe CPU 工作进程') for id,task in [('face_landmarker','face'),('hand_landmarker','hand')]],
]
MODELS={x['id']:x for x in MODEL_LIST}
MODELS['swin-denoise']['files']['config.yml']='https://raw.githubusercontent.com/swz30/Restormer/main/Denoising/Options/RealDenoising_Restormer.yml'
MODELS['restormer']['files']['config.yml']='https://raw.githubusercontent.com/swz30/Restormer/main/Motion_Deblurring/Options/Deblurring_Restormer.yml'
for id in ['rapidocr','rmbg','face_landmarker','hand_landmarker']:
    MODELS[id]['devices']=['cpu']
for id in ['swin-denoise','restormer']:
    MODELS[id]['version']='Restormer official weights v1.0; configuration/source SHA256 in inventory'
for id,name in {'edsr':'Swin2SR ×2','swin-denoise':'Restormer 真实去噪','rmbg':'U2NetP 前景提取','layout':'DocLayout-YOLO','rapidocr':'PP-OCRv4 / RapidOCR'}.items():
    MODELS[id]['name']=name
