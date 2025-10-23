# HydroClaude 开发指南
# Development Guide

**版本**: 2.0
**更新日期**: 2025-10-23
**重要更新**: 新增通用工具库（ScriptHelper, PlotHelper）

---

## 🚀 快速开始（新增工具）

### ScriptHelper - 消除路径设置重复代码

```python
from utils.script_helper import quick_setup

# 一行代码完成所有设置（自动添加项目路径）
helper = quick_setup(__file__)

# 导入项目模块（无需手动设置sys.path）
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

# 获取输出路径
output_dir = helper.get_output_dir()  # 自动创建results/目录
fig_path = helper.get_output_path("figure.png")
```

### PlotHelper - 标准化绘图

```python
from utils.plot_helper import PlotHelper

helper = PlotHelper()

# 快速绘制纵剖面
fig = helper.plot_profile(
    x, h,
    xlabel="Distance (km)",
    ylabel="Water Depth (m)",
    structures=[(25, "Gate"), (50, "Pump")],  # 自动标注结构物
    save_path=output_dir / "profile.png"
)
```

---

## 📋 目录

1. [开发原则](#开发原则)
2. [基础类库优先原则](#基础类库优先原则)
3. [基础类库清单](#基础类库清单)
4. [新增通用工具](#新增通用工具) ⭐ NEW
5. [开发工作流](#开发工作流)
6. [代码规范](#代码规范)
7. [测试与验证](#测试与验证)
8. [何时扩展基础库](#何时扩展基础库)

---

## 🎯 开发原则

### 核心原则

1. **📚 基础库优先 (Library First)**
   - **始终先检查基础库**是否已有相关功能
   - **禁止重复实现**已有的功能
   - 有疑问时查阅 `LIBRARY_REFERENCE.md`

2. **🔍 搜索后扩展 (Search Then Extend)**
   - 基础库无法解决时，**必须先上网搜索**最佳实践
   - 参考权威文献和最新研究成果
   - 将新功能**整合到基础库**，而非临时实现

3. **✅ 验证为本 (Validation First)**
   - 所有结果必须使用 `ResultValidator` 验证
   - 生成专业可视化和报告
   - 追求数值精度和物理合理性

4. **📖 文档同步 (Documentation Sync)**
   - 新增基础库功能必须更新文档
   - 提供使用示例
   - 说明适用场景和限制

---

## 📚 基础类库优先原则

### ⚠️ 开发前必读检查清单

在开始任何新功能开发之前，**必须**按以下顺序检查：

```
✅ 1. 检查 LIBRARY_REFERENCE.md - 查看基础库是否已有相关功能
✅ 2. 检查 examples/ - 查看示例代码是否有类似实现
✅ 3. 检查 SCRIPT_UPGRADE_SUMMARY.md - 查看最近的最佳实践
✅ 4. 如果都没有 → 搜索最佳方案 → 扩展基础库
```

### 🚫 禁止行为

❌ **禁止：随手写一个临时函数**
```python
# ❌ 错误示例
def validate_flow(Q, Q_target):
    error = abs(Q - Q_target) / Q_target * 100
    if error < 1.0:
        print("OK")
    else:
        print("Bad")
```

✅ **正确：使用基础库**
```python
# ✅ 正确示例
from utils.result_validator import quick_validate_steady_state

validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=Q_target,
    name="我的测试"
)
# 自动分级、生成报告、保存图表
```

---

## 📦 基础类库清单

### 1. 求解器类 (Solvers)

#### 🌟 HydrostaticCanalSolver (Phase 2) - **首选**

**位置**: `solvers/hydrostatic_canal_solver.py`

**何时使用**:
- ✅ 任何需要高精度流量守恒的场景
- ✅ 稳态求解（0-1次迭代收敛）
- ✅ 包含闸门/堰/孔口的复杂结构
- ✅ 小Froude数流动

**核心方法**:
```python
# 创建求解器
solver = HydrostaticCanalSolver(
    length=1000.0,          # 渠道长度
    nx=201,                 # 网格数
    B=10.0,                 # 宽度
    S0=0.001,               # 底坡
    n=0.025,                # Manning糙率
    internal_structures=[   # 内部结构
        (位置, 结构对象),
        ...
    ]
)

# 稳态求解
result = solver.solve_steady_state(
    Q_target=10.0,              # 目标流量
    h_downstream=1.0,           # 下游水深
    max_iterations=5000,
    convergence_tol=0.1,        # 推荐宽松容差
    dt=0.5,
    verbose=True
)

# 非恒定流时间步进
h_new, hu_new = solver.step_preissmann(
    dt=0.5,
    max_iter=10,
    enforce_bc=True,
    Q_in=Q_upstream,
    h_out=h_downstream
)
```

**预期性能**:
- 流量误差: **0.000000%** (所有场景)
- 迭代次数: **0-1次** (简单场景), **1-10次** (复杂场景)
- 闸门误差: **< 0.5%**

**参考示例**:
- `examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py`
- `examples/example_01_canal_flow/scripts/08_optimized_steady_solving_v2.py`
- `examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py`

---

### 2. 验证工具 (Validation)

#### 🌟 ResultValidator - **必须使用**

**位置**: `utils/result_validator.py`

**何时使用**:
- ✅ **所有稳态求解后** - 验证流量守恒
- ✅ **所有含结构的场景** - 验证闸门/堰/孔口流量
- ✅ **生成报告时** - 自动分级和专业报告

**快速使用**:
```python
from utils.result_validator import quick_validate_steady_state

# 一行搞定验证
validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=10.0,
    name="我的场景名称"
)

# 自动输出：
# ✓ 收敛状态
# ✓ 流量守恒分级（优秀/良好/可接受）
# ✓ 闸门流量验证
```

**高级使用**:
```python
from utils.result_validator import ResultValidator

validator = ResultValidator()

# 1. 验证流量守恒
validator.validate_flow_conservation(
    Q_computed=result['Q'],
    Q_target=10.0,
    label="Overall Flow"
)

# 2. 验证闸门流量
validator.validate_gate_discharge(
    solver=solver,
    gate_objects=[gate1, gate2],
    gate_indices=[i1, i2],
    Q_target=10.0,
    result_h=result['h']
)

# 3. 生成流量验证图
fig = validator.plot_flow_distribution(
    x=solver.x,
    Q=result['Q'],
    Q_target=10.0,
    gate_positions=[5000.0],
    save_path="my_validation.png"
)

# 4. 保存报告
validator.save_report("my_report.txt")
```

**自动分级标准**:
- **优秀 (Excellent)**: < 0.01%
- **良好 (Good)**: < 0.1%
- **可接受 (Acceptable)**: < 1.0%

---

### 3. 可视化工具 (Visualization)

#### 🌟 VisualizationTemplates - **专业图表必备**

**位置**: `utils/visualization_templates.py`

**何时使用**:
- ✅ 生成专业水力学图表
- ✅ 需要标准化可视化
- ✅ 论文/报告级别的图表质量

**18种专业模板**:

```python
from utils.visualization_templates import VisualizationTemplates

viz = VisualizationTemplates()

# 1. 纵剖面图（水面线）
fig = viz.plot_longitudinal_profile(
    x=x, h=h, S0=0.001,
    canal_length=1000.0,
    title="Water Surface Profile"
)

# 2. 流量分布图
fig = viz.plot_flow_distribution(
    x=x, Q=Q, Q_target=10.0,
    show_error=True
)

# 3. 速度场（流线图）
fig = viz.plot_velocity_field(
    X=X, Y=Y, U=U, V=V,
    streamlines=True,
    quiver=False
)

# 4. 3D水面
fig = viz.plot_3d_water_surface(
    x=x, time=time, h=h,
    S0=0.001, canal_length=1000.0
)

# 5. 回水曲线分析
fig = viz.plot_backwater_curve(
    x=x, h=h,
    h_normal=h_n, h_critical=h_c,
    S0=0.001, classify=True
)

# 6. Froude数分布
fig = viz.plot_froude_number(
    x=x, Fr=Fr,
    highlight_critical=True
)

# 7. 能量线（EGL/HGL）
fig = viz.plot_energy_line(
    x=x, h=h, v=v,
    S0=0.001, canal_length=1000.0
)

# 8. 动画（纵剖面演化）
fig, anim = viz.create_longitudinal_animation(
    x=x,
    h_snapshots=h_list,
    Q_snapshots=Q_list,
    time_snapshots=time_list,
    save_path="animation.gif"
)

# ... 还有10+其他模板，详见 LIBRARY_REFERENCE.md
```

**完整模板列表**: 参见 `LIBRARY_REFERENCE.md` 第3节

---

### 4. 水力学计算工具 (Utilities)

#### canal_utils.py

**位置**: `utils/canal_utils.py`

**常用函数**:

```python
from utils.canal_utils import (
    compute_steady_uniform_flow,    # 计算均匀流水深
    compute_critical_depth,         # 计算临界水深
    compute_froude_number,          # 计算Froude数
    compute_specific_energy,        # 计算比能
    get_convergence_metrics         # 收敛性指标
)

# 1. 均匀流水深（最常用！）
h_uniform = compute_steady_uniform_flow(
    Q=10.0,      # 流量
    B=10.0,      # 宽度
    S0=0.001,    # 底坡
    n=0.025      # Manning糙率
)

# 2. 临界水深
h_c = compute_critical_depth(Q=10.0, B=10.0)

# 3. Froude数
Fr = compute_froude_number(h=1.0, u=1.0)

# 4. 比能
E = compute_specific_energy(h=1.0, u=1.0)

# 5. 收敛性分析
metrics = get_convergence_metrics(
    time=time_array,
    h_history=h_history,
    Q_history=Q_history
)
```

---

### 5. 结构对象 (Structures)

#### gate.py

**位置**: `solvers/gate.py`

**可用结构**:

```python
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice

# 1. 闸门
gate = SluiceGate(
    position=5000.0,    # 位置
    width=10.0,         # 宽度
    opening=5.0,        # 开度
    Cd=0.6              # 流量系数
)

# 2. 宽顶堰
weir = BroadCrestedWeir(
    position=5000.0,
    width=10.0,
    crest_height=0.5,   # 堰顶高度
    Cd=0.848
)

# 3. 孔口
orifice = Orifice(
    position=5000.0,
    width=4.0,
    height=2.0,
    bottom_elevation=0.2,
    Cd=0.61
)

# 使用方法：
solver = HydrostaticCanalSolver(
    ...,
    internal_structures=[
        (2500.0, gate),
        (5000.0, weir),
        (7500.0, orifice)
    ]
)
```

---

### 6. 输出助手 (Output Helper)

#### output_helper.py

**位置**: `examples/example_01_canal_flow/scripts/output_helper.py`

**自动管理输出**:

```python
from output_helper import get_output_path, save_figure, save_table

# 1. 自动管理路径
fig_path = get_output_path('figures', 'my_plot.png')
# 自动创建: results/figures/my_plot.png

table_path = get_output_path('tables', 'my_data.csv')
# 自动创建: results/tables/my_data.csv

# 2. 保存图表（自动创建目录）
save_figure(fig, 'my_analysis.png')
# 保存到: results/figures/my_analysis.png
# 自动打印确认信息

# 3. 保存数据表
import pandas as pd
df = pd.DataFrame({...})
save_table(df, 'my_results.csv', index=False)
# 保存到: results/tables/my_results.csv
# 自动打印确认信息
```

---

## 🔄 开发工作流

### 标准工作流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 收到新任务                                                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2. 📚 检查 LIBRARY_REFERENCE.md                             │
│     - 基础库是否已有相关功能？                                 │
│     - 有类似的示例吗？                                         │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    是否找到？
                    ↙        ↘
                  是          否
                  ↓            ↓
    ┌─────────────────┐  ┌──────────────────┐
    │  3a. 使用基础库  │  │  3b. 🔍 搜索方案  │
    │   - 参考示例     │  │   - 上网搜索      │
    │   - 复用代码     │  │   - 查文献        │
    └─────────────────┘  │   - 找最佳实践    │
                         └──────────────────┘
                                  ↓
                         ┌──────────────────┐
                         │  4. 扩展基础库    │
                         │   - 实现新功能    │
                         │   - 更新文档      │
                         │   - 添加示例      │
                         └──────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│  5. ✅ 验证结果                                               │
│     - 使用 ResultValidator                                   │
│     - 生成专业可视化                                           │
│     - 保存报告                                                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  6. 📝 提交代码                                               │
│     - 更新文档（如有新功能）                                    │
│     - 提交清晰的commit message                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 代码规范

### 1. 脚本结构标准模板

**所有新脚本必须遵循此模板**:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本名称和功能描述

详细说明脚本的目的、测试场景等

Author: [作者]
Date: [日期]
"""

import sys, os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_path))))
sys.path.insert(0, project_root)

script_dir = os.path.dirname(script_path)
sys.path.insert(0, script_dir)

# ========== 基础库导入 ==========
# 1. 求解器
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

# 2. 结构
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice

# 3. 水力学计算
from utils.canal_utils import compute_steady_uniform_flow

# 4. 验证工具（必须！）
from utils.result_validator import ResultValidator, quick_validate_steady_state

# 5. 可视化
from utils.visualization_templates import VisualizationTemplates

# 6. 输出助手
from output_helper import get_output_path, save_figure, save_table

# ========== 其他导入 ==========
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def main():
    """主函数"""
    print("=" * 80)
    print("脚本标题")
    print("=" * 80)

    # 1. 参数设置
    print("\n1. 参数设置")
    print("-" * 80)
    # ... 参数定义 ...

    # 2. 创建求解器
    print("\n2. 创建求解器")
    print("-" * 80)
    solver = HydrostaticCanalSolver(...)

    # 3. 求解
    print("\n3. 稳态求解")
    print("-" * 80)
    result = solver.solve_steady_state(...)

    # 4. 验证（必须！）
    print("\n4. 结果验证")
    print("-" * 80)
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q_target,
        name="脚本名称"
    )

    # 5. 可视化
    print("\n5. 生成可视化")
    print("-" * 80)
    viz = VisualizationTemplates()
    fig = viz.plot_longitudinal_profile(...)
    save_figure(fig, 'my_result.png')

    # 6. 保存数据
    print("\n6. 保存数据")
    print("-" * 80)
    df = pd.DataFrame({...})
    save_table(df, 'my_data.csv')

    # 7. 总结
    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)
    print("\n关键结果:")
    print(f"  流量误差: {result['Q_error_percent']:.6f}%")
    # ...

    return validator


if __name__ == '__main__':
    validator = main()
```

---

### 2. 求解器使用规范

#### ✅ 正确示例

```python
# 1. 创建求解器
solver = HydrostaticCanalSolver(
    length=canal_length,
    nx=n_points,
    B=canal_width,
    S0=bed_slope,
    n=manning_n,
    internal_structures=[(pos, gate)]
)

# 2. 初始化
h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
solver.h[:] = h_uniform
solver.hu[:] = Q_target / B

# 3. 稳态求解
result = solver.solve_steady_state(
    Q_target=Q_target,
    h_downstream=h_uniform,
    max_iterations=5000,
    convergence_tol=0.1,      # 推荐宽松容差
    dt=0.5,
    verbose=True
)

# 4. 验证（必须！）
validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=Q_target,
    name="场景名称"
)
```

#### ❌ 错误示例

```python
# ❌ 错误1: 使用已废弃的旧求解器
from solvers.single_canal_solver import SingleCanalSolver
solver = SingleCanalSolver(...)  # 禁止！

# ❌ 错误2: 不验证结果
result = solver.solve_steady_state(...)
print(f"Done! Q_error = {result['Q_error_percent']}")  # 不够！

# ❌ 错误3: 手写验证代码
Q_avg = np.mean(result['Q'])
error = abs(Q_avg - Q_target) / Q_target * 100
if error < 1.0:
    print("Good")  # 应该用ResultValidator！
```

---

### 3. 可视化规范

#### ✅ 正确：使用VisualizationTemplates

```python
from utils.visualization_templates import VisualizationTemplates

viz = VisualizationTemplates()

# 使用专业模板
fig = viz.plot_longitudinal_profile(
    x=solver.x,
    h=result['h'],
    S0=bed_slope,
    canal_length=length,
    title="My Analysis"
)

save_figure(fig, 'my_analysis.png')
plt.close(fig)
```

#### ❌ 错误：手写matplotlib代码

```python
# ❌ 除非VisualizationTemplates没有对应模板，否则不要这样做
fig, ax = plt.subplots()
ax.plot(x, h)
ax.set_xlabel('Distance')
ax.set_ylabel('Depth')
# ... 一大堆格式化代码 ...
```

---

## ✅ 测试与验证

### 1. 必须的验证步骤

**每个脚本都必须包含**:

```python
# 1. 使用 ResultValidator
validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=Q_target,
    name="测试场景"
)

# 2. 生成流量验证图
fig = validator.plot_flow_distribution(
    x=solver.x,
    Q=result['Q'],
    Q_target=Q_target,
    gate_positions=[5000.0] if has_gates else None,
    save_path=get_output_path('figures', 'flow_validation.png')
)

# 3. 保存验证报告
report_path = get_output_path('reports', 'validation_report.txt')
validator.save_report(report_path)
```

### 2. 质量标准

**所有求解必须达到**:

- ✅ 流量守恒误差 < 0.01% (优秀)
- ✅ 闸门流量误差 < 1% (可接受)
- ✅ 收敛成功（不接受发散结果）
- ✅ 物理合理性（水深 > 0，Froude数合理）

---

## 🔧 何时扩展基础库

### 需要扩展的情况

当遇到以下情况时，应该扩展基础库：

1. **功能缺失**
   - 基础库确实没有相关功能
   - 这个功能具有通用性（不是一次性的）
   - 可能在其他地方重复使用

2. **性能问题**
   - 现有方法性能不足
   - 找到了更好的算法
   - 有学术论文支持

3. **精度提升**
   - 发现数值精度问题
   - 有更精确的方法
   - 需要更高阶格式

### 扩展基础库的流程

```
1. 🔍 上网搜索
   ├─ 搜索关键词: "water hydraulics [功能名] python 2024"
   ├─ 查找学术论文（Google Scholar）
   ├─ 查看开源项目（GitHub）
   └─ 阅读最佳实践

2. 📝 设计API
   ├─ 参考现有基础库的风格
   ├─ 保持接口简洁
   └─ 考虑扩展性

3. 💻 实现功能
   ├─ 在 utils/ 或 solvers/ 中添加
   ├─ 添加详细注释
   └─ 遵循代码规范

4. ✅ 测试验证
   ├─ 创建测试脚本
   ├─ 验证正确性
   └─ 性能测试

5. 📖 更新文档
   ├─ 更新 LIBRARY_REFERENCE.md
   ├─ 添加使用示例
   └─ 说明适用场景

6. 📦 提交代码
   ├─ 清晰的commit message
   ├─ 包含测试结果
   └─ 更新 CHANGELOG
```

### 扩展示例

**场景**: 需要计算渠道中的污染物输运

```python
# ========== Step 1: 搜索 ==========
# 搜索: "pollutant transport open channel python"
# 找到: 对流-扩散方程，上风格式

# ========== Step 2: 设计API ==========
# 文件: utils/transport_solver.py

class PollutantTransport:
    """
    污染物输运求解器

    使用一阶上风格式求解对流-扩散方程

    References:
        - [论文引用]
        - [开源项目引用]
    """

    def __init__(self, solver, diffusion_coeff=0.1):
        """
        Args:
            solver: HydrostaticCanalSolver实例
            diffusion_coeff: 扩散系数 (m²/s)
        """
        ...

    def step(self, C, dt):
        """
        时间步进

        Args:
            C: 浓度场 (mg/L)
            dt: 时间步长

        Returns:
            C_new: 新的浓度场
        """
        ...

# ========== Step 3: 实现并测试 ==========
# 创建测试脚本验证

# ========== Step 4: 更新文档 ==========
# 在 LIBRARY_REFERENCE.md 添加章节
```

---

## 📚 推荐资源

### 项目内文档

1. **LIBRARY_REFERENCE.md** - 基础库详细手册
2. **SCRIPT_UPGRADE_SUMMARY.md** - 最佳实践案例
3. **examples/** - 参考示例代码

### 水力学参考

1. **Open Channel Hydraulics** - Chow (1959)
2. **Computational Hydraulics** - Cunge et al. (1980)
3. **Finite Volume Methods for Hyperbolic Problems** - LeVeque (2002)

### 数值方法

1. **NumPy/SciPy** 官方文档
2. **Matplotlib** 官方示例
3. **Pandas** 数据处理

---

## 🎓 学习路径

### 新手开发者

1. 阅读 `LIBRARY_REFERENCE.md`
2. 运行 `examples/example_01_canal_flow/scripts/` 下的所有 v2 脚本
3. 理解 `HydrostaticCanalSolver` 和 `ResultValidator` 的使用
4. 尝试修改示例脚本的参数

### 进阶开发者

1. 深入理解 Phase 2 静水重构方法
2. 学习扩展基础库的流程
3. 贡献新功能到基础库
4. 优化现有算法性能

---

## ⚠️ 常见错误

### 1. 重复造轮子

```python
# ❌ 错误
def my_flow_validator(Q, Q_target):
    # ... 100行代码 ...
    pass

# ✅ 正确
from utils.result_validator import quick_validate_steady_state
validator = quick_validate_steady_state(...)
```

### 2. 不验证结果

```python
# ❌ 错误
result = solver.solve_steady_state(...)
# 直接用结果，不验证

# ✅ 正确
result = solver.solve_steady_state(...)
validator = quick_validate_steady_state(...)  # 必须验证！
```

### 3. 使用废弃的求解器

```python
# ❌ 错误
from solvers.single_canal_solver import SingleCanalSolver

# ✅ 正确
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
```

### 4. 手写可视化代码

```python
# ❌ 错误（除非必要）
fig, ax = plt.subplots()
# ... 50行matplotlib代码 ...

# ✅ 正确
from utils.visualization_templates import VisualizationTemplates
viz = VisualizationTemplates()
fig = viz.plot_longitudinal_profile(...)
```

---

## 📞 获取帮助

遇到问题时：

1. **查文档**: 先查 `LIBRARY_REFERENCE.md`
2. **看示例**: 参考 `examples/` 下的 v2 脚本
3. **搜历史**: 查看 `SCRIPT_UPGRADE_SUMMARY.md`
4. **搜网络**: 上网搜索最佳实践

---

**记住核心原则**:
1. 📚 **基础库优先** - 先查后写
2. 🔍 **搜索后扩展** - 学术严谨
3. ✅ **验证为本** - 质量第一
4. 📖 **文档同步** - 知识传承

---

**最后更新**: 2025-10-23
**维护者**: HydroClaude开发团队

**Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**
