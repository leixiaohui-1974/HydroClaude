# Phase 8.3 技术文档 - 工程案例库

**日期**: 2025-10-31
**阶段**: Stage 8 - Phase 8.3
**状态**: 🚧 开发中
**目标**: 通过实际工程案例展示Phase 8.1+8.2的改进效果

---

## 📊 执行摘要

基于Phase 8.1（正定性保持WENO3）和Phase 8.2（湿干界面增强）的数值方法改进，创建工程案例库展示实际应用价值。

**核心成果**（预期）:
- ✅ 案例1: 溃坝模拟（Dam Break Simulation）
- ✅ 案例2: 河道洪水演进（Flood Routing）
- ✅ 案例3: 水库泄洪优化（Reservoir Release Optimization）
- ✅ 工程案例可视化框架
- 🚧 总计~2500行代码+文档

---

## 🎯 Phase 8.3策略调整

### 原规划 vs 修订方案

**原Stage 8规划**（Phase 8.3）:
- 6个复杂工程系统（水电调度、供水管网、灌溉控制等）
- 每个案例300-500行
- 时间：3-4周

**修订方案**（聚焦Phase 8.1+8.2展示）:
- 3-4个基础案例，展示数值方法改进
- 每个案例200-400行
- 时间：1-2周
- **重点**：对比Phase 8.1+8.2与原始方法的效果

### 修订原因

1. **聚焦核心价值**: Phase 8.1+8.2的价值在于提升数值精度和稳定性
2. **展示改进效果**: 需要能清晰对比改进前后的案例
3. **可持续发展**: 基础案例库建立后，Stage 9+10可扩展复杂案例
4. **实际可行**: 1-2周内完成高质量基础案例库

---

## 🏗️ 案例清单

### 案例1: 溃坝模拟（Dam Break Simulation）

**工程背景**:
- 水坝溃决是水利工程中最严重的灾害
- 需要精确预测洪水波传播速度和淹没范围
- 涉及干床、激波、湿干界面

**物理特征**:
```
初始状态:
┌────────┐
│  水库  │ h=10m   空地 h=0
│████████│
└────────┘────────────────
   坝

溃坝后:
    ╱╲  激波波前
   ╱  ╲
  ╱    ╲
 ╱  洪水 ╲
╱        ╲___________
湿干界面 ↑  干床扩展
```

**数值挑战**:
1. **干床问题**: h=0区域，常规方法易失败
2. **激波捕捉**: 溃坝波前是强激波
3. **湿干界面**: 水流前沿需要特殊处理
4. **质量守恒**: 长时间模拟不能有质量泄漏

**Phase 8.1+8.2优势**:
- ✅ Phase 8.1正定性保持 → 激波无过冲
- ✅ Phase 8.2湿干界面 → 干床稳定扩展
- ✅ 质量守恒 → 长时间准确

**案例配置**:

**配置A: 经典溃坝**（Stoker解析解）
```python
# 初值
h_upstream = 10.0  # 上游水深
h_downstream = 0.0  # 下游干床
dam_position = 500.0  # 坝位置
channel_length = 2000.0
channel_width = 50.0

# 物理参数
manning_n = 0.0  # 无摩阻（与解析解对比）
slope = 0.0
g = 9.81

# 模拟时间
t_end = 30.0  # 30秒
```

**配置B: 真实地形溃坝**
```python
# 下游有村镇、道路、建筑物
terrain = realistic_topography(...)
structures = [village1, village2, road, bridge]

# 关键输出
- 洪水到达时间
- 最大水深
- 流速峰值
- 淹没面积
```

**代码结构**:
```
examples/case_library/case_01_dam_break/
├── dam_break_classical.py      # 经典溃坝（对比解析解）
├── dam_break_realistic.py      # 真实地形溃坝
├── dam_break_comparison.py     # 对比Phase 8.1+8.2 vs 原始
├── visualize_dam_break.py      # 可视化工具
└── README.md                   # 案例文档
```

**预期成果**:
- ✅ 与Stoker解析解误差<5%（Phase 8.1+8.2）vs >20%（原始）
- ✅ 质量守恒误差<0.1% vs >1%
- ✅ 完整可视化（时空演化、流速矢量图等）

---

### 案例2: 河道洪水演进（Flood Routing）

**工程背景**:
- 洪水预报和调度的核心问题
- 输入：上游入流过程线
- 输出：下游出流过程线
- 关键：洪峰削减、洪峰滞后时间

**物理特征**:
```
上游入流过程线:
Q(t) = Q_base + Q_peak * exp(-(t-t_peak)²/σ²)

┌───┐
│▲  │        入流
│ ▲ │      ╱╲
│  ▲│     ╱  ╲___
└───┘____╱________  基流

河道（L=50km）:
摩阻 + 底坡 → 洪峰削减 + 滞后

出流:
    ╱╲  削减后
   ╱  ╲___
__╱_______  滞后Δt
```

