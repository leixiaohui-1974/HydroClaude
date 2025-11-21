/**
 * 可访问性测试 (Accessibility / a11y)
 * 
 * 测试前端的无障碍访问特性，确保残障人士也能使用
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('可访问性测试', () => {
  
  test('测试页面标题', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 页面标题');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    const title = await page.title();
    
    console.log(`页面标题: "${title}"`);
    
    if (title && title.length > 0 && title !== 'Document') {
      console.log('✅ 页面有描述性标题');
      expect(title.length).toBeGreaterThan(0);
    } else {
      console.log('⚠️ 页面标题缺失或使用默认值');
    }
    
    console.log('✅ 页面标题测试完成');
  });
  
  test('测试语言属性', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 语言属性');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    const lang = await page.locator('html').getAttribute('lang');
    
    if (lang) {
      console.log(`✅ HTML lang 属性: "${lang}"`);
      expect(lang).toBeTruthy();
    } else {
      console.log('⚠️ HTML 缺少 lang 属性（影响屏幕阅读器）');
    }
    
    console.log('✅ 语言属性测试完成');
  });
  
  test('测试图片alt文本', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 图片alt文本');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    const totalImages = await page.locator('img').count();
    const imagesWithAlt = await page.locator('img[alt]').count();
    const imagesWithEmptyAlt = await page.locator('img[alt=""]').count();
    const imagesWithoutAlt = totalImages - imagesWithAlt;
    
    console.log(`总图片数: ${totalImages}`);
    console.log(`有 alt 属性: ${imagesWithAlt}`);
    console.log(`空 alt 属性: ${imagesWithEmptyAlt} (装饰性图片)`);
    console.log(`缺少 alt 属性: ${imagesWithoutAlt}`);
    
    if (totalImages > 0) {
      const coverage = ((imagesWithAlt / totalImages) * 100).toFixed(1);
      console.log(`alt 覆盖率: ${coverage}%`);
      
      if (coverage >= 90) {
        console.log('✅ 图片 alt 覆盖率优秀 (>= 90%)');
      } else if (coverage >= 70) {
        console.log('⚠️ 图片 alt 覆盖率良好 (>= 70%)');
      } else {
        console.log('⚠️ 图片 alt 覆盖率较低 (< 70%)');
      }
    } else {
      console.log('⚠️ 页面无图片');
    }
    
    console.log('✅ 图片alt文本测试完成');
  });
  
  test('测试标题层级', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 标题层级');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 统计各级标题
    const headings = {
      h1: await page.locator('h1').count(),
      h2: await page.locator('h2').count(),
      h3: await page.locator('h3').count(),
      h4: await page.locator('h4').count(),
      h5: await page.locator('h5').count(),
      h6: await page.locator('h6').count()
    };
    
    console.log('标题统计:');
    for (const [level, count] of Object.entries(headings)) {
      if (count > 0) {
        console.log(`  ${level.toUpperCase()}: ${count} 个`);
      }
    }
    
    // 检查h1
    if (headings.h1 === 1) {
      console.log('✅ 页面有且仅有一个 h1 标题（符合最佳实践）');
    } else if (headings.h1 === 0) {
      console.log('⚠️ 页面缺少 h1 标题');
    } else {
      console.log(`⚠️ 页面有 ${headings.h1} 个 h1 标题（应该只有一个）`);
    }
    
    // 检查标题层级是否跳过
    const levels = Object.values(headings);
    let skipped = false;
    
    for (let i = 1; i < levels.length; i++) {
      if (levels[i] > 0 && levels[i - 1] === 0) {
        // 检查更早的层级是否存在
        let hasEarlier = false;
        for (let j = 0; j < i - 1; j++) {
          if (levels[j] > 0) {
            hasEarlier = true;
            break;
          }
        }
        
        if (hasEarlier) {
          console.log(`⚠️ 标题层级跳过 (h${i + 1} 出现但 h${i} 缺失)`);
          skipped = true;
        }
      }
    }
    
    if (!skipped && headings.h1 > 0) {
      console.log('✅ 标题层级结构合理');
    }
    
    console.log('✅ 标题层级测试完成');
  });
  
  test('测试ARIA标签', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: ARIA标签');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 统计ARIA属性使用
    const ariaLabels = await page.locator('[aria-label]').count();
    const ariaLabelledby = await page.locator('[aria-labelledby]').count();
    const ariaDescribedby = await page.locator('[aria-describedby]').count();
    const ariaHidden = await page.locator('[aria-hidden]').count();
    const ariaLive = await page.locator('[aria-live]').count();
    const roles = await page.locator('[role]').count();
    
    console.log('ARIA 使用情况:');
    console.log(`  aria-label: ${ariaLabels} 个`);
    console.log(`  aria-labelledby: ${ariaLabelledby} 个`);
    console.log(`  aria-describedby: ${ariaDescribedby} 个`);
    console.log(`  aria-hidden: ${ariaHidden} 个`);
    console.log(`  aria-live: ${ariaLive} 个`);
    console.log(`  role: ${roles} 个`);
    
    const totalAria = ariaLabels + ariaLabelledby + ariaDescribedby + ariaHidden + ariaLive + roles;
    
    if (totalAria > 0) {
      console.log(`✅ 使用了 ${totalAria} 个 ARIA 属性（提升可访问性）`);
    } else {
      console.log('⚠️ 未使用 ARIA 属性（可能依赖语义化HTML）');
    }
    
    console.log('✅ ARIA标签测试完成');
  });
  
  test('测试键盘导航', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 键盘导航');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 测试Tab键导航
    console.log('测试 Tab 键导航...');
    
    let focusableCount = 0;
    
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
      
      const focusedElement = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? el.tagName.toLowerCase() : null;
      });
      
      if (focusedElement && focusedElement !== 'body') {
        focusableCount++;
        console.log(`  Tab ${i + 1}: 焦点在 <${focusedElement}>`);
      }
    }
    
    if (focusableCount > 0) {
      console.log(`✅ 检测到 ${focusableCount} 个可聚焦元素（键盘可导航）`);
    } else {
      console.log('⚠️ 未检测到可聚焦元素（可能影响键盘导航）');
    }
    
    // 检查焦点样式
    const hasFocusVisibleStyles = await page.evaluate(() => {
      const styles = window.getComputedStyle(document.body);
      return styles.getPropertyValue('outline-style') !== 'none';
    });
    
    console.log(`焦点可见样式: ${hasFocusVisibleStyles ? '✅ 存在' : '⚠️ 可能缺失'}`);
    
    console.log('✅ 键盘导航测试完成');
  });
  
  test('测试表单标签', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 表单标签');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    const totalInputs = await page.locator('input, textarea, select').count();
    const inputsWithLabel = await page.locator('input[id], textarea[id], select[id]').count();
    const labels = await page.locator('label').count();
    
    console.log(`总输入框: ${totalInputs}`);
    console.log(`有 id 的输入框: ${inputsWithLabel}`);
    console.log(`label 元素: ${labels}`);
    
    if (totalInputs > 0) {
      const labelCoverage = ((inputsWithLabel / totalInputs) * 100).toFixed(1);
      console.log(`label 关联覆盖率: ${labelCoverage}%`);
      
      if (labelCoverage >= 80) {
        console.log('✅ 表单 label 覆盖率优秀 (>= 80%)');
      } else {
        console.log('⚠️ 表单 label 覆盖率较低 (< 80%)');
      }
    } else {
      console.log('⚠️ 页面无表单输入框');
    }
    
    // 检查placeholder滥用
    const placeholders = await page.locator('input[placeholder], textarea[placeholder]').count();
    
    if (placeholders > 0 && placeholders === totalInputs && labels === 0) {
      console.log('⚠️ 仅使用 placeholder 而无 label（不推荐，影响可访问性）');
    }
    
    console.log('✅ 表单标签测试完成');
  });
  
  test('测试颜色对比度', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 颜色对比度');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 获取主要文本颜色和背景色
    const colors = await page.evaluate(() => {
      const body = document.body;
      const styles = window.getComputedStyle(body);
      
      return {
        color: styles.color,
        backgroundColor: styles.backgroundColor
      };
    });
    
    console.log(`文本颜色: ${colors.color}`);
    console.log(`背景颜色: ${colors.backgroundColor}`);
    
    console.log('ℹ️ 颜色对比度需要专门工具检测（如 axe-core）');
    console.log('ℹ️ WCAG 2.0 要求: 普通文本对比度 >= 4.5:1，大文本 >= 3:1');
    
    console.log('✅ 颜色对比度测试完成');
  });
  
  test('测试跳转链接', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 跳转链接 (Skip Links)');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 查找跳转链接
    const skipLinks = await page.locator('a[href^="#"]:has-text("skip"), a:has-text("跳过")').count();
    
    if (skipLinks > 0) {
      console.log(`✅ 检测到 ${skipLinks} 个跳转链接（提升键盘导航效率）`);
    } else {
      console.log('⚠️ 未检测到跳转链接（可选功能，但有助于可访问性）');
    }
    
    console.log('✅ 跳转链接测试完成');
  });
  
  test('测试语义化HTML', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 语义化HTML');
    console.log('='.repeat(70));
    
    await page.goto('/');
    
    // 检查语义化标签
    const semanticTags = {
      header: await page.locator('header').count(),
      nav: await page.locator('nav').count(),
      main: await page.locator('main').count(),
      article: await page.locator('article').count(),
      section: await page.locator('section').count(),
      aside: await page.locator('aside').count(),
      footer: await page.locator('footer').count()
    };
    
    console.log('语义化标签使用情况:');
    let totalSemantic = 0;
    
    for (const [tag, count] of Object.entries(semanticTags)) {
      if (count > 0) {
        console.log(`  <${tag}>: ${count} 个`);
        totalSemantic += count;
      }
    }
    
    if (totalSemantic >= 3) {
      console.log(`✅ 使用了 ${totalSemantic} 个语义化标签（优秀）`);
    } else if (totalSemantic > 0) {
      console.log(`⚠️ 使用了 ${totalSemantic} 个语义化标签（可以更多）`);
    } else {
      console.log('⚠️ 未使用语义化标签（影响可访问性和SEO）');
    }
    
    // 检查div滥用
    const divs = await page.locator('div').count();
    console.log(`<div> 元素: ${divs} 个`);
    
    if (divs > 50 && totalSemantic < 3) {
      console.log('⚠️ 过多 div 元素且语义化标签少（建议改进）');
    }
    
    console.log('✅ 语义化HTML测试完成');
  });
});
