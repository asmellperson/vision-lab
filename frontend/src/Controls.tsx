import {useEffect,useState} from 'react'
import {RotateCcw,Upload,FileImage,Info} from 'lucide-react'
import {api,errorMessage} from './api'
import type {Parameter,Asset} from './types'

export function ParameterControl({definition:p,value,onChange}:{definition:Parameter;value:unknown;onChange:(value:unknown)=>void}){
  const [draft,setDraft]=useState('');const [invalid,setInvalid]=useState(false)
  useEffect(()=>{setDraft(JSON.stringify(value,null,2));setInvalid(false)},[value])
  return <div className="parameter"><label htmlFor={'param-'+p.key}>{p.label}<button className="icon-button" title="重置此参数" onClick={()=>onChange(p.default)}><RotateCcw size={12}/></button></label>
    {p.type==='number'?<><div className="range-row"><input id={'param-'+p.key} type="range" min={p.min} max={p.max} step={p.step} value={Number(value)} onChange={e=>onChange(Number(e.target.value))}/><input aria-label={p.label+'数值'} className="number" type="number" min={p.min} max={p.max} step={p.step} value={Number(value)} onChange={e=>onChange(Number(e.target.value))}/></div><div className="range-label"><span>{p.min}</span><span>{p.max}</span></div></>:
    p.type==='select'?<select id={'param-'+p.key} value={String(value)} onChange={e=>onChange(e.target.value)}>{p.options.map(option=><option key={option}>{option}</option>)}</select>:
    p.type==='json'?<textarea id={'param-'+p.key} className={invalid?'invalid':''} rows={5} value={draft} onChange={e=>{setDraft(e.target.value);try{onChange(JSON.parse(e.target.value));setInvalid(false)}catch{setInvalid(true)}}}/>:
    <div className="range-row">{p.key==='background'&&<input aria-label="背景颜色" type="color" value={String(value)} onChange={e=>onChange(e.target.value)}/>}<input id={'param-'+p.key} type="text" value={String(value??'')} onChange={e=>onChange(e.target.value)}/></div>}
    {invalid&&<small className="danger">JSON 格式尚未完整，请修正后运行。</small>}<small>{p.help}</small></div>
}

export function UploadBox({onUploaded,compact=false,multiple=false,accept}:{onUploaded:(assets:Asset[])=>void;compact?:boolean;multiple?:boolean;accept?:string}){
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [over,setOver]=useState(false)
  async function upload(files:FileList|null){if(!files?.length)return;setBusy(true);setError('');try{const assets:Asset[]=[];for(const file of Array.from(files)){const form=new FormData();form.append('file',file);assets.push(await api<Asset>('/assets',form))}onUploaded(assets)}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
  return <div className={'upload-box '+(compact?'compact ':'')+(over?'dragover':'')} onDragOver={e=>{e.preventDefault();setOver(true)}} onDragLeave={()=>setOver(false)} onDrop={e=>{e.preventDefault();setOver(false);if(!busy)void upload(e.dataTransfer.files)}}>
    <label><input type="file" accept={accept} multiple={multiple} disabled={busy} onChange={e=>{void upload(e.target.files);e.target.value=''}}/><Upload size={compact?17:28}/><strong>{busy?'正在上传与准备…':compact?'添加文件':'拖入图片或视频，开始一次实验'}</strong>{!compact&&<span>或点击选择文件 · JPG / PNG / MP4 / 点云 · 最大 256 MB</span>}</label>{error&&<p className="danger">{error}</p>}</div>
}

export function AssetPicker({assets,selected,onSelect,kind,compact=false}:{assets:Asset[];selected?:string;onSelect:(asset:Asset)=>void;kind?:string;compact?:boolean}){
  return <div className={'example-list '+(compact?'small':'')}>{assets.filter(a=>!kind||a.kind===kind).map(asset=><button key={asset.id} className={'example '+(asset.id===selected?'selected':'')} onClick={()=>onSelect(asset)} title={asset.name}>
    {asset.kind==='image'||asset.kind==='video'?<img src={asset.kind==='video'?asset.poster:asset.url} alt={asset.name}/>:<FileImage size={32}/>}<span>{asset.name}</span>{asset.kind==='video'&&<em>视频</em>}</button>)}</div>
}

export function Notice({children}:{children:React.ReactNode}){return <div className="notice"><Info size={16}/><span>{children}</span></div>}
