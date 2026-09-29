import {chromium, expect} from '@playwright/test'
import {mkdir, writeFile} from 'node:fs/promises'
import path from 'node:path'

const base = process.env.BASE_URL || 'http://127.0.0.1:5178'
const output = path.resolve('../docs/screenshots/learning')
await mkdir(output, {recursive: true})
const browser = await chromium.launch({executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser', headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage', '--no-proxy-server']})
const context = await browser.newContext({viewport: {width: 1440, height: 1000}, permissions: ['clipboard-read', 'clipboard-write']})
const page = await context.newPage()
const errors = [], checks = []
page.on('pageerror', error => errors.push(error.message))
const code = page.getByLabel('Python 示例代码')
async function noOverflow() {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
}
async function capture(name) {
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  await page.screenshot({path: path.join(output, name + '.png'), fullPage: true})
}
try {
  await page.goto(base + '/#algorithm/canny', {waitUntil: 'networkidle'})
  await expect(page.getByRole('heading', {name: '解决什么问题'})).toBeVisible()
  await expect(page.getByRole('heading', {name: '怎样理解原理'})).toBeVisible()
  await expect(page.getByRole('heading', {name: '怎么解读结果'})).toBeVisible()
  await expect(page.locator('.algorithm-guide')).toContainText('白色表示保留下来的边缘')
  await expect(page.getByText('操作步骤', {exact: true})).toHaveCount(0)
  await page.getByRole('tab', {name: 'Python 示例'}).click()
  await expect(code).toContainText('cv2.Canny')
  await expect(code).not.toContainText('app.engine')
  await expect(page.getByRole('button', {name: '复制代码', exact: true})).toBeEnabled()
  await page.getByRole('button', {name: '复制代码', exact: true}).click()
  await expect(page.getByRole('button', {name: '已复制', exact: true})).toBeVisible()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('cv2.Canny')
  await page.getByRole('button', {name: '复现实验', exact: true}).click()
  await expect(code).toContainText('请先选择实验素材')
  await expect(page.getByRole('button', {name: '复制代码', exact: true})).toBeDisabled()
  await page.getByRole('button', {name: '载入完整示例'}).click()
  await expect(code).toContainText('from app.engine import')
  await page.getByRole('button', {name: '算法调用', exact: true}).click()
  await page.locator('.parameter input[type=number]').first().fill('23')
  await expect(code).toContainText('"low": 23')
  await capture('canny-python')
  checks.push('无素材可读算法代码、真实剪贴板复制、当前参数同步；复现脚本沿用原接口')

  // A delayed error response must not leave stale code available for copying.
  await page.route('**/api/code', async route => {
    await new Promise(resolve => setTimeout(resolve, 250))
    await route.fulfill({status: 503, json: {detail: '测试：代码服务暂时不可用'}})
  })
  await page.getByRole('button', {name: '复现实验', exact: true}).click()
  await expect(code).toContainText('正在生成')
  await expect(page.getByRole('button', {name: '复制代码', exact: true})).toBeDisabled()
  await expect(page.locator('.python-error')).toContainText('测试：代码服务暂时不可用')
  await page.getByRole('button', {name: '算法调用', exact: true}).click()
  await expect(code).toContainText('cv2.Canny')
  await page.unroute('**/api/code')
  checks.push('模拟复现接口延迟和 503：显示加载与错误，禁用旧代码复制，算法用法仍可查看')

  for (const [id, call, interpretation] of [
    ['threshold', 'cv2.threshold', '白色'],
    ['open', 'cv2.MORPH_OPEN', '白'],
    ['contour_area', 'cv2.contourArea', 'area_px2'],
    ['classify', 'model(x).softmax', '概率'],
    ['multi_track', 'YOLO', '编号'],
  ]) {
    await page.goto(base + '/#algorithm/' + id)
    await expect(page.locator('.algorithm-guide')).toContainText(interpretation)
    if (id === 'threshold') await capture('threshold-guide')
    await page.getByRole('tab', {name: 'Python 示例'}).click()
    await expect(code).toContainText(call)
    await expect(code).not.toContainText('app.engine')
    if (id === 'classify') await capture('classify-python')
    await noOverflow()
  }
  checks.push('阈值、开运算、轮廓面积、分类、跟踪显示各自讲解与实际 Python 调用')

  await page.goto(base + '/#algorithm/canny')
  await capture('canny-guide')
  for (const width of [768, 390, 320]) {
    await page.setViewportSize({width, height: 844})
    await noOverflow()
    await page.getByRole('tab', {name: 'Python 示例'}).click()
    await noOverflow()
    const overflow = await code.evaluate(element => ({inside: element.scrollWidth > element.clientWidth, mode: getComputedStyle(element).overflowX}))
    if (overflow.inside) expect(overflow.mode).toBe('auto')
    if (width === 390) await capture('mobile-python')
    await page.getByRole('tab', {name: '原理与结果解读'}).click()
    if (width === 390) await capture('mobile-guide')
  }
  checks.push('768 / 390 / 320 px 学习区和代码无页面横向溢出，长代码在代码框内滚动')
  expect(errors).toEqual([])
  const report = {status: 'passed', checks, runtimeErrors: errors}
  await writeFile('../docs/learning-browser-validation.json', JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
} finally {await browser.close()}
