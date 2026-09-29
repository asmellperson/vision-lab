import {useEffect,useState} from 'react'
import {ArrowRight,Download,CheckCircle2,AlertCircle,Database,RefreshCw,Plus,ArrowUp,ArrowDown,X,Play,Save,LoaderCircle,Search,ChevronDown,ChevronRight} from 'lucide-react'
import {api,errorMessage} from './api'
import type {Algorithm,Asset,Job,Model,Preset,Step} from './types'
import {defaults} from './types'
import {AssetPicker,ParameterControl,UploadBox,Notice} from './Controls'

// These groups organize the homepage only; all entries come from the existing registry.
const HOME_DOMAINS = [
  {id: 'traditional', name: '传统视觉', description: '从像素、边缘到形状与特征', categories: ['图像基础', '滤波与增强', '阈值与形态学', '边缘与形状', '几何与传统分割', '特征与匹配'], featured: ['gray', 'gaussian', 'threshold', 'canny', 'contours', 'template']},
  {id: 'deep', name: '深度学习', description: '识别、分割与图文理解', categories: ['深度学习识别', '文字与图文理解', '图像恢复', '模型学习与评估'], featured: ['classify', 'detect', 'instance', 'sam', 'pose', 'ocr']},
  {id: 'industrial', name: '工业视觉', description: '测量、比对与外观检测', categories: ['工业视觉'], featured: ['count', 'measure', 'industrial_template', 'difference', 'anomaly', 'char_check']},
  {id: 'spatial', name: '视频与三维', description: '运动、时序与空间几何', categories: ['视频与时序', '标定与三维'], featured: ['frame_diff', 'multi_track', 'events', 'calibrate', 'depth', 'pointcloud']},
]

