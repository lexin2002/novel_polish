import { test, expect } from '@playwright/test'
import { openConfigSidebar } from './helpers'

test.describe('Config Sidebar', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await openConfigSidebar(page)
  })

  test('LLM configuration section shows provider selector', async ({ page }) => {
    await expect(page.getByText('LLM 配置')).toBeVisible()
    await expect(page.getByText('当前提供商')).toBeVisible()
    await expect(page.getByRole('combobox', { name: '选择提供商' })).toBeVisible()
  })

  test('provider selector dropdown shows all providers', async ({ page }) => {
    const providerTrigger = page.getByRole('combobox', { name: '选择提供商' })
    await providerTrigger.click()

    await expect(page.getByRole('option', { name: 'OpenAI' })).toBeVisible()
    await expect(page.getByRole('option', { name: 'Anthropic' })).toBeVisible()
    await expect(page.getByRole('option', { name: 'DeepSeek' })).toBeVisible()
    await expect(page.getByRole('option', { name: '通义千问' })).toBeVisible()
    await expect(page.getByRole('option', { name: 'SiliconFlow' })).toBeVisible()
    await expect(page.getByRole('option', { name: '自定义' })).toBeVisible()
  })

  test('switching provider changes config display', async ({ page }) => {
    const providerTrigger = page.getByRole('combobox', { name: '选择提供商' })
    await providerTrigger.click()
    await page.getByRole('option', { name: 'Anthropic' }).click()

    await expect(page.getByText('Anthropic 配置')).toBeVisible()
    await expect(page.getByText('Anthropic (Messages API)')).toBeVisible()
  })

  test('API key field accepts input', async ({ page }) => {
    const apiKeyInput = page.locator('input[type="password"]').first()
    await expect(apiKeyInput).toBeVisible()
    await apiKeyInput.fill('sk-test-api-key-12345')
    await expect(apiKeyInput).toHaveValue('sk-test-api-key-12345')
  })

  test('model input field works', async ({ page }) => {
    const modelInput = page.locator('input[list]').first()
    await expect(modelInput).toBeVisible()
    await modelInput.fill('gpt-4o-mini')
    await expect(modelInput).toHaveValue('gpt-4o-mini')
  })

  test('test connection button exists', async ({ page }) => {
    await expect(page.getByRole('button', { name: '测试连接' })).toBeVisible()
  })

  test('temperature slider is present', async ({ page }) => {
    const sliderThumb = page.locator('[role="slider"][aria-label="Temperature"]')
    await expect(sliderThumb).toBeVisible()
  })

  test('max tokens number input works', async ({ page }) => {
    const maxTokensInput = page.locator('input[type="number"]').first()
    await expect(maxTokensInput).toBeVisible()
    await maxTokensInput.fill('8192')
    await expect(maxTokensInput).toHaveValue('8192')
  })

  test('safety switches are present', async ({ page }) => {
    const safetySwitches = page.locator('[role="switch"]')
    const count = await safetySwitches.count()
    expect(count).toBeGreaterThanOrEqual(1)
  })

  test('engine parameter section expands and shows controls', async ({ page }) => {
    // "引擎性能参数" is expanded by default (Accordion defaultValue=['llm','engine'])
    // Look for the slider controls inside the engine section
    await page.waitForTimeout(300)

    await expect(page.getByText('切块大小')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('并发线程数')).toBeVisible()
  })

  test('network section expands', async ({ page }) => {
    await page.getByText('网络请求配置').click()
    await page.waitForTimeout(500)

    await expect(page.getByText('请求超时(秒)')).toBeVisible()
    await expect(page.getByText('重试次数')).toBeVisible()
  })

  test('UI behavior section expands', async ({ page }) => {
    await page.getByText('UI 行为配置').click()
    await page.waitForTimeout(500)

    await expect(page.getByText('日志文件启用')).toBeVisible()
    await expect(page.getByText('日志目录')).toBeVisible()
  })

  test('reset and refresh buttons exist', async ({ page }) => {
    await expect(page.getByRole('button', { name: '重置' })).toBeVisible()
  })
})
