"""测试产物隔离到临时目录，不污染用户实验历史。"""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_temp=tempfile.TemporaryDirectory(prefix='vision-lab-tests-')
os.environ['VISION_DATA']=_temp.name
os.environ['VISION_DEVICE']='cpu'

def pytest_sessionfinish(session,exitstatus):_temp.cleanup()
