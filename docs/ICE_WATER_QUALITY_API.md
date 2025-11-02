# HydroClaude 冰-水质模块 API 参考文档

**版本**: v1.0
**日期**: 2025-11-02
**状态**: Production Ready

---

## 📚 概述

本文档提供 HydroClaude 冰-水质耦合模块的完整 API 参考，包括:
- 水温求解器
- 溶解氧求解器
- 冰盖求解器
- 营养盐求解器
- 藻类求解器
- 模块耦合方法
- 最佳实践

---

## 🚀 快速入门

### 最小示例：溶解氧模拟

```python
import numpy as np
from solvers.dissolved_oxygen import DissolvedOxygenSolver

# 创建求解器
solver = DissolvedOxygenSolver(
    n_cells=100,    # 网格数量
    dx=100.0,       # 网格间距 (m)
    kd_20=0.15,     # BOD降解系数 (1/day)
    SOD_20=1.0      # 河床需氧量 (g/m2/day)
)

# 初始条件
solver.DO = np.full(100, 8.0)   # DO = 8 mg/L
solver.BOD = np.full(100, 3.0)  # BOD = 3 mg/L

# 环境条件
u = np.full(100, 0.5)           # 流速 0.5 m/s
h = np.full(100, 2.0)           # 水深 2.0 m
T = np.full(100, 20.0)          # 水温 20°C
manning_n = np.full(100, 0.03)

# 运行24小时
dt = 3600.0  # 1小时步长
for step in range(24):
    state = solver.step(dt, u, h, T, manning_n)
    print(f"步 {step+1}: DO = {state['DO'].mean():.2f} mg/L")
```

### 完整示例：冰-水质耦合模拟

```python
import numpy as np
from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

# 1. 初始化所有求解器
n_cells = 100
dx = 100.0

temp_solver = WaterTemperatureSolver(n_cells, dx)
do_solver = DissolvedOxygenSolver(n_cells, dx)
ice_solver = IceCoverSolver(n_cells=n_cells)
nutrients_solver = NutrientsSolver(n_cells, dx)
algae_solver = PhytoplanktonSolver(n_cells, dx)

# 2. 设置初始条件
temp_solver.T = np.full(n_cells, 2.0)
do_solver.DO = np.full(n_cells, 12.0)
ice_solver.ice_thickness = np.zeros(n_cells)
nutrients_solver.NH4 = np.full(n_cells, 0.3)
nutrients_solver.NO3 = np.full(n_cells, 1.2)
algae_solver.Chla = np.full(n_cells, 12.0)

# 3. 时间循环
dt = 3600.0
for step in range(720):  # 30天
    # 气象条件
    T_air = -5.0 - step * 0.01  # 逐渐降温

    # 推进各模块
    T = temp_solver.step(dt, u, h, T_air, I_0, wind, rh)
    ice_state = ice_solver.step(dt, T_air, T)
    nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)
    algae_state = algae_solver.step(dt, u, h, T, I_0, NH4, NO3, PO4)
    do_state = do_solver.step(dt, u, h, T, manning_n)

    # 耦合：藻类产氧和营养盐消耗
    do_solver.DO += algae_state['DO_production'] * (dt / 86400.0)
    nutrients_solver.NH4 -= algae_state['NH4_uptake'] * (dt / 86400.0)
```

---

## 📖 API 详细参考

## 1. 水温求解器 `WaterTemperatureSolver`

### 类定义

```python
class WaterTemperatureSolver:
    """
    一维水温对流-扩散求解器

    物理过程:
    - 对流传输 (MUSCL重构 + HLL求解器)
    - 扩散混合 (中心差分)
    - 表面热交换 (长波辐射、蒸发、对流)
    - 短波辐射吸收

    数值方法:
    - TVD-RK2 时间积分
    - 二阶空间精度
    """
```

### 构造函数

```python
def __init__(
    self,
    n_cells: int,          # 网格数量
    dx: float,             # 网格间距 (m)
    use_numba: bool = False  # 是否使用Numba加速
)
```

**参数说明:**
- `n_cells`: 计算域网格数，建议 50-500
- `dx`: 网格间距，典型值 50-200 m
- `use_numba`: 启用后可提速 2-5 倍

**示例:**
```python
solver = WaterTemperatureSolver(n_cells=100, dx=100.0, use_numba=True)
```

### 状态变量

