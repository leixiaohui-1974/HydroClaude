#!/bin/bash
# HydroClaude Web端到端全量测试脚本（Linux/Mac）
# 使用方法: ./run_full_test.sh [案例数量]

set -e

echo "================================================================"
echo "HydroClaude Web端到端测试"
echo "================================================================"
echo ""

# 检查参数
MAX_CASES=${1:-10}

echo "测试配置:"
echo "  - 最大案例数: $MAX_CASES"
echo "  - 浏览器: Chromium (中文)"
echo "  - 截图: 启用"
echo ""

# 检查环境
echo "[1/5] 检查环境..."
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python未安装"
    exit 1
fi
echo "  ✅ Python已安装"

if ! command -v playwright &> /dev/null; then
    echo "  ⚠️  Playwright未安装，正在安装..."
    pip3 install playwright
    playwright install chromium
fi
echo "  ✅ Playwright已安装"

# 检查Web应用
echo ""
echo "[2/5] 检查Web应用..."
if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "  ❌ Web应用未运行"
    echo "  请先启动: cd webapp && npm run dev"
    exit 1
fi
echo "  ✅ Web应用运行中"

# 转换测试案例
echo ""
echo "[3/5] 转换测试案例..."
python3 convert_test_cases.py
echo "  ✅ 转换完成"

# 运行测试
echo ""
echo "[4/5] 运行端到端测试..."
echo "  正在测试 $MAX_CASES 个案例，请稍候..."
echo ""
python3 test_web_e2e.py --max-cases $MAX_CASES

# 打开报告
echo ""
echo "[5/5] 生成报告..."
LATEST_REPORT=$(ls -t reports/test_report_*.html | head -1)
if [ -f "$LATEST_REPORT" ]; then
    echo "  ✅ 报告已生成: $LATEST_REPORT"
    echo ""
    echo "是否打开测试报告? (y/n)"
    read -r OPEN_REPORT
    if [ "$OPEN_REPORT" = "y" ]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$LATEST_REPORT"
        elif command -v open &> /dev/null; then
            open "$LATEST_REPORT"
        fi
    fi
else
    echo "  ⚠️  未找到报告文件"
fi

echo ""
echo "================================================================"
echo "测试完成！"
echo "================================================================"
echo ""
echo "查看结果:"
echo "  - HTML报告: $LATEST_REPORT"
echo "  - JSON报告: reports/test_report_*.json"
echo "  - 截图: screenshots/"
echo ""
