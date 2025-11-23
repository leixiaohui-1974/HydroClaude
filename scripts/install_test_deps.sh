#!/bin/bash
# HydroClaude 测试依赖安装脚本
# 一键安装所有测试依赖

set -e  # 遇到错误立即退出

echo "=========================================="
echo "HydroClaude 测试依赖安装脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Python 版本
echo -e "${YELLOW}[1/6] 检查 Python 版本...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✅ Python 版本: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 未安装，请先安装 Python 3.9+${NC}"
    exit 1
fi

# 检查 pip
echo ""
echo -e "${YELLOW}[2/6] 检查 pip...${NC}"
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✅ pip 已安装${NC}"
    pip3 --version
else
    echo -e "${RED}❌ pip 未安装，请先安装 pip${NC}"
    exit 1
fi

# 升级 pip
echo ""
echo -e "${YELLOW}[2.1] 升级 pip...${NC}"
pip3 install --upgrade pip

# 安装 Python 依赖
echo ""
echo -e "${YELLOW}[3/6] 安装 Python 依赖...${NC}"
echo "这可能需要几分钟..."

# 检查 requirements.txt
if [ -f "requirements.txt" ]; then
    echo "从 requirements.txt 安装基础依赖..."
    pip3 install -r requirements.txt
else
    echo -e "${YELLOW}⚠️ requirements.txt 未找到，跳过基础依赖安装${NC}"
fi

# 安装测试依赖
echo ""
echo "安装测试依赖..."
pip3 install \
    pytest==7.4.0 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    pytest-html==3.2.0 \
    pytest-xdist==3.3.1 \
    httpx==0.24.1 \
    locust==2.15.1 \
    playwright==1.40.0

echo -e "${GREEN}✅ Python 依赖安装完成${NC}"

# 安装 Playwright 浏览器
echo ""
echo -e "${YELLOW}[4/6] 安装 Playwright 浏览器...${NC}"
echo "这可能需要几分钟..."

if command -v playwright &> /dev/null; then
    playwright install chromium firefox webkit
    echo -e "${GREEN}✅ Playwright 浏览器安装完成${NC}"
else
    echo -e "${RED}❌ Playwright 命令未找到${NC}"
    echo "尝试通过 Python 模块安装..."
    python3 -m playwright install chromium firefox webkit
    echo -e "${GREEN}✅ Playwright 浏览器安装完成${NC}"
fi

# 检查 Node.js
echo ""
echo -e "${YELLOW}[5/6] 检查 Node.js...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✅ Node.js 版本: $NODE_VERSION${NC}"
    
    # 检查 npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        echo -e "${GREEN}✅ npm 版本: $NPM_VERSION${NC}"
        
        # 安装 Node.js 依赖
        echo ""
        echo "安装 Node.js 依赖..."
        if [ -f "package.json" ]; then
            npm install
            echo -e "${GREEN}✅ Node.js 依赖安装完成${NC}"
        else
            echo -e "${YELLOW}⚠️ package.json 未找到，跳过 Node.js 依赖安装${NC}"
        fi
    else
        echo -e "${RED}❌ npm 未安装${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Node.js 未安装，前端测试将无法运行${NC}"
    echo "请访问 https://nodejs.org/ 安装 Node.js 16+"
fi

# 运行环境检查
echo ""
echo -e "${YELLOW}[6/6] 运行环境检查...${NC}"
echo ""

if [ -f "tests/test_environment.py" ]; then
    python3 tests/test_environment.py
else
    echo -e "${YELLOW}⚠️ 环境检查脚本未找到${NC}"
fi

# 完成
echo ""
echo "=========================================="
echo -e "${GREEN}✅ 安装完成！${NC}"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 运行后端测试: pytest tests/backend/ -v"
echo "  2. 运行前端测试: npm run test"
echo "  3. 运行 E2E 测试: npm run test:e2e"
echo "  4. 运行性能测试: locust -f locustfile.py --host=http://localhost:8000"
echo ""
echo "查看详细指南: QUICK_START_TESTING.md"
echo ""
