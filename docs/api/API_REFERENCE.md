# HydroClaude API 参考文档

本文档提供 HydroClaude 项目的核心 API 参考。

## 核心模块 (Core)

### solver.py - 水力求解器

主求解器模块，实现圣维南方程组的数值求解。

#### `HydraulicSolver`

一维明渠非恒定流求解器，采用有限体积方法求解圣维南方程组。

**主要方法:**

- `__init__(x, h, u, z_bed, width, manning_n, ...)` - 初始化求解器
  - `x`: 空间坐标数组 (m)
  - `h`: 初始水深 (m)
  - `u`: 初始流速 (m/s)
  - `z_bed`: 底高程 (m)
  - `width`: 渠道宽度 (m)
  - `manning_n`: 曼宁系数

- `solve(t_final, dt, save_interval=1)` - 运行模拟
  - `t_final`: 模拟总时间 (s)
  - `dt`: 时间步长 (s)
  - `save_interval`: 保存间隔
  - **返回**: `(time, results)` - 时间数组和结果字典

- `set_boundary_conditions(bc_func)` - 设置边界条件
  - `bc_func`: 函数 `f(t) -> (Q_upstream, h_downstream)`

- `add_structure(structure)` - 添加水工结构物
  - `structure`: 结构物对象 (SluiceGate, Weir, Pump等)

**使用示例:**

```python
import numpy as np
from core.solver import HydraulicSolver

# 创建求解器
x = np.linspace(0, 1000, 100)
h = np.ones(100) * 2.0
u = np.zeros(100)
z_bed = np.zeros(100)

solver = HydraulicSolver(
    x=x, h=h, u=u, z_bed=z_bed,
    width=10.0, manning_n=0.025
)

# 设置边界条件
solver.set_boundary_conditions(lambda t: (20.0, 2.0))

# 运行模拟
time, results = solver.solve(t_final=600, dt=0.1)
```

---

### structures.py - 水工结构物

定义各类水工结构物（闸门、堰、泵站等）。

#### `SluiceGate` - 闸门

**参数:**
- `position`: 闸门位置 (m from start)
- `opening`: 闸门开度 (0-1)
- `width`: 闸门宽度 (m)
- `discharge_coeff`: 流量系数 (默认0.6)

**方法:**
- `set_opening(opening)` - 设置开度
- `get_flow_rate(h_upstream, h_downstream)` - 计算过闸流量

**使用示例:**

```python
from core.structures import SluiceGate

gate = SluiceGate(position=500, opening=0.5, width=8.0)
Q = gate.get_flow_rate(h_upstream=3.0, h_downstream=2.5)
```

#### `Weir` - 堰

**参数:**
- `position`: 堰位置 (m)
- `crest_height`: 堰顶高程 (m)
- `width`: 堰宽 (m)
- `discharge_coeff`: 流量系数 (默认0.4)

#### `Pump` - 泵站

**参数:**
- `position`: 泵站位置 (m)
- `capacity`: 额定流量 (m³/s)
- `power`: 额定功率 (kW)
- `efficiency`: 效率 (0-1)

**方法:**
- `set_flow_rate(Q)` - 设置抽排流量
- `start()` / `stop()` - 启动/停止泵

---

## 控制模块 (Control)

### pid_controller.py - PID控制器

标准PID控制器实现，包含抗饱和、输出限幅、微分滤波等增强功能。

#### `PIDController`

**配置类:** `PIDConfig`
- `kp`: 比例增益
- `ki`: 积分增益
- `kd`: 微分增益
- `output_min`, `output_max`: 输出限制
- `integral_min`, `integral_max`: 积分限制
- `derivative_filter`: 微分滤波系数
- `deadband`: 误差死区
- `dt`: 采样时间

**主要方法:**

- `__init__(config, name="PID")` - 初始化控制器
- `set_setpoint(setpoint)` - 设置目标值
- `compute(measurement, dt=None)` - 计算控制输出
  - `measurement`: 当前测量值
  - `dt`: 时间步长
  - **返回**: 控制输出

- `reset()` - 重置控制器状态
- `get_performance_metrics()` - 获取性能指标
- `auto_tune_ziegler_nichols(Ku, Tu, method)` - Ziegler-Nichols自动调参

**使用示例:**

```python
from control.pid_controller import PIDController, PIDConfig

# 配置PID
config = PIDConfig(
    kp=1.0, ki=0.1, kd=0.05,
    output_min=0.0, output_max=10.0,
    dt=1.0
)

# 创建控制器
pid = PIDController(config, name="Water Level PID")
pid.set_setpoint(3.0)  # 目标水位3m

# 在循环中使用
for t in range(1000):
    measurement = get_current_water_level()
    control_output = pid.compute(measurement)
    apply_control(control_output)
```

---

### mpc_controller.py - MPC控制器

模型预测控制器，基于系统模型预测和优化。

#### `MPCController`

