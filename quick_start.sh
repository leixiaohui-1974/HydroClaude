#!/bin/bash
# HydroClaude v2.0 一键启动脚本
# 最简单的方式开始使用HydroClaude

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

clear

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              HydroClaude v2.0.0 一键启动                         ║
║                                                                  ║
║              世界级水力学仿真平台                                 ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

# 显示欢迎信息
echo -e "${GREEN}欢迎使用 HydroClaude！${NC}"
echo -e "${BLUE}这个脚本将帮助你快速开始使用本平台。${NC}\n"

# 检测操作系统
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi

echo -e "${CYAN}检测到的操作系统: ${BOLD}$OS${NC}\n"

# 检查依赖
echo -e "${YELLOW}[1/5] 检查依赖...${NC}"

# 检查Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "  ${GREEN}✓${NC} Docker 已安装: $DOCKER_VERSION"
    HAS_DOCKER=true
else
    echo -e "  ${RED}✗${NC} Docker 未安装"
    HAS_DOCKER=false
fi

# 检查Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "  ${GREEN}✓${NC} Python 已安装: $PYTHON_VERSION"
    HAS_PYTHON=true
else
    echo -e "  ${RED}✗${NC} Python 未安装"
    HAS_PYTHON=false
fi

# 检查Make
if command -v make &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Make 已安装"
    HAS_MAKE=true
else
    echo -e "  ${YELLOW}⚠${NC} Make 未安装（可选）"
    HAS_MAKE=false
fi

echo ""

# 选择启动方式
echo -e "${YELLOW}[2/5] 选择启动方式${NC}\n"

if [ "$HAS_DOCKER" = true ] && [ "$HAS_MAKE" = true ]; then
    echo -e "${BOLD}推荐方式：${NC}"
    echo -e "  ${GREEN}1)${NC} Docker + Make（一键启动，最简单）${BOLD} ⭐推荐${NC}"
    echo -e "\n${BOLD}其他方式：${NC}"
    echo -e "  ${GREEN}2)${NC} Docker命令（手动启动）"
    echo -e "  ${GREEN}3)${NC} Python本地运行（开发模式）"
    echo -e "  ${GREEN}4)${NC} 仅安装依赖（稍后手动启动）"
    echo -e "  ${GREEN}5)${NC} 运行演示脚本"
    echo -e "  ${GREEN}6)${NC} 检查发布准备"
    echo -e "  ${GREEN}0)${NC} 退出\n"
    
    read -p "请选择 [1-6，0退出]: " choice
elif [ "$HAS_DOCKER" = true ]; then
    echo -e "  ${GREEN}1)${NC} Docker命令启动"
    echo -e "  ${GREEN}2)${NC} 仅安装依赖"
    echo -e "  ${GREEN}0)${NC} 退出\n"
    
    read -p "请选择 [1-2，0退出]: " choice
    case $choice in
        1) choice=2;;
        2) choice=4;;
        0) choice=0;;
    esac
elif [ "$HAS_PYTHON" = true ]; then
    echo -e "  ${GREEN}1)${NC} Python本地运行"
    echo -e "  ${GREEN}2)${NC} 仅安装依赖"
    echo -e "  ${GREEN}0)${NC} 退出\n"
    
    read -p "请选择 [1-2，0退出]: " choice
    case $choice in
        1) choice=3;;
        2) choice=4;;
        0) choice=0;;
    esac
else
    echo -e "${RED}错误：未检测到Docker或Python，无法启动！${NC}"
    echo -e "${YELLOW}请先安装Docker或Python 3.12+${NC}\n"
    exit 1
fi

echo ""

