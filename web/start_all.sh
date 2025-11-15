#!/bin/bash
# HydroClaude Web 完整系统启动脚本

echo "================================================================================"
echo "🌊 HydroClaude Web System - 完整启动"
echo "================================================================================"
echo ""

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📂 工作目录: $SCRIPT_DIR"
echo ""

# 检查依赖
echo "🔍 检查系统依赖..."
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    echo "请安装Python 3.8+: https://www.python.org/downloads/"
    exit 1
fi
echo "✅ Python3: $(python3 --version)"

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    echo "请安装Node.js 16+: https://nodejs.org/"
    exit 1
fi
echo "✅ Node.js: $(node --version)"
echo "✅ npm: $(npm --version)"

echo ""
echo "================================================================================"
echo "🚀 启动步骤"
echo "================================================================================"
echo ""
echo "1️⃣  后端服务将在端口 8000 启动"
echo "2️⃣  前端服务将在端口 5173 启动"
echo ""
echo "请在两个独立的终端窗口中运行："
echo ""
echo "终端1 (后端):"
echo "  cd $SCRIPT_DIR"
echo "  ./start_backend.sh"
echo ""
echo "终端2 (前端):"
echo "  cd $SCRIPT_DIR"
echo "  ./start_frontend.sh"
echo ""
echo "或者使用以下命令同时启动（需要tmux或screen）："
echo ""
echo "使用tmux:"
echo "  tmux new-session -d -s hydroclaude-backend 'cd $SCRIPT_DIR && ./start_backend.sh'"
echo "  tmux new-session -d -s hydroclaude-frontend 'cd $SCRIPT_DIR && ./start_frontend.sh'"
echo "  tmux attach -t hydroclaude-backend"
echo ""
echo "================================================================================"
echo "📍 访问地址"
echo "================================================================================"
echo ""
echo "🌐 前端应用:  http://localhost:5173"
echo "📡 API文档:   http://localhost:8000/api/docs"
echo "❤️  健康检查:  http://localhost:8000/health"
echo "🔍 分析API:   http://localhost:8000/api/v1/analysis/health"
echo ""
echo "================================================================================"
echo ""

# 提示用户选择
echo "请选择启动方式："
echo "1) 分别启动（推荐，需要两个终端）"
echo "2) 使用tmux同时启动（需要安装tmux）"
echo "3) 仅查看启动命令"
echo ""
read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "✅ 请打开两个终端窗口，分别运行："
        echo "   终端1: cd $SCRIPT_DIR && ./start_backend.sh"
        echo "   终端2: cd $SCRIPT_DIR && ./start_frontend.sh"
        ;;
    2)
        if ! command -v tmux &> /dev/null; then
            echo "❌ tmux 未安装，请先安装: sudo apt-get install tmux"
            exit 1
        fi
        echo ""
        echo "🚀 使用tmux启动..."
        tmux new-session -d -s hydroclaude-backend "cd $SCRIPT_DIR && ./start_backend.sh"
        tmux new-session -d -s hydroclaude-frontend "cd $SCRIPT_DIR && ./start_frontend.sh"
        echo "✅ 服务已在后台启动"
        echo ""
        echo "查看后端日志: tmux attach -t hydroclaude-backend"
        echo "查看前端日志: tmux attach -t hydroclaude-frontend"
        echo "列出所有会话: tmux ls"
        echo "停止服务: tmux kill-session -t hydroclaude-backend && tmux kill-session -t hydroclaude-frontend"
        ;;
    3)
        echo ""
        echo "✅ 启动命令已显示在上方"
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "================================================================================"
echo "✅ 准备完成！"
echo "================================================================================"
