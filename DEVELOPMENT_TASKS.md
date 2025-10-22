# HydroClaude 开发任务清单

**生成日期**: 2025-10-22
**状态**: 活跃开发中
**优先级说明**: 🔴 高 | 🟡 中 | 🟢 低

---

## 📊 项目当前状态

### ✅ 已完成 (本次会话)
- [x] 修复Reservoir类数组类型转换问题
- [x] 修复组件接口兼容性（Pump, Tank, Pipe）
- [x] 修复Examples 18, 19, 20运行错误
- [x] 创建Example 24 - 多目标优化
- [x] 运行并通过163个测试用例
- [x] 代码提交并推送到远程分支

### 📈 测试覆盖率
- **单元测试**: 163/164 通过 (99.4%)
- **示例测试**: 8/24 已验证 (33.3%)
  - ✅ Examples 17, 18, 19, 20, 21, 22, 23, 24
  - ⏳ Examples 1-16 待测试

---

## 🎯 任务分类

## 一、示例验证与修复 (优先级: 🟡)

### 1.1 运行未测试的示例 (估计: 4-6小时)

**目标**: 验证Examples 1-16的正确性，修复发现的问题

| 示例 | 文件路径 | 功能描述 | 优先级 | 状态 |
|-----|---------|---------|--------|-----|
| Example 01 | `example_01_canal_flow/` | 渠道流动分析（多个子示例） | 🟡 | ⏳ 待测试 |
| Example 02 | `example_02_pump_system/` | 泵站系统 | 🟡 | ⏳ 待测试 |
| Example 02 | `example_02_spillway_cascade/` | 溢洪道级联 | 🟡 | ⏳ 待测试 |
| Example 03 | `example_03_complex_network/` | 复杂管网 | 🟡 | ⏳ 待测试 |
| Example 03 | `example_03_turbine_demo/` | 水轮机对比 | 🟡 | ✅ 已测试 |
| Example 04 | `example_04_hydropower_system/` | 水电站系统 | 🟡 | ⏳ 待测试 |
| Example 04 | `example_04_moc_boundary/` | MOC边界条件 | 🟡 | ⏳ 待测试 |
| Example 05 | `example_05_mode_comparison/` | 模式对比 | 🟡 | ⏳ 待测试 |
| Example 05 | `example_05_transient_analysis/` | 瞬态分析 | 🟡 | ⏳ 待测试 |
| Example 06 | `example_06_complete_hydropower_system/` | 完整水电系统 | 🟡 | ⏳ 待测试 |
| Example 06 | `example_06_sil_basic/` | SIL基础 | 🟡 | ⏳ 待测试 |
| Example 07 | `example_07_fault_test/` | 故障测试 | 🟡 | ⏳ 待测试 |
| Example 07 | `example_07_multi_unit_agc/` | 多机组AGC | 🟡 | ⏳ 待测试 |
| Example 08 | `example_08_load_acceptance/` | 负荷接受 | 🟡 | ⏳ 待测试 |
| Example 08 | `example_08_preissmann_vs_fvm/` | Preissmann vs FVM | 🟡 | ⏳ 待测试 |
| Example 09 | `example_09_pipe_rk4/` | 管道RK4求解 | 🟡 | ⏳ 待测试 |
| Example 10 | `example_10_series_network/` | 串联网络 | 🟡 | ⏳ 待测试 |
| Example 11 | `example_11_tree_network/` | 树形网络 | 🟡 | ⏳ 待测试 |
| Example 12 | `example_12_loop_network/` | 环形网络 | 🟡 | ⏳ 待测试 |
| Example 13 | `example_13_adaptive_timescale/` | 自适应时间尺度 | 🟡 | ⏳ 待测试 |
| Example 14 | `example_14_adaptive_mpc/` | 自适应MPC | 🟡 | ⏳ 待测试 |
| Example 15 | `example_15_rls_identification/` | RLS辨识 | 🟡 | ⏳ 待测试 |
| Example 16 | `example_16_weirs_application/` | 堰的应用 | 🟡 | ⏳ 待测试 |

