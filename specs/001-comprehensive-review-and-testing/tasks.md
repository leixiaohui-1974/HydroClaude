# 任务列表：HydroClaude 全面审查与商业级测试

**Tasks Version**: 1.0  
**Created**: 2025-11-20  
**Based on Plan**: 001-comprehensive-review-and-testing/plan.md  
**Status**: Ready for Implementation

---

## 📋 任务概览

**总任务数**: 45  
**预计工时**: 80-100 小时  
**并行任务**: 标记为 [P] 的任务可以并行执行  
**优先级**: P0 (高) > P1 (中) > P2 (低)

---

## Phase 1: 基础设施准备 (Tasks 1-8)

### [P0] Task 1: 创建测试目录结构
**预计时间**: 0.5小时  
**依赖**: 无  
**可并行**: ✅

```bash
# 创建目录
mkdir -p tests/{backend,frontend,e2e,performance,fixtures,utils}
mkdir -p tests/backend/{api,solvers,integration}
mkdir -p tests/frontend/{pages,components,visual}
mkdir -p reports/{html,screenshots,baseline}
```

**验收标准**:
- [ ] 所有目录创建成功
- [ ] README.md 文件在每个目录下
- [ ] .gitkeep 文件确保空目录被跟踪

---

### [P0] Task 2: 安装测试依赖
**预计时间**: 1小时  
**依赖**: Task 1  
**可并行**: ✅

创建 `requirements_test.txt`:
```txt
# 测试框架
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-html==4.1.1
pytest-xdist==3.5.0

# API测试
httpx==0.25.2
faker==20.1.0

# 浏览器自动化
playwright==1.40.0
pytest-playwright==0.4.3

# 图像处理
Pillow==10.1.0
opencv-python==4.8.1.78

# 性能测试
locust==2.18.3

# 报告生成
allure-pytest==2.13.2
```

**执行命令**:
```bash
pip install -r requirements_test.txt
playwright install chromium firefox
```

**验收标准**:
- [ ] 所有包安装成功
- [ ] `pytest --version` 可执行
- [ ] `playwright --version` 可执行
- [ ] 浏览器下载完成

---

### [P0] Task 3: 配置 pytest.ini
**预计时间**: 0.5小时  
**依赖**: Task 2  
**可并行**: ✅

创建 `/workspace/pytest.ini`:
```ini
[pytest]
pythonpath = . web/backend solvers utils
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test* *Tests
python_functions = test_*

addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=solvers
    --cov=web/backend
    --cov=utils
    --cov-report=html:reports/html/coverage
    --cov-report=term-missing
    --html=reports/html/pytest_report.html
    --self-contained-html
    -n auto

markers =
    backend: Backend API and solver tests
    frontend: Frontend UI tests
    e2e: End-to-end workflow tests
    performance: Performance and load tests
    commercial: Commercial software comparison
    smoke: Quick smoke tests
    slow: Tests that take > 5 seconds

asyncio_mode = auto
```

**验收标准**:
- [ ] pytest 配置文件创建
- [ ] `pytest --co -q` 可运行
- [ ] 标记定义正确

---

### [P] Task 4: 创建测试 Fixtures
**预计时间**: 2小时  
**依赖**: Task 3  
**可并行**: ✅

创建 `tests/conftest.py`:
```python
import pytest
import asyncio
from httpx import AsyncClient
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def api_client():
    """API测试客户端"""
    async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        yield client

@pytest.fixture(scope="session")
def screenshot_path():
    """截图保存路径"""
    path = Path("reports/screenshots")
    path.mkdir(parents=True, exist_ok=True)
    return str(path)

@pytest.fixture(scope="session")
def baseline_path():
    """基准图像路径"""
    path = Path("reports/baseline")
    path.mkdir(parents=True, exist_ok=True)
    return str(path)
```

**验收标准**:
- [ ] Fixtures 定义完整
- [ ] 路径自动创建
- [ ] 异步支持正常

---

### [P] Task 5: 准备标准测试数据
**预计时间**: 3小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/fixtures/standard_cases.py` (见 plan.md)

**测试数据包括**:
- HEC-RAS 恒定流案例
- MIKE 11 溃坝案例
- EPANET 管网案例
- 典型边界条件组合
- 异常输入数据

**验收标准**:
- [ ] 至少 5 个标准算例
- [ ] 每个案例有预期结果
- [ ] 容差定义合理
- [ ] 文档说明完整

---

### [P0] Task 6: 配置 Docker 测试环境
**预计时间**: 2小时  
**依赖**: Task 2  
**可并行**: ✅

创建 `Dockerfile.test`:
```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    chromium \
    firefox-esr \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements_test.txt .
