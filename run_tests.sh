#!/bin/bash
# HydroClaude 测试执行脚本
# 按照 Spec-Kit 规范编写
# Spec: 001-comprehensive-review-and-testing

echo "=========================================="
echo "HydroClaude 测试套件"
echo "Powered by Spec-Kit"
echo "=========================================="
echo ""

# 检查 pytest 是否安装
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest 未安装，正在安装..."
    pip install -r requirements_test.txt
fi

echo "📋 可用的测试命令:"
echo ""
echo "1. 运行所有测试:"
echo "   pytest -v"
echo ""
echo "2. 运行商业对标测试:"
echo "   pytest -m commercial -v"
echo ""
echo "3. 运行后端测试:"
echo "   pytest -m backend -v"
echo ""
echo "4. 运行单个测试文件:"
echo "   pytest tests/backend/solvers/test_godunov_commercial.py -v -s"
echo ""
echo "5. 生成 HTML 报告:"
echo "   pytest --html=reports/html/test_report.html --self-contained-html"
echo ""
echo "6. 生成覆盖率报告:"
echo "   pytest --cov --cov-report=html"
echo ""

read -p "选择要执行的测试 (1-6, 或按 Enter 跳过): " choice

case $choice in
    1)
        echo "运行所有测试..."
        pytest -v
        ;;
    2)
        echo "运行商业对标测试..."
        pytest -m commercial -v -s
        ;;
    3)
        echo "运行后端测试..."
        pytest -m backend -v
        ;;
    4)
        echo "运行 GodunvFVMSolver 对标测试..."
        pytest tests/backend/solvers/test_godunov_commercial.py -v -s
        ;;
    5)
        echo "生成 HTML 报告..."
        pytest --html=reports/html/test_report.html --self-contained-html
        echo "报告已生成: reports/html/test_report.html"
        ;;
    6)
        echo "生成覆盖率报告..."
        pytest --cov --cov-report=html
        echo "覆盖率报告: reports/html/coverage/index.html"
        ;;
    *)
        echo "跳过测试执行"
        ;;
esac

echo ""
echo "=========================================="
echo "测试套件准备完成！"
echo "=========================================="
