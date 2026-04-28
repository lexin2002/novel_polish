import { Page, Locator } from '@playwright/test'

/** Wait for the backend to be ready by polling health endpoint */
export async function waitForBackend(page: Page): Promise<void> {
  await page.waitForFunction(async () => {
    try {
      const res = await fetch('http://localhost:57621/api/health')
      return res.ok
    } catch { return false }
  }, { timeout: 15000 })
}

/** Click a tab by its visible label text */
export async function clickTab(page: Page, label: string): Promise<void> {
  await page.getByRole('button', { name: label, exact: false }).click()
  await page.waitForTimeout(500)
}

/** Navigate to the config tab so the sidebar becomes visible */
export async function openConfigSidebar(page: Page): Promise<void> {
  await clickTab(page, '系统设置')
  // The sidebar is hidden until config tab is active
  await page.waitForSelector('aside', { state: 'visible', timeout: 5000 })
}

/** Read the current store state from the page context */
export async function evaluateStore<T>(page: Page, storeName: string, getter: string): Promise<T> {
  return page.evaluate<T>(([name, fn]) => {
    // @ts-expect-error - accessing zustand store internals
    const store = window.__ZUSTAND_STORES__?.[name]
    return store ? store.getState()[fn]() : null
  }, [storeName, getter])
}
