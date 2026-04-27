/**
 * Diagnostic test: replaces manual F12 with automated console + network capture
 */
import { test, ConsoleMessage, Request } from '@playwright/test'
import * as fs from 'fs'

test.describe('Automated Diagnostic - Config Loading Error', () => {
  const consoleErrors: string[] = []
  const consoleWarnings: string[] = []
  const networkCapture: Array<{ method: string; url: string; status: number | null; body: string | null; failure: string | null }> = []

  test('should capture all evidence for "配置加载失败" error', async ({ page }) => {
    console.log('='.repeat(60))
    console.log('  Novel Polish - Automated Diagnostic Pipeline')
    console.log('='.repeat(60))

    // --- Phase 2: Console listener (F12 Console replacement) ---
    page.on('console', (msg: ConsoleMessage) => {
      const text = msg.text()
      if (msg.type() === 'error') {
        consoleErrors.push(text)
        console.log(`  [CONSOLE ERROR] ${text}`)
      } else if (msg.type() === 'warning') {
        consoleWarnings.push(text)
        console.log(`  [CONSOLE WARN] ${text}`)
      } else if (msg.type() === 'log' && text.includes('[Sidebar]')) {
        console.log(`  [CONSOLE LOG] ${text}`)
      }
    })

    // --- Phase 2: Network interception (F12 Network replacement) ---
    page.on('response', async (response) => {
      const url = response.url()
      if (url.includes('/api/')) {
        let body: string | null = null
        try {
          body = await response.text()
          networkCapture.push({
            method: response.request().method(),
            url,
            status: response.status(),
            body: body.substring(0, 500),
            failure: null,
          })
          console.log(`  [NETWORK] ${response.request().method()} ${url} → ${response.status()}`)
        } catch {
          networkCapture.push({
            method: response.request().method(),
            url,
            status: response.status(),
            body: null,
            failure: 'Failed to read body',
          })
        }
      }
    })

    page.on('requestfailed', (request: Request) => {
      const url = request.url()
      if (url.includes('/api/')) {
        networkCapture.push({
          method: request.method(),
          url,
          status: null,
          body: null,
          failure: request.failure()?.errorText || 'unknown',
        })
        console.log(`  [NETWORK FAIL] ${request.method()} ${url} → ${request.failure()?.errorText}`)
      }
    })

    page.on('pageerror', (err: Error) => {
      console.log(`  [PAGE ERROR] ${err.message}`)
      consoleErrors.push(`[PageError] ${err.message}`)
    })

    // --- Navigate ---
    console.log('\n[1/4] Navigating to http://localhost:5173...')
    await page.goto('http://localhost:5173', { timeout: 15000 })
    await page.waitForLoadState('networkidle')
    console.log('  ✓ Page loaded')

    // --- Click System Settings tab ---
    console.log('\n[2/4] Clicking "系统设置" tab...')
    const configTab = page.locator('nav button:has-text("系统设置")')
    await configTab.click()
    await page.waitForTimeout(3000)
    console.log('  ✓ Tab clicked, waited for config fetch')

    // --- Check UI state ---
    console.log('\n[3/4] Checking UI state...')
    const errorCount = await page.locator('text=配置加载失败').count()
    const failedFetchCount = await page.locator('text=Failed to fetch').count()
    const loadingCount = await page.locator('text=加载配置中').count()

    if (errorCount > 0) console.log('  ⚠ UI shows "配置加载失败"')
    if (failedFetchCount > 0) console.log('  ⚠ UI shows "Failed to fetch"')
    if (loadingCount > 0) console.log('  ⚠ UI is still in loading state')

    // Screenshot
    await page.screenshot({ path: '/tmp/diagnostic_screenshot.png', fullPage: true })
    console.log('  📸 Screenshot saved: /tmp/diagnostic_screenshot.png')

    // --- Backend logs (Phase 1) ---
    console.log('\n[4/4] Backend log analysis...')
    if (fs.existsSync('/tmp/backend_diag.log')) {
      const logs = fs.readFileSync('/tmp/backend_diag.log', 'utf-8')
      const lines = logs.split('\n')
      const errors = lines.filter(l => l.includes('ERROR') || l.includes('Traceback') || l.includes('Exception'))
      if (errors.length > 0) {
        console.log('  ⚠ Backend ERROR/Traceback found:')
        errors.forEach(l => console.log(`    ${l}`))
      } else {
        console.log('  ✓ No ERROR/Traceback in backend log')
      }
    } else {
      console.log('  ? Backend log file not found at /tmp/backend_diag.log')
    }

    // --- Final Report ---
    console.log('\n' + '='.repeat(60))
    console.log('  DIAGNOSTIC REPORT')
    console.log('='.repeat(60))

    console.log(`\nConsole Errors (${consoleErrors.length}):`)
    if (consoleErrors.length === 0) {
      console.log('  (none)')
    } else {
      consoleErrors.forEach(e => console.log(`  ❌ ${e}`))
    }

    console.log(`\nNetwork Requests (${networkCapture.length}):`)
    networkCapture.forEach(r => {
      const status = r.status ? `${r.status}` : 'FAILED'
      const body = r.body ? r.body.substring(0, 200) : r.failure || ''
      console.log(`  HTTP ${r.method} ${r.url}`)
      console.log(`    → ${status} | ${body}`)
    })

    console.log('\nUI State:')
    console.log(`  - "配置加载失败" visible: ${errorCount > 0 ? '❌ YES' : '✓ NO'}`)
    console.log(`  - "Failed to fetch" visible: ${failedFetchCount > 0 ? '❌ YES' : '✓ NO'}`)
    console.log(`  - Still loading: ${loadingCount > 0 ? '⏳ YES' : '✓ NO'}`)

    // Assertions
    if (consoleErrors.length > 0) {
      console.log('\n❌ Console errors detected - investigate these first')
    }
    if (networkCapture.length === 0) {
      console.log('\n❌ No API requests captured - proxy may be broken')
    }
    const failedApi = networkCapture.filter(r => r.status && r.status >= 400)
    if (failedApi.length > 0) {
      console.log(`\n❌ ${failedApi.length} failed API call(s) - check proxy`)
    }
    if (errorCount > 0 || failedFetchCount > 0 || loadingCount > 0) {
      console.log('\n⚠ UI is showing loading/error state - config failed to load')
    }
    if (consoleErrors.length === 0 && networkCapture.length > 0 && errorCount === 0) {
      console.log('\n✅ Everything looks normal - error may have been intermittent')
    }
  })
})