export function Home({algorithms,assets,models,onSelect}:{algorithms:Algorithm[];assets:Asset[];models:Model[];onSelect:(id:string,asset?:Asset)=>void}){
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState<string[]>([])
  const keyword = query.trim().toLowerCase()
  const matches = algorithms.filter(a => [a.name, a.english, a.category, a.summary, a.uses, a.id].join(' ').toLowerCase().includes(keyword))
  const domainOf = (a: Algorithm) => HOME_DOMAINS.find(domain => domain.categories.includes(a.category))?.id || 'traditional'
  function exampleFor(a: Algorithm) {
    if (a.inputs[0] === 'video' || a.inputs[0] === 'pointcloud') return assets.find(asset => asset.kind === a.inputs[0] && asset.metadata.example)
    const id = a.category === '工业视觉' ? 'example-parts' : a.model ? 'example-bus' : 'example-fruits'
    return assets.find(asset => asset.id === id)
  }
  function launch(a: Algorithm) { onSelect(a.id, exampleFor(a)) }
  const common = [
    {id: 'canny', title: 'Canny 边缘检测', detail: '调节双阈值，观察轮廓与细节。'},
    {id: 'detect', title: '目标检测', detail: '定位物体，查看类别与置信度。'},
    {id: 'measure', title: '尺寸、角度与间隙', detail: '从零件轮廓读取几何测量结果。'},
  ]
  return <div className="lab-home">
    <header className="lab-home-header">
      <div><h1>实验入口</h1><p>选择算法，带着一张图开始探索。</p></div>
      <div className="lab-home-search" role="search" aria-label="首页算法搜索">
        <Search size={20}/><input type="search" aria-label="查找实验" placeholder="搜索算法、任务或关键词，例如 Canny、分割、测量" value={query}
          onChange={e => setQuery(e.target.value)} onKeyDown={e => {
            if (e.key === 'Enter' && !e.nativeEvent.isComposing && keyword && matches[0]) {e.preventDefault(); launch(matches[0])}
            if (e.key === 'Escape') setQuery('')
          }}/>
        {query && <button className="icon-button" aria-label="清空实验搜索" onClick={() => setQuery('')}><X size={17}/></button>}
      </div>
    </header>
    {keyword ? <section className="lab-search-results" aria-labelledby="home-search-title">
      <div className="lab-section-heading"><h2 id="home-search-title">搜索结果</h2><span role="status">找到 {matches.length} 个实验</span></div>
      {matches.length ? <div className="lab-result-list">{matches.map(a => <button key={a.id} className="lab-result" onClick={() => launch(a)}>
        <span><strong>{a.name}</strong><small>{a.category}</small><p>{a.summary}</p></span><ChevronRight size={17}/>
      </button>)}</div> : <div className="lab-search-empty"><h3>没有找到匹配的实验</h3><p>试试“边缘”“目标检测”或算法英文名，也可以清空搜索按方向浏览。</p><button onClick={() => setQuery('')}>查看全部方向</button></div>}
    </section> : <>
      <section className="lab-common" aria-labelledby="home-common-title">
        <div className="lab-section-heading"><h2 id="home-common-title">常用实验</h2><a href="#history">实验记录 <ChevronRight size={14}/></a></div>
        <div className="lab-common-list">{common.map(item => {
          const a = algorithms.find(a => a.id === item.id)
          if (!a) return null
          const example = exampleFor(a)
          const model = models.find(model => model.id === a.model)
          return <button className="lab-quick-experiment" key={a.id} onClick={() => launch(a)} aria-label={'打开' + item.title}>
            <div className="lab-thumbnail">{example ? <img src={example.url} alt={example.name}/> : <span>{a.english}</span>}</div>
            <div className="lab-quick-copy"><span>{a.category}</span><h3>{item.title}</h3><p>{item.detail}</p><small>{a.model && model?.state !== 'ready' ? '需先准备本地模型' : '使用示例开始'}<ArrowRight size={14}/></small></div>
          </button>
        })}</div>
      </section>
      <section className="lab-directory" aria-labelledby="home-directory-title">
        <div className="lab-section-heading"><h2 id="home-directory-title">按方向探索</h2><span>从基础处理到完整视觉任务</span></div>
        <div className="lab-domains">{HOME_DOMAINS.map(domain => {
          const items = algorithms.filter(a => domainOf(a) === domain.id)
          const isExpanded = expanded.includes(domain.id)
          const favorites = domain.featured.map(id => items.find(a => a.id === id)).filter((a): a is Algorithm => !!a)
          return <section className="lab-domain" key={domain.id} aria-labelledby={'domain-' + domain.id}>
            <h3 id={'domain-' + domain.id}>{domain.name}</h3><p>{domain.description}</p>
            <div className="lab-domain-links" id={'domain-links-' + domain.id}>
              {isExpanded ? [...new Set(items.map(a => a.category))].map(category => <div className="lab-domain-category" key={category}>
                <h4>{category}</h4>{items.filter(a => a.category === category).map(a => <button key={a.id} onClick={() => launch(a)}>{a.name}<ChevronRight size={14}/></button>)}
              </div>) : favorites.map(a => <button key={a.id} onClick={() => launch(a)}>{a.name}<ChevronRight size={14}/></button>)}
            </div>
            <button className="lab-domain-expand" aria-controls={'domain-links-' + domain.id} aria-expanded={isExpanded} onClick={() => setExpanded(isExpanded ? expanded.filter(id => id !== domain.id) : [...expanded, domain.id])}>
              {isExpanded ? '收起目录' : '查看全部 ' + items.length + ' 个实验'}<ChevronDown size={14}/>
            </button>
          </section>
        })}</div>
      </section>
      <footer className="lab-home-footer"><p>想把多个算法组合起来？</p><a href="#pipeline">打开处理流水线 <ArrowRight size={14}/></a></footer>
    </>}
  </div>
}

