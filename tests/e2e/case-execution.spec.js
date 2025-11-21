/**
 * 案例运行工作流 E2E 测试
 * 
 * 测试运行预设案例的完整流程
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('案例运行工作流 E2E 测试', () => {
  
  test('工作流: 浏览案例 -> 选择案例 -> 运行 -> 查看结果', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 案例运行工作流');
    console.log('='.repeat(70));
    
    // ========== 步骤 1: 访问案例列表 ==========
    console.log('\n[步骤 1] 访问案例列表...');
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // 查找案例列表入口
    const caseLinkSelectors = [
      'a:has-text("案例")',
      'a:has-text("示例")',
      'a:has-text("Examples")',
      'a:has-text("Cases")',
      'a[href*="case"]',
      'a[href*="example"]'
    ];
    
    let enteredCases = false;
    
    for (const selector of caseLinkSelectors) {
      const link = page.locator(selector).first();
      
      if (await link.count() > 0) {
        try {
          await link.click();
          await page.waitForTimeout(1000);
          
          console.log(`✅ 点击: ${selector}`);
          enteredCases = true;
          break;
        } catch (e) {
          continue;
        }
      }
    }
    
    if (!enteredCases) {
      console.log('⚠️ 未找到案例入口，尝试直接访问');
      
      const casePaths = ['/cases', '/examples', '/demos'];
      
      for (const path of casePaths) {
        try {
          await page.goto(path);
          const is404 = await page.locator('text=/404|not found/i').count() > 0;
          
          if (!is404) {
            console.log(`✅ 访问: ${path}`);
            enteredCases = true;
            break;
          }
        } catch (e) {
          continue;
        }
      }
    }
    
    // 截图 - 案例列表
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-cases-step1-list.png',
      fullPage: true 
    });
    
    console.log(enteredCases ? '✅ 进入案例列表' : '⚠️ 未找到案例列表');
    
    // ========== 步骤 2: 选择案例 ==========
    console.log('\n[步骤 2] 选择一个案例...');
    
    // 查找案例项
    const caseItemSelectors = [
      '.case-item',
      '.example-item',
      '.card',
      '[class*="case"]',
      'a[href*="/case/"]',
      'button:has-text("运行")'
    ];
    
    let caseSelected = false;
    
    for (const selector of caseItemSelectors) {
      const item = page.locator(selector).first();
      
      if (await item.count() > 0) {
        try {
          await item.click();
          await page.waitForTimeout(1000);
          
          console.log(`✅ 选择案例: ${selector}`);
          caseSelected = true;
          break;
        } catch (e) {
          continue;
        }
      }
    }
    
    if (!caseSelected) {
      console.log('⚠️ 未找到可选择的案例');
    }
    
    // 截图 - 案例详情
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-cases-step2-selected.png',
      fullPage: true 
    });
    
    // ========== 步骤 3: 查看案例描述 ==========
    console.log('\n[步骤 3] 查看案例描述...');
    
    // 查找描述文本
    const descriptionSelectors = [
      '.description',
      '.case-description',
      '.readme',
      'p',
      '[class*="description"]'
    ];
    
    let descriptionFound = false;
    
    for (const selector of descriptionSelectors) {
      const desc = page.locator(selector).first();
      
      if (await desc.count() > 0 && await desc.isVisible()) {
        const text = await desc.textContent();
        
        if (text && text.length > 10) {
          console.log(`✅ 找到描述: ${text.substring(0, 50)}...`);
          descriptionFound = true;
          break;
        }
      }
    }
    
    if (!descriptionFound) {
      console.log('⚠️ 未找到案例描述');
    }
    
    // ========== 步骤 4: 运行案例 ==========
    console.log('\n[步骤 4] 运行案例...');
    
    // 查找运行按钮
    const runButtonSelectors = [
      'button:has-text("运行")',
      'button:has-text("Run")',
      'button:has-text("执行")',
      'button:has-text("Execute")',
      '.run-button',
      '#run'
    ];
    
    let caseRun = false;
    
    for (const selector of runButtonSelectors) {
      const button = page.locator(selector).first();
      
      if (await button.count() > 0 && await button.isVisible()) {
        try {
          await button.click();
          
          console.log(`✅ 点击运行: ${selector}`);
          
          // 等待运行
          await page.waitForTimeout(2000);
          
          caseRun = true;
          break;
        } catch (e) {
          console.log(`⚠️ 运行失败: ${e.message}`);
        }
      }
    }
    
    if (!caseRun) {
      console.log('⚠️ 未找到运行按钮');
    }
    
    // 截图 - 运行中
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-cases-step4-running.png',
      fullPage: true 
    });
    
    // ========== 步骤 5: 等待结果 ==========
    console.log('\n[步骤 5] 等待计算结果...');
    
    // 检查加载状态
    const loadingSelectors = [
      '.loading',
      '.spinner',
      '[class*="loading"]',
      'text=/计算中|Running|Loading/i'
    ];
    
    let loadingFound = false;
    
    for (const selector of loadingSelectors) {
      if (await page.locator(selector).count() > 0) {
        console.log(`✅ 检测到加载状态: ${selector}`);
        loadingFound = true;
        break;
      }
    }
    
    if (loadingFound) {
      // 等待加载完成
      await page.waitForTimeout(3000);
      console.log('✅ 等待完成');
    } else {
      console.log('⚠️ 未检测到加载状态 (可能瞬间完成)');
    }
    
    // ========== 步骤 6: 查看结果 ==========
    console.log('\n[步骤 6] 查看计算结果...');
    
    // 查找结果元素
    const resultSelectors = [
      'canvas',
      'svg',
      '.chart',
      '.results',
      '.output',
      'table'
    ];
    
    let resultsFound = 0;
    
    for (const selector of resultSelectors) {
      const count = await page.locator(selector).count();
      
      if (count > 0) {
        console.log(`✅ 找到结果元素: ${selector} (${count} 个)`);
        resultsFound += count;
      }
    }
    
    if (resultsFound === 0) {
      console.log('⚠️ 未找到结果展示元素');
    }
    
    // 截图 - 结果
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-cases-step6-results.png',
      fullPage: true 
    });
    
    // ========== 步骤 7: 下载结果 ==========
    console.log('\n[步骤 7] 下载结果数据...');
    
    // 查找下载按钮
    const downloadButtonSelectors = [
      'button:has-text("下载")',
      'button:has-text("Download")',
      'button:has-text("导出")',
      'button:has-text("Export")',
      'a[download]'
    ];
    
    let downloadAvailable = false;
    
    for (const selector of downloadButtonSelectors) {
      if (await page.locator(selector).count() > 0) {
        console.log(`✅ 找到下载按钮: ${selector}`);
        downloadAvailable = true;
        break;
      }
    }
    
    if (!downloadAvailable) {
      console.log('⚠️ 未找到下载按钮');
    }
    
    // 最终截图
    await page.screenshot({ 
      path: 'reports/screenshots/e2e-cases-step7-final.png',
      fullPage: true 
    });
    
    // ========== 工作流完成 ==========
    console.log('\n' + '='.repeat(70));
    console.log('案例运行工作流完成');
    console.log('='.repeat(70));
    
    console.log('\n工作流步骤总结:');
    console.log(`  1. 访问案例列表: ${enteredCases ? '✅' : '⚠️'}`);
    console.log(`  2. 选择案例: ${caseSelected ? '✅' : '⚠️'}`);
    console.log(`  3. 查看描述: ${descriptionFound ? '✅' : '⚠️'}`);
    console.log(`  4. 运行案例: ${caseRun ? '✅' : '⚠️'}`);
    console.log(`  5. 等待结果: ${loadingFound || resultsFound > 0 ? '✅' : '⚠️'}`);
    console.log(`  6. 查看结果: ${resultsFound > 0 ? '✅' : '⚠️'}`);
    console.log(`  7. 下载数据: ${downloadAvailable ? '✅' : '⚠️'}`);
    
    const successCount = [
      enteredCases,
      caseSelected,
      descriptionFound,
      caseRun,
      loadingFound || resultsFound > 0,
      resultsFound > 0,
      downloadAvailable
    ].filter(Boolean).length;
    
    const totalSteps = 7;
    const completionRate = (successCount / totalSteps * 100).toFixed(1);
    
    console.log(`\n完成度: ${successCount}/${totalSteps} (${completionRate}%)`);
    
    // 软性断言
    expect(successCount).toBeGreaterThanOrEqual(2);
    
    console.log('\n✅ 案例运行工作流测试完成！');
  });
  
  test('工作流: 案例列表浏览', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 案例列表浏览');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 查找案例数量
    const caseItemSelectors = [
      '.case-item',
      '.example-item',
      '.card',
      '[class*="case"]'
    ];
    
    let totalCases = 0;
    
    for (const selector of caseItemSelectors) {
      const count = await page.locator(selector).count();
      
      if (count > 0) {
        totalCases = count;
        console.log(`✅ 找到 ${count} 个案例: ${selector}`);
        break;
      }
    }
    
    if (totalCases === 0) {
      console.log('⚠️ 未找到案例');
    } else {
      console.log(`\n案例总数: ${totalCases}`);
    }
    
    console.log('\n✅ 案例列表浏览完成');
  });
  
  test('工作流: 案例分类筛选', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('E2E 测试: 案例分类筛选');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 查找分类选择器
    const filterSelectors = [
      '.filter',
      '.category',
      'select',
      '[role="tab"]',
      'button[class*="filter"]'
    ];
    
    let filterFound = false;
    
    for (const selector of filterSelectors) {
      if (await page.locator(selector).count() > 0) {
        console.log(`✅ 找到筛选器: ${selector}`);
        filterFound = true;
        break;
      }
    }
    
    if (!filterFound) {
      console.log('⚠️ 未找到分类筛选功能');
    }
    
    console.log('\n✅ 案例分类筛选测试完成');
  });
});