```python
solver.T  # 水温 (°C), shape=(n_cells,)
```

### 主方法: `step()`

```python
def step(
    self,
    dt: float,                  # 时间步长 (s)
    u: np.ndarray,             # 流速 (m/s), shape=(n_cells,)
    h: np.ndarray,             # 水深 (m), shape=(n_cells,)
    T_air: float,              # 气温 (°C)
    I_0: float,                # 表面太阳辐射 (W/m2)
    wind_speed: float,         # 风速 (m/s)
    relative_humidity: float   # 相对湿度 (0-1)
) -> np.ndarray:
    """
    推进一个时间步

    Returns:
        T: 更新后的水温数组 (°C)
    """
```

**参数范围:**
- `dt`: 建议 600-3600 s (10分钟 - 1小时)
- `u`: 0.1 - 3.0 m/s
- `h`: 0.5 - 20.0 m
- `T_air`: -30 到 +40 °C
- `I_0`: 0 - 1000 W/m2
- `wind_speed`: 0 - 20 m/s
- `relative_humidity`: 0.3 - 1.0

**返回值:**
- `T`: 水温数组 (°C), shape=(n_cells,)

**完整示例:**
```python
from solvers.water_temperature import WaterTemperatureSolver
import numpy as np

# 初始化
solver = WaterTemperatureSolver(n_cells=100, dx=100.0)
solver.T = np.full(100, 20.0)  # 初始水温 20°C

# 环境条件
u = np.full(100, 0.5)
h = np.full(100, 2.5)
T_air = 25.0
I_0 = 500.0
wind_speed = 3.0
relative_humidity = 0.7

# 运行模拟
dt = 3600.0
for hour in range(24):
    T = solver.step(dt, u, h, T_air, I_0, wind_speed, relative_humidity)
    print(f"第{hour+1}小时: 水温 = {T.mean():.2f}°C")
```

---

## 2. 溶解氧求解器 `DissolvedOxygenSolver`

### 类定义

```python
class DissolvedOxygenSolver:
    """
    Streeter-Phelps 溶解氧方程求解器

    物理过程:
    - BOD 降解 (耗氧)
    - 河床需氧 (SOD)
    - 表面复氧
    - 温度影响 (Arrhenius方程)

    数值方法:
    - 算子分裂法 (Strang splitting)
    - 二阶时间精度
    """
```

### 构造函数

```python
def __init__(
    self,
    n_cells: int,              # 网格数量
    dx: float,                 # 网格间距 (m)
    kd_20: float = 0.15,       # 20°C时BOD降解系数 (1/day)
    SOD_20: float = 1.0,       # 20°C时河床需氧量 (g/m2/day)
    use_numba: bool = False    # 是否使用Numba加速
)
```

**参数说明:**
- `kd_20`: BOD降解系数
  - 清洁水体: 0.05 - 0.15
  - 污染水体: 0.15 - 0.40
- `SOD_20`: 河床需氧量
  - 沙质河床: 0.5 - 1.5
  - 淤泥河床: 1.5 - 3.0

**示例:**
```python
# 污染河流
solver = DissolvedOxygenSolver(
    n_cells=100,
    dx=100.0,
    kd_20=0.25,      # 较高BOD降解
    SOD_20=2.0       # 较高河床需氧
)

# 清洁河流
solver = DissolvedOxygenSolver(
    n_cells=100,
    dx=100.0,
    kd_20=0.10,      # 较低BOD降解
    SOD_20=1.0       # 较低河床需氧
)
```

### 状态变量

```python
solver.DO   # 溶解氧 (mg/L), shape=(n_cells,)
solver.BOD  # 生化需氧量 (mg/L), shape=(n_cells,)
```

### 主方法: `step()`

```python
def step(
    self,
    dt: float,               # 时间步长 (s)
    u: np.ndarray,          # 流速 (m/s)
    h: np.ndarray,          # 水深 (m)
    T: np.ndarray,          # 水温 (°C)
    manning_n: np.ndarray   # Manning粗糙系数
) -> dict:
    """
    推进一个时间步

    Returns:
        state: 状态字典
            - 'DO': 溶解氧 (mg/L)
            - 'BOD': BOD (mg/L)
            - 'DO_sat': 饱和溶解氧 (mg/L)
    """
```

