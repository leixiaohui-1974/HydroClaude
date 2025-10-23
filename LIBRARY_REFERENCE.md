# HydroClaude 基础类库参考手册
# Library Reference Manual

**版本**: 1.0
**更新日期**: 2025-10-23

---

## 📋 快速索引

| 类别 | 库/模块 | 文件路径 | 核心功能 |
|-----|--------|---------|---------|
| **求解器** | HydrostaticCanalSolver | `solvers/hydrostatic_canal_solver.py` | Phase 2高精度求解 |
| **结构** | gate.py | `solvers/gate.py` | 闸门/堰/孔口 |
| **验证** | ResultValidator | `utils/result_validator.py` | 自动验证与分级 |
| **可视化** | VisualizationTemplates | `utils/visualization_templates.py` | 18种专业图表 |
| **水力学** | canal_utils | `utils/canal_utils.py` | 水力学计算 |
| **输出** | output_helper | `examples/.../output_helper.py` | 文件管理 |

---

## 1️⃣ HydrostaticCanalSolver - 高精度求解器

### 📍 位置
```
solvers/hydrostatic_canal_solver.py
```

### 🎯 核心功能

Phase 2静水重构方法求解器，专为高精度流量守恒设计

**特点**:
- ✅ 流量误差 < 0.000001%
- ✅ 稳态求解 0-1次迭代
- ✅ 支持闸门/堰/孔口
- ✅ 正水深保证
- ✅ C-property保持

### 📖 完整API

#### 构造函数

```python
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

solver = HydrostaticCanalSolver(
    length,                    # 渠道长度 (m)
    nx,                        # 网格数
    B,                         # 渠道宽度 (m)
    S0,                        # 渠底坡度
    n,                         # Manning糙率系数
    internal_structures=None,  # 内部结构列表
    g=9.81                     # 重力加速度 (m/s²)
)
```

**参数说明**:
- `internal_structures`: 格式为 `[(位置, 结构对象), ...]`
  ```python
  internal_structures=[
      (2500.0, gate1),
      (5000.0, weir),
      (7500.0, gate2)
  ]
  ```

#### 主要属性

```python
solver.x          # x坐标数组 (nx,)
solver.h          # 水深数组 (nx,)
solver.hu         # 单宽流量数组 (nx,)
solver.dx         # 空间步长
solver.B          # 渠道宽度
solver.S0         # 底坡
solver.n          # Manning糙率
solver.current_time  # 当前时间
```

#### 方法1: 稳态求解 (最常用)

```python
result = solver.solve_steady_state(
    Q_target,              # 目标流量 (m³/s)
    h_downstream,          # 下游边界水深 (m)
    max_iterations=5000,   # 最大迭代次数
    convergence_tol=0.1,   # 收敛容差（推荐0.1）
    dt=0.5,                # 伪时间步长 (s)
    verbose=True           # 是否打印详细信息
)
```

**返回值** (`result` 字典):
```python
{
    'converged': bool,           # 是否收敛
    'iterations': int,           # 迭代次数
    'Q_error_percent': float,    # 流量误差百分比
    'h': np.ndarray,             # 最终水深分布
    'Q': np.ndarray,             # 最终流量分布 (hu数组)
    'Q_mean': float,             # 平均流量
    'Q_std': float,              # 流量标准差
    'h_min': float,              # 最小水深
    'h_max': float               # 最大水深
}
```

**使用示例**:
```python
# 1. 创建求解器
solver = HydrostaticCanalSolver(
    length=10000.0,
    nx=301,
    B=10.0,
    S0=0.0005,
    n=0.025,
    internal_structures=[(5000.0, gate)]
)

# 2. 初始化
from utils.canal_utils import compute_steady_uniform_flow
h_uniform = compute_steady_uniform_flow(10.0, 10.0, 0.0005, 0.025)
solver.h[:] = h_uniform
solver.hu[:] = 10.0 / 10.0  # Q_target / B

# 3. 稳态求解
result = solver.solve_steady_state(
    Q_target=10.0,
    h_downstream=h_uniform,
    max_iterations=5000,
    convergence_tol=0.1,  # 宽松容差，极快收敛
    dt=0.5,
    verbose=True
)

# 4. 检查结果
if result['converged']:
    print(f"✓ 收敛! 迭代{result['iterations']}次")
    print(f"  流量误差: {result['Q_error_percent']:.6f}%")
```

