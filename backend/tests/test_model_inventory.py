"""校验后修复必须重新获取损坏文件，不能将损坏文件重新登记为正确版本。"""
import io
import json
from app import models

def test_repair_changed_bytes_and_keep_verified_files(tmp_path,monkeypatch):
    meta={'id':'test-local','files':{'weights.bin':'https://example.invalid/weights'},'version':'v1','source':'https://example.invalid','kind':'raw','devices':['cpu']}
    monkeypatch.setattr(models,'MODEL_DIR',tmp_path);monkeypatch.setitem(models.MODELS,'test-local',meta)
    monkeypatch.setattr(models,'ERRORS',{});monkeypatch.setattr(models,'DOWNLOADS',{})
    root=tmp_path/'test-local';root.mkdir();file=root/'weights.bin';file.write_bytes(b'good')
    inventory={'revision':'v1','files':[{'path':'weights.bin','size':4,'sha256':models.sha256(file)}]};(root/'inventory.json').write_text(json.dumps(inventory));file.write_bytes(b'bad!')
    assert models.status('test-local',verify=True)['state']=='loading_failed'
    class Response(io.BytesIO):headers={'Content-Length':'4'}
    calls=[]
    def fetch(*args,**kwargs):calls.append(1);return Response(b'good')
    monkeypatch.setattr(models.urllib.request,'urlopen',fetch)
    assert models.download('test-local')['state']=='ready' and file.read_bytes()==b'good'
    models.download('test-local');assert len(calls)==1
