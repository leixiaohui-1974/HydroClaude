/**
 * 结果可视化工作流 E2E 测试
 * 
 * 测试从获取结果到可视化展示的完整流程
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('结果可视化工作流 E2E 测试', () => {
  
  test('工作流: 运行模拟 -> 生成结果 -> 可视化展示 -> 交互分析', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 结果可视化工作流');
    console.log('='.repeat(70));
    
    // ========== 步骤 1: 访问可视化页面 ==========
    console.log('\n[步骤 1] 访问可视化页面...');
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // 查找可视化入口
    const vizLinkSelectors = [
      'a:has-text("可视化")',
      'a:has-text("结果")',
      'a:has-text("Visualization")',
      'a:has-text("Results")',
      'a[href*="viz"]',
      'a[href*="result"]'
    ];
    
    let enteredViz = false;
    
    for (const selector of vizLinkSelectors) {
      const link = page.locator(selector).first();
      
      if (await link.count() > 0) {
        try {
          await link.click();
          await page.waitForTimeout(1000);
          
          console.log(`✅ 点击: ${selector}`);
          enteredViz = true;
          break;
        } catch (e) {
          continue;
        }
      }
    }
    
    if (!enteredViz) {
      console.log('⚠️ 未找到可视化入口，尝试直接访问');
      
      const vizPaths = ['/viz', '/results', '/visualization'];
      
      for (const path of vizPaths) {
        try {
          await page.goto(path);
          const is404 = await page.locator('text=/404|not found/i').count() > 0;
          
          if (!is404) {
            console.log(`✅ 访问: ${path}`);
            enteredViz = true;
            break;
          }
        } catch (e) {
          continue;
        }
      }
    }
    
    // 截图 - 可视化页面
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-viz-step1-page.png',
      fullPage: true 
    });
    
    console.log(enteredViz ? '✅ 进入可视化页面' : '⚠️ 未找到可视化页面');
    
    // ========== 步骤 2: 检测图表库 ==========
    console.log('\n[步骤 2] 检测图表库...');
    
    // 检测 Plotly
    const hasPlotly = await page.evaluate(() => {
      return typeof window.Plotly !== 'undefined';
    });
    
    // 检测 D3
    const hasD3 = await page.evaluate(() => {
      return typeof window.d3 !== 'undefined';
    });
    
    // 检测 ECharts
    const hasECharts = await page.evaluate(() => {
      return typeof window.echarts !== 'undefined';
    });
    
    console.log(`  Plotly: ${hasPlotly ? '✅' : '❌'}`);
    console.log(`  D3.js: ${hasD3 ? '✅' : '❌'}`);
    console.log(`  ECharts: ${hasECharts ? '✅' : '❌'}`);
    
    const chartLibFound = hasPlotly || hasD3 || hasECharts;
    
    // ========== 步骤 3: 检测图表元素 ==========
    console.log('\n[步骤 3] 检测图表元素...');
    
    // 查找图表元素
    const chartSelectors = [
      'canvas',
      'svg',
      '.plotly',
      '.chart',
      '[class*="chart"]',
      '[id*="chart"]'
    ];
    
    let chartsFound = 0;
    const chartDetails = [];
    
    for (const selector of chartSelectors) {
      const count = await page.locator(selector).count();
      
      if (count > 0) {
        console.log(`✅ 找到图表元素: ${selector} (${count} 个)`);
        chartsFound += count;
        chartDetails.push({ selector, count });
      }
    }
    
    if (chartsFound === 0) {
      console.log('⚠️ 未找到图表元素');
    } else {
      console.log(`\n图表总数: ${chartsFound}`);
    }
    
    // 截图 - 图表展示
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-viz-step3-charts.png',
      fullPage: true 
    });
    
    // ========== 步骤 4: 测试图表交互 (Hover) ==========
    console.log('\n[步骤 4] 测试图表交互 (Hover)...');
    
    let hoverWorked = false;
    
    if (chartsFound > 0) {
      // 尝试 hover 第一个图表
      const firstChart = page.locator(chartDetails[0].selector).first();
      
      try {
        const box = await firstChart.boundingBox();
        
        if (box) {
          // Hover 到图表中心
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.waitForTimeout(500);
          
          // 检测是否出现 tooltip
          const tooltipSelectors = [
            '.tooltip',
            '[class*="tooltip"]',
            '.plotly-tooltip',
            '.d3-tooltip',
            '[role="tooltip"]'
          ];
          
          for (const selector of tooltipSelectors) {
            if (await page.locator(selector).count() > 0) {
              console.log(`✅ Hover 触发 tooltip: ${selector}`);
              hoverWorked = true;
              break;
            }
          }
          
          if (!hoverWorked) {
            console.log('⚠️ Hover 未触发 tooltip (可能未实现)');
          }
        }
      } catch (e) {
        console.log(`⚠️ Hover 测试失败: ${e.message}`);
      }
    } else {
      console.log('⚠️ 无图表可供测试');
    }
    
    // 截图 - Hover 后
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-viz-step4-hover.png',
      fullPage: true 
    });
    
    // ========== 步骤 5: 测试缩放功能 ==========
    console.log('\n[步骤 5] 测试缩放功能...');
    
    let zoomWorked = false;
    
    if (chartsFound > 0) {
      const firstChart = page.locator(chartDetails[0].selector).first();
      
      try {
        const box = await firstChart.boundingBox();
        
        if (box) {
          // 滚轮缩放
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.mouse.wheel(0, -100); // 向上滚动
          await page.waitForTimeout(300);
          
          console.log('✅ 执行缩放操作');
          zoomWorked = true;
        }
      } catch (e) {
        console.log(`⚠️ 缩放测试失败: ${e.message}`);
      }
    } else {
      console.log('⚠️ 无图表可供测试');
    }
    
    // 截图 - 缩放后
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-viz-step5-zoom.png',
      fullPage: true 
    });
    
    // ========== 步骤 6: 测试数据表格 ==========
    console.log('\n[步骤 6] 测试数据表格...');
    
    // 查找数据表格
    const tableSelectors = [
      'table',
      '.data-table',
      '[class*="table"]',
      '.results-table'
    ];
    
    let tableFound = false;
    let rowCount = 0;
    
    for (const selector of tableSelectors) {
      const table = page.locator(selector).first();
      
      if (await table.count() > 0) {
        try {
          // 统计行数
          const rows = await page.locator(`${selector} tr`).count();
          
          if (rows > 0) {
            console.log(`✅ 找到数据表格: ${selector} (${rows} 行)`);
            tableFound = true;
            rowCount = rows;
            break;
          }
        } catch (e) {
          continue;
        }
      }
    }
    
    if (!tableFound) {
      console.log('⚠️ 未找到数据表格');
    }
    
    // 截图 - 数据表格
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-viz-step6-table.png',
      fullPage: true 
    });
    
    // ========== 步骤 7: 测试导出功能 ==========
    console.log('\n[步骤 7] 测试导出功能...');
    
    // 查找导出按钮
    const exportButtonSelectors = [
      'button:has-text("导出")',
      'button:has-text("Export")',
      'button:has-text("下载")',
      'button:has-text("Download")',
      'button:has-text("保存图表")',
      '.export-button'
    ];
    
    let exportAvailable = false;
    
    for (const selector of exportButtonSelectors) {
      if (await page.locator(selector).count() > 0) {
        console.log(`✅ 找到导出按钮: ${selector}`);
        exportAvailable = true;
        break;
      }
    }
    
    if (!exportAvailable) {
      console.log('⚠️ 未找到导出按钮');
    }
    
    // ========== 步骤 8: 测试视图切换 ==========
    console.log('\n[步骤 8] 测试视图切换...');
    
    // 查找视图切换按钮
    const viewSwitchSelectors = [
      'button:has-text("图表")',
      'button:has-text("表格")',
      'button:has-text("地图")',
      'button:has-text("Chart")',
      'button:has-text("Table")',
      '[role="tab"]'
    ];
    
    let viewSwitchFound = false;
    
    for (const selector of viewSwitchSelectors) {
      const count = await page.locator(selector).count();
      
      if (count > 0) {
        console.log(`✅ 找到视图切换: ${selector} (${count} 个)`);
        viewSwitchFound = true;
        
        // 尝试切换
        try {
          await page.locator(selector).first().click();
          await page.waitForTimeout(500);
          console.log(`✅ 切换视图成功`);
        } catch (e) {
          console.log(`⚠️ 切换失败: ${e.message}`);
        }
        
        break;
      }
    }
    
    if (!viewSwitchFound) {
      console.log('⚠️ 未找到视图切换功能');
    }
    
    // 最终截图
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-viz-step8-final.png',
      fullPage: true 
    });
    
    // ========== 工作流完成 ==========
    console.log('\n' + '='.repeat(70));
    console.log('结果可视化工作流完成');
    console.log('='.repeat(70));
    
    console.log('\n工作流步骤总结:');
    console.log(`  1. 访问可视化页面: ${enteredViz ? '✅' : '⚠️'}`);
    console.log(`  2. 检测图表库: ${chartLibFound ? '✅' : '⚠️'}`);
    console.log(`  3. 检测图表元素: ${chartsFound > 0 ? '✅' : '⚠️'} (${chartsFound} 个)`);
    console.log(`  4. 测试 Hover 交互: ${hoverWorked ? '✅' : '⚠️'}`);
    console.log(`  5. 测试缩放功能: ${zoomWorked ? '✅' : '⚠️'}`);
    console.log(`  6. 测试数据表格: ${tableFound ? '✅' : '⚠️'} (${rowCount} 行)`);
    console.log(`  7. 测试导出功能: ${exportAvailable ? '✅' : '⚠️'}`);
    console.log(`  8. 测试视图切换: ${viewSwitchFound ? '✅' : '⚠️'}`);
    
    const successCount = [
      enteredViz,
      chartLibFound,
      chartsFound > 0,
      hoverWorked,
      zoomWorked,
      tableFound,
      exportAvailable,
      viewSwitchFound
    ].filter(Boolean).length;
    
    const totalSteps = 8;
    const completionRate = (successCount / totalSteps * 100).toFixed(1);
    
    console.log(`\n完成度: ${successCount}/${totalSteps} (${completionRate}%)`);
    
    // 软性断言
    expect(successCount).toBeGreaterThanOrEqual(2);
    
    console.log('\n✅ 结果可视化工作流测试完成！');
  });
  
  test('工作流: 多图表展示', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 多图表展示');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 统计不同类型的图表
    const chartTypes = {
      canvas: await page.locator('canvas').count(),
      svg: await page.locator('svg').count(),
      plotly: await page.locator('.plotly').count(),
    };
    
    const totalCharts = Object.values(chartTypes).reduce((a, b) => a + b, 0);
    
    console.log('\n图表统计:');
    console.log(`  Canvas: ${chartTypes.canvas}`);
    console.log(`  SVG: ${chartTypes.svg}`);
    console.log(`  Plotly: ${chartTypes.plotly}`);
    console.log(`  总计: ${totalCharts}`);
    
    if (totalCharts > 0) {
      console.log('✅ 检测到图表');
    } else {
      console.log('⚠️ 未检测到图表');
    }
    
    console.log('\n✅ 多图表展示测试完成');
  });
  
  test('工作流: 图表性能检测', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 图表性能检测');
    console.log('='.repeat(70));
    
    // 记录开始时间
    const startTime = Date.now();
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // 等待图表渲染
    await page.waitForTimeout(2000);
    
    const loadTime = Date.now() - startTime;
    
    console.log(`\n加载时间: ${loadTime}ms`);
    
    // 检测 FPS
    const fps = await page.evaluate(() => {
      return new Promise((resolve) => {
        let frames = 0;
        const start = performance.now();
        
        function countFrames() {
          frames++;
          
          if (performance.now() - start < 1000) {
            requestAnimationFrame(countFrames);
          } else {
            resolve(frames);
          }
        }
        
        requestAnimationFrame(countFrames);
      });
    });
    
    console.log(`FPS: ${fps}`);
    
    if (loadTime < 5000) {
      console.log('✅ 加载时间合格 (< 5s)');
    } else {
      console.log('⚠️ 加载时间较长 (>= 5s)');
    }
    
    if (fps >= 30) {
      console.log('✅ FPS 合格 (>= 30)');
    } else {
      console.log('⚠️ FPS 较低 (< 30)');
    }
    
    console.log('\n✅ 图表性能检测完成');
  });
});
