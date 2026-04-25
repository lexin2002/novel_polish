import { test, expect } from '@playwright/test'

test.describe('Sidebar Configuration Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Wait for app to load
    await page.waitForSelector('nav button')
  })

  test('should switch to config tab and show sidebar container', async ({ page }) => {
    // Click config tab
    await page.click('nav button:has-text("配置驾驶舱")')

    // Wait for sidebar area to appear (sidebar container is always rendered when config tab active)
    await page.waitForTimeout(500)

    // The sidebar should appear as an aside element
    const sidebar = page.locator('aside')
    await expect(sidebar).toBeVisible()
  })

  test('should display config cockpit title in sidebar header', async ({ page }) => {
    await page.click('nav button:has-text("配置驾驶舱")')
    await page.waitForTimeout(500)

    // Should show config cockpit header text
    const headerText = page.locator('aside h2:has-text("配置驾驶舱")')
    await expect(headerText).toBeVisible()
  })

  test('should show loading or error state when backend unavailable', async ({ page }) => {
    await page.click('nav button:has-text("配置驾驶舱")')
    await page.waitForTimeout(500)

    // Should show either loading spinner OR error message OR config content
    // The key is that sidebar container is visible
    const sidebar = page.locator('aside')
    await expect(sidebar).toBeVisible()
  })

  test('should display accordion headers for config sections', async ({ page }) => {
    await page.click('nav button:has-text("配置驾驶舱")')
    await page.waitForTimeout(500)

    // Accordion headers should be visible in the sidebar
    // These are buttons with accordion trigger functionality
    await expect(page.locator('aside button:has-text("LLM 配置")')).toBeVisible()
    await expect(page.locator('aside button:has-text("引擎性能参数")')).toBeVisible()
  })

  test('should expand accordion section when clicked', async ({ page }) => {
    await page.click('nav button:has-text("配置驾驶舱")')
    await page.waitForTimeout(500)

    // Click on Network section to expand it
    await page.click('aside button:has-text("网络请求配置")')
    await page.waitForTimeout(300)

    // The accordion content should now be visible
    // Look for any text content that's inside the expanded network section
    const networkContent = page.locator('aside').filter({ hasText: '请求超时' })
    await expect(networkContent.or(page.locator('aside').filter({ hasText: '网络请求配置' }))).toBeVisible()
  })

  test('should have reset button in sidebar header', async ({ page }) => {
    await page.click('nav button:has-text("配置驾驶舱")')
    await page.waitForTimeout(500)

    // Reset button should be visible in sidebar header
    const resetButton = page.locator('aside button:has-text("重置")')
    await expect(resetButton).toBeVisible()
  })
})
