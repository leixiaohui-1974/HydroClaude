# HydroClaude 示例代码快速索引
# Examples Quick Reference Index

**版本**: 2.1
**更新日期**: 2025-10-27
**目的**: 帮助开发者快速找到参考示例，避免重复造轮子

---

## 🎯 快速查询表

### 当你需要...请参考这个示例

| 需求场景 | 使用的基础库 | 参考示例 | 关键代码 |
|---------|------------|---------|---------|
| **基本渠道流动** | HydrostaticCanalSolver | `examples/example_01_canal_flow/scripts/01_basic_v2.py` | 稳态求解 + 验证 |
| **单个闸门** | SluiceGate + ResultValidator | `examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py` | 闸门流量验证 |
| **多个闸门串联** | 多个 SluiceGate | `examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py` | 三闸门场景 |
| **宽顶堰** | BroadCrestedWeir | `examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py` | 混合结构 |
| **孔口** | Orifice | `examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py` | 混合结构 |
| **边界条件设置** | solve_steady_state | `examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py` | 上下游边界 |
| **稳态求解优化** | convergence_tol | `examples/example_01_canal_flow/scripts/08_optimized_steady_solving_v2.py` | 宽松容差 |
| **绘制纵剖面图** | PlotHelper.plot_profile | `examples/example_01_canal_flow/scripts/01_basic_v2.py` | 水面线剖面 |
| **绘制流量分布** | PlotHelper.plot_profile | `examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py` | 流量验证图 |
| **流量守恒验证** | ResultValidator | `examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py` | 自动分级 |
| **计算均匀流水深** | canal_utils.compute_steady_uniform_flow | 所有 v2 示例 | 初始化 |
| **计算临界水深** | canal_utils.compute_critical_depth | `examples/` | 回水曲线分析 |
| **非恒定流模拟** | Canal (Preissmann) | `examples/example_08_preissmann_vs_fvm/example_08_preissmann_demo.py` | 时间步进 |
| **PID控制** | PIDController | `examples/example_control/` | 水位控制 |
| **MPC控制** | MPCController | `examples/example_control/` | 预测控制 |
| **IDZ模型** | IDZParameters, IDZModel | `examples/advanced_examples/idz_saint_venant_integration.py` | 在线辨识 |
| **性能基准测试** | PerformanceBenchmark | `examples/advanced_examples/benchmark_controllers.py` | 控制器对比 |
| **长距离调水** | 多池段+泵站+闸门 | `examples/real_world_cases/long_distance_water_transfer.py` | 100km工程 |

---

## 📚 按功能分类的示例

### 1. 基础功能（必学）⭐⭐⭐

#### 1.1 最简单的示例
```
examples/example_simple_canal/run.py
```
- ✅ 10行核心代码
- ✅ 自动验证
- ✅ 自动绘图
- 🎯 适合：第一次使用 HydroClaude

#### 1.2 基本渠道流动
```
examples/example_01_canal_flow/scripts/01_basic_v2.py
```
- ✅ 使用 HydrostaticCanalSolver
- ✅ 使用 ResultValidator 验证
- ✅ 使用 PlotHelper 绘图
- 🎯 适合：学习标准代码结构

#### 1.3 边界条件
```
examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py
```
- ✅ 上游流量边界
- ✅ 下游水深边界
- 🎯 适合：理解边界条件设置

---

### 2. 水工结构（常用）⭐⭐⭐

#### 2.1 单闸门
```
examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py
```
**关键代码**：
```python
from solvers.gate import SluiceGate

gate = SluiceGate(position=5000.0, width=10.0, opening=5.0)
solver = HydrostaticCanalSolver(..., internal_structures=[(5000.0, gate)])
```

#### 2.2 多闸门串联
```
examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py
```
**关键代码**：
```python
gate1 = SluiceGate(position=2500.0, width=10.0, opening=4.5)
gate2 = SluiceGate(position=5000.0, width=10.0, opening=5.5)
gate3 = SluiceGate(position=7500.0, width=10.0, opening=5.0)

solver = HydrostaticCanalSolver(
    ...,
    internal_structures=[
        (2500.0, gate1),
        (5000.0, gate2),
        (7500.0, gate3)
    ]
)
```

