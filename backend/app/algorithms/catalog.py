"""中文学习实验清单。所有具名基础算子拥有独立入口。"""
from .registry import add, number as n, choice as c, text as t, jsonparam as j, KERNEL, THRESH, AREA

def register():
    base = '图像基础'
    add('pixels','像素与取色','Pixel inspector',base,'读取指定位置的颜色和邻域。','图像是 H×W×C 的数组，像素坐标以左上角为原点。','取色、曝光检查、定位数据错误。','越界坐标无效；显示缩放不改变原图坐标。',[n('x','横坐标',0,0,10000,'原图坐标 x。'),n('y','纵坐标',0,0,10000,'原图坐标 y。')],interaction='points')
    add('gray','灰度化','Grayscale',base,'把彩色图像转为亮度图。','对 RGB 通道做加权和，OpenCV 内部采用 BGR 顺序。','边缘、阈值和形状分析的前处理。','颜色差异但亮度相同的目标会合并。',output_kind='gray')
    add('color','颜色空间转换','RGB HSV Lab YCrCb',base,'观察不同颜色空间的编码。','通过非线性或线性变换分离色相、亮度与色度；结果显示编码通道而非自然色。','颜色分割、白平衡、光照分析。','HSV 的 H 范围为 0–179，不能按 RGB 解释。',[c('space','目标空间','HSV',['RGB','HSV','Lab','YCrCb'],'输出三个编码通道，数据记录通道范围。')])
    add('channel','通道分离','Split channels',base,'单独查看一个颜色通道。','从多维数组提取一个平面。','颜色缺陷分析和单波段检测。','BGR 通道顺序与 RGB 不同。',[c('channel','通道','R',['R','G','B'],'选择希望单独显示的通道。')],output_kind='gray')
    add('merge','通道合并','Merge channels',base,'按权重重新合并 RGB 通道。','每个原通道乘以增益后截断到 0–255。','白平衡、颜色一致性调整。','过大增益造成饱和并丢失细节。',[n(k,k+' 通道增益',1,0,3,'线性通道增益。',0.05) for k in ['R','G','B']])
    for id,name,desc in [('add','加法','饱和加法'),('subtract','减法','饱和减法'),('blend','加权融合','线性加权'),('bit_and','按位与','逐位 AND'),('bit_or','按位或','逐位 OR'),('bit_xor','按位异或','逐位 XOR')]:
        add(id,name,'Image '+id,base,'组合两张同尺寸图片。',desc+'；第二张图片必须与第一张同尺寸。','参考差异、合成和掩膜运算。','不同尺寸不自动拉伸，避免错误对应。',[n('alpha','第一张权重',0.5,0,1,'仅融合时生效，第二张权重为 1−α。',0.05)] if id=='blend' else [],inputs=['image','reference'])
    add('bit_not','按位非','Bitwise NOT',base,'反转图像的所有位。','8 位像素取反等价于 255−I。','掩膜反选和负片观察。','不能当作亮度归一化。')
    add('histogram','直方图','Histogram',base,'展示各通道像素值分布。','统计每一个灰度级出现的次数。','判断曝光、对比度和阈值。','直方图不保留像素空间位置。')
    add('brightness','亮度与对比度','Brightness contrast',base,'线性调整明暗及动态范围。','结果为 clip(αI+β)。','光照补偿、预处理。','截断造成高光或暗部细节损失。',[n('alpha','对比度',1,0.1,3,'大于 1 扩大像素差异。',0.05),n('beta','亮度偏移',0,-100,100,'对每个像素增加的亮度值。')])
    add('gamma','伽马校正','Gamma correction',base,'非线性调整中间调。','输出 255×(I/255)^γ；γ 小于 1 提亮。','低照度显示、曝光调整。','不能恢复完全欠曝或饱和信息。',[n('gamma','伽马',0.7,0.1,4,'小于 1 提亮，大于 1 压暗。',0.05)])
    for id,name in [('equalize','直方图均衡'),('clahe','CLAHE 局部均衡')]:
        add(id,name,id.upper(),base,'增强亮度对比。','对亮度通道进行累计分布映射。CLAHE 在局部网格限制对比度。','雾化、低对比度表面增强。','均衡可能增强噪声并改变外观。',[n('clip','对比度上限',2,0.1,10,'越大局部对比度越强。',0.1),n('grid','网格数',8,2,32,'每个方向的局部网格数量。')] if id=='clahe' else [])
    cat='滤波与增强'
    for id,name,en,principle in [('mean','均值滤波','Mean blur','邻域均值抑制高频。'),('gaussian','高斯滤波','Gaussian blur','按高斯权重平均邻域。'),('median','中值滤波','Median blur','用邻域中位数替代像素。'),('bilateral','双边滤波','Bilateral filter','同时考虑空间与颜色距离。'),('nlm','非局部均值去噪','Non-local means','搜索相似图块并加权平均。')]:
        ps=[n('strength','滤波强度',10,1,40,'数值越大去噪越强、细节越少。')] if id=='nlm' else [KERNEL]
        if id=='bilateral': ps += [n('sigma','颜色尺度',50,1,150,'允许参与平滑的颜色差异。')]
        add(id,name,en,cat,'平滑噪声并观察边缘变化。',principle,'相机噪声预处理。','核或强度过大会抹掉小缺陷。',ps)
    add('convolution','自定义卷积核','Convolution',cat,'输入矩阵执行二维滤波。','局部邻域与核逐元素相乘并求和。','设计边缘、模糊和锐化算子。','核总和过大使图像过曝；限制为奇数方阵 1–15。',[j('matrix','卷积核',[[0,-1,0],[-1,5,-1],[0,-1,0]],'输入二维 JSON 数组。')])
    add('sharpen','锐化','Unsharp mask',cat,'增强高频细节。','原图加上原图减模糊图的加权差。','纹理、文字增强。','也会放大噪声与光晕。',[n('amount','锐化量',1,0,4,'高频残差的放大比例。',0.1),KERNEL])
    for id,name in [('fft','傅里叶频谱'),('lowpass','频域低通'),('highpass','频域高通')]:
        add(id,name,'Fourier '+id,cat,'观察或筛选图像空间频率。','FFT 将空间信号分解为频率；中心是低频，外缘是高频。','周期噪声分析、纹理和边缘提取。','硬截止会产生振铃；频谱显示采用对数幅度。',[n('radius','截止半径比例',0.1,0.01,0.5,'相对较短边长度的频率半径。',0.01)] if id!='fft' else [],output_kind='gray')
    cat='阈值与形态学'
    for id,name,principle,ps in [('threshold','固定阈值','按固定亮度阈值二值化。',[THRESH]),('adaptive','自适应阈值','每个邻域独立计算高斯加权阈值。',[n('block','邻域尺寸',21,3,101,'自动取奇数，大于局部目标宽度。',2),n('constant','阈值偏移',5,-30,30,'从局部均值减去的值。')]),('otsu','Otsu 自动阈值','最大化前景与背景的类间方差。',[])]:
        add(id,name,id,cat,'把灰度图分成前景与背景。',principle,'印刷字符、零件轮廓、掩膜生成。','背景不均匀或两类灰度重叠时失败。',ps,output_kind='mask')
    for id,name in [('erode','腐蚀'),('dilate','膨胀'),('open','开运算'),('close','闭运算'),('morph_gradient','形态学梯度'),('tophat','顶帽'),('blackhat','黑帽')]:
        add(id,name,id,cat,'用结构元素改变局部形状。','腐蚀取局部最小值，膨胀取最大值；开闭及差分组合这些操作。','连接断点、去除小噪点、提取局部亮暗缺陷。','结构元素过大可能合并零件或删除细线。',[KERNEL,n('iterations','迭代次数',1,1,10,'重复应用结构元素。'),c('shape','结构元素','ellipse',['ellipse','rect','cross'],'椭圆适合圆形目标，矩形适合规则边缘。')])
    add('skeleton','骨架提取','Skeleton thinning',cat,'把二值前景收缩为中心线。','重复腐蚀并保留无法由开运算恢复的像素。','线宽、拓扑、裂纹路径分析。','噪声和毛刺会产生额外分支。',[THRESH],output_kind='mask')
    add('distance','距离变换','Distance transform',cat,'计算前景像素到背景的距离。','欧氏距离场在目标中心取局部峰值。','分水岭种子、厚度和间隙分析。','阈值质量直接影响距离；显示按最大距离归一化。',[THRESH],output_kind='gray')
    cat='边缘与形状'
    for id,name,principle in [('sobel','Sobel','一阶差分估计 x/y 梯度。'),('scharr','Scharr','更精确的三阶模板估计一阶梯度。'),('laplacian','Laplacian','二阶差分突出亮度急剧变化。'),('canny','Canny','平滑、梯度、非极大值抑制和双阈值连接。')]:
        add(id,name,name,cat,'检测亮度变化形成的边缘。',principle,'尺寸测量、轮廓定位。','纹理和噪声也会形成边缘。',[n('low','低阈值',60,0,255,'弱边缘连接阈值。'),n('high','高阈值',160,0,255,'强边缘起始阈值，须不低于低阈值。')] if id=='canny' else [],output_kind='mask' if id=='canny' else 'gray')
    for id,name in [('contours','轮廓、面积与周长'),('components','连通域与质心'),('hull','凸包'),('shape_match','形状匹配')]:
        add(id,name,id,cat,'定位二值图中的独立对象并输出几何属性。','阈值分割后分析连接关系与边界；形状匹配比较 Hu 不变矩。','零件计数、轮廓检测和形状一致性。','相接物体可能连成一个；形状匹配需要同一阈值语义。',[THRESH,AREA],inputs=['image','reference'] if id=='shape_match' else ['image'],output_kind='overlay')
    add('hough_lines','霍夫直线','Hough lines',cat,'检测线段并输出端点。','边缘像素在参数空间投票。','直边、角度和车道定位。','杂乱纹理可能造成多条伪线。',[n('votes','投票阈值',50,1,300,'最小投票数。'),n('length','最短线长',40,1,500,'单位为像素。'),n('gap','最大间隙',10,0,100,'允许连接的断点长度。')],output_kind='overlay')
    add('hough_circles','霍夫圆','Hough circles',cat,'定位圆心与半径。','基于梯度的圆参数空间投票。','轴承、孔洞、瓶盖检测。','低对比、椭圆、遮挡可能漏检。',[n('votes','圆心阈值',30,5,100,'越低越敏感。'),n('min_radius','最小半径',5,1,300,'像素。'),n('max_radius','最大半径',100,2,600,'像素，应大于最小半径。')],output_kind='overlay')
    cat='几何与传统分割'
    add('crop','ROI 裁剪','Crop',cat,'保留矩形区域。','通过原图坐标切片裁剪。','只分析有效检测区域。','请先绘制矩形，宽高不能为零。',interaction='rectangle')
    add('resize','缩放与插值','Resize interpolation',cat,'比较不同采样方式。','对目标网格按指定插值估计像素。','模型输入、图像缩放。','放大不会恢复真实细节；标签应使用最近邻。',[n('scale','缩放比例',0.5,0.1,3,'宽高同时缩放。',0.1),c('method','插值','linear',['nearest','linear','cubic','area','lanczos'],'缩小推荐 area，掩膜用 nearest。')])
    add('rotate','旋转','Rotation',cat,'围绕图像中心旋转。','二维旋转矩阵映射坐标；画布维持原尺寸。','方向校正。','超出原画布的部分会裁切。',[n('angle','角度',15,-180,180,'正值逆时针。')])
    add('affine','仿射变换','Affine transform',cat,'应用 2×3 仿射矩阵。','保持直线和平行关系，允许平移缩放剪切。','平面图像对齐。','无法表示透视消失点。',[j('matrix','2×3 矩阵',[[1,0,20],[0,1,10]],'原图坐标到输出坐标的映射。')])
    add('perspective','透视变换','Perspective transform',cat,'把选中的四边形展开为矩形。','四组对应点确定单应矩阵。','文档矫正、平面测量。','必须按左上、右上、右下、左下顺序选择四点。',interaction='polygon')
    add('register','图像配准','Image registration',cat,'把输入图对齐到参考图。','ORB 匹配结合 RANSAC 估计单应矩阵。','参考差异检测、平面定位。','纹理少、视差大或匹配不足时不能配准。',inputs=['image','reference'],preview=False)
    add('region_grow','区域生长','Region growing',cat,'从点选种子扩张相似颜色区域。','在连通邻域内比较与种子的色差。','颜色相近区域分割。','边界弱或容差过大会泄漏。',[n('tolerance','颜色容差',25,1,100,'相对于种子的每通道最大差异。')],interaction='points',output_kind='mask')
    add('watershed','分水岭','Watershed',cat,'分开相接的前景。','距离场构建内部种子，按梯度进行集水区划分。','相邻零件、细胞分割。','种子不充分会欠分割。',[n('seed_ratio','种子比例',0.45,0.1,0.9,'距离大于最大距离乘该比例的像素作为种子。',0.05)],output_kind='overlay')
    add('grabcut','GrabCut 前景分割','GrabCut',cat,'通过框选建立前景背景模型。','高斯混合模型与图割迭代优化能量。','前景提取和背景替换准备。','框须包含整个前景，且边界留有背景。',[n('iterations','迭代次数',5,1,15,'更多迭代可能改善边界，但更慢。')],interaction='rectangle',output_kind='mask',preview=False)
    add('kmeans_segment','颜色聚类分割','K-means segmentation',cat,'用少量聚类中心替代颜色。','最小化像素到颜色中心的平方距离。','颜色分类和区域简化。','颜色类别不等于语义类别。',[n('clusters','颜色数',5,2,16,'聚类中心数量。')],preview=False)
    cat='特征与匹配'
    for id,name,en in [('harris','Harris 角点','Harris'),('shi','Shi-Tomasi 角点','Shi-Tomasi'),('sift','SIFT 特征','SIFT'),('orb','ORB 特征','ORB')]:
        add(id,name,en,cat,'检测局部可重复的特征点。','角点衡量邻域结构变化；SIFT/ORB 同时生成匹配描述子。','定位、匹配和运动估计。','模糊、纯色或重复纹理影响特征可靠性。',[n('max_features','最多特征点',300,10,2000,'上限越高，计算和显示越密集。')],output_kind='overlay')
    add('hog','HOG 方向梯度','Histogram of oriented gradients',cat,'显示局部梯度方向分布。','将梯度按方向直方图编码。','传统行人识别、形状描述。','对旋转与尺度变化敏感。')
    add('lbp','LBP 局部纹理','Local binary pattern',cat,'编码邻域相对中心的亮暗关系。','八邻域比较生成 8 位模式。','表面纹理分析。','噪声和尺度变化影响模式。',output_kind='gray')
    for id,name in [('matching','特征匹配'),('ransac','RANSAC 鲁棒匹配'),('stitch','图像拼接')]:
        add(id,name,id,cat,'匹配两个视图中的对应位置。','ORB 描述子近邻匹配；RANSAC 剔除不符合单应矩阵的离群点。','平面配准、全景拼接。','需要重叠、足够纹理；明显视差或运动目标会失败。',[n('ratio','比率阈值',0.75,0.3,0.95,'最佳匹配距离 / 次佳距离，越小越严格。',0.05)],inputs=['image','reference'],preview=False)
    add('template','模板匹配','Template matching',cat,'寻找局部模板的最佳位置。','滑动窗口计算归一化相关系数。','固定视角定位、工业模板搜索。','尺度或旋转变化会降低得分；模板必须小于原图。',inputs=['image','template'],interaction='rectangle',output_kind='overlay')
    for id,name in [('knn','KNN 小型学习'),('svm','SVM 小型学习'),('kmeans_demo','K-means 小型学习')]:
        add(id,name,id,cat,'对图像的二维颜色样本学习决策区域。','使用 OpenCV ML 在 R/G 特征空间训练，绘制决策边界；标签按蓝通道强弱生成，仅作教学。','理解距离、间隔和聚类。','这是教学标签，不能作为实际任务准确率。',[n('complexity','邻居数 / C / 聚类数',3,1,10,'KNN 的 k、SVM 的 C 或 K-means 的类别数。')])
    register_special()

