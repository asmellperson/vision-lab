#!/usr/bin/env python3
"""Build two editable DOCX books from the requested professional-docx template."""
from __future__ import annotations
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parent.parent
SKILL = Path('/usr/zyy/Fuda_CVPreject_V3/.agents/skills/professional-docx')
sys.path.insert(0, str(SKILL / 'scripts'))
from docx_utils import clear_body_keep_sections, add_toc, set_update_fields

REFERENCES = [
 ('R01','OpenCV 官方教程：传统视觉、几何与视频','https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html'),
 ('R02','Torchvision ResNet：架构与模型说明','https://docs.pytorch.org/vision/stable/models/resnet.html'),
 ('R03','Ultralytics YOLOv8：任务与模型说明','https://docs.ultralytics.com/models/yolov8/'),
 ('R04','YOLOv8 v8.3.0 架构配置','https://github.com/ultralytics/ultralytics/blob/v8.3.0/ultralytics/cfg/models/v8/yolov8.yaml'),
 ('R05','DeepLabV3 MobileNetV3-Large 官方说明','https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.segmentation.deeplabv3_mobilenet_v3_large.html'),
 ('R06','DETR 官方实现','https://github.com/facebookresearch/detr'),
 ('R07','SAM 2 论文','https://arxiv.org/abs/2408.00714'),
 ('R08','SAM 2 官方实现','https://github.com/facebookresearch/sam2'),
 ('R09','MediaPipe Face Landmarker 官方说明','https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker'),
 ('R10','MediaPipe Hand Landmarker 官方说明','https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker'),
 ('R11','PP-OCRv4 官方技术说明','https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/doc/doc_ch/PP-OCRv4_introduction.md'),
 ('R12','DocLayout-YOLO 官方实现','https://github.com/opendatalab/DocLayout-YOLO'),
 ('R13','CLIP 论文','https://arxiv.org/abs/2103.00020'),
 ('R14','OWL-ViT 论文','https://arxiv.org/abs/2205.06230'),
 ('R15','BLIP 论文','https://arxiv.org/abs/2201.12086'),
 ('R16','Depth Anything V2 论文','https://arxiv.org/abs/2406.09414'),
 ('R17','Swin2SR 论文','https://arxiv.org/abs/2209.11345'),
 ('R18','Swin2SR 官方实现','https://github.com/mv-lab/swin2sr'),
 ('R19','Restormer 论文','https://arxiv.org/abs/2111.09881'),
 ('R20','Restormer 官方实现','https://github.com/swz30/Restormer'),
 ('R21','U2-Net 官方实现','https://github.com/xuebinqin/U-2-Net'),
 ('R22','Torchvision R3D18 官方说明','https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.video.r3d_18.html'),
 ('R23','PatchCore 官方实现（用于对照教学版差异）','https://github.com/amazon-science/patchcore-inspection'),
]

