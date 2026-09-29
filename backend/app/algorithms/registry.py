"""声明式算法目录：前端表单、验证、教学文档共用同一个来源。"""
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class Parameter:
    key: str
    label: str
    default: Any
    help: str
    type: str = 'number'
    min: float | None = None
    max: float | None = None
    step: float = 1
    options: list = field(default_factory=list)

def number(key, label, value, lo, hi, help, step=1):
    return Parameter(key, label, value, help, 'number', lo, hi, step)

def choice(key, label, value, options, help):
    return Parameter(key, label, value, help, 'select', options=options)

def text(key, label, value, help):
    return Parameter(key, label, value, help, 'text')

def jsonparam(key, label, value, help):
    return Parameter(key, label, value, help, 'json')

@dataclass
class Algorithm:
    id: str
    name: str
    english: str
    category: str
    summary: str
    principle: str
    uses: str
    failures: str
    params: list[Parameter] = field(default_factory=list)
    inputs: list[str] = field(default_factory=lambda: ['image'])
    interaction: str = ''
    model: str = ''
    output: str = 'image'
    input_kind: str = 'image'
    output_kind: str = 'image'
    preview: bool = True
    temporal: bool = False
    status: str = 'implemented'
    reason: str = ''

    def dict(self):
        return asdict(self)

    def validate(self, params):
        allowed = {p.key for p in self.params}
        unknown = set(params) - allowed - {'roi', 'points', 'polygon', 'mask_points', 'model_id'}
        if unknown:
            raise ValueError(f'未知参数：{", ".join(sorted(unknown))}')
        result = {p.key: p.default for p in self.params}
        result.update(params)
        for p in self.params:
            value = result[p.key]
            if p.type == 'number':
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f'{p.label}必须是数值')
                if not (p.min <= value <= p.max):
                    raise ValueError(f'{p.label}应在 {p.min} 到 {p.max} 之间')
                if p.step == 1 and value != int(value):
                    raise ValueError(f'{p.label}必须是整数')
            if p.type == 'select' and value not in p.options:
                raise ValueError(f'{p.label}选项无效')
        return result

REGISTRY: dict[str, Algorithm] = {}
ALIASES={'rgb':'color','hsv':'color','lab':'color','ycrcb':'color','contour_area':'contours','contour_perimeter':'contours','centroid':'contours','bounding_box':'contours','industrial_template':'template','angle_measure':'measure','gap_measure':'measure'}

def add(id, name, english, category, summary, principle, uses, failures, params=None, **kwargs):
    if id in REGISTRY:
        raise RuntimeError(f'重复算法 {id}')
    REGISTRY[id] = Algorithm(id, name, english, category, summary, principle, uses, failures, params or [], **kwargs)

KERNEL = number('kernel', '核尺寸', 5, 1, 51, '邻域边长；自动取相邻奇数。越大平滑或形态变化越强。', 2)
THRESH = number('threshold', '阈值', 127, 0, 255, '像素大于该亮度时进入前景；光照变化会影响分割。')
AREA = number('min_area', '最小面积', 100, 0, 100000, '过滤面积过小的目标，单位为原图像素平方。')

def load():
    if REGISTRY:
        return
    from . import catalog
    catalog.register()
    from dataclasses import replace
    for id,space in [('rgb','RGB'),('hsv','HSV'),('lab','Lab'),('ycrcb','YCrCb')]:
        source=REGISTRY['color'];parameter=replace(source.params[0],default=space,options=[space])
        REGISTRY[id]=replace(source,id=id,name=space+' 颜色空间',english=space,params=[parameter])
    geometry=[('contour_area','轮廓面积','用格林公式计算闭合边界包围的面积，单位 px²。'),('contour_perimeter','轮廓周长','按顺序累加相邻轮廓点距离，闭合轮廓包含首尾线段。'),('centroid','图像矩与质心','几何矩 m10/m00、m01/m00 给出面积中心。'),('bounding_box','外接框','轴对齐外接框与旋转最小面积矩形描述目标范围。')]
    for id,name,principle in geometry:REGISTRY[id]=replace(REGISTRY['contours'],id=id,name=name,english=id,principle=principle)
    REGISTRY['industrial_template']=replace(REGISTRY['template'],id='industrial_template',name='工业模板定位',category='工业视觉')
    REGISTRY['angle_measure']=replace(REGISTRY['measure'],id='angle_measure',name='角度测量',summary='从最小外接矩形估计目标主轴角度，输出度数；近圆形目标方向不稳定。')
    REGISTRY['gap_measure']=replace(REGISTRY['measure'],id='gap_measure',name='间隙测量',summary='用轮廓边界最近邻距离计算目标间隙，默认输出像素。')
    from .teaching import DEEP_LESSONS
    for id,(principle,uses,failures) in DEEP_LESSONS.items():
        if id in REGISTRY:REGISTRY[id]=replace(REGISTRY[id],principle=principle,uses=uses,failures=failures)
