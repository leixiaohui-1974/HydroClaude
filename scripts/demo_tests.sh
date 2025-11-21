#!/bin/bash
# HydroClaude 测试演示脚本
# 展示各种测试场景和用法

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 打印标题
print_title() {
    echo ""
    echo -e "${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
    echo ""
}

# 打印步骤
print_step() {
    echo -e "${YELLOW}[$1] $2${NC}"
}

# 打印成功
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 打印错误
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 暂停
pause() {
    echo ""
    read -p "按 Enter 继续..."
    echo ""
}

# 主菜单
show_menu() {
    clear
    print_title "HydroClaude 测试演示"
    echo "请选择要演示的测试类型："
    echo ""
    echo "  1) 环境检查"
    echo "  2) 后端测试演示"
    echo "  3) 前端测试演示"
    echo "  4) E2E 测试演示"
    echo "  5) 性能测试演示"
    echo "  6) Docker 测试演示"
    echo "  7) 生成测试报告"
    echo "  8) 完整测试流程"
    echo "  0) 退出"
    echo ""
    read -p "请输入选项 (0-8): " choice
    
    case $choice in
        1) demo_environment ;;
        2) demo_backend ;;
        3) demo_frontend ;;
        4) demo_e2e ;;
        5) demo_performance ;;
        6) demo_docker ;;
        7) demo_reports ;;
        8) demo_full ;;
        0) exit 0 ;;
        *) echo "无效选项"; pause; show_menu ;;
    esac
}

# 演示 1: 环境检查
demo_environment() {
    print_title "演示 1: 环境检查"
    
    print_step "1.1" "检查 Python 版本"
    python3 --version
    
    print_step "1.2" "检查 Node.js 版本"
    node --version || echo "Node.js 未安装"
    
    print_step "1.3" "运行完整环境检查"
    python3 tests/test_environment.py || true
    
    print_success "环境检查演示完成"
    pause
    show_menu
}

# 演示 2: 后端测试
demo_backend() {
    print_title "演示 2: 后端测试"
    
    print_step "2.1" "列出所有后端测试文件"
    find tests/backend -name "test_*.py" -type f
    
    print_step "2.2" "运行单个测试文件（商业对标）"
    echo "命令: pytest tests/backend/solvers/test_hydrostatic_commercial.py -v"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        pytest tests/backend/solvers/test_hydrostatic_commercial.py -v || true
    fi
    
    print_step "2.3" "运行所有后端测试（带覆盖率）"
    echo "命令: pytest tests/backend/ -v --cov=solvers --cov=utils --cov-report=term"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        pytest tests/backend/ -v --cov=solvers --cov=utils --cov-report=term || true
    fi
    
    print_success "后端测试演示完成"
    pause
    show_menu
}

# 演示 3: 前端测试
demo_frontend() {
    print_title "演示 3: 前端测试"
    
    print_step "3.1" "列出所有前端测试文件"
    find tests/frontend -name "*.spec.js" -type f
    
    print_step "3.2" "运行响应式测试"
    echo "命令: npx playwright test tests/frontend/responsive.spec.js"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        npx playwright test tests/frontend/responsive.spec.js || true
    fi
    
    print_step "3.3" "运行可访问性测试"
    echo "命令: npx playwright test tests/frontend/accessibility.spec.js"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        npx playwright test tests/frontend/accessibility.spec.js || true
    fi
    
    print_step "3.4" "运行所有前端测试"
    echo "命令: npm run test"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        npm run test || true
    fi
    
    print_success "前端测试演示完成"
    pause
    show_menu
}

# 演示 4: E2E 测试
demo_e2e() {
    print_title "演示 4: E2E 测试"
    
    print_step "4.1" "列出所有 E2E 测试文件"
    find tests/e2e -name "*.spec.js" -type f
    
    print_step "4.2" "运行建模工作流测试（带界面）"
    echo "命令: npx playwright test tests/e2e/modeling-workflow.spec.js --headed"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        npx playwright test tests/e2e/modeling-workflow.spec.js --headed || true
    fi
    
    print_step "4.3" "运行所有 E2E 测试"
    echo "命令: npm run test:e2e"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        npm run test:e2e || true
    fi
    
    print_success "E2E 测试演示完成"
    pause
    show_menu
}

# 演示 5: 性能测试
demo_performance() {
    print_title "演示 5: 性能测试"
    
    print_step "5.1" "检查 Locust 安装"
    locust --version || echo "Locust 未安装"
    
    print_step "5.2" "运行快速性能测试（10用户，30秒）"
    echo "命令: locust -f locustfile.py --host=http://localhost:8000 --headless --users 10 --spawn-rate 2 --run-time 30s"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        echo "注意: 需要后端服务运行在 http://localhost:8000"
        locust -f locustfile.py --host=http://localhost:8000 --headless --users 10 --spawn-rate 2 --run-time 30s || true
    fi
    
    print_step "5.3" "启动 Locust Web UI"
    echo "命令: locust -f locustfile.py --host=http://localhost:8000"
    echo "访问: http://localhost:8089"
    echo ""
    read -p "是否启动? (y/n) " run
    if [ "$run" = "y" ]; then
        echo "按 Ctrl+C 停止 Locust"
        locust -f locustfile.py --host=http://localhost:8000 || true
    fi
    
    print_success "性能测试演示完成"
    pause
    show_menu
}