FOUNDATIONS = [
 ('读公式前先明确量的含义',
  '本书 I 表示图像强度或颜色向量，M 表示掩膜，H/W/C 表示高、宽、通道数；卷积核中的 k 与聚类数 K 依章节另作解释。Σ 表示求和，||·||₂ 是欧氏范数，1[条件] 在条件成立时取 1，ε 是避免除零的小量。公式是理论或教学表达；凡项目存在截断、归一化、简化或不同配置，正文另行说明。',
  '一条公式要回答四件事：输入是什么、输出是什么、变量单位是什么、什么条件下成立。例如 Z=fB/d 要求校正双目、像素焦距与有效视差；仅背公式而忽略这些条件，计算结果可能没有物理意义。'),
 ('先分清图像、标签与可视化',
  '普通图像数值描述编码颜色，类别标签数值只是类别编号，深度与距离数组则有自己的量纲。彩色热图通常经过归一化和色表映射，同一个红色在不同图片中可能代表不同原始值。实验应同时记录输入、参数、原始数组和显示图，不从显示颜色直接推导测量结论。',
  'uint8 只能表示 0–255，算术前先决定是否需要有符号或浮点类型。裁剪、取绝对值、阈值和整数转换都可能不可逆。图像坐标以左上角为原点，数组使用先行后列，所有 ROI、提示点和检测结果都要确认处于哪张图的坐标系。'),
 ('从滤波到分割：信号与决策是两步',
  '滤波估计局部信号，梯度量化变化，阈值才把连续数值转为离散决策。增强后的噪点更明显不等于出现新缺陷，平滑后边缘更完整也不等于尺寸更准确。选择参数要参照噪声尺度、目标最小结构和允许测量误差。',
  '建立小型对照实验：固定素材，只改一个参数，记录目标保留、误检、边界位置与耗时。需要比较算法时保持分辨率、预处理及评价口径一致；不要为每个方法挑选不同的最有利输入。'),
 ('神经网络的五段数据流',
  '预处理定义模型实际看到的输入；backbone 提取视觉特征；neck 或 decoder 融合尺度与恢复空间；head 将特征映射为任务输出；后处理把输出变成可用结果。不同架构可以省略某段或让其职责重叠，但这五个问题始终有助于阅读模型。',
  '分类头输出整图 logits；检测头增加框；语义头保留每像素类别竞争；实例头区分同类对象；语言解码头逐 token 生成文本。网络训练损失、推理分数、用户阈值是三个不同概念，不能把任何输出都称为经过校准的概率。'),
 ('卷积、残差与尺寸变化',
  '卷积输出尺寸可写为 floor((H+2p−d(k−1)−1)/s+1)，其中 p 为 padding、d 为 dilation、k 为核宽、s 为 stride。参数量与输入输出通道、核面积有关；逐通道卷积先独立处理通道，再用 1×1 混合，可减少计算。',
  '残差连接直接相加，要求张量尺寸相容；拼接则增加通道维，需要后续投影。下采样扩大感受野并节省计算，但细小对象可能丢失。U 形跳接把浅层空间细节送回解码器，特征金字塔则在多个尺度交换语义与位置。'),
 ('注意力、token 与恢复网络',
  '标准注意力可写为 softmax(QKᵀ/√d)V。Q 指定查询，K 用于匹配，V 提供聚合内容；多头让不同子空间学习不同关系。图像切为 patch token 后仍需位置编码，否则仅集合式比较无法充分表达位置。',
  '全局空间注意力的矩阵随 token 数平方增长。Swin 类在窗口内计算并移动窗口建立跨区联系；Restormer 的 MDTA 主要建立通道间注意力，计算对象不同。CLIP 独立编码两种模态后比较向量，BLIP 则在交叉注意力中让文本读取图像，两者不能只因都含 Transformer 就视为同一架构。'),
 ('训练、推理与实验边界',
  '本项目的深度学习入口主要运行已训练权重，本书讨论训练目标是为解释架构，不表示平台在每次实验中重新训练网络。eval() 改变 BatchNorm、Dropout 等行为；no_grad()/inference_mode() 控制梯度记录；Grad-CAM 需要梯度，但网络仍可处于 eval 模式。',
  '训练集拟合、独立验证和上线分布是不同层次。正常样本库、阈值或超参数若使用测试集调过，就不能再把该测试集结果当完全独立证据。模型 ID 只是资源名称，以本地加载代码和配置确定真正架构。'),
 ('怎样使用两册进行学习练习',
  '先阅读一项原理，用自己的话画出输入到输出流程，再手算公式中的一个小例子，并在平台运行建议实验。合上学习册，按题号作答，最后到答案册对照。答案给出关键结论和理由，不要求逐字背诵；若采用不同但成立的假设，应说明前提。',
  '每题可自评 0–3 分：0 分无法回答，1 分只记住结论，2 分说明机制，3 分同时说明边界或项目实现差异。每算法满分 18 分。算法 ID 与题号在两册保持一致，即使排版页码不同也可直接定位。'),
]

def parse_entries():
    catalog = {x['id']: x for x in json.loads((ROOT/'docs/algorithm-catalog.json').read_text())}
    lessons = json.loads((HERE/'project-lessons.json').read_text())
    entries=[]
    for path in sorted(HERE.glob('[0-9][0-9]-*.txt')):
        for block in path.read_text().split('@@ ')[1:]:
            lines=block.strip().splitlines(); key=lines.pop(0).strip()
            theory=[]; formula=[]; experiment=[]; qa=[]
            for line in lines:
                if line.startswith('= '): formula.append(line[2:])
                elif line.startswith('> '): experiment.append(line[2:])
                elif line.startswith('? '):
                    q,a=line[2:].split('|',1);qa.append({'question':q,'answer':a})
                elif line.strip(): theory.append(line)
            assert len(qa)==6,(key,len(qa))
            assert all(len(q['answer'])>=18 for q in qa),key
            assert theory and formula and experiment,key
            entries.append({'number':len(entries)+1,**catalog[key], 'lesson':lessons[key], 'theory':theory,'formula':formula,'experiment':experiment,'qa':qa})
    assert len(entries)==140 and len({e['id'] for e in entries})==140
    assert {e['id'] for e in entries}==set(catalog)
    architectures={}
    for block in (HERE/'architectures.txt').read_text().split('@@ ')[1:]:
        lines=block.strip().splitlines();key=lines[0]
        architectures[key]={'number':len(architectures)+1,'title':lines[1],'flow':lines[2][2:],'blocks':lines[3:-1],'source':lines[-1]}
    assert len(architectures)==22
    for e in entries:
        if e['model']: assert e['model'] in architectures,e['id']
    return entries,architectures

