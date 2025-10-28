# HydroClaude 开发规范与质量标准

**版本**: 1.0
**生效日期**: 2025-10-28
**状态**: 强制执行 (MANDATORY)
**目标**: 达到商业软件级质量标准

---

## 📋 文档说明

本文档定义了HydroClaude项目的**强制性**开发规范和质量标准。所有代码贡献者（包括AI助手如Claude Code）**必须严格遵守**。

### 核心原则

> **"质量第一，功能第二；验证先行，实现随后"**
>
> **"宁可功能少但稳定，不要功能多但不可靠"**
>
> **"每一行代码都必须经过测试，每一个功能都必须经过验证"**

---

## 第一章：开发流程规范

### 1.1 测试驱动开发（TDD）- 强制执行

#### 规则 R1.1: 测试先行原则

**要求**: 必须先编写测试，再编写实现代码

**流程**:
```
1. 编写测试用例 (test_*.py)
2. 运行测试，确认失败 (Red)
3. 编写最小实现代码
4. 运行测试，确认通过 (Green)
5. 重构代码，优化实现 (Refactor)
6. 再次运行测试，确认仍通过
```

**禁止行为** ❌:
- ❌ 先写代码再写测试
- ❌ 写完代码不写测试
- ❌ 写了测试但不运行
- ❌ 测试失败但仍然提交代码

**示例**:

```python
# ✅ 正确: 先写测试
def test_lake_at_rest():
    """测试well-balanced性质：静水应保持不动"""
    solver = GodunovFVMSolver(
        nx=100, length=1000, B=10, S0=0.001, n=0.025
    )

    # 初始条件：静水，h=2m
    h_init = np.ones(100) * 2.0
    Q_init = np.zeros(100)
    solver.set_initial_conditions(h_init, Q_init)

    # 运行100秒
    solver.run(t_end=100.0)

    # 验证：水深应不变（机器精度）
    assert np.allclose(solver.h, h_init, rtol=1e-14)
    assert np.allclose(solver.Q, Q_init, atol=1e-14)
```

然后再实现求解器，确保通过此测试。

#### 规则 R1.2: 最小测试覆盖率要求

**要求**:

| 代码类型 | 最小覆盖率 | 理想覆盖率 |
|----------|-----------|-----------|
| 核心求解器 | 90% | 100% |
| 物理模型 | 80% | 95% |
| 工具函数 | 70% | 90% |
| 总体覆盖率 | 80% | 95% |

**强制要求**:
- ✅ 每个公共方法必须至少有1个测试
- ✅ 每个边界情况必须有测试
- ✅ 每个error handling路径必须有测试

**检查方式**:
```bash
pytest --cov=engine --cov=solvers --cov-report=term-missing --cov-report=html
```

### 1.2 代码质量门槛

#### 规则 R1.3: Pull Request必须满足的条件

**所有PR必须通过以下检查才能合并**:

- [ ] ✅ 所有新增代码有对应测试
- [ ] ✅ 所有测试通过（100% pass rate）
- [ ] ✅ 代码覆盖率未降低
- [ ] ✅ 通过代码风格检查（flake8/black）
- [ ] ✅ 通过类型检查（mypy，如适用）
- [ ] ✅ 有清晰的commit message
- [ ] ✅ 有文档更新（如适用）
- [ ] ✅ Code review通过

**自动化检查**:
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest --cov --cov-fail-under=80
      - name: Lint
        run: flake8 .
      - name: Type check
        run: mypy engine/ solvers/