**推荐配置**:
| 场景 | convergence_tol | 预期迭代 | 预期时间 |
|-----|----------------|---------|---------|
| 简单（无结构） | 0.1 | 0次 | <0.05s |
| 中等（1-2结构） | 0.1 | 0-1次 | <0.1s |
| 复杂（3+结构） | 0.1 | 1-10次 | <0.5s |
| 极高精度需求 | 0.001 | 1-100次 | <3s |

#### 方法2: 非恒定流时间步进

```python
h_new, hu_new = solver.step_preissmann(
    dt,                    # 时间步长 (s)
    max_iter=10,           # Preissmann最大内迭代
    enforce_bc=True,       # 是否强制边界条件
    Q_in=None,             # 上游流量 (m³/s)
    h_out=None             # 下游水深 (m)
)

# 更新状态
solver.h = h_new
solver.hu = hu_new
solver.current_time += dt
```

**使用示例**:
```python
# 非恒定流模拟
dt = 0.5
T_total = 100.0
n_steps = int(T_total / dt)

for i in range(n_steps):
    t = (i + 1) * dt

    # 边界条件
    Q_upstream = 10.0  # 可以是时变的
    h_downstream = 1.0

    # 时间步进
    h_new, hu_new = solver.step_preissmann(
        dt=dt,
        max_iter=10,
        enforce_bc=True,
        Q_in=Q_upstream,
        h_out=h_downstream
    )

    # 更新
    solver.h = h_new
    solver.hu = hu_new
    solver.current_time = t

    # 记录或输出
    if i % 20 == 0:
        print(f"t={t:.1f}s: Q_avg={np.mean(hu_new):.4f} m³/s")
```

#### 方法3: HLL通量计算（内部使用）

```python
# 一般不需要直接调用，供高级用户参考
F_mass, F_momentum = solver.compute_hll_flux(
    h_L, hu_L,    # 左状态
    h_R, hu_R     # 右状态
)
```

### 🔬 算法细节

**Phase 2静水重构方法**:

1. **水深重构**:
   ```
   h*_L = h_i - (S0 * dx) / 2
   h*_R = h_{i+1} + (S0 * dx) / 2
   ```

2. **HLL通量**:
   ```
   F_HLL = (s_R * F_L - s_L * F_R + s_L * s_R * (U_R - U_L)) / (s_R - s_L)
   ```

3. **静水压力源项**:
   ```
   S_gravity = 0.5 * g * (h*_R^2 - h*_L^2) / dx
   ```

**参考文献**:
- Audusse et al. (2004): "A fast and stable well-balanced scheme..."
- LeVeque (2002): "Finite Volume Methods for Hyperbolic Problems"

### ⚡ 性能基准

基于 `SCRIPT_UPGRADE_SUMMARY.md` 的测试结果:

| 测试场景 | 迭代次数 | 流量误差 | 计算时间 |
|---------|---------|---------|---------|
| 单闸门 | 0-1 | 0.000000% | 0.04-0.08s |
| 三闸门串联 | 0-1 | 0.000000% | 0.04-0.08s |
| 混合结构 | 1-82 | 0.000000% | 0.07-3.08s |
| 10km渠道 301点 | 0-1 | 0.000000% | <0.1s |

### 🎓 参考示例

- `examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py`
- `examples/example_01_canal_flow/scripts/08_optimized_steady_solving_v2.py`
- `examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py`
- `examples/example_01_canal_flow/scripts/01_basic_v2.py`
- `examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py`

---

## 2️⃣ ResultValidator - 自动验证工具

### 📍 位置
```
utils/result_validator.py
```

### 🎯 核心功能

自动验证流量守恒、结构流量，生成分级报告和专业图表

**自动分级标准**:
- 🟢 **优秀 (Excellent)**: < 0.01%
- 🔵 **良好 (Good)**: < 0.1%
- 🟡 **可接受 (Acceptable)**: < 1.0%
- 🔴 **差 (Poor)**: ≥ 1.0%