**实施步骤**:
1. 按顺序运行每个示例
2. 记录运行结果（成功/失败/错误信息）
3. 修复发现的问题（参考Examples 18-20的修复方法）
4. 生成运行报告和结果可视化
5. 更新示例文档

**预期产出**:
- 示例测试报告
- 修复补丁（如有需要）
- 所有示例的输出图表汇总

---

## 二、测试修复 (优先级: 🔴)

### 2.1 修复 test_boundaries.py 导入错误 (估计: 1小时)

**问题**:
```python
ImportError: cannot import name 'ConstantHead' from 'physics.boundaries'
```

**可能原因**:
- 类名已更改
- 文件已重构
- 导入路径错误

**解决方案**:
1. 检查`physics/boundaries.py`的实际类名
2. 更新`test_boundaries.py`的导入语句
3. 验证所有边界条件类的接口一致性
4. 重新运行测试

---

### 2.2 修复 test_continuation_robustness.py fixture问题 (估计: 30分钟)

**问题**:
```python
fixture 'name' not found
```

**原因**: pytest parametrize装饰器使用不当

**解决方案**:
```python
# 修改前
def test_initial_condition(name, h_init_func, Q_init_func, system, Q_target):
    pass

# 修改后
@pytest.mark.parametrize("name,h_init_func,Q_init_func,system,Q_target", [
    # 参数列表
])
def test_initial_condition(name, h_init_func, Q_init_func, system, Q_target):
    pass
```

---

## 三、核心算法改进 (优先级: 🔴)

### 3.1 修复牛顿法边界条件问题 (估计: 2-3天)

**问题描述**:
- 当前Jacobian矩阵奇异（秩21/22，应为22/22）
- 上游边界条件不完整（h_0是自由变量）
- 导致牛顿法无法收敛

**修复方案A - 直接指定法** (推荐):
```python
# physics/steady_saint_venant.py
def set_boundary_conditions(self, Q_upstream, h_upstream, h_downstream):
    """
    上游：指定Q和h（两个边界条件）
    下游：指定h（一个边界条件，亚临界流）
    """
    self.Q_upstream = Q_upstream
    self.h_upstream = h_upstream  # 新增
    self.h_downstream = h_downstream

# 修改residual计算
F[0] = Q[0] - self.Q_upstream      # 上游流量BC
F[1] = h[0] - self.h_upstream      # 上游水深BC（替代连续性）
F[2*(nx-1)] = h[nx-1] - self.h_downstream  # 下游水深BC
```

**修复方案B - 特征线法** (更物理):
```python
# 使用Riemann不变量
# C+ = V + 2*sqrt(g*h) 沿 dx/dt = V + c 特征线传播
# C- = V - 2*sqrt(g*h) 沿 dx/dt = V - c 特征线传播

# 上游边界（只有C+进入）
F[0] = Q[0] - Q_upstream
# F[1]使用从内部传播来的C-关系
C_minus_interior = V[1] - 2*np.sqrt(g*h[1])
V_0 = Q[0] / (B * h[0])
C_minus_0 = V_0 - 2*np.sqrt(g*h[0])
F[1] = C_minus_0 - C_minus_interior
```

**实施步骤**:
1. Day 1: 实现方案A
   - 修改`steady_saint_venant.py`
   - 更新residual和Jacobian
   - 单元测试

2. Day 2: 验证和测试
   - 验证Jacobian非奇异（np.linalg.matrix_rank）
   - 验证条件数（np.linalg.cond）
   - 测试单闸门和三闸门场景
   - 确认牛顿法收敛性能

3. Day 3: 文档和优化（可选）
   - 实现方案B
   - 性能对比
   - 技术文档

**验收标准**:
- ✅ Jacobian秩 = 2*nx（满秩）
- ✅ 条件数 < 1e10（良好条件）
- ✅ 牛顿法收敛迭代次数 < 10
- ✅ 收敛速度比迭代法快10-100倍

**预期收益**:
- 牛顿法可用（二次收敛）
- 大幅提升求解速度
- 为后续优化奠定基础