export function ModelsPage({models,refresh}:{models:Model[];refresh:()=>void}){
  const [error,setError]=useState('');const [tasks,setTasks]=useState<Job[]>([])
  async function download(id:string){try{const job=await api<Job>('/models/'+id+'/download',{});setTasks(old=>[job,...old]);refresh()}catch(e){setError(errorMessage(e))}}
  useEffect(()=>{const timer=setInterval(()=>{refresh();for(const task of tasks.filter(t=>['running','queued'].includes(t.status)))void api<Job>('/experiments/'+task.id).then(next=>setTasks(old=>old.map(j=>j.id===next.id?next:j))).catch(e=>setError(errorMessage(e)))},2500);return()=>clearInterval(timer)},[tasks])
  return <><header className="page-heading"><div><h1>本地模型管理</h1><p>权重、配置、词表与实际支持类别，一处查看。运行实验时不访问外部推理接口。</p></div><button onClick={()=>{void api('/models/all/release',{}).then(refresh).catch(e=>setError(errorMessage(e)))}}><RefreshCw size={16}/>释放全部模型</button></header><Notice>模型按需加载，缓存最多一个模型；重型推理串行执行。下载状态只表示文件就绪，首次运行会验证加载与任务适配。设备由 VISION_DEVICE 配置。</Notice>{error&&<div className="error-banner">{error}</div>}
    {tasks.some(t=>t.status==='failed')&&<div className="error-banner">{tasks.filter(t=>t.status==='failed').map(t=><p key={t.id}>{t.message}</p>)}</div>}
    <div className="models-grid">{models.map(model=><article className="model-card" key={model.id}><div className="model-card-head"><span className="model-icon"><Database size={21}/></span><div><h3>{model.name||model.id}</h3><span>{model.tasks.join(' · ')}</span></div><span className={'status-pill '+model.state}>{model.state==='ready'?<CheckCircle2 size={12}/>:<AlertCircle size={12}/>}{{ready:'文件就绪',missing:'缺少文件',loading_failed:'加载失败',blocked:'环境阻塞',downloading:'下载中'}[model.state]||model.state}</span></div><p className="model-classes">{model.classes}</p><dl><dt>版本</dt><dd>{model.version}</dd><dt>固定版本</dt><dd>{model.revision}</dd><dt>执行设备</dt><dd>{model.device}（支持 {model.devices.join(" / ")}）</dd><dt>许可证</dt><dd>{model.license}</dd><dt>路径</dt><dd>{model.local_path}</dd></dl>{model.reason&&<p className="model-error">{model.reason}</p>}{model.download?.state==='downloading'&&<><progress max={1} value={model.download.progress}/><small>{model.download.message}</small></>}
      <details><summary>文件清单与校验（{model.files.length}）</summary>{model.files.length?model.files.map(file=><div className="file-record" key={file.path}><strong>{file.path}</strong><span>{(file.size/1024/1024).toFixed(2)} MB</span><code>{file.sha256}</code></div>):<p className="muted">{model.missing.join('、')}</p>}</details><footer><a href={model.source} target="_blank" rel="noreferrer">官方来源 ↗</a><div>{model.loaded&&<button onClick={()=>{void api('/models/'+model.id+'/release',{}).then(refresh).catch(e=>setError(errorMessage(e)))}}>释放</button>}{model.state==='ready'?<button onClick={()=>{void api('/models/'+model.id+'/verify',{}).then(refresh).catch(e=>setError(errorMessage(e)))}}>校验文件</button>:<button disabled={model.state==='blocked'||model.state==='downloading'||tasks.some(t=>t.request.params.model===model.id&&['queued','running'].includes(t.status))} onClick={()=>void download(model.id)}><Download size={14}/>准备模型</button>}</div></footer></article>)}</div></>
}