def set_style(style,size=12,bold=False,indent=True):
    style.font.name='Times New Roman';style.font.size=Pt(size);style.font.bold=bold
    style.font.color.rgb=RGBColor(0,0,0)
    rf=style.element.get_or_add_rPr().get_or_add_rFonts()
    rf.set(qn('w:eastAsia'),'Noto Sans CJK SC' if bold else 'Noto Serif CJK SC')
    f=style.paragraph_format;f.line_spacing=1.5;f.space_before=Pt(0);f.space_after=Pt(4)
    f.first_line_indent=Pt(24) if indent else Pt(0);f.widow_control=True
    f.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY

def new_document(title,subtitle):
    doc=Document(SKILL/'assets/report-template.docx')
    clear_body_keep_sections(doc)
    for name,size,bold,indent in [('Normal',12,False,True),('Title',24,True,False),('Subtitle',14,False,False),('Heading 1',16,True,False),('Heading 2',14,True,False),('Heading 3',12,True,False),('Caption',10.5,False,False)]:
        set_style(doc.styles[name],size,bold,indent)
    for name,size,bold,indent in [('Meta',10,False,False),('Formula',11,False,False),('Question',12,False,False),('Answer',12,False,True),('SmallText',9,False,False),('ModelBlock',11,False,True),('TocLabel',16,True,False),('Reference',9.5,False,False),('ReferenceIntro',10.5,False,True)]:
        style=doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH) if name not in doc.styles else doc.styles[name]
        style.base_style=doc.styles['Normal'];set_style(style,size,bold,indent)
    for name in ['Heading 1','Heading 2','Heading 3']:
        doc.styles[name].paragraph_format.keep_with_next=True
        doc.styles[name].paragraph_format.space_before=Pt(10)
        doc.styles[name].paragraph_format.space_after=Pt(6)
    doc.styles['Question'].paragraph_format.space_after=Pt(5)
    doc.styles['ModelBlock'].paragraph_format.line_spacing=1.4
    doc.styles['SmallText'].paragraph_format.line_spacing=1.2
    doc.styles['Formula'].paragraph_format.line_spacing=1.35
    doc.styles['Formula'].paragraph_format.left_indent=Cm(.35)
    doc.styles['Formula'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
    for name in ['TOC 1','TOC 2']:
        style=doc.styles[name] if name in doc.styles else doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        set_style(style,12,False,False)
        style.paragraph_format.line_spacing=1.3
        style.paragraph_format.space_after=Pt(2)
    for name,spacing,after in [('Reference',1.0,2),('ReferenceIntro',1.3,5)]:
        fmt=doc.styles[name].paragraph_format
        fmt.line_spacing=spacing;fmt.space_after=Pt(after)
        fmt.alignment=WD_ALIGN_PARAGRAPH.LEFT
    # Use installed Song-style/Hei-style CJK fonts to make both DOCX and PDF predictable.
    for sec in doc.sections:
        sec.page_width=Cm(21);sec.page_height=Cm(29.7)
        sec.top_margin=Cm(2.54);sec.bottom_margin=Cm(2.54);sec.left_margin=Cm(3);sec.right_margin=Cm(2.6)
        sec.header_distance=Cm(1.2);sec.footer_distance=Cm(1.2)
        hp=sec.header.paragraphs[0];hp.text='Vision Lab  ·  计算机视觉算法学习系列';hp.style=doc.styles['SmallText'];hp.alignment=WD_ALIGN_PARAGRAPH.CENTER
        sec.footer.paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
    p=doc.add_paragraph('VISION LAB',style='Subtitle');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(95)
    p=doc.add_paragraph(title,style='Title');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(25)
    p=doc.add_paragraph(subtitle,style='Subtitle');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(15)
    p=doc.add_paragraph('140 个算法实验 · 13 个模块 · 每算法 6 题',style='Meta');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(25)
    p=doc.add_paragraph('依据当前项目代码与模型配置编写\n编写日期：2026 年 9 月 30 日',style='Meta');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(65)
    doc.add_page_break()
    p=doc.add_paragraph('目录',style='TocLabel')
    p=doc.add_paragraph();add_toc(p,levels='1-2');doc.add_page_break()
    doc.core_properties.title=title;doc.core_properties.subject=subtitle;doc.core_properties.author='Vision Lab 学习资料'
    set_update_fields(doc)
    return doc

def heading(doc,text,level=1,new_page=False):
    p=doc.add_paragraph(text,style=f'Heading {level}')
    p.paragraph_format.keep_with_next=True
    if new_page:p.paragraph_format.page_break_before=True
    return p

def para(doc,text,style=None):
    p=doc.add_paragraph(text,style=style)
    p.paragraph_format.widow_control=True
    return p

def hyperlink(p,text,url):
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');rp=OxmlElement('w:rPr');u=OxmlElement('w:u');u.set(qn('w:val'),'single');rp.append(u);r.append(rp)
    t=OxmlElement('w:t');t.text=text;r.append(t);h.append(r);p._p.append(h)

def make_diagrams(architectures):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import FancyBboxPatch
    font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    dest=HERE/'figures';dest.mkdir(exist_ok=True)
    for key,a in architectures.items():
        labels=[x.strip() for x in a['flow'].split('→')]
        fig,ax=plt.subplots(figsize=(10,3.0));ax.set(xlim=(0,10),ylim=(0,3));ax.axis('off')
        # Numbered serpentine flow, maximum four nodes per row.
        n=len(labels);cols=(n+1)//2;pos=[]
        bw=min(2.65,9.4/cols-.25)
        for i,label in enumerate(labels):
            row=i//cols;col=i%cols
            if row:col=cols-1-col
            x=.3+col*(9.4/cols);y=1.72 if row==0 else .30
            pos.append((x+bw/2,y+.38))
            ax.add_patch(FancyBboxPatch((x,y),bw,.76,boxstyle='round,pad=0.02',fc='#f3f3f3',ec='#303030',lw=1))
            # Explicit wrapping to prevent long Chinese/Latin labels overflowing.
            chunks=[];line='';width=0
            for ch in label:
                cw=1 if ord(ch)>255 else .55
                if width+cw>bw*5.0 and line:chunks.append(line);line='';width=0
                line+=ch;width+=cw
            if line:chunks.append(line)
            ax.text(x+bw/2,y+.40,f'{i+1}. '+ '\n'.join(chunks),ha='center',va='center',fontproperties=font,fontsize=10.3)
        for i in range(n-1):
            x1,y1=pos[i];x2,y2=pos[i+1]
            if abs(y1-y2)<.1:
                sign=1 if x2>x1 else -1;start=(x1+sign*bw/2+.03*sign,y1);end=(x2-sign*bw/2-.04*sign,y2)
            else:start=(x1,y1-.41);end=(x2,y2+.42)
            ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#333333','lw':1.4})
        fig.savefig(dest/f'{key}.png',dpi=170,bbox_inches='tight',pad_inches=.10,facecolor='white');plt.close(fig)

def add_references(doc):
    heading(doc,'资料来源与核对说明',1,True)
    para(doc,'本书范围由 docs/algorithm-catalog.json 的 140 个入口确定，编号按本书模块顺序排列，与算法 ID 一起作为两册定位键。通俗实验说明参考项目 frontend/src/learning/lessons.ts；深入讲解、问题和答案为本次新增编写。',style='ReferenceIntro')
    para(doc,'项目行为依据 backend/app/algorithms/classical.py、common.py、special.py、teaching.py、backend/app/inference.py、models.py、video.py，以及 docs/MODELS.md、docs/EXPERIMENTS.md。模型维度优先核对本地 config.json / config.yml，避免把模型家族的其他版本误作当前实现。',style='ReferenceIntro')
    para(doc,'下列为官方资料、论文与实现的延伸阅读入口（访问核对日期：2026-09-30）。架构专题中的 R 编号对应这里的链接。通用教学推导与本地实现说明应结合阅读；论文报告的实验性能不自动属于本项目。',style='ReferenceIntro')
    for rid,title,url in REFERENCES:
        p=para(doc,f'{rid}  ',style='Reference');hyperlink(p,title,url)
    para(doc,'符号采用可编辑的文本公式；图示为本次按模块关系绘制的教学示意，不是逐算子计算图。中文正文采用本机可用的思源宋体风格字体，标题采用思源黑体风格字体，以保持导出稳定。',style='Reference')

def build():
    entries,architectures=parse_entries()
    make_diagrams(architectures)
    guide=new_document('计算机视觉 140 算法学习文档','原理详解 · 模型架构 · 实验方法 · 840 道配套练习')
    answers=new_document('计算机视觉 140 算法练习参考答案','独立答案册 · 840 题逐题解析')
    heading(guide,'学习方法与共同基础')
    para(guide,'阅读范围：当前 Vision Lab 的 140 个算法实验入口，而非 140 篇互不相关的论文。有些入口共享底层算法，例如角度、间隙与综合测量，但本书仍逐项说明它们的不同测量对象和易错点。')
    for title,*texts in FOUNDATIONS:
        heading(guide,title,2)
        for t in texts:para(guide,t)
    heading(answers,'答案册使用说明')
    para(answers,'本册与《计算机视觉 140 算法学习文档》逐项对应。编号格式为 Q001-1：前三位为本书算法编号，最后一位为该算法题号。每题先重述问题，再给参考答案，便于单独阅读。')
    para(answers,'建议先独立口述或书写，再核对。答案给出关键结论及必要理由；若题目涉及实现约定，须以当前项目说明为准。扩展方案不代表项目已实现。自评可按每题 0–3 分、每算法 18 分记录。')
    para(answers,'模型架构的完整组成、流程图和配置核对在学习册“模型架构专题”中。答案涉及 backbone、neck、head、token 等术语时，先复习学习册共同基础。')
    # Architecture atlas, one entry per model; task chapters link to stable M numbers.
    overview_start=len(guide.paragraphs)
    heading(guide,'模型架构专题：22 套本地模型',1,True)
    para(guide,'本专题覆盖所有使用预训练模型的算法，包括工业异常、图文理解、图像恢复、视频动作和模型解释。先按数据流认识组件，再到对应算法理解任务损失、输出语义和使用边界。模型编号 M01–M22 是架构定位键。')
    heading(guide,'按输出形态建立阅读路线',3)
    para(guide,'先读 M01，掌握卷积、残差 stage 与分类头。接着读 M02–M05，比较同一检测家族如何增加旋转角、掩膜原型和关键点分支。M06–M08 则比较语义类别图、全景集合预测和提示式区域选择，理解“输出都是掩膜”并不意味着网络结构和监督目标相同。')
    para(guide,'M09–M12 关注流水线：人脸和手部先定位 ROI 再回归，OCR 先检测文字再识别，版面检测先划分页面区域。分析误差时，要判断出错来自哪一级，以及前一级的裁剪、缩放误差如何传给后一级。')
    para(guide,'M13–M16 依次比较向量检索、文本条件检测、图像描述和视觉问答。重点观察文字在哪里进入网络：独立编码后比较、与局部视觉特征匹配，还是通过交叉注意力参与逐 token 生成。')
    para(guide,'M17–M22 面向深度、清晰图像、显著前景与视频动作。比较稠密解码、窗口注意力、通道注意力、嵌套 U 形结构和三维卷积，说明它们分别怎样恢复空间细节或引入时间信息。')
    heading(guide,'从框图走到可解释的架构',3)
    para(guide,'每读一套模型，至少标注输入与输出形状、空间下采样位置、特征合并方式、任务头的预测量，以及后处理的坐标变换。再选择一个组件，说明移除它会失去什么能力。例如去掉时间卷积会削弱运动建模，去掉提示编码器会失去用户指定区域的输入通道。')
    para(guide,'同一家族的训练目标和权重也需区分：真实去噪与运动去模糊都使用 Restormer，但不能因此任意交换检查点；分类用到 ResNet18，异常记忆库和 Grad-CAM 则复用它的不同中间特征或梯度。下面的架构专题与后面的实验原理应结合阅读。')
    for p in guide.paragraphs[overview_start:]:
        if p.style.name=='Normal':p.style=guide.styles['ModelBlock']
    for key,a in architectures.items():
        heading(guide,f'M{a["number"]:02d}  {a["title"]}',2,True)
        para(guide,f'资源 ID：{key}',style='Meta')
        p=guide.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(HERE/'figures'/f'{key}.png'),width=Cm(15.0))
        p.paragraph_format.keep_with_next=True
        para(guide,f'图 M{a["number"]:02d}  模块数据流（教学示意）',style='Caption')
        for b in a['blocks']:para(guide,b,style='ModelBlock')
        para(guide,a['source'],style='SmallText')
    current=None;module=0
    for e in entries:
        if current!=e['category']:
            current=e['category'];module+=1
            # Let algorithm modules flow continuously; forcing each new module
            # to a fresh page strands the preceding questions on sparse pages.
            for doc in [guide,answers]:heading(doc,f'第 {module:02d} 模块  {current}',1,module==1)
        label=f'{e["number"]:03d}  {e["name"]}（{e["id"]}）'
        answer_start=len(answers.paragraphs)
        for doc in [guide,answers]:heading(doc,label,2)
        qprefix=f'Q{e["number"]:03d}'
        inputs='、'.join(e['inputs'])
        para(guide,f'实验输入：{inputs}。用途：{e["uses"]}',style='Meta')
        if e['model']:
            a=architectures[e['model']]
            para(guide,f'模型架构：M{a["number"]:02d} {a["title"]}。资源 ID：{e["model"]}。详见前面的架构专题。',style='Meta')
        heading(guide,'学习目标与直观理解',3)
        para(guide,e['lesson'][0]);para(guide,e['lesson'][1])
        heading(guide,'核心机制与推导',3)
        for t in e['theory']:para(guide,t)
        for t in e['formula']:para(guide,t,style='Formula')
        heading(guide,'参数、实验与结果解读',3)
        if e['params']:
            vals=[]
            for p in e['params']:
                v=json.dumps(p['default'],ensure_ascii=False,separators=(',',':')) if isinstance(p['default'],(dict,list)) else str(p['default'])
                vals.append(f'{p["key"]}={v}')
            para(guide,'项目默认参数：'+'；'.join(vals)+'。',style='Meta')
        else:para(guide,'本入口无普通数值参数；输入内容、交互提示和模型预处理仍会影响结果。',style='Meta')
        for t in e['experiment']:para(guide,'建议实验：'+t)
        para(guide,'结果解读：'+e['lesson'][2])
        para(guide,'边界与误区：'+e['lesson'][3])
        heading(guide,'学习练习（答案见独立答案册）',3)
        for j,qa in enumerate(e['qa'],1):
            qid=f'{qprefix}-{j}'
            para(guide,f'{qid}  {qa["question"]}',style='Question')
            p=para(answers,f'{qid}  {qa["question"]}',style='Question');p.paragraph_format.keep_with_next=True
            para(answers,'参考答案：'+qa['answer'],style='Answer')
        if e['number']==len(entries):
            # Keep the final algorithm's six answers as one readable closing
            # block instead of leaving a single final question on its own page.
            for p in answers.paragraphs[answer_start:-1]:
                p.paragraph_format.keep_with_next=True
    add_references(guide)
    guide_path=OUT/'01_140算法原理与练习.docx'
    answer_path=OUT/'02_140算法练习参考答案.docx'
    guide.save(guide_path);answers.save(answer_path)
    source_files=[ROOT/'docs/algorithm-catalog.json',ROOT/'frontend/src/learning/lessons.ts',ROOT/'backend/app/inference.py',ROOT/'backend/app/models.py']
    manifest={'algorithm_count':len(entries),'question_count':sum(len(e['qa']) for e in entries),'model_count':len(architectures),'modules':dict(Counter(e['category'] for e in entries)), 'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}, 'algorithms':[{'number':e['number'],'id':e['id'],'name':e['name'],'category':e['category'],'question_ids':[f'Q{e["number"]:03d}-{j}' for j in range(1,7)]} for e in entries]}
    (OUT/'quality'/'coverage.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    (HERE/'content.json').write_text(json.dumps({'entries':entries,'architectures':architectures},ensure_ascii=False,indent=2))
    # Meaningful artifact validation: coverage, pairing, separation, fields, no empty sections.
    for path,is_answer in [(guide_path,False),(answer_path,True)]:
        doc=Document(path);texts=[p.text for p in doc.paragraphs];qs=[re.match(r'Q\d{3}-[1-6]\b',t).group() for t in texts if re.match(r'Q\d{3}-[1-6]\b',t)]
        expected=[qid for a in manifest['algorithms'] for qid in a['question_ids']]
        assert qs==expected,(path,'question order')
        assert sum(t.startswith('参考答案：') for t in texts)==(840 if is_answer else 0)
        assert all(not x in '\n'.join(texts) for x in ['TODO','TBD','待补充'])
        print(path.name,'paragraphs',len(texts),'characters',sum(map(len,texts)),'questions',len(qs))
    print('Coverage OK: 140 algorithms, 13 modules, 840 Q/A, 22 model architectures.')

if __name__=='__main__':build()