```

#### 规则 R1.4: 禁止的行为

**严格禁止**:

1. ❌ **提交未测试的代码**
   - 后果：立即回滚，PR被拒绝

2. ❌ **修改代码导致测试失败后提交**
   - 后果：立即回滚，PR被拒绝

3. ❌ **删除或注释掉测试以通过CI**
   - 后果：严重违规，永久记录

4. ❌ **夸大功能或性能**
   - 例如："100x加速"但无基准测试证明
   - 后果：文档修正，记录问题

5. ❌ **声称功能"已实现"但实际未测试**
   - 例如：声称"Well-balanced"但无Lake at Rest测试
   - 后果：移除声称或立即补充测试

6. ❌ **复制粘贴代码导致重复**
   - 后果：要求重构，提取公共函数

7. ❌ **提交大量功能的单个commit**
   - 后果：要求拆分成小的逻辑单元

---

## 第二章：数值方法质量标准

### 2.1 标准测试案例（强制）

#### 规则 R2.1: P0级测试（阻塞性，必须通过）

**所有求解器必须通过以下测试才能声称"可用"**:

| 测试名称 | 测试目的 | 通过标准 | 优先级 |
|---------|---------|---------|--------|
| **Lake at Rest** | Well-balanced性质 | 数值扰动 < 机器精度 | P0 |
| **Steady Uniform Flow** | 稳态正确性 | 摩阻与重力平衡 | P0 |
| **Dam Break (Ritter)** | 激波捕捉能力 | L2误差 < 10% | P0 |
| **Mass Conservation** | 质量守恒 | 误差 < 0.01% | P0 |
| **Positivity Preservation** | 非负性 | h ≥ 0 始终成立 | P0 |

**测试模板**:

```python
# tests/standard_tests/test_p0_lake_at_rest.py

import pytest
import numpy as np

@pytest.mark.p0  # 标记为P0级测试
def test_lake_at_rest_godunov():
    """P0-1: Lake at Rest (Well-balanced)

    测试目的：验证well-balanced性质
    参考：Audusse et al. (2004)
    通过标准：数值扰动 < 1e-14 (机器精度)
    """
    from solvers.godunov_fvm_solver import GodunovFVMSolver

    # 设置
    solver = GodunovFVMSolver(
        nx=100,
        length=1000.0,
        B=10.0,
        S0=0.001,  # 有坡度但静水
        n=0.025
    )

    # 初始条件：静水，底坡与水面平行
    h_init = 2.0 + solver.z_b - solver.z_b[0]  # 水平水面
    Q_init = np.zeros_like(h_init)
    solver.set_initial_conditions(h_init, Q_init)

    # 运行1000秒（足够长）
    solver.run(t_end=1000.0, output=False)

    # 验证
    h_final = solver.h
    Q_final = solver.Q

    # 水深变化应该为0（数值精度内）
    max_h_change = np.max(np.abs(h_final - h_init))
    max_Q_change = np.max(np.abs(Q_final - Q_init))

    assert max_h_change < 1e-14, f"水深变化 {max_h_change} 超过机器精度"
    assert max_Q_change < 1e-14, f"流量变化 {max_Q_change} 超过机器精度"

    print(f"✅ P0-1 通过: 水深变化 = {max_h_change:.2e}")
```

#### 规则 R2.2: P1级测试（严重，强烈建议）

| 测试名称 | 测试目的 | 通过标准 | 优先级 |
|---------|---------|---------|--------|
| **MacDonald Test 1** | 回水曲线 | 误差 < 1cm | P1 |
| **MacDonald Test 2** | 激波 | 位置误差 < 5% | P1 |
| **MacDonald Test 3** | 稀疏波 | 波速误差 < 5% | P1 |
| **MacDonald Test 4** | 混合流态 | 流态正确识别 | P1 |
| **Hydraulic Jump** | 水跃捕捉 | 跃后水深误差 < 10% | P1 |
| **Dry Bed Dam Break** | 干湿界面 | 无崩溃，波阵面清晰 | P1 |

### 2.2 数值精度要求

#### 规则 R2.3: 误差容忍度

**质量守恒**:
```python
mass_error = |mass_final - mass_initial| / mass_initial * 100%

# 要求
assert mass_error < 0.01%  # P0级
assert mass_error < 0.001%  # 理想
```

**解析解对比**:
```python
# L2 (RMS) 误差
L2_error = sqrt(mean((h_numerical - h_analytical)^2))

# 相对误差
relative_error = L2_error / mean(h_analytical) * 100%

# 要求（取决于测试类型）
assert relative_error < 10%   # Dam break (激波问题)
assert relative_error < 5%    # Steady flow (平滑问题)
assert relative_error < 1%    # Uniform flow (简单问题)
```

**数值稳定性**:
```python
# CFL条件
assert dt <= CFL * dx / max_wave_speed
assert CFL <= 1.0  # 显式格式

# 非负性
assert np.all(h >= 0), "水深出现负值！"
assert np.all(h >= -eps_dry), f"水深低于干床阈值 {eps_dry}"
```

### 2.3 性能基准要求

#### 规则 R2.4: 性能测试

**必须建立性能基准**:

```python
# tests/performance/test_benchmarks.py