**数值挑战**:
1. **摩阻源项**: Manning公式在高流速时刚性大
2. **长河段模拟**: 需要高效稳定格式
3. **精度要求**: 洪峰值误差<3%，滞后时间误差<10%

**Phase 8.1+8.2优势**:
- ✅ WENO3高精度 → 洪峰捕捉准确
- ✅ 正定性保持 → 数值稳定
- ✅ 长时间模拟 → 24-72小时洪水过程

**案例配置**:

**配置A: 矩形河道**
```python
# 河道参数
length = 50000.0  # 50km
width = 100.0
manning_n = 0.025
slope = 0.0001  # 1:10000

# 入流过程线（三角形）
Q_base = 100.0  # m³/s
Q_peak = 2000.0  # m³/s
t_peak = 6.0  # 小时
duration = 24.0  # 小时

# 网格
n_cells = 1000  # 精细网格

# 观测点
stations = [0, 10000, 25000, 40000, 50000]  # 5个站点
```

**配置B: 天然河道**
```python
# 实际断面数据（梯形/复式）
cross_sections = load_survey_data("river_sections.csv")

# 糙率分区
manning_n = {
    'main_channel': 0.025,
    'floodplain': 0.050,
    'vegetation': 0.080
}

# 实测洪水对比
observed_data = load_gauge_data("2020_flood_event.csv")
```

**关键指标**:

| 指标 | 原始WENO3 | Phase 8.1+8.2 | 目标 |
|------|-----------|---------------|------|
| 洪峰值误差 | 5-8% | **<3%** | <5% |
| 滞后时间误差 | 15-20min | **<10min** | <15min |
| 质量守恒 | >1% | **<0.1%** | <0.5% |
| 数值振荡 | 有 | **无** | 无 |

**代码结构**:
```
examples/case_library/case_02_flood_routing/
├── flood_routing_simple.py      # 简单河道
├── flood_routing_natural.py     # 天然河道
├── flood_routing_comparison.py  # 对比不同方法
├── visualize_flood_routing.py   # 可视化
└── README.md
```

---

### 案例3: 水库泄洪优化（Reservoir Release Optimization）

**工程背景**:
- 水库调度的核心问题：如何泄洪以平衡防洪和发电
- 决策变量：闸门开度随时间变化
- 约束条件：下游水位/流量限制
- 优化目标：最大发电量或最小洪峰

**物理特征**:
```
系统组成:
┌──────────┐
│  水库    │ 库容V, 水位H
│  ████    │
└────┬─────┘
     │ 泄洪闸
     ↓ Q_release(t)
  下游河道 → 控制断面
```

**控制问题**:
```python
# 决策变量
release_schedule = [Q(t0), Q(t1), ..., Q(tn)]

# 约束
H_min ≤ H_reservoir(t) ≤ H_max
Q_downstream(x_control) ≤ Q_safe

# 目标函数
maximize: ∫ Power(Q, H) dt  # 最大发电
或
minimize: max(Q_downstream(t))  # 最小洪峰
```

**数值挑战**:
1. **水库-河道耦合**: 水位影响泄洪，泄洪影响水位
2. **优化算法**: PSO/GA + 水动力模型
3. **多目标权衡**: 防洪 vs 发电 vs 供水

**Phase 8.1+8.2优势**:
- ✅ 高精度 → 准确预测下游流量
- ✅ 快速计算 → 优化迭代次数可达数百次
- ✅ 稳定性 → 极端工况不崩溃

**案例配置**:

**配置A: 单库单目标**
```python
# 水库参数
storage_capacity = 5e8  # m³
H_normal = 150.0  # 正常蓄水位
H_flood = 153.0  # 防洪限制水位
spillway_width = 50.0

# 下游河道
channel_length = 100000.0  # 100km
control_point = 50000.0  # 50km处有城市
Q_safe_control = 5000.0  # 安全流量

# 入库洪水
Q_inflow = flood_hydrograph(Q_peak=8000, duration=48)

# 优化
method = 'PSO'  # 粒子群优化
n_particles = 50
n_iterations = 100
objective = 'minimize_downstream_peak'
```

**配置B: 双库协调**
```python
# 梯级水库
reservoir_1 = {...}  # 上游
reservoir_2 = {...}  # 下游

# 联合调度
coordination_strategy = 'upstream_first'  # 上游先泄
或
coordination_strategy = 'optimal_allocation'  # 最优分配
```

**优化性能**:

| 方案 | 下游洪峰 (m³/s) | 发电量 (MW·h) | 计算时间 |
|------|----------------|---------------|----------|
| 无调度 | 8000 | 5000 | - |
| 经验规则 | 6500 | 4200 | <1s |
| PSO优化 | 5200 | 4800 | ~5min |

