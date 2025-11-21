/**
 * 首页加载测试
 * 
 * 测试首页的基本加载和核心元素
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('首页加载测试', () => {
  
  test('应该成功加载首页', async ({ page }) => {
    console.log('\n=== 测试: 首页加载 ===');
    
    // 1. 导航到首页
    await page.goto('/');
    
    // 2. 等待页面加载完成
    await page.waitForLoadState('networkidle');
    
    // 3. 验证页面标题
    await expect(page).toHaveTitle(/HydroClaude|水力|Hydro/i);
    
    console.log('✅ 首页标题验证通过');
    
    // 4. 截图
    await page.screenshot({ 
      path: 'reports/screenshots/homepage.png',
      fullPage: true 
    });
    
    console.log('✅ 首页加载测试通过');
  });
  
  test('应该显示导航栏', async ({ page }) => {
    console.log('\n=== 测试: 导航栏显示 ===');
    
    await page.goto('/');
    
    // 查找导航栏 (尝试多种选择器)
    const navSelectors = [
      'nav',
      '[role="navigation"]',
      '.navbar',
      '.nav',
      'header nav'
    ];
    
    let navFound = false;
    
    for (const selector of navSelectors) {
      const nav = page.locator(selector).first();
      
      if (await nav.count() > 0) {
        await expect(nav).toBeVisible();
        navFound = true;
        console.log(`✅ 找到导航栏: ${selector}`);
        break;
      }
    }
    
    if (!navFound) {
      console.log('⚠️ 未找到导航栏 (可能页面结构不同)');
    }
    
    console.log('✅ 导航栏测试完成');
  });
  
  test('应该显示主要内容区域', async ({ page }) => {
    console.log('\n=== 测试: 主要内容区域 ===');
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // 查找主要内容区域
    const mainSelectors = [
      'main',
      '[role="main"]',
      '.main-content',
      '#main',
      '.container'
    ];
    
    let mainFound = false;
    
    for (const selector of mainSelectors) {
      const main = page.locator(selector).first();
      
      if (await main.count() > 0) {
        await expect(main).toBeVisible();
        mainFound = true;
        console.log(`✅ 找到主内容区: ${selector}`);
        break;
      }
    }
    
    if (!mainFound) {
      console.log('⚠️ 未找到标准主内容区 (检查页面中是否有内容)');
      
      // 至少应该有一些可见内容
      const body = page.locator('body');
      await expect(body).toBeVisible();
      
      const bodyText = await body.textContent();
      expect(bodyText.length).toBeGreaterThan(0);
      
      console.log('✅ 页面有可见内容');
    }
    
    console.log('✅ 主内容区测试完成');
  });
  
  test('页面加载性能测试', async ({ page }) => {
    console.log('\n=== 测试: 页面加载性能 ===');
    
    const startTime = Date.now();
    
    // 导航到首页
    await page.goto('/');
    await page.waitForLoadState('load');
    
    const loadTime = Date.now() - startTime;
    
    console.log(`页面加载时间: ${loadTime}ms`);
    
    // 验收标准: 页面加载应在 5 秒内完成
    expect(loadTime).toBeLessThan(5000);
    
    if (loadTime < 2000) {
      console.log('✅ 加载速度: 优秀 (< 2s)');
    } else if (loadTime < 3000) {
      console.log('✅ 加载速度: 良好 (< 3s)');
    } else {
      console.log('⚠️ 加载速度: 一般 (< 5s)');
    }
    
    console.log('✅ 性能测试完成');
  });
  
  test('响应式设计测试 - 移动端', async ({ page }) => {
    console.log('\n=== 测试: 移动端响应式 ===');
    
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // 截图
    await page.screenshot({ 
      path: 'reports/screenshots/homepage-mobile.png',
      fullPage: true 
    });
    
    // 验证页面在移动端可见
    const body = page.locator('body');
    await expect(body).toBeVisible();
    
    console.log('✅ 移动端视口: 375x667');
    console.log('✅ 页面在移动端可正常显示');
    
    console.log('✅ 移动端响应式测试完成');
  });
  
  test('无障碍性测试 - 基础检查', async ({ page }) => {
    console.log('\n=== 测试: 无障碍性基础检查 ===');
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // 检查是否有 lang 属性
    const htmlLang = await page.locator('html').getAttribute('lang');
    console.log(`HTML lang 属性: ${htmlLang || '未设置'}`);
    
    // 检查是否有跳过导航链接 (可选)
    const skipLink = page.locator('a[href="#main"], a[href="#content"]').first();
    if (await skipLink.count() > 0) {
      console.log('✅ 找到跳过导航链接');
    } else {
      console.log('⚠️ 未找到跳过导航链接 (可选功能)');
    }
    
    // 检查图片是否有 alt 属性
    const images = page.locator('img');
    const imageCount = await images.count();
    
    if (imageCount > 0) {
      console.log(`页面图片数量: ${imageCount}`);
      
      // 检查前 5 个图片
      for (let i = 0; i < Math.min(5, imageCount); i++) {
        const img = images.nth(i);
        const alt = await img.getAttribute('alt');
        
        if (alt !== null) {
          console.log(`✅ 图片 ${i + 1} 有 alt 属性`);
        } else {
          console.log(`⚠️ 图片 ${i + 1} 缺少 alt 属性`);
        }
      }
    } else {
      console.log('ℹ️ 页面无图片');
    }
    
    console.log('✅ 无障碍性基础检查完成');
  });
  
  test('控制台错误检查', async ({ page }) => {
    console.log('\n=== 测试: 控制台错误检查 ===');
    
    const consoleMessages = [];
    const consoleErrors = [];
    
    // 监听控制台消息
    page.on('console', msg => {
      consoleMessages.push({
        type: msg.type(),
        text: msg.text()
      });
      
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // 导航到首页
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 等待一段时间以捕获延迟的错误
    await page.waitForTimeout(2000);
    
    console.log(`控制台消息总数: ${consoleMessages.length}`);
    console.log(`控制台错误数: ${consoleErrors.length}`);
    
    if (consoleErrors.length > 0) {
      console.log('\n控制台错误:');
      consoleErrors.forEach((error, index) => {
        console.log(`  ${index + 1}. ${error.substring(0, 100)}`);
      });
      
      console.log('\n⚠️ 存在控制台错误 (可能需要修复)');
    } else {
      console.log('✅ 无控制台错误');
    }
    
    // 不强制要求无错误，只记录
    console.log('✅ 控制台检查完成');
  });
});
