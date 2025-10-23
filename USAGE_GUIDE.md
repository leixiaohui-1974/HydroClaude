# HydrostaticCanalSolver 使用指南

**快速开始指南** - 5分钟上手静水重构渠道求解器

---

## 安装与依赖

```bash
# 依赖
pip install numpy matplotlib

# 克隆项目
cd HydroClaude
```

---

## 快速示例

### 示例1: 简单渠道流（无闸门）

```python
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
import numpy as np

# 创建求解器
solver = HydrostaticCanalSolver(
    length=1000.0,    # 渠道长度 (m)
    nx=101,           # 网格点数
    B=10.0,           # 渠道宽度 (m)
    S0=0.001,         # 底坡
    n=0.025           # Manning糙率
)

# 求解稳态流
result = solver.solve_steady_state(
    Q_target=10.0,        # 目标流量 (m³/s)
    h_downstream=0.93,    # 下游水深 (m)
    max_iterations=3000,
    verbose=True
)

# 查看结果
print(f"流量误差: {result['Q_error_percent']:.4f}%")    # 0.00%
print(f"收敛状态: {result['converged']}")                # True
print(f"迭代次数: {result['iterations']}")               # 0

# 绘图
import matplotlib.pyplot as plt
plt.plot(solver.x, result['h'])
plt.xlabel('Position (m)')
plt.ylabel('Water depth (m)')
plt.show()
```

**输出**: 流量误差 0.00%, 即时收敛 ✅

---

### 示例2: 带闸门的渠道

```python
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate

# 步骤1: 创建闸门对象
gate = SluiceGate(
    position=500.0,    # 闸门位置 (m)
    width=10.0,        # 闸门宽度 (m)
    opening=0.5,       # 闸门开度 (m)
    Cd=0.6             # 流量系数
)

# 步骤2: 创建带闸门的求解器
solver = HydrostaticCanalSolver(
    length=1000.0,
    nx=101,
    B=10.0,
    S0=0.001,
    n=0.025,
    internal_structures=[(500.0, gate)]  # ⭐ 添加闸门
)

# 步骤3: 求解
result = solver.solve_steady_state(
    Q_target=5.0,
    h_downstream=0.60,    # 建议使用均匀流水深
    max_iterations=3000
)

# 步骤4: 验证闸门流量
gate_idx = solver.structure_indices[0]
h_up = result['h'][gate_idx - 1]
h_down = result['h'][gate_idx + 1]
Q_gate, flow_type = gate.calculate_discharge(h_up, h_down)

print(f"流量守恒误差: {result['Q_error_percent']:.2f}%")  # 0.00%
print(f"闸门流量: {Q_gate:.4f} m³/s")                      # 4.955 m³/s
print(f"闸门误差: {abs(Q_gate-5.0)/5.0*100:.2f}%")        # 0.91%
print(f"流态: {flow_type}")                                 # submerged
```

**输出**: 流量0.00%, 闸门0.91%误差 ✅

---

### 示例3: 多闸门系统

```python
# 创建多个闸门
gate1 = SluiceGate(2500.0, 10.0, 4.5, 0.6)
gate2 = SluiceGate(5000.0, 10.0, 4.0, 0.6)
gate3 = SluiceGate(7500.0, 10.0, 5.0, 0.6)

# 创建求解器（添加所有闸门）
solver = HydrostaticCanalSolver(
    length=10000.0,
    nx=301,
    B=10.0,
    S0=0.0005,
    n=0.025,
    internal_structures=[
        (2500.0, gate1),
        (5000.0, gate2),
        (7500.0, gate3)
    ]
)

# 求解
result = solver.solve_steady_state(
    Q_target=10.0,
    h_downstream=1.16,
    max_iterations=5000,
    verbose=True
)

# 结果: 流量0.00%, 各闸门0.34-0.41%误差
```

**输出**: 三闸门系统完美运行 ✅

---

## 参数说明

### HydrostaticCanalSolver 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `length` | float | 必需 | 渠道长度 (m) |
| `nx` | int | 必需 | 网格点数（推荐100-300） |
| `B` | float | 必需 | 渠道宽度 (m) |
| `S0` | float | 必需 | 底坡（无量纲，如0.001） |
| `n` | float | 必需 | Manning糙率（如0.025） |
| `g` | float | 9.81 | 重力加速度 (m/s²) |
| `internal_structures` | list | None | 内部结构 [(位置, 对象), ...] |
| `theta` | float | 0.6 | Preissmann时间加权系数 |
| `omega` | float | 0.95 | 松弛因子 |

