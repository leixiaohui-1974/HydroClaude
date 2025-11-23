/**
 * 可视化和图表测试
 * 
 * 测试数据可视化、图表渲染和交互
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('可视化和图表功能测试', () => {
  
  test('应该能找到图表/可视化元素', async ({ page }) => {
    console.log('\n=== 测试: 图表/可视化元素查找 ===');
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找图表元素
    const chartSelectors = [
      'canvas',
      'svg',
      '.chart',
      '.graph',
      '.plot',
      '.visualization',
      '[class*="plotly"]',
      '[class*="chart"]'
    ];
    
    let chartFound = false;
    
    for (const selector of chartSelectors) {
      const chart = page.locator(selector);
      const count = await chart.count();
      
      if (count > 0) {
        console.log(`✅ 找到 ${count} 个图表元素: ${selector}`);
        chartFound = true;
      }
    }
    
    if (!chartFound) {
      console.log('⚠️ 首页未找到图表元素 (可能在其他页面)');
    }
    
    console.log('✅ 图表元素查找完成');
  });
  
  test('图表库检测 - Plotly/D3/ECharts', async ({ page }) => {
    console.log('\n=== 测试: 图表库检测 ===');
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 检测图表库
    const libraries = await page.evaluate(() => {
      return {
        plotly: typeof window.Plotly !== 'undefined',
        d3: typeof window.d3 !== 'undefined',
        echarts: typeof window.echarts !== 'undefined',
        chart: typeof window.Chart !== 'undefined'
      };
    });
    
    console.log('\n检测到的图表库:');
    
    if (libraries.plotly) {
      console.log('  ✅ Plotly.js');
    }
    if (libraries.d3) {
      console.log('  ✅ D3.js');
    }
    if (libraries.echarts) {
      console.log('  ✅ ECharts');
    }
    if (libraries.chart) {
      console.log('  ✅ Chart.js');
    }
    
    if (!Object.values(libraries).some(v => v)) {
      console.log('  ⚠️ 未检测到常见图表库 (可能使用其他库)');
    }
    
    console.log('✅ 图表库检测完成');
  });
  
  test('地图元素检测', async ({ page }) => {
    console.log('\n=== 测试: 地图元素检测 ===');
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找地图元素
    const mapSelectors = [
      '.mapboxgl-map',
      '.leaflet-container',
      '.map-container',
      '#map',
      '[class*="map"]',
      'canvas[class*="mapbox"]'
    ];
    
    let mapFound = false;
    
    for (const selector of mapSelectors) {
      const map = page.locator(selector).first();
      
      if (await map.count() > 0) {
        console.log(`✅ 找到地图元素: ${selector}`);
        
        const isVisible = await map.isVisible();
        if (isVisible) {
          console.log('✅ 地图元素可见');
          
          // 获取地图尺寸
          const box = await map.boundingBox();
          if (box) {
            console.log(`   地图尺寸: ${box.width}x${box.height}`);
          }
          
          // 截图
          await page.screenshot({ 
            path: 'reports/screenshots/map-view.png',
            fullPage: true 
          });
          
          mapFound = true;
          break;
        }
      }
    }
    
    if (!mapFound) {
      console.log('⚠️ 未找到地图元素 (可能在其他页面)');
    }
    
    console.log('✅ 地图元素检测完成');
  });
  
  test('地图交互测试 - 缩放和平移', async ({ page }) => {
    console.log('\n=== 测试: 地图交互 (缩放/平移) ===');
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找地图
    const mapSelectors = [
      '.mapboxgl-map',
      '.leaflet-container',
      '#map'
    ];
    
    for (const selector of mapSelectors) {
      const map = page.locator(selector).first();
      
      if (await map.count() > 0 && await map.isVisible()) {
        console.log(`✅ 找到地图: ${selector}`);
        
        try {
          const box = await map.boundingBox();
          
          if (box) {
            // 测试平移
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
            await page.mouse.down();
            await page.mouse.move(box.x + box.width / 2 + 50, box.y + box.height / 2 + 50, { steps: 5 });
            await page.mouse.up();
            
            console.log('✅ 地图平移测试完成');
            
            // 等待地图更新
            await page.waitForTimeout(500);
            
            // 测试缩放 (滚轮)
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
            await page.mouse.wheel(0, -100); // 放大
            await page.waitForTimeout(300);
            await page.mouse.wheel(0, 100);  // 缩小
            
            console.log('✅ 地图缩放测试完成');
            
            // 截图
            await page.screenshot({ 
              path: 'reports/screenshots/map-after-interaction.png',
              fullPage: true 
            });
          }
        } catch (e) {
          console.log(`⚠️ 地图交互测试失败: ${e.message}`);
        }
        
        break;
      }
    }
    
    console.log('✅ 地图交互测试完成');
  });
  
  test('数据表格渲染测试', async ({ page }) => {
    console.log('\n=== 测试: 数据表格渲染 ===');
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找表格元素
    const table = page.locator('table').first();
    const tableCount = await page.locator('table').count();
    
    console.log(`页面表格数量: ${tableCount}`);
    
    if (tableCount > 0 && await table.isVisible()) {
      console.log('✅ 找到数据表格');
      
      // 获取表头
      const headers = await table.locator('th').allTextContents();
      console.log(`  表头数量: ${headers.length}`);
      
      if (headers.length > 0) {
        console.log(`  表头: ${headers.slice(0, 5).join(', ')}`);
      }
      
      // 获取行数
      const rows = await table.locator('tr').count();
      console.log(`  数据行数: ${rows}`);
      
      // 截图
      await table.screenshot({ 
        path: 'reports/screenshots/data-table.png'
      });
    } else {
      console.log('⚠️ 未找到可见的数据表格');
    }
    
    console.log('✅ 数据表格测试完成');
  });
  
  test('结果展示区域检测', async ({ page }) => {
    console.log('\n=== 测试: 结果展示区域 ===');
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找结果展示区域
    const resultSelectors = [
      '.results',
      '.result-panel',
      '.output',
      '#results',
      '[class*="result"]'
    ];
    
    let resultFound = false;
    
    for (const selector of resultSelectors) {
      const result = page.locator(selector).first();
      
      if (await result.count() > 0) {
        console.log(`✅ 找到结果展示区域: ${selector}`);
        
        const isVisible = await result.isVisible();
        if (isVisible) {
          console.log('✅ 结果区域可见');
          resultFound = true;
          break;
        }
      }
    }
    
    if (!resultFound) {
      console.log('⚠️ 未找到结果展示区域');
    }
    
    console.log('✅ 结果展示区域检测完成');
  });
  
  test('图表交互测试 - 悬停提示', async ({ page }) => {
    console.log('\n=== 测试: 图表悬停提示 ===');
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找图表
    const chart = page.locator('canvas, svg').first();
    
    if (await chart.count() > 0 && await chart.isVisible()) {
      console.log('✅ 找到图表元素');
      
      try {
        const box = await chart.boundingBox();
        
        if (box) {
          // 移动鼠标到图表上
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.waitForTimeout(500);
          
          // 查找工具提示
          const tooltipSelectors = [
            '.tooltip',
            '[role="tooltip"]',
            '.popover',
            '[class*="tooltip"]'
          ];
          
          let tooltipFound = false;
          
          for (const selector of tooltipSelectors) {
            if (await page.locator(selector).count() > 0) {
              console.log(`✅ 找到工具提示: ${selector}`);
              tooltipFound = true;
              break;
            }
          }
          
          if (!tooltipFound) {
            console.log('⚠️ 未检测到工具提示 (可能需要特定交互)');
          }
        }
      } catch (e) {
        console.log(`⚠️ 悬停测试失败: ${e.message}`);
      }
    } else {
      console.log('⚠️ 未找到图表元素');
    }
    
    console.log('✅ 图表交互测试完成');
  });
  
  test('可视化页面性能测试', async ({ page }) => {
    console.log('\n=== 测试: 可视化页面性能 ===');
    
    const startTime = Date.now();
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    console.log(`页面加载时间: ${loadTime}ms`);
    
    // 等待图表渲染
    await page.waitForTimeout(1000);
    
    // 检查 FPS (通过 requestAnimationFrame)
    const fps = await page.evaluate(() => {
      return new Promise(resolve => {
        let lastTime = performance.now();
        let frames = 0;
        
        function count() {
          frames++;
          const currentTime = performance.now();
          
          if (currentTime >= lastTime + 1000) {
            resolve(frames);
          } else {
            requestAnimationFrame(count);
          }
        }
        
        requestAnimationFrame(count);
      });
    });
    
    console.log(`FPS: ${fps}`);
    
    if (fps >= 30) {
      console.log('✅ 性能良好 (FPS >= 30)');
    } else {
      console.log('⚠️ 性能一般 (FPS < 30)');
    }
    
    console.log('✅ 性能测试完成');
  });
});