**返回值:**
```python
state = {
    'DO': np.ndarray,      # 溶解氧 (mg/L)
    'BOD': np.ndarray,     # BOD (mg/L)
    'DO_sat': np.ndarray   # 饱和DO (mg/L)
}
```

**完整示例:**
```python
from solvers.dissolved_oxygen import DissolvedOxygenSolver
import numpy as np
import matplotlib.pyplot as plt

# 初始化
solver = DissolvedOxygenSolver(
    n_cells=100,
    dx=100.0,
    kd_20=0.20,
    SOD_20=1.5
)

# 初始条件
solver.DO = np.full(100, 9.0)   # 上游DO较高
solver.BOD = np.full(100, 4.0)  # 有机污染物

# 环境条件
u = np.full(100, 0.3)
h = np.full(100, 2.0)
T = np.full(100, 20.0)
manning_n = np.full(100, 0.03)

# 运行7天
dt = 3600.0
n_steps = 168  # 7天 x 24小时
DO_history = []

for step in range(n_steps):
    state = solver.step(dt, u, h, T, manning_n)
    DO_history.append(state['DO'].mean())

    if step % 24 == 0:
        print(f"第{step//24 + 1}天: "
              f"DO = {state['DO'].mean():.2f} mg/L, "
              f"BOD = {state['BOD'].mean():.2f} mg/L")

# 绘制结果
plt.plot(np.arange(n_steps) / 24, DO_history)
plt.axhline(y=5.0, color='r', linestyle='--', label='低氧阈值')
plt.xlabel('时间 (天)')
plt.ylabel('溶解氧 (mg/L)')
plt.legend()
plt.show()
```

---

## 3. 冰盖求解器 `IceCoverSolver`

### 类定义

```python
class IceCoverSolver:
    """
    冰盖生长和融化模拟器

    物理过程:
    - 静态冰生长 (Stefan方程)
    - 冰融化
    - 动态冰 (Frazil ice, 可选)
    - 冰塞 (Ice jam, 可选)

    数值方法:
    - 解析积分 (Stefan方程)
    - 能量平衡法
    """
```

### 构造函数

```python
def __init__(
    self,
    n_cells: int,                           # 网格数量
    ice_density: float = 917.0,             # 冰密度 (kg/m3)
    latent_heat_fusion: float = 334000.0,   # 冰融化潜热 (J/kg)
    ice_thermal_conductivity: float = 2.22, # 冰导热系数 (W/m/K)
    enable_frazil: bool = False,            # 是否启用动态冰
    enable_ice_jam: bool = False            # 是否启用冰塞
)
```

**参数说明:**
- `ice_density`: 冰密度，默认 917 kg/m³
- `latent_heat_fusion`: 融化潜热，默认 334 kJ/kg
- `ice_thermal_conductivity`: 冰导热系数，默认 2.22 W/(m·K)
- `enable_frazil`: 启用动态冰模拟 (计算成本增加 20%)
- `enable_ice_jam`: 启用冰塞模拟 (实验性功能)

**示例:**
```python
# 简化模拟（仅静态冰）
solver = IceCoverSolver(n_cells=100)

# 完整模拟（含动态冰）
solver = IceCoverSolver(
    n_cells=100,
    enable_frazil=True,
    enable_ice_jam=False  # 冰塞暂不启用
)
```

### 状态变量

```python
solver.ice_thickness        # 冰厚 (m), shape=(n_cells,)
solver.ice_cover_fraction   # 冰盖面积比 (0-1), shape=(n_cells,)
solver.frazil_concentration # 动态冰浓度 (kg/m3), shape=(n_cells,)
```

### 主方法: `step()`

```python
def step(
    self,
    dt: float,           # 时间步长 (s)
    T_air: float,        # 气温 (°C)
    T_water: np.ndarray  # 水温 (°C), shape=(n_cells,)
) -> dict:
    """
    推进一个时间步

    Returns:
        state: 状态字典
            - 'ice_thickness': 冰厚 (m)
            - 'ice_cover_fraction': 冰盖面积比 (0-1)
            - 'frazil_concentration': 动态冰浓度 (kg/m3)
            - 'growth_rate': 冰生长速率 (m/s)
            - 'ice_on': 是否有冰 (bool)
    """
```

