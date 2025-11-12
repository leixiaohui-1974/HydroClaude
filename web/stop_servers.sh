#!/bin/bash
# HydroClaude Web 服务停止脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}停止 HydroClaude Web 服务${NC}"
echo -e "${BLUE}================================${NC}\n"

# 停止后端
echo -e "${YELLOW}[1/2] 停止后端服务...${NC}"
if [ -f /tmp/hydroclaude_backend.pid ]; then
    BACKEND_PID=$(cat /tmp/hydroclaude_backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✅ 后端服务已停止 (PID: $BACKEND_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  后端进程不存在${NC}"
    fi
    rm /tmp/hydroclaude_backend.pid
else
    # 尝试通过进程名停止
    pkill -f "python3 main.py" 2>/dev/null && echo -e "${GREEN}✅ 后端服务已停止${NC}" || echo -e "${YELLOW}⚠️  未找到后端进程${NC}"
fi

# 停止前端
echo -e "\n${YELLOW}[2/2] 停止前端服务...${NC}"
if [ -f /tmp/hydroclaude_frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/hydroclaude_frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✅ 前端服务已停止 (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  前端进程不存在${NC}"
    fi
    rm /tmp/hydroclaude_frontend.pid
else
    # 尝试通过进程名停止
    pkill -f "vite" 2>/dev/null && echo -e "${GREEN}✅ 前端服务已停止${NC}" || echo -e "${YELLOW}⚠️  未找到前端进程${NC}"
fi

# 清理端口
echo -e "\n${YELLOW}清理端口占用...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}所有服务已停止${NC}"
echo -e "${GREEN}================================${NC}\n"