@pytest.mark.benchmark
def test_godunov_performance_scalability():
    """性能基准：可扩展性测试

    目的：建立性能数据库，指导用户选择网格
    """
    grid_sizes = [100, 200, 500, 1000, 2000, 5000]
    wall_times = []

    for nx in grid_sizes:
        solver = GodunovFVMSolver(nx=nx, ...)

        t_start = time.time()
        solver.run(t_end=100.0, output=False)
        t_end = time.time()

        wall_time = t_end - t_start
        wall_times.append(wall_time)

        print(f"nx={nx:5d}: {wall_time:.3f}s")

    # 检查可扩展性（应接近O(N)）
    # 网格翻倍，时间应< 3倍（考虑步数增加）
    for i in range(len(grid_sizes)-1):
        ratio = wall_times[i+1] / wall_times[i]
        grid_ratio = grid_sizes[i+1] / grid_sizes[i]
        assert ratio < grid_ratio * 3, f"可扩展性差: {ratio}x"
```

**性能回归检测**:
- ✅ 每次提交自动运行性能测试
- ✅ 性能下降 > 10% 触发警告
- ✅ 性能下降 > 50% 阻塞合并

---

## 第三章：代码规范

### 3.1 Python代码风格

#### 规则 R3.1: 遵循PEP 8 + 项目扩展

**基础**:
- ✅ 使用 `black` 自动格式化 (line-length=100)
- ✅ 使用 `flake8` 检查风格
- ✅ 使用 `isort` 排序import

**命名约定**:
```python
# ✅ 正确
class GodunovFVMSolver:  # 类名：大驼峰
    def compute_flux(self, ...):  # 方法名：小写下划线
        max_wave_speed = ...  # 变量名：小写下划线
        CFL = 0.5  # 常见缩写：大写

# ❌ 错误
class godunov_fvm_solver:  # 类名不是大驼峰
    def ComputeFlux(self, ...):  # 方法名不是小写下划线
        MaxWaveSpeed = ...  # 变量名不是小写下划线
```

**类型注解（强烈建议）**:
```python
# ✅ 有类型注解
def compute_flux(self,
                 h_L: float,
                 Q_L: float,
                 h_R: float,
                 Q_R: float) -> Tuple[float, float]:
    """计算数值通量

    Args:
        h_L: 左侧水深 (m)
        Q_L: 左侧流量 (m³/s)
        h_R: 右侧水深 (m)
        Q_R: 右侧流量 (m³/s)

    Returns:
        (F_mass, F_momentum): 质量和动量通量
    """
    ...
    return F_mass, F_momentum

# ❌ 无类型注解（不推荐）
def compute_flux(self, h_L, Q_L, h_R, Q_R):
    ...
```

### 3.2 文档字符串（Docstring）

#### 规则 R3.2: 所有公共API必须有文档

**格式**: 使用Google或NumPy风格

```python
# ✅ 完整文档
class GodunovFVMSolver:
    """Godunov有限体积法求解器

    使用Godunov格式求解1D浅水方程，支持HLL和HLLC Riemann求解器。

    理论基础：
        - Godunov (1959): 一阶精度守恒型格式
        - Toro (2009): HLL/HLLC Riemann求解器
        - LeVeque (2002): 有限体积法

    特性：
        - Well-balanced: 满足C-property (Lake at Rest)
        - TVD: 使用TVD-RK2时间积分和slope limiter
        - 正定性保持: 保证 h ≥ 0

    验证状态：
        ✅ MacDonald Test 1-4 (通过)
        ✅ Ritter Dam Break (L2误差 < 5%)
        ✅ Lake at Rest (扰动 < 1e-14)

    示例:
        >>> solver = GodunovFVMSolver(nx=100, length=1000, B=10)
        >>> solver.set_initial_conditions(h=2.0, Q=0.0)
        >>> solver.run(t_end=100.0)
        >>> print(f"Final mass error: {solver.mass_error:.6f}%")

    参考文献：
        - Toro, E.F. (2009). Riemann Solvers and Numerical Methods
          for Fluid Dynamics. Springer.
    """

    def __init__(self,
                 nx: int = 201,
                 length: float = 1000.0,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 riemann_solver: str = 'hll'):
        """初始化求解器

        Args:
            nx: 网格单元数（必须 > 10）
            length: 渠道长度 (m，必须 > 0)
            B: 渠道宽度 (m，必须 > 0)
            S0: 底坡 (无量纲，通常0.0001-0.01)
            n: Manning糙率系数 (通常0.01-0.05)
            riemann_solver: Riemann求解器类型 ('hll' 或 'hllc')

        Raises:
            ValueError: 如果参数不在有效范围

        注意：
            - CFL数默认为0.5，可通过set_cfl()修改
            - 网格为均匀分布，dx = length / nx
        """
        if nx < 10:
            raise ValueError(f"nx={nx} 太小，至少需要10个网格")
        if length <= 0 or B <= 0:
            raise ValueError("length和B必须为正")
        ...
