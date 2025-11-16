#!/bin/bash
# 启动Web服务（后端+前端）

echo "======================================================================"
echo "🚀 启动HydroClaude Web服务"
echo "======================================================================"
echo

# 1. 检查Python后端
echo "1️⃣ 检查Python后端..."
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "   ✅ 后端API已在运行 (http://localhost:5000)"
else
    echo "   ⚠️  后端API未运行"
    echo "   提示: 请在另一个终端运行: python api/main.py"
fi
echo

# 2. 检查前端应用
echo "2️⃣ 检查React前端..."
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "   ✅ 前端应用已在运行 (http://localhost:5173)"
else
    echo "   ⚠️  前端应用未运行"
    echo "   提示: 请在另一个终端运行:"
    echo "     cd webapp"
    echo "     npm install"
    echo "     npm run dev"
fi
echo

echo "======================================================================"
echo "🔍 服务状态检查完成"
echo "======================================================================"
echo
echo "准备好后，运行测试:"
echo "  python tests/e2e/real_web_e2e_test.py"
echo
