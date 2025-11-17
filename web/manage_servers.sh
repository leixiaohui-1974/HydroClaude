#!/bin/bash
# HydroClaude 服务器管理脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 工作目录
BACKEND_DIR="/workspace/web/backend"
WEB_DIR="/workspace/web"

# PID文件
BACKEND_PID_FILE="/tmp/hydroclaude_backend.pid"
FRONTEND_PID_FILE="/tmp/hydroclaude_frontend.pid"

# 打印标题
print_header() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║          🚀 HydroClaude 服务器管理工具                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
}

# 检查服务器状态
check_status() {
    echo -e "${BLUE}📊 检查服务器状态...${NC}"
    echo ""
    
    # 检查后端
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  后端API:     ${GREEN}✅ 运行中${NC} (http://localhost:8000)"
        BACKEND_RUNNING=1
    else
        echo -e "  后端API:     ${RED}❌ 未运行${NC}"
        BACKEND_RUNNING=0
    fi
    
    # 检查前端
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        echo -e "  前端服务:    ${GREEN}✅ 运行中${NC} (http://localhost:8080)"
        FRONTEND_RUNNING=1
    else
        echo -e "  前端服务:    ${RED}❌ 未运行${NC}"
        FRONTEND_RUNNING=0
    fi
    
    echo ""
}

# 启动后端服务器
start_backend() {
    echo -e "${BLUE}🔄 启动后端服务器...${NC}"
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  后端服务器已在运行${NC}"
        return 0
    fi
    
    cd "$BACKEND_DIR"
    nohup python3 start_server_working.py > /tmp/hydroclaude_backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$BACKEND_PID_FILE"
    
    # 等待启动
    echo -e "  等待服务器启动..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 后端服务器启动成功！${NC}"
            echo -e "   PID: $BACKEND_PID"
            echo -e "   地址: http://localhost:8000"
            echo -e "   文档: http://localhost:8000/docs"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}❌ 后端服务器启动失败${NC}"
    echo -e "   查看日志: tail -f /tmp/hydroclaude_backend.log"
    return 1
}

# 启动前端服务器
start_frontend() {
    echo -e "${BLUE}🔄 启动前端服务器...${NC}"
    
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  前端服务器已在运行${NC}"
        return 0
    fi
    
    cd "$WEB_DIR"
    nohup python3 -m http.server 8080 > /tmp/hydroclaude_frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$FRONTEND_PID_FILE"
    
    # 等待启动
    sleep 2
    
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 前端服务器启动成功！${NC}"
        echo -e "   PID: $FRONTEND_PID"
        echo -e "   地址: http://localhost:8080"
        echo -e "   页面:"
        echo -e "     • 集成测试: http://localhost:8080/frontend_integration_test.html"
        echo -e "     • 监控仪表盘: http://localhost:8080/frontend_dashboard.html"
        echo -e "     • Web演示应用: http://localhost:8080/demo_webapp.html"
        return 0
    else
        echo -e "${RED}❌ 前端服务器启动失败${NC}"
        return 1
    fi
}

# 停止服务器
stop_servers() {
    echo -e "${BLUE}🛑 停止服务器...${NC}"
    
    # 停止后端
    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat "$BACKEND_PID_FILE")
        if kill -0 $BACKEND_PID 2>/dev/null; then
            kill $BACKEND_PID
            echo -e "  ${GREEN}✅ 后端服务器已停止${NC} (PID: $BACKEND_PID)"
            rm "$BACKEND_PID_FILE"
        fi
    else
        # 查找并杀死进程
        PIDS=$(ps aux | grep 'start_server_working.py' | grep -v grep | awk '{print $2}')
        if [ ! -z "$PIDS" ]; then
            echo "$PIDS" | xargs kill 2>/dev/null
            echo -e "  ${GREEN}✅ 后端服务器已停止${NC}"
        fi
    fi
    
    # 停止前端
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            kill $FRONTEND_PID
            echo -e "  ${GREEN}✅ 前端服务器已停止${NC} (PID: $FRONTEND_PID)"
            rm "$FRONTEND_PID_FILE"
        fi
    else
        # 查找并杀死进程
        PIDS=$(ps aux | grep 'http.server 8080' | grep -v grep | awk '{print $2}')
        if [ ! -z "$PIDS" ]; then
            echo "$PIDS" | xargs kill 2>/dev/null
            echo -e "  ${GREEN}✅ 前端服务器已停止${NC}"
        fi
    fi
    
    echo ""
}

