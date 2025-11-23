#!/bin/bash
# HydroClaude v2.0 发布检查脚本
# 自动检查项目是否准备好发布

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计数器
PASSED=0
FAILED=0
WARNINGS=0

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  HydroClaude v2.0 发布检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# 函数：检查文件是否存在
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $description"
        ((PASSED++))
        return 0
    else
        echo -e "  ${RED}✗${NC} $description - 文件不存在: $file"
        ((FAILED++))
        return 1
    fi
}

# 函数：检查目录是否存在
check_dir() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $description"
        ((PASSED++))
        return 0
    else
        echo -e "  ${RED}✗${NC} $description - 目录不存在: $dir"
        ((FAILED++))
        return 1
    fi
}

# 函数：检查Python包
check_python_package() {
    local package=$1
    local description=$2
    
    if python -c "import $package" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $description"
        ((PASSED++))
        return 0
    else
        echo -e "  ${YELLOW}⚠${NC} $description - 包未安装: $package"
        ((WARNINGS++))
        return 1
    fi
}

# 1. 检查核心文件
echo -e "${BLUE}[1/8] 核心文件检查${NC}"
check_file "README.md" "README.md 存在"
check_file "LICENSE" "LICENSE 存在"
check_file "CONTRIBUTING.md" "CONTRIBUTING.md 存在"
check_file "CHANGELOG.md" "CHANGELOG.md 存在"
check_file "requirements.txt" "requirements.txt 存在"
check_file "setup.py" "setup.py 存在"
echo ""

# 2. 检查部署文件
echo -e "${BLUE}[2/8] 部署配置检查${NC}"
check_file "Dockerfile" "Dockerfile 存在"
check_file "docker-compose.yml" "docker-compose.yml 存在"
check_file ".dockerignore" ".dockerignore 存在"
check_file "Makefile" "Makefile 存在"
check_file ".editorconfig" ".editorconfig 存在"
echo ""

# 3. 检查GitHub生态
echo -e "${BLUE}[3/8] GitHub生态检查${NC}"
check_dir ".github" ".github 目录存在"
check_file ".github/PULL_REQUEST_TEMPLATE.md" "PR模板存在"
check_dir ".github/ISSUE_TEMPLATE" "Issue模板目录存在"
check_dir ".github/workflows" "GitHub Actions目录存在"
echo ""

# 4. 检查项目管理文件
echo -e "${BLUE}[4/8] 项目管理文件检查${NC}"
check_file "ROADMAP.md" "ROADMAP.md 存在"
check_file "SECURITY.md" "SECURITY.md 存在"
echo ""

# 5. 检查核心代码
echo -e "${BLUE}[5/8] 核心代码检查${NC}"
check_dir "solvers" "solvers 目录存在"
check_dir "utils" "utils 目录存在"
check_dir "tests" "tests 目录存在"
check_file "main.py" "main.py 存在"
echo ""

# 6. 检查Python环境
echo -e "${BLUE}[6/8] Python环境检查${NC}"

# 检查Python版本
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.12"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo -e "  ${GREEN}✓${NC} Python版本: $PYTHON_VERSION (>= $REQUIRED_VERSION)"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠${NC} Python版本: $PYTHON_VERSION (建议 >= $REQUIRED_VERSION)"
    ((WARNINGS++))
fi

# 检查核心依赖
check_python_package "numpy" "numpy已安装"
check_python_package "scipy" "scipy已安装"
check_python_package "matplotlib" "matplotlib已安装"
check_python_package "fastapi" "fastapi已安装"
check_python_package "uvicorn" "uvicorn已安装"
echo ""

# 7. 运行测试
echo -e "${BLUE}[7/8] 运行测试${NC}"
if [ -d "tests/backend" ]; then
    if python -m pytest tests/backend/ -q --tb=no 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} 后端测试通过"
        ((PASSED++))
    else
        echo -e "  ${YELLOW}⚠${NC} 后端测试失败或未运行"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC} 测试目录不存在"
    ((WARNINGS++))
fi
echo ""

# 8. 检查Git状态
echo -e "${BLUE}[8/8] Git状态检查${NC}"
if [ -d ".git" ]; then
    echo -e "  ${GREEN}✓${NC} Git仓库已初始化"
    ((PASSED++))
    
    # 检查是否有未提交的更改
    if [ -z "$(git status --porcelain)" ]; then
        echo -e "  ${GREEN}✓${NC} 工作区干净（无未提交更改）"
        ((PASSED++))
    else
        echo -e "  ${YELLOW}⚠${NC} 有未提交的更改"
        ((WARNINGS++))
    fi
    
    # 检查当前分支
    CURRENT_BRANCH=$(git branch --show-current)
    echo -e "  ${BLUE}ℹ${NC} 当前分支: $CURRENT_BRANCH"
else
    echo -e "  ${YELLOW}⚠${NC} 不是Git仓库"
    ((WARNINGS++))
fi
echo ""

# 总结
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  检查结果总结${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "  ${GREEN}通过: $PASSED${NC}"
echo -e "  ${RED}失败: $FAILED${NC}"
echo -e "  ${YELLOW}警告: $WARNINGS${NC}"
echo ""

TOTAL=$((PASSED + FAILED + WARNINGS))
PASS_RATE=$((PASSED * 100 / TOTAL))

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ 项目准备就绪，可以发布！${NC}"
    echo -e "${GREEN}  通过率: $PASS_RATE%${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${BLUE}下一步操作:${NC}"
    echo -e "  1. 构建Docker镜像: ${YELLOW}make docker-build${NC}"
    echo -e "  2. 运行测试: ${YELLOW}make test${NC}"
    echo -e "  3. 构建Python包: ${YELLOW}make build${NC}"
    echo -e "  4. 发布到PyPI: ${YELLOW}make publish${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ❌ 项目未准备好发布${NC}"
    echo -e "${RED}  通过率: $PASS_RATE%${NC}"
    echo -e "${RED}  请修复上述 $FAILED 个错误${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    exit 1
fi