```

**最小要求**:
- ✅ 类：说明功能、验证状态、示例
- ✅ 公共方法：说明参数、返回值、异常
- ✅ 复杂算法：说明理论依据、参考文献

### 3.3 代码组织

#### 规则 R3.3: 文件和模块结构

**目录结构**:
```
HydroClaude/
├── engine/              # 核心引擎（配置、仿真）
│   ├── config_parser.py
│   ├── model_builder.py
│   └── simulation_engine.py
├── solvers/             # 数值求解器（按功能分类）
│   ├── __init__.py
│   ├── godunov_fvm_solver.py      # ✅ 已测试
│   ├── hydrostatic_canal_solver.py # ⚠️ 待测试
│   └── experimental/               # ❌ 实验性代码隔离
│       ├── README.md  # 说明：这些代码未经测试，不要用于生产！
│       └── ...
├── physics/             # 物理模型
│   ├── boundaries.py
│   ├── cross_section.py
│   └── structures/
├── tests/               # 测试（镜像代码结构）
│   ├── test_engine/
│   ├── test_solvers/
│   │   ├── test_godunov_fvm_solver.py
│   │   └── test_hydrostatic_canal_solver.py
│   ├── standard_tests/  # 国际标准测试
│   │   ├── test_macdonald_benchmarks.py
│   │   ├── test_lake_at_rest.py
│   │   └── test_ritter_dam_break.py
│   └── performance/     # 性能测试
└── docs/                # 文档
    ├── api/             # API参考
    ├── user_guide/      # 用户指南
    ├── developer_guide/ # 开发者指南
    └── validation/      # 验证报告
```

**文件大小限制**:
- ✅ 单个文件 < 1000行（建议）
- ✅ 单个文件 < 2000行（最大）
- ❌ > 2000行必须拆分

**函数长度限制**:
- ✅ 单个函数 < 50行（建议）
- ✅ 单个函数 < 100行（最大）
- ❌ > 100行建议拆分成子函数

---

## 第四章：Git工作流

### 4.1 分支策略

#### 规则 R4.1: Git Flow分支模型

**主要分支**:
```
main          # 生产就绪代码，只接受merge
├── develop   # 开发分支，日常开发基准
│   ├── feature/xxx  # 功能分支
│   ├── test/xxx     # 测试分支
│   └── fix/xxx      # 修复分支
└── release/v1.0     # 发布分支
```

**分支命名**:
```bash
# ✅ 正确
feature/macdonald-test-1
test/lake-at-rest
fix/godunov-cfl-bug
release/v1.0.0

# ❌ 错误
my-changes
test
fix
```

### 4.2 Commit规范

#### 规则 R4.2: Conventional Commits

**格式**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）**:
- `feat`: 新功能
- `test`: 新增测试或测试修复
- `fix`: Bug修复
- `refactor`: 重构（不改变功能）
- `docs`: 文档更新
- `perf`: 性能优化
- `chore`: 构建/工具变更

**示例**:
```bash
# ✅ 好的commit
test(solvers): Add MacDonald Test 1 (backwater curve)

Implement MacDonald et al. (1997) Test 1 for steady gradually
varied flow validation.

Test setup:
- Channel: L=1000m, B=10m, S0=0.001, n=0.025
- Flow: Q=20 m³/s, downstream h=2.0m
- Expected: Backwater curve (M1 profile)

Pass criteria:
- Water depth error < 1cm
- Discharge error < 1%

References:
- MacDonald et al. (1997) J. Hydraulic Eng. 123(11):1041-1045

Closes #42

