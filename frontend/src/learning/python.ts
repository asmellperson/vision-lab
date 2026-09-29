import type { Algorithm } from '../types'
import { defaults } from '../types'
import { recipes } from './pythonShared'
import './pythonClassical'
import './pythonGeometry'
import './pythonModels'
import './pythonVideo'

// Python literals, not JSON: booleans and null must become True/False/None.
function pythonLiteral(value: unknown): string {
  if (value == null) return 'None'
  if (typeof value === 'boolean') return value ? 'True' : 'False'
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : 'None'
  if (typeof value === 'string') return JSON.stringify(value)
  if (Array.isArray(value)) return '[' + value.map(pythonLiteral).join(', ') + ']'
  if (typeof value === 'object') return '{' + Object.entries(value).map(([key, item]) => `${pythonLiteral(key)}: ${pythonLiteral(item)}`).join(', ') + '}'
  return 'None'
}

export const pythonExampleIds = Object.keys(recipes)
export function getPythonExample(algorithm: Algorithm, params: Record<string, unknown>) {
  const recipe = recipes[algorithm.id]
  if (!recipe) return undefined
  const values = { ...defaults(algorithm), ...params }
  return {
    ...recipe,
    code: `# ${algorithm.name}：直接调用算法的 Python 示例\n# 依赖：${recipe.dependencies}\n\n` +
      recipe.code.replaceAll('{{params}}', () => pythonLiteral(values)),
  }
}
