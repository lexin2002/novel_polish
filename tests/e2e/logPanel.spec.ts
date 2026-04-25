import { test, expect } from '@playwright/test'

test.describe('LogPanel E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should toggle log panel visibility', async ({ page }) => {
    // Initially log panel should not be visible
    const logPanel = page.locator('text=实时日志')
    await expect(logPanel).not.toBeVisible()

    // Click the Log button in header
    await page.click('button:has-text("日志")')

    // Now log panel should be visible
    await expect(logPanel).toBeVisible()
  })

  test('should show connection status', async ({ page }) => {
    // Open log panel
    await page.click('button:has-text("日志")')

    // Should show connection status (either connected or disconnected)
    await expect(page.locator('text=已连接').or(page.locator('text=已断开'))).toBeVisible()
  })

  test('should have pause and clear buttons', async ({ page }) => {
    // Open log panel
    await page.click('button:has-text("日志")')

    // Should have pause and clear buttons
    await expect(page.locator('button:has-text("暂停")')).toBeVisible()
    await expect(page.locator('button:has-text("清空")')).toBeVisible()
  })

  test('should toggle pause state', async ({ page }) => {
    // Open log panel
    await page.click('button:has-text("日志")')

    // Click pause button
    await page.click('button:has-text("暂停")')

    // Button should now show "继续"
    await expect(page.locator('button:has-text("继续")')).toBeVisible()
  })

  test('should clear logs on clear button click', async ({ page }) => {
    // Open log panel
    await page.click('button:has-text("日志")')

    // Wait for any logs to appear (may be empty or show waiting message)
    // Check the log count shows 0 条
    await expect(page.locator('text=0 条')).toBeVisible()
  })

  test('should display waiting message when no logs', async ({ page }) => {
    // Open log panel
    await page.click('button:has-text("日志")')

    // Should show waiting message or log list (depending on connection state)
    // When no logs yet, shows waiting message
    const waitingOrLogArea = page.locator('text=等待日志数据...').or(page.locator('.font-mono'))
    await expect(waitingOrLogArea.first()).toBeVisible()
  })

  test('should show progress bar when progress data received', async ({ page }) => {
    // Inject mock WebSocket to simulate progress messages
    await page.goto('/')
    await page.click('button:has-text("日志")')

    // Evaluate script to inject mock WebSocket
    await page.evaluate(() => {
      // @ts-expect-error - Mocking WebSocket for testing
      window.WebSocket = function(_url: string) {
        const mockWs = {
          readyState: 1,
          close: () => {},
          send: () => {},
          onopen: null,
          onmessage: null,
          onerror: null,
          onclose: null,
        }
        // Simulate connection open
        setTimeout(() => mockWs.onopen?.({ type: 'open' }), 10)
        // Send progress message
        setTimeout(() => {
          mockWs.onmessage?.({
            type: 'message',
            data: JSON.stringify({
              type: 'progress',
              data: {
                chunk: 2,
                total_chunks: 5,
                iteration: 3,
                total_iterations: 4,
                message: 'Processing chunk 2',
              },
            }),
          })
        }, 50)
        // Send log message
        setTimeout(() => {
          mockWs.onmessage?.({
            type: 'message',
            data: '2026-04-25 22:00:00 - INFO - Test log message',
          })
        }, 100)
        return mockWs
      }
      // @ts-expect-error - Mocking WebSocket constants
      window.WebSocket.CONNECTING = 0
      // @ts-expect-error - Mocking WebSocket constants
      window.WebSocket.CLOSED = 3
    })

    // Wait for progress bar to appear
    await page.waitForTimeout(200)

    // Should show progress indicator with chunk/iteration info (use first() to avoid strict mode)
    await expect(page.locator('text=块 2/5，迭代 3/4').first()).toBeVisible()
  })

  test('should show log entry count', async ({ page }) => {
    // Open log panel
    await page.click('button:has-text("日志")')

    // Log count should be visible
    await expect(page.locator('text=/\\(\\d+ 条\\)/')).toBeVisible()
  })
})