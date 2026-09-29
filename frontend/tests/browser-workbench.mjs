import { chromium, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const base = process.env.BASE_URL || 'http://127.0.0.1:5178'
const output = path.resolve('../docs/screenshots/workbench')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser',
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--no-proxy-server'],
})
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 })
const checks = [], errors = [], screenshots = []
page.on('pageerror', error => errors.push(error.message))
async function capture(name) {
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  await page.screenshot({ path: path.join(output, name + '.png'), fullPage: true })
  screenshots.push(name + '.png')
}
async function noOverflow() {
  const dimensions = await page.evaluate(() => ({
    viewport: innerWidth, document: document.documentElement.scrollWidth,
    overflowing: [...document.querySelectorAll('main *')].filter(element => element.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(element => element.className),
  }))
  expect(dimensions.document, JSON.stringify(dimensions)).toBeLessThanOrEqual(dimensions.viewport + 1)
}
try {
  await page.goto(base + '/#algorithm/canny', { waitUntil: 'networkidle' })
  await expect(page.getByRole('heading', { name: /Canny/ })).toBeVisible()
  await expect(page.getByRole('button', { name: '运行实验', exact: true })).toBeDisabled()
  await capture('empty')
  await page.getByRole('button', { name: '载入完整示例' }).click()
  await expect(page.locator('.image-empty')).toContainText('在这里观察边缘')
  await expect(page.getByRole('button', { name: '滑动', exact: true })).toBeDisabled()
  await noOverflow()
  await capture('ready')
  checks.push('真实示例加载；无素材时禁止运行，未运行时不伪装处理结果')

  await page.getByLabel('搜索算法').fill('Canny')
  await expect(page.locator('.algorithm-children a')).toHaveCount(1)
  await expect(page.locator('.algorithm-children a')).toHaveAttribute('aria-current', 'page')
  await page.getByLabel('搜索算法').fill('不存在的算法名称')
  await expect(page.locator('.algorithm-nav')).toContainText('没有匹配的算法')
  await page.getByLabel('清除算法搜索').click()
  checks.push('算法搜索、无匹配提示、清空与当前路由高亮')

  const controls = page.locator('.parameter input[type=number]')
  const first = controls.first()
  const original = await first.inputValue()
  const max = Number(await first.getAttribute('max'))
  const changed = String(Math.min(max, Number(original) + 10))
  await first.fill(changed)
  await page.getByLabel('调参预览').check()
  await expect(page.locator('.image-label em')).toHaveText('低分辨率预览', { timeout: 20000 })
  await expect(first).toHaveValue(changed)
  await page.getByLabel('调参预览').uncheck()
  await page.getByTitle('重置全部参数').click()
  await expect(first).toHaveValue(original)
  checks.push('真实参数修改、低分辨率预览与恢复默认值')

  await page.getByRole('button', { name: '运行实验', exact: true }).click()
  await expect(page.locator('.job-status.completed')).toBeVisible({ timeout: 30000 })
  await expect(page.locator('.image-empty')).toHaveCount(0)
  await expect(page.locator('.download-row a').filter({ hasText: '全部结果 ZIP' })).toBeVisible()
  const downloadHref = await page.locator('.download-row a').filter({ hasText: '结果图片' }).getAttribute('href')
  const download = await page.request.get(base + downloadHref)
  expect(download.ok()).toBe(true)
  expect(download.headers()['content-type']).toContain('image')
  await page.waitForFunction(() => [...document.querySelectorAll('.image-viewport image')].every(image => {
    const url = image.getAttribute('href')
    return url && performance.getEntriesByName(new URL(url, location.href).href).length > 0
  }))
  await capture('desktop')
  checks.push('真实 Canny 运行成功，原图与结果并排显示，结果图片可下载')

  const before = (await page.locator('.viewer').boundingBox()).width
  await page.getByRole('button', { name: '收起参数' }).click()
  await expect(page.getByRole('complementary', { name: '实验参数' })).toBeHidden()
  expect((await page.locator('.viewer').boundingBox()).width).toBeGreaterThan(before + 200)
  await expect(page.getByRole('button', { name: '运行实验', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: '滑动', exact: true }).click()
  await page.getByLabel('对比滑块').fill('35')
  await page.getByLabel('同步缩放').fill('1.5')
  await expect(page.locator('.zoom')).toContainText('150%')
  await page.getByTitle('重置视图').click()
  await expect(page.getByLabel('同步缩放')).toHaveValue('1')
  await page.getByRole('button', { name: '结果', exact: true }).click()
  await expect(page.locator('.image-pane')).toHaveCount(1)
  await capture('focused-result')
  await page.getByRole('button', { name: '展开参数' }).click()
  await expect(first).toHaveValue(original)
  await page.getByRole('button', { name: '并排', exact: true }).click()
  checks.push('折叠扩展图像空间且保留参数；滑动、单结果、同步缩放与重置正常')

  await page.getByRole('tab', { name: 'Python 示例' }).click()
  await expect(page.locator('.code-panel pre')).toContainText('cv2.Canny')
  await capture('python')
  await page.getByRole('tab', { name: 'Python 示例' }).press('ArrowRight')
  await expect(page.getByRole('tab', { name: '结果数据' })).toBeFocused()
  await expect(page.getByRole('tab', { name: '结果数据' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator('.data-panel pre')).toBeVisible()
  await page.getByRole('tab', { name: '同素材对比' }).click()
  await expect(page.locator('.comparison-panel .chips input').first()).toBeVisible()
  await page.locator('.comparison-panel .chips input').first().check()
  await expect(page.locator('.compare-grid img')).toHaveCount(1)
  await page.getByRole('tab', { name: '原理与结果解读' }).click()
  await first.fill(changed)
  await expect(page.locator('.notice').filter({ hasText: '参数已修改' })).toBeVisible()
  await page.getByTitle('重置全部参数').click()
  checks.push('当前参数代码、结果数据、历史对比与键盘标签切换；修改参数后提示旧结果')

  for (const width of [1920, 1280, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: width < 700 ? 844 : 1000 })
    await noOverflow()
    if (width === 1024) await capture('tablet')
    if (width === 390) {
      await page.getByRole('button', { name: '收起参数' }).click()
      await capture('mobile')
      await page.getByRole('button', { name: '切换侧栏' }).click()
      await expect(page.getByLabel('搜索算法')).toBeVisible()
      await page.getByLabel('搜索算法').fill('gray')
      await page.locator('.algorithm-children a[href="#algorithm/gray"]').click()
      await expect(page.locator('.sidebar-backdrop')).toHaveCount(0)
      await expect(page).toHaveURL(/#algorithm\/gray$/)
      await page.goBack()
      await expect(page.getByRole('heading', { name: /Canny/ })).toBeVisible()
    }
  }
  checks.push('1920 / 1280 / 1024 / 768 / 390 / 320 px 无页面横向溢出；移动端搜索与导航可用')

  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '载入完整示例' }).click()
  const mockJob = { id: 'ui-state-check', algorithm: 'canny', status: 'running', progress: .4, message: '正在计算边缘', created: Date.now() / 1000 }
  await page.route('**/api/experiments', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    const request = route.request().postDataJSON()
    Object.assign(mockJob, { asset_id: request.asset_id, request })
    await route.fulfill({ json: mockJob })
  })
  await page.route('**/api/experiments/ui-state-check', route => route.fulfill({ json: mockJob }))
  await page.route('**/api/experiments/ui-state-check/cancel', route => {
    Object.assign(mockJob, { status: 'cancelled', message: '任务已取消' })
    return route.fulfill({ json: mockJob })
  })
  await page.getByRole('button', { name: '运行实验', exact: true }).click()
  await expect(page.locator('.job-status.running')).toBeVisible()
  await expect(page.locator('.image-empty')).toContainText('正在提取边缘')
  await expect(page.getByRole('button', { name: '运行实验', exact: true })).toBeDisabled()
  await capture('running-simulated')
  await page.getByRole('button', { name: '收起参数' }).click()
  await page.getByRole('button', { name: '取消任务', exact: true }).click()
  await expect(page.locator('.job-status.cancelled')).toBeVisible()
  await page.unroute('**/api/experiments')
  await page.unroute('**/api/experiments/ui-state-check')
  await page.unroute('**/api/experiments/ui-state-check/cancel')
  await page.route('**/api/experiments', route => route.request().method() === 'POST'
    ? route.fulfill({ status: 503, json: { detail: '服务暂时不可用，请稍后重试。' } })
    : route.continue())
  await page.getByRole('button', { name: '运行实验', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('服务暂时不可用')
  await expect(page.getByRole('button', { name: '运行实验', exact: true })).toBeEnabled()
  await capture('error-simulated')
  await page.getByLabel('关闭错误提示').click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.unroute('**/api/experiments')
  checks.push('浏览器模拟慢任务和 503：加载状态、防重复运行、折叠后取消、错误提示与重试入口正常')

  const assets = await (await page.request.get(base + '/api/assets')).json()
  const portrait = assets.find(asset => asset.metadata.example && asset.kind === 'image' && asset.metadata.width < asset.metadata.height)
  const landscape = assets.find(asset => asset.metadata.example && asset.kind === 'image' && asset.metadata.width > asset.metadata.height * 1.5)
  expect(portrait).toBeTruthy()
  expect(landscape).toBeTruthy()
  const longName = '用于检查长文件名的原始实验素材_' + '边缘检测样本_'.repeat(8) + '.png'
  const renamed = assets.map(asset => asset.id === portrait.id ? { ...asset, name: longName, metadata: { ...asset.metadata, example: true } } : asset)
  await page.route('**/api/assets', route => route.request().method() === 'GET' ? route.fulfill({ json: renamed }) : route.continue())
  await page.reload({ waitUntil: 'networkidle' })
  for (const asset of [portrait, landscape]) {
    if (await page.locator('.sample-drawer').count()) await page.locator('.sample-drawer summary').click()
    await page.getByTitle(asset.id === portrait.id ? longName : asset.name, { exact: true }).click()
    if (await page.locator('.sample-drawer[open]').count()) await page.locator('.sample-drawer summary').click()
    const geometry = await page.locator('.image-viewport svg').first().evaluate(svg => {
      const transform = svg.getScreenCTM(), view = svg.viewBox.baseVal, box = svg.getBoundingClientRect()
      return { sx: transform.a, sy: transform.d, width: view.width * transform.a, height: view.height * transform.d, containerWidth: box.width, containerHeight: box.height }
    })
    expect(geometry.sx).toBeCloseTo(geometry.sy, 5)
    expect(geometry.width).toBeLessThanOrEqual(geometry.containerWidth + 1)
    expect(geometry.height).toBeLessThanOrEqual(geometry.containerHeight + 1)
    await noOverflow()
    await capture(asset.id === portrait.id ? 'portrait-long-name' : 'landscape')
    if (asset.id === portrait.id) {
      await page.setViewportSize({ width: 390, height: 844 })
      await noOverflow()
      await capture('mobile-long-name')
      await page.setViewportSize({ width: 1440, height: 1000 })
    }
  }
  await page.unroute('**/api/assets')
  checks.push('真实竖图和宽图等比适配，不拉伸、不裁切；模拟长文件名在桌面省略、手机换行且无横向溢出')

  for (const [route, heading] of [['home', '实验入口'], ['pipeline', '处理流水线'], ['models', '本地模型管理'], ['history', '实验记录'], ['algorithm/gray', '灰度化']]) {
    await page.goto(base + '/#' + route)
    await expect(page.getByRole('heading', { name: new RegExp('^' + heading) })).toBeVisible()
    await expect(page.locator('.workbench-page')).toHaveCount(0)
  }
  checks.push('学习概览、处理流水线、模型管理、实验记录、灰度化原路由仍可打开')
  expect(errors).toEqual([])
  await writeFile('../docs/workbench-browser-validation.json', JSON.stringify({ status: 'passed', base, checks, runtimeErrors: errors, screenshots }, null, 2) + '\n')
  console.log(JSON.stringify({ status: 'passed', checks, screenshots }, null, 2))
} catch (error) {
  await capture('failure')
  throw error
} finally {
  await browser.close()
}