**代码结构**:
```
examples/case_library/case_03_reservoir_optimization/
├── reservoir_single.py           # 单库优化
├── reservoir_cascade.py          # 梯级优化
├── optimization_algorithms.py    # PSO/GA算法
├── visualize_optimization.py     # 可视化
└── README.md
```

---

### 案例4（可选）: 明渠缓变流（Gradually Varied Flow）

**工程背景**:
- 水利工程设计的基础问题
- 确定水面线形态
- 判断临界流、缓流、急流

**经典问题**:
1. M1/M2/M3水面线
2. 临界水深处的数值处理
3. 跌水/陡坡/缓坡组合

**Phase 8.1+8.2优势**:
- ✅ 临界流稳定计算（Fr≈1时不振荡）
- ✅ 跌水处正定性保持

---

## 🎨 工程案例可视化框架

### 统一可视化模块

**文件**: `examples/case_library/visualization_framework.py` (~400行)

**功能**:
1. **时空演化动画**
```python
def create_spacetime_animation(
    x, t, h, u,
    title="Flood Evolution",
    save_path="animation.mp4"
):
    """
    创建时空演化动画

    输出:
    - 水深随时间和空间的变化
    - 可选：流速矢量场
    """
```

2. **对比图表**
```python
def plot_method_comparison(
    results: Dict[str, SimulationResult],
    metrics: List[str] = ['h', 'u', 'Fr'],
    save_path: str = None
):
    """
    对比不同方法

    输入:
    - results['WENO3']: 原始WENO3结果
    - results['PP-WENO3']: Phase 8.1结果
    - results['WD-Enhanced']: Phase 8.2结果

    输出:
    - 3×N子图对比
    """
```

3. **专业工程报告**
```python
def generate_engineering_report(
    case_name: str,
    simulation_results: Dict,
    save_path: str = "report.pdf"
):
    """
    生成工程报告（PDF）

    内容:
    1. 案例概述
    2. 模拟参数
    3. 结果图表
    4. 误差分析
    5. 结论建议
    """
```

4. **交互式可视化**
```python
def create_interactive_dashboard(
    simulation_results: Dict,
    port: int = 8050
):
    """
    创建交互式Dashboard（Plotly Dash）

    功能:
    - 时间滑块
    - 参数调整
    - 实时对比
    """
```

---

## 📊 性能对比基准

### 对比维度

**每个案例都包含对比测试**:

```python
def run_case_comparison(case_config):
    """
    运行案例对比

    对比方法:
    1. 原始WENO3
    2. Phase 8.1 PP-WENO3
    3. Phase 8.2 WD-Enhanced-WENO3

    对比指标:
    - 精度（L2误差）
    - 稳定性（h_min, CFL崩溃）
    - 质量守恒
    - 计算时间
    """
    results = {}

    # 方法1: 原始WENO3
    results['WENO3'] = run_simulation(
        solver_class=GodunvFVMWENO3,
        config=case_config
    )

    # 方法2: PP-WENO3 (Phase 8.1)
    results['PP-WENO3'] = run_simulation(
        solver_class=PositivityPreservingWENO3,
        config=case_config,
        use_pp=True
    )

    # 方法3: WD-Enhanced (Phase 8.2)
    results['WD-Enhanced'] = run_simulation(
        solver_class=WetDryEnhancedWENO3,
        config=case_config,
        use_pp=True,
        use_wd_flux=True
    )

    # 生成对比报告
    report = generate_comparison_report(results)

    return results, report
```

### 预期改进

**案例1: 溃坝模拟**

| 指标 | WENO3 | Phase 8.1 | Phase 8.2 | 改进 |
|------|-------|-----------|-----------|------|
| L2误差 | 23.4% | 18.2% | **12.5%** | 46%↓ |
| 质量守恒 | 1.2% | 0.3% | **0.05%** | 96%↓ |
| h_min | -0.002 | 0.0 ✅ | 0.0 ✅ | 稳定 |

**案例2: 洪水演进**

| 指标 | WENO3 | Phase 8.1 | Phase 8.2 | 改进 |
|------|-------|-----------|-----------|------|
| 洪峰误差 | 6.8% | 4.2% | **2.8%** | 59%↓ |
| 滞后误差 | 18min | 12min | **8min** | 56%↓ |
| 计算时间 | 1.0× | 1.15× | 1.25× | +25% |

**案例3: 水库优化**

| 指标 | WENO3 | Phase 8.1 | Phase 8.2 | 改进 |
|------|-------|-----------|-----------|------|
| 优化收敛 | 80% | 95% | **98%** | 稳定 |
| 最优解质量 | - | - | **+5%** | 更优 |
| 单次评估 | 2.0s | 2.3s | 2.5s | +25% |

---

## 🧪 测试策略

### 单元测试