---

### 3.2 Anderson加速实际验证 (估计: 1-2天)

**目标**: 在实际问题上对比Anderson vs Aitken加速效果

**测试场景**:
1. 单闸门稳态
2. 三闸门串联
3. 混合结构（闸门+堰+孔口）

**参数组合**:
```python
test_configs = [
    {'m': 3, 'beta': 0.7, 'name': '保守配置'},
    {'m': 5, 'beta': 0.8, 'name': '平衡配置'},
    {'m': 5, 'beta': 1.0, 'name': '激进配置'},
]
```

**对比指标**:
- 收敛迭代次数
- 总计算时间
- 内存使用量
- 稳定性（失败率）

**实施步骤**:
1. 完成`test_anderson_vs_aitken.py`
2. 运行完整测试矩阵
3. 数据分析和可视化
4. 编写结论报告

**产出**:
- 性能对比报告
- 参数选择建议
- 使用场景指南

---

## 四、代码质量改进 (优先级: 🟡)

### 4.1 修复README.md编码问题 (估计: 30分钟)

**问题**: README文件出现乱码

**解决方案**:
1. 检查文件编码（应为UTF-8）
2. 重新编写或转换编码
3. 添加项目徽章（build status, coverage, license等）
4. 完善安装说明和快速开始指南

**内容大纲**:
```markdown
# HydroClaude - 水力学仿真与优化框架

## 功能特性
- 1D水力学模拟
- 多种求解器
- 控制系统设计
- 优化调度

## 快速开始
## API文档
## 示例库
## 开发指南
## 许可证
```

---

### 4.2 创建YAML配置文件支持 (估计: 2-3天)

**目标**: 允许用户通过YAML文件配置系统参数

**功能设计**:
```yaml
# config/reservoir_system.yaml
system:
  name: "三级梯级水电站"
  description: "示例配置文件"

reservoirs:
  - id: R1_upstream
    total_capacity: 100e6  # m³
    min_level: 200.0
    normal_level: 260.0
    flood_level: 265.0
    design_level: 270.0
    turbine_capacity: 200.0  # MW
    ecological_flow: 50.0  # m³/s

  - id: R2_middle
    total_capacity: 50e6
    # ... 其他参数

topology:
  connections:
    - from: R1_upstream
      to: R2_middle
      travel_time: 7200  # 秒
```

**实施**:
```python
# core/config.py
import yaml
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ReservoirConfig:
    id: str
    total_capacity: float
    min_level: float
    # ... 其他字段

class SystemConfig:
    """从YAML加载系统配置"""

    @staticmethod
    def from_yaml(filepath: str) -> 'SystemConfig':
        with open(filepath) as f:
            data = yaml.safe_load(f)
        return SystemConfig._parse(data)

    def create_system(self):
        """根据配置创建实际系统对象"""
        reservoirs = [
            Reservoir(**cfg.__dict__)
            for cfg in self.reservoir_configs
        ]
        return CascadeSystem(reservoirs, self.topology)
```

**验收标准**:
- ✅ 支持完整的系统配置
- ✅ 配置验证和错误提示
- ✅ 至少2个示例配置文件
- ✅ 配置文件文档

---

### 4.3 添加日志系统 (估计: 1天)

**目标**: 统一的日志记录系统，便于调试和监控

**实施**:
```python
# core/logging.py
import logging
from pathlib import Path

def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """配置项目日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 文件处理器
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / f'{name}.log')
    file_handler.setLevel(logging.DEBUG)

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# 使用示例
# logger = setup_logger('HydroClaude.Reservoir')
# logger.info("开始仿真")
# logger.debug(f"当前水位: {level}")
# logger.warning("接近防洪限制水位")
# logger.error("水量平衡失败")
```

---

## 五、新功能开发 (优先级: 🟢)

### 5.1 性能基准测试套件 (估计: 3-4天)

**目标**: 标准化性能测试框架