**配置类:** `MPCConfig`
- `prediction_horizon`: 预测时域长度 N
- `control_horizon`: 控制时域长度 M
- `dt`: 采样时间
- `state_weight`: 状态误差权重 Q
- `control_weight`: 控制输入权重 R
- `control_change_weight`: 控制变化权重
- `state_min`, `state_max`: 状态约束
- `control_min`, `control_max`: 控制约束
- `control_rate_min`, `control_rate_max`: 控制变化率约束

**主要方法:**

- `__init__(config, model_func=None, name="MPC")` - 初始化
- `set_linear_model(A, B)` - 设置线性模型
  - 系统模型: `x[k+1] = A*x[k] + B*u[k]`
- `set_nonlinear_model(model_func)` - 设置非线性模型
- `compute(measurement, reference_trajectory=None)` - 计算控制输出
- `get_predicted_trajectory()` - 获取预测轨迹

**使用示例:**

```python
from control.mpc_controller import MPCController, MPCConfig

# 配置MPC
config = MPCConfig(
    prediction_horizon=10,
    control_horizon=5,
    dt=1.0,
    state_weight=10.0,
    control_weight=0.1,
    control_min=0.0,
    control_max=20.0
)

# 创建控制器
mpc = MPCController(config, name="Water Level MPC")
mpc.set_setpoint(3.0)
mpc.set_linear_model(A=1.0, B=-0.01)  # 简化模型

# 使用
control_output = mpc.compute(current_water_level)
```

#### `AdaptiveMPCController`

自适应MPC，增加在线模型参数估计功能。

---

## 工具模块 (Utils)

### visualizer.py - 可视化工具

高级可视化功能，提供多种专业绘图样式。

#### `HydroVisualizer`

**参数:**
- `style`: 绘图风格 ('default', 'scientific', 'presentation')
- `color_scheme`: 配色方案

**主要方法:**

- `plot_water_surface(x, h, z_bed, ...)` - 绘制水面线
- `plot_control_performance(time, actual, target, control, ...)` - 绘制控制性能
- `create_dashboard(time, water_level, flow_rate, control_input, ...)` - 创建仪表板
- `plot_time_series(time, data, ...)` - 绘制时间序列
- `save_figure(filename, ...)` - 保存图形

**使用示例:**

```python
from utils.visualizer import HydroVisualizer

viz = HydroVisualizer(style='scientific')

# 绘制水面线
viz.plot_water_surface(
    x=x,
    h=water_depth,
    z_bed=bed_elevation,
    title='水面线'
)

# 创建控制系统仪表板
viz.create_dashboard(
    time=time,
    water_level=h_history,
    flow_rate=Q_history,
    control_input=u_control,
    target_level=3.0
)
```

---

### config_generator.py - 配置生成器

交互式配置文件生成工具。

#### `ConfigGenerator`

**主要方法:**

- `create_basic_canal(length, nx, width, ...)` - 创建基础渠道配置
- `add_structure(config, structure_type, position, **params)` - 添加结构物
- `add_controller(config, controller_type, target_level, ...)` - 添加控制器
- `interactive_wizard()` - 交互式向导
- `export_yaml(config, filename)` - 导出YAML配置

**使用示例:**

```python
from utils.config_generator import ConfigGenerator

gen = ConfigGenerator()

# 方法1: 使用模板
config = gen.from_template('canal_with_gate')

# 方法2: 交互式创建
config = gen.interactive_wizard()

# 导出
gen.export_yaml(config, 'my_canal.yaml')
```

---

### data_validator.py - 数据验证器

数据质量检查和物理合理性验证。

#### `DataValidator`

**主要方法:**

- `validate_water_depth(h, check_continuity=True)` - 验证水深数据
- `validate_velocity(u)` - 验证流速数据
- `check_mass_conservation(Q_in, Q_out, dV_dt, tolerance=0.01)` - 检查质量守恒
- `check_courant_condition(u, h, dx, dt)` - 检查CFL条件
- `detect_outliers(data, method='iqr', threshold=3.0)` - 检测异常值
- `generate_html_report(results, filename)` - 生成HTML报告

**使用示例:**

```python
from utils.data_validator import DataValidator

validator = DataValidator()

# 验证模拟结果
results = {
    'h': water_depth_array,
    'u': velocity_array,
    'Q': flow_rate_array
}

report = validator.validate_simulation_results(results)
validator.generate_html_report(report, 'validation_report.html')
```

---

### performance_profiler.py - 性能分析器

代码性能分析和优化建议。

#### `PerformanceProfiler`

**主要方法:**

- `profile(func)` - 装饰器，分析函数性能
- `print_report(detailed=False)` - 打印性能报告
- `get_bottlenecks(top_n=5)` - 识别性能瓶颈
- `generate_optimization_suggestions()` - 生成优化建议

**使用示例:**

```python
from utils.performance_profiler import PerformanceProfiler

profiler = PerformanceProfiler(enable_memory_tracking=True)

@profiler.profile
def my_simulation():
    # ... 模拟代码

# 运行
my_simulation()

# 查看报告
profiler.print_report()
suggestions = profiler.generate_optimization_suggestions()
```

