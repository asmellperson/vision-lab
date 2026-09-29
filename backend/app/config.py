"""项目路径、设备和资源上限；默认只监听本机。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv('VISION_DATA', ROOT / 'data')).resolve()
MODELS = Path(os.getenv('VISION_MODELS', ROOT / 'models')).resolve()
DEVICE = os.getenv('VISION_DEVICE', 'cpu')
MAX_UPLOAD = int(os.getenv('VISION_MAX_UPLOAD_MB', '256')) * 1024 * 1024
MAX_PIXELS = 24_000_000
for directory in (DATA, DATA / 'uploads', DATA / 'results', MODELS):
    directory.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('YOLO_CONFIG_DIR',str(DATA/'runtime'/'ultralytics'))
os.environ.setdefault('MPLCONFIGDIR',str(DATA/'runtime'/'matplotlib'))
os.environ.setdefault('NO_ALBUMENTATIONS_UPDATE','1')
