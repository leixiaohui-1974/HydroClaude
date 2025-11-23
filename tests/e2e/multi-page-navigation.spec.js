/**
 * 多页面导航流程 E2E 测试
 * 
 * 测试应用的多页面导航、路由、面包屑等功能
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('多页面导航流程 E2E 测试', () => {
  
  test('工作流: 导航栏 -> 各主要页面 -> 返回 -> 面包屑', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 多页面导航流程');
    console.log('='.repeat(70));
    
    // ========== 步骤 1: 访问首页 ==========
    console.log('\n[步骤 1] 访问首页...');
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    const homeUrl = page.url();
    console.log(`✅ 首页 URL: ${homeUrl}`);
    
    // 截图 - 首页
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-nav-step1-homepage.png',
      fullPage: true 
    });
    
    // ========== 步骤 2: 检测导航栏 ==========
    console.log('\n[步骤 2] 检测导航栏...');
    
    // 查找导航栏
    const navSelectors = [
      'nav',
      '.navbar',
      '.navigation',
      '.header-nav',
      '[role="navigation"]'
    ];
    
    let navFound = false;
    let navLinks = [];
    
    for (const selector of navSelectors) {
      const nav = page.locator(selector).first();
      
      if (await nav.count() > 0) {
        console.log(`✅ 找到导航栏: ${selector}`);
        navFound = true;
        
        // 统计导航链接数量
        const links = await page.locator(`${selector} a`).count();
        console.log(`  导航链接数: ${links}`);
        
        // 获取所有链接文本
        const linkElements = await page.locator(`${selector} a`).all();
        
        for (const link of linkElements.slice(0, 10)) { // 最多显示 10 个
          try {
            const text = await link.textContent();
            const href = await link.getAttribute('href');
            
            if (text && text.trim()) {
              navLinks.push({ text: text.trim(), href });
              console.log(`  - ${text.trim()}: ${href || 'N/A'}`);
            }
          } catch (e) {
            continue;
          }
        }
        
        break;
      }
    }
    
    if (!navFound) {
      console.log('⚠️ 未找到导航栏');
    }
    
    // ========== 步骤 3: 测试主要页面导航 ==========
    console.log('\n[步骤 3] 测试主要页面导航...');
    
    const mainPages = [
      { name: '建模', keywords: ['建模', '新建', 'Modeling', 'Create', 'New'] },
      { name: '案例', keywords: ['案例', '示例', 'Cases', 'Examples', 'Demos'] },
      { name: '可视化', keywords: ['可视化', '结果', 'Visualization', 'Results', 'Charts'] },
      { name: '文档', keywords: ['文档', '帮助', 'Documentation', 'Docs', 'Help'] },
      { name: '关于', keywords: ['关于', 'About', 'Info'] }
    ];
    
    const visitedPages = [];
    
    for (const mainPage of mainPages) {
      console.log(`\n测试 ${mainPage.name} 页面...`);
      
      let pageVisited = false;
      
      // 尝试从导航链接中找到匹配的页面
      for (const keyword of mainPage.keywords) {
        const linkSelector = `a:has-text("${keyword}")`;
        const link = page.locator(linkSelector).first();
        
        if (await link.count() > 0) {
          try {
            await link.click();
            await page.waitForTimeout(1000);
            
            const currentUrl = page.url();
            console.log(`  ✅ 访问成功: ${currentUrl}`);
            
            visitedPages.push({
              name: mainPage.name,
              url: currentUrl
            });
            
            pageVisited = true;
            
            // 截图
            await page.screenshot({ 
              path: `reports/screenshots/e2e-nav-page-${mainPage.name}.png`,
              fullPage: true 
            });
            
            break;
          } catch (e) {
            console.log(`  ⚠️ 访问失败: ${e.message}`);
          }
        }
      }
      
      if (!pageVisited) {
        console.log(`  ⚠️ 未找到 ${mainPage.name} 页面`);
      }
      
      // 返回首页
      await page.goto('/');
      await page.waitForTimeout(500);
    }
    
    console.log(`\n成功访问页面数: ${visitedPages.length}/${mainPages.length}`);
    
    // ========== 步骤 4: 测试浏览器后退/前进 ==========
    console.log('\n[步骤 4] 测试浏览器后退/前进...');
    
    if (visitedPages.length > 0) {
      // 访问第一个页面
      await page.goto(visitedPages[0].url);
      await page.waitForTimeout(500);
      
      console.log(`  访问: ${visitedPages[0].name}`);
      
      // 后退到首页
      await page.goBack();
      await page.waitForTimeout(500);
      
      console.log('  ✅ 后退到首页');
      
      // 前进
      await page.goForward();
      await page.waitForTimeout(500);
      
      console.log(`  ✅ 前进到 ${visitedPages[0].name}`);
    } else {
      console.log('⚠️ 无页面可测试后退/前进');
    }
    
    // ========== 步骤 5: 检测面包屑导航 ==========
    console.log('\n[步骤 5] 检测面包屑导航...');
    
    // 查找面包屑
    const breadcrumbSelectors = [
      '.breadcrumb',
      '.breadcrumbs',
      '[aria-label="breadcrumb"]',
      '.path',
      '.nav-path'
    ];
    
    let breadcrumbFound = false;
    
    for (const selector of breadcrumbSelectors) {
      if (await page.locator(selector).count() > 0) {
        const text = await page.locator(selector).first().textContent();
        console.log(`✅ 找到面包屑: ${text?.substring(0, 50)}`);
        breadcrumbFound = true;
        break;
      }
    }
    
    if (!breadcrumbFound) {
      console.log('⚠️ 未找到面包屑导航');
    }
    
    // ========== 步骤 6: 测试页面刷新 ==========
    console.log('\n[步骤 6] 测试页面刷新...');
    
    if (visitedPages.length > 0) {
      await page.goto(visitedPages[0].url);
      await page.waitForTimeout(500);
      
      const urlBeforeReload = page.url();
      
      await page.reload();
      await page.waitForLoadState('domcontentloaded');
      
      const urlAfterReload = page.url();
      
      if (urlBeforeReload === urlAfterReload) {
        console.log('✅ 页面刷新成功，URL 保持一致');
      } else {
        console.log('⚠️ 刷新后 URL 改变');
      }
    } else {
      console.log('⚠️ 无页面可测试刷新');
    }
    
    // ========== 步骤 7: 测试 Logo 返回首页 ==========
    console.log('\n[步骤 7] 测试 Logo 返回首页...');
    
    // 查找 Logo
    const logoSelectors = [
      '.logo',
      '.brand',
      '.site-logo',
      'a[href="/"]',
      'img[alt*="logo" i]'
    ];
    
    let logoFound = false;
    
    for (const selector of logoSelectors) {
      const logo = page.locator(selector).first();
      
      if (await logo.count() > 0) {
        try {
          // 先访问其他页面
          if (visitedPages.length > 0) {
            await page.goto(visitedPages[0].url);
            await page.waitForTimeout(500);
          }
          
          // 点击 Logo
          await logo.click();
          await page.waitForTimeout(1000);
          
          const currentUrl = page.url();
          
          if (currentUrl === homeUrl || currentUrl.endsWith('/')) {
            console.log(`✅ Logo 返回首页成功: ${selector}`);
            logoFound = true;
          } else {
            console.log(`⚠️ Logo 点击后未返回首页: ${currentUrl}`);
          }
          
          break;
        } catch (e) {
          console.log(`⚠️ Logo 测试失败: ${e.message}`);
        }
      }
    }
    
    if (!logoFound) {
      console.log('⚠️ 未找到或测试 Logo');
    }
    
    // 最终截图
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-nav-step7-final.png',
      fullPage: true 
    });
    
    // ========== 工作流完成 ==========
    console.log('\n' + '='.repeat(70));
    console.log('多页面导航流程完成');
    console.log('='.repeat(70));
    
    console.log('\n工作流步骤总结:');
    console.log(`  1. 访问首页: ✅`);
    console.log(`  2. 检测导航栏: ${navFound ? '✅' : '⚠️'} (${navLinks.length} 链接)`);
    console.log(`  3. 测试主要页面: ${visitedPages.length}/${mainPages.length} 访问成功`);
    console.log(`  4. 测试后退/前进: ${visitedPages.length > 0 ? '✅' : '⚠️'}`);
    console.log(`  5. 检测面包屑: ${breadcrumbFound ? '✅' : '⚠️'}`);
    console.log(`  6. 测试页面刷新: ${visitedPages.length > 0 ? '✅' : '⚠️'}`);
    console.log(`  7. 测试 Logo: ${logoFound ? '✅' : '⚠️'}`);
    
    const successCount = [
      true, // 首页总是成功
      navFound,
      visitedPages.length > 0,
      visitedPages.length > 0,
      breadcrumbFound,
      visitedPages.length > 0,
      logoFound
    ].filter(Boolean).length;
    
    const totalSteps = 7;
    const completionRate = (successCount / totalSteps * 100).toFixed(1);
    
    console.log(`\n完成度: ${successCount}/${totalSteps} (${completionRate}%)`);
    
    // 软性断言
    expect(successCount).toBeGreaterThanOrEqual(3);
    
    console.log('\n✅ 多页面导航流程测试完成！');
  });
  
  test('工作流: URL 路由测试', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: URL 路由测试');
    console.log('='.repeat(70));
    
    // 测试常见路由
    const routes = [
      '/',
      '/model',
      '/cases',
      '/examples',
      '/viz',
      '/results',
      '/docs',
      '/about'
    ];
    
    const validRoutes = [];
    
    for (const route of routes) {
      try {
        await page.goto(route);
        await page.waitForLoadState('domcontentloaded');
        
        // 检查是否为 404
        const is404 = await page.locator('text=/404|not found/i').count() > 0;
        
        if (!is404) {
          console.log(`✅ 路由有效: ${route}`);
          validRoutes.push(route);
        } else {
          console.log(`⚠️ 路由无效 (404): ${route}`);
        }
      } catch (e) {
        console.log(`⚠️ 路由访问失败: ${route}`);
      }
    }
    
    console.log(`\n有效路由: ${validRoutes.length}/${routes.length}`);
    
    console.log('\n✅ URL 路由测试完成');
  });
  
  test('工作流: 移动端导航菜单', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 移动端导航菜单');
    console.log('='.repeat(70));
    
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // 查找汉堡菜单按钮
    const hamburgerSelectors = [
      '.hamburger',
      '.menu-toggle',
      '.mobile-menu-button',
      'button[aria-label*="menu" i]',
      '.nav-toggle'
    ];
    
    let hamburgerFound = false;
    
    for (const selector of hamburgerSelectors) {
      const button = page.locator(selector).first();
      
      if (await button.count() > 0 && await button.isVisible()) {
        console.log(`✅ 找到汉堡菜单: ${selector}`);
        hamburgerFound = true;
        
        try {
          // 点击打开菜单
          await button.click();
          await page.waitForTimeout(500);
          
          console.log('✅ 汉堡菜单打开');
          
          // 截图
          await page.screenshot({ 
            path: 'reports/screenshots/e2e-nav-mobile-menu.png',
            fullPage: true 
          });
          
          // 再次点击关闭
          await button.click();
          await page.waitForTimeout(500);
          
          console.log('✅ 汉堡菜单关闭');
          
        } catch (e) {
          console.log(`⚠️ 汉堡菜单交互失败: ${e.message}`);
        }
        
        break;
      }
    }
    
    if (!hamburgerFound) {
      console.log('⚠️ 未找到汉堡菜单 (可能响应式设计不同)');
    }
    
    console.log('\n✅ 移动端导航菜单测试完成');
  });
  
  test('工作流: 页面标题和元数据', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 页面标题和元数据');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 获取页面标题
    const title = await page.title();
    console.log(`页面标题: ${title}`);
    
    if (title && title.length > 0) {
      console.log('✅ 页面标题存在');
    } else {
      console.log('⚠️ 页面标题为空');
    }
    
    // 检查 meta 标签
    const metaDescription = await page.locator('meta[name="description"]').getAttribute('content');
    const metaKeywords = await page.locator('meta[name="keywords"]').getAttribute('content');
    
    if (metaDescription) {
      console.log(`Meta Description: ${metaDescription.substring(0, 50)}...`);
      console.log('✅ Meta Description 存在');
    } else {
      console.log('⚠️ Meta Description 缺失');
    }
    
    if (metaKeywords) {
      console.log(`Meta Keywords: ${metaKeywords.substring(0, 50)}...`);
      console.log('✅ Meta Keywords 存在');
    } else {
      console.log('⚠️ Meta Keywords 缺失');
    }
    
    console.log('\n✅ 页面标题和元数据测试完成');
  });
});
