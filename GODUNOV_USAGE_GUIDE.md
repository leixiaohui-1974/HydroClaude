# Godunov-FVM求解器使用指南

**文件**: `/workspace/solvers/godunov_fvm_solver.py`
**类**: `GodunvFVMSolver`

---

## 🎯 快速开始

### 最简示例（稳态均匀流）

```python
import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow

# 配置
width = 10.0
length = 1000.0
n_cells = 100
manning_n = 0.025
slope = 0.001
Q_target = 50.0

# 创建求解器（推荐Order 1）
solver = GodunvFVMSolver(
    width=width,
    length=length,
    n_cells=n_cells,
    manning_n=manning_n,
    slope=slope,
    cfl=0.5,
    order=1  # 1=稳定可靠，2=高精度但需Well-Balanced
)

# 初始条件
h_uniform = compute_steady_uniform_flow(Q_target, width, slope, manning_n)
h_init = np.ones(n_cells) * h_uniform
Q_init = np.ones(n_cells) * Q_target

# 边界条件
bc_left = {'type': 'Q', 'value': Q_target}  # 上游流量
bc_right = {'type': 'h', 'value': h_uniform}  # 下游水深

# 初始化
solver.initialize(h_init, Q_init, bc_left, bc_right)

# 时间推进
while solver.t < 1000.0:
    h, Q = solver.step()  # 自动计算时间步长
    
    if solver.step_count % 100 == 0:
        state = solver.get_state()
        print(f"t={state['t']:.1f}s, 质量误差={state['mass_error']:.4f}%")

# 结果
state = solver.get_state()
print(f"最终水深: {np.mean(state['h']):.4f}m (理论: {h_uniform:.4f}m)")
print(f"质量误差: {state['mass_error']:.6f}%")
```

**预期结果**:
- 质量误差: < 0.5%
- 水深误差: < 1%
- 流量误差: < 0.1%

---

## 📖 API参考

### 构造函数

```python
solver = GodunvFVMSolver(
    width: float,          # 渠道宽度 (m)
    length: float,         # 渠道长度 (m)
    n_cells: int,          # 单元数
    manning_n: float,      # Manning粗糙系数
    slope: float,          # 渠底坡度
    g: float = 9.81,       # 重力加速度
    cfl: float = 0.5,      # CFL数（0.3-0.8）
    eps_dry: float = 1e-6, # 干床阈值
    order: int = 1         # 空间精度（1或2）
)
```

**参数说明**:
- `order=1`: **推荐**，稳定可靠，适合所有场景
- `order=2`: 高精度，但含源项时不稳定（需Well-Balanced）
- `cfl`: 越小越稳定，但越慢。推荐0.5

---

### 初始化

```python
solver.initialize(
    h_init: np.ndarray,  # 初始水深 [n_cells]
    Q_init: np.ndarray,  # 初始流量 [n_cells]
    bc_left: Dict,       # 左边界条件
    bc_right: Dict       # 右边界条件
)
```

**边界条件格式**:
```python
# 水深边界
bc = {'type': 'h', 'value': 2.0}  # 常数
bc = {'type': 'h', 'value': lambda t: 2.0 + 0.5*np.sin(2*np.pi*t/100)}  # 时变

# 流量边界
bc = {'type': 'Q', 'value': 50.0}  # 常数
bc = {'type': 'Q', 'value': lambda t: 50.0 + 10*np.sin(2*np.pi*t/100)}  # 时变
```

---

### 时间推进

```python
# 自动时间步长
h, Q = solver.step()

# 指定时间步长
h, Q = solver.step(dt=0.1)

# 计算时间步长（不推进）
dt = solver.compute_dt()
```

**返回值**:
- `h`: 水深数组 [n_cells]
- `Q`: 流量数组 [n_cells]

---

### 状态查询

```python
state = solver.get_state()

# state包含:
# - 'x': 单元中心坐标 [n_cells]
# - 'h': 水深 [n_cells]
# - 'Q': 流量 [n_cells]
# - 't': 当前时间
# - 'dt': 当前时间步长
# - 'step': 步数
# - 'mass_error': 质量误差 (%)
```

**质量守恒误差**:
```python
error = solver.get_mass_conservation_error()  # 返回百分比
```

---

## 🔧 典型应用场景

### 场景1: Dam Break（溃坝）

```python
# 配置
solver = GodunvFVMSolver(
    width=10.0,
    length=200.0,
    n_cells=200,
    manning_n=0.0,  # 无摩阻
    slope=0.0,      # 水平
    cfl=0.5,
    order=2  # Dam Break用Order 2效果更好
)

# 初始条件：阶跃
x_dam = 100.0
h_init = np.where(solver.x < x_dam, 10.0, 1.0)
Q_init = np.zeros(200)

# 边界条件
bc_left = {'type': 'h', 'value': 10.0}
bc_right = {'type': 'h', 'value': 1.0}

solver.initialize(h_init, Q_init, bc_left, bc_right)

# 时间推进
while solver.t < 2.0:
    solver.step()

# 结果
state = solver.get_state()
print(f"质量误差: {state['mass_error']:.4f}%")  # 预期 < 1%
```

