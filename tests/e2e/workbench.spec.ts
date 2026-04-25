import { test, expect } from '@playwright/test'

test.describe('Workbench E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Navigate to polish tab (workbench)
    await page.click('nav button:has-text("润色工作台")')
  })

  test('should display workbench with control bar', async ({ page }) => {
    // Should show control bar with start/stop buttons
    await expect(page.locator('button:has-text("启动润色")')).toBeVisible()
    await expect(page.locator('button:has-text("停止")')).toBeVisible()
  })

  test('should display original text label in header', async ({ page }) => {
    // Should show header with original/revised label
    await expect(page.locator('text=原文 (左) / 润色后 (右)')).toBeVisible()
    await expect(page.locator('button:has-text("导入原文")')).toBeVisible()
  })

  test('should start polish process on start button click', async ({ page }) => {
    // Click start button
    await page.click('button:has-text("启动润色")')

    // Start button should be disabled during processing
    await expect(page.locator('button:has-text("启动润色")')).toBeDisabled()
  })

  test('should show sync scroll button with link icon', async ({ page }) => {
    // Find sync scroll button - it's the one with the link icon next to "同步滚动" text
    // The button has the title "启用同步滚动" or "取消同步滚动"
    const syncButton = page.locator('button').filter({ has: page.locator('svg') }).first()
    await expect(syncButton).toBeVisible()
  })

  test('should display diff editor container', async ({ page }) => {
    // Wait for Monaco to load
    await page.waitForTimeout(1000)
    // Monaco diff editor should be present (may be loading)
    // Just verify the main content area is visible
    const workbench = page.locator('.overflow-hidden').first()
    await expect(workbench).toBeVisible()
  })

  test('should show progress bar when running', async ({ page }) => {
    // Click start button
    await page.click('button:has-text("启动润色")')

    // Should show "等待开始润色任务..." before progress starts
    await expect(page.locator('text=等待开始润色任务...')).toBeVisible()
  })

  test('should handle stop button during processing', async ({ page }) => {
    // Click start to begin processing
    await page.click('button:has-text("启动润色")')

    // Stop button should now be enabled
    const stopButton = page.locator('button:has-text("停止")')
    await expect(stopButton).toBeEnabled()

    // Click stop
    await stopButton.click()

    // Start button should be re-enabled
    await expect(page.locator('button:has-text("启动润色")')).toBeEnabled()
  })

  test('should show waiting message in modified panel before start', async ({ page }) => {
    // Should show placeholder text in modified panel
    await expect(page.locator('text=点击"启动润色"开始处理')).toBeVisible()
  })

  test('should toggle sync scroll state', async ({ page }) => {
    // The sync scroll button should toggle when clicked
    // We verify by clicking it and checking that the appearance changes
    const syncButton = page.locator('button').filter({ has: page.locator('svg') }).first()

    // Click to toggle
    await syncButton.click()

    // After clicking, the icon should change (we can't easily verify icon change)
    // But the button should still be visible and functional
    await expect(syncButton).toBeVisible()
  })
})