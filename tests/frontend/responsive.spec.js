/**
 * 响应式设计测试
 * 
 * 测试前端在不同设备和屏幕尺寸下的响应式表现
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect, devices } = require('@playwright/test');

test.describe('响应式设计测试', () => {
  
  test('测试桌面端布局', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 桌面端布局 (1920x1080)');
    console.log('='.repeat(70));
    
    // 设置桌面端视口
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    
    // 检查导航栏
    const nav = page.locator('nav, .navbar, [role="navigation"]').first();
    
    if (await nav.count() > 0) {
      const box = await nav.boundingBox();
      console.log(`导航栏宽度: ${box?.width}px`);
      
      if (box && box.width > 1000) {
        console.log('✅ 导航栏充分利用桌面宽度');
      }
    }
    
    // 检查内容区域
    const main = page.locator('main, .main, .content, #content').first();
    
    if (await main.count() > 0) {
      const box = await main.boundingBox();
      console.log(`主内容区域宽度: ${box?.width}px`);
    }
    
    // 截图
    await page.screenshot({ 
      path: 'reports/screenshots/responsive-desktop-1920x1080.png',
      fullPage: true 
    });
    
    console.log('✅ 桌面端布局测试完成');
  });
  
  test('测试平板端布局', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 平板端布局 (768x1024)');
    console.log('='.repeat(70));
    
    // 设置平板端视口
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    
    // 检查布局变化
    const nav = page.locator('nav').first();
    
    if (await nav.count() > 0) {
      const box = await nav.boundingBox();
      console.log(`导航栏宽度: ${box?.width}px`);
      
      if (box && box.width <= 768) {
        console.log('✅ 导航栏适应平板宽度');
      }
    }
    
    // 检查是否有汉堡菜单
    const hamburger = page.locator('.hamburger, .menu-toggle, [aria-label*="menu"]').first();
    
    if (await hamburger.count() > 0 && await hamburger.isVisible()) {
      console.log('✅ 检测到汉堡菜单（响应式导航）');
    }
    
    // 截图
    await page.screenshot({ 
      path: 'reports/screenshots/responsive-tablet-768x1024.png',
      fullPage: true 
    });
    
    console.log('✅ 平板端布局测试完成');
  });
  
  test('测试移动端布局', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 移动端布局 (375x667)');
    console.log('='.repeat(70));
    
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // 检查视口meta标签
    const viewportMeta = await page.locator('meta[name="viewport"]').getAttribute('content');
    
    if (viewportMeta) {
      console.log(`✅ 视口配置: ${viewportMeta}`);
      
      if (viewportMeta.includes('width=device-width')) {
        console.log('✅ 正确配置了移动端视口');
      }
    } else {
      console.log('⚠️ 未找到视口meta标签');
    }
    
    // 检查汉堡菜单
    const hamburger = page.locator('.hamburger, .menu-toggle, [aria-label*="menu"]').first();
    
    if (await hamburger.count() > 0) {
      const isVisible = await hamburger.isVisible();
      console.log(`汉堡菜单可见: ${isVisible}`);
      
      if (isVisible) {
        // 测试点击汉堡菜单
        await hamburger.click();
        await page.waitForTimeout(500);
        
        console.log('✅ 汉堡菜单可点击');
      }
    }
    
    // 检查文字是否溢出
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = 375;
    
    if (bodyWidth <= viewportWidth) {
      console.log('✅ 内容适应移动端宽度（无横向滚动）');
    } else {
      console.log(`⚠️ 内容溢出: body宽度 ${bodyWidth}px > 视口宽度 ${viewportWidth}px`);
    }
    
    // 截图
    await page.screenshot({ 
      path: 'reports/screenshots/responsive-mobile-375x667.png',
      fullPage: true 
    });
    
    console.log('✅ 移动端布局测试完成');
  });
  
  test('测试小屏幕移动端', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 小屏幕移动端 (320x568)');
    console.log('='.repeat(70));
    
    // 设置小屏幕视口
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto('/');
    
    // 检查内容是否溢出
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    
    console.log(`body宽度: ${bodyWidth}px, 视口宽度: 320px`);
    
    if (bodyWidth <= 320) {
      console.log('✅ 内容适应小屏幕（无横向滚动）');
    } else {
      console.log(`⚠️ 内容溢出: ${bodyWidth}px > 320px`);
    }
    
    // 截图
    await page.screenshot({ 
      path: 'reports/screenshots/responsive-small-mobile-320x568.png',
      fullPage: true 
    });
    
    console.log('✅ 小屏幕移动端测试完成');
  });
  
  test('测试横屏模式', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 横屏模式 (667x375)');
    console.log('='.repeat(70));
    
    // 设置横屏视口
    await page.setViewportSize({ width: 667, height: 375 });
    await page.goto('/');
    
    // 检查布局是否适应横屏
    const main = page.locator('main, .main').first();
    
    if (await main.count() > 0) {
      const box = await main.boundingBox();
      
      if (box) {
        console.log(`主内容区域: ${box.width}x${box.height}`);
        
        if (box.width > box.height) {
          console.log('✅ 布局适应横屏比例');
        }
      }
    }
    
    // 截图
    await page.screenshot({ 
      path: 'reports/screenshots/responsive-landscape-667x375.png',
      fullPage: true 
    });
    
    console.log('✅ 横屏模式测试完成');
  });
  
  test('测试2K显示器', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 2K显示器 (2560x1440)');
    console.log('='.repeat(70));
    
    // 设置2K视口
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto('/');
    
    // 检查布局是否充分利用大屏幕
    const container = page.locator('.container, .main, main').first();
    
    if (await container.count() > 0) {
      const box = await container.boundingBox();
      
      if (box) {
        console.log(`主容器宽度: ${box.width}px`);
        
        if (box.width >= 1200 && box.width <= 2000) {
          console.log('✅ 使用合理的max-width限制（提升可读性）');
        } else if (box.width > 2000) {
          console.log('⚠️ 内容过宽（可能影响可读性）');
        }
      }
    }
    
    // 截图
    await page.screenshot({ 
      path: 'reports/screenshots/responsive-2k-2560x1440.png',
      fullPage: true 
    });
    
    console.log('✅ 2K显示器测试完成');
  });
  
  test('测试响应式图片', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 响应式图片');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 检查图片是否使用响应式属性
    const imgWithSrcset = await page.locator('img[srcset]').count();
    const imgWithSizes = await page.locator('img[sizes]').count();
    const pictureElements = await page.locator('picture').count();
    
    console.log(`使用 srcset 的图片: ${imgWithSrcset}`);
    console.log(`使用 sizes 的图片: ${imgWithSizes}`);
    console.log(`使用 picture 元素: ${pictureElements}`);
    
    if (imgWithSrcset > 0 || pictureElements > 0) {
      console.log('✅ 使用了响应式图片技术');
    } else {
      console.log('⚠️ 未使用响应式图片（可能影响性能）');
    }
    
    // 检查图片是否溢出
    const images = await page.locator('img').all();
    let overflowCount = 0;
    
    for (const img of images.slice(0, 5)) { // 检查前5张图片
      try {
        const box = await img.boundingBox();
        const viewportWidth = page.viewportSize()?.width || 1920;
        
        if (box && box.width > viewportWidth) {
          overflowCount++;
        }
      } catch (e) {
        continue;
      }
    }
    
    if (overflowCount === 0) {
      console.log('✅ 图片适应视口宽度');
    } else {
      console.log(`⚠️ ${overflowCount} 张图片溢出视口`);
    }
    
    console.log('✅ 响应式图片测试完成');
  });
  
  test('测试断点切换', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 断点切换');
    console.log('='.repeat(70));
    
    // 测试常见断点
    const breakpoints = [
      { name: '移动端', width: 375, height: 667 },
      { name: '平板端', width: 768, height: 1024 },
      { name: '桌面端', width: 1280, height: 720 },
      { name: '大屏', width: 1920, height: 1080 }
    ];
    
    await page.goto('/');
    
    for (const bp of breakpoints) {
      await page.setViewportSize({ width: bp.width, height: bp.height });
      await page.waitForTimeout(300);
      
      // 检查body宽度
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      
      const isResponsive = bodyWidth <= bp.width;
      
      console.log(`${bp.name} (${bp.width}x${bp.height}): ${isResponsive ? '✅' : '⚠️'} (body宽度: ${bodyWidth}px)`);
    }
    
    console.log('✅ 断点切换测试完成');
  });
});