#### `SimulationOptimizer`

**静态方法:**

- `analyze_grid_efficiency(nx, dx, dt, u_max, h_max)` - 分析网格效率
- `suggest_optimal_parameters(L, T, u_typical, h_typical, target_accuracy)` - 建议最优参数

**使用示例:**

```python
from utils.performance_profiler import SimulationOptimizer

# 分析当前网格
result = SimulationOptimizer.analyze_grid_efficiency(
    nx=100, dx=10.0, dt=0.1,
    u_max=2.0, h_max=3.0
)
print(f"效率评分: {result['efficiency_score']}/100")

# 获取优化建议
optimal = SimulationOptimizer.suggest_optimal_parameters(
    L=1000.0, T=600.0,
    u_typical=2.0, h_typical=3.0,
    target_accuracy='medium'
)
print(f"建议网格点数: {optimal['nx']}")
print(f"建议时间步长: {optimal['dt']}s")
```

---

## 命令行工具

### hydroclaude_cli.py - 统一CLI工具

提供所有功能的统一命令行接口。

**子命令:**

#### `run` - 运行模拟

```bash
python hydroclaude_cli.py run config.yaml [--plot] [--export FILE] [--verbose]
```

#### `config` - 配置管理

```bash
# 创建配置
python hydroclaude_cli.py config create [--template NAME] [--interactive]

# 验证配置
python hydroclaude_cli.py config validate config.yaml
```

#### `validate` - 验证示例

```bash
python hydroclaude_cli.py validate [--report] [--examples DIR]
```

#### `test` - 运行测试

```bash
python hydroclaude_cli.py test [--type unit|integration|all]
```

#### `benchmark` - 性能测试

```bash
python hydroclaude_cli.py benchmark [--output FILE]
```

#### `health` - 健康检查

```bash
python hydroclaude_cli.py health [--report]
```

---

## 数据结构

### 模拟结果字典

`solver.solve()` 返回的结果字典包含：

```python
{
    'h': np.ndarray,      # 水深历史 [n_steps, nx]
    'u': np.ndarray,      # 流速历史 [n_steps, nx]
    'Q': np.ndarray,      # 流量历史 [n_steps, nx]
    'Fr': np.ndarray,     # 弗劳德数 [n_steps, nx]
    'control': dict,      # 控制输出历史（如果有控制器）
    'structures': dict    # 结构物状态历史（如果有结构物）
}
```

### 边界条件函数

边界条件函数签名：

```python
def boundary_conditions(t: float) -> Tuple[float, float]:
    """
    Args:
        t: 当前时间 (s)

    Returns:
        (Q_upstream, h_downstream): 上游流量和下游水深
    """
    return Q_upstream, h_downstream
```

---

## 常用工作流程

### 1. 基础模拟

```python
import numpy as np
from core.solver import HydraulicSolver

# 创建求解器
x = np.linspace(0, 1000, 100)
solver = HydraulicSolver(
    x=x,
    h=np.ones(100) * 2.0,
    u=np.zeros(100),
    z_bed=np.zeros(100),
    width=10.0,
    manning_n=0.025
)

# 边界条件
solver.set_boundary_conditions(lambda t: (20.0, 2.0))

# 运行
time, results = solver.solve(t_final=600, dt=0.1)

# 可视化
from utils.visualizer import HydroVisualizer
viz = HydroVisualizer()
viz.plot_water_surface(x, results['h'][-1], solver.z_bed)
```

### 2. 闸门控制

```python
from core.solver import HydraulicSolver
from core.structures import SluiceGate
from control.pid_controller import PIDController, PIDConfig

# 创建系统
solver = HydraulicSolver(...)
gate = SluiceGate(position=500, opening=0.5)
solver.add_structure(gate)

# 创建控制器
config = PIDConfig(kp=1.0, ki=0.1, kd=0.05)
controller = PIDController(config)
controller.set_setpoint(3.0)  # 目标水位

# 控制循环
for step in range(n_steps):
    current_depth = solver.get_depth_at(500)  # 闸门处水位
    control = controller.compute(current_depth)
    gate.set_opening(control)
    solver.step(dt)
```

### 3. 性能优化

```python
from utils.performance_profiler import PerformanceProfiler, SimulationOptimizer

# 分析当前配置
result = SimulationOptimizer.analyze_grid_efficiency(
    nx=100, dx=10.0, dt=0.1, u_max=2.0, h_max=3.0
)

if not result['is_stable']:
    # 获取优化建议
    optimal = SimulationOptimizer.suggest_optimal_parameters(
        L=1000, T=600, u_typical=2.0, h_typical=3.0
    )
    # 使用建议的参数重新配置
```

---

## 参考资料

- **README.md** - 项目概览
- **QUICKSTART.md** - 快速入门指南
- **DEVELOPMENT_SUMMARY.md** - 开发文档
- **examples/** - 示例代码
- **tests/** - 单元测试（最佳学习资源）

---

*本文档由 HydroClaude 团队维护。最后更新: 2025-10-24*
