#!/bin/bash
# HydroClaude Web 服务启动脚本
# 同时启动后端和前端服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}HydroClaude Web 服务启动${NC}"
echo -e "${BLUE}================================${NC}\n"

# 检查是否在web目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ 错误: 请在 /workspace/web 目录下运行此脚本${NC}"
    exit 1
fi

# 1. 启动后端服务
echo -e "${YELLOW}[1/2] 启动后端API服务器...${NC}"

# 检查后端端口是否被占用
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  端口8000已被占用，尝试停止...${NC}"
    pkill -f "python3 main.py" 2>/dev/null || true
    sleep 2
fi

# 启动后端
cd backend/api_gateway
nohup python3 main.py > /tmp/hydroclaude_backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

echo -e "${GREEN}✅ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
echo -e "   日志文件: /tmp/hydroclaude_backend.log"

# 等待后端启动
echo -e "${YELLOW}   等待后端就绪...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}   后端服务就绪！${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 10 ]; then
        echo -e "${RED}   后端启动超时，请检查日志${NC}"
        cat /tmp/hydroclaude_backend.log | tail -20
        exit 1
    fi
done

# 2. 启动前端服务
echo -e "\n${YELLOW}[2/2] 启动前端开发服务器...${NC}"

# 检查前端依赖
cd frontend
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  前端依赖未安装，正在安装...${NC}"
    npm install
fi

# 检查前端端口
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  端口5173已被占用，尝试停止...${NC}"
    pkill -f "vite" 2>/dev/null || true
    sleep 2
fi

# 启动前端
echo -e "${YELLOW}   启动Vite开发服务器...${NC}"
nohup npm run dev > /tmp/hydroclaude_frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}✅ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
echo -e "   日志文件: /tmp/hydroclaude_frontend.log"

# 等待前端启动
echo -e "${YELLOW}   等待前端就绪...${NC}"
sleep 5

# 3. 显示访问信息
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}🎉 所有服务启动成功！${NC}"
echo -e "${GREEN}================================${NC}\n"

echo -e "${BLUE}📍 访问地址:${NC}"
echo -e "   ${GREEN}前端应用:${NC} http://localhost:5173"
echo -e "   ${GREEN}后端API:${NC}  http://localhost:8000"
echo -e "   ${GREEN}API文档:${NC}  http://localhost:8000/api/docs\n"

echo -e "${BLUE}📋 进程信息:${NC}"
echo -e "   后端PID: $BACKEND_PID"
echo -e "   前端PID: $FRONTEND_PID\n"

echo -e "${BLUE}📝 日志文件:${NC}"
echo -e "   后端: /tmp/hydroclaude_backend.log"
echo -e "   前端: /tmp/hydroclaude_frontend.log\n"

echo -e "${YELLOW}💡 提示:${NC}"
echo -e "   - 在浏览器打开: ${GREEN}http://localhost:5173${NC}"
echo -e "   - 查看后端日志: ${BLUE}tail -f /tmp/hydroclaude_backend.log${NC}"
echo -e "   - 查看前端日志: ${BLUE}tail -f /tmp/hydroclaude_frontend.log${NC}"
echo -e "   - 停止服务: ${RED}kill $BACKEND_PID $FRONTEND_PID${NC}\n"

echo -e "${BLUE}📖 测试指南:${NC}"
echo -e "   查看完整测试步骤: ${GREEN}BROWSER_TESTING_GUIDE.md${NC}\n"

# 保存PID到文件
echo "$BACKEND_PID" > /tmp/hydroclaude_backend.pid
echo "$FRONTEND_PID" > /tmp/hydroclaude_frontend.pid

echo -e "${GREEN}准备就绪，可以开始测试了！${NC}\n"