export function HistoryPage({algorithms,onOpen}:{algorithms:Algorithm[];onOpen:(job:Job)=>void}){
  const [jobs,setJobs]=useState<Job[]>([]),[error,setError]=useState('');useEffect(()=>{const refresh=()=>void api<Job[]>('/experiments').then(setJobs).catch(e=>setError(errorMessage(e)));refresh();const timer=setInterval(refresh,3000);return()=>clearInterval(timer)},[])
  return <><header className="page-heading"><div><h1>实验记录</h1><p>保存输入、参数、执行状态与结果。打开一次实验，即可继续调整。</p></div></header>{error&&<p className="danger">{error}</p>}<div className="history-list">{jobs.length===0&&<div className="empty-state">暂无实验记录，请先选择算法运行实验。</div>}{jobs.map(job=><article key={job.id}>{job.result?.composite_url?<img src={job.result.composite_url} alt="实验缩略图"/>:<div className="history-icon"><LayersIcon/></div>}<div><h3>{algorithms.find(a=>a.id===job.algorithm)?.name||job.algorithm}</h3><span>{new Date(job.created*1000).toLocaleString('zh-CN')}</span><p>{job.message}</p></div><span className={'status-pill '+job.status}>{job.status}</span><div className="history-actions">{job.result?.downloads?.find(d=>d.name==='experiment.zip')&&<a href={job.result.downloads.find(d=>d.name==='experiment.zip')!.url}><Download size={16}/>下载</a>}{job.algorithm!=='model_download'&&<button onClick={()=>onOpen(job)}>打开实验 <ArrowRight size={14}/></button>}</div></article>)}</div></>
}
function LayersIcon(){return <Database size={26}/>}