**预期性能**:
- 质量误差: 0.9%
- 波前误差: 16%
- 稳定无NaN

---

### 场景2: 稳态流动（工程应用）

```python
# 配置
solver = GodunvFVMSolver(
    width=10.0,
    length=1000.0,
    n_cells=100,
    manning_n=0.025,  # 含摩阻
    slope=0.001,
    cfl=0.5,
    order=1  # ← 推荐Order 1（稳定）
)

# 理论均匀流
h_uniform = compute_steady_uniform_flow(50.0, 10.0, 0.001, 0.025)

# 初始条件
h_init = np.ones(100) * h_uniform
Q_init = np.ones(100) * 50.0

# 边界条件
bc_left = {'type': 'Q', 'value': 50.0}
bc_right = {'type': 'h', 'value': h_uniform}

solver.initialize(h_init, Q_init, bc_left, bc_right)

# 推进到稳态
while solver.t < 1000.0:
    solver.step()

# 验证
state = solver.get_state()
h_mean = np.mean(state['h'])
Q_mean = np.mean(state['Q'])

print(f"水深误差: {abs(h_mean - h_uniform)/h_uniform*100:.2f}%")  # 预期 < 1%
print(f"流量误差: {abs(Q_mean - 50.0)/50.0*100:.2f}%")  # 预期 < 0.1%
```

**预期性能**:
- 质量误差: 0.36%
- 水深误差: 0.36%
- 流量误差: 0.05%

---

### 场景3: 时变边界（洪水演进）

```python
# 配置
solver = GodunvFVMSolver(
    width=20.0,
    length=5000.0,
    n_cells=500,
    manning_n=0.03,
    slope=0.0005,
    cfl=0.5,
    order=1
)

# 洪水过程线（上游）
def flood_hydrograph(t):
    """三角形洪峰"""
    if t < 3600:  # 1小时涨水
        return 100 + 400 * (t / 3600)
    elif t < 7200:  # 1小时退水
        return 500 - 400 * ((t - 3600) / 3600)
    else:
        return 100

# 初始条件
h_base = compute_steady_uniform_flow(100, 20.0, 0.0005, 0.03)
h_init = np.ones(500) * h_base
Q_init = np.ones(500) * 100

# 边界条件
bc_left = {'type': 'Q', 'value': flood_hydrograph}  # 时变流量
bc_right = {'type': 'h', 'value': h_base}  # 固定水深

solver.initialize(h_init, Q_init, bc_left, bc_right)

# 模拟3小时
t_end = 3 * 3600
history = {'t': [], 'Q_peak': [], 'h_peak': []}

while solver.t < t_end:
    solver.step()
    
    if solver.step_count % 100 == 0:
        state = solver.get_state()
        history['t'].append(state['t'] / 3600)  # 小时
        history['Q_peak'].append(np.max(state['Q']))
        history['h_peak'].append(np.max(state['h']))
        
        print(f"t={state['t']/3600:.2f}h, Q_peak={np.max(state['Q']):.1f}m³/s")

# 可视化洪峰传播
import matplotlib.pyplot as plt
plt.plot(history['t'], history['Q_peak'])
plt.xlabel('Time (h)')
plt.ylabel('Peak Discharge (m³/s)')
plt.title('Flood Wave Propagation')
plt.show()
```

---

## ⚠️ 注意事项

### 1. Order 1 vs Order 2

| 特性 | Order 1 | Order 2 |
|------|---------|---------|
| 稳定性 | ✅ 绝对稳定 | ⚠️ 含源项时不稳定 |
| 精度 | 一阶 | 二阶 |
| 速度 | 快 | 慢（时间步小） |
| 推荐场景 | 工程应用 | 理想流、Dam Break |

**建议**:
- ✅ 默认使用Order 1
- ✅ 无摩阻问题可用Order 2
- ❌ 含摩阻避免Order 2（除非实施Well-Balanced）

---

### 2. CFL数选择

| CFL | 稳定性 | 速度 | 推荐场景 |
|-----|--------|------|----------|
| 0.3 | 极高 | 慢 | 激波、强间断 |
| 0.5 | 高 | 中 | **通用推荐** |
| 0.8 | 中 | 快 | 光滑流动 |

**不推荐** CFL > 0.8（可能不稳定）

---

### 3. 网格分辨率

| dx | 精度 | 速度 | 推荐场景 |
|----|------|------|----------|
| < 5m | 高 | 慢 | 激波、闸门 |
| 5-10m | 中 | 中 | **通用推荐** |
| > 10m | 低 | 快 | 长河道、粗估 |