**返回值:**
```python
state = {
    'ice_thickness': np.ndarray,        # 冰厚 (m)
    'ice_cover_fraction': np.ndarray,   # 冰盖面积比
    'frazil_concentration': np.ndarray, # 动态冰浓度
    'growth_rate': np.ndarray,          # 生长速率 (m/s)
    'ice_on': bool                      # 是否有冰
}
```

**完整示例:**
```python
from solvers.ice_cover import IceCoverSolver
import numpy as np

# 初始化
solver = IceCoverSolver(n_cells=100, enable_frazil=True)

# 初始条件（秋季，无冰）
solver.ice_thickness = np.zeros(100)
solver.ice_cover_fraction = np.zeros(100)

# 模拟冬季降温
dt = 3600.0
T_water = np.full(100, 2.0)  # 初始水温 2°C

# 气温从 0°C 降到 -20°C (30天)
n_steps = 30 * 24
T_air_schedule = np.linspace(0.0, -20.0, n_steps)

for step in range(n_steps):
    T_air = T_air_schedule[step]

    # 水温逐渐降至冰点
    T_water = np.maximum(T_water - 0.01, 0.0)

    state = solver.step(dt, T_air, T_water)

    if step % (24*5) == 0:  # 每5天
        print(f"第{step//24 + 1}天: "
              f"气温 = {T_air:.1f}°C, "
              f"冰厚 = {state['ice_thickness'].mean():.3f}m, "
              f"冰盖比 = {state['ice_cover_fraction'].mean():.2f}")
```

---

## 4. 营养盐求解器 `NutrientsSolver`

### 类定义

```python
class NutrientsSolver:
    """
    氮磷循环模拟器

    物理过程:
    - 氨化: 有机氮 → NH4
    - 硝化: NH4 → NO3 (需氧)
    - 反硝化: NO3 → N2 (厌氧)
    - 磷释放: 有机磷 → PO4
    - 沉降

    数值方法:
    - 算子分裂法
    - 一阶动力学
    """
```

### 构造函数

```python
def __init__(
    self,
    n_cells: int,          # 网格数量
    dx: float,             # 网格间距 (m)
    use_numba: bool = False  # 是否使用Numba加速
)
```

### 状态变量

```python
solver.NH4   # 铵态氮 (mg-N/L), shape=(n_cells,)
solver.NO3   # 硝态氮 (mg-N/L), shape=(n_cells,)
solver.PO4   # 磷酸盐 (mg-P/L), shape=(n_cells,)
solver.OrgN  # 有机氮 (mg-N/L), shape=(n_cells,)
solver.OrgP  # 有机磷 (mg-P/L), shape=(n_cells,)
```

### 主方法: `step()`

```python
def step(
    self,
    dt: float,          # 时间步长 (s)
    u: np.ndarray,      # 流速 (m/s)
    h: np.ndarray,      # 水深 (m)
    T: np.ndarray,      # 水温 (°C)
    DO: np.ndarray      # 溶解氧 (mg/L)
) -> dict:
    """
    推进一个时间步

    Returns:
        state: 状态字典
            - 'NH4', 'NO3', 'PO4': 各营养盐浓度
            - 'OrgN', 'OrgP': 有机物浓度
            - 'TN', 'TP': 总氮总磷
    """
```

**返回值:**
```python
state = {
    'NH4': np.ndarray,   # 铵态氮 (mg-N/L)
    'NO3': np.ndarray,   # 硝态氮 (mg-N/L)
    'PO4': np.ndarray,   # 磷酸盐 (mg-P/L)
    'OrgN': np.ndarray,  # 有机氮 (mg-N/L)
    'OrgP': np.ndarray,  # 有机磷 (mg-P/L)
    'TN': np.ndarray,    # 总氮 (mg-N/L)
    'TP': np.ndarray     # 总磷 (mg-P/L)
}
```

**完整示例:**
```python
from solvers.nutrients import NutrientsSolver
import numpy as np

# 初始化
solver = NutrientsSolver(n_cells=100, dx=100.0)

# 初始条件
solver.NH4 = np.full(100, 0.3)
solver.NO3 = np.full(100, 1.5)
solver.PO4 = np.full(100, 0.08)
solver.OrgN = np.full(100, 0.5)
solver.OrgP = np.full(100, 0.05)

# 环境条件
u = np.full(100, 0.4)
h = np.full(100, 2.5)
T = np.full(100, 18.0)
DO = np.full(100, 8.5)

# 运行14天
dt = 3600.0
n_steps = 14 * 24

for step in range(n_steps):
    state = solver.step(dt, u, h, T, DO)

    if step % 24 == 0:
        print(f"第{step//24 + 1}天: "
              f"TN = {state['TN'].mean():.3f} mg/L, "
              f"TP = {state['TP'].mean():.3f} mg/L")
```