# ❌ 坏的commit
fixed stuff
update
test
```

### 4.3 Code Review

#### 规则 R4.3: Review检查清单

**提交者checklist**:
- [ ] 代码通过所有测试（本地运行`pytest`）
- [ ] 新增功能有对应测试
- [ ] 代码通过linter（`flake8`, `black`）
- [ ] 更新相关文档
- [ ] Commit message符合规范
- [ ] 无调试代码（print, pdb等）
- [ ] 无注释掉的代码

**审查者checklist**:
- [ ] 代码逻辑正确
- [ ] 测试覆盖充分
- [ ] 文档清晰完整
- [ ] 命名规范一致
- [ ] 无安全问题
- [ ] 性能可接受
- [ ] 符合项目架构

---

## 第五章：测试分类与组织

### 5.1 测试层次

#### 规则 R5.1: 测试金字塔

```
        /\
       /  \  E2E测试 (5%)
      /____\
     /      \  集成测试 (15%)
    /________\
   /          \
  /   单元测试  \  单元测试 (80%)
 /______________\
```

**单元测试（Unit Tests）**:
- 测试单个函数/方法
- 快速（< 100ms per test）
- 无外部依赖
- 占比：80%

```python
# test_riemann_solvers.py
def test_hll_flux_positive_speeds():
    """测试HLL通量：正速度情况"""
    F = hll_flux(h_L=2.0, Q_L=10.0, h_R=1.5, Q_R=8.0, ...)
    assert F[0] > 0  # 质量通量为正
    assert F[1] > 0  # 动量通量为正
```

**集成测试（Integration Tests）**:
- 测试组件交互
- 中等速度（< 1s per test）
- 可能有文件I/O
- 占比：15%

```python
# test_solver_integration.py
def test_godunov_with_gate():
    """测试求解器与闸门边界条件集成"""
    solver = GodunovFVMSolver(...)
    gate = SluiceGate(position=500, opening=0.5)
    solver.add_structure(gate)
    solver.run(t_end=100.0)
    assert solver.mass_error < 0.01
```

**端到端测试（E2E Tests）**:
- 测试完整工作流
- 慢速（几秒到几分钟）
- 模拟真实使用
- 占比：5%

```python
# test_e2e_config_driven.py
def test_full_workflow_dam_break():
    """端到端测试：配置驱动溃坝仿真"""
    # 1. 解析配置
    parser = ConfigParser('dam_break.json')
    config = parser.parse()

    # 2. 构建模型
    builder = ModelBuilder.from_config(config)
    solver = builder.build_solver()

    # 3. 运行仿真
    engine = SimulationEngine(solver, config)
    engine.run()

    # 4. 验证输出
    assert Path(config['output']['directory']).exists()
    assert solver.mass_error < 0.01
```

### 5.2 测试标记（Markers）

#### 规则 R5.2: 使用pytest markers分类

**定义markers**:
```python
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, no I/O)
    integration: Integration tests (medium speed)
    e2e: End-to-end tests (slow)
    p0: P0 blocking tests (must pass)
    p1: P1 critical tests (should pass)
    p2: P2 important tests (nice to have)
    slow: Slow tests (> 1s)
    benchmark: Performance benchmarks
    experimental: Experimental features (may fail)
```

**使用**:
```python
@pytest.mark.unit
@pytest.mark.p0
def test_hll_flux_symmetry():
    """P0单元测试：HLL通量对称性"""
    ...

@pytest.mark.slow
@pytest.mark.p1
def test_dam_break_convergence():
    """P1慢速测试：网格收敛性"""
    ...
```

**运行特定测试**:
```bash
# 只运行P0测试
pytest -m p0

# 只运行快速测试（排除slow）
pytest -m "not slow"

# 只运行单元测试
pytest -m unit

# 运行P0和P1，但排除slow
pytest -m "(p0 or p1) and not slow"
```

---

## 第六章：性能优化规范

### 6.1 优化原则

#### 规则 R6.1: 先保证正确，再优化性能

**流程**:
```
1. 实现正确的版本（naive implementation）
2. 编写测试，确认正确性
3. 建立性能基准（baseline）
4. 识别瓶颈（profiling）
5. 优化瓶颈
6. 再次测试，确认仍正确
7. 对比性能，量化提升
```

**禁止**:
- ❌ 未测试先优化
- ❌ 优化后破坏正确性
- ❌ 过早优化（premature optimization）

**示例**:
```python
# Step 1: 正确但慢的版本
def compute_fluxes_slow(h, Q, B, g):
    """计算通量（未优化版本）"""
    n = len(h)
    F_mass = np.zeros(n+1)
    F_momentum = np.zeros(n+1)

    for i in range(n+1):
        # ... 逐个计算

    return F_mass, F_momentum