def register_special():
    cat='工业视觉'
    for id,name,summary in [('count','零件计数','阈值与连通域统计零件数量。'),('measure','尺寸、角度与间隙','从轮廓最小外接矩形测量尺寸、角度和相邻间距。'),('color_check','颜色一致性','比较两图 Lab 颜色均值与差异。'),('difference','参考图差异','比较已经对齐的两张图像。'),('defects','表面缺陷规则','用局部残差定位亮暗缺陷。'),('assembly','缺件与错装规则','比较参考图中各 ROI 的相似性。'),('anomaly','工业异常热力图','使用预训练骨干建立正常样本特征库并比较最近邻距离。')]:
        inputs=['image','normal_samples'] if id=='anomaly' else ['image','reference'] if id in ['color_check','difference','assembly'] else ['image']
        ps=[THRESH,AREA] if id in ['count','measure'] else [n('sensitivity','敏感度',25,1,100,'差异或残差阈值，越低越敏感。')]
        if id=='anomaly':ps=[n('score_threshold','异常距离阈值',0,0,100,'0 仅展示分数；非零时将最近邻特征距离超过阈值的区域标出。请用验证样本选择阈值。',0.1)]
        if id=='measure':ps += [n('pixels_per_mm','每毫米像素数',0,0,10000,'0 表示未标定，只输出 px；必须提供同一平面的尺度。',0.1)]
        if id=='assembly':ps += [j('regions','检测区域',[],'原图矩形列表 [[x,y,w,h], ...]；未配置时使用画出的 ROI。')]
        add(id,name,id,cat,summary,'规则算法按阈值、轮廓或参考差异分析；异常模型使用局部预训练特征的正常记忆库。','固定相机、稳定光照下的质量检测。','需要合适参考与正常样本；通用模型不具备专用缺陷类别。',ps,inputs=inputs,model='resnet18' if id=='anomaly' else '',interaction='rectangle' if id=='assembly' else '',preview=False,output_kind='overlay')
    add('char_check','字符校验','OCR validation',cat,'识别字符后按正则规则校验。','OCR 检测与识别后对文本执行正则 fullmatch。','批号、标签、编码检查。','字体和反光影响识别，规则须匹配业务格式。',[t('pattern','正则表达式','[A-Z0-9]+','每一段识别文本都独立执行 fullmatch。')],model='rapidocr',preview=False)
    cat='文字与图文理解'
    add('qr','二维码识别','QR decode',cat,'检测并解码二维码。','OpenCV 二维码定位、透视矫正与解码。','物料追溯。','模糊、反光和小尺寸可能无法解码。',output_kind='overlay')
    add('barcode','条码识别','Barcode decode',cat,'检测 EAN/UPC 条码。','OpenCV barcode 模块识别平行线结构并解码。','商品条码。','该接口不支持所有码制；无结果会明确返回空列表。',output_kind='overlay')
    deep=[
        ('classify','图像分类','深度学习识别','resnet18','ImageNet 1000 类'),
        ('detect','目标检测','深度学习识别','yolov8n','COCO 80 类'),
        ('obb','旋转框检测','深度学习识别','yolov8n-obb','DOTA 15 类，航拍领域'),
        ('instance','实例分割','深度学习识别','yolov8n-seg','COCO 80 类'),
        ('pose','人体姿态','深度学习识别','yolov8n-pose','人体 17 关键点'),
        ('semantic','语义分割','深度学习识别','deeplab','VOC 20 类 + 背景'),
        ('panoptic','全景分割','深度学习识别','detr-panoptic','COCO stuff/thing'),
        ('sam','交互式分割','深度学习识别','sam2','类别无关，点选/框选提示'),
        ('face','人脸关键点','深度学习识别','face_landmarker','478 个脸部点'),
        ('hand','手部关键点','深度学习识别','hand_landmarker','每手 21 个点'),
        ('ocr','文字检测与识别','文字与图文理解','rapidocr','中文与英文印刷体'),
        ('layout','版面分析','文字与图文理解','layout','DocStructBench 10 类文档元素'),
        ('similarity','图像相似度检索','文字与图文理解','clip','CLIP 特征余弦相似度'),
        ('text_retrieval','图文检索','文字与图文理解','clip','英文提示较可靠'),
        ('grounding','文字提示目标检测','文字与图文理解','owlvit','开放词汇英文目标'),
        ('caption','图像描述','文字与图文理解','blip','英文描述'),
        ('vqa','视觉问答','文字与图文理解','blip-vqa','英文问答'),
        ('depth','单目相对深度','标定与三维','depth-anything','相对逆深度，无公制尺度'),
        ('superres','深度学习超分辨率','图像恢复','edsr','Swin2SR x2'),
        ('denoise_dl','深度学习去噪','图像恢复','swin-denoise','Restormer 真实图像去噪'),
        ('deblur','深度学习去模糊','图像恢复','restormer','运动去模糊'),
        ('matting','前景抠图与背景替换','图像恢复','rmbg','前景 alpha'),
        ('action','视频动作识别','视频与时序','r3d','Kinetics-400 动作类别'),
        ('gradcam','Grad-CAM 类激活图','模型学习与评估','resnet18','ImageNet 1000 类'),
        ('feature_maps','特征图可视化','模型学习与评估','resnet18','ResNet18 layer4 的 512 通道'),
        ('benchmark','推理后端对比','模型学习与评估','resnet18','PyTorch 指定设备 / ONNX Runtime CPU'),
    ]
    for id,name,cat,model,classes in deep:
        ps=[n('confidence','置信度阈值',0.25,0.01,0.95,'低于此值的候选不显示。',0.01)] if id in ['detect','obb','instance','pose','grounding','layout'] else []
        if id in ['grounding','text_retrieval','vqa']:ps += [t('prompt','文本提示','a person' if id!='vqa' else 'What is in the picture?','输入英文类别；检索可用逗号分隔多个候选。')]
        if id=='matting':ps += [t('background','背景颜色','#e8eef5','十六进制 RGB 颜色。')]
        if id=='benchmark':ps += [n('repeats','重复次数',5,1,30,'预热后测量，输出中位延迟。')]
        add(id,name,id,cat,'本地预训练模型推理。支持范围：'+classes,'通过预训练网络提取特征并完成指定任务；模型结构、权重和预处理必须一致。','在支持类别与训练分布接近的图像上辅助学习和实验。','域偏移、遮挡或低分辨率会降低可靠性；缺少文件时不自动联网。',ps,model=model,inputs=['video'] if id=='action' else ['image','gallery'] if id in ['similarity','text_retrieval'] else ['image'],interaction='prompts' if id=='sam' else '',preview=False,output_kind='overlay',temporal=id=='action')
    add('lowlight','低光增强 Retinex','Retinex','图像恢复','估计并补偿光照。','用对数反射模型分离高斯平滑照明。','低照度图像预处理。','这是传统 Retinex；强噪声会被增强。',[n('sigma','光照尺度',40,5,150,'高斯照明估计的尺度。')])
    add('inpaint','图像修复','Telea inpaint','图像恢复','修复手绘掩膜覆盖区域。','沿边界传播邻域颜色。','去除小划痕、坏点和细小遮挡。','传统算法不能合理重建大面积语义内容。',[n('radius','修复半径',3,1,20,'邻域半径，单位像素。')],interaction='brush')
    for id,name,principle in [('frame_diff','帧差','比较连续帧的绝对差异。'),('mog2','背景建模 MOG2','随时间更新混合高斯背景模型。'),('flow_sparse','稀疏光流','Lucas–Kanade 跟踪前一帧角点。'),('flow_dense','稠密光流','Farneback 估计每个像素的位移。'),('single_track','单目标跟踪','CSRT 从首帧矩形 ROI 学习并更新目标。'),('multi_track','多目标跟踪与轨迹','YOLO 检测结合最近邻 IoU 关联维持目标 ID。'),('events','计数、越线、区域与停留','对跟踪 ID 的轨迹检查线交叉、区域进入和持续时间。'),('sequence','事件顺序规则','按配置事件序列及时间窗口验证轨迹产生的事件。'),('video_segment','视频分割','SAM2 以首帧提示初始化记忆并在后续帧传播。')]:
        ps=[n('sample_every','推理间隔帧数',1,1,1,'当前时序工作流固定逐帧运行，不抽帧；结果保留原时长和帧率。')]
        if id in ['events','sequence']: ps += [n('line_x','计数线横坐标比例',0.5,0.05,0.95,'在原图上建立竖直越线判定线。',0.05),n('dwell','停留秒数',2,0.1,60,'同一 ID 在区域内连续停留时长。',0.1)]
        if id=='sequence':ps += [j('event_order','事件顺序',['enter','cross','dwell'],'可用事件：enter、cross、dwell、exit。'),n('window','时间窗口',10,1,120,'首个事件到最后事件允许的秒数。')]
        add(id,name,id,'视频与时序','流式处理连续视频并保留时间轴。',principle,'运动分析、轨迹、产线事件。','摄像机移动、遮挡和 ID 切换影响规则；事件必须结合场景验证。',ps,inputs=['video'],interaction='rectangle' if id in ['single_track','events','sequence','video_segment'] else '',model='yolov8n' if id in ['multi_track','events','sequence'] else 'sam2' if id=='video_segment' else '',preview=False,temporal=True)
    for id,name,inputs,ps in [
        ('calibrate','相机标定',['image','calibration_images'],[n('cols','内角点列数',9,3,20,'棋盘格内角点列数。'),n('rows','内角点行数',6,3,20,'棋盘格内角点行数。'),n('square_mm','棋盘格边长 mm',25,1,200,'真实棋盘格格子边长。')]),
        ('undistort','畸变校正',['image'],[j('camera','相机矩阵',[[800,0,320],[0,800,240],[0,0,1]],'与原图分辨率对应的 3×3 内参。'),j('distortion','畸变系数',[-0.2,0.05,0,0,0],'k1,k2,p1,p2,k3。')]),
        ('stereo','双目视差与深度',['image','reference'],[n('disparities','视差搜索数',64,16,256,'向上取 16 的倍数。',16),n('block','匹配块边长',5,3,21,'自动取奇数。',2),n('focal','焦距像素',0,0,10000,'0 表示未知，只输出视差。'),n('baseline','基线毫米',0,0,2000,'已校正平行双目基线，非零且提供焦距才计算深度。')]),
        ('stereo_rectify','双目校正',['image','reference'],[j('calibration','双目标定 JSON',{},'需要 K1,D1,K2,D2,R,T。可用相机标定结果配合已知双目外参。')]),
        ('reconstruct','双视图基础重建',['image','reference'],[j('camera','第一视图内参',[[800,0,320],[0,800,240],[0,0,1]],'需真实内参；单目多视图重建只有相对尺度。'),j('camera_reference','第二视图内参',[[800,0,320],[0,800,240],[0,0,1]],'同一相机时使用相同内参。双相机可分别填写。')]),
        ('pointcloud','点云查看、滤波与配准',['pointcloud'],[n('voxel','体素边长',0.05,0,10,'0 保留全部点；单位与输入点云相同。',0.01),c('operation','操作','view',['view','plane','register'],'plane 用 RANSAC 平面分割；register 需要第二份点云。'),n('distance','平面距离阈值',0.05,0.001,2,'RANSAC 内点距离。',0.001)]),
    ]:
        add(id,name,id,'标定与三维','由专用输入计算几何关系。','基于投影几何、特征对应或空间邻域估计。','尺寸校正、空间理解和重建。','标定视角不足、错误内参、纹理少会失败；单目重建没有真实尺度。',ps,inputs=inputs,preview=False)
    add('augmentation','预处理与数据增强','Data augmentation','模型学习与评估','展示可重复的数据增强。','对图像施加翻转、旋转、亮度和噪声扰动。','学习训练输入分布。','增强必须符合真实场景，标注也需同步变换。',[n('angle','旋转',10,-90,90,'角度。'),n('brightness','亮度增益',1.1,0.1,2,'乘法增益。',0.05),n('noise','噪声标准差',5,0,40,'固定随机种子保证可重复。'),c('flip','翻转','none',['none','horizontal','vertical'],'镜像变换。')])
    for id,name in [('eval_classification','分类指标'),('eval_detection','检测 AP / mAP'),('eval_segmentation','分割 IoU / Dice')]:
        ps=[c('mode','掩膜类型','binary',['binary','multiclass'],'binary 按 127 阈值；multiclass 将灰度值作为整数类别 ID。'),n('ignore_label','忽略类别 ID',255,0,255,'多类别模式中此真值标签不参加统计。')] if id=='eval_segmentation' else [j('annotations','标注与预测',{},'格式见算法说明下方输入示例和 README；分类为 truth/prediction 数组，检测为真值/预测框列表。')]
        add(id,name,id,'模型学习与评估','输入真实标注与预测计算指标。','按分类混淆矩阵、框的 IoU 匹配或像素交并比计算。','数据集验证和回归比较。','必须提供真值，不能从无标签图片生成准确率。',ps,inputs=['image','truth_mask'] if id=='eval_segmentation' else ['image'],preview=False)