# 演示 6: Docker 测试
demo_docker() {
    print_title "演示 6: Docker 测试"
    
    print_step "6.1" "检查 Docker 安装"
    docker --version || echo "Docker 未安装"
    docker-compose --version || echo "Docker Compose 未安装"
    
    print_step "6.2" "构建测试镜像"
    echo "命令: docker build -f Dockerfile.test -t hydroclaude:test ."
    echo ""
    read -p "是否构建? (y/n) " run
    if [ "$run" = "y" ]; then
        docker build -f Dockerfile.test -t hydroclaude:test . || true
    fi
    
    print_step "6.3" "启动 Docker Compose 测试环境"
    echo "命令: docker-compose -f docker-compose.test.yml up -d backend"
    echo ""
    read -p "是否启动? (y/n) " run
    if [ "$run" = "y" ]; then
        docker-compose -f docker-compose.test.yml up -d backend || true
        echo "等待服务启动..."
        sleep 5
        docker-compose -f docker-compose.test.yml ps
    fi
    
    print_step "6.4" "运行 Docker 测试"
    echo "命令: docker-compose -f docker-compose.test.yml run test-runner"
    echo ""
    read -p "是否运行? (y/n) " run
    if [ "$run" = "y" ]; then
        docker-compose -f docker-compose.test.yml run test-runner || true
    fi
    
    print_step "6.5" "清理 Docker 环境"
    echo "命令: docker-compose -f docker-compose.test.yml down"
    echo ""
    read -p "是否清理? (y/n) " run
    if [ "$run" = "y" ]; then
        docker-compose -f docker-compose.test.yml down || true
    fi
    
    print_success "Docker 测试演示完成"
    pause
    show_menu
}

# 演示 7: 生成测试报告
demo_reports() {
    print_title "演示 7: 生成测试报告"
    
    print_step "7.1" "生成后端 HTML 报告"
    echo "命令: pytest tests/backend/ --html=reports/html/backend_demo.html --self-contained-html"
    echo ""
    read -p "是否生成? (y/n) " run
    if [ "$run" = "y" ]; then
        pytest tests/backend/ --html=reports/html/backend_demo.html --self-contained-html || true
        print_success "报告已生成: reports/html/backend_demo.html"
    fi
    
    print_step "7.2" "生成覆盖率报告"
    echo "命令: pytest tests/backend/ --cov=. --cov-report=html:reports/coverage/demo"
    echo ""
    read -p "是否生成? (y/n) " run
    if [ "$run" = "y" ]; then
        pytest tests/backend/ --cov=. --cov-report=html:reports/coverage/demo || true
        print_success "覆盖率报告已生成: reports/coverage/demo/index.html"
    fi
    
    print_step "7.3" "生成 Playwright 报告"
    echo "命令: npx playwright show-report"
    echo ""
    read -p "是否查看? (y/n) " run
    if [ "$run" = "y" ]; then
        npx playwright show-report || true
    fi
    
    print_success "测试报告演示完成"
    pause
    show_menu
}

# 演示 8: 完整测试流程
demo_full() {
    print_title "演示 8: 完整测试流程"
    
    echo "这将运行一个完整的测试流程，包括："
    echo "  1. 环境检查"
    echo "  2. 后端测试"
    echo "  3. 前端测试"
    echo "  4. E2E 测试"
    echo "  5. 性能测试"
    echo "  6. 生成报告"
    echo ""
    read -p "是否继续? (y/n) " run
    
    if [ "$run" = "y" ]; then
        print_step "1/6" "环境检查"
        python3 tests/test_environment.py || true
        pause
        
        print_step "2/6" "后端测试"
        pytest tests/backend/ -v || true
        pause
        
        print_step "3/6" "前端测试"
        npm run test || true
        pause
        
        print_step "4/6" "E2E 测试"
        npm run test:e2e || true
        pause
        
        print_step "5/6" "性能测试（快速）"
        locust -f locustfile.py --host=http://localhost:8000 --headless --users 10 --spawn-rate 2 --run-time 30s || true
        pause
        
        print_step "6/6" "生成综合报告"
        pytest tests/backend/ --html=reports/html/full_test_report.html --self-contained-html --cov=. --cov-report=html:reports/coverage/full || true
        
        print_success "完整测试流程完成！"
        echo ""
        echo "查看报告："
        echo "  - HTML 报告: reports/html/full_test_report.html"
        echo "  - 覆盖率报告: reports/coverage/full/index.html"
        echo "  - Playwright 报告: playwright-report/index.html"
    fi
    
    pause
    show_menu
}

# 主程序
main() {
    # 检查是否在项目根目录
    if [ ! -f "pytest.ini" ]; then
        print_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 显示菜单
    show_menu
}

# 运行主程序
main
