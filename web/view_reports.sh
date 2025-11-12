#!/bin/bash
# view_reports.sh - 快速查看所有测试报告

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║         HydroClaude Web 测试报告查看器                      ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查是否在正确的目录
if [ ! -f "README_TEST_COMPLETE.md" ]; then
    echo "❌ 错误: 请在 /workspace/web 目录下运行此脚本"
    exit 1
fi

# 菜单
while true; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  请选择要查看的报告："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  📋 核心报告"
    echo "  ─────────────────────────────────────────────────────────"
    echo "  1)  📊 最终综合报告 (FINAL_COMPREHENSIVE_REPORT.md)"
    echo "  2)  🔧 问题修复报告 (ISSUE_FIX_REPORT.md)"
    echo "  3)  📖 测试执行指南 (TEST_EXECUTION_GUIDE.md)"
    echo "  4)  🚀 快速开始指南 (QUICK_START.md)"
    echo "  5)  📑 完整导航索引 (README_TEST_COMPLETE.md)"
    echo ""
    echo "  📊 测试数据"
    echo "  ─────────────────────────────────────────────────────────"
    echo "  6)  📈 终极测试JSON (ultimate_test_report.json)"
    echo "  7)  📄 测试汇总JSON (test_summary.json)"
    echo "  8)  📸 查看所有截图目录"
    echo ""
    echo "  🛠️ 部署和维护"
    echo "  ─────────────────────────────────────────────────────────"
    echo "  9)  ✅ 部署检查清单 (DEPLOYMENT_CHECKLIST.md)"
    echo "  10) 🔧 维护运维指南 (MAINTENANCE_GUIDE.md)"
    echo ""
    echo "  📁 其他"
    echo "  ─────────────────────────────────────────────────────────"
    echo "  11) 📂 项目结构说明 (PROJECT_STRUCTURE.md)"
    echo "  12) 🖼️  截图分析报告 (SCREENSHOT_ANALYSIS_REPORT.md)"
    echo "  13) 🌐 打开HTML索引 (TEST_INDEX.html)"
    echo ""
    echo "  14) 📊 显示快速统计"
    echo "  15) 🔍 搜索文档内容"
    echo ""
    echo "  0)  ❌ 退出"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -p "请输入选项 (0-15): " choice
    
    case $choice in
        1)
            clear
            echo "📊 最终综合报告"
            echo "════════════════════════════════════════════════════════"
            cat FINAL_COMPREHENSIVE_REPORT.md | less
            ;;
        2)
            clear
            echo "🔧 问题修复报告"
            echo "════════════════════════════════════════════════════════"
            cat ISSUE_FIX_REPORT.md | less
            ;;
        3)
            clear
            echo "📖 测试执行指南"
            echo "════════════════════════════════════════════════════════"
            cat TEST_EXECUTION_GUIDE.md | less
            ;;
        4)
            clear
            echo "🚀 快速开始指南"
            echo "════════════════════════════════════════════════════════"
            cat QUICK_START.md | less
            ;;
        5)
            clear
            echo "📑 完整导航索引"
            echo "════════════════════════════════════════════════════════"
            cat README_TEST_COMPLETE.md | less
            ;;
        6)
            clear
            echo "📈 终极测试JSON"
            echo "════════════════════════════════════════════════════════"
            cat ultimate_test_report.json | python3 -m json.tool | less
            ;;
        7)
            clear
            echo "📄 测试汇总JSON"
            echo "════════════════════════════════════════════════════════"
            if [ -f "test_summary.json" ]; then
                cat test_summary.json | python3 -m json.tool | less
            else
                echo "❌ 文件不存在"
            fi
            ;;
        8)
            clear
            echo "📸 所有截图目录"
            echo "════════════════════════════════════════════════════════"
            echo ""
            for dir in ultimate_screenshots final_screenshots comprehensive_screenshots advanced_screenshots detailed_screenshots; do
                if [ -d "$dir" ]; then
                    count=$(ls -1 "$dir"/*.png 2>/dev/null | wc -l)
                    echo "  📁 $dir/ ($count 张)"
                    ls -lh "$dir"/*.png 2>/dev/null | awk '{print "     ", $9, "(" $5 ")"}'
                    echo ""
                fi
            done
            read -p "按Enter继续..."
            ;;
        9)
            clear
            echo "✅ 部署检查清单"
            echo "════════════════════════════════════════════════════════"
            cat DEPLOYMENT_CHECKLIST.md | less
            ;;
        10)
            clear
            echo "🔧 维护运维指南"
            echo "════════════════════════════════════════════════════════"
            cat MAINTENANCE_GUIDE.md | less
            ;;
        11)
            clear
            echo "📂 项目结构说明"
            echo "════════════════════════════════════════════════════════"
            cat PROJECT_STRUCTURE.md | less
            ;;
        12)
            clear
            echo "🖼️ 截图分析报告"
            echo "════════════════════════════════════════════════════════"
            cat SCREENSHOT_ANALYSIS_REPORT.md | less
            ;;
        13)
            echo ""
            echo "🌐 打开HTML索引..."
            if command -v xdg-open > /dev/null; then
                xdg-open TEST_INDEX.html &
                echo "✅ 已在浏览器中打开"
            elif command -v open > /dev/null; then
                open TEST_INDEX.html &
                echo "✅ 已在浏览器中打开"
            else
                echo "⚠️  无法自动打开浏览器"
                echo "请手动打开: file://$(pwd)/TEST_INDEX.html"
            fi
            read -p "按Enter继续..."
            ;;
        14)
            clear
            echo "📊 快速统计"
            echo "════════════════════════════════════════════════════════"
            echo ""
            echo "📋 文档统计:"
            echo "  • Markdown报告: $(ls -1 *REPORT*.md 2>/dev/null | wc -l) 个"
            echo "  • 测试脚本: $(ls -1 *test*.py 2>/dev/null | wc -l) 个"
            echo "  • JSON数据: $(ls -1 *.json 2>/dev/null | wc -l) 个"
            echo "  • Shell脚本: $(ls -1 *.sh 2>/dev/null | wc -l) 个"
            echo ""
            echo "📸 截图统计:"
            total_screenshots=0
            for dir in ultimate_screenshots final_screenshots comprehensive_screenshots advanced_screenshots detailed_screenshots; do
                if [ -d "$dir" ]; then
                    count=$(ls -1 "$dir"/*.png 2>/dev/null | wc -l)
                    echo "  • $dir: $count 张"
                    total_screenshots=$((total_screenshots + count))
                fi
            done
            echo "  ─────────────────────────"
            echo "  总计: $total_screenshots 张"
            echo ""
            echo "📊 测试结果摘要:"
            if [ -f "ultimate_test_report.json" ]; then
                python3 -c "
import json
with open('ultimate_test_report.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    summary = data.get('summary', {})
    print(f\"  • 总测试项: {summary.get('total', 0)} 个\")
    print(f\"  • 通过: {summary.get('passed', 0)} 个\")
    print(f\"  • 失败: {summary.get('failed', 0)} 个\")
    print(f\"  • 成功率: {summary.get('success_rate', 0)}\")
"
            fi
            echo ""
            read -p "按Enter继续..."
            ;;
        15)
            clear
            echo "🔍 搜索文档内容"
            echo "════════════════════════════════════════════════════════"
            echo ""
            read -p "请输入搜索关键词: " keyword
            if [ ! -z "$keyword" ]; then
                echo ""
                echo "搜索结果:"
                echo "─────────────────────────────────────────────────────"
                grep -r -i "$keyword" *.md 2>/dev/null | head -20
                echo ""
                echo "（显示前20条结果）"
            fi
            read -p "按Enter继续..."
            ;;
        0)
            echo ""
            echo "👋 再见！"
            echo ""
            exit 0
            ;;
        *)
            echo ""
            echo "❌ 无效选项，请重新选择"
            sleep 2
            ;;
    esac
done