#### 2.3 混合结构（闸门+堰+孔口）
```
examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py
```
**关键代码**：
```python
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice

gate = SluiceGate(...)
weir = BroadCrestedWeir(...)
orifice = Orifice(...)

solver = HydrostaticCanalSolver(
    ...,
    internal_structures=[
        (2500.0, gate),
        (5000.0, weir),
        (7500.0, orifice)
    ]
)
```

#### 2.4 泵站
```
examples/example_gate_pump_cascade/
examples/real_world_cases/long_distance_water_transfer.py
```
**关键代码**：
```python
from solvers.gate import PumpStation

pump = PumpStation(position=25000.0, rated_flow=20.0, head=10.0)
```

---

### 3. 求解优化（提升性能）⭐⭐

#### 3.1 稳态求解优化
```
examples/example_01_canal_flow/scripts/08_optimized_steady_solving_v2.py
```
**关键技巧**：
```python
# 推荐：宽松容差，极快收敛（0-1次迭代）
result = solver.solve_steady_state(
    Q_target=10.0,
    h_downstream=h_uniform,
    convergence_tol=0.1,  # 宽松容差
    dt=0.5,
    verbose=True
)
```

---

### 4. 验证与可视化（必须使用）⭐⭐⭐

#### 4.1 结果验证
```
examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py
```
**关键代码**：
```python
from utils.result_validator import quick_validate_steady_state

# 一行搞定验证
validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=10.0,
    name="单闸门测试"
)
# 自动输出：收敛状态 + 流量误差 + 闸门验证
```

#### 4.2 纵剖面图
```
examples/example_01_canal_flow/scripts/01_basic_v2.py
```
**关键代码**：
```python
from utils.plot_helper import PlotHelper

plotter = PlotHelper()
fig = plotter.plot_profile(
    x / 1000,  # 转换为km
    h,
    xlabel="Distance (km)",
    ylabel="Water Depth (m)",
    structures=[(5.0, "Gate")],  # 自动标注结构物
    save_path="results/profile.png"
)
```

#### 4.3 流量分布验证图
```
examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py
```
**关键代码**：
```python
fig = validator.plot_flow_distribution(
    x=solver.x,
    Q=result['Q'],
    Q_target=10.0,
    gate_positions=[5000.0],
    save_path="results/flow_validation.png"
)
```

---

### 5. 非恒定流（时变模拟）⭐⭐

#### 5.1 Preissmann求解器
```
examples/example_08_preissmann_vs_fvm/example_08_preissmann_demo.py
```
**关键代码**：
```python
from physics.canal import Canal

canal = Canal(
    name="Canal",
    volume_min=0,
    volume_max=10000,
    length=5000.0,
    width=10.0,
    slope=0.001,
    manning_n=0.025,
    method='preissmann',  # 唯一可用
    n_sections=51
)

# 时间步进
for step in range(n_steps):
    canal.update_high_fidelity(dt, {
        'upstream_flow': 20.0,
        'downstream_flow': 20.0
    })
```

#### 5.2 时变边界条件
```
examples/example_time_varying_bc/run_all.py
```
- 正弦波边界（潮汐）
- 阶跃边界（突发事件）
- 线性边界（渐进过程）

---

### 6. 控制系统（高级）⭐⭐⭐

#### 6.1 PID控制
```
examples/example_control/config_pid_water_level.yaml
```
**运行方法**：
```bash
python -m modeling.universal_modeler examples/example_control/config_pid_water_level.yaml
```

#### 6.2 MPC控制
```
examples/example_control/config_mpc_tuned.yaml
```

#### 6.3 IDZ模型与在线辨识
```
examples/advanced_examples/idz_saint_venant_integration.py
```
**关键代码**：
```python
from control.idz_model import IDZParameters, IDZModel
from control.online_identification import IDZIdentifier

# 从水力学参数计算IDZ参数
params = IDZParameters.from_hydraulics(
    length=1000.0, width=10.0, bed_slope=0.0001,
    manning=0.025, normal_depth=2.0
)

# 在线辨识
identifier = IDZIdentifier(dt=10.0)
for u, y in data:
    identified_params = identifier.update(u, y)
```

