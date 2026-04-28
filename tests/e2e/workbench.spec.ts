import { test, expect } from '@playwright/test'
import { clickTab } from './helpers'

test.describe('Workbench (Polish Tab)', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Ensure we're on the polish tab (it's the default)
    await clickTab(page, '润色工作台')
  })

  test('shows control bar with start/stop buttons', async ({ page }) => {
    // Start button enabled by default
    const startBtn = page.getByRole('button', { name: '启动润色' })
    await expect(startBtn).toBeVisible()
    await expect(startBtn).toBeEnabled()

    // Stop button disabled by default (not running)
    const stopBtn = page.getByRole('button', { name: '停止' })
    await expect(stopBtn).toBeVisible()
    await expect(stopBtn).toBeDisabled()
  })

  test('sync scroll toggle switches state', async ({ page }) => {
    const syncButton = page.getByTitle('取消同步滚动')
    await expect(syncButton).toBeVisible()

    // Click to disable sync scroll
    await syncButton.click()
    await expect(page.getByTitle('启用同步滚动')).toBeVisible()

    // Click to re-enable
    await page.getByTitle('启用同步滚动').click()
    await expect(page.getByTitle('取消同步滚动')).toBeVisible()
  })

  test('shows import file button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '导入原文' })).toBeVisible()
  })

  test('shows placeholder text in the diff editor area', async ({ page }) => {
    // The DiffEditor lazy-loads Monaco, so wait for it briefly
    // The modified panel should show the idle message
    await page.waitForTimeout(3000)

    // After loading, the editor should show the sample text on the left
    // and the instruction text on the right
    await expect(page.getByText('点击"启动润色"开始处理')).toBeVisible()
  })
})
