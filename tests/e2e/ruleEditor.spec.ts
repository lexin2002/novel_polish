import { test, expect, Page } from '@playwright/test'
import { clickTab } from './helpers'

test.describe('Rule Editor', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await clickTab(page, '规则配置中心')
    // Wait for rules to load from backend API (the "保存规则" button indicates loaded state)
    await expect(page.getByRole('button', { name: '保存规则' })).toBeVisible({ timeout: 10000 })
  })

  test('loads and displays the rule editor header', async ({ page }) => {
    await expect(page.getByText('规则配置中心').first()).toBeVisible()
    await expect(page.getByRole('button', { name: '保存规则' })).toBeVisible()
    await expect(page.getByRole('button', { name: '放弃更改' })).toBeVisible()
  })

  test('adds a new main category', async ({ page }) => {
    const addCategoryBtn = page.getByRole('button', { name: '添加类别' })
    await addCategoryBtn.click()

    // New category with default name "新类别" — use locator with attribute
    await expect(page.locator('input[value="新类别"]')).toBeVisible()
  })

  test('renames a category', async ({ page }) => {
    // Ensure at least one category exists
    const addBtn = page.getByRole('button', { name: '添加类别' })
    const existingInputs = page.locator('input[placeholder="主类别名称"]')
    if ((await existingInputs.count()) === 0) {
      await addBtn.click()
      await page.waitForTimeout(300)
    }

    const categoryInput = page.locator('input[placeholder="主类别名称"]').first()
    await expect(categoryInput).toBeVisible()
    await categoryInput.fill('我的自定义类别')
    await expect(categoryInput).toHaveValue('我的自定义类别')
  })

  test('adds and removes a sub-category', async ({ page }) => {
    // Find the + button for adding sub-category
    const addSubBtns = page.locator('button[title="添加子类别"]')
    const count = await addSubBtns.count()

    if (count === 0) {
      // No categories yet, add one first
      await page.getByRole('button', { name: '添加类别' }).click()
      await page.waitForTimeout(300)
    }

    await page.locator('button[title="添加子类别"]').first().click()

    // New sub-category should appear
    await expect(page.locator('input[value="新子类别"]')).toBeVisible()

    // Delete it
    await page.locator('button[title="删除子类别"]').first().click()
    await expect(page.locator('input[value="新子类别"]')).not.toBeVisible()
  })

  test('adds a rule with instruction text', async ({ page }) => {
    const addRuleBtns = page.locator('button[title="添加规则"]')

    if ((await addRuleBtns.count()) === 0) {
      await page.getByRole('button', { name: '添加类别' }).click()
      await page.waitForTimeout(200)
      await page.locator('button[title="添加子类别"]').first().click()
      await page.waitForTimeout(200)
    }

    await page.locator('button[title="添加规则"]').first().click()
    await page.waitForTimeout(300)

    await expect(page.locator('input[value="新规则"]')).toBeVisible()

    // Type instructions in the last textarea
    const textareas = page.locator('textarea')
    await textareas.last().fill('检查并修复所有错别字')
    await expect(textareas.last()).toHaveValue('检查并修复所有错别字')

    // Type direction in the instruction input
    const directionInputs = page.locator('input[placeholder="如：诊断并修改"]')
    if (await directionInputs.count() > 0) {
      await directionInputs.last().fill('诊断并修改')
      await expect(directionInputs.last()).toHaveValue('诊断并修改')
    }
  })

  test('delete a rule', async ({ page }) => {
    const addRuleBtns = page.locator('button[title="添加规则"]')

    if ((await addRuleBtns.count()) > 0) {
      await page.locator('button[title="添加规则"]').first().click()
      await page.waitForTimeout(300)

      // Delete the rule
      const deleteRuleBtns = page.locator('button[title="删除规则"]')
      if ((await deleteRuleBtns.count()) > 0) {
        await deleteRuleBtns.first().click()
        await page.waitForTimeout(200)
      }
    }
  })

  test('deletes a category', async ({ page }) => {
    // Add a category first so we have one to delete
    await page.getByRole('button', { name: '添加类别' }).click()
    await page.waitForTimeout(300)
    await expect(page.locator('input[value="新类别"]')).toBeVisible()

    // Delete it
    await page.locator('button[title="删除类别"]').first().click()
    await page.waitForTimeout(300)
  })

  test('save button can be clicked', async ({ page }) => {
    const saveBtn = page.getByRole('button', { name: '保存规则' })
    await expect(saveBtn).toBeVisible()
    if (await saveBtn.isEnabled()) {
      await saveBtn.click()
    }
  })
})

test.describe('Rule Editor - Priority Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await clickTab(page, '规则配置中心')
    await expect(page.getByRole('button', { name: '保存规则' })).toBeVisible({ timeout: 10000 })
    // Ensure at least one category exists for select elements
    const existingSelects = page.locator('select')
    if ((await existingSelects.count()) === 0) {
      await page.getByRole('button', { name: '添加类别' }).click()
      await page.waitForTimeout(300)
    }
  })

  test('priority select has P0-P5 options', async ({ page }) => {
    const prioritySelect = page.locator('select').first()
    await expect(prioritySelect).toBeVisible()

    const options = await prioritySelect.locator('option').allTextContents()
    expect(options).toEqual(['P0', 'P1', 'P2', 'P3', 'P4', 'P5'])
  })

  test('changing priority updates the value', async ({ page }) => {
    const prioritySelect = page.locator('select').first()
    await expect(prioritySelect).toBeVisible()
    await prioritySelect.selectOption('P5')
    await expect(prioritySelect).toHaveValue('P5')

    await prioritySelect.selectOption('P0')
    await expect(prioritySelect).toHaveValue('P0')
  })
})
