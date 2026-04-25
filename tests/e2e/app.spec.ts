import { test, expect } from '@playwright/test'

test.describe('NovelPolish E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display the application title and header', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('小说智能润色工作台')
    await expect(page.locator('text=Novel Polish')).toBeVisible()
  })

  test('should have light theme applied to body', async ({ page }) => {
    const body = page.locator('body')
    const bgColor = await body.evaluate((el) =>
      getComputedStyle(el).backgroundColor
    )
    expect(bgColor).toMatch(/rgb\(249, 249, 249\)|f9f9f9|249.*249.*249/i)
  })

  test('should have four navigation tabs', async ({ page }) => {
    await expect(page.locator('nav button')).toHaveCount(4)
    await expect(page.locator('nav button:has-text("润色工作台")')).toBeVisible()
    await expect(page.locator('nav button:has-text("规则配置中心")')).toBeVisible()
    await expect(page.locator('nav button:has-text("历史档案馆")')).toBeVisible()
    await expect(page.locator('nav button:has-text("配置驾驶舱")')).toBeVisible()
  })

  test('should switch tabs correctly', async ({ page }) => {
    const tabs = [
      { tab: '润色工作台', content: '粘贴原文，开始智能润色之旅' },
      { tab: '规则配置中心', content: '配置和管理润色规则' },
      { tab: '历史档案馆', content: '查看历史润色记录' },
      { tab: '配置驾驶舱', content: '调整系统配置' },
    ]

    for (const { tab, content } of tabs) {
      await page.click(`nav button:has-text("${tab}")`)
      await expect(page.locator(`main h2:has-text("${tab}")`)).toBeVisible()
      await expect(page.locator(`main p:text("${content}")`)).toBeVisible()
    }
  })

  test('should have correct text colors based on light theme', async ({ page }) => {
    const h1 = page.locator('h1')
    const color = await h1.evaluate((el) => getComputedStyle(el).color)
    expect(color).toMatch(/rgb\(26, 26, 26\)|#1a1a1a|26.*26.*26/i)
  })

  test('should display footer with version info', async ({ page }) => {
    await expect(page.locator('footer')).toContainText('NovelPolish v1.0.0')
    await expect(page.locator('footer')).toContainText('Electron + React + TypeScript')
  })

  test('should have no console errors on load', async ({ page }) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    await page.waitForTimeout(1000)
    expect(errors.filter(e => !e.includes('Failed to load resource'))).toHaveLength(0)
  })

  test('should display status indicator', async ({ page }) => {
    const statusElement = page.locator('text=状态:')
    await expect(statusElement).toBeVisible()
  })
})