### solve_steady_state 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `Q_target` | float | 必需 | 目标流量 (m³/s) |
| `h_downstream` | float | 必需 | 下游水深 (m) |
| `max_iterations` | int | 5000 | 最大迭代次数 |
| `convergence_tol` | float | 0.001 | 收敛容差 (m) |
| `dt` | float | 0.5 | 时间步长 (s) |
| `verbose` | bool | True | 是否打印进度 |

### SluiceGate 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `position` | float | 必需 | 闸门位置 (m) |
| `width` | float | 必需 | 闸门宽度 (m) |
| `opening` | float | 必需 | 闸门开度 (m) |
| `Cd` | float | 0.6 | 流量系数 |
| `g` | float | 9.81 | 重力加速度 (m/s²) |

---

## 重要提示

### ⚠️ 下游水深的选择

**关键**: 下游水深必须是物理合理的值，推荐使用均匀流水深。

```python
def compute_uniform_flow(Q, B, S0, n):
    """计算Manning均匀流水深"""
    h = 1.0  # 初始猜测
    for i in range(100):
        A = B * h
        R = A / (B + 2*h)  # 水力半径
        Q_calc = (1/n) * A * R**(2/3) * (S0**0.5)
        residual = Q - Q_calc
        if abs(residual) < 1e-6:
            break
        # 牛顿法
        dQ_dh = (1/n) * (S0**0.5) * (
            B * R**(2/3) +
            A * (2/3) * R**(-1/3) * (B - 2*h) / (B + 2*h)**2
        )
        h = h + residual / dQ_dh
        h = max(0.1, h)  # 确保正值
    return h

# 使用
h_downstream = compute_uniform_flow(Q_target, B, S0, n)
```

### ✅ 最佳实践

```python
# 1. 计算合理的下游边界条件
h_uniform = compute_uniform_flow(Q_target, B, S0, n)

# 2. 使用适当的网格密度
nx = 101  # 简单问题
nx = 201  # 复杂问题/多闸门

# 3. 检查收敛
if result['converged']:
    print("✓ 求解成功")
else:
    print("✗ 未收敛，尝试增加max_iterations")

# 4. 验证流量守恒
if result['Q_error_percent'] < 1.0:
    print("✓ 流量守恒优秀")

# 5. 对于闸门，验证约束
Q_gate, _ = gate.calculate_discharge(h_up, h_down)
gate_error = abs(Q_gate - Q_target) / Q_target * 100
if gate_error < 5.0:
    print(f"✓ 闸门约束满足 ({gate_error:.2f}%)")
```

---

## 结果解释

### result 字典内容

```python
result = {
    'converged': bool,           # 是否收敛
    'iterations': int,           # 迭代次数
    'h': np.ndarray,             # 水深数组 (m)
    'Q': np.ndarray,             # 流量数组 (m³/s)
    'Q_mean': float,             # 平均流量 (m³/s)
    'Q_error_percent': float,    # 流量误差 (%)
    'dh_max': float,             # 最大水深变化 (m)
    'dhu_max': float             # 最大流量变化 (m²/s)
}
```

### 访问数据

```python
# 水深分布
depths = result['h']

# 流量分布
flows = result['Q']

# 位置坐标
positions = solver.x

# 水位 = 水深 + 底床高程
water_surface = result['h'] + solver.z

# 绘制水深剖面
plt.plot(solver.x, result['h'])
plt.xlabel('Position (m)')
plt.ylabel('Water depth (m)')

# 绘制水位剖面
plt.plot(solver.x, water_surface, label='Water surface')
plt.fill_between(solver.x, solver.z, alpha=0.3, label='Bed')
plt.legend()
```

---

## 常见问题

### Q1: 流量误差很大怎么办？

**A**: 检查下游边界条件是否合理
```python
# 确保使用均匀流水深
h_downstream = compute_uniform_flow(Q_target, B, S0, n)
```

### Q2: 求解不收敛怎么办？

**A**: 尝试以下方法
```python
# 1. 增加最大迭代次数
max_iterations = 10000

# 2. 降低松弛因子
solver.omega = 0.9

# 3. 减小时间步长
dt = 0.1

# 4. 提供更好的初始猜测
h_upstream_guess = h_downstream * 1.5
```

### Q3: 闸门流量误差大怎么办？

**A**:
```python
# 1. 确保下游边界合理（均匀流水深）
# 2. 检查闸门开度是否合理（不要太小）
# 3. 调整闸门边界条件参数
solver._apply_internal_bc(..., tol=0.01, relax=0.6)
```

### Q4: 如何添加更多类型的水工建筑物？

**A**: 查看 `solvers/gate.py`，已定义多种类型
```python
from solvers.gate import (
    SluiceGate,           # 平板闸门
    BroadCrestedWeir,     # 宽顶堰
    Orifice,              # 孔口
    Spillway,             # 溢洪道
    Drop                  # 跌水
)

# 使用示例
weir = BroadCrestedWeir(
    position=500.0,
    width=10.0,
    crest_height=0.5,
    Cd=0.848
)

solver = HydrostaticCanalSolver(
    ...,
    internal_structures=[(500.0, weir)]
)
```