RUN pip install --no-cache-dir -r requirements_test.txt
RUN playwright install-deps
RUN playwright install chromium firefox

COPY . .

CMD ["pytest", "-v"]
```

创建 `docker-compose.test.yml`:
```yaml
version: '3.8'

services:
  backend:
    build: ./web/backend
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    command: python main.py
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
  
  frontend:
    build: ./web/frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - REACT_APP_API_URL=http://backend:8000
  
  test:
    build:
      context: .
      dockerfile: Dockerfile.test
    depends_on:
      backend:
        condition: service_healthy
    volumes:
      - ./reports:/app/reports
    command: pytest --html=/app/reports/report.html
```

**验收标准**:
- [ ] Docker 镜像构建成功
- [ ] 容器可以启动
- [ ] 测试可以在容器中运行
- [ ] 报告可以导出

---

### [P] Task 7: 设置 GitHub Actions CI
**预计时间**: 2小时  
**依赖**: Task 6  
**可并行**: ✅

创建 `.github/workflows/comprehensive-tests.yml`:
```yaml
name: Comprehensive Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 0'  # 每周日运行

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements_test.txt
      
      - name: Run backend tests
        run: |
          pytest tests/backend -v --cov --html=reports/backend_report.html
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          
      - name: Upload test report
        uses: actions/upload-artifact@v3
        with:
          name: backend-test-report
          path: reports/

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Playwright
        run: |
          pip install playwright pytest-playwright
          playwright install --with-deps
      
      - name: Run frontend tests
        run: |
          pytest tests/frontend -v --html=reports/frontend_report.html
      
      - name: Upload screenshots
        uses: actions/upload-artifact@v3
        with:
          name: test-screenshots
          path: reports/screenshots/

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: |
          docker-compose -f docker-compose.test.yml up -d
          sleep 30
      
      - name: Run E2E tests
        run: |
          pytest tests/e2e -v --html=reports/e2e_report.html
      
      - name: Stop services
        run: docker-compose -f docker-compose.test.yml down
```

**验收标准**:
- [ ] CI 配置文件创建
- [ ] 可以触发构建
- [ ] 测试报告上传
- [ ] 覆盖率报告正常

---

### [P0] Task 8: 编写测试工具函数
**预计时间**: 2小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/utils/helpers.py`:
```python
import numpy as np
from pathlib import Path
import json
import time
from typing import Dict, Any

def compare_with_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    """比较数值（带容差）"""
    return abs(actual - expected) <= tolerance

def calculate_error_percentage(actual: float, expected: float) -> float:
    """计算误差百分比"""
    if expected == 0:
        return 0.0 if actual == 0 else float('inf')
    return abs(actual - expected) / abs(expected) * 100

def wait_for_completion(
    check_func,
    timeout=30,
    interval=0.5,
    timeout_message="操作超时"
):
    """等待条件满足"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_func():
            return True
        time.sleep(interval)
    raise TimeoutError(timeout_message)

def save_test_result(result: Dict[str, Any], filename: str):
    """保存测试结果"""
    path = Path("reports") / filename
    with open(path, "w") as f:
        json.dump(result, f, indent=2)

class PerformanceTimer:
    """性能计时器"""
    def __init__(self, name="Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        print(f"{self.name}: {elapsed:.3f}s")
    
    @property
    def elapsed(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
```

**验收标准**:
- [ ] 工具函数完整
- [ ] 单元测试通过
- [ ] 文档清晰

---

## Phase 2: 后端测试 (Tasks 9-20)

### [P0] Task 9: 测试 GodunvFVMSolver vs HEC-RAS
**预计时间**: 3小时  
**依赖**: Task 5, 8  
**可并行**: 否

创建 `tests/backend/solvers/test_godunov_commercial.py`

**测试内容**:
- 恒定流对标
- 溃坝对标
- 含摩阻流动
- 质量守恒验证

**验收标准**:
- [ ] 水深误差 < 1%
- [ ] 流量误差 < 0.01%
- [ ] 质量守恒误差 < 0.1%
- [ ] 与理论解对比通过

---

### [P0] Task 10: 测试 HydrostaticCanalSolver 精度
**预计时间**: 2小时  
**依赖**: Task 5, 8  
**可并行**: ✅ (与 Task 9)

创建 `tests/backend/solvers/test_hydrostatic_accuracy.py`

**测试内容**:
- 均匀流计算
- 渐变流计算
- 闸门流动
- 堰流计算

**验收标准**:
- [ ] 流量误差 < 0.001%
- [ ] 收敛迭代 < 10次
- [ ] 所有算例通过