**文件**: `tests/case_library/test_engineering_cases.py`

```python
def test_case01_dam_break_mass_conservation():
    """案例1：质量守恒测试"""
    result = run_dam_break_simulation(...)
    mass_error = result['mass_conservation_error']
    assert mass_error < 0.1, f"质量误差{mass_error}%超标"

def test_case01_dam_break_positivity():
    """案例1：正定性测试"""
    result = run_dam_break_simulation(...)
    assert np.all(result['h'] >= 0), "存在负水深"

def test_case02_flood_routing_peak_accuracy():
    """案例2：洪峰精度测试"""
    result = run_flood_routing_simulation(...)
    peak_error = compute_peak_error(result, observed_data)
    assert peak_error < 3.0, f"洪峰误差{peak_error}%超标"

def test_case03_reservoir_optimization_convergence():
    """案例3：优化收敛测试"""
    result = run_reservoir_optimization(...)
    assert result['converged'], "优化未收敛"
    assert result['iterations'] < 200, "迭代次数过多"
```

### 集成测试

```python
def test_full_case_pipeline():
    """完整案例流程测试"""
    # 1. 运行模拟
    results = run_case_comparison(case_config)

    # 2. 生成可视化
    fig = plot_method_comparison(results)
    assert fig is not None

    # 3. 生成报告
    report = generate_engineering_report(results)
    assert os.path.exists(report)
```

---

## 📚 文档结构

### 每个案例的文档

**结构**:
```
案例X: XXXXX
├── 1. 工程背景
├── 2. 物理模型
├── 3. 数值方法
├── 4. 代码说明
├── 5. 运行指南
├── 6. 结果分析
├── 7. Phase 8.1+8.2改进效果
└── 8. 参考文献
```

**示例** (`examples/case_library/case_01_dam_break/README.md`):

```markdown
# 案例1: 溃坝模拟

## 1. 工程背景

水坝溃决是水利工程中最严重的灾害...

## 2. 物理模型

Saint-Venant方程...

## 3. 数值方法

本案例对比三种方法:
- 原始WENO3
- Phase 8.1 PP-WENO3
- Phase 8.2 WD-Enhanced-WENO3

## 4. 代码说明

主要文件:
- `dam_break_classical.py`: 经典溃坝
- `dam_break_comparison.py`: 方法对比

## 5. 运行指南

```bash
# 运行经典溃坝
python dam_break_classical.py

# 运行方法对比
python dam_break_comparison.py --solver all --plot
```

## 6. 结果分析

[图表]

## 7. Phase 8.1+8.2改进效果

| 指标 | 改进 |
|------|------|
| L2误差 | 46%↓ |
| 质量守恒 | 96%↓ |

## 8. 参考文献

...
```

---

## 🚀 开发计划

### Week 1: 案例1 + 可视化框架（5天）

**Day 1-2**: 溃坝模拟核心代码
- `dam_break_classical.py`
- `dam_break_comparison.py`

**Day 3**: 可视化框架
- `visualization_framework.py`

**Day 4**: 测试和文档
- 单元测试
- README

**Day 5**: 运行验证和优化

### Week 2: 案例2 + 案例3（5天）

**Day 6-7**: 洪水演进
- `flood_routing_simple.py`
- `flood_routing_comparison.py`

**Day 8-9**: 水库优化
- `reservoir_single.py`
- `optimization_algorithms.py`

**Day 10**: 集成测试和总结文档

---

## 🎯 成功标准

**Phase 8.3达标条件**:
- ✅ 完成3个核心案例（溃坝、洪水演进、水库优化）
- ✅ 每个案例都展示Phase 8.1+8.2改进效果
- ✅ 统一可视化框架
- ✅ 完整文档和测试
- ✅ 所有案例误差指标达标

**当前状态**: 🚧 规划完成，待实现

---

## 💡 技术要点

### 代码复用

**充分利用Phase 8.1+8.2成果**:
```python
# 案例代码结构
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from solvers.positivity_preserving_weno3 import PositivityPreservingWENO3
from solvers.wet_dry_enhanced_weno3 import WetDryEnhancedWENO3

# 所有案例共享相同的求解器
solvers = {
    'WENO3': GodunvFVMWENO3,
    'PP-WENO3': PositivityPreservingWENO3,
    'WD-Enhanced': WetDryEnhancedWENO3
}

# 只需实现案例特定的：
# - 初始条件
# - 边界条件
# - 后处理
```

### 工程价值

**展示实际应用价值**:
1. **溃坝模拟**: 防洪减灾、应急预案
2. **洪水演进**: 洪水预报、调度决策
3. **水库优化**: 发电效益、防洪安全

---

**文档版本**: 1.0
**作者**: Claude Code (Anthropic)
**创建日期**: 2025-10-31
**下次更新**: 开始实现后

---

**🤖 Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**
