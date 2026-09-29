#!/usr/bin/env python3
"""按任务模块、单模型或全部已接入模型预下载，不执行推理。"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.algorithms.registry import load,REGISTRY
from app.models import download
from app.model_manifest import MODELS

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--all',action='store_true');group.add_argument('--module',help='中文模块名，例如 深度学习识别');group.add_argument('--model');args=parser.parse_args();load()
    ids=list(MODELS) if args.all else [args.model] if args.model else sorted({a.model for a in REGISTRY.values() if a.category==args.module and a.model})
    results={}
    for id in ids:
        print(f'准备 {id}',flush=True)
        try:download(id,lambda p,m:print(f'  {p:.0%} {m}',flush=True));results[id]='ready'
        except Exception as exc:results[id]=str(exc);print(f'  阻塞：{exc}',flush=True)
    print(json.dumps(results,ensure_ascii=False,indent=2));return int(any(v!='ready' for v in results.values()))
if __name__=='__main__':raise SystemExit(main())