### 📖 API

#### 快速使用（推荐）

```python
from utils.result_validator import quick_validate_steady_state

validator = quick_validate_steady_state(
    solver,         # HydrostaticCanalSolver实例
    result_dict,    # solve_steady_state()的返回值
    Q_target,       # 目标流量
    name            # 场景名称
)

# 自动输出：
# ✓ 收敛状态
# ✓ 流量守恒分级
# ✓ 闸门流量验证（如果有）
```

**完整示例**:
```python
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.result_validator import quick_validate_steady_state

# 1. 求解
solver = HydrostaticCanalSolver(...)
result = solver.solve_steady_state(...)

# 2. 验证（一行搞定）
validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=10.0,
    name="单闸门流动分析"
)

# 输出示例：
# ================================================================================
# 单闸门流动分析
# ================================================================================
#
# [✓ 收敛] 迭代次数: 1 (极快 (1次))
# [优秀 (Excellent)] Overall 流量守恒: 0.000000% (目标=10.0000, 平均=10.0000)
#
# 闸门流量验证:
# [优秀] 闸门1: Q=9.9655 m³/s (误差0.35%, submerged)
```

#### 高级使用

**类定义**:
```python
from utils.result_validator import ResultValidator

validator = ResultValidator()
```

**方法1: 验证流量守恒**

```python
validator.validate_flow_conservation(
    Q_computed,        # 计算的流量数组或值
    Q_target,          # 目标流量
    label="Flow"       # 标签
)
```

**返回**:
```python
{
    'Q_mean': float,           # 平均流量
    'Q_std': float,            # 标准差
    'Q_target': float,         # 目标流量
    'error_percent': float,    # 误差百分比
    'grade': str,              # 等级（优秀/良好/可接受/差）
    'color': str               # 颜色（green/blue/yellow/red）
}
```

**示例**:
```python
result = validator.validate_flow_conservation(
    Q_computed=solver.hu,  # 流量数组
    Q_target=10.0,
    label="Overall Flow"
)

print(f"等级: {result['grade']}")
print(f"误差: {result['error_percent']:.6f}%")
```

**方法2: 验证闸门流量**

```python
validator.validate_gate_discharge(
    solver,            # 求解器实例
    gate_objects,      # 闸门对象列表
    gate_indices,      # 闸门索引列表
    Q_target,          # 目标流量
    result_h           # 水深数组
)
```

**示例**:
```python
# 假设有2个闸门
gate1 = SluiceGate(position=2500.0, ...)
gate2 = SluiceGate(position=5000.0, ...)

# 找到闸门索引
idx1 = np.argmin(np.abs(solver.x - 2500.0))
idx2 = np.argmin(np.abs(solver.x - 5000.0))

# 验证
validator.validate_gate_discharge(
    solver=solver,
    gate_objects=[gate1, gate2],
    gate_indices=[idx1, idx2],
    Q_target=10.0,
    result_h=result['h']
)

# 自动输出：
# 闸门流量验证:
# [优秀] 闸门1: Q=9.9655 m³/s (误差0.35%, submerged)
# [优秀] 闸门2: Q=9.9702 m³/s (误差0.30%, submerged)
```

**方法3: 生成流量验证图**

```python
fig = validator.plot_flow_distribution(
    x,                      # x坐标
    Q,                      # 流量数组
    Q_target,               # 目标流量
    gate_positions=None,    # 闸门位置列表（可选）
    title=None,             # 标题
    save_path=None          # 保存路径
)
```

**示例**:
```python
from output_helper import get_output_path

fig = validator.plot_flow_distribution(
    x=solver.x,
    Q=result['Q'],
    Q_target=10.0,
    gate_positions=[2500.0, 5000.0, 7500.0],
    title="三闸门流量分布验证",
    save_path=get_output_path('figures', 'flow_validation.png')
)
plt.close(fig)
```

**方法4: 保存验证报告**

```python
validator.save_report(file_path)
```

