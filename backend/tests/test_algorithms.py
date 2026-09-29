from pathlib import Path
import cv2
import numpy as np
import pytest
from app.config import ROOT
from app.algorithms.registry import load,REGISTRY
from app.algorithms.common import read_image
from app.algorithms.special import evaluate,pointcloud
from app.engine import execute,composite,validate_pipeline,run_pipeline
load()
EXAMPLES=ROOT/'assets/examples'
SPECIAL={'calibrate','stereo_rectify','reconstruct','pointcloud','stitch'}
IDS=[id for id,a in REGISTRY.items() if not a.model and not a.temporal and id not in SPECIAL]

@pytest.mark.parametrize('id',IDS)
def test_classical_real_image(id,tmp_path):
    im=read_image(EXAMPLES/'fruits.jpg');h,w=im.shape[:2];p={};extra={
        'reference':[EXAMPLES/'fruits.jpg'],'template':[EXAMPLES/'template.png'],'truth_mask':[EXAMPLES/'fruits.jpg']}
    if id in ['count','measure','components','contours','hull','shape_match']:im=read_image(EXAMPLES/'parts.png');extra['reference']=[EXAMPLES/'parts.png']
    if REGISTRY[id].interaction=='rectangle':p['roi']=[w//4,h//4,w//2,h//2]
    if id=='region_grow' or id=='pixels':p['points']=[[w//2,h//2,1]]
    if id=='perspective':p['polygon']=[[0,0],[w-1,0],[w-1,h-1],[0,h-1]]
    if id=='inpaint':p['mask_points']=[[w//2,h//2,10]]
    if id=='eval_classification':p['annotations']={'truth':[0,1,1,2],'prediction':[0,0,1,2]}
    if id=='eval_detection':p['annotations']={'truth':[{'image_id':'a','class_id':0,'box':[0,0,20,20]}],'prediction':[{'image_id':'a','class_id':0,'box':[0,0,20,20],'score':.9}]}
    result=execute(id,im,p,extra)
    assert result.image.size>0 and result.image.dtype==np.uint8
    assert np.isfinite(result.image).all()
    shown=composite(result);assert shown.ndim==3 and shown.shape[2]==3
    for layer in result.layers.values():assert layer.shape[:2]==result.image.shape[:2]

def test_parameters_change_result_and_no_target():
    im=read_image(EXAMPLES/'fruits.jpg')
    assert not np.array_equal(execute('threshold',im,{'threshold':40}).image,execute('threshold',im,{'threshold':200}).image)
    result=execute('count',np.zeros((80,90,3),np.uint8),{})
    assert result.data['count']==0 and result.data['objects']==[]

def test_pixel_scale_and_exact_count():
    im=read_image(EXAMPLES/'parts.png')
    result=execute('measure',im,{'pixels_per_mm':10})
    assert result.data['count']==5 and result.data['unit']=='mm'
    for obj in result.data['objects']:assert obj['width_mm']==pytest.approx(obj['width_px']/10)
    uncalibrated=execute('measure',im,{})
    assert uncalibrated.data['unit']=='px' and 'width_mm' not in uncalibrated.data['objects'][0]

def test_reject_invalid_parameters_and_roi():
    im=np.zeros((20,20,3),np.uint8)
    for params in [{'low':-1},{'low':90,'high':40},{'made_up':2}]:
        with pytest.raises(ValueError):execute('canny',im,params)
    with pytest.raises(ValueError):execute('crop',im,{'roi':[30,30,10,10]})
    with pytest.raises(ValueError):execute('perspective',im,{'polygon':[[1,1],[1,1],[1,1],[1,1]]})

def test_pipeline_connections_and_outputs(tmp_path):
    steps=[{'algorithm':id,'params':{},'enabled':True} for id in ['gray','gaussian','otsu','open','count']]
    result=run_pipeline(read_image(EXAMPLES/'parts.png'),steps,tmp_path,lambda p,m:None,lambda:False)
    assert len(result['steps'])==5 and result['data']['count']==5
    with pytest.raises(ValueError):validate_pipeline([{'algorithm':'count'},{'algorithm':'gaussian'}])
    with pytest.raises(ValueError):validate_pipeline([{'algorithm':'open'}])

def test_true_annotation_metrics():
    result=evaluate('eval_classification',{'truth':[0,1,1,2],'prediction':[0,0,1,2]},None,{})
    assert result['accuracy']==.75 and result['confusion_matrix']==[[1,0,0],[1,1,0],[0,0,1]]
    truth=[{'image_id':'a','class_id':0,'box':[0,0,20,20]}]
    pred=[{'image_id':'a','class_id':0,'box':[0,0,20,20],'score':.9}]
    assert evaluate('eval_detection',{'truth':truth,'prediction':pred},None,{})['mAP50_95']==1
    assert evaluate('eval_detection',{'truth':truth,'prediction':[]},None,{})['AP50']==0
    with pytest.raises(ValueError):evaluate('eval_detection',{},None,{})

def test_multiclass_metrics_ignore_label(tmp_path):
    truth=np.array([[0,1,2],[0,1,255]],np.uint8);prediction=np.array([[0,2,2],[0,1,9]],np.uint8)
    path=tmp_path/'labels.png';cv2.imwrite(str(path),truth)
    result=execute('eval_segmentation',cv2.cvtColor(prediction,cv2.COLOR_GRAY2BGR),{'mode':'multiclass','ignore_label':255},{'truth_mask':[path]}).data
    assert result['pixel_accuracy']==.8
    assert result['mIoU']==pytest.approx(2/3)
    assert [q['class_id'] for q in result['classes']]==[0,1,2]

def test_pointcloud_plane_and_icp():
    p=REGISTRY['pointcloud'].validate({'operation':'plane'});result=pointcloud(EXAMPLES/'plane.xyz',p,{})
    assert result.data['inlier_count']>100 and len(result.data['plane'])==4
    result=pointcloud(EXAMPLES/'plane.xyz',REGISTRY['pointcloud'].validate({'operation':'register'}),{'reference_cloud':[EXAMPLES/'plane.xyz']})
    assert result.data['rmse']<.01

def test_stereo_invalid_scale():
    im=read_image(EXAMPLES/'fruits.jpg');result=execute('stereo',im,{}, {'reference':[EXAMPLES/'fruits.jpg']})
    assert 'depth_mm' not in result.arrays

def test_real_stereo_rectification_and_reconstruction():
    import json
    calibration=json.loads((EXAMPLES/'stereo-calibration.json').read_text());im=read_image(EXAMPLES/'calibration-left01.jpg');extra={'reference':[EXAMPLES/'calibration-right01.jpg']}
    rectified=execute('stereo_rectify',im,{'calibration':calibration},extra)
    assert rectified.image.shape[1]==im.shape[1]*2 and np.asarray(rectified.data['Q']).shape==(4,4)
    result=execute('reconstruct',im,{'camera':calibration['K1'],'camera_reference':calibration['K2']},extra)
    assert result.data['count']>=8 and '相对尺度' in result.data['scale']
