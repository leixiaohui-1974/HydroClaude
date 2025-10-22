# 水库组件模块

## 概述

本模块提供完整的水库物理仿真与优化调度功能，融合了HydroClaude的高保真物理模型和Test-Opt的优化调度能力。

## 核心组件

### 1. Reservoir (水库组件)
- **文件**: `physics/reservoir.py`
- **功能**: 单水库物理仿真与调度
- **特性**:
  - 高保真库容演算
  - 库容-水位关系（分段线性/非线性）
  - 发电计算
  - 溢洪道泄流
  - 约束管理（防洪、生态、供水）

### 2. ReservoirCascade (梯级水库系统)
- **文件**: `physics/reservoir_cascade.py`
- **功能**: 梯级水库联合仿真与调度
- **特性**:
  - 拓扑管理
  - 水流传递和时间延迟
  - 梯级协调仿真
  - 防洪协调控制
  - 发电优化协调

### 3. ReservoirScheduler (水库调度器)
- **文件**: `optimization/reservoir_scheduler.py`
- **功能**: 基于优化的调度决策
- **特性**:
  - Pyomo优化模型
  - 多目标优化
  - 约束验证
  - 多求解器支持

## 快速开始

### 基础示例

```python
from physics.reservoir import Reservoir

# 创建水库
reservoir = Reservoir(
    reservoir_id="my_reservoir",
    total_capacity=5000e4,  # 5000万m³
    dead_storage=500e4,
    min_level=100.0,
    normal_level=150.0,
    flood_limit_level=145.0,
    design_level=155.0,
    has_turbine=True,
    turbine_capacity=100.0,
    hydraulic_head=50.0
)

# 仿真
dt = 3600.0  # 1小时
inputs = {
    'inflow': 500.0,  # m³/s
    'turbine_discharge': 300.0
}
state = reservoir.update_high_fidelity(dt, inputs)

print(f"水位: {state.water_level:.2f} m")
print(f"发电: {state.power_generation:.2f} MW")
```

### 梯级示例

```python
from physics.reservoir import Reservoir
from physics.reservoir_cascade import ReservoirCascade, CascadeTopology

# 创建水库
r1 = Reservoir(reservoir_id="R1", ...)
r2 = Reservoir(reservoir_id="R2", ...)

# 定义拓扑
topology = CascadeTopology(
    reservoir_ids=["R1", "R2"],
    connections={"R1": ["R2"]},
    travel_times={("R1", "R2"): 2.0},
    lateral_inflows={"R1": 50.0, "R2": 30.0}
)

# 创建梯级系统
cascade = ReservoirCascade(
    cascade_id="cascade",
    reservoirs=[r1, r2],
    topology=topology
)

# 仿真
states = cascade.simulate_cascade(
    dt=3600.0,
    inflows={"R1": 800.0}
)
```

## 示例程序

### 示例17: 单水库基础仿真
- **位置**: `examples/example_17_reservoir_basic/`
- **运行**: `python demo_reservoir.py`
- **内容**:
  - 基础物理仿真
  - 库容演算
  - 发电计算
  - 约束检查

### 示例18: 梯级水电站调度
- **位置**: `examples/example_18_cascade_hydropower/`
- **运行**: `python demo_cascade.py`
- **内容**:
  - 三级梯级系统
  - 水流传递
  - 联合优化
  - 防洪协调
  - 峰谷电价调度

## 参数说明

### 水库基本参数
- `total_capacity`: 总库容 (m³)
- `dead_storage`: 死库容 (m³)
- `min_level`: 死水位 (m)
- `normal_level`: 正常蓄水位 (m)
- `flood_limit_level`: 防洪限制水位 (m)
- `design_level`: 设计洪水位 (m)

### 水电参数
- `turbine_capacity`: 装机容量 (MW)
- `hydraulic_head`: 水头 (m)
- `turbine_efficiency`: 综合效率 (0-1)

### 运行约束
- `ecological_flow`: 生态流量 (m³/s)
- `max_discharge`: 最大泄流 (m³/s)

## 物理模型

### 水量平衡方程
```
dV/dt = Q_in - Q_out
```

### 库容-水位关系
```
V = f(Z)
```
支持：
- 线性关系
- 分段线性
- 三次样条插值

### 发电功率
```
P = η * ρ * g * Q * H / 1000  (MW)
  = 9.81 * Q * H * η / 1000
```

### 溢洪道泄流
```
Q = C * L * opening * H^(3/2)
```

## 约束条件

### 水位约束
```
Z_min ≤ Z ≤ Z_max
```

### 库容约束
```
V_dead ≤ V ≤ V_total
```

### 生态流量约束
```
Q_out ≥ Q_ecological
```

### 防洪约束
```
Z ≤ Z_flood_limit  (汛期)
```

## 优化调度

### 目标函数
```
min: -发电收益 + 缺水惩罚
```

### 决策变量
- 库容 V(t)
- 出流 Q(t)
- 水轮机流量 Q_turbine(t)

### 约束
- 质量平衡
- 容量限制
- 运行约束
- 梯级连接

## 性能指标

### 仿真性能
- 时间步长: 1秒 - 1小时
- 仿真速度: > 1000倍实时（降阶模型）
- 精度: < 5% 误差

### 优化性能
- 小规模 (24小时): < 1秒
- 中等规模 (7天): < 10秒
- 大规模 (1月): < 60秒

## 注意事项

1. **时间步长选择**
   - 瞬态分析: dt < 60秒
   - 日常调度: dt = 3600秒 (1小时)
   - 长期规划: dt = 86400秒 (1天)

2. **数值稳定性**
   - 避免库容突变
   - 确保初始条件合理
   - 检查约束一致性

3. **优化求解器**
   - 开源: GLPK, HiGHS
   - 商业: CPLEX, Gurobi (性能更好)

## 扩展开发

### 添加新的调度规则
```python
class CustomScheduler(ReservoirScheduler):
    def compute_schedule(self, ...):
        # 自定义调度逻辑
        pass
```

### 自定义库容-水位关系
```python
def custom_storage_curve(level):
    # 自定义关系
    return storage

reservoir = Reservoir(
    ...,
    storage_curve=custom_storage_curve
)
```

## 参考文献

1. 水库调度原理与方法
2. 梯级水电站优化调度
3. Test-Opt优化框架文档
4. HydroClaude物理模型文档

## 支持与反馈

- 问题报告: GitHub Issues
- 文档: `/docs/INTEGRATION_DESIGN.md`
- 示例: `/examples/example_17_*` 和 `/examples/example_18_*`
