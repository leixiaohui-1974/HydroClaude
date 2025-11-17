#!/bin/bash
# 启动HydroClaude后端服务器
# Start HydroClaude Backend Server

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🚀 启动 HydroClaude 后端服务器                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

echo "✅ Python版本: $(python3 --version)"
echo ""

# 进入后端目录
cd "$(dirname "$0")/backend" || exit 1

# 检查依赖
echo "检查依赖..."
python3 -c "import fastapi, pydantic, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  缺少依赖，正在安装..."
    pip3 install fastapi pydantic uvicorn --quiet
fi

echo "✅ 依赖检查完成"
echo ""

# 启动服务器
echo "启动服务器..."
echo "访问地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "─────────────────────────────────────────────────────────"
echo ""

python3 -m uvicorn api_gateway.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