---

## 5. 藻类求解器 `PhytoplanktonSolver`

### 类定义

```python
class PhytoplanktonSolver:
    """
    藻类生长动力学模拟器

    物理过程:
    - 光照限制 (Steele公式)
    - 营养盐限制 (Monod公式)
    - 温度影响
    - 呼吸和死亡
    - 沉降

    数值方法:
    - 一阶动力学
    - 算子分裂法
    """
```

### 构造函数

```python
def __init__(
    self,
    n_cells: int,          # 网格数量
    dx: float,             # 网格间距 (m)
    use_numba: bool = False  # 是否使用Numba加速
)
```

### 状态变量

```python
solver.Chla  # 叶绿素 a 浓度 (μg/L), shape=(n_cells,)
```

### 主方法: `step()`

```python
def step(
    self,
    dt: float,           # 时间步长 (s)
    u: np.ndarray,       # 流速 (m/s)
    h: np.ndarray,       # 水深 (m)
    T: np.ndarray,       # 水温 (°C)
    I_0: np.ndarray,     # 表面光强 (W/m2)
    NH4: np.ndarray,     # NH4浓度 (mg-N/L)
    NO3: np.ndarray,     # NO3浓度 (mg-N/L)
    PO4: np.ndarray      # PO4浓度 (mg-P/L)
) -> dict:
    """
    推进一个时间步

    Returns:
        state: 状态字典
            - 'Chla': 叶绿素 a (μg/L)
            - 'growth_rate': 生长速率 (1/day)
            - 'DO_production': DO产生 (mg/L/day)
            - 'NH4_uptake', 'NO3_uptake', 'PO4_uptake': 营养盐吸收
            - 'light_limitation': 光照限制因子 (0-1)
            - 'nutrient_limitation': 营养盐限制因子 (0-1)
    """
```

**返回值:**
```python
state = {
    'Chla': np.ndarray,              # 叶绿素 a (μg/L)
    'growth_rate': np.ndarray,       # 生长速率 (1/day)
    'DO_production': np.ndarray,     # DO产生 (mg/L/day)
    'NH4_uptake': np.ndarray,        # NH4吸收 (mg-N/L/day)
    'NO3_uptake': np.ndarray,        # NO3吸收 (mg-N/L/day)
    'PO4_uptake': np.ndarray,        # PO4吸收 (mg-P/L/day)
    'light_limitation': np.ndarray,  # 光照限制 (0-1)
    'nutrient_limitation': np.ndarray  # 营养盐限制 (0-1)
}
```

**完整示例:**
```python
from solvers.phytoplankton import PhytoplanktonSolver
import numpy as np

# 初始化
solver = PhytoplanktonSolver(n_cells=100, dx=100.0)

# 初始条件
solver.Chla = np.full(100, 5.0)  # 初始叶绿素 5 μg/L

# 环境条件
u = np.full(100, 0.3)
h = np.full(100, 2.0)
T = np.full(100, 25.0)  # 适宜温度
I_0 = np.full(100, 300.0)  # 充足光照
NH4 = np.full(100, 0.5)
NO3 = np.full(100, 2.0)
PO4 = np.full(100, 0.1)

# 运行21天
dt = 3600.0
n_steps = 21 * 24

for step in range(n_steps):
    state = solver.step(dt, u, h, T, I_0, NH4, NO3, PO4)

    # 营养盐消耗
    NH4 -= state['NH4_uptake'] * (dt / 86400.0)
    NO3 -= state['NO3_uptake'] * (dt / 86400.0)
    PO4 -= state['PO4_uptake'] * (dt / 86400.0)

    NH4 = np.maximum(NH4, 0.0)
    NO3 = np.maximum(NO3, 0.0)
    PO4 = np.maximum(PO4, 0.0)

    if step % (24*3) == 0:  # 每3天
        print(f"第{step//24 + 1}天: "
              f"Chla = {state['Chla'].mean():.2f} μg/L, "
              f"生长率 = {state['growth_rate'].mean():.3f} 1/day")
```

---

## 🔗 模块耦合

