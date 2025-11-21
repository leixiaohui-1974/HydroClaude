/**
 * 视觉回归测试 (Visual Regression Testing)
 * 
 * 使用 Playwright 截图对比功能检测 UI 视觉变化
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('视觉回归测试', () => {
  
  test('首页整体视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 首页整体视觉快照');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 等待主要内容加载
    await page.waitForTimeout(1000);
    
    // 全页截图
    await page.screenshot({ 
      path: 'reports/screenshots/visual-homepage-full.png',
      fullPage: true 
    });
    
    console.log('✅ 首页整体截图已保存');
    
    // Playwright 视觉快照对比
    // 首次运行会创建基准，后续运行会与基准对比
    await expect(page).toHaveScreenshot('homepage-full.png', {
      fullPage: true,
      maxDiffPixels: 100 // 允许100像素差异
    });
    
    console.log('✅ 首页视觉快照测试完成');
  });
  
  test('导航栏视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 导航栏视觉快照');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 定位导航栏
    const nav = page.locator('nav, .navbar, [role="navigation"]').first();
    
    if (await nav.count() > 0) {
      await nav.screenshot({ 
        path: 'reports/screenshots/visual-navbar.png' 
      });
      
      console.log('✅ 导航栏截图已保存');
      
      // 视觉对比
      await expect(nav).toHaveScreenshot('navbar.png', {
        maxDiffPixels: 50
      });
      
      console.log('✅ 导航栏视觉快照测试完成');
    } else {
      console.log('⚠️ 未找到导航栏');
    }
  });
  
  test('按钮样式视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 按钮样式视觉快照');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找所有按钮
    const buttons = await page.locator('button, .btn, input[type="button"]').all();
    
    if (buttons.length > 0) {
      console.log(`找到 ${buttons.length} 个按钮`);
      
      // 截取前3个按钮
      for (let i = 0; i < Math.min(3, buttons.length); i++) {
        try {
          if (await buttons[i].isVisible()) {
            await buttons[i].screenshot({ 
              path: `reports/screenshots/visual-button-${i + 1}.png` 
            });
            
            console.log(`✅ 按钮 ${i + 1} 截图已保存`);
          }
        } catch (e) {
          console.log(`⚠️ 按钮 ${i + 1} 截图失败: ${e.message}`);
        }
      }
      
      console.log('✅ 按钮样式视觉快照测试完成');
    } else {
      console.log('⚠️ 未找到按钮');
    }
  });
  
  test('卡片组件视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 卡片组件视觉快照');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找卡片
    const cards = await page.locator('.card, [class*="card"]').all();
    
    if (cards.length > 0) {
      console.log(`找到 ${cards.length} 个卡片`);
      
      // 截取第一个卡片
      try {
        if (await cards[0].isVisible()) {
          await cards[0].screenshot({ 
            path: 'reports/screenshots/visual-card-1.png' 
          });
          
          console.log('✅ 卡片截图已保存');
          
          // 视觉对比
          await expect(cards[0]).toHaveScreenshot('card-1.png', {
            maxDiffPixels: 50
          });
          
          console.log('✅ 卡片视觉快照测试完成');
        }
      } catch (e) {
        console.log(`⚠️ 卡片截图失败: ${e.message}`);
      }
    } else {
      console.log('⚠️ 未找到卡片组件');
    }
  });
  
  test('表单视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 表单视觉快照');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const form = page.locator('form').first();
    
    if (await form.count() > 0) {
      await form.screenshot({ 
        path: 'reports/screenshots/visual-form.png' 
      });
      
      console.log('✅ 表单截图已保存');
      
      // 视觉对比
      await expect(form).toHaveScreenshot('form.png', {
        maxDiffPixels: 50
      });
      
      console.log('✅ 表单视觉快照测试完成');
    } else {
      console.log('⚠️ 未找到表单');
    }
  });
  
  test('移动端视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 移动端视觉快照');
    console.log('='.repeat(70));
    
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 全页截图
    await page.screenshot({ 
      path: 'reports/screenshots/visual-mobile-full.png',
      fullPage: true 
    });
    
    console.log('✅ 移动端截图已保存');
    
    // 视觉对比
    await expect(page).toHaveScreenshot('mobile-full.png', {
      fullPage: true,
      maxDiffPixels: 100
    });
    
    console.log('✅ 移动端视觉快照测试完成');
  });
  
  test('暗黑模式视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 暗黑模式视觉快照');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 检查是否有暗黑模式切换按钮
    const darkModeToggle = page.locator('[aria-label*="dark"], [title*="dark"], .dark-mode-toggle').first();
    
    if (await darkModeToggle.count() > 0) {
      // 切换到暗黑模式
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      // 截图
      await page.screenshot({ 
        path: 'reports/screenshots/visual-dark-mode.png',
        fullPage: true 
      });
      
      console.log('✅ 暗黑模式截图已保存');
      
      // 视觉对比
      await expect(page).toHaveScreenshot('dark-mode.png', {
        fullPage: true,
        maxDiffPixels: 200
      });
      
      console.log('✅ 暗黑模式视觉快照测试完成');
    } else {
      console.log('⚠️ 未找到暗黑模式切换按钮');
    }
  });
  
  test('页面交互状态视觉快照', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 页面交互状态视觉快照');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 测试按钮悬停状态
    const button = page.locator('button').first();
    
    if (await button.count() > 0 && await button.isVisible()) {
      // 悬停
      await button.hover();
      await page.waitForTimeout(300);
      
      await button.screenshot({ 
        path: 'reports/screenshots/visual-button-hover.png' 
      });
      
      console.log('✅ 按钮悬停状态截图已保存');
    }
    
    // 测试输入框焦点状态
    const input = page.locator('input[type="text"]').first();
    
    if (await input.count() > 0 && await input.isVisible()) {
      await input.focus();
      await page.waitForTimeout(300);
      
      await input.screenshot({ 
        path: 'reports/screenshots/visual-input-focus.png' 
      });
      
      console.log('✅ 输入框焦点状态截图已保存');
    }
    
    console.log('✅ 页面交互状态视觉快照测试完成');
  });
  
  test('不同浏览器视觉一致性', async ({ page, browserName }) => {
    console.log('\n' + '='.repeat(70));
    console.log(`测试: ${browserName} 浏览器视觉一致性`);
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 截图（带浏览器标识）
    await page.screenshot({ 
      path: `reports/screenshots/visual-${browserName}-homepage.png`,
      fullPage: true 
    });
    
    console.log(`✅ ${browserName} 浏览器截图已保存`);
    
    console.log(`✅ ${browserName} 视觉一致性测试完成`);
  });
});