# Step 2-3: 测试 + 基准
def test_compute_fluxes():
    F_m, F_p = compute_fluxes_slow(...)
    assert_flux_properties(F_m, F_p)  # 验证正确性

def benchmark_compute_fluxes():
    t = timeit(lambda: compute_fluxes_slow(...))
    print(f"Baseline: {t:.3f}s")  # 例如: 2.5s

# Step 4: Profiling
import cProfile
cProfile.run('compute_fluxes_slow(...)')
# 发现瓶颈：HLL求解器调用

# Step 5: 优化（Numba JIT）
from numba import njit

@njit
def compute_fluxes_fast(h, Q, B, g):
    """计算通量（Numba优化版本）"""
    # 相同逻辑，但JIT编译
    ...

# Step 6-7: 验证 + 对比
def test_compute_fluxes_fast():
    F_slow = compute_fluxes_slow(...)
    F_fast = compute_fluxes_fast(...)
    assert np.allclose(F_slow, F_fast)  # 结果一致

def benchmark_compute_fluxes_optimized():
    t = timeit(lambda: compute_fluxes_fast(...))
    print(f"Optimized: {t:.3f}s")  # 例如: 0.05s
    print(f"Speedup: {2.5/0.05:.1f}x")  # 50x加速
```

### 6.2 Numba使用规范

#### 规则 R6.2: Numba JIT编译

**适用场景**:
- ✅ 数值密集计算（循环、数组操作）
- ✅ 瓶颈已确认（profiling）
- ❌ 字符串处理
- ❌ 复杂Python对象

**最佳实践**:
```python
from numba import njit
import numpy as np

# ✅ 好的Numba代码
@njit
def hll_flux_numba(h_L: float, Q_L: float,
                   h_R: float, Q_R: float,
                   B: float, g: float, eps_dry: float):
    """HLL通量计算（Numba加速）

    注意：
        - 使用njit装饰器
        - 避免Python对象
        - 使用NumPy数组
        - 类型注解帮助编译
    """
    # 干床检查
    if h_L < eps_dry and h_R < eps_dry:
        return 0.0, 0.0

    # ... HLL计算 ...

    return F_mass, F_momentum

# ✅ 测试Numba版本与原版一致
def test_numba_consistency():
    """测试Numba版本与Python版本结果一致"""
    # 测试数据
    h_L, Q_L, h_R, Q_R = 2.0, 10.0, 1.5, 8.0

    # Python版本
    F_python = hll_flux_python(h_L, Q_L, h_R, Q_R, ...)

    # Numba版本
    F_numba = hll_flux_numba(h_L, Q_L, h_R, Q_R, ...)

    # 应该一致（浮点误差内）
    assert np.allclose(F_python, F_numba, rtol=1e-14)
```

---

## 第七章：文档要求

### 7.1 文档层次

#### 规则 R7.1: 四层文档结构

**1. 代码注释（Code Comments）**:
- 解释"为什么"，不是"是什么"
- 复杂算法必须注释

```python
# ✅ 好的注释
# 使用Roe平均以提高激波分辨率（Toro 2009, Sec. 11.3）
S_L, S_R = roe_average_speeds(h_L, Q_L, h_R, Q_R)

# ❌ 坏的注释
# 计算S_L和S_R
S_L, S_R = roe_average_speeds(...)
```

**2. Docstrings（函数/类文档）**:
- 所有公共API必须有
- 格式：Google或NumPy style

**3. 用户文档（User Documentation）**:
- 安装指南
- 快速开始
- 教程（Tutorials）
- 常见问题（FAQ）

**4. 技术文档（Technical Documentation）**:
- API参考
- 验证报告（V&V）
- 开发者指南
- 架构设计文档

### 7.2 验证文档

#### 规则 R7.2: V&V报告强制要求

**每个求解器必须有V&V文档**:

```markdown
# GodunovFVMSolver验证报告

## 1. 概述
求解器名称：GodunovFVMSolver
版本：1.0
验证日期：2025-10-28
验证人员：XXX

