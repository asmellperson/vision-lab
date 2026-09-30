#!/usr/bin/python3
"""Refresh editable Word TOC and page fields using LibreOffice UNO."""
import pathlib
import subprocess
import time
import uuid
import uno
from com.sun.star.beans import PropertyValue

def props(**kw):
    result=[]
    for name,value in kw.items():
        p=PropertyValue();p.Name=name;p.Value=value;result.append(p)
    return tuple(result)

def main():
    output=pathlib.Path(__file__).resolve().parent.parent
    name='visionlab_docs_'+uuid.uuid4().hex
    profile=pathlib.Path('/tmp')/name
    proc=subprocess.Popen(['soffice','--headless','--norestore','--nodefault',f'-env:UserInstallation={profile.as_uri()}',f'--accept=pipe,name={name};urp;StarOffice.ComponentContext'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        local=uno.getComponentContext()
        resolver=local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',local)
        remote=None
        for _ in range(100):
            try:remote=resolver.resolve(f'uno:pipe,name={name};urp;StarOffice.ComponentContext');break
            except Exception:
                if proc.poll() is not None:raise RuntimeError(proc.stderr.read().decode())
                time.sleep(.2)
        if remote is None:raise RuntimeError('LibreOffice UNO connection timed out')
        desktop=remote.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',remote)
        for path in sorted(output.glob('*.docx')):
            doc=desktop.loadComponentFromURL(path.as_uri(),'_blank',0,props(Hidden=True,ReadOnly=False,UpdateDocMode=3))
            if doc is None:raise RuntimeError(f'Cannot load {path}')
            doc.refresh()
            for _ in range(2):
                indexes=doc.getDocumentIndexes()
                for i in range(indexes.getCount()):indexes.getByIndex(i).update()
                doc.getTextFields().refresh()
            doc.store()
            doc.close(True)
            print('Updated TOC and fields:',path.name,flush=True)
        desktop.terminate()
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill()

if __name__=='__main__':main()