**设计**:
```python
# benchmarks/benchmark_suite.py

from dataclasses import dataclass
from typing import Dict, List
import time
import numpy as np

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    solver: str
    iterations: int
    cpu_time: float
    wall_time: float
    memory_mb: float
    converged: bool
    residual: float

class BenchmarkSuite:
    """性能基准测试套件"""

    def __init__(self):
        self.benchmarks = {
            'uniform_flow': self._test_uniform_flow,
            'single_gate': self._test_single_gate,
            'three_gates': self._test_three_gates,
            'cascade_system': self._test_cascade_system,
        }

    def run_all(self, solver_configs: List[Dict]) -> List[BenchmarkResult]:
        """运行所有基准测试"""
        results = []
        for bench_name, test_func in self.benchmarks.items():
            for config in solver_configs:
                result = self._run_single(bench_name, test_func, config)
                results.append(result)
        return results

    def generate_report(self, results: List[BenchmarkResult]) -> str:
        """生成性能报告"""
        # Markdown表格格式
        # 对比图表
        # 性能分析
        pass
```

**测试场景**:
1. 均匀流（验证基础性能）
2. 单闸门（简单结构）
3. 三闸门（中等复杂度）
4. 梯级系统（高复杂度）
5. 时变边界（动态场景）

**对比求解器**:
- 固定松弛迭代
- Aitken加速
- Anderson加速
- 牛顿法（修复后）

**产出**:
- `benchmarks/` 目录
- 基准测试脚本
- 性能报告模板
- CI/CD集成（可选）

---

### 5.2 开发混合求解器策略 (估计: 4-5天)

**目标**: 自动选择最优求解策略

**设计理念**:
```python
class HybridSolver:
    """混合求解策略

    策略选择逻辑:
    1. 简单问题 → 固定松弛迭代（快速）
    2. 中等问题 → Aitken加速（稳健）
    3. 复杂问题 → 牛顿法（高效）
    4. 牛顿法失败 → 回退到Aitken
    """

    def solve(self, system):
        # 1. 问题诊断
        complexity = self._assess_complexity(system)

        # 2. 选择策略
        if complexity < 0.3:
            solver = FixedPointSolver(relax=0.5)
        elif complexity < 0.7:
            solver = AitkenSolver()
        else:
            solver = NewtonSolver()

        # 3. 求解（带回退）
        try:
            result = solver.solve(system)
            if not result.converged and isinstance(solver, NewtonSolver):
                # 回退策略
                logger.warning("牛顿法失败，回退到Aitken加速")
                solver = AitkenSolver()
                result = solver.solve(system)
            return result
        except Exception as e:
            logger.error(f"求解失败: {e}")
            raise
```

**复杂度评估指标**:
```python
def _assess_complexity(self, system) -> float:
    """评估问题复杂度 (0-1)"""
    factors = {
        'num_gates': min(system.num_gates / 10, 1.0),
        'gate_opening_range': self._calc_opening_range(system),
        'flow_variation': self._calc_flow_variation(system),
        'has_structures': float(system.has_weirs or system.has_orifices),
    }
    return np.mean(list(factors.values()))
```

---

### 5.3 自适应网格功能 (估计: 5-7天)

**目标**: 根据水力梯度自动加密网格

**算法设计**:
```python
class AdaptiveMesh:
    """自适应网格管理"""

    def __init__(self, initial_nx: int, refinement_threshold: float = 0.1):
        self.nx = initial_nx
        self.refinement_threshold = refinement_threshold
        self.x = np.linspace(0, L, nx)

    def refine(self, h: np.ndarray, Q: np.ndarray):
        """根据解的梯度加密网格"""
        # 1. 计算梯度指示器
        dh_dx = np.gradient(h)
        indicator = np.abs(dh_dx)

        # 2. 标记需要加密的区域
        refine_cells = indicator > self.refinement_threshold

        # 3. 插值生成新网格
        new_x = self._insert_points(self.x, refine_cells)

        # 4. 插值解到新网格
        new_h = np.interp(new_x, self.x, h)
        new_Q = np.interp(new_x, self.x, Q)

        self.x = new_x
        self.nx = len(new_x)

        return new_h, new_Q
```

