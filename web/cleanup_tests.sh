#!/bin/bash
# HydroClaude Web 测试环境清理脚本

echo "=========================================="
echo "HydroClaude Web 测试环境清理"
echo "=========================================="
echo ""

# 询问用户
read -p "是否清理测试截图？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "清理测试截图..."
    rm -rf /workspace/web/comprehensive_screenshots/
    rm -rf /workspace/web/advanced_screenshots/
    rm -rf /workspace/web/detailed_screenshots/
    rm -rf /workspace/web/final_screenshots/
    rm -rf /workspace/web/ultimate_screenshots/
    rm -rf /workspace/web/test_screenshots/
    echo "✅ 截图已清理"
fi

read -p "是否清理测试报告JSON文件？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "清理测试报告..."
    rm -f /workspace/web/*test_report.json
    rm -f /workspace/web/test_summary.json
    echo "✅ JSON报告已清理"
fi

read -p "是否清理测试日志？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "清理测试日志..."
    rm -f /tmp/backend*.log
    rm -f /tmp/frontend*.log
    rm -f /tmp/vite*.log
    echo "✅ 日志已清理"
fi

echo ""
echo "=========================================="
echo "清理完成！"
echo "=========================================="
echo ""
echo "保留的文件:"
ls -lh /workspace/web/*REPORT*.md 2>/dev/null | tail -5
echo ""
echo "提示: Markdown报告文件已保留，如需删除请手动执行:"
echo "  rm /workspace/web/*REPORT*.md"
