#!/bin/bash
# HydroClaude Web Backend 启动脚本

echo "================================================================================"
echo "🌊 HydroClaude Web Backend"
echo "================================================================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python 3.8+"
    exit 1
fi

echo "✅ Python版本: $(python3 --version)"

# 检查依赖
echo ""
echo "📦 检查依赖..."
python3 -c "import numpy" 2>/dev/null || { echo "⚠️  缺少numpy，正在安装..."; pip3 install numpy; }
python3 -c "import fastapi" 2>/dev/null || { echo "⚠️  缺少fastapi，正在安装..."; pip3 install fastapi uvicorn; }
python3 -c "import pydantic" 2>/dev/null || { echo "⚠️  缺少pydantic，正在安装..."; pip3 install pydantic; }

echo "✅ 所有依赖已安装"

# 切换到后端目录
cd "$(dirname "$0")/backend/api_gateway" || exit 1

echo ""
echo "================================================================================"
echo "🚀 启动后端服务..."
echo "================================================================================"
echo ""
echo "📍 API文档: http://localhost:8000/api/docs"
echo "📍 健康检查: http://localhost:8000/health"
echo "📍 分析API: http://localhost:8000/api/v1/analysis/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""
echo "================================================================================"
echo ""

# 启动服务
python3 main.py