**示例**:
```python
from output_helper import get_output_path

report_path = get_output_path('reports', 'validation_report.txt')
validator.save_report(report_path)

# 生成详细文本报告，包含：
# - 所有验证结果
# - 分级信息
# - 误差统计
# - 闸门流量详情
```

### 📊 输出格式

**控制台输出示例**:
```
================================================================================
脚本07 - 闸门流动分析
================================================================================

[✓ 收敛] 迭代次数: 1 (极快 (1次))
[优秀 (Excellent)] Overall 流量守恒: 0.000000% (目标=10.0000, 平均=10.0000)

闸门流量验证:
[优秀] 闸门1: Q=9.9655 m³/s (误差0.35%, submerged)
```

**报告文件示例** (`validation_report.txt`):
```
================================================================================
验证报告: 脚本07 - 闸门流动分析
生成时间: 2025-10-23 12:00:00
================================================================================

【收敛状态】
  状态: ✓ 收敛
  迭代次数: 1
  评价: 极快 (1次)

【流量守恒验证】
  目标流量: 10.0000 m³/s
  平均流量: 10.0000 m³/s
  标准差: 0.0034 m³/s
  误差: 0.000000%
  等级: 优秀 (Excellent)

【闸门流量验证】
  闸门1:
    计算流量: 9.9655 m³/s
    误差: 0.35%
    等级: 优秀
    工况: submerged (淹没出流)

================================================================================
```

### 🎓 参考示例

所有v2脚本都使用了ResultValidator：
- `scripts/07_sluice_gate_flow_v2.py` - 单闸门验证
- `scripts/12_advanced_optimized_v2.py` - 多闸门验证
- `scripts/01_basic_v2.py` - 基础流动验证

---

## 3️⃣ VisualizationTemplates - 专业可视化

### 📍 位置
```
utils/visualization_templates.py
```

### 🎯 核心功能

18种专业水力学图表模板，论文级别质量

### 📖 完整模板列表

#### 类定义

```python
from utils.visualization_templates import VisualizationTemplates

viz = VisualizationTemplates()
```

#### 模板1: 纵剖面图（水面线）

```python
fig = viz.plot_longitudinal_profile(
    x,                 # x坐标数组
    h,                 # 水深数组
    S0,                # 底坡
    canal_length,      # 渠道长度
    structures=None,   # 结构位置列表
    title="Longitudinal Profile",
    xlabel="Distance (m)",
    ylabel="Elevation (m)",
    figsize=(14, 8),
    save_path=None
)
```

**生成内容**:
- 渠底线
- 水面线
- 水体填充
- 结构位置标记（如果提供）
- 网格和图例

**示例**:
```python
fig = viz.plot_longitudinal_profile(
    x=solver.x,
    h=result['h'],
    S0=0.001,
    canal_length=10000.0,
    structures=[2500.0, 5000.0, 7500.0],  # 三个闸门位置
    title="三闸门纵剖面"
)
```

#### 模板2: 流量分布图

```python
fig = viz.plot_flow_distribution(
    x,                 # x坐标
    Q,                 # 流量数组
    Q_target,          # 目标流量
    show_error=True,   # 是否显示误差
    structures=None,   # 结构位置
    title="Flow Distribution",
    xlabel="Distance (m)",
    ylabel="Flow Rate (m³/s)",
    figsize=(14, 6),
    save_path=None
)
```

**示例**:
```python
fig = viz.plot_flow_distribution(
    x=solver.x,
    Q=result['Q'],
    Q_target=10.0,
    show_error=True,
    structures=[5000.0]
)
```

#### 模板3: 速度场（流线图）

```python
fig = viz.plot_velocity_field(
    X, Y,              # 网格坐标
    U, V,              # 速度分量
    streamlines=True,  # 是否绘制流线
    quiver=False,      # 是否绘制箭头
    density=1.5,       # 流线密度
    title="Velocity Field",
    xlabel="x (m)",
    ylabel="y (m)",
    figsize=(14, 8),
    save_path=None
)
```

**示例**:
```python
# 创建网格
X, Y = np.meshgrid(solver.x, np.linspace(0, 1, 50))
U = solver.hu / solver.h  # u = Q/h
V = np.zeros_like(U)

fig = viz.plot_velocity_field(
    X, Y, U, V,
    streamlines=True,
    quiver=False
)
```