---

### [P] Task 11-14: 测试其他核心求解器
**预计时间**: 6小时  
**依赖**: Task 5, 8  
**可并行**: ✅

- Task 11: HardyCrossSolver vs EPANET (2h)
- Task 12: WaterHammerMOCSolver (2h)
- Task 13: Canal (Preissmann) (1h)
- Task 14: NewtonRaphson Network (1h)

**验收标准**:
- [ ] 每个求解器 ≥ 3 个测试案例
- [ ] 计算精度验证通过
- [ ] 性能基准建立

---

### [P0] Task 15: 知识库 API 测试
**预计时间**: 2小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/backend/api/test_knowledge_api.py`

**测试端点**:
- GET /api/knowledge/
- GET /api/knowledge/stats
- GET /api/knowledge/categories
- POST /api/knowledge/search

**验收标准**:
- [ ] 所有端点返回 200
- [ ] 响应格式正确
- [ ] 边界条件处理
- [ ] 错误处理完善

---

### [P0] Task 16: 案例运行 API 测试
**预计时间**: 3小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/backend/api/test_cases_api.py`

**测试端点**:
- GET /api/cases/
- POST /api/cases/run/{case_id}
- GET /api/cases/{case_id}/results

**验收标准**:
- [ ] 案例可以成功运行
- [ ] 结果返回正确
- [ ] 异步任务处理正常

---

### [P0] Task 17: 模拟计算 API 测试
**预计时间**: 3小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/backend/api/test_simulation_api.py`

**测试端点**:
- POST /api/simulation/create
- GET /api/simulation/{id}/status
- GET /api/simulation/{id}/results

**验收标准**:
- [ ] 模拟任务创建成功
- [ ] 状态查询正常
- [ ] 结果获取正确

---

### [P] Task 18-19: 其他 API 测试
**预计时间**: 4小时  
**可并行**: ✅

- Task 18: 教材 API 测试 (2h)
- Task 19: 学习进度 API 测试 (2h)

---

### [P1] Task 20: API 性能基准测试
**预计时间**: 2小时  
**依赖**: Task 15-19  
**可并行**: 否

创建 `tests/performance/test_api_performance.py`

**测试指标**:
- 响应时间 P50, P95, P99
- QPS (每秒请求数)
- 并发处理能力

**验收标准**:
- [ ] P95 < 1秒
- [ ] 可支持 10+ 并发

---

## Phase 3: 前端测试 (Tasks 21-30)

### [P0] Task 21: 首页加载测试
**预计时间**: 1小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/frontend/pages/test_homepage.py`

**测试内容**:
- 页面加载时间
- 关键元素存在
- 导航链接有效

**验收标准**:
- [ ] 加载时间 < 2秒
- [ ] 无 console 错误
- [ ] 截图基准建立

---

### [P0] Task 22: 知识库页面测试
**预计时间**: 2小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/frontend/pages/test_knowledge_page.py`

**测试内容**:
- 书籍列表展示
- 搜索功能
- 详情查看
- 截图验证

**验收标准**:
- [ ] 功能正常
- [ ] 截图清晰
- [ ] 交互流畅

---

### [P0] Task 23: 案例运行页面测试
**预计时间**: 3小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/frontend/pages/test_cases_page.py`

**测试内容**:
- 案例列表
- 参数编辑
- 运行按钮
- 结果展示

**验收标准**:
- [ ] 完整工作流测试
- [ ] 每步截图
- [ ] 错误处理验证

---

### [P0] Task 24: 模拟器页面测试
**预计时间**: 3小时  
**依赖**: Task 4  
**可并行**: ✅

创建 `tests/frontend/pages/test_simulation_page.py`

**测试内容**:
- 几何建模
- 参数输入
- 实时计算
- 结果可视化

**验收标准**:
- [ ] 建模工具可用
- [ ] 计算流程正常
- [ ] 可视化正确

---

### [P] Task 25-27: 可视化组件测试
**预计时间**: 6小时  
**可并行**: ✅

- Task 25: 图表组件测试 (2h)
- Task 26: 地图组件测试 (2h)
- Task 27: 3D可视化测试 (2h)

**验收标准**:
- [ ] 数据渲染正确
- [ ] 交互响应正常
- [ ] 导出功能可用

---

### [P1] Task 28-30: 浏览器兼容性测试
**预计时间**: 3小时  
**可并行**: ✅

- Task 28: Chrome 测试 (1h)
- Task 29: Firefox 测试 (1h)
- Task 30: Edge 测试 (1h)

**验收标准**:
- [ ] 所有浏览器通过
- [ ] 截图对比
- [ ] 性能一致

