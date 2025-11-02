# HydroClaude 冰-水质模块快速入门指南

欢迎使用 **HydroClaude 冰-水质模块** - 全球首个开源冰-水质耦合模拟系统！

本指南将帮助您在5分钟内开始使用HydroClaude进行冰-水质模拟。

---

## 📋 目录

1. [系统要求](#系统要求)
2. [快速开始](#快速开始)
3. [基础示例](#基础示例)
4. [运行测试](#运行测试)
5. [应用案例](#应用案例)
6. [进阶使用](#进阶使用)
7. [常见问题](#常见问题)

---

## 系统要求

### 必需软件
- Python 3.7+
- NumPy
- Matplotlib (可视化)

### 可选软件
- Numba (性能加速，2-5倍提速)
- pytest (运行测试套件)

### 安装依赖

```bash
# 基础依赖
pip install numpy matplotlib

# 可选依赖
pip install numba pytest
```

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/HydroClaude.git
cd HydroClaude
```

### 2. 运行第一个示例

```bash
# 冬季河流模拟（30天，100网格）
python examples/winter_river_simulation.py
```

**预期输出**:
```
======================================================================
HydroClaude 冬季河流冰-水质模拟示例
======================================================================
...
Day  30: T= 0.00°C, DO= 14.19mg/L, Ice=  0.0cm, Chla=  1.0μg/L
✓ 模拟完成!
```

### 3. 查看结果

模拟完成后，会在当前目录生成可视化结果：
- `winter_river_simulation_results.png` - 时间序列图
- `winter_river_simulation_spatial.png` - 空间分布图

---

## 基础示例

### 示例1: 简单DO模拟

```python
import numpy as np
from solvers.dissolved_oxygen import DissolvedOxygenSolver

# 创建求解器
n_cells = 100  # 网格数
dx = 100.0     # 空间步长 (m)
solver = DissolvedOxygenSolver(n_cells, dx, kd_20=0.2, SOD_20=1.0)

# 初始条件
solver.DO = np.full(n_cells, 8.0)   # 初始DO: 8 mg/L
solver.BOD = np.full(n_cells, 5.0)  # 初始BOD: 5 mg/L

# 水力条件
u = np.full(n_cells, 0.5)     # 流速: 0.5 m/s
h = np.full(n_cells, 2.0)     # 水深: 2.0 m
T = np.full(n_cells, 20.0)    # 水温: 20 °C
manning_n = np.full(n_cells, 0.03)

# 模拟1天
dt = 3600.0  # 1小时步长 (s)
for step in range(24):
    state = solver.step(dt, u, h, T, manning_n)
    print(f"Hour {step+1}: DO = {solver.DO.mean():.2f} mg/L")
```

---

### 示例2: 冰盖-水温耦合

```python
import numpy as np
from solvers.water_temperature import WaterTemperatureSolver
from solvers.ice_cover import IceCoverSolver

# 创建求解器
n_cells = 100
dx = 100.0

temp_solver = WaterTemperatureSolver(n_cells, dx)
temp_solver.T = np.full(n_cells, 2.0)  # 初始水温: 2°C

ice_solver = IceCoverSolver(n_cells=n_cells)

# 水力和气象条件
u = np.full(n_cells, 0.3)
h = np.full(n_cells, 2.5)
T_air = -10.0          # 气温: -10°C
I_0 = 100.0            # 太阳辐射: 100 W/m²
wind_speed = 5.0       # 风速: 5 m/s
relative_humidity = 0.7

# 模拟10天
dt = 3600.0
for day in range(10):
    for hour in range(24):
        # 水温模块
        T = temp_solver.step(
            dt, u, h, T_air, I_0, wind_speed, relative_humidity,
            ice_cover_fraction=ice_solver.ice_cover_fraction
        )

        # 冰盖模块
        ice_state = ice_solver.step(dt, T_air, T)

    print(f"Day {day+1}: T={T.mean():.2f}°C, Ice={ice_solver.ice_thickness.mean()*100:.1f}cm")
```

---

### 示例3: 完整耦合模拟

```python
import numpy as np
from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

# 创建所有求解器
n_cells = 100
dx = 100.0

temp_solver = WaterTemperatureSolver(n_cells, dx)
do_solver = DissolvedOxygenSolver(n_cells, dx, kd_20=0.15, SOD_20=1.0)
nutrients_solver = NutrientsSolver(n_cells, dx)
algae_solver = PhytoplanktonSolver(n_cells, dx)

# 初始化
temp_solver.T = np.full(n_cells, 25.0)
do_solver.DO = np.full(n_cells, 7.0)
do_solver.BOD = np.full(n_cells, 3.0)
nutrients_solver.NH4 = np.full(n_cells, 0.5)
nutrients_solver.NO3 = np.full(n_cells, 2.0)
nutrients_solver.PO4 = np.full(n_cells, 0.1)
algae_solver.Chla = np.full(n_cells, 20.0)

# 模拟循环
u = np.full(n_cells, 0.3)
h = np.full(n_cells, 2.5)
manning_n = np.full(n_cells, 0.03)
T_air = 28.0
I_0 = np.full(n_cells, 400.0)
wind_speed = 3.0
relative_humidity = 0.75

dt = 3600.0

for step in range(168):  # 7天
    # 各模块求解
    T = temp_solver.step(dt, u, h, T_air, I_0.mean(), wind_speed, relative_humidity)
    nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)
    algae_state = algae_solver.step(
        dt, u, h, T, I_0,
        nutrients_solver.NH4,
        nutrients_solver.NO3,
        nutrients_solver.PO4
    )
    do_state = do_solver.step(dt, u, h, T, manning_n)

    # 耦合
    dt_day = dt / 86400.0
    do_solver.DO += algae_state['DO_production'] * dt_day
    do_solver.DO = np.maximum(do_solver.DO, 0.0)
    nutrients_solver.NH4 -= algae_state['NH4_uptake'] * dt_day
    nutrients_solver.NH4 = np.maximum(nutrients_solver.NH4, 0.0)

    if (step + 1) % 24 == 0:
        day = (step + 1) / 24
        print(f"Day {day:.0f}: Chla={algae_solver.Chla.mean():.1f}μg/L, "
              f"DO={do_solver.DO.mean():.2f}mg/L")
```

---

## 运行测试

### 运行所有测试

```bash
# 需要先安装pytest
pip install pytest

# 运行所有测试
python -m pytest tests/ -v
```

### 运行特定测试

```bash
# Phase 1: 水温-DO-冰盖
python tests/test_ice_water_quality.py

# Phase 2: 冰花-冰塞
python tests/test_frazil_ice_jam.py

# Phase 3: 营养盐
python tests/test_nutrients.py

# Phase 4: 藻类
python tests/test_phytoplankton.py

# 集成测试
python tests/test_integration_simple.py
```

### 预期结果

所有测试应该通过：
```
======================================================================
通过率: 17/17 (100.0%)
======================================================================
🎉 所有测试通过!
```

---

## 应用案例

HydroClaude提供了多个完整的应用案例：

### 1. 冬季河流模拟
**文件**: `examples/winter_river_simulation.py`

**场景**: 北方河流冬季冰封期水质演变
- 模拟时间: 30天
- 气温: 0°C → -15°C
- 完整冰-水质耦合

**运行**:
```bash
python examples/winter_river_simulation.py
```

---

### 2. 夏季富营养化
**文件**: `examples/summer_eutrophication.py`

**场景**: 平原河流夏季藻华爆发
- 模拟时间: 14天
- 高温促进藻类生长
- DO昼夜变化明显

**运行**:
```bash
python examples/summer_eutrophication.py
```

---

### 3. 春季融冰期
**文件**: `examples/spring_ice_breakup.py`

**场景**: 春季解冻和生态恢复
- 模拟时间: 21天
- 气温: -5°C → 15°C
- 冰盖融化过程

**运行**:
```bash
python examples/spring_ice_breakup.py
```

---

### 4. 性能基准测试
**文件**: `examples/benchmark_performance.py`

**功能**: 测试不同网格规模的计算性能

**运行**:
```bash
python examples/benchmark_performance.py
```

**结果示例**:
```
规模                  网格数      每步耗时        加速比
----------------------------------------------------------
小规模 (50网格)         50       2.12  ms    1694343.1x
中规模 (100网格)        100      3.81  ms    944354.7x
大规模 (200网格)        200      7.29  ms    493677.9x
超大规模 (500网格)      500      17.84 ms    201750.8x
```

---

## 进阶使用

### 1. 启用Numba加速

```python
from solvers.water_temperature import WaterTemperatureSolver

# 启用Numba (2-5倍提速)
solver = WaterTemperatureSolver(n_cells, dx, use_numba=True)
```

**注意**: 首次运行会编译，之后速度显著提升。

---

### 2. 自定义参数

所有求解器都支持自定义参数：

```python
# DO求解器自定义参数
do_solver = DissolvedOxygenSolver(
    n_cells, dx,
    kd_20=0.20,        # BOD降解系数 (1/day) @ 20°C
    SOD_20=2.0,        # 底泥耗氧 (g/m²/day) @ 20°C
    Ka_method='ASCE',  # 复氧计算方法
    use_numba=False
)

# 藻类求解器自定义参数
algae_solver = PhytoplanktonSolver(
    n_cells, dx,
    mu_max_20=2.0,     # 最大生长速率 (1/day) @ 20°C
    I_s=100.0,         # 饱和光强 (W/m²)
    K_N_NH4=0.025,     # NH4半饱和常数 (mg/L)
    K_P=0.001,         # PO4半饱和常数 (mg/L)
    use_numba=False
)
```

完整参数列表请参考各模块的docstring。

---

### 3. 获取详细诊断信息

```python
# 运行一步模拟
algae_state = algae_solver.step(dt, u, h, T, I_0, NH4, NO3, PO4)

# 获取诊断信息
diagnostics = algae_state['diagnostics']
print(f"光限制因子: {diagnostics['f_I']}")
print(f"氮限制因子: {diagnostics['f_N']}")
print(f"磷限制因子: {diagnostics['f_P']}")
print(f"温度限制因子: {diagnostics['f_T']}")
print(f"生长速率: {algae_state['growth_rate']} μg/L/day")
print(f"DO产生: {algae_state['DO_production']} mg/L/day")
```

---

### 4. 保存和读取结果

```python
import numpy as np

# 保存结果
np.savez('simulation_results.npz',
    times=output_times,
    temperature=output_T,
    DO=output_DO,
    chlorophyll=output_Chla
)

# 读取结果
data = np.load('simulation_results.npz')
times = data['times']
temperature = data['temperature']
DO = data['DO']
chlorophyll = data['chlorophyll']
```

---

## 常见问题

### Q1: 如何选择合适的网格数？

**A**: 根据模拟需求选择：
- **教学演示**: 50-100网格
- **工程应用**: 100-200网格
- **科研精度**: 200-500网格
- **大规模**: > 500网格（建议启用Numba）

---

### Q2: 时间步长如何选择？

**A**: 遵循CFL稳定性条件：
```python
# CFL数
CFL = u * dt / dx  # 建议 < 0.5

# 推荐时间步长
dt = 0.5 * dx / u_max
```

常用值：
- 快速模拟: `dt = 3600 s` (1小时)
- 一般模拟: `dt = 1800 s` (30分钟)
- 精细模拟: `dt = 600 s` (10分钟)

---

### Q3: 如何处理"数值不稳定"？

**A**:
1. 减小时间步长 `dt`
2. 增加网格数（减小 `dx`）
3. 检查初始条件是否合理
4. 确保边界条件物理合理

---

### Q4: 结果如何验证？

**A**:
1. **质量守恒检查**: TN、TP应守恒
2. **物理合理性**: 值应在合理范围内
   - DO: 0-20 mg/L
   - 水温: -0.1-40 °C
   - 叶绿素: 0-500 μg/L
3. **对比经典解**: 使用Streeter-Phelps等解析解验证
4. **运行测试套件**: `python tests/test_*.py`

---

### Q5: 如何获得帮助？

**A**:
- 查看完整文档: `README_ICE_WATER_QUALITY.md`
- 查看测试代码: `tests/test_*.py`
- 查看应用案例: `examples/*.py`
- 提交Issue: GitHub Issues
- 技术文档: `docs/` 目录

---

## 下一步

现在您已经掌握了HydroClaude的基础使用，可以：

1. ✅ 探索更多应用案例 (`examples/`)
2. ✅ 阅读完整文档 (`README_ICE_WATER_QUALITY.md`)
3. ✅ 查看测试代码学习最佳实践 (`tests/`)
4. ✅ 尝试真实案例模拟
5. ✅ 贡献代码和反馈

---

## 相关资源

- **完整文档**: `README_ICE_WATER_QUALITY.md`
- **测试报告**: `TEST_RESULTS_COMPLETE.md`
- **项目总结**: `HYDROCLAUDE_V1_COMPLETE_SUMMARY.md`
- **技术文档**: `docs/ICE_WATER_QUALITY_PHASE*.md`

---

**欢迎使用 HydroClaude 冰-水质模块！** 🎉

如有问题或建议，请通过GitHub Issues联系我们。

**HydroClaude v1.0 - 全球首个开源冰-水质耦合模拟系统** ✨