#### 模板4: 等值线图

```python
fig = viz.plot_contour_map(
    X, Y, Z,           # 网格和数据
    levels=20,         # 等值线数量
    filled=True,       # 是否填充
    colorbar=True,     # 是否显示色标
    title="Contour Map",
    xlabel="x (m)",
    ylabel="y (m)",
    figsize=(12, 8),
    cmap='viridis',
    save_path=None
)
```

#### 模板5: 热力图

```python
fig = viz.plot_heatmap(
    data,              # 2D数据数组
    annot=False,       # 是否标注数值
    fmt='.2f',         # 数值格式
    cmap='coolwarm',   # 色图
    title="Heatmap",
    xlabel="Column",
    ylabel="Row",
    figsize=(10, 8),
    save_path=None
)
```

#### 模板6: 3D表面图

```python
fig = viz.plot_3d_surface(
    X, Y, Z,           # 网格和数据
    view_angle=(30, 45),  # 视角（仰角，方位角）
    colormap='viridis',
    title="3D Surface",
    xlabel="x (m)",
    ylabel="y (m)",
    zlabel="z (m)",
    figsize=(12, 9),
    save_path=None
)
```

**示例**:
```python
# 水面3D可视化
X, Y = np.meshgrid(solver.x, np.linspace(0, 10, 50))
Z = np.tile(result['h'], (50, 1))

fig = viz.plot_3d_surface(
    X, Y, Z,
    view_angle=(20, 60),
    title="水面3D视图"
)
```

#### 模板7: 3D水面演化图

```python
fig = viz.plot_3d_water_surface(
    x,                 # x坐标
    time,              # 时间数组
    h,                 # 水深历史数组 (n_time, n_x)
    S0,                # 底坡
    canal_length,      # 渠道长度
    view_angle=(25, 120),
    title="Water Surface Evolution (3D)",
    figsize=(14, 10),
    save_path=None
)
```

**示例**:
```python
# 假设记录了50个时间步的水深
h_history = np.array([...])  # shape: (50, 301)
time_array = np.linspace(0, 100, 50)

fig = viz.plot_3d_water_surface(
    x=solver.x,
    time=time_array,
    h=h_history,
    S0=0.001,
    canal_length=10000.0,
    title="水面演化(100s)"
)
```

#### 模板8: 回水曲线分析

```python
fig = viz.plot_backwater_curve(
    x,                 # x坐标
    h,                 # 水深数组
    h_normal,          # 正常水深
    h_critical,        # 临界水深
    S0,                # 底坡
    canal_length,      # 渠道长度
    classify=True,     # 是否分类（M1/M2等）
    title="Backwater Curve Analysis",
    figsize=(14, 8),
    save_path=None
)
```

**示例**:
```python
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth

h_n = compute_steady_uniform_flow(10.0, 10.0, 0.001, 0.025)
h_c = compute_critical_depth(10.0, 10.0)

fig = viz.plot_backwater_curve(
    x=solver.x,
    h=result['h'],
    h_normal=h_n,
    h_critical=h_c,
    S0=0.001,
    canal_length=10000.0,
    classify=True
)
```

#### 模板9: Froude数分布

```python
fig = viz.plot_froude_number(
    x,                 # x坐标
    Fr,                # Froude数数组
    highlight_critical=True,  # 高亮临界区
    title="Froude Number Distribution",
    xlabel="Distance (m)",
    ylabel="Froude Number",
    figsize=(14, 6),
    save_path=None
)
```

**示例**:
```python
from utils.canal_utils import compute_froude_number

# 计算Froude数
u = result['Q'] / result['h']
Fr = compute_froude_number(result['h'], u)

fig = viz.plot_froude_number(
    x=solver.x,
    Fr=Fr,
    highlight_critical=True
)
```

#### 模板10: 能量线（EGL/HGL）

```python
fig = viz.plot_energy_line(
    x,                 # x坐标
    h,                 # 水深
    v,                 # 流速
    S0,                # 底坡
    canal_length,      # 渠道长度
    title="Energy Grade Line",
    figsize=(14, 8),
    save_path=None
)
```