#### 6.4 控制器性能对比
```
examples/advanced_examples/benchmark_controllers.py
```
**功能**：
- PID vs MPC vs 自适应MPC
- MAE、RMSE、超调量、计算时间

---

### 7. 工程案例（实战）⭐⭐⭐

#### 7.1 灌溉渠道设计
```
examples/engineering_cases/case_01_irrigation_design/
```

#### 7.2 防洪应急响应
```
examples/engineering_cases/case_02_flood_emergency/
```

#### 7.3 多闸门协同控制
```
examples/engineering_cases/case_03_multi_gate_control/
```

#### 7.4 参数在线校准
```
examples/engineering_cases/case_04_parameter_calibration/
```

#### 7.5 水资源优化调度
```
examples/engineering_cases/case_05_water_resource_optimization/
```

#### 7.6 长距离调水工程（100km）
```
examples/real_world_cases/long_distance_water_transfer.py
```
**规模**：
- 10个池段（每段10km）
- 3座泵站（总扬程50m）
- 7个闸门
- 24小时仿真

---

## ❌ 禁止参考的旧示例

以下示例使用了废弃的API，**不要参考**：

- ❌ 任何不含 `_v2` 后缀的脚本（example_01_canal_flow/scripts/）
- ❌ 使用 `SingleCanalSolver` 的示例
- ❌ 使用 `CanalSolver` 的示例
- ❌ 使用 `MOCSolver` 的示例
- ❌ 手写验证代码的示例（不使用 ResultValidator）

---

## 🔍 快速搜索技巧

### 按关键字搜索

**求解器**：
```bash
grep -r "HydrostaticCanalSolver" examples/
```

**验证**：
```bash
grep -r "quick_validate_steady_state" examples/
```

**闸门**：
```bash
grep -r "SluiceGate" examples/
```

**绘图**：
```bash
grep -r "PlotHelper" examples/
grep -r "plot_profile" examples/
```

---

## 📖 学习路径推荐

### 新手路径（2小时）

```
1. examples/example_simple_canal/run.py (10分钟)
   → 运行第一个示例

2. examples/example_01_canal_flow/scripts/01_basic_v2.py (30分钟)
   → 理解标准代码结构

3. examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py (30分钟)
   → 学习水工结构

4. examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py (30分钟)
   → 掌握复杂场景

5. 自己修改参数，观察结果 (30分钟)
```

### 进阶路径（4小时）

```
1. 控制系统示例 (1小时)
   → examples/example_control/

2. 工程案例 (2小时)
   → examples/engineering_cases/

3. 高级功能 (1小时)
   → examples/advanced_examples/
```

---

## 🎯 常见问题速查

### Q1: 如何设置闸门？
**A**: 参考 `examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py`

### Q2: 如何验证流量守恒？
**A**: 使用 `quick_validate_steady_state`，参考所有 v2 示例

### Q3: 如何绘制纵剖面图？
**A**: 使用 `PlotHelper.plot_profile`，参考 `01_basic_v2.py`

### Q4: 如何提高收敛速度？
**A**: 使用宽松容差（convergence_tol=0.1），参考 `08_optimized_steady_solving_v2.py`

### Q5: 如何实现多闸门？
**A**: 参考 `12_advanced_optimized_v2.py`

### Q6: 如何做非恒定流模拟？
**A**: 使用 Canal (Preissmann)，参考 `example_08_preissmann_demo.py`

### Q7: 如何实现PID/MPC控制？
**A**: 参考 `examples/example_control/`

### Q8: 如何对比不同控制策略？
**A**: 参考 `examples/advanced_examples/benchmark_controllers.py`

---

## 📚 相关文档

- **完整API**: `LIBRARY_REFERENCE.md`
- **开发规范**: `DEVELOPMENT_GUIDE.md`
- **最佳实践**: `SCRIPT_UPGRADE_SUMMARY.md`
- **AI开发规则**: `.cursorrules`

---

**Generated by HydroClaude Development Team**
**Last Updated: 2025-10-27**