## 2. 数值方法
- 空间离散：Godunov有限体积法
- 时间积分：TVD-RK2
- Riemann求解器：HLL/HLLC
- Slope limiter：Minmod/Van Leer/Superbee

## 3. 验证测试

### 3.1 P0级测试（5/5通过）

#### Test P0-1: Lake at Rest
- 状态：✅ 通过
- 误差：1.2e-15 (机器精度)
- 详情：[test_lake_at_rest.py](../tests/test_lake_at_rest.py)

#### Test P0-2: Steady Uniform Flow
- 状态：✅ 通过
- 流量误差：0.0001%
- 详情：...

### 3.2 P1级测试（6/6通过）

#### Test P1-1: MacDonald Test 1 (Backwater)
- 状态：✅ 通过
- L2误差：0.8cm (标准 < 1cm)
- 参考：MacDonald et al. (1997)
- 详情：...

## 4. 性能基准

### 4.1 可扩展性
| 网格数 | 时间 | 加速比 |
|--------|------|--------|
| 100 | 0.1s | 1x |
| 1000 | 1.2s | 12x |
| 10000 | 15s | 150x |

结论：接近O(N)线性可扩展性 ✅

### 4.2 Numba加速
- 无Numba：10.5s
- 有Numba：0.2s
- 加速比：52x ✅

## 5. 已知限制
- 仅支持矩形截面
- 不支持干河床重新湿润（wetting/drying）
- CFL > 0.9时可能不稳定

## 6. 结论
GodunovFVMSolver已通过所有P0和P1级测试，满足商业级质量要求。

## 7. 参考文献
1. Toro, E.F. (2009). Riemann Solvers...
2. MacDonald et al. (1997). J. Hydraulic Eng...
```

---

## 第八章：版本发布规范

### 8.1 语义化版本

#### 规则 R8.1: 遵循SemVer 2.0

**格式**: `MAJOR.MINOR.PATCH`

```
v1.2.3
  │ │ └─ PATCH: 修复bug，不改变API
  │ └─── MINOR: 新功能，向后兼容
  └───── MAJOR: 破坏性变更，不兼容旧版本

示例：
v0.1.0 - 初始原型
v0.2.0 - 添加HLLC求解器（新功能）
v0.2.1 - 修复CFL bug（修复）
v1.0.0 - 首个稳定版（所有P0测试通过）
v1.1.0 - 添加闸门支持（新功能）
v2.0.0 - 重构API（破坏性变更）
```

**Pre-release标签**:
```
v1.0.0-alpha.1  # Alpha版本
v1.0.0-beta.2   # Beta版本
v1.0.0-rc.1     # Release Candidate
v1.0.0          # 正式版
```

### 8.2 发布checklist

#### 规则 R8.2: 发布前必须满足

**v1.0.0发布条件**:
- [ ] 所有P0测试通过（5/5）
- [ ] 所有P1测试通过（至少80%）
- [ ] 测试覆盖率 > 80%
- [ ] 完整V&V文档
- [ ] 用户文档完整
- [ ] API文档完整
- [ ] Changelog完整
- [ ] 外部专家评审通过
- [ ] 无已知P0级bug
- [ ] 性能满足基准

**发布流程**:
```bash
# 1. 创建release分支
git checkout -b release/v1.0.0

# 2. 更新版本号
# - setup.py
# - __init__.py
# - CHANGELOG.md

# 3. 运行完整测试套件
pytest --cov --cov-fail-under=80

# 4. 构建文档
cd docs && make html

# 5. Tag版本
git tag -a v1.0.0 -m "Release v1.0.0: First stable release"

# 6. 合并到main
git checkout main
git merge release/v1.0.0

# 7. 推送
git push origin main --tags

