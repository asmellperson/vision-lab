import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdtemp, writeFile, rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {fileURLToPath, pathToFileURL} from 'node:url'
import path from 'node:path'
import {build} from 'esbuild'

const frontend = fileURLToPath(new URL('../', import.meta.url))
const root = path.resolve(frontend, '..')
const python = process.env.VISION_PYTHON || 'python3'
const algorithms = JSON.parse(execFileSync(python, ['-c',
  'import json; from app.algorithms.registry import load, REGISTRY; load(); print(json.dumps([a.dict() for a in REGISTRY.values()]))',
], {cwd: root, env: {...process.env, PYTHONPATH: path.join(root, 'backend')}, encoding: 'utf8'}))
const folder = await mkdtemp(path.join(tmpdir(), 'vision-learning-'))
try {
  const bundle = path.join(folder, 'learning.mjs')
  await build({stdin: {contents: 'export * from "./src/learning/python"; export * from "./src/learning/lessons";', resolveDir: frontend}, bundle: true, platform: 'node', format: 'esm', outfile: bundle})
  const {lessonIds, pythonExampleIds, getLesson, getPythonExample} = await import(pathToFileURL(bundle).href)
  const ids = algorithms.map(a => a.id).sort()
  assert.deepEqual([...lessonIds].sort(), ids, '每个算法都需要独立的学习说明')
  assert.deepEqual([...pythonExampleIds].sort(), ids, '每个算法都需要 Python 用法')
  const examples = {}
  for (const algorithm of algorithms) {
    const lesson = getLesson(algorithm.id)
    assert.ok(lesson.goal.length > 20 && lesson.idea.length > 25, algorithm.id)
    assert.equal(lesson.reading.length, 2, algorithm.id)
    assert.ok(lesson.reading.every(text => text.length > 20), algorithm.id)
    const example = getPythonExample(algorithm, {})
    assert.ok(example.note && example.dependencies, algorithm.id)
    assert.doesNotMatch(example.code, /from app\.|import app\./, algorithm.id)
    assert.doesNotMatch(example.code, /\{\{params\}\}/, algorithm.id)
    examples[algorithm.id] = example.code
  }
  assert.equal(new Set(algorithms.map(a => JSON.stringify(getLesson(a.id)))).size, algorithms.length, '学习说明不可整段重复')
  const canny = algorithms.find(a => a.id === 'canny')
  const special = {low: 23, high: 111, custom: {enabled: true, disabled: false, missing: null, text: '引号"\n$& ${test} \\路径'}}
  examples.parameter_serialization = getPythonExample(canny, special).code
  await writeFile(path.join(folder, 'examples.json'), JSON.stringify(examples))
  const syntax = execFileSync(python, ['-c', `
import ast, json, sys
examples = json.load(open(sys.argv[1]))
for name, source in examples.items():
    tree = ast.parse(source, filename=name + '.py')
    value = next((n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'params' for t in n.targets)), ast.Dict(keys=[], values=[]))
    params = ast.literal_eval(value)
    required = {n.slice.value for n in ast.walk(tree) if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == 'params' and isinstance(n.slice, ast.Constant)}
    assert not required - params.keys() - {'roi', 'points', 'polygon', 'mask_points', 'model_id'}, (name, required - params.keys())
    if name == 'parameter_serialization':
        assert params['low'] == 23 and params['high'] == 111
        assert params['custom']['enabled'] is True and params['custom']['disabled'] is False and params['custom']['missing'] is None
        assert params['custom'] == json.loads(sys.argv[2])['custom']
print('Python syntax and parameter serialization passed:', len(examples))
`, path.join(folder, 'examples.json'), JSON.stringify(special)], {encoding: 'utf8'})
  console.log(syntax.trim())
  if (process.env.RUN_PYTHON_EXAMPLES === '1') {
    console.log(execFileSync(python, [path.join(frontend, 'tests/run-python-examples.py'), path.join(folder, 'examples.json')], {cwd: root, encoding: 'utf8', maxBuffer: 4 * 1024 * 1024}).trim())
  }
  console.log(`Learning content coverage passed: ${algorithms.length} algorithms`)
} finally {
  await rm(folder, {recursive: true, force: true})
}
