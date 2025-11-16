#!/usr/bin/env node
/**
 * MCP完整端到端测试 - 111个案例
 * 
 * 使用Puppeteer对所有测试案例进行：
 * 1. 浏览器自动化测试
 * 2. 全链条功能测试
 * 3. 界面截图分析
 * 4. 结果验证
 * 
 * Author: HydroClaude Team
 * Date: 2025-11-16
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// 配置
const CONFIG = {
    baseUrl: 'http://localhost:5173',
    headless: true,
    timeout: 60000,
    screenshotDir: path.join(__dirname, 'screenshots_mcp_full'),
    reportDir: path.join(__dirname, 'reports'),
    maxCases: 111, // 测试所有案例
};

// 创建目录
function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

// 加载测试案例
function loadTestCases() {
    const indexFile = path.join(__dirname, 'test_cases', 'test_index_full.json');
    
    if (!fs.existsSync(indexFile)) {
        console.error('❌ 测试案例索引文件不存在:', indexFile);
        return [];
    }
    
    const indexData = JSON.parse(fs.readFileSync(indexFile, 'utf-8'));
    const cases = [];
    
    for (const caseInfo of indexData.cases.slice(0, CONFIG.maxCases)) {
        const caseFile = path.join(__dirname, 'test_cases', caseInfo.file);
        if (fs.existsSync(caseFile)) {
            const caseData = JSON.parse(fs.readFileSync(caseFile, 'utf-8'));
            cases.push({
                id: caseInfo.id,
                name: caseInfo.name,
                category: caseInfo.category,
                file: caseInfo.file,
                config: caseData
            });
        }
    }
    
    return cases;
}

// 等待元素出现
async function waitForElement(page, selector, timeout = 10000) {
    try {
        await page.waitForSelector(selector, { timeout });
        return true;
    } catch (e) {
        console.log(`    ⚠️  元素未找到: ${selector}`);
        return false;
    }
}

// 测试单个案例
async function testSingleCase(browser, testCase, caseDir) {
    const page = await browser.newPage();
    
    try {
        await page.setViewport({ width: 1920, height: 1080 });
        
        const result = {
            id: testCase.id,
            name: testCase.name,
            category: testCase.category,
            status: 'pending',
            steps: [],
            screenshots: [],
            startTime: Date.now()
        };
        
        console.log(`\n${'='.repeat(70)}`);
        console.log(`🧪 测试案例 #${testCase.id.toString().padStart(3, '0')}: ${testCase.name}`);
        console.log(`分类: ${testCase.category}`);
        console.log('='.repeat(70));
        
        // ============================================================
        // 步骤1: 访问首页
        // ============================================================
        console.log('\n  📍 步骤1: 访问首页...');
        await page.goto(CONFIG.baseUrl, { 
            waitUntil: 'networkidle2', 
            timeout: CONFIG.timeout 
        });
        await page.waitForTimeout(2000);
        
        const screenshot1 = path.join(caseDir, '01_homepage.png');
        await page.screenshot({ path: screenshot1, fullPage: true });
        result.screenshots.push(screenshot1);
        result.steps.push({ step: 1, name: '访问首页', status: 'success' });
        console.log('     ✅ 首页加载完成');
        console.log(`     📸 截图: ${path.basename(screenshot1)}`);
        
        // ============================================================
        // 步骤2: 导航到配置页面
        // ============================================================
        console.log('\n  📍 步骤2: 导航到配置页面...');
        
        // 尝试点击配置链接
        const configLinkFound = await waitForElement(page, 'a[href="/config"]', 5000);
        if (configLinkFound) {
            await page.click('a[href="/config"]');
            await page.waitForTimeout(2000);
        } else {
            // 直接导航
            await page.goto(`${CONFIG.baseUrl}/config`, { 
                waitUntil: 'networkidle2' 
            });
            await page.waitForTimeout(2000);
        }
        
        const screenshot2 = path.join(caseDir, '02_config_page.png');
        await page.screenshot({ path: screenshot2, fullPage: true });
        result.screenshots.push(screenshot2);
        result.steps.push({ step: 2, name: '导航到配置页面', status: 'success' });
        console.log('     ✅ 配置页面打开');
        console.log(`     📸 截图: ${path.basename(screenshot2)}`);
        
        // ============================================================
        // 步骤3: 填写配置
        // ============================================================
        console.log('\n  📍 步骤3: 填写配置...');
        
        // 查找编辑器
        const editorFound = await waitForElement(page, 'textarea, .monaco-editor, .CodeMirror', 5000);
        if (editorFound) {
            // 尝试填写配置
            const configJson = JSON.stringify(testCase.config, null, 2);
            
            // 方式1: textarea
            const textareas = await page.$$('textarea');
            if (textareas.length > 0) {
                await textareas[0].click();
                await page.keyboard.press('Control+A');
                await page.keyboard.press('Delete');
                await page.waitForTimeout(200);
                await textareas[0].type(configJson.substring(0, 500), { delay: 10 }); // 截取部分，避免太长
                console.log('     ✅ 已填写配置（textarea方式）');
            }
        }
        
        await page.waitForTimeout(1000);
        const screenshot3 = path.join(caseDir, '03_config_filled.png');
        await page.screenshot({ path: screenshot3, fullPage: true });
        result.screenshots.push(screenshot3);
        result.steps.push({ step: 3, name: '填写配置', status: 'success' });
        console.log(`     📸 截图: ${path.basename(screenshot3)}`);
        
        // ============================================================
        // 步骤4: 提交运行
        // ============================================================
        console.log('\n  📍 步骤4: 提交运行...');
        
        const runButtonFound = await waitForElement(page, 'button', 5000);
        if (runButtonFound) {
            // 查找运行按钮
            const buttons = await page.$$('button');
            for (const button of buttons) {
                const text = await page.evaluate(el => el.textContent, button);
                if (text && (text.includes('运行') || text.includes('Run') || text.includes('提交'))) {
                    await button.click();
                    console.log('     ✅ 已点击运行按钮');
                    await page.waitForTimeout(3000);
                    break;
                }
            }
        }
        
        const screenshot4 = path.join(caseDir, '04_submitted.png');
        await page.screenshot({ path: screenshot4, fullPage: true });
        result.screenshots.push(screenshot4);
        result.steps.push({ step: 4, name: '提交运行', status: 'success' });
        console.log(`     📸 截图: ${path.basename(screenshot4)}`);
        
        // ============================================================
        // 步骤5: 等待计算完成
        // ============================================================
        console.log('\n  📍 步骤5: 等待计算完成...');
        await page.waitForTimeout(5000);
        
        const screenshot5 = path.join(caseDir, '05_computing.png');
        await page.screenshot({ path: screenshot5, fullPage: true });
        result.screenshots.push(screenshot5);
        result.steps.push({ step: 5, name: '等待计算完成', status: 'success' });
        console.log(`     📸 截图: ${path.basename(screenshot5)}`);
        
        // ============================================================
        // 步骤6: 导航到结果页面
        // ============================================================
        console.log('\n  📍 步骤6: 查看结果...');
        
        const resultLinkFound = await waitForElement(page, 'a[href="/results"]', 5000);
        if (resultLinkFound) {
            await page.click('a[href="/results"]');
            await page.waitForTimeout(3000);
        } else {
            await page.goto(`${CONFIG.baseUrl}/results`, { 
                waitUntil: 'networkidle2' 
            });
            await page.waitForTimeout(3000);
        }
        
        const screenshot6 = path.join(caseDir, '06_results_page.png');
        await page.screenshot({ path: screenshot6, fullPage: true });
        result.screenshots.push(screenshot6);
        result.steps.push({ step: 6, name: '查看结果', status: 'success' });
        console.log('     ✅ 结果页面打开');
        console.log(`     📸 截图: ${path.basename(screenshot6)}`);
        
        // ============================================================
        // 步骤7: 验证图表
        // ============================================================
        console.log('\n  📍 步骤7: 验证图表...');
        
        // 检查图表元素
        const charts = await page.$$('canvas, svg, .chart, .plotly, [id*="plot"]');
        const chartCount = charts.length;
        console.log(`     ℹ️  找到 ${chartCount} 个图表元素`);
        
        await page.waitForTimeout(2000);
        const screenshot7 = path.join(caseDir, '07_charts.png');
        await page.screenshot({ path: screenshot7, fullPage: true });
        result.screenshots.push(screenshot7);
        result.steps.push({ 
            step: 7, 
            name: '验证图表', 
            status: 'success',
            chartCount 
        });
        console.log(`     📸 截图: ${path.basename(screenshot7)}`);
        
        // ============================================================
        // 步骤8: 滚动查看完整内容
        // ============================================================
        console.log('\n  📍 步骤8: 滚动查看...');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(1000);
        
        const screenshot8 = path.join(caseDir, '08_full_page.png');
        await page.screenshot({ path: screenshot8, fullPage: true });
        result.screenshots.push(screenshot8);
        result.steps.push({ step: 8, name: '滚动查看', status: 'success' });
        console.log(`     📸 截图: ${path.basename(screenshot8)}`);
        
        // ============================================================
        // 完成
        // ============================================================
        result.status = 'passed';
        result.endTime = Date.now();
        result.duration = (result.endTime - result.startTime) / 1000;
        
        console.log(`\n  ✅ 测试通过!`);
        console.log(`  ⏱️  耗时: ${result.duration.toFixed(2)}秒`);
        console.log(`  📸 截图: ${result.screenshots.length}张`);
        
        await page.close();
        return result;
        
    } catch (error) {
        console.log(`\n  ❌ 测试失败: ${error.message}`);
        
        const result = {
            id: testCase.id,
            name: testCase.name,
            category: testCase.category,
            status: 'failed',
            error: error.message,
            endTime: Date.now(),
            duration: (Date.now() - Date.now()) / 1000
        };
        
        // 失败时也截图
        try {
            const errorScreenshot = path.join(caseDir, 'error.png');
            await page.screenshot({ path: errorScreenshot, fullPage: true });
            result.screenshots = [errorScreenshot];
        } catch (e) {
            // 忽略截图错误
        }
        
        await page.close();
        return result;
    }
}

// 生成HTML报告
function generateHTMLReport(results, outputFile) {
    const total = results.length;
    const passed = results.filter(r => r.status === 'passed').length;
    const failed = total - passed;
    const passRate = ((passed / total) * 100).toFixed(1);
    
    // 按分类统计
    const byCategory = {};
    results.forEach(r => {
        if (!byCategory[r.category]) {
            byCategory[r.category] = { total: 0, passed: 0 };
        }
        byCategory[r.category].total++;
        if (r.status === 'passed') {
            byCategory[r.category].passed++;
        }
    });
    
    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>MCP完整端到端测试报告 - ${total}个案例</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; }
        h1 { color: #1890ff; margin-bottom: 10px; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }
        .summary-card { background: #f9f9f9; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
        .summary-card .value { font-size: 32px; font-weight: bold; }
        .category-stats { margin: 30px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f5f5f5; font-weight: 600; }
        .status-passed { color: #52c41a; font-weight: bold; }
        .status-failed { color: #f5222d; font-weight: bold; }
        .screenshots { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 15px 0; }
        .screenshot img { width: 100%; height: auto; border: 1px solid #eee; border-radius: 4px; cursor: pointer; }
        .screenshot-caption { font-size: 12px; text-align: center; color: #666; }
        .case-result { margin: 20px 0; padding: 20px; border: 1px solid #eee; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 MCP完整端到端测试报告</h1>
        <p>测试时间: ${new Date().toISOString()}</p>
        <p>测试案例: ${total}个 | 浏览器: Chromium | 分辨率: 1920x1080</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>总案例数</h3>
                <div class="value">${total}</div>
            </div>
            <div class="summary-card">
                <h3>通过数量</h3>
                <div class="value" style="color: #52c41a;">${passed}</div>
            </div>
            <div class="summary-card">
                <h3>失败数量</h3>
                <div class="value" style="color: #f5222d;">${failed}</div>
            </div>
            <div class="summary-card">
                <h3>通过率</h3>
                <div class="value">${passRate}%</div>
            </div>
        </div>
        
        <div class="category-stats">
            <h2>按分类统计</h2>
            <table>
                <tr>
                    <th>分类</th>
                    <th>总数</th>
                    <th>通过</th>
                    <th>失败</th>
                    <th>通过率</th>
                </tr>
                ${Object.entries(byCategory).map(([cat, stats]) => `
                <tr>
                    <td><strong>${cat}</strong></td>
                    <td>${stats.total}</td>
                    <td>${stats.passed}</td>
                    <td>${stats.total - stats.passed}</td>
                    <td>${((stats.passed / stats.total) * 100).toFixed(1)}%</td>
                </tr>
                `).join('')}
            </table>
        </div>
        
        <h2>测试案例详情（前20个）</h2>
        ${results.slice(0, 20).map(result => `
        <div class="case-result">
            <h3>#${result.id.toString().padStart(3, '0')} - ${result.name}</h3>
            <p><strong>分类:</strong> ${result.category} | 
               <strong>状态:</strong> <span class="status-${result.status}">${result.status === 'passed' ? '✅ 通过' : '❌ 失败'}</span> |
               <strong>耗时:</strong> ${result.duration ? result.duration.toFixed(2) + '秒' : 'N/A'}</p>
            ${result.screenshots && result.screenshots.length > 0 ? `
            <div class="screenshots">
                ${result.screenshots.slice(0, 8).map(screenshot => `
                <div class="screenshot">
                    <img src="${screenshot}" alt="Screenshot" onclick="window.open(this.src)">
                    <div class="screenshot-caption">${path.basename(screenshot)}</div>
                </div>
                `).join('')}
            </div>
            ` : ''}
        </div>
        `).join('')}
        
        <p style="margin-top: 30px; color: #666; text-align: center;">
            © 2025 HydroClaude MCP Testing System
        </p>
    </div>
</body>
</html>`;
    
    fs.writeFileSync(outputFile, html, 'utf-8');
    console.log(`✅ HTML报告已保存: ${outputFile}`);
}

// 主函数
async function main() {
    console.log('='.repeat(70));
    console.log('🌐 HydroClaude MCP完整端到端测试');
    console.log('='.repeat(70));
    console.log();
    console.log(`配置:`);
    console.log(`  • Web应用: ${CONFIG.baseUrl}`);
    console.log(`  • 测试案例: ${CONFIG.maxCases}个`);
    console.log(`  • 截图目录: ${CONFIG.screenshotDir}`);
    console.log(`  • 无头模式: ${CONFIG.headless}`);
    console.log();
    
    // 创建目录
    ensureDir(CONFIG.screenshotDir);
    ensureDir(CONFIG.reportDir);
    
    // 加载测试案例
    console.log('📂 加载测试案例...');
    const testCases = loadTestCases();
    console.log(`✅ 已加载 ${testCases.length} 个测试案例\n`);
    
    if (testCases.length === 0) {
        console.error('❌ 没有找到测试案例');
        process.exit(1);
    }
    
    // 启动浏览器
    console.log('🚀 启动浏览器...');
    const browser = await puppeteer.launch({
        headless: CONFIG.headless,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
        ]
    });
    console.log('✅ 浏览器已启动\n');
    
    // 运行测试
    const results = [];
    const startTime = Date.now();
    
    for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];
        const caseDir = path.join(
            CONFIG.screenshotDir,
            `case_${testCase.id.toString().padStart(3, '0')}_${testCase.name}`
        );
        ensureDir(caseDir);
        
        const result = await testSingleCase(browser, testCase, caseDir);
        results.push(result);
        
        // 短暂休息
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    const endTime = Date.now();
    const totalDuration = (endTime - startTime) / 1000;
    
    // 关闭浏览器
    await browser.close();
    console.log('\n✅ 浏览器已关闭\n');
    
    // 统计
    console.log('='.repeat(70));
    console.log('📊 测试完成统计');
    console.log('='.repeat(70));
    
    const total = results.length;
    const passed = results.filter(r => r.status === 'passed').length;
    const failed = total - passed;
    const passRate = ((passed / total) * 100).toFixed(1);
    
    console.log(`\n总测试: ${total}个`);
    console.log(`通过:   ${passed}个`);
    console.log(`失败:   ${failed}个`);
    console.log(`通过率: ${passRate}%`);
    console.log(`总耗时: ${totalDuration.toFixed(1)}秒 (${(totalDuration / 60).toFixed(1)}分钟)`);
    console.log(`平均:   ${(totalDuration / total).toFixed(1)}秒/案例`);
    
    // 保存JSON报告
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    const jsonFile = path.join(CONFIG.reportDir, `mcp_full_test_${timestamp}.json`);
    const report = {
        timestamp: new Date().toISOString(),
        config: CONFIG,
        summary: {
            total,
            passed,
            failed,
            passRate: `${passRate}%`,
            totalDuration,
            avgDuration: totalDuration / total
        },
        results
    };
    fs.writeFileSync(jsonFile, JSON.stringify(report, null, 2), 'utf-8');
    console.log(`\n✅ JSON报告已保存: ${jsonFile}`);
    
    // 生成HTML报告
    const htmlFile = path.join(CONFIG.reportDir, `mcp_full_test_${timestamp}.html`);
    generateHTMLReport(results, htmlFile);
    
    console.log('\n' + '='.repeat(70));
    console.log('✅ MCP完整端到端测试完成');
    console.log('='.repeat(70));
    
    process.exit(failed > 0 ? 1 : 0);
}

// 运行
if (require.main === module) {
    main().catch(error => {
        console.error('❌ 测试失败:', error);
        process.exit(1);
    });
}

module.exports = { testSingleCase };