# 8. 发布到PyPI（如适用）
python setup.py sdist bdist_wheel
twine upload dist/*
```

---

## 附录A：快速参考

### A.1 日常开发checklist

**开始新功能**:
```bash
# 1. 创建feature分支
git checkout develop
git pull
git checkout -b feature/my-feature

# 2. 先写测试（TDD）
touch tests/test_my_feature.py
# 编写测试

# 3. 运行测试（应该失败）
pytest tests/test_my_feature.py
# 输出：FAILED

# 4. 实现功能
# 编写代码...

# 5. 运行测试（应该通过）
pytest tests/test_my_feature.py
# 输出：PASSED

# 6. 运行所有测试
pytest

# 7. 检查覆盖率
pytest --cov

# 8. Code style
black .
flake8 .

# 9. Commit
git add -A
git commit -m "feat(solvers): Add MacDonald Test 1

Implement backwater curve test for validation.

Closes #42"

# 10. Push并创建PR
git push origin feature/my-feature
# 在GitHub创建Pull Request
```

### A.2 测试命令速查

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_godunov.py

# 运行特定测试
pytest tests/test_godunov.py::test_lake_at_rest

# 只运行P0测试
pytest -m p0

# 排除慢速测试
pytest -m "not slow"

# 详细输出
pytest -v

# 显示print输出
pytest -s

# 停在第一个失败
pytest -x

# 覆盖率报告
pytest --cov=engine --cov=solvers --cov-report=term-missing

# 并行运行（需要pytest-xdist）
pytest -n auto

# Benchmark模式
pytest --benchmark-only
```

### A.3 质量检查命令

```bash
# 代码格式化
black .

# 代码风格检查
flake8 .

# 类型检查
mypy engine/ solvers/

# Import排序
isort .

# 一键检查所有
black . && flake8 . && mypy engine/ solvers/ && pytest --cov
```

---

## 附录B：工具配置

### B.1 pytest.ini

```ini
[pytest]
minversion = 6.0
addopts = -ra -q --strict-markers
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, no I/O)
    integration: Integration tests (medium speed)
    e2e: End-to-end tests (slow)
    p0: P0 blocking tests (must pass)
    p1: P1 critical tests (should pass)
    p2: P2 important tests (nice to have)
    slow: Slow tests (> 1s)
    benchmark: Performance benchmarks
    experimental: Experimental features (may fail)

# 覆盖率配置
[coverage:run]
source = engine, solvers, physics
omit =
    */tests/*
    */experimental/*
    */__pycache__/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
```

### B.2 .flake8

```ini
[flake8]
max-line-length = 100
extend-ignore = E203, E266, E501, W503
exclude =
    .git,
    __pycache__,
    build,
    dist,
    .eggs,
    *.egg-info,
    .tox,
    .venv,
    experimental/
max-complexity = 10
```

### B.3 pyproject.toml (Black)

```toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
  | experimental
)/
'''

[tool.isort]
profile = "black"
line_length = 100
```

---

## 附录C：违规处理

### C.1 违规级别

| 级别 | 描述 | 示例 | 处理 |
|------|------|------|------|
| **P0 - 严重** | 破坏质量基准 | 提交未测试代码 | 立即回滚PR |
| **P1 - 重要** | 违反规范 | Commit message不规范 | 要求修正 |
| **P2 - 轻微** | 风格问题 | 缺少docstring | Code review提醒 |

### C.2 违规记录

**维护违规记录**:
```markdown
# VIOLATIONS.md

## 2025-10-28

### Violation #001 (P0)
- **提交者**: XXX
- **PR**: #123
- **问题**: 提交未经测试的HydrostaticCanalSolver
- **处理**: PR rejected, 要求补充测试
- **状态**: ✅ 已修复 (PR #124)

### Violation #002 (P1)
- **提交者**: YYY
- **Commit**: abc1234
- **问题**: Commit message不符合Conventional Commits
- **处理**: 要求修正commit message
- **状态**: ✅ 已修复
```

---

## 结论

本开发规范是**强制性**的，所有代码贡献者必须遵守。

**核心要求总结**:
1. ✅ **测试先行**：先写测试，再写代码
2. ✅ **100%测试通过**：不允许提交失败的测试
3. ✅ **覆盖率 > 80%**：新代码必须有测试
4. ✅ **通过标准测试**：MacDonald, Ritter等必须通过
5. ✅ **代码风格一致**：使用black, flake8
6. ✅ **文档完整**：Docstrings, V&V报告
7. ✅ **版本控制规范**：Git Flow, Conventional Commits

**记住**:
> **质量不是检查出来的，而是构建出来的**

通过遵循这些规范，我们将构建一个**可信赖的、商业级的**1D水力学仿真系统。

---

**文档版本**: 1.0
**生效日期**: 2025-10-28
**维护者**: HydroClaude Team
**修订历史**:
- 2025-10-28: v1.0初始版本

