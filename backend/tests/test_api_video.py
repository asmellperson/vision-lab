import io
import time
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import ROOT
from app.video import run_video,probe,normalize_video,EventRules,Cancelled,ffmpeg
from app.engine import execute,composite
from app.algorithms.registry import REGISTRY

def await_job(client,id):
    for _ in range(200):
        job=client.get('/api/experiments/'+id).json()
        if job['status'] in ['completed','failed','cancelled']:return job
        time.sleep(.03)
    raise AssertionError('任务未及时完成')

def test_upload_run_download_history_and_failure():
    with TestClient(app) as client:
        assert client.get('/api/health').status_code==200
        for id in REGISTRY:
            recipe=client.get('/api/algorithms/'+id+'/example')
            assert recipe.status_code==200,(id,recipe.text)
            assert recipe.json()['asset_id']
        with open(ROOT/'assets/examples/fruits.jpg','rb') as f:response=client.post('/api/assets',files={'file':('真实图片.jpg',f,'image/jpeg')})
        assert response.status_code==200;asset=response.json();assert asset['metadata']['orientation']=='EXIF 已归一化'
        response=client.post('/api/experiments',json={'algorithm':'canny','asset_id':asset['id'],'params':{'low':30,'high':100}});assert response.status_code==200
        job=await_job(client,response.json()['id']);assert job['status']=='completed',job
        assert client.get(job['result']['image_url']).headers['content-type']=='image/png'
        zip_url=next(d['url'] for d in job['result']['downloads'] if d['name']=='experiment.zip');assert client.get(zip_url).content[:2]==b'PK'
        assert len(client.get('/api/experiments?asset_id='+asset['id']).json())==1
        code=client.post('/api/code',json=job['request']).json()['code'];assert '30' in code and '100' in code
        response=client.post('/api/experiments',json={'algorithm':'crop','asset_id':asset['id']});failed=await_job(client,response.json()['id']);assert failed['status']=='failed' and 'ROI' in failed['message']
        assert client.post('/api/experiments',json={'algorithm':'canny','asset_id':asset['id'],'params':{'low':-5}}).status_code==422
        assert client.post('/api/assets',files={'file':('invalid.png',b'bad','image/png')}).status_code in [400,422]

def test_video_timeline_audio_and_cancel(tmp_path):
    source=ROOT/'assets/examples/pedestrians.mp4';info=probe(source);assert info['duration']>1
    audio=tmp_path/'audio.mp4';ffmpeg(['-i',source,'-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','1.2','-c:v','copy','-c:a','aac',audio]);normalized=tmp_path/'input.mp4';normalize_video(audio,normalized)
    folder=tmp_path/'result';folder.mkdir();a=REGISTRY['frame_diff'];result=run_video(a,normalized,a.validate({}),{},folder,lambda p,m:None,lambda:False,execute,composite)
    output=probe(folder/'result.mp4');assert output['audio'];assert abs(output['duration']-probe(normalized)['duration'])<.15;assert result['frame_count']>5
    assert len((folder/'frames.jsonl').read_text().splitlines())==result['frame_count']
    with pytest.raises(Cancelled):run_video(a,source,a.validate({}),{},folder,lambda p,m:None,lambda:True,execute,composite)

def test_sequence_uses_actual_trajectory_and_time():
    p={'line_x':.5,'dwell':2,'event_order':['enter','cross','dwell'],'window':5,'roi':[0,0,100,100]};rules=EventRules(p,100,100)
    def track(x):return [{'id':1,'history':[[x,30]],'box':[x-5,20,x+5,40],'class_id':0}]
    assert [e['kind'] for e in rules.update(track(20),0)]==['enter']
    assert [e['kind'] for e in rules.update(track(70),1)]==['cross']
    events=rules.update(track(70),2.1);assert [e['kind'] for e in events]==['dwell','sequence_complete'];assert len(events[-1]['evidence'])==3
    rules.update([],3);assert not rules.state[1]['inside']

def test_video_raw_masks_preserve_holes_and_timestamps(tmp_path):
    import zipfile
    from app.algorithms.common import Result
    source=ROOT/'assets/examples/pedestrians.mp4'
    def segmented(id,frame,p,extra):
        h,w=frame.shape[:2];labels=np.zeros((h,w),np.uint16);labels[10:50,10:50]=3;labels[20:40,20:40]=0
        return Result(frame,{},arrays={'instance_labels':labels})
    a=REGISTRY['gray'];result=run_video(a,source,a.validate({}),{},tmp_path,lambda p,m:None,lambda:False,segmented,composite)
    assert result['mask_archive']=='masks.zip'
    with zipfile.ZipFile(tmp_path/'masks.zip') as z:
        assert len(z.namelist())==result['frame_count']
        mask=cv2.imdecode(np.frombuffer(z.read('instance_labels/000000.png'),np.uint8),cv2.IMREAD_UNCHANGED)
        assert mask.dtype==np.uint16 and mask[15,15]==3 and mask[25,25]==0