### 完整耦合示例

以下示例展示如何将所有模块耦合在一起进行完整的冰-水质模拟:

```python
import numpy as np
from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

# ==================== 1. 初始化 ====================
n_cells = 100
dx = 100.0
dt = 3600.0  # 1小时步长
n_days = 30

# 创建所有求解器
temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=False)
do_solver = DissolvedOxygenSolver(n_cells, dx, kd_20=0.15, SOD_20=1.0, use_numba=False)
ice_solver = IceCoverSolver(n_cells=n_cells)
nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=False)
algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)

# ==================== 2. 初始条件 ====================
temp_solver.T = np.full(n_cells, 2.0)
do_solver.DO = np.full(n_cells, 12.0)
do_solver.BOD = np.full(n_cells, 3.0)
ice_solver.ice_thickness = np.zeros(n_cells)
ice_solver.ice_cover_fraction = np.zeros(n_cells)
nutrients_solver.NH4 = np.full(n_cells, 0.3)
nutrients_solver.NO3 = np.full(n_cells, 1.2)
nutrients_solver.PO4 = np.full(n_cells, 0.08)
nutrients_solver.OrgN = np.full(n_cells, 0.5)
nutrients_solver.OrgP = np.full(n_cells, 0.05)
algae_solver.Chla = np.full(n_cells, 12.0)

# ==================== 3. 水力和气象 ====================
u = np.full(n_cells, 0.3)
h = np.full(n_cells, 2.5)
manning_n = np.full(n_cells, 0.03)

T_air_initial = 0.0
T_air_final = -15.0

# ==================== 4. 主循环 ====================
results = []
n_steps = n_days * 24

for step in range(n_steps):
    time_days = step * dt / 86400.0

    # 气温线性降温
    T_air = T_air_initial + (T_air_final - T_air_initial) * (time_days / n_days)

    # 气象参数
    I_0 = np.full(n_cells, 100.0)
    wind_speed = 5.0
    relative_humidity = 0.7

    # ==================== 5. 推进各模块 ====================

    # (a) 水温
    T = temp_solver.step(dt, u, h, T_air, I_0.mean(), wind_speed, relative_humidity)

    # (b) 冰盖
    ice_state = ice_solver.step(dt, T_air, T)

    # (c) 营养盐
    nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)

    # (d) 藻类
    algae_state = algae_solver.step(
        dt, u, h, T, I_0,
        nutrients_solver.NH4,
        nutrients_solver.NO3,
        nutrients_solver.PO4
    )

    # (e) 溶解氧
    do_state = do_solver.step(dt, u, h, T, manning_n)

    # ==================== 6. 耦合 ====================
    dt_day = dt / 86400.0

    # 藻类产氧
    do_solver.DO += algae_state['DO_production'] * dt_day
    do_solver.DO = np.maximum(do_solver.DO, 0.0)

    # 营养盐消耗
    nutrients_solver.NH4 -= algae_state['NH4_uptake'] * dt_day
    nutrients_solver.NO3 -= algae_state['NO3_uptake'] * dt_day
    nutrients_solver.PO4 -= algae_state['PO4_uptake'] * dt_day

    nutrients_solver.NH4 = np.maximum(nutrients_solver.NH4, 0.0)
    nutrients_solver.NO3 = np.maximum(nutrients_solver.NO3, 0.0)
    nutrients_solver.PO4 = np.maximum(nutrients_solver.PO4, 0.0)

    # ==================== 7. 保存结果 ====================
    if step % 24 == 0:  # 每天保存
        results.append({
            'time': time_days,
            'T': T.mean(),
            'DO': do_solver.DO.mean(),
            'ice_thickness': ice_state['ice_thickness'].mean(),
            'NH4': nutrients_solver.NH4.mean(),
            'NO3': nutrients_solver.NO3.mean(),
            'Chla': algae_solver.Chla.mean()
        })

        print(f"第{int(time_days)+1}天: "
              f"T={T.mean():.2f}°C, "
              f"DO={do_solver.DO.mean():.2f}mg/L, "
              f"冰厚={ice_state['ice_thickness'].mean():.3f}m, "
              f"Chla={algae_solver.Chla.mean():.2f}μg/L")

# ==================== 8. 保存和可视化 ====================
# 保存为NPZ
import pandas as pd
df = pd.DataFrame(results)
np.savez('coupled_results.npz',
         times=df['time'].values,
         water_temperature=df['T'].values,
         dissolved_oxygen=df['DO'].values,
         ice_thickness=df['ice_thickness'].values,
         NH4=df['NH4'].values,
         NO3=df['NO3'].values,
         chlorophyll_a=df['Chla'].values)

print("\n结果已保存至 coupled_results.npz")
print("可使用以下命令可视化:")
print("  python tools/visualize_results.py coupled_results.npz --plot-type all")
```

