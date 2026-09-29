"""SQLite 持久化：每次操作独立连接，WAL 支持任务与界面并发读取。"""
import json
import sqlite3
import time
from contextlib import contextmanager
from .config import DATA

@contextmanager
def connection():
    db=sqlite3.connect(DATA/'vision.sqlite3',timeout=30);db.row_factory=sqlite3.Row
    try:yield db;db.commit()
    finally:db.close()

def init():
    with connection() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, name TEXT, kind TEXT, path TEXT, metadata TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, algorithm TEXT, asset_id TEXT, request TEXT, status TEXT, progress REAL, message TEXT, result TEXT, created REAL, finished REAL);
        CREATE TABLE IF NOT EXISTS presets (id TEXT PRIMARY KEY, name TEXT, algorithm TEXT, content TEXT, created REAL);
        ''')
        db.execute("UPDATE jobs SET status='failed',message='服务在执行期间重启，请重新运行',finished=? WHERE status IN ('queued','running','cancelling')",(time.time(),))

def rows(sql,args=()):
    with connection() as db:return [dict(row) for row in db.execute(sql,args).fetchall()]

def execute(sql,args=()):
    with connection() as db:db.execute(sql,args)

def asset(id):
    found=rows('SELECT * FROM assets WHERE id=?',(id,))
    if not found:raise ValueError('素材不存在，请重新上传')
    item=found[0];item['metadata']=json.loads(item['metadata']);return item

def job(id):
    found=rows('SELECT * FROM jobs WHERE id=?',(id,))
    if not found:raise ValueError('实验不存在')
    result=found[0]
    for key in ['request','result']:
        if result[key]:result[key]=json.loads(result[key])
    return result