**生成内容**:
- 渠底高程
- 水面高程（HGL）
- 能量线（EGL = HGL + v²/2g）
- 比能图例

**示例**:
```python
v = result['Q'] / result['h']

fig = viz.plot_energy_line(
    x=solver.x,
    h=result['h'],
    v=v,
    S0=0.001,
    canal_length=10000.0
)
```

#### 模板11-18: 其他模板

详细API请查看源码 `utils/visualization_templates.py`，包括：
- 时间序列图
- 对比图
- 散点图
- 直方图
- 箱线图
- 相图
- 谱图
- 动画制作

### 🎨 通用参数

所有模板都支持以下通用参数：

```python
figsize=(width, height)  # 图表尺寸（英寸）
save_path=None          # 保存路径（None则不保存）
title="..."             # 标题
xlabel="..."            # x轴标签
ylabel="..."            # y轴标签
```

### 🎓 最佳实践

```python
from utils.visualization_templates import VisualizationTemplates
from output_helper import save_figure
import matplotlib.pyplot as plt

viz = VisualizationTemplates()

# 1. 创建图表
fig = viz.plot_longitudinal_profile(...)

# 2. 保存（使用output_helper）
save_figure(fig, 'my_profile.png')

# 3. 关闭图表释放内存
plt.close(fig)
```

---

## 4️⃣ canal_utils - 水力学计算工具

### 📍 位置
```
utils/canal_utils.py
```

### 📖 函数列表

#### 1. 均匀流水深（最常用）

```python
from utils.canal_utils import compute_steady_uniform_flow

h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
```

**参数**:
- `Q`: 流量 (m³/s)
- `B`: 渠道宽度 (m)
- `S0`: 渠底坡度
- `n`: Manning糙率系数

**返回**: 均匀流水深 (m)

**公式**: Manning方程求解
```
Q = (1/n) * A * R^(2/3) * S0^(1/2)
```

**示例**:
```python
h = compute_steady_uniform_flow(
    Q=10.0,      # 10 m³/s
    B=10.0,      # 10 m宽
    S0=0.001,    # 千分之一坡度
    n=0.025      # 混凝土渠道
)
print(f"均匀流水深: {h:.4f} m")
# 输出: 均匀流水深: 0.9298 m
```

#### 2. 临界水深

```python
from utils.canal_utils import compute_critical_depth

h_c = compute_critical_depth(Q, B)
```

**参数**:
- `Q`: 流量 (m³/s)
- `B`: 渠道宽度 (m)

**返回**: 临界水深 (m)

**公式**:
```
Fr = 1  →  h_c = (Q² / (g * B²))^(1/3)
```

**示例**:
```python
h_c = compute_critical_depth(Q=10.0, B=10.0)
print(f"临界水深: {h_c:.4f} m")
# 输出: 临界水深: 0.4670 m
```

#### 3. Froude数

```python
from utils.canal_utils import compute_froude_number

Fr = compute_froude_number(h, u)
```

**参数**:
- `h`: 水深 (m) - 标量或数组
- `u`: 流速 (m/s) - 标量或数组

**返回**: Froude数

**公式**:
```
Fr = u / sqrt(g * h)
```

**判断**:
- Fr < 1: 缓流（subcritical）
- Fr = 1: 临界流
- Fr > 1: 急流（supercritical）

**示例**:
```python
# 单个值
Fr = compute_froude_number(h=1.0, u=1.5)

# 数组
u_array = result['Q'] / result['h']
Fr_array = compute_froude_number(result['h'], u_array)
```

#### 4. 比能

```python
from utils.canal_utils import compute_specific_energy

E = compute_specific_energy(h, u)
```

**参数**:
- `h`: 水深 (m)
- `u`: 流速 (m/s)

**返回**: 比能 (m)

**公式**:
```
E = h + u² / (2g)
```

**示例**:
```python
E = compute_specific_energy(h=1.0, u=1.5)
print(f"比能: {E:.4f} m")
```

#### 5. 收敛性指标

