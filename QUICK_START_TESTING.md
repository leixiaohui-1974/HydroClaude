# 🚀 HydroClaude 测试快速启动指南

**5分钟开始测试 HydroClaude 项目**

---

## 📋 前置要求

### 必需
- Python 3.9+ (推荐 3.11)
- Node.js 16+ (推荐 18)
- Git

### 可选
- Docker & Docker Compose (用于容器化测试)
- GitHub Account (用于 CI/CD)

---

## ⚡ 快速开始（3步）

### 步骤 1: 安装依赖

#### 方式 A: 使用安装脚本（推荐）⭐
```bash
# 一键安装所有依赖
bash scripts/install_test_deps.sh
```

#### 方式 B: 手动安装
```bash
# Python 依赖
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-html pytest-xdist httpx locust playwright

# Playwright 浏览器
playwright install --with-deps

# Node.js 依赖
npm install
```

### 步骤 2: 检查环境

```bash
# 运行环境检查脚本
python3 tests/test_environment.py
```

**期望输出**：
```
✅ Python 版本符合要求 (>= 3.9)
✅ 所有依赖包已安装
✅ 目录结构完整
✅ 测试覆盖率良好
✅ 所有配置文件已创建
✅ Playwright 已安装
⚠️ API 服务器未运行 (需要启动后端)
```

### 步骤 3: 运行测试

#### 后端测试
```bash
# 运行所有后端测试
pytest tests/backend/ -v

# 运行商业对标测试
pytest tests/backend/solvers/ -v -m commercial

# 生成覆盖率报告
pytest tests/backend/ -v --cov=solvers --cov=utils --cov-report=html
```

#### 前端测试
```bash
# 运行所有前端测试
npm run test

# 运行特定浏览器
npm run test:chromium
npm run test:firefox

# 调试模式
npm run test:debug
```

#### E2E 测试
```bash
# 运行所有 E2E 测试
npm run test:e2e

# 带 UI 模式
npm run test:ui
```

#### 性能测试
```bash
# 启动 Locust Web UI
locust -f locustfile.py --host=http://localhost:8000

# 无头模式（自动化）
locust -f locustfile.py --host=http://localhost:8000 --headless \
       --users 50 --spawn-rate 5 --run-time 60s
```

---

## 🐳 Docker 测试（推荐）

### 快速启动

```bash
# 1. 构建测试镜像
docker build -f Dockerfile.test -t hydroclaude:test .

# 2. 启动完整测试环境
docker-compose -f docker-compose.test.yml up

# 3. 查看测试报告
open reports/html/test_report.html
```

### 单独运行

```bash
# 仅启动后端服务
docker-compose -f docker-compose.test.yml up backend

# 仅运行测试
docker-compose -f docker-compose.test.yml run test-runner

# 启动 Locust 性能测试
docker-compose -f docker-compose.test.yml up locust-master
# 访问 http://localhost:8089
```

---

## 📊 查看测试报告

### HTML 报告
```bash
# 后端测试报告
open reports/html/backend_test_report.html

# API 测试报告
open reports/html/api_test_report.html

# 前端测试报告
open playwright-report/index.html
```

### 覆盖率报告
```bash
# 后端覆盖率
open reports/coverage/index.html

# 前端覆盖率（如果配置）
open reports/coverage/frontend/index.html
```

### 性能报告
```bash
# Locust 报告（运行时）
open http://localhost:8089

# 生成的 HTML 报告
open reports/locust_report.html
```

---

## 🎯 测试场景示例

### 场景 1: 商业对标测试

**目标**: 验证 HydrostaticCanalSolver 精度

```bash
# 运行单个测试文件
pytest tests/backend/solvers/test_hydrostatic_commercial.py -v

# 查看详细输出
pytest tests/backend/solvers/test_hydrostatic_commercial.py -v -s
```

**期望结果**:
- ✅ 均匀流测试通过（误差 < 1%）
- ✅ 非均匀流测试通过（误差 < 2%）
- ✅ 闸门控制测试通过（误差 < 3%）

### 场景 2: 前端响应式测试

**目标**: 验证前端在不同设备上的表现

```bash
# 运行响应式测试
npx playwright test tests/frontend/responsive.spec.js

# 查看截图
open reports/screenshots/responsive-*.png
```

**期望结果**:
- ✅ 桌面端布局正常（1920x1080）
- ✅ 平板端布局自适应（768x1024）
- ✅ 移动端无横向滚动（375x667）

### 场景 3: E2E 建模工作流

**目标**: 验证完整建模流程

```bash
# 运行建模工作流测试
npx playwright test tests/e2e/modeling-workflow.spec.js --headed

# 带截图和追踪
npx playwright test tests/e2e/modeling-workflow.spec.js --trace on
```

**期望结果**:
- ✅ 成功访问建模页面
- ✅ 成功拖拽添加组件
- ✅ 成功配置参数
- ✅ 成功运行模拟
- ✅ 成功查看结果

### 场景 4: API 压力测试

**目标**: 验证 API 性能

```bash
# 运行 50 用户、持续 60 秒的压力测试
locust -f tests/performance/test_api_load.py \
       --host=http://localhost:8000 \
       --headless \
       --users 50 \
       --spawn-rate 5 \
       --run-time 60s \
       --html reports/api_load_report.html
```

**期望结果**:
- ✅ P95 响应时间 < 200ms
- ✅ 错误率 < 1%
- ✅ 吞吐量 > 100 req/s

