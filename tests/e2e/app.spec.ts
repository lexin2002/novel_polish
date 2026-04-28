import { test, expect } from '@playwright/test'
import { clickTab } from './helpers'

test.describe('App Navigation & Layout', () => {

  test('loads the app and shows all four tab buttons', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText('小说智能润色工作台')).toBeVisible()
    await expect(page.getByText('Novel Polish - AI-Powered')).toBeVisible()

    await expect(page.getByRole('button', { name: '润色工作台' })).toBeVisible()
    await expect(page.getByRole('button', { name: '规则配置中心' })).toBeVisible()
    await expect(page.getByRole('button', { name: '历史档案馆' })).toBeVisible()
    await expect(page.getByRole('button', { name: '系统设置' })).toBeVisible()

    await expect(page.getByText('NovelPolish v1.0.0')).toBeVisible()
  })

  test('polish tab is active by default and shows the workbench', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('button', { name: '启动润色' })).toBeVisible()
    await expect(page.getByRole('button', { name: '停止' })).toBeVisible()
    await expect(page.getByText('同步滚动')).toBeVisible()
  })

  test('switching to rules tab shows the rule editor', async ({ page }) => {
    await page.goto('/')
    await clickTab(page, '规则配置中心')

    // Use .first() because "规则配置中心" appears in both tab and heading
    await expect(page.getByText('规则配置中心').first()).toBeVisible()
    const saveBtn = page.getByRole('button', { name: '保存规则' })
    await expect(saveBtn).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('button', { name: '放弃更改' })).toBeVisible()
  })

  test('history tab shows placeholder content', async ({ page }) => {
    await page.goto('/')
    await clickTab(page, '历史档案馆')

    await expect(page.getByText('历史档案馆').first()).toBeVisible()
    await expect(page.getByText('查看历史润色记录')).toBeVisible()
  })

  test('config tab shows sidebar and placeholder', async ({ page }) => {
    await page.goto('/')
    await clickTab(page, '系统设置')

    await expect(page.getByText('系统设置').first()).toBeVisible()
    await expect(page.getByText('在左侧配置驾驶舱中调整系统参数')).toBeVisible()

    // Sidebar loads LLM config from API, then shows the accordion
    await expect(page.getByText('LLM 配置')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('引擎性能参数')).toBeVisible()
  })
})

test.describe('Log Panel', () => {

  test('log panel toggle button shows/hides the panel', async ({ page }) => {
    await page.goto('/')

    const logButton = page.getByRole('button', { name: '日志' })
    await expect(logButton).toBeVisible()

    await logButton.click()
    await expect(page.getByText('实时日志')).toBeVisible()

    // Panel should show either waiting text or connection status
    const panel = page.locator('text=实时日志').locator('..')
    await expect(panel).toBeVisible()

    // Connection status indicator (may show "已连接" or "已断开")
    const connStatus = page.getByText(/已连接|已断开/)
    if (await connStatus.isVisible()) {
      // good - WebSocket connected or disconnected indicator is visible
    }

    await expect(page.getByRole('button', { name: '暂停' })).toBeVisible()
    await expect(page.getByRole('button', { name: '清空' })).toBeVisible()

    await logButton.click()
    await expect(page.getByText('实时日志')).not.toBeVisible()
  })

  test('log panel pause and resume work', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('button', { name: '日志' }).click()
    await expect(page.getByText('实时日志')).toBeVisible()

    const pauseButton = page.getByRole('button', { name: '暂停' })
    await pauseButton.click()
    await expect(page.getByRole('button', { name: '继续' })).toBeVisible()

    await page.getByRole('button', { name: '继续' }).click()
    await expect(page.getByRole('button', { name: '暂停' })).toBeVisible()
  })

  test('log panel clear button is visible', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('button', { name: '日志' }).click()
    await expect(page.getByText('实时日志')).toBeVisible()
    await expect(page.getByRole('button', { name: '清空' })).toBeVisible()
  })
})
