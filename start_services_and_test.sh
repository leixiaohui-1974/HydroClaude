#!/bin/bash
# HydroClaude 启动服务并运行完整测试
# 用于端到端全流程测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "      🚀 HydroClaude 启动服务和测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -e "\n${BLUE}请选择操作:${NC}\n"
echo "  1) 启动后端服务"
echo "  2) 运行后端测试 (68个测试)"
echo "  3) 运行E2E测试"
echo "  4) 完整流程测试 (后端测试 + E2E测试)"
echo "  5) 查看服务状态"
echo "  6) 停止所有服务"
echo "  0) 退出"

read -p "请输入选项 [1-6]: " choice

case $choice in
    1)
        echo -e "\n${GREEN}启动后端服务...${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 检查端口8000是否被占用
        if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  端口8000已被占用${NC}"
            echo "请先停止占用端口的进程，或选择选项6停止服务"
            exit 1
        fi
        
        echo "启动后端API服务..."
        echo "访问: http://localhost:8000"
        echo "文档: http://localhost:8000/docs"
        echo ""
        echo -e "${YELLOW}提示: 按 Ctrl+C 停止服务${NC}"
        echo ""
        
        # 启动后端服务
        python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
        
    2)
        echo -e "\n${GREEN}运行后端测试 (68个测试)...${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 运行后端测试
        ./run_tests.sh
        
        echo -e "\n${GREEN}✅ 后端测试完成！${NC}"
        ;;
        
    3)
        echo -e "\n${GREEN}运行E2E测试...${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 检查后端服务是否运行
        if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  后端服务未运行${NC}"
            echo "E2E测试需要后端服务运行"
            echo "请先选择选项1启动后端服务"
            echo ""
            echo "运行E2E测试（无服务模式）..."
        fi
        
        # 运行E2E测试
        pytest tests/e2e/test_full_workflow.py -v -s
        
        echo -e "\n${GREEN}✅ E2E测试完成！${NC}"
        ;;
        
    4)
        echo -e "\n${GREEN}运行完整流程测试...${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Step 1: 运行后端测试
        echo -e "\n${BLUE}Step 1/2: 后端测试${NC}"
        ./run_tests.sh
        
        # Step 2: 运行E2E测试
        echo -e "\n${BLUE}Step 2/2: E2E测试${NC}"
        
        # 检查服务
        if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  后端服务未运行，部分E2E测试将跳过${NC}"
        fi
        
        pytest tests/e2e/test_full_workflow.py -v -s
        
        echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✅ 完整流程测试完成！${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        ;;
        
    5)
        echo -e "\n${GREEN}检查服务状态...${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 检查后端服务
        if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${GREEN}✅ 后端服务运行中${NC} - http://localhost:8000"
            echo "   进程ID: $(lsof -Pi :8000 -sTCP:LISTEN -t)"
        else
            echo -e "${RED}❌ 后端服务未运行${NC}"
        fi
        
        # 检查前端服务
        if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${GREEN}✅ 前端服务运行中${NC} - http://localhost:5173"
            echo "   进程ID: $(lsof -Pi :5173 -sTCP:LISTEN -t)"
        else
            echo -e "${RED}❌ 前端服务未运行${NC}"
        fi
        ;;
        
    6)
        echo -e "\n${YELLOW}停止所有服务...${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 停止后端服务
        if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "停止后端服务..."
            kill -9 $(lsof -Pi :8000 -sTCP:LISTEN -t) 2>/dev/null || true
            echo -e "${GREEN}✅ 后端服务已停止${NC}"
        else
            echo "后端服务未运行"
        fi
        
        # 停止前端服务
        if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "停止前端服务..."
            kill -9 $(lsof -Pi :5173 -sTCP:LISTEN -t) 2>/dev/null || true
            echo -e "${GREEN}✅ 前端服务已停止${NC}"
        else
            echo "前端服务未运行"
        fi
        ;;
        
    0)
        echo "退出"
        exit 0
        ;;
        
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}操作完成${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
