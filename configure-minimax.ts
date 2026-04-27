import { chromium } from '@playwright/test';

async function configureMiniMax() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('1. 打开应用...');
  await page.goto('http://localhost:5173');
  await page.waitForLoadState('networkidle');

  console.log('2. 点击"系统设置"标签...');
  await page.click('nav button:has-text("系统设置")');
  await page.waitForTimeout(2000);

  console.log('3. 选择提供商: 自定义...');
  // 展开 LLM 配置区域（如果需要）
  const providerSelector = page.locator('text=自定义').first();
  if (await providerSelector.isVisible()) {
    await providerSelector.click();
    await page.waitForTimeout(500);
  }

  // 查找并填写 API Key
  console.log('4. 填写 API Key...');
  const apiKeyInput = page.locator('input[type="password"], input[placeholder*="API"], input[placeholder*="Key"]').first();
  if (await apiKeyInput.isVisible()) {
    await apiKeyInput.fill('sk-cp-xMgG9N3YJzPo81kzeG3gf_KkGx6aM9kPtcoJTnvOhuG4nVjb43ejZl_T3SxqOky_FrwoZ7_MXJFGVBIoohV6Q-frc174H13ksMc2akhp6bmrcVdiQBS7mJk');
    console.log('   API Key 已填写');
  }

  // 查找并填写 Base URL
  console.log('5. 填写 Base URL...');
  const baseUrlInput = page.locator('input[placeholder*="URL"], input[placeholder*="base"]').first();
  if (await baseUrlInput.isVisible()) {
    await baseUrlInput.fill('https://api.minimaxi.com/v1');
    console.log('   Base URL 已填写: https://api.minimaxi.com/v1');
  }

  // 查找并填写 Model
  console.log('6. 填写 Model...');
  const modelInput = page.locator('input[placeholder*="Model"], input[placeholder*="模型"]').first();
  if (await modelInput.isVisible()) {
    await modelInput.fill('MiniMax-M2.7');
    console.log('   Model 已填写: MiniMax-M2.7');
  }

  // 查找并填写名称
  console.log('7. 填写提供商名称...');
  const nameInput = page.locator('input[placeholder*="名称"], input[placeholder*="Name"]').first();
  if (await nameInput.isVisible()) {
    await nameInput.fill('MiniMax');
    console.log('   名称已填写: MiniMax');
  }

  // 滚动到页面上方看是否需要展开更多配置
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);

  // 点击保存
  console.log('8. 点击保存按钮...');
  const saveButton = page.locator('button:has-text("保存"), button:has-text("Save"), button:has-text("保存配置")').first();
  if (await saveButton.isVisible()) {
    await saveButton.click();
    await page.waitForTimeout(2000);
    console.log('   保存成功');
  }

  // 点击测试连接
  console.log('9. 点击测试连接按钮...');
  const testButton = page.locator('button:has-text("测试连接"), button:has-text("测试"), button:has-text("Test")').first();
  if (await testButton.isVisible()) {
    await testButton.click();
    await page.waitForTimeout(5000); // 等待连接测试完成
    console.log('   测试连接中...');

    // 检查结果
    const resultText = await page.locator('text=/成功|失败|ok|error|Error/i').first().textContent().catch(() => '未找到结果');
    console.log('   结果:', resultText);
  }

  // 截图保存
  await page.screenshot({ path: '/tmp/minimax-config-result.png', fullPage: true });
  console.log('10. 截图已保存到 /tmp/minimax-config-result.png');

  await browser.close();
  console.log('完成!');
}

configureMiniMax().catch(console.error);