---

## 🔧 常见问题

### Q1: 提示"python: command not found"
**解决**:
```bash
# 使用 python3
python3 tests/test_environment.py

# 或创建别名
alias python=python3
```

### Q2: pytest 找不到模块
**解决**:
```bash
# 设置 PYTHONPATH
export PYTHONPATH=/workspace:$PYTHONPATH

# 或在项目根目录运行
cd /workspace && pytest tests/
```

### Q3: Playwright 浏览器未安装
**解决**:
```bash
# 安装浏览器
playwright install

# 安装浏览器及系统依赖
playwright install --with-deps
```

### Q4: 端口被占用
**解决**:
```bash
# 查找占用进程
lsof -i :8000
lsof -i :8089

# 杀死进程
kill -9 <PID>

# 或使用不同端口
locust -f locustfile.py --host=http://localhost:8000 --web-port 8090
```

### Q5: Docker 测试失败
**解决**:
```bash
# 清理 Docker 环境
docker-compose -f docker-compose.test.yml down -v

# 重新构建
docker build -f Dockerfile.test -t hydroclaude:test . --no-cache

# 查看日志
docker-compose -f docker-compose.test.yml logs backend
```

---

## 📚 测试文件索引

### 后端测试（8 个）
```
tests/backend/solvers/
├── test_godunov_commercial.py       # Godunov vs HEC-RAS
├── test_hydrostatic_commercial.py   # 静水求解器
├── test_hardycross_commercial.py    # 管网求解器
├── test_waterhammer_commercial.py   # 水锤求解器
└── test_multi_structure.py          # 多结构测试

tests/backend/api/
├── test_knowledge_api.py            # 知识库 API
└── test_additional_apis.py          # 其他 API
```

### 前端测试（8 个）
```
tests/frontend/
├── homepage.spec.js                 # 首页测试
├── modeling.spec.js                 # 建模测试
├── visualization.spec.js            # 可视化测试
├── form-submission.spec.js          # 表单测试
├── responsive.spec.js               # 响应式测试
├── accessibility.spec.js            # 可访问性测试
├── visual-regression.spec.js        # 视觉回归测试
└── performance.spec.js              # 前端性能测试
```

### E2E 测试（6 个）
```
tests/e2e/
├── modeling-workflow.spec.js        # 建模工作流
├── case-execution.spec.js           # 案例运行
├── results-visualization.spec.js    # 结果可视化
├── data-import-export.spec.js       # 数据导入导出
├── user-authentication.spec.js      # 用户认证
└── multi-page-navigation.spec.js    # 多页面导航
```

---

## 🎓 进阶使用

### 并行测试
```bash
# pytest 并行（使用 pytest-xdist）
pytest tests/backend/ -v -n auto

# Playwright 并行
npx playwright test --workers=4
```

### 测试覆盖率
```bash
# 后端覆盖率
pytest tests/backend/ --cov=. --cov-report=term --cov-report=html

# 查看详细覆盖率
open reports/coverage/index.html
```

### 自定义测试标记
```bash
# 运行商业对标测试
pytest -v -m commercial

# 运行快速测试
pytest -v -m "not slow"

# 运行特定标记
pytest -v -m "api or solver"
```

### 生成测试报告
```bash
# HTML 报告
pytest tests/backend/ --html=reports/custom_report.html --self-contained-html

# JUnit XML（CI/CD）
pytest tests/backend/ --junitxml=reports/junit.xml

# Allure 报告（高级）
pytest tests/backend/ --alluredir=reports/allure-results
allure serve reports/allure-results
```

---

## 📖 相关文档

- **详细文档**: `⭐_按规范开发_最终成果_Phase1-6.md`
- **完成报告**: `✅_按规范开发_100%完成.md`
- **测试报告**: `reports/comprehensive_test_report.md`
- **性能测试**: `tests/performance/README.md`
- **CI/CD 配置**: `.github/workflows/test.yml`

---

## 🎯 推荐测试流程

### 每日开发
```bash
# 1. 快速检查
python3 tests/test_environment.py

# 2. 运行相关测试
pytest tests/backend/solvers/test_hydrostatic_commercial.py -v

# 3. 前端快速测试
npm run test:chromium -- --grep="首页"
```

### 提交前
```bash
# 1. 运行所有后端测试
pytest tests/backend/ -v

# 2. 运行所有前端测试
npm run test

# 3. 检查代码质量
flake8 .
black --check .
```

### 发布前
```bash
# 1. 完整测试套件
pytest tests/ -v --cov=. --cov-report=html

# 2. E2E 测试
npm run test:e2e

# 3. 性能测试
locust -f locustfile.py --host=http://localhost:8000 --headless \
       --users 100 --spawn-rate 10 --run-time 300s

# 4. Docker 测试
docker-compose -f docker-compose.test.yml up test-runner
```

---

## ✅ 下一步

1. ⏳ 运行 `python3 tests/test_environment.py` 检查环境
2. ⏳ 运行 `bash scripts/install_test_deps.sh` 安装依赖
3. ⏳ 运行 `pytest tests/backend/ -v` 测试后端
4. ⏳ 运行 `npm run test` 测试前端
5. ⏳ 查看报告 `open reports/html/test_report.html`

---

**Happy Testing! 🎉**

Generated by HydroClaude Test Team
Date: 2025-11-20
