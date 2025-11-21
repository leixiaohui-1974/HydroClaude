/**
 * 前端性能测试
 * 
 * 测试前端页面加载速度、渲染性能和交互响应时间
 * 按照 Spec-Kit 规范编写
 * 
 * Author: HydroClaude Test Team
 * Date: 2025-11-20
 * Spec: 001-comprehensive-review-and-testing
 */

const { test, expect } = require('@playwright/test');

test.describe('前端性能测试', () => {
  
  test('首页加载性能', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 首页加载性能');
    console.log('='.repeat(70));
    
    const startTime = Date.now();
    
    await page.goto('/');
    
    const loadTime = Date.now() - startTime;
    
    console.log(`页面加载时间: ${loadTime}ms`);
    
    // 获取 Performance API 数据
    const performanceData = await page.evaluate(() => {
      const perf = window.performance;
      const timing = perf.timing;
      
      return {
        dns: timing.domainLookupEnd - timing.domainLookupStart,
        tcp: timing.connectEnd - timing.connectStart,
        ttfb: timing.responseStart - timing.requestStart,
        download: timing.responseEnd - timing.responseStart,
        domParse: timing.domInteractive - timing.responseEnd,
        domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
        fullLoad: timing.loadEventEnd - timing.navigationStart
      };
    });
    
    console.log('性能指标:');
    console.log(`  DNS 查询: ${performanceData.dns}ms`);
    console.log(`  TCP 连接: ${performanceData.tcp}ms`);
    console.log(`  TTFB (首字节时间): ${performanceData.ttfb}ms`);
    console.log(`  资源下载: ${performanceData.download}ms`);
    console.log(`  DOM 解析: ${performanceData.domParse}ms`);
    console.log(`  DOM Ready: ${performanceData.domReady}ms`);
    console.log(`  完全加载: ${performanceData.fullLoad}ms`);
    
    // 性能断言
    expect(performanceData.ttfb).toBeLessThan(1000); // TTFB < 1s
    expect(performanceData.domReady).toBeLessThan(3000); // DOM Ready < 3s
    expect(performanceData.fullLoad).toBeLessThan(5000); // 完全加载 < 5s
    
    if (performanceData.fullLoad < 2000) {
      console.log('✅ 加载性能优秀 (< 2s)');
    } else if (performanceData.fullLoad < 3000) {
      console.log('✅ 加载性能良好 (< 3s)');
    } else {
      console.log('⚠️ 加载性能一般 (> 3s)');
    }
    
    console.log('✅ 首页加载性能测试完成');
  });
  
  test('Core Web Vitals 测试', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: Core Web Vitals (核心Web指标)');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 获取 Core Web Vitals
    const vitals = await page.evaluate(() => {
      return new Promise((resolve) => {
        const vitals = {
          lcp: null, // Largest Contentful Paint
          fid: null, // First Input Delay
          cls: null  // Cumulative Layout Shift
        };
        
        // LCP
        if ('PerformanceObserver' in window) {
          try {
            new PerformanceObserver((entryList) => {
              const entries = entryList.getEntries();
              const lastEntry = entries[entries.length - 1];
              vitals.lcp = lastEntry.renderTime || lastEntry.loadTime;
            }).observe({ type: 'largest-contentful-paint', buffered: true });
          } catch (e) {}
          
          // CLS
          try {
            let clsValue = 0;
            new PerformanceObserver((entryList) => {
              for (const entry of entryList.getEntries()) {
                if (!entry.hadRecentInput) {
                  clsValue += entry.value;
                }
              }
              vitals.cls = clsValue;
            }).observe({ type: 'layout-shift', buffered: true });
          } catch (e) {}
        }
        
        // 等待一段时间收集数据
        setTimeout(() => resolve(vitals), 2000);
      });
    });
    
    console.log('Core Web Vitals:');
    
    if (vitals.lcp) {
      console.log(`  LCP (最大内容绘制): ${vitals.lcp.toFixed(0)}ms`);
      
      if (vitals.lcp < 2500) {
        console.log('    ✅ 优秀 (< 2.5s)');
      } else if (vitals.lcp < 4000) {
        console.log('    ⚠️ 需要改进 (2.5s - 4s)');
      } else {
        console.log('    ❌ 差 (> 4s)');
      }
    } else {
      console.log('  LCP: ⚠️ 未测量到');
    }
    
    if (vitals.cls !== null) {
      console.log(`  CLS (累积布局偏移): ${vitals.cls.toFixed(4)}`);
      
      if (vitals.cls < 0.1) {
        console.log('    ✅ 优秀 (< 0.1)');
      } else if (vitals.cls < 0.25) {
        console.log('    ⚠️ 需要改进 (0.1 - 0.25)');
      } else {
        console.log('    ❌ 差 (> 0.25)');
      }
    } else {
      console.log('  CLS: ⚠️ 未测量到');
    }
    
    console.log('  FID (首次输入延迟): ℹ️ 需要用户交互才能测量');
    
    console.log('✅ Core Web Vitals 测试完成');
  });
  
  test('资源加载性能', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 资源加载性能');
    console.log('='.repeat(70));
    
    // 监听网络请求
    const resources = {
      js: [],
      css: [],
      images: [],
      fonts: [],
      others: []
    };
    
    page.on('response', response => {
      const url = response.url();
      const type = response.request().resourceType();
      const size = response.headers()['content-length'];
      const timing = response.timing();
      
      const resource = {
        url: url.split('/').pop(),
        size: size ? parseInt(size) : 0,
        time: timing ? timing.responseEnd : 0
      };
      
      if (type === 'script') resources.js.push(resource);
      else if (type === 'stylesheet') resources.css.push(resource);
      else if (type === 'image') resources.images.push(resource);
      else if (type === 'font') resources.fonts.push(resource);
      else resources.others.push(resource);
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    console.log('资源统计:');
    console.log(`  JavaScript: ${resources.js.length} 个`);
    console.log(`  CSS: ${resources.css.length} 个`);
    console.log(`  图片: ${resources.images.length} 个`);
    console.log(`  字体: ${resources.fonts.length} 个`);
    console.log(`  其他: ${resources.others.length} 个`);
    
    // 分析最慢的资源
    const allResources = [
      ...resources.js,
      ...resources.css,
      ...resources.images,
      ...resources.fonts,
      ...resources.others
    ];
    
    const slowestResources = allResources
      .filter(r => r.time > 0)
      .sort((a, b) => b.time - a.time)
      .slice(0, 5);
    
    if (slowestResources.length > 0) {
      console.log('\n最慢的5个资源:');
      
      slowestResources.forEach((r, i) => {
        console.log(`  ${i + 1}. ${r.url} - ${r.time.toFixed(0)}ms`);
      });
    }
    
    console.log('✅ 资源加载性能测试完成');
  });
  
  test('JavaScript 执行性能', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: JavaScript 执行性能');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 测试 JavaScript 执行时间
    const jsPerformance = await page.evaluate(() => {
      const perf = window.performance;
      
      // 获取所有 script 相关的性能条目
      const scripts = perf.getEntriesByType('resource')
        .filter(entry => entry.initiatorType === 'script');
      
      const totalScriptTime = scripts.reduce((sum, entry) => {
        return sum + entry.duration;
      }, 0);
      
      return {
        scriptCount: scripts.length,
        totalTime: totalScriptTime,
        avgTime: scripts.length > 0 ? totalScriptTime / scripts.length : 0
      };
    });
    
    console.log(`JavaScript 脚本数: ${jsPerformance.scriptCount}`);
    console.log(`总执行时间: ${jsPerformance.totalTime.toFixed(0)}ms`);
    console.log(`平均执行时间: ${jsPerformance.avgTime.toFixed(0)}ms`);
    
    if (jsPerformance.totalTime < 1000) {
      console.log('✅ JavaScript 执行性能优秀 (< 1s)');
    } else if (jsPerformance.totalTime < 2000) {
      console.log('✅ JavaScript 执行性能良好 (< 2s)');
    } else {
      console.log('⚠️ JavaScript 执行时间较长 (> 2s)');
    }
    
    console.log('✅ JavaScript 执行性能测试完成');
  });
  
  test('渲染性能 (FPS)', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 渲染性能 (FPS)');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 测试滚动时的 FPS
    const fps = await page.evaluate(() => {
      return new Promise((resolve) => {
        const frames = [];
        let lastTime = performance.now();
        
        const measureFPS = () => {
          const currentTime = performance.now();
          const delta = currentTime - lastTime;
          
          if (delta > 0) {
            frames.push(1000 / delta);
          }
          
          lastTime = currentTime;
          
          if (frames.length < 60) {
            requestAnimationFrame(measureFPS);
          } else {
            const avgFPS = frames.reduce((a, b) => a + b, 0) / frames.length;
            resolve(avgFPS);
          }
        };
        
        requestAnimationFrame(measureFPS);
      });
    });
    
    console.log(`平均 FPS: ${fps.toFixed(1)}`);
    
    if (fps >= 55) {
      console.log('✅ 渲染性能优秀 (>= 55 FPS)');
    } else if (fps >= 30) {
      console.log('✅ 渲染性能可接受 (>= 30 FPS)');
    } else {
      console.log('⚠️ 渲染性能较差 (< 30 FPS)');
    }
    
    console.log('✅ 渲染性能测试完成');
  });
  
  test('内存使用情况', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 内存使用情况');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 获取内存信息
    const memory = await page.evaluate(() => {
      if (performance.memory) {
        return {
          used: performance.memory.usedJSHeapSize,
          total: performance.memory.totalJSHeapSize,
          limit: performance.memory.jsHeapSizeLimit
        };
      }
      
      return null;
    });
    
    if (memory) {
      const usedMB = (memory.used / 1024 / 1024).toFixed(2);
      const totalMB = (memory.total / 1024 / 1024).toFixed(2);
      const limitMB = (memory.limit / 1024 / 1024).toFixed(2);
      
      console.log(`使用内存: ${usedMB} MB`);
      console.log(`总分配内存: ${totalMB} MB`);
      console.log(`内存限制: ${limitMB} MB`);
      
      const usagePercent = (memory.used / memory.limit * 100).toFixed(1);
      console.log(`内存使用率: ${usagePercent}%`);
      
      if (usagePercent < 30) {
        console.log('✅ 内存使用率优秀 (< 30%)');
      } else if (usagePercent < 60) {
        console.log('✅ 内存使用率良好 (< 60%)');
      } else {
        console.log('⚠️ 内存使用率较高 (> 60%)');
      }
    } else {
      console.log('⚠️ 浏览器不支持 performance.memory API');
    }
    
    console.log('✅ 内存使用测试完成');
  });
  
  test('缓存性能', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 缓存性能');
    console.log('='.repeat(70));
    
    // 首次加载
    console.log('首次加载...');
    const firstLoadStart = Date.now();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const firstLoadTime = Date.now() - firstLoadStart;
    
    console.log(`首次加载时间: ${firstLoadTime}ms`);
    
    // 重新加载（测试缓存）
    console.log('重新加载（测试缓存）...');
    const reloadStart = Date.now();
    await page.reload();
    await page.waitForLoadState('networkidle');
    const reloadTime = Date.now() - reloadStart;
    
    console.log(`重新加载时间: ${reloadTime}ms`);
    
    // 计算改进百分比
    const improvement = ((firstLoadTime - reloadTime) / firstLoadTime * 100).toFixed(1);
    
    console.log(`缓存提升: ${improvement}%`);
    
    if (improvement > 50) {
      console.log('✅ 缓存策略优秀 (提升 > 50%)');
    } else if (improvement > 20) {
      console.log('✅ 缓存策略良好 (提升 > 20%)');
    } else {
      console.log('⚠️ 缓存策略需要改进 (提升 < 20%)');
    }
    
    console.log('✅ 缓存性能测试完成');
  });
  
  test('交互响应时间', async ({ page }) => {
    console.log('\n' + '='.repeat(70));
    console.log('测试: 交互响应时间');
    console.log('='.repeat(70));
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 测试按钮点击响应
    const button = page.locator('button').first();
    
    if (await button.count() > 0 && await button.isVisible()) {
      const clickStart = Date.now();
      await button.click();
      await page.waitForTimeout(100);
      const clickTime = Date.now() - clickStart;
      
      console.log(`按钮点击响应时间: ${clickTime}ms`);
      
      if (clickTime < 100) {
        console.log('✅ 交互响应优秀 (< 100ms)');
      } else if (clickTime < 300) {
        console.log('✅ 交互响应良好 (< 300ms)');
      } else {
        console.log('⚠️ 交互响应较慢 (> 300ms)');
      }
    } else {
      console.log('⚠️ 未找到可交互按钮');
    }
    
    console.log('✅ 交互响应时间测试完成');
  });
});