---

## 📊 参数调优指南

### 溶解氧模块参数

| 参数 | 清洁水体 | 污染水体 | 单位 |
|------|----------|----------|------|
| kd_20 | 0.05 - 0.15 | 0.15 - 0.40 | 1/day |
| SOD_20 | 0.5 - 1.5 | 1.5 - 3.0 | g/m²/day |

### 营养盐模块参数

| 过程 | 速率范围 | 单位 |
|------|----------|------|
| 氨化 | 0.02 - 0.10 | 1/day |
| 硝化 | 0.05 - 0.20 | 1/day |
| 反硝化 | 0.01 - 0.05 | 1/day |
| 磷释放 | 0.01 - 0.05 | 1/day |

### 藻类模块参数

| 藻种 | 最大生长率 (mu_max_20) | 最适光照 (I_opt) |
|------|----------------------|------------------|
| 硅藻 | 1.0 - 2.0 1/day | 100 - 150 W/m² |
| 蓝藻 | 0.5 - 1.5 1/day | 150 - 200 W/m² |
| 绿藻 | 1.5 - 3.0 1/day | 100 - 200 W/m² |

**半饱和常数:**
- 氮 (K_N): 0.01 - 0.05 mg-N/L
- 磷 (K_P): 0.001 - 0.005 mg-P/L

---

## ⚠️ 常见问题

### Q1: 如何处理边界条件？

A: 目前实现为周期性边界。如需其他边界条件，可在 `step()` 后手动设置:

```python
# 上游固定浓度
solver.DO[0] = 10.0

# 下游零梯度
solver.DO[-1] = solver.DO[-2]
```

### Q2: 如何选择时间步长？

A: 建议:
- 水温/DO/营养盐: dt = 600 - 3600 s (10分钟 - 1小时)
- 冰盖: dt = 3600 - 7200 s (1 - 2小时)
- 藻类: dt = 600 - 1800 s (10 - 30分钟)

### Q3: 如何加速计算？

A: 三种方法:
1. 启用 Numba: `use_numba=True` (提速 2-5x)
2. 增大时间步长 (注意稳定性)
3. 使用粗网格 (注意精度)

### Q4: 模型如何验证？

A: 参考:
- `tests/` 目录中的验证案例
- Streeter-Phelps 解析解对比
- 商业软件 (QUAL2K, CE-QUAL-W2) 对比

### Q5: 如何调试数值不稳定？

A: 检查:
1. 时间步长是否过大
2. 初始条件是否合理
3. 参数是否在建议范围内
4. 是否有NaN或Inf值

```python
# 调试代码
import numpy as np

# 检查NaN
if np.any(np.isnan(solver.DO)):
    print("警告: DO中存在NaN值")

# 检查范围
if np.any(solver.DO < 0):
    print("警告: DO出现负值")
    solver.DO = np.maximum(solver.DO, 0.0)
```

---

## 📚 更多资源

- **示例代码**: `examples/` 目录
  - `winter_river_simulation.py`: 冬季河流模拟
  - `summer_eutrophication.py`: 夏季富营养化
  - `spring_ice_breakup.py`: 春季融冰

- **测试案例**: `tests/` 目录
  - 单元测试
  - 集成测试
  - 验证案例

- **工具**:
  - `tools/visualize_results.py`: 结果可视化
  - `tools/export_data.py`: 数据导出
  - `tools/sensitivity_analysis.py`: 参数敏感性分析
  - `tools/run_from_config.py`: 配置驱动模拟

- **文档**:
  - `CONTRIBUTING.md`: 开发者贡献指南
  - `QUICKSTART_ICE_WATER_QUALITY.md`: 快速入门
  - `README_ICE_WATER_QUALITY.md`: 模块总览

---

**版本**: v1.0
**更新日期**: 2025-11-02
**维护**: HydroClaude Team
**许可证**: MIT License