# 执行选择的操作
case $choice in
    1)
        # Docker + Make 启动
        echo -e "${YELLOW}[3/5] 使用Docker + Make启动...${NC}\n"
        
        echo -e "${CYAN}步骤1: 构建Docker镜像${NC}"
        make docker-build
        
        echo -e "\n${CYAN}步骤2: 启动Docker容器${NC}"
        make docker-up
        
        echo -e "\n${GREEN}✓ 启动成功！${NC}\n"
        
        echo -e "${YELLOW}[4/5] 访问信息${NC}"
        echo -e "  • 后端API: ${CYAN}http://localhost:8000${NC}"
        echo -e "  • API文档: ${CYAN}http://localhost:8000/docs${NC}"
        echo -e "  • 健康检查: ${CYAN}http://localhost:8000/health${NC}\n"
        
        echo -e "${YELLOW}[5/5] 常用命令${NC}"
        echo -e "  • 查看日志: ${CYAN}make docker-logs${NC}"
        echo -e "  • 停止服务: ${CYAN}make docker-down${NC}"
        echo -e "  • 运行测试: ${CYAN}make test${NC}"
        echo -e "  • 查看帮助: ${CYAN}make help${NC}\n"
        ;;
    
    2)
        # Docker 命令启动
        echo -e "${YELLOW}[3/5] 使用Docker命令启动...${NC}\n"
        
        echo -e "${CYAN}步骤1: 构建Docker镜像${NC}"
        docker build -t hydroclaude:2.0.0 .
        
        echo -e "\n${CYAN}步骤2: 启动Docker容器${NC}"
        docker run -d -p 8000:8000 --name hydroclaude hydroclaude:2.0.0
        
        echo -e "\n${GREEN}✓ 启动成功！${NC}\n"
        
        echo -e "${YELLOW}[4/5] 访问信息${NC}"
        echo -e "  • 后端API: ${CYAN}http://localhost:8000${NC}"
        echo -e "  • API文档: ${CYAN}http://localhost:8000/docs${NC}\n"
        
        echo -e "${YELLOW}[5/5] 常用命令${NC}"
        echo -e "  • 查看日志: ${CYAN}docker logs -f hydroclaude${NC}"
        echo -e "  • 停止服务: ${CYAN}docker stop hydroclaude${NC}"
        echo -e "  • 删除容器: ${CYAN}docker rm hydroclaude${NC}\n"
        ;;
    
    3)
        # Python 本地运行
        echo -e "${YELLOW}[3/5] Python本地运行...${NC}\n"
        
        echo -e "${CYAN}步骤1: 安装依赖${NC}"
        if [ -f "requirements.txt" ]; then
            pip3 install -r requirements.txt
        else
            echo -e "${RED}错误：requirements.txt 不存在${NC}"
            exit 1
        fi
        
        echo -e "\n${CYAN}步骤2: 启动应用${NC}"
        echo -e "${YELLOW}正在启动...按 Ctrl+C 停止${NC}\n"
        python3 main.py
        ;;
    
    4)
        # 仅安装依赖
        echo -e "${YELLOW}[3/5] 安装依赖...${NC}\n"
        
        read -p "安装开发依赖吗？[y/N]: " install_dev
        
        if [[ $install_dev =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}安装开发依赖...${NC}"
            pip3 install -r requirements-dev.txt
        else
            echo -e "${CYAN}安装生产依赖...${NC}"
            pip3 install -r requirements.txt
        fi
        
        echo -e "\n${GREEN}✓ 依赖安装完成！${NC}\n"
        
        echo -e "${YELLOW}[4/5] 下一步${NC}"
        echo -e "  • 启动应用: ${CYAN}python3 main.py${NC}"
        echo -e "  • 或使用Make: ${CYAN}make run${NC}"
        echo -e "  • 运行测试: ${CYAN}pytest tests/backend/${NC}\n"
        
        echo -e "${YELLOW}[5/5] 文档${NC}"
        echo -e "  • 快速开始: ${CYAN}cat ⭐_START_HERE.md${NC}"
        echo -e "  • 用户手册: ${CYAN}cat 📖_用户使用手册.md${NC}\n"
        ;;
    
    5)
        # 运行演示脚本
        echo -e "${YELLOW}[3/5] 启动演示脚本...${NC}\n"
        
        if [ -f "demo.sh" ]; then
            chmod +x demo.sh
            ./demo.sh
        else
            echo -e "${RED}错误：demo.sh 不存在${NC}"
            exit 1
        fi
        ;;
    
    6)
        # 检查发布准备
        echo -e "${YELLOW}[3/5] 运行发布检查...${NC}\n"
        
        if [ -f "check_release.sh" ]; then
            chmod +x check_release.sh
            ./check_release.sh
        else
            echo -e "${RED}错误：check_release.sh 不存在${NC}"
            exit 1
        fi
        ;;
    
    0)
        echo -e "${YELLOW}退出${NC}\n"
        exit 0
        ;;
    
    *)
        echo -e "${RED}无效选项${NC}\n"
        exit 1
        ;;
esac

# 最终提示
if [ $choice -ne 5 ] && [ $choice -ne 6 ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}启动完成！${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${YELLOW}更多信息：${NC}"
    echo -e "  • 项目文档: ${CYAN}cat 🎯_HydroClaude_终极导航指南.md${NC}"
    echo -e "  • 快速参考: ${CYAN}cat 🎯_快速参考卡片.txt${NC}"
    echo -e "  • 运行演示: ${CYAN}./demo.sh${NC}"
    echo -e "  • 检查发布: ${CYAN}./check_release.sh${NC}\n"
    
    echo -e "${GREEN}感谢使用 HydroClaude！${NC}\n"
fi
