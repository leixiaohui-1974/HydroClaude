#!/bin/bash
# HydroClaude Web Frontend 启动脚本

echo "================================================================================"
echo "🎨 HydroClaude Web Frontend"
echo "================================================================================"
echo ""

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装Node.js 16+"
    exit 1
fi

echo "✅ Node.js版本: $(node --version)"
echo "✅ npm版本: $(npm --version)"

# 切换到前端目录
cd "$(dirname "$0")/frontend" || exit 1

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 首次运行，安装依赖..."
    npm install
fi

echo ""
echo "================================================================================"
echo "🚀 启动前端开发服务器..."
echo "================================================================================"
echo ""
echo "📍 本地访问: http://localhost:5173"
echo "📍 网络访问: 使用 --host 参数"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""
echo "================================================================================"
echo ""

# 启动服务
npm run dev
