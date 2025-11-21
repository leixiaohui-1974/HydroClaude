#!/bin/bash
# HydroClaude 测试执行脚本
# 版本: v1.0
# 日期: 2025-11-20

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "      🏆 HydroClaude 测试执行脚本"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 进入项目目录
cd /workspace

# 显示菜单
echo -e "${BLUE}请选择测试选项:${NC}"
echo ""
echo "  1) 运行所有测试 (68个测试, ~14秒)"
echo "  2) 运行基础测试 (4个测试, ~1秒)"
echo "  3) 运行多场景测试 (11个测试, ~2秒)"
echo "  4) 运行极端场景测试 (11个测试, ~1秒)"
echo "  5) 运行水力学函数测试 (15个测试, ~1秒)"
echo "  6) 运行水工结构测试 (15个测试, ~1秒)"
echo "  7) 运行集成测试 (6个测试, ~2秒)"
echo "  8) 运行性能基准测试 (6个测试, ~8秒)"
echo "  9) 生成HTML测试报告"
echo " 10) 生成覆盖率报告"
echo "  0) 退出"
echo ""
read -p "请输入选项 [1-10]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}运行所有测试...${NC}"
        echo ""
        python3 -m pytest \
            tests/backend/solvers/test_hydrostatic_simple.py \
            tests/backend/solvers/test_hydrostatic_scenarios.py \
            tests/backend/solvers/test_hydrostatic_extreme.py \
            tests/backend/utils/test_canal_utils.py \
            tests/backend/structures/test_gate_simple.py \
            tests/backend/integration/test_solver_with_structures.py \
            tests/backend/benchmarks/test_performance_benchmark.py \
            -v
        ;;
    2)
        echo ""
        echo -e "${YELLOW}运行基础测试...${NC}"
        echo ""
        python3 -m pytest tests/backend/solvers/test_hydrostatic_simple.py -v
        ;;
    3)
        echo ""
        echo -e "${YELLOW}运行多场景测试...${NC}"
        echo ""
        python3 -m pytest tests/backend/solvers/test_hydrostatic_scenarios.py -v
        ;;
    4)
        echo ""
        echo -e "${YELLOW}运行极端场景测试...${NC}"
        echo ""
        python3 -m pytest tests/backend/solvers/test_hydrostatic_extreme.py -v
        ;;
    5)
        echo ""
        echo -e "${YELLOW}运行水力学函数测试...${NC}"
        echo ""
        python3 -m pytest tests/backend/utils/test_canal_utils.py -v
        ;;
    6)
        echo ""
        echo -e "${YELLOW}运行水工结构测试...${NC}"
        echo ""
        python3 -m pytest tests/backend/structures/test_gate_simple.py -v
        ;;
    7)
        echo ""
        echo -e "${YELLOW}运行集成测试...${NC}"
        echo ""
        python3 -m pytest tests/backend/integration/test_solver_with_structures.py -v
        ;;
    8)
        echo ""
        echo -e "${YELLOW}运行性能基准测试...${NC}"
        echo ""
        python3 -m pytest tests/backend/benchmarks/test_performance_benchmark.py -v
        ;;
    9)
        echo ""
        echo -e "${YELLOW}生成HTML测试报告...${NC}"
        echo ""
        python3 -m pytest \
            tests/backend/solvers/test_hydrostatic_*.py \
            tests/backend/utils/test_canal_utils.py \
            tests/backend/structures/test_gate_simple.py \
            tests/backend/integration/test_solver_with_structures.py \
            tests/backend/benchmarks/test_performance_benchmark.py \
            --html=reports/html/test_report_$(date +%Y%m%d_%H%M%S).html \
            --self-contained-html
        echo ""
        echo -e "${GREEN}✅ HTML报告已生成到 reports/html/目录${NC}"
        ;;
    10)
        echo ""
        echo -e "${YELLOW}生成覆盖率报告...${NC}"
        echo ""
        python3 -m pytest \
            tests/backend/solvers/test_hydrostatic_*.py \
            tests/backend/utils/test_canal_utils.py \
            tests/backend/structures/test_gate_simple.py \
            tests/backend/integration/test_solver_with_structures.py \
            tests/backend/benchmarks/test_performance_benchmark.py \
            --cov=solvers.hydrostatic_canal_solver \
            --cov=utils.canal_utils \
            --cov=solvers.gate \
            --cov-report=html:reports/coverage \
            --cov-report=term
        echo ""
        echo -e "${GREEN}✅ 覆盖率报告已生成到 reports/coverage/index.html${NC}"
        ;;
    0)
        echo ""
        echo -e "${BLUE}退出${NC}"
        exit 0
        ;;
    *)
        echo ""
        echo -e "${RED}无效选项！${NC}"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ 测试执行完成！${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
