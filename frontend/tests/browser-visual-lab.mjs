import {chromium, expect} from '@playwright/test'
import {mkdir, writeFile, readFile} from 'node:fs/promises'
import path from 'node:path'

const before = process.env.VISUAL_PHASE === 'before'
const base = process.env.BASE_URL || 'http://127.0.0.1:5178'
const output = before ? '/tmp/vision-ui-before/browser' : path.resolve('../docs/screenshots/visual-lab')
await mkdir(output, {recursive: true})
const browser = await chromium.launch({executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser', headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage', '--no-proxy-server']})
const page = await browser.newPage({viewport: {width: 1920, height: 1080}, deviceScaleFactor: 1})
const errors = [], measurements = [], checks = []
page.on('pageerror', error => errors.push(error.message))
async function capture(name) {
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  await page.screenshot({path: path.join(output, name + '.png'), fullPage: true, animations: 'disabled'})
  measurements.push(await page.evaluate(name => {
    const rect = selector => {
      const r = document.querySelector(selector)?.getBoundingClientRect()
      return r ? {x:r.x,y:r.y,width:r.width,height:r.height} : null
    }
    const visible = element => {const r = element.getBoundingClientRect(); return r.width > 0 && r.height > 0}
    const borders = [...document.querySelectorAll('main *')].filter(element => visible(element) && ['Top','Right','Bottom','Left'].some(side => {
      const s = getComputedStyle(element)
      return parseFloat(s['border'+side+'Width']) > 0 && s['border'+side+'Style'] !== 'none' && !['transparent','rgba(0, 0, 0, 0)'].includes(s['border'+side+'Color'])
    })).length
    return {name, width:innerWidth,height:innerHeight, documentWidth:document.documentElement.scrollWidth, main:rect('main'),viewer:rect('.viewer'), viewport:rect('.image-viewport'), parameters:rect('.parameter-panel'), borderedElements:borders}
  },name))
  expect(measurements.at(-1).documentWidth).toBeLessThanOrEqual(measurements.at(-1).width + 1)
}
try {
  for (const [width,height] of [[1920,1080],[2560,1440]]) {
    await page.setViewportSize({width,height})
    await page.goto(base + '/#home', {waitUntil:'networkidle'})
    await capture('home-'+width)
  }
  if (!before) {
    for (const name of ['传统视觉','深度学习','工业视觉','视频与三维']) await expect(page.getByRole('heading',{name,exact:true})).toBeVisible()
    await expect(page.locator('.hero-visual, .stats-row, .path-card')).toHaveCount(0)
    await page.getByLabel('查找实验').fill('CANNY')
    await expect(page.locator('.lab-result')).toHaveCount(1)
    await expect(page.locator('.lab-result')).toContainText('Canny')
    await page.getByLabel('查找实验').fill('没有这个实验xyz')
    await expect(page.getByRole('heading',{name:'没有找到匹配的实验'})).toBeVisible()
    await page.getByRole('button',{name:'查看全部方向'}).click()
    const catalog = await (await page.request.get(base+'/api/algorithms')).json()
    for (const expand of await page.locator('.lab-domain-expand').all()) await expand.click()
    await expect(page.locator('.lab-domain-links button')).toHaveCount(catalog.length)
    for (const expand of await page.locator('.lab-domain-expand').all()) await expand.click()
    await page.getByLabel('查找实验').fill('canny')
    await page.getByLabel('查找实验').press('Enter')
    await expect(page).toHaveURL(/#algorithm\/canny$/)
    await expect(page.locator('.asset-bar')).toContainText('水果')
    await expect(page.getByRole('button',{name:'运行实验',exact:true})).toBeEnabled()
    checks.push('首页关键词搜索、空结果、清空、140 个动态入口展开、Enter 进入算法并加载素材')
  }
  await page.goto(base + '/#algorithm/canny', {waitUntil:'networkidle'})
  await page.getByRole('button',{name:'载入完整示例'}).click()
  await page.getByRole('button',{name:'运行实验',exact:true}).click()
  await expect(page.locator('.job-status.completed')).toBeVisible({timeout:30000})
  for (const [width,height] of [[1920,1080],[2560,1440]]) {
    await page.setViewportSize({width,height})
    await capture('canny-'+width)
  }
  if (!before) {
    const current = await page.locator('.algorithm-children a[aria-current=page]').evaluate(a => ({background:getComputedStyle(a).backgroundColor,marker:getComputedStyle(a,'::before').width}))
    expect(current.background).toBe('rgba(0, 0, 0, 0)')
    expect(current.marker).toBe('3px')
    await expect(page.locator('.parameter-panel .primary')).toHaveCount(1)
    expect(await page.locator('.workbench-actions .primary').count()).toBe(0)
    await page.getByRole('button',{name:'滑动',exact:true}).click()
    await page.getByLabel('对比滑块').fill('40')
    await capture('canny-slide-2560')
    await page.getByRole('button',{name:'结果',exact:true}).click()
    await page.getByRole('button',{name:'收起参数'}).click()
    await capture('canny-focus-2560')
    await page.getByRole('button',{name:'展开参数'}).click()
    await page.getByRole('button',{name:'并排',exact:true}).click()
    for (const [width,height] of [[1440,1000],[1024,900],[390,844],[320,844]]) {
      await page.setViewportSize({width,height})
      if (width === 390) await page.getByRole('button',{name:'收起参数'}).click()
      await capture('canny-'+width)
      if (width === 390) {
        await page.getByRole('button',{name:'展开参数'}).click()
        await expect(page.locator('.parameter-panel')).toBeVisible()
        await page.getByLabel('低阈值数值').fill('45')
        await expect(page.getByLabel('低阈值数值')).toHaveValue('45')
        await capture('canny-mobile-parameters')
        await page.getByRole('button',{name:'收起参数'}).click()
        await page.getByRole('tab',{name:'Python 示例'}).click()
        await expect(page.getByLabel('Python 示例代码')).toContainText('"low": 45')
        await capture('canny-mobile-python')
        await page.getByRole('tab',{name:'原理与结果解读'}).click()
      }
    }
    checks.push('真实 Canny 运行，画布对比模式、参数折叠、独立选中标记、手机调参与代码仍可用')
    for (const width of [1440,1024,390,320]) {
      await page.setViewportSize({width,height:width<700?844:1000})
      await page.goto(base+'/#home',{waitUntil:'networkidle'})
      await capture('home-'+width)
      if (width === 390) {
        await page.getByLabel('查找实验').fill('分割')
        await capture('home-mobile-search')
        await page.getByLabel('查找实验').press('Escape')
        await expect(page.getByRole('heading',{name:'常用实验'})).toBeVisible()
        await page.getByLabel('切换侧栏').click()
        await expect(page.getByLabel('搜索算法')).toBeVisible()
        await page.getByLabel('搜索算法').fill('canny')
        await page.locator('.algorithm-children a[href="#algorithm/canny"]').click()
        await expect(page.locator('.sidebar-backdrop')).toHaveCount(0)
      }
    }
    checks.push('1440 / 1024 / 390 / 320 px 两页无横向溢出，手机搜索与侧栏导航正常')
  }
  await page.goto(base + '/#algorithm/gray', {waitUntil:'networkidle'})
  await page.setViewportSize({width:1440,height:1000})
  await page.getByLabel('搜索算法').fill('')
  await capture('gray-scope-control')
  if (!before) {
    await expect(page.locator('.lab-pilot')).toHaveCount(0)
    const baseline = JSON.parse(await readFile('../docs/visual-lab-before-measurements.json','utf8'))
    for (const width of [1920,2560]) {
      const old = baseline.measurements.find(item=>item.name==='canny-'+width)
      const now = measurements.find(item=>item.name==='canny-'+width)
      expect(now.viewport.height).toBeGreaterThan(old.viewport.height*1.4)
      expect(now.borderedElements).toBeLessThanOrEqual(old.borderedElements*.7)
      expect(now.main.x).toBeLessThan(250)
    }
    const old = baseline.measurements.find(item=>item.name==='gray-scope-control')
    expect(measurements.at(-1)).toEqual(old)
    checks.push('两种大屏画布高度增长超过 40%，带边框元素减少超过 30%；灰度页布局测量与改版前完全一致')
  }
  expect(errors).toEqual([])
  const report = JSON.stringify({phase:before?'before':'after',measurements,checks,errors},null,2)+'\n'
  await writeFile(path.join(output,'measurements.json'),report)
  if (before) await writeFile('../docs/visual-lab-before-measurements.json',report)
  console.log(JSON.stringify({phase:before?'before':'after',checks,screenshots:measurements.length,errors},null,2))
} finally {await browser.close()}