---

## Phase 4: 端到端测试 (Tasks 31-36)

### [P0] Task 31: 明渠恒定流 E2E 测试
**预计时间**: 4小时  
**依赖**: Task 21-24  
**可并行**: 否

创建 `tests/e2e/test_steady_flow_workflow.py`

**完整流程**:
1. 访问首页
2. 选择案例
3. 设置参数
4. 运行计算
5. 查看结果
6. 导出数据
7. 每步截图

**验收标准**:
- [ ] 完整工作流通过
- [ ] 至少 7 张截图
- [ ] 计算时间 < 10秒
- [ ] 结果准确

---

### [P0] Task 32: 非恒定流+闸门 E2E 测试
**预计时间**: 4小时  
**依赖**: Task 21-24  
**可并行**: ✅ (与 Task 31)

创建 `tests/e2e/test_unsteady_gate_workflow.py`

**完整流程**:
1. 选择非恒定流案例
2. 添加闸门
3. 设置时间步
4. 运行模拟
5. 查看动画
6. 验证质量守恒

**验收标准**:
- [ ] 动画播放正常
- [ ] 质量守恒验证
- [ ] 截图完整

---

### [P] Task 33-35: 其他 E2E 场景
**预计时间**: 9小时  
**可并行**: ✅

- Task 33: 管网计算 E2E (3h)
- Task 34: 水锤分析 E2E (3h)
- Task 35: 多案例对比 E2E (3h)

---

### [P1] Task 36: E2E 性能测试
**预计时间**: 2小时  
**依赖**: Task 31-35  
**可并行**: 否

**测试内容**:
- 端到端响应时间
- 资源使用情况
- 内存泄漏检测

**验收标准**:
- [ ] 总时间 < 30秒
- [ ] 无内存泄漏
- [ ] CPU/内存合理

---

## Phase 5: 性能与负载测试 (Tasks 37-40)

### [P1] Task 37: 编写 Locust 负载测试脚本
**预计时间**: 3小时  
**依赖**: Task 15-19  
**可并行**: ✅

创建 `tests/performance/locustfile.py` (见 plan.md)

**测试场景**:
- 知识库浏览 (高频)
- 案例运行 (中频)
- 模拟计算 (低频)

**验收标准**:
- [ ] 脚本可运行
- [ ] 场景合理
- [ ] 统计完整

---

### [P1] Task 38: 运行负载测试
**预计时间**: 2小时  
**依赖**: Task 37  
**可并行**: 否

**测试配置**:
- 用户数: 10, 50, 100
- 持续时间: 5分钟
- 递增速率: 5 用户/秒

**验收标准**:
- [ ] 测试完成
- [ ] 无崩溃
- [ ] 报告生成

---

### [P1] Task 39: 分析性能瓶颈
**预计时间**: 3小时  
**依赖**: Task 38  
**可并行**: 否

**分析内容**:
- 响应时间分布
- 失败请求分析
- 资源瓶颈识别
- 优化建议

**验收标准**:
- [ ] 瓶颈报告
- [ ] 优化建议清单
- [ ] 性能基准文档

---

### [P1] Task 40: 求解器性能基准
**预计时间**: 3小时  
**依赖**: Task 9-14  
**可并行**: ✅

创建 `tests/performance/test_solver_benchmark.py`

**测试规模**:
- 100, 500, 1000, 5000 单元
- 不同求解器对比
- 扩展性分析

**验收标准**:
- [ ] 性能数据完整
- [ ] 扩展性图表
- [ ] 对比表格

---

## Phase 6: 报告与文档 (Tasks 41-45)

### [P0] Task 41: 编写报告生成器
**预计时间**: 4小时  
**依赖**: 所有测试任务  
**可并行**: 否

创建 `tests/utils/report_generator.py` (见 plan.md)

**功能**:
- JSON 报告
- Markdown 报告
- HTML 报告
- 图表生成

**验收标准**:
- [ ] 报告完整
- [ ] 格式规范
- [ ] 图表清晰

---

### [P0] Task 42: 生成综合测试报告
**预计时间**: 3小时  
**依赖**: Task 41  
**可并行**: 否

运行报告生成器，生成：
- comprehensive_test_report.md
- comprehensive_test_report.json
- comprehensive_test_report.html

**包含内容**:
- 测试摘要
- 后端测试结果
- 前端测试结果
- E2E 测试结果
- 性能分析
- 截图展示

**验收标准**:
- [ ] 报告完整
- [ ] 数据准确
- [ ] 格式规范
- [ ] 截图清晰

---

### [P0] Task 43: 编写商业对标分析报告
**预计时间**: 4小时  
**依赖**: Task 9-14  
**可并行**: ✅ (与 Task 42)