```python
from utils.canal_utils import get_convergence_metrics

metrics = get_convergence_metrics(time, h_history, Q_history)
```

**参数**:
- `time`: 时间数组
- `h_history`: 水深历史数组（列表或2D数组）
- `Q_history`: 流量历史数组

**返回**: 字典
```python
{
    'cv_h_upstream': float,      # 上游水深变异系数 (%)
    'cv_h_downstream': float,    # 下游水深变异系数 (%)
    'cv_Q_upstream': float,      # 上游流量变异系数 (%)
    'cv_Q_downstream': float,    # 下游流量变异系数 (%)
    'max_cv': float,             # 最大CV
    'converged': bool            # 是否收敛（CV < 0.01%）
}
```

**示例**:
```python
# 记录历史
time_list = []
h_history_list = []
Q_history_list = []

for i in range(n_steps):
    # ... 时间步进 ...
    time_list.append(t)
    h_history_list.append(solver.h.copy())
    Q_history_list.append(solver.hu.copy())

# 分析收敛性
metrics = get_convergence_metrics(
    time=np.array(time_list),
    h_history=h_history_list,
    Q_history=Q_history_list
)

print(f"上游水深CV: {metrics['cv_h_upstream']:.6f}%")
print(f"收敛: {'✓' if metrics['converged'] else '✗'}")
```

---

## 5️⃣ gate.py - 水工结构

### 📍 位置
```
solvers/gate.py
```

### 📖 结构类型

#### 1. 闸门 (SluiceGate)

```python
from solvers.gate import SluiceGate

gate = SluiceGate(
    position,      # 位置 (m)
    width,         # 闸门宽度 (m)
    opening,       # 开度 (m)
    Cd=0.6        # 流量系数（默认0.6）
)
```

**流量计算**:
- 自由出流: `Q = Cd * B * a * sqrt(2 * g * (h1 - a/2))`
- 淹没出流: `Q = Cd * B * a * sqrt(2 * g * (h1 - h2))`

**自动判断淹没条件**: `h2/h1 > 0.67`

**示例**:
```python
gate = SluiceGate(
    position=5000.0,
    width=10.0,
    opening=5.0,
    Cd=0.6
)

# 使用
solver = HydrostaticCanalSolver(
    ...,
    internal_structures=[(5000.0, gate)]
)
```

#### 2. 宽顶堰 (BroadCrestedWeir)

```python
from solvers.gate import BroadCrestedWeir

weir = BroadCrestedWeir(
    position,          # 位置 (m)
    width,             # 堰宽 (m)
    crest_height,      # 堰顶高度 (m)
    Cd=0.848          # 流量系数（默认0.848）
)
```

**流量计算**:
- 自由出流: `Q = Cd * B * sqrt(2*g) * (H - P)^(3/2)`
- 淹没出流: 修正系数

**示例**:
```python
weir = BroadCrestedWeir(
    position=5000.0,
    width=10.0,
    crest_height=0.5,  # 堰高0.5m
    Cd=0.848
)
```

#### 3. 孔口 (Orifice)

```python
from solvers.gate import Orifice

orifice = Orifice(
    position,           # 位置 (m)
    width,              # 孔口宽度 (m)
    height,             # 孔口高度 (m)
    bottom_elevation,   # 底部高程 (m)
    Cd=0.61            # 流量系数（默认0.61）
)
```

**流量计算**:
- 自由出流: `Q = Cd * A * sqrt(2 * g * (h1 - h_center))`
- 淹没出流: `Q = Cd * A * sqrt(2 * g * (h1 - h2))`

**示例**:
```python
orifice = Orifice(
    position=7500.0,
    width=4.0,
    height=2.0,
    bottom_elevation=0.2,
    Cd=0.61
)
```

### 🔧 组合使用

```python
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice

# 创建多个结构
gate1 = SluiceGate(position=2500.0, width=10.0, opening=4.5)
weir = BroadCrestedWeir(position=5000.0, width=10.0, crest_height=0.5)
gate2 = SluiceGate(position=7500.0, width=10.0, opening=5.0)

# 组合到求解器
solver = HydrostaticCanalSolver(
    length=10000.0,
    nx=301,
    B=10.0,
    S0=0.0005,
    n=0.025,
    internal_structures=[
        (2500.0, gate1),
        (5000.0, weir),
        (7500.0, gate2)
    ]
)
```