---

## 性能提示

### 网格大小选择

```python
# 简单场景（无闸门）
nx = 51-101      # 足够

# 中等复杂（1-2个闸门）
nx = 101-201     # 推荐

# 复杂场景（多闸门，长渠道）
nx = 201-501     # 根据需要
```

### 典型计算时间

| 场景 | 网格 | 迭代次数 | 时间 |
|------|------|----------|------|
| 无闸门 1km | 101 | 0 | <1s |
| 单闸门 1km | 101 | ~100 | ~5s |
| 三闸门 10km | 301 | 1 | <1s |

---

## 测试文件

学习更多用法请参考：

```python
# 基础测试
test_hydrostatic_solver.py         # 无闸门稳态流

# 闸门测试
test_gate_simple.py                 # 单闸门系统
test_three_gates_hydrostatic.py    # 三闸门系统

# Phase 1 算法验证
test_well_balanced.py               # 良平衡特性验证
```

---

## 完整示例：从头到尾

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整示例：求解带闸门的渠道稳态流
"""

import numpy as np
import matplotlib.pyplot as plt
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate

# 步骤1: 定义参数
L = 1000.0       # 渠道长度
B = 10.0         # 宽度
S0 = 0.001       # 底坡
n = 0.025        # Manning糙率
Q = 5.0          # 流量

# 步骤2: 计算均匀流水深
def compute_h_uniform(Q, B, S0, n):
    h = 1.0
    for _ in range(100):
        A = B * h
        R = A / (B + 2*h)
        Q_calc = (1/n) * A * R**(2/3) * (S0**0.5)
        if abs(Q - Q_calc) < 1e-6:
            break
        dQ_dh = (1/n) * (S0**0.5) * (
            B * R**(2/3) + A * (2/3) * R**(-1/3) * (B - 2*h) / (B + 2*h)**2
        )
        h += (Q - Q_calc) / dQ_dh
    return h

h_uniform = compute_h_uniform(Q, B, S0, n)
print(f"均匀流水深: {h_uniform:.4f} m")

# 步骤3: 创建闸门
gate = SluiceGate(
    position=500.0,
    width=B,
    opening=0.5,
    Cd=0.6
)

# 步骤4: 创建求解器
solver = HydrostaticCanalSolver(
    length=L,
    nx=101,
    B=B,
    S0=S0,
    n=n,
    internal_structures=[(500.0, gate)]
)

# 步骤5: 求解
result = solver.solve_steady_state(
    Q_target=Q,
    h_downstream=h_uniform,
    max_iterations=3000,
    verbose=True
)

# 步骤6: 验证结果
print(f"\n结果:")
print(f"  流量误差: {result['Q_error_percent']:.4f}%")
print(f"  收敛: {result['converged']}")

# 闸门验证
gate_idx = solver.structure_indices[0]
h_up = result['h'][gate_idx - 1]
h_down = result['h'][gate_idx + 1]
Q_gate, flow_type = gate.calculate_discharge(h_up, h_down)
print(f"  闸门流量: {Q_gate:.4f} m³/s ({abs(Q_gate-Q)/Q*100:.2f}%)")

# 步骤7: 绘图
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# 水深
ax1.plot(solver.x, result['h'], 'b-', linewidth=2)
ax1.axvline(500, color='r', linestyle='--', label='Gate')
ax1.set_ylabel('Water depth (m)')
ax1.set_title(f'Steady State Solution (Q={Q} m³/s)')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 水位
water_surface = result['h'] + solver.z
ax2.plot(solver.x, water_surface, 'r-', linewidth=2, label='Water surface')
ax2.fill_between(solver.x, solver.z, alpha=0.3, color='brown', label='Bed')
ax2.axvline(500, color='r', linestyle='--', alpha=0.5)
ax2.set_xlabel('Position (m)')
ax2.set_ylabel('Elevation (m)')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('my_canal_simulation.png', dpi=150)
plt.show()

print("\n完成！图表保存至 my_canal_simulation.png")
```

---

## 技术支持

- **理论文档**: `HYDROSTATIC_RECONSTRUCTION_THEORY.md` (2000行)
- **完整总结**: `HYDROSTATIC_RECONSTRUCTION_FINAL_SUMMARY.md`
- **Phase 1报告**: `PHASE_1_COMPLETION_SUMMARY.md`
- **Phase 2报告**: `PHASE_2_COMPLETION_REPORT.md`

---

**祝使用愉快！** 🎉

如有问题，请参考测试文件或查阅技术文档。