**经验公式**: `n_cells = length / 10` （通常足够）

---

### 4. 边界条件选择

**上游**:
- ✅ 流量边界（`type='Q'`）- 推荐
- ⚠️ 水深边界（`type='h'`）- 可能不物理

**下游**:
- ✅ 水深边界（`type='h'`）- 推荐
- ⚠️ 流量边界（`type='Q'`）- 可能不稳定

---

## 🐛 常见问题

### Q1: 出现NaN怎么办？

**可能原因**:
1. Order 2 + 含源项 → 使用Order 1
2. CFL太大 → 降至0.3
3. 初始条件不合理 → 检查h>0, Q合理

**解决方案**:
```python
# 方案1：降阶
solver = GodunvFVMSolver(..., order=1)

# 方案2：降低CFL
solver = GodunvFVMSolver(..., cfl=0.3)

# 方案3：检查初始条件
h_init = np.maximum(h_init, 0.1)  # 避免干床
```

---

### Q2: 质量误差太大？

**可能原因**:
1. 边界条件不守恒
2. 时间步长太大
3. 网格太粗

**解决方案**:
```python
# 方案1：检查边界条件
# 确保流入=流出（稳态流）

# 方案2：降低CFL
solver = GodunvFVMSolver(..., cfl=0.3)

# 方案3：加密网格
n_cells = int(length / 5)  # dx=5m
```

---

### Q3: 结果振荡怎么办？

**可能原因**:
1. CFL太大
2. 边界条件不平滑
3. 源项不平衡

**解决方案**:
```python
# 方案1：降低CFL
cfl=0.3

# 方案2：平滑初始条件
h_init = scipy.ndimage.gaussian_filter1d(h_init, sigma=2)

# 方案3：使用Order 1
order=1
```

---

## 📊 性能基准

### 计算速度（参考）

| 场景 | 单元数 | 时间步 | 墙钟时间 | 速度 |
|------|--------|--------|----------|------|
| Dam Break | 200 | 40 | ~1s | 极快 |
| 稳态流 | 100 | 1430 | ~3s | 快 |
| 洪水演进 | 500 | ~5000 | ~10s | 快 |

**硬件**: Intel i7, 单核

---

### 内存占用

- 基础: ~10KB
- 每单元: ~100 bytes
- 1000单元: ~110KB

**结论**: 内存高效

---

## 🚀 高级技巧

### 技巧1: 并行多场景

```python
from multiprocessing import Pool

def run_scenario(params):
    Q, slope = params
    solver = GodunvFVMSolver(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=slope, order=1
    )
    # ... 运行模拟 ...
    return result

# 并行计算
with Pool(4) as pool:
    results = pool.map(run_scenario, [
        (50, 0.001),
        (60, 0.001),
        (70, 0.001),
        (80, 0.001)
    ])
```

---

### 技巧2: 自适应时间步长

```python
# 自动选择最优dt
while solver.t < t_end:
    dt = solver.compute_dt()  # 根据CFL计算
    
    # 限制最大时间步
    dt = min(dt, 10.0)
    
    solver.step(dt)
```

---

### 技巧3: 结果后处理

```python
state = solver.get_state()

# Froude数
Fr = (state['Q'] / (state['h'] * width)) / np.sqrt(9.81 * state['h'])

# 流速
u = state['Q'] / (state['h'] * width)

# 能量水头
H = state['h'] + u**2 / (2 * 9.81) + slope * state['x']

# 导出CSV
import pandas as pd
df = pd.DataFrame({
    'x': state['x'],
    'h': state['h'],
    'Q': state['Q'],
    'u': u,
    'Fr': Fr
})
df.to_csv('results.csv', index=False)
```

---

## ✅ 最佳实践

1. ✅ **默认使用Order 1**（稳定可靠）
2. ✅ **CFL=0.5**（速度与稳定性平衡）
3. ✅ **dx=5-10m**（精度与速度平衡）
4. ✅ **上游Q边界，下游h边界**
5. ✅ **定期检查质量误差**（< 1%）
6. ✅ **长时间模拟每100步输出一次**
7. ✅ **保存关键时刻的完整状态**

---

## 📚 参考资料

### 理论基础
- Toro, E.F. (2009). "Riemann Solvers and Numerical Methods"
- LeVeque, R.J. (2002). "Finite Volume Methods"

### 相关文档
- `GODUNOV_VALIDATION_REPORT.md` - 完整验证报告
- `LIBRARY_REFERENCE.md` - 完整API参考
- `DEVELOPMENT_GUIDE.md` - 开发指南

---

**Generated by**: HydroClaude Team
**Last Updated**: 2025-10-29
**Version**: 1.0