---

## 6️⃣ output_helper - 文件管理

### 📍 位置
```
examples/example_01_canal_flow/scripts/output_helper.py
```

### 📖 函数

#### 1. 获取输出路径

```python
from output_helper import get_output_path

path = get_output_path(category, filename)
```

**参数**:
- `category`: 类别（'figures', 'tables', 'reports', 'animations'）
- `filename`: 文件名

**返回**: 完整路径（自动创建目录）

**示例**:
```python
fig_path = get_output_path('figures', 'my_plot.png')
# 返回: .../results/figures/my_plot.png
# 自动创建 results/figures/ 目录

table_path = get_output_path('tables', 'data.csv')
# 返回: .../results/tables/data.csv
```

#### 2. 保存图表

```python
from output_helper import save_figure

save_figure(fig, filename)
```

**功能**:
- 自动创建目录
- 保存为高分辨率PNG（150 DPI）
- 打印确认信息

**示例**:
```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
# ... 绘图 ...

save_figure(fig, 'my_analysis.png')
# 输出: ✓ Saved figure: my_analysis.png
# 保存到: results/figures/my_analysis.png

plt.close(fig)
```

#### 3. 保存数据表

```python
from output_helper import save_table

save_table(df, filename, **kwargs)
```

**参数**:
- `df`: pandas DataFrame
- `filename`: 文件名
- `**kwargs`: 传递给 `df.to_csv()` 的参数

**示例**:
```python
import pandas as pd

df = pd.DataFrame({
    'x': solver.x,
    'h': result['h'],
    'Q': result['Q']
})

save_table(df, 'profile_data.csv', index=False)
# 输出: ✓ Saved table: profile_data.csv
# 保存到: results/tables/profile_data.csv
```

#### 4. 保存动画

```python
from output_helper import save_animation

save_animation(anim, filename)
```

**示例**:
```python
from matplotlib import animation

# 创建动画
fig, ax = plt.subplots()
# ...
anim = animation.FuncAnimation(...)

save_animation(anim, 'evolution.gif')
# 保存到: results/animations/evolution.gif
```

---

## 🎯 快速参考卡

### 典型工作流

```python
# 1. 导入基础库
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import quick_validate_steady_state
from utils.visualization_templates import VisualizationTemplates
from output_helper import save_figure, save_table

# 2. 创建求解器
gate = SluiceGate(position=5000.0, width=10.0, opening=5.0)
solver = HydrostaticCanalSolver(
    length=10000.0, nx=301, B=10.0, S0=0.0005, n=0.025,
    internal_structures=[(5000.0, gate)]
)

# 3. 初始化
h_uniform = compute_steady_uniform_flow(10.0, 10.0, 0.0005, 0.025)
solver.h[:] = h_uniform
solver.hu[:] = 10.0 / 10.0

# 4. 稳态求解
result = solver.solve_steady_state(
    Q_target=10.0, h_downstream=h_uniform,
    convergence_tol=0.1, verbose=True
)

# 5. 验证
validator = quick_validate_steady_state(
    solver, result, 10.0, "测试场景"
)

# 6. 可视化
viz = VisualizationTemplates()
fig = viz.plot_longitudinal_profile(
    solver.x, result['h'], 0.0005, 10000.0
)
save_figure(fig, 'profile.png')

# 7. 保存数据
import pandas as pd
df = pd.DataFrame({'x': solver.x, 'h': result['h']})
save_table(df, 'data.csv')
```

---

## 📚 进一步学习

1. **示例脚本**: `examples/example_01_canal_flow/scripts/*_v2.py`
2. **开发指南**: `DEVELOPMENT_GUIDE.md`
3. **升级总结**: `SCRIPT_UPGRADE_SUMMARY.md`
4. **源码**: 直接阅读基础库源代码（有详细注释）

---

**最后更新**: 2025-10-23
**维护者**: HydroClaude开发团队

**Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**