创建 `commercial_comparison_analysis.md`

**对标软件**:
- HEC-RAS
- MIKE 11
- EPANET
- WaterGEMS

**对比维度**:
- 功能完整性
- 计算精度
- 性能表现
- 用户体验
- 价格/许可

**验收标准**:
- [ ] 功能对比矩阵
- [ ] 精度对比表
- [ ] 差距分析
- [ ] 竞争优势

---

### [P0] Task 44: 编写改进建议清单
**预计时间**: 3小时  
**依赖**: Task 42, 43  
**可并行**: 否

创建 `improvement_recommendations.md`

**建议分类**:
- P0: 紧急修复
- P1: 重要改进
- P2: 优化建议
- P3: 长期规划

**每条建议包含**:
- 问题描述
- 影响分析
- 解决方案
- 工作量估算
- 优先级

**验收标准**:
- [ ] 至少 20 条建议
- [ ] 优先级明确
- [ ] 可操作性强

---

### [P0] Task 45: 编写开发路线图
**预计时间**: 3小时  
**依赖**: Task 44  
**可并行**: 否

创建 `roadmap_phase_1_2_3.md`

**规划内容**:
- Phase 1: 核心功能完善 (3-6个月)
- Phase 2: 用户体验提升 (6-12个月)
- Phase 3: 企业级功能 (12-18个月)

**每个 Phase 包含**:
- 目标说明
- 功能清单
- 里程碑定义
- 资源需求
- 风险评估

**验收标准**:
- [ ] 路线图清晰
- [ ] 目标可达
- [ ] 时间合理
- [ ] 资源明确

---

## 📊 任务统计

### 按阶段统计

| 阶段 | 任务数 | 预计时间 | 优先级分布 |
|------|--------|----------|-----------|
| Phase 1 | 8 | 13h | P0:5, P:3 |
| Phase 2 | 12 | 27h | P0:6, P:4, P1:2 |
| Phase 3 | 10 | 21h | P0:4, P:3, P1:3 |
| Phase 4 | 6 | 21h | P0:2, P:3, P1:1 |
| Phase 5 | 4 | 11h | P1:4 |
| Phase 6 | 5 | 17h | P0:5 |
| **总计** | **45** | **110h** | **P0:22, P:13, P1:10** |

### 并行能力分析

**可并行任务组**:
- Group 1: Task 2-5, 7-8 (6个任务)
- Group 2: Task 9-14 (6个求解器测试)
- Group 3: Task 15-19 (5个 API 测试)
- Group 4: Task 21-27 (7个前端测试)
- Group 5: Task 28-30 (3个浏览器测试)
- Group 6: Task 31-35 (5个 E2E 测试)

**理论最短完成时间** (2人并行): ~7天  
**实际预计完成时间** (考虑依赖): 10-14天

---

## ✅ 任务验收总清单

### 必须完成 (P0)

- [ ] 所有 22 个 P0 任务完成
- [ ] 测试覆盖率达标
- [ ] 报告完整交付
- [ ] 截图文档齐全

### 建议完成 (P + P1)

- [ ] 至少 15 个 P/P1 任务完成
- [ ] 性能基准建立
- [ ] 商业对标完成

### 可选完成 (其他)

- [ ] 视觉回归测试
- [ ] CI/CD 集成
- [ ] 用户手册草稿

---

## 🚀 执行建议

### 快速启动 (第1天)

```bash
# 1. 创建目录结构
bash scripts/create_test_structure.sh

# 2. 安装依赖
pip install -r requirements_test.txt
playwright install

# 3. 配置 pytest
cp pytest.ini.template pytest.ini

# 4. 运行第一个测试
pytest tests/backend/test_example.py -v
```

### 每日工作流

```bash
# 早上：运行所有测试
pytest -v --html=reports/daily_$(date +%Y%m%d).html

# 开发期间：运行相关测试
pytest tests/backend/api/ -v

# 晚上：生成报告
python tests/utils/report_generator.py
```

### 里程碑检查点

- **Day 3**: 完成 Task 1-8 (基础设施)
- **Day 6**: 完成 Task 9-20 (后端测试)
- **Day 9**: 完成 Task 21-30 (前端测试)
- **Day 12**: 完成 Task 31-40 (E2E + 性能)
- **Day 14**: 完成 Task 41-45 (报告)

---

**Tasks Version**: 1.0  
**Total Tasks**: 45  
**Estimated Hours**: 80-110  
**Parallel Groups**: 6  
**Status**: Ready for Implementation  
**Next Step**: 开始执行 Task 1