export function PipelinePage({algorithms,assets,refreshAssets,initialJob}:{algorithms:Algorithm[];assets:Asset[];refreshAssets:()=>void;initialJob?:Job}){
  const [asset,setAsset]=useState<Asset|null>(assets.find(a=>initialJob?a.id===initialJob.asset_id:a.kind==='image')||null);const [steps,setSteps]=useState<Step[]>(initialJob?.request.steps||[{algorithm:'gray',params:{},enabled:true},{algorithm:'gaussian',params:{kernel:5},enabled:true},{algorithm:'otsu',params:{},enabled:true},{algorithm:'open',params:{kernel:5,iterations:1,shape:'ellipse'},enabled:true},{algorithm:'count',params:{threshold:127,min_area:100},enabled:true}]);const [selected,setSelected]=useState(0);const [job,setJob]=useState<Job|undefined>(initialJob);const [error,setError]=useState('');const [name,setName]=useState('');const [presets,setPresets]=useState<Preset[]>([]);const [addId,setAddId]=useState('gray');const busy=job&&['running','queued','cancelling'].includes(job.status);const current=steps[selected];const definition=algorithms.find(a=>a.id===current?.algorithm)
  useEffect(()=>{void api<Preset[]>('/presets').then(setPresets).catch(e=>setError(errorMessage(e)))},[])
  useEffect(()=>{if(!busy||!job)return;const timer=setInterval(()=>{void api<Job>('/experiments/'+job.id).then(setJob).catch(e=>setError(errorMessage(e)))},1000);return()=>clearInterval(timer)},[job?.id,busy])
  function update(index:number,patch:Partial<Step>){setSteps(steps.map((step,i)=>i===index?{...step,...patch}:step))}
  function move(index:number,delta:number){const next=[...steps];[next[index],next[index+delta]]=[next[index+delta],next[index]];setSteps(next);setSelected(index+delta)}
  async function run(){try{setError('');if(document.querySelector('textarea.invalid'))throw new Error('请先修正参数中的 JSON 格式');if(!asset)throw new Error('先选择图片');setJob(await api<Job>('/experiments',{algorithm:'pipeline',asset_id:asset.id,steps,params:{},extra:{}}))}catch(e){setError(errorMessage(e))}}
  async function save(){try{if(!name)throw new Error('请输入流程名称');await api('/presets',{name,algorithm:'pipeline',content:{steps}});setPresets(await api<Preset[]>('/presets'));setName('')}catch(e){setError(errorMessage(e))}}
  return <><header className="page-heading"><div><h1>处理流水线</h1><p>添加、排序或关闭步骤，查看每一步的变化。结构化输出须位于末端。</p></div><button className="primary" disabled={!!busy} onClick={()=>void run()}>{busy?<LoaderCircle size={17} className="spin"/>:<Play size={17}/>}运行流程</button></header><Notice>默认示例：灰度 → 去噪 → 阈值 → 形态学 → 轮廓计数。形态学要求灰度或掩膜输入；轮廓、计数、测量为终点。服务端会校验连接。</Notice>{error&&<div className="error-banner">{error}</div>}<div className="pipeline-layout"><section><div className="pipeline-input"><UploadBox compact accept="image/*" onUploaded={items=>{setAsset(items[0]);refreshAssets()}}/><select aria-label="流水线素材" value={asset?.id||''} onChange={e=>setAsset(assets.find(a=>a.id===e.target.value)||null)}><option value="">选择输入图片…</option>{assets.filter(a=>a.kind==='image').map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select></div><div className="step-list">{steps.map((step,i)=><div key={i} className={'pipeline-step '+(i===selected?'selected':'')+(!step.enabled?' disabled':'')} onClick={()=>setSelected(i)}><span>{String(i+1).padStart(2,'0')}</span><input aria-label={'启用步骤'+(i+1)} type="checkbox" checked={step.enabled} onChange={e=>update(i,{enabled:e.target.checked})}/><div><strong>{algorithms.find(a=>a.id===step.algorithm)?.name}</strong><small>输出：{algorithms.find(a=>a.id===step.algorithm)?.output_kind}</small></div><button title="上移" disabled={i===0} onClick={e=>{e.stopPropagation();move(i,-1)}}><ArrowUp size={14}/></button><button title="下移" disabled={i===steps.length-1} onClick={e=>{e.stopPropagation();move(i,1)}}><ArrowDown size={14}/></button><button title="删除步骤" onClick={e=>{e.stopPropagation();setSteps(steps.filter((_,n)=>n!==i));setSelected(0)}}><X size={14}/></button></div>)}</div><div className="input-add"><select aria-label="添加算法" value={addId} onChange={e=>setAddId(e.target.value)}>{algorithms.filter(a=>a.pipeline_compatible).map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select><button disabled={steps.length>=15} onClick={()=>{const a=algorithms.find(a=>a.id===addId)!;setSteps([...steps,{algorithm:a.id,params:defaults(a),enabled:true}]);setSelected(steps.length)}}><Plus size={16}/>添加</button></div><div className="preset-box"><h4>保存与复用流程</h4><select aria-label="加载流水线" value="" onChange={e=>{const p=presets.find(p=>p.id===e.target.value);if(p?.content.steps){setSteps(p.content.steps);setSelected(0)}}}><option value="">加载流程…</option>{presets.filter(p=>p.algorithm==='pipeline').map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select><div className="input-add"><input placeholder="流程名称" value={name} onChange={e=>setName(e.target.value)}/><button onClick={()=>void save()}><Save size={15}/>保存</button></div></div></section><section className="pipeline-params"><h3>{definition?.name||'请选择步骤'}</h3>{definition?.params.map(p=><ParameterControl key={p.key} definition={p} value={current.params[p.key]??p.default} onChange={value=>update(selected,{params:{...current.params,[p.key]:value}})}/>)}<p className="muted">{definition?.principle}</p></section></div>{job&&<div className={'job-status '+job.status}><div><strong>{job.status}</strong><span>{job.message}</span>{busy&&<button onClick={()=>{void api<Job>('/experiments/'+job.id+'/cancel',{}).then(setJob)}}>取消</button>}</div><progress max={1} value={job.progress}/></div>}<div className="pipeline-results">{asset&&<figure><img src={asset.url} alt="流水线原图"/><figcaption>输入 · {asset.name}</figcaption></figure>}{job?.status==='completed'&&job.result?.steps?.map(step=><figure key={step.step}><img src={step.image_url} alt={step.algorithm}/><figcaption>{step.step+1} · {algorithms.find(a=>a.id===step.algorithm)?.name}</figcaption></figure>)}</div>{job?.result?.downloads?.map(d=><a className="download-chip" href={d.url} key={d.name} download>{d.name}</a>)}</>
}