**使用场景**:
- 闸门附近（水力梯度大）
- 结构物处（流态突变）
- 水跃区域（激波）

---

### 5.4 可视化工具增强 (估计: 2-3天)

**目标**: 交互式可视化和动画

**功能列表**:
1. **水力剖面动画**
   ```python
   from animation import create_profile_animation

   ani = create_profile_animation(
       results,
       fps=30,
       show_structures=True,
       show_velocity=True
   )
   ani.save('simulation.mp4')
   ```

2. **交互式仪表盘**
   ```python
   # 使用plotly/dash
   from dashboard import HydraulicDashboard

   dashboard = HydraulicDashboard(system)
   dashboard.add_plot('water_level')
   dashboard.add_plot('flow_rate')
   dashboard.add_slider('gate_opening', min=0, max=1)
   dashboard.run(port=8050)
   ```

3. **网络拓扑可视化**
   ```python
   from visualization import plot_network_topology

   plot_network_topology(
       cascade_system,
       layout='hierarchical',
       show_flows=True,
       show_capacities=True
   )
   ```

---

### 5.5 并行计算支持 (估计: 7-10天)

**目标**: 多线程/多进程加速大规模仿真

**阶段1: 多线程求解** (3天)
```python
from concurrent.futures import ThreadPoolExecutor

class ParallelReservoirSimulator:
    """并行水库仿真"""

    def simulate_multiple_scenarios(self, scenarios: List[Dict]):
        """并行运行多个场景"""
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self._simulate_single, scenario)
                for scenario in scenarios
            ]
            results = [f.result() for f in futures]
        return results
```

**阶段2: 空间并行化** (4-5天)
```python
# 将长渠道分割成多段并行求解
class DomainDecomposition:
    """区域分解并行"""

    def __init__(self, n_domains: int):
        self.n_domains = n_domains

    def solve_parallel(self, system):
        # Schwarz交替法
        # 1. 分解区域
        # 2. 并行求解各子区域
        # 3. 边界信息交换
        # 4. 迭代直到收敛
        pass
```

**阶段3: GPU加速** (可选，2-3天)
```python
# 使用CuPy/Numba实现GPU加速
import cupy as cp

@numba.cuda.jit
def solve_tridiagonal_gpu(a, b, c, d):
    """GPU加速三对角矩阵求解"""
    pass
```

---

## 六、文档完善 (优先级: 🟡)

### 6.1 用户文档 (估计: 3-4天)

**内容大纲**:
```
docs/
├── user_guide/
│   ├── installation.md
│   ├── quick_start.md
│   ├── basic_concepts.md
│   ├── tutorials/
│   │   ├── 01_simple_canal.md
│   │   ├── 02_reservoir_operation.md
│   │   ├── 03_cascade_system.md
│   │   └── 04_optimization.md
│   └── faq.md
├── api_reference/
│   ├── physics/
│   ├── solvers/
│   ├── control/
│   └── optimization/
├── developer_guide/
│   ├── architecture.md
│   ├── coding_standards.md
│   ├── testing.md
│   └── contributing.md
└── examples/
    └── gallery.md
```

**工具**: 使用Sphinx自动生成文档

---

### 6.2 API参考文档 (估计: 2-3天)

**实施**:
1. 为所有公共类和函数添加完整的docstring
2. 使用Google风格或NumPy风格
3. 使用Sphinx自动生成HTML文档
4. 托管到GitHub Pages或Read the Docs

**Docstring模板**:
```python
def calculate_flow(self, h_upstream: float, h_downstream: float) -> float:
    """计算通过结构物的流量

    使用能量方程和流量系数计算自由流或淹没流条件下的流量。

    Args:
        h_upstream: 上游水深 (m)
        h_downstream: 下游水深 (m)

    Returns:
        流量 (m³/s)

    Raises:
        ValueError: 如果水深为负值

    Examples:
        >>> gate = SluiceGate(width=5.0, coefficient=0.6)
        >>> Q = gate.calculate_flow(h_upstream=3.0, h_downstream=1.0)
        >>> print(f"Flow rate: {Q:.2f} m³/s")
        Flow rate: 12.34 m³/s

    References:
        - Henderson (1966): Open Channel Flow
        - Chow (1959): Open-channel Hydraulics
    """
    # 实现
```

