#!/bin/bash
# MCP浏览器测试环境设置脚本

echo "======================================================================"
echo "🔧 设置MCP浏览器测试环境"
echo "======================================================================"
echo

# 1. 检查Node.js
echo "1️⃣ 检查Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "   ✅ Node.js已安装: $NODE_VERSION"
else
    echo "   ❌ Node.js未安装"
    echo "   请访问 https://nodejs.org/ 下载安装"
    exit 1
fi

# 2. 检查npm
echo
echo "2️⃣ 检查npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "   ✅ npm已安装: $NPM_VERSION"
else
    echo "   ❌ npm未安装"
    exit 1
fi

# 3. 安装Puppeteer
echo
echo "3️⃣ 安装Puppeteer..."
if npm list -g puppeteer &> /dev/null; then
    echo "   ✅ Puppeteer已安装"
else
    echo "   📦 正在安装Puppeteer..."
    npm install -g puppeteer
    if [ $? -eq 0 ]; then
        echo "   ✅ Puppeteer安装完成"
    else
        echo "   ❌ Puppeteer安装失败"
        exit 1
    fi
fi

# 4. 创建测试脚本目录
echo
echo "4️⃣ 创建测试目录..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/screenshots_mcp"
mkdir -p "$SCRIPT_DIR/reports"
echo "   ✅ 目录已创建"

# 5. 创建Node.js测试脚本
echo
echo "5️⃣ 创建测试脚本..."

cat > "$SCRIPT_DIR/screenshot_helper.js" << 'EOF'
/**
 * Puppeteer截图助手
 * 用于MCP浏览器自动化测试
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function captureScreenshot(url, outputPath, options = {}) {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        await page.setViewport({ 
            width: options.width || 1920, 
            height: options.height || 1080 
        });
        
        console.log(`Navigating to ${url}...`);
        await page.goto(url, { 
            waitUntil: 'networkidle2', 
            timeout: 30000 
        });
        
        if (options.waitTime) {
            await page.waitForTimeout(options.waitTime);
        }
        
        console.log(`Taking screenshot...`);
        await page.screenshot({ 
            path: outputPath,
            fullPage: options.fullPage || true
        });
        
        console.log(`✅ Screenshot saved: ${outputPath}`);
        return true;
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        return false;
    } finally {
        await browser.close();
    }
}

async function runTestFlow(url, actions, screenshotDir) {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        
        console.log(`🌐 Navigating to ${url}...`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        await page.waitForTimeout(2000);
        
        console.log(`📝 Executing ${actions.length} actions...`);
        
        for (let i = 0; i < actions.length; i++) {
            const action = actions[i];
            console.log(`  Action ${i + 1}: ${action.type}`);
            
            switch (action.type) {
                case 'click':
                    await page.click(action.selector);
                    await page.waitForTimeout(1000);
                    break;
                    
                case 'type':
                    await page.type(action.selector, action.text);
                    await page.waitForTimeout(500);
                    break;
                    
                case 'wait':
                    await page.waitForTimeout(action.duration * 1000);
                    break;
                    
                case 'screenshot':
                    const filepath = path.join(screenshotDir, action.filename);
                    await page.screenshot({ path: filepath, fullPage: true });
                    console.log(`    📸 Screenshot: ${action.filename}`);
                    break;
                    
                case 'scroll':
                    await page.evaluate(() => window.scrollBy(0, window.innerHeight));
                    await page.waitForTimeout(500);
                    break;
            }
        }
        
        console.log(`✅ Test flow completed`);
        return true;
    } catch (error) {
        console.error(`❌ Error: ${error.message}`);
        return false;
    } finally {
        await browser.close();
    }
}

// 命令行接口
if (require.main === module) {
    const args = process.argv.slice(2);
    
    if (args.length < 2) {
        console.log('Usage: node screenshot_helper.js <url> <output_path> [options]');
        process.exit(1);
    }
    
    const url = args[0];
    const outputPath = args[1];
    const options = args[2] ? JSON.parse(args[2]) : {};
    
    captureScreenshot(url, outputPath, options)
        .then(success => process.exit(success ? 0 : 1));
}

module.exports = { captureScreenshot, runTestFlow };
EOF

echo "   ✅ screenshot_helper.js已创建"

# 6. 测试Puppeteer
echo
echo "6️⃣ 测试Puppeteer..."
cat > "$SCRIPT_DIR/test_puppeteer.js" << 'EOF'
const puppeteer = require('puppeteer');

(async () => {
    console.log('🧪 Testing Puppeteer...');
    
    try {
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox']
        });
        
        const page = await browser.newPage();
        await page.goto('https://example.com');
        console.log('✅ Puppeteer works!');
        
        await browser.close();
        process.exit(0);
    } catch (error) {
        console.error('❌ Puppeteer test failed:', error.message);
        process.exit(1);
    }
})();
EOF

node "$SCRIPT_DIR/test_puppeteer.js"
if [ $? -eq 0 ]; then
    echo "   ✅ Puppeteer测试通过"
    rm "$SCRIPT_DIR/test_puppeteer.js"
else
    echo "   ❌ Puppeteer测试失败"
    exit 1
fi

echo
echo "======================================================================"
echo "✅ MCP浏览器测试环境设置完成"
echo "======================================================================"
echo
echo "可用的工具:"
echo "  • screenshot_helper.js - Puppeteer截图助手"
echo "  • mcp_browser_test.py  - Python测试脚本"
echo
echo "快速测试:"
echo "  node $SCRIPT_DIR/screenshot_helper.js https://example.com test.png"
echo
echo "运行完整测试:"
echo "  python3 $SCRIPT_DIR/mcp_browser_test.py"
echo
