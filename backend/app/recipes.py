"""每个实验的可编辑示例输入，避免多图任务只给一张无关图片。"""
import json
from .config import ROOT
from .algorithms.registry import REGISTRY,ALIASES
from . import storage

def example_for(id):
    if id not in REGISTRY:raise ValueError('未知实验')
    a=REGISTRY[id];id=ALIASES.get(id,id);p={};extra={};note='示例参数可自由修改；算法结果取决于输入内容。'
    names={row['id'] for row in storage.rows('SELECT id FROM assets')}
    def asset(name):
        value='example-'+name
        if value not in names:raise ValueError(f'缺少示例 {name}，请先运行 scripts/prepare_examples.py 与 scripts/prepare_special_examples.py，然后重启服务')
        return value
    name='fruits'
    if a.temporal:name='pedestrians'
    elif id=='pointcloud':name='plane'
    elif id in ['count','measure','contours','components','hull','shape_match','watershed','skeleton','distance']:name='parts'
    elif id in ['anomaly','difference','assembly','defects']:name='defect'
    elif id in ['calibrate','undistort','stereo_rectify','reconstruct']:name='calibration-left01'
    elif id=='stereo':name='stereo-left'
    elif id=='obb':name='aerial'
    elif id=='layout':name='document'
    elif id=='hand':name='hands'
    elif id in ['pose','face']:name='zidane'
    elif id in ['ocr','char_check']:name='text'
    elif a.model:name='bus'
    source=asset(name);meta=storage.asset(source)['metadata'];w,h=int(meta.get('width',640)),int(meta.get('height',480))
    if 'reference' in a.inputs:
        reference='parts' if id in ['shape_match','difference','assembly'] else 'fruits-shift' if id in ['matching','ransac','stitch','register'] else 'stereo-right' if id=='stereo' else 'calibration-right01' if id in ['reconstruct','stereo_rectify'] else 'fruits'
        extra['reference']=[asset(reference)]
    if 'template' in a.inputs:extra['template']=[asset('template')]
    if 'normal_samples' in a.inputs:extra['normal_samples']=[asset(f'normal-{i}') for i in range(4)]
    if 'gallery' in a.inputs:extra['gallery']=[asset(q) for q in ['bus','fruits','zidane']]
    if 'calibration_images' in a.inputs:extra['calibration_images']=sorted(q for q in names if q.startswith('example-calibration-left'));p['square_mm']=1;note='真实棋盘照片来自 OpenCV；示例未提供实测格子大小，1 mm 只是演示尺度。用于实际测量前必须输入真实格子边长。'
    if a.interaction=='rectangle' or a.interaction=='prompts':p['roi']=[w//5,h//5,w*3//5,h*3//5]
    if a.interaction=='points':p['points']=[[w//2,h//2,1]]
    if a.interaction=='polygon':p['polygon']=[[w*.1,h*.1],[w*.9,h*.15],[w*.9,h*.9],[w*.15,h*.9]]
    if a.interaction=='brush':p['mask_points']=[[w//2+i,h//2,8] for i in range(-35,36,3)]
    if id=='text_retrieval':p['prompt']='a bus, an orange, a person'
    if id=='eval_classification':p['annotations']={'truth':[0,1,1,2],'prediction':[0,0,1,2]};note='指标来自示例标签数组，与当前展示的图片无关。'
    if id=='eval_detection':p['annotations']={'truth':[{'image_id':'a','class_id':0,'box':[10,10,80,80]}],'prediction':[{'image_id':'a','class_id':0,'box':[12,10,80,82],'score':.9}]};note='指标来自示例标注框，不把素材图片当作带标签验证集。'
    if id=='eval_segmentation':source=asset('parts');extra['truth_mask']=[asset('parts')];note='示例使用同一二值图作为预测和真值，指标为 1；更换其中一个输入观察变化。'
    if id=='undistort':
        path=ROOT/'assets/examples/calibration-result.json'
        if path.exists():cal=json.loads(path.read_text());p.update(camera=cal['camera'],distortion=cal['distortion'])
    if id in ['stereo_rectify','reconstruct']:
        path=ROOT/'assets/examples/stereo-calibration.json'
        if path.exists():
            cal=json.loads(path.read_text())
            if id=='stereo_rectify':p['calibration']=cal
            else:p.update(camera=cal['K1'],camera_reference=cal['K2'])
        note='示例相机来自 OpenCV 双目棋盘照片；外参只具有格子大小的相对尺度，不用于公制测量。'
    return {'asset_id':source,'params':a.validate(p),'extra':extra,'note':note}