---

### 6.3 示例库整理 (估计: 2天)

**目标**: 创建示例索引和说明文档

**内容**:
```markdown
# 示例库

## 基础示例
- Example 01: 渠道流动分析
- Example 02: 泵站系统
- ...

## 进阶示例
- Example 17: 水库基础仿真
- Example 18: 梯级水电站调度
- ...

## 优化示例
- Example 21: 灌区优化配水
- Example 24: 多目标优化

## 每个示例包含:
- 功能描述
- 物理模型
- 关键参数
- 运行方法
- 预期输出
- 可视化结果
```

---

## 七、工程化改进 (优先级: 🟢)

### 7.1 CI/CD集成 (估计: 2天)

**目标**: GitHub Actions自动化测试和部署

**配置示例**:
```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest tests/ --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

### 7.2 代码质量检查 (估计: 1天)

**工具集成**:
- **Black**: 代码格式化
- **Flake8**: 代码风格检查
- **MyPy**: 类型检查
- **Pylint**: 代码质量

**配置**:
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

---

### 7.3 性能分析工具 (估计: 2天)

**实施**:
```python
# utils/profiling.py

import cProfile
import pstats
from functools import wraps

def profile(output_file=None):
    """性能分析装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()

            result = func(*args, **kwargs)

            profiler.disable()
            stats = pstats.Stats(profiler)

            if output_file:
                stats.dump_stats(output_file)
            else:
                stats.sort_stats('cumulative')
                stats.print_stats(20)

            return result
        return wrapper
    return decorator

# 使用
@profile(output_file='profile_results.prof')
def run_simulation():
    # 仿真代码
    pass
```

**可视化工具**:
- SnakeViz: 交互式profile可视化
- py-spy: 实时性能监控

---

## 八、研究性探索 (优先级: 🟢 - 长期)

### 8.1 机器学习降阶模型 (估计: 2-3周)

**目标**: 使用神经网络加速复杂系统仿真

**方法**:
```python
import torch
import torch.nn as nn

class ReservoirSurrogate(nn.Module):
    """水库响应的神经网络代理模型"""

    def __init__(self, input_dim=3, hidden_dim=64, output_dim=2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )

    def forward(self, x):
        """
        输入: [inflow, initial_level, gate_opening]
        输出: [final_level, outflow]
        """
        return self.net(x)

# 训练数据生成
def generate_training_data(n_samples=10000):
    # 使用物理模型生成大量样本
    # 输入: 随机入流、初始水位、闸门开度
    # 输出: 运行物理模型得到的结果
    pass

# 一旦训练完成，代理模型可以快1000倍
```

**应用场景**:
- 实时优化调度
- 蒙特卡洛模拟
- 不确定性量化

---

### 8.2 不确定性量化 (估计: 2-3周)

**目标**: 量化参数不确定性对结果的影响

**方法**:
```python
from scipy import stats
import numpy as np

class UncertaintyQuantification:
    """不确定性量化"""

    def __init__(self, model, uncertain_params):
        self.model = model
        self.uncertain_params = uncertain_params

    def monte_carlo(self, n_samples=1000):
        """蒙特卡洛采样"""
        results = []
        for _ in range(n_samples):
            # 从分布中采样参数
            params = self._sample_parameters()
            # 运行模型
            result = self.model.run(params)
            results.append(result)

        # 统计分析
        mean = np.mean(results, axis=0)
        std = np.std(results, axis=0)
        percentiles = np.percentile(results, [5, 95], axis=0)

        return {
            'mean': mean,
            'std': std,
            'confidence_interval_90': percentiles
        }
```

---

### 8.3 2D浅水方程求解器 (估计: 4-6周)

**目标**: 扩展到二维水力学

**核心方程**:
```
∂h/∂t + ∂(hu)/∂x + ∂(hv)/∂y = 0  (连续性)
∂(hu)/∂t + ∂(hu² + gh²/2)/∂x + ∂(huv)/∂y = -gh∂z/∂x - friction_x
∂(hv)/∂t + ∂(huv)/∂x + ∂(hv² + gh²/2)/∂y = -gh∂z/∂y - friction_y
```

**数值方法**:
- 有限体积法（FVM）
- Godunov格式或Roe格式
- HLL近似Riemann求解器

---

## 📊 优先级矩阵

| 任务 | 优先级 | 工作量 | 影响力 | 建议顺序 |
|-----|-------|-------|-------|---------|
| 修复牛顿法边界条件 | 🔴 高 | 中 (2-3天) | 高 | 1 |
| 测试Examples 1-16 | 🟡 中 | 中 (4-6小时) | 中 | 2 |
| 修复test_boundaries.py | 🔴 高 | 低 (1小时) | 中 | 3 |
| 修复test_continuation | 🔴 高 | 低 (30分钟) | 低 | 4 |
| Anderson加速验证 | 🟡 中 | 低 (1-2天) | 中 | 5 |
| 修复README编码 | 🟡 中 | 低 (30分钟) | 低 | 6 |
| 性能基准测试 | 🟡 中 | 中 (3-4天) | 高 | 7 |
| YAML配置支持 | 🟡 中 | 中 (2-3天) | 中 | 8 |
| 日志系统 | 🟡 中 | 低 (1天) | 中 | 9 |
| 混合求解器 | 🟢 低 | 中 (4-5天) | 高 | 10 |
| 自适应网格 | 🟢 低 | 高 (5-7天) | 中 | 11 |
| 用户文档 | 🟡 中 | 中 (3-4天) | 高 | 12 |
| API文档 | 🟡 中 | 中 (2-3天) | 中 | 13 |
| CI/CD | 🟢 低 | 低 (2天) | 中 | 14 |
| 可视化增强 | 🟢 低 | 中 (2-3天) | 中 | 15 |
| 并行计算 | 🟢 低 | 高 (7-10天) | 高 | 16 |
| 机器学习ROM | 🟢 低 | 高 (2-3周) | 中 | 17 |
| 不确定性量化 | 🟢 低 | 高 (2-3周) | 中 | 18 |
| 2D求解器 | 🟢 低 | 很高 (4-6周) | 高 | 19 |

---

## 🎯 推荐开发路线

### 第一阶段 (1-2周): 核心修复
1. ✅ 修复牛顿法边界条件
2. ✅ 修复两个测试错误
3. ✅ 运行并验证所有示例
4. ✅ Anderson加速验证

### 第二阶段 (2-3周): 工程质量
1. ✅ 性能基准测试套件
2. ✅ YAML配置支持
3. ✅ 日志系统
4. ✅ 修复README
5. ✅ 代码质量检查工具

### 第三阶段 (3-4周): 功能扩展
1. ✅ 混合求解器策略
2. ✅ 用户文档和API文档
3. ✅ 示例库整理
4. ✅ CI/CD集成

### 第四阶段 (4-6周): 高级功能
1. ✅ 自适应网格
2. ✅ 可视化增强
3. ✅ 并行计算（初步）

### 第五阶段 (长期): 研究探索
1. ✅ 机器学习降阶模型
2. ✅ 不确定性量化
3. ✅ 2D求解器

---

## 📝 总结

本任务清单涵盖了从**短期修复**到**长期研究**的完整开发计划，包括：

- ✅ **19个主要任务**
- ✅ **预估总工作量**: 20-30周（全职开发）
- ✅ **覆盖领域**:
  - 核心算法改进
  - 代码质量提升
  - 文档完善
  - 工程化
  - 研究探索

建议**优先完成第一阶段**的核心修复任务，这将为后续开发奠定坚实基础。

---

**更新日期**: 2025-10-22
**维护者**: HydroClaude开发团队