# 重启服务器
restart_servers() {
    echo -e "${BLUE}🔄 重启服务器...${NC}"
    echo ""
    stop_servers
    sleep 2
    start_backend
    echo ""
    start_frontend
}

# 查看日志
view_logs() {
    echo -e "${BLUE}📋 服务器日志${NC}"
    echo ""
    echo "后端日志: /tmp/hydroclaude_backend.log"
    echo "前端日志: /tmp/hydroclaude_frontend.log"
    echo ""
    echo "查看实时日志:"
    echo "  tail -f /tmp/hydroclaude_backend.log"
    echo "  tail -f /tmp/hydroclaude_frontend.log"
    echo ""
}

# 运行测试
run_tests() {
    echo -e "${BLUE}🧪 运行测试...${NC}"
    echo ""
    
    cd "$WEB_DIR"
    
    echo "选择测试类型:"
    echo "  1) API测试 (17个端点)"
    echo "  2) 压力测试"
    echo "  3) 场景测试"
    echo "  4) 端到端测试"
    echo "  5) 全部测试"
    echo ""
    read -p "请选择 (1-5): " choice
    
    case $choice in
        1)
            python3 complete_api_test.py
            ;;
        2)
            python3 stress_test.py
            ;;
        3)
            python3 real_world_scenarios_test.py
            ;;
        4)
            python3 automated_e2e_test.py
            ;;
        5)
            echo "运行全部测试..."
            python3 complete_api_test.py
            echo ""
            python3 stress_test.py
            echo ""
            python3 real_world_scenarios_test.py
            echo ""
            python3 automated_e2e_test.py
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            ;;
    esac
}

# 显示菜单
show_menu() {
    print_header
    check_status
    
    echo "请选择操作:"
    echo ""
    echo "  1) 启动所有服务器"
    echo "  2) 停止所有服务器"
    echo "  3) 重启所有服务器"
    echo "  4) 查看服务器状态"
    echo "  5) 查看日志"
    echo "  6) 运行测试"
    echo "  7) 打开Web界面"
    echo "  0) 退出"
    echo ""
    read -p "请选择 (0-7): " choice
    
    case $choice in
        1)
            echo ""
            start_backend
            echo ""
            start_frontend
            ;;
        2)
            echo ""
            stop_servers
            ;;
        3)
            echo ""
            restart_servers
            ;;
        4)
            # 状态已在菜单显示
            ;;
        5)
            echo ""
            view_logs
            ;;
        6)
            echo ""
            run_tests
            ;;
        7)
            echo ""
            echo -e "${BLUE}🌐 Web界面地址:${NC}"
            echo ""
            echo "  集成测试:    http://localhost:8080/frontend_integration_test.html"
            echo "  监控仪表盘:  http://localhost:8080/frontend_dashboard.html"
            echo "  Web演示应用: http://localhost:8080/demo_webapp.html"
            echo "  API文档:     http://localhost:8000/docs"
            echo ""
            ;;
        0)
            echo ""
            echo "再见！"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            ;;
    esac
    
    echo ""
    read -p "按Enter键继续..."
}

# 主循环
main() {
    # 检查是否在正确的目录
    if [ ! -d "$BACKEND_DIR" ]; then
        echo -e "${RED}错误: 找不到后端目录${NC}"
        exit 1
    fi
    
    # 如果有参数，直接执行命令
    if [ $# -gt 0 ]; then
        case $1 in
            start)
                start_backend
                echo ""
                start_frontend
                ;;
            stop)
                stop_servers
                ;;
            restart)
                restart_servers
                ;;
            status)
                check_status
                ;;
            *)
                echo "用法: $0 {start|stop|restart|status}"
                exit 1
                ;;
        esac
        exit 0
    fi
    
    # 交互式菜单
    while true; do
        show_menu
    done
}

# 运行主程序
main "$@"
