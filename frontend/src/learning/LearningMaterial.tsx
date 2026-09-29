import {useEffect, useState} from 'react'
import {api, errorMessage} from '../api'
import type {Algorithm, Asset, Model} from '../types'
import {Notice} from '../Controls'
import {getLesson} from './lessons'
import {getPythonExample} from './python'
import './learning.css'

export function AlgorithmGuide({algorithm: a, model}: {algorithm: Algorithm; model?: Model}) {
  const lesson = getLesson(a.id)
  return <div className="learning-content algorithm-guide">
    <div>
      <h3>解决什么问题</h3><p>{lesson?.goal || a.summary}</p>
      <h3>怎样理解原理</h3><p>{lesson?.idea || a.principle}</p>
      <h3>可以用在哪里</h3><p>{a.uses}</p>
    </div>
    <div>
      <h3>怎么解读结果</h3>
      {lesson ? lesson.reading.map((text, index) => <p key={index}>{text}</p>) : <p>{a.failures}</p>}
      {a.model && <><h3>模型支持范围</h3><p>{model?.classes || '请在模型管理中查看当前模型的支持范围。'}</p></>}
      {a.id.startsWith('eval_') && <Notice>{a.id === 'eval_classification'
        ? '标注格式：{"truth":[0,1,1],"prediction":[0,0,1]}。两个数组按同一批样本的顺序一一对应。'
        : a.id === 'eval_detection'
          ? 'truth / prediction 为对象数组；每项包含 image_id、class_id、box:[x1,y1,x2,y2]，预测另加 score。坐标以原图像素为单位。'
          : '二值模式以 127 分割；多类别模式使用灰度标签 ID，按真值的忽略标签过滤像素。'}</Notice>}
    </div>
  </div>
}

export function PythonExample({algorithm, params, extra, asset}: {
  algorithm: Algorithm; params: Record<string, unknown>; extra: Record<string, string[]>; asset: Asset | null
}) {
  const [mode, setMode] = useState<'algorithm' | 'reproduce'>('algorithm')
  const [reproduction, setReproduction] = useState<{request: string; code?: string; error?: string}>()
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState('')
  const example = getPythonExample(algorithm, params)
  const request = JSON.stringify({algorithm: algorithm.id, asset_id: asset?.id || '', params, extra})
  const current = reproduction?.request === request ? reproduction : undefined
  const code = mode === 'algorithm' ? example?.code : asset ? current?.code : undefined
  const loading = mode === 'reproduce' && !!asset && !current

  useEffect(() => {
    if (mode !== 'reproduce' || !asset) return
    let active = true
    void api<{code: string}>('/code', JSON.parse(request)).then(result => {
      if (active) setReproduction({request, code: result.code})
    }).catch(error => {
      if (active) setReproduction({request, error: errorMessage(error)})
    })
    return () => { active = false }
  }, [mode, request, asset?.id])
  useEffect(() => {setCopied(false); setCopyError('')}, [mode, code])

  async function copy() {
    if (!code) return
    try {await navigator.clipboard.writeText(code); setCopied(true); setCopyError('')}
    catch {setCopyError('复制失败，请选中下方代码手动复制。')}
  }

  return <div className="python-example">
    <div className="python-options" role="group" aria-label="Python 示例类型">
      <button aria-pressed={mode === 'algorithm'} onClick={() => setMode('algorithm')}>算法调用</button>
      <button aria-pressed={mode === 'reproduce'} onClick={() => setMode('reproduce')}>复现实验</button>
    </div>
    <p className="python-help">{mode === 'algorithm'
      ? '直接使用 Python 库完成当前算法，参数随右侧设置更新。文件路径请替换为本地文件；图中选取的坐标也会写入示例。'
      : '使用本项目执行库，复现当前素材、专用输入与参数；请在项目的 Python 环境中运行。'}</p>
    {mode === 'algorithm' && example && <p className="python-help">{example.note}</p>}
    <div className="code-panel algorithm-code">
      <div><span>{mode === 'algorithm' ? '依赖：' + (example?.dependencies || '暂无示例') : '本项目 · app.engine'}</span>
        <button disabled={!code} onClick={() => void copy()}>{copied ? '已复制' : '复制代码'}</button></div>
      {mode === 'reproduce' && current?.error ? <p className="python-error" role="alert">生成失败：{current.error}</p>
        : <pre aria-label="Python 示例代码" aria-busy={loading}><code>{code || (loading ? '正在生成复现脚本…' : mode === 'reproduce' ? '请先选择实验素材。' : '此算法暂未提供 Python 示例。')}</code></pre>}
    </div>
    {copyError && <p className="python-error" role="alert">{copyError}</p>}
  </div>
}
