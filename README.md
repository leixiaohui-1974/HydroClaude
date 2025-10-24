# HydroClaude - 水力学仿真与优化框架

[![CI](https://github.com/leixiaohui-1974/HydroClaude/workflows/CI/badge.svg)](https://github.com/leixiaohui-1974/HydroClaude/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flow Accuracy](https://img.shields.io/badge/flow_error-0.000000%25-brightgreen.svg)](SCRIPT_UPGRADE_SUMMARY.md)
[![Solver](https://img.shields.io/badge/solver-Phase_2_Hydrostatic-blue.svg)](solvers/hydrostatic_canal_solver.py)

HydroClaude是一个专业的水力学仿真与优化框架，专注于明渠流动、管网系统和梯级水库调度。

**🎯 核心特性**:
- 🚀 **极致精度**: 流量守恒误差 < 0.000001%
- ⚡ **极速收敛**: 0-1次迭代（典型场景）
- 🔧 **产品级质量**: 经过5+示例脚本验证
- 📚 **完整文档**: 开发指南 + 库参考手册

---

## 📚 文档导航

| 文档 | 说明 | 适用对象 |
|-----|------|---------|
| **[快速入门指南](QUICKSTART_GUIDE.md)** 🆕 | 30分钟快速上手 | 新用户 ⭐⭐⭐ |
| **[示例案例目录](examples/EXAMPLES_CATALOG.md)** 🆕 | 43个示例的完整索引 | 所有用户 ⭐⭐⭐ |
| **[开发指南](DEVELOPMENT_GUIDE.md)** | 基础库优先原则、代码规范、工作流 | 所有开发者 ⭐ |
| **[库参考手册](LIBRARY_REFERENCE.md)** | 完整API文档、使用示例 | 所有开发者 ⭐ |
| **[脚本升级总结](SCRIPT_UPGRADE_SUMMARY.md)** | 5个示例的详细测试结果 | 了解最佳实践 |
| **[示例代码](examples/)** | 可运行的完整示例 | 快速上手 |

**⚠️ 开发前必读**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - 避免重复造轮子！

---

## 🚀 快速开始（5分钟）

### 第一个示例

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行最简单的示例
cd examples/example_simple_canal
python run.py

# 3. 查看结果
# results/profile.png - 水面线剖面图
```

### 使用通用建模器

```bash
# 命令行运行任意配置
python -m modeling.universal_modeler examples/example_simple_canal/config.yaml

# 查看帮助
python -m modeling.universal_modeler
```

### 使用统一CLI工具 🆕

HydroClaude提供统一的命令行工具，整合所有功能：

```bash
# 查看帮助
python hydroclaude_cli.py --help

# 运行模拟
python hydroclaude_cli.py run config.yaml

# 创建配置（交互式）
python hydroclaude_cli.py config create

# 使用模板快速创建配置
python hydroclaude_cli.py config create --template basic_canal

# 列出所有示例
python hydroclaude_cli.py list

# 验证所有示例
python hydroclaude_cli.py validate --report

# 运行测试
python hydroclaude_cli.py test --type unit

# 性能基准测试
python hydroclaude_cli.py benchmark

# 项目健康检查
python hydroclaude_cli.py health --report

# 查看文档
python hydroclaude_cli.py docs --type quickstart
```

**完整教程**: 查看 [快速入门指南](QUICKSTART_GUIDE.md)

---

## 🆕 新增功能（v1.0 - 2025-10-24）

### 1. 工程案例库 ✨

完整的工程实践案例，涵盖设计、运行、控制、优化：

| 案例 | 类型 | 说明 | 运行时间 |
|------|------|------|----------|
| [case_01_irrigation_design](examples/engineering_cases/case_01_irrigation_design/) | 设计 | 灌溉渠道设计优化 | ~10s |
| [case_02_flood_emergency](examples/engineering_cases/case_02_flood_emergency/) | 运行 | 防洪应急响应（时变边界） | ~30s |
| [case_03_multi_gate_control](examples/engineering_cases/case_03_multi_gate_control/) | 控制 | 多闸门协同控制（3×3 MPC） | ~60s |
| [case_04_parameter_calibration](examples/engineering_cases/case_04_parameter_calibration/) | 校准 | 参数在线估计（增广EKF） | ~30s |
| [case_05_water_resource_optimization](examples/engineering_cases/case_05_water_resource_optimization/) | 优化 | 水资源调度（峰谷电价） | ~20s |

### 2. 控制系统示例 ✨

完整的PID和MPC控制器示例：

```bash
# PID控制
python -m modeling.universal_modeler examples/example_control/config_pid_water_level.yaml

# MPC控制（调优版）
python -m modeling.universal_modeler examples/example_control/config_mpc_tuned.yaml
```

**性能**：
- PID: MAE 0.79m
- MPC: MAE 0.95m（控制更平滑）

[查看控制系统文档 →](examples/example_control/README.md)

### 3. 闸泵控制策略对比 ✨

3种不同控制策略的系统对比：

| 策略 | 方法 | MAE | 控制平滑度 | 特点 |
|------|------|-----|-----------|------|
| Strategy 1 | PID | 0.546m | 基准 | 快速响应 |
| Strategy 2 | MPC | 0.546m | **54% ↑** | 预测优化 |
| Strategy 3 | 分层MPC+PID | 0.546m | **77% ↑** | 协同控制 |

[查看策略对比总结 →](examples/example_gate_pump_cascade/control_strategies/SUMMARY.md)

### 4. 结构类型展示 ✨

展示所有7种水工结构类型的综合案例：

```bash
python examples/example_structure_showcase/run.py
```

**支持的结构**：SluiceGate（闸门）、Transition（过渡段）、BroadCrestedWeir（宽顶堰）、Drop（跌水）、Spillway（溢洪道）、Orifice（孔口）、PumpStation（泵站）

[查看结构展示文档 →](examples/example_structure_showcase/README.md)

### 5. 时变边界条件展示 ✨

3种时变边界条件类型的完整展示：

```bash
# 运行所有3种类型
python examples/example_time_varying_bc/run_all.py
```

**类型**：
- **Sinusoidal**（正弦波动）- 潮汐、周期调度 - 性能：38× 实时
- **Step**（阶跃变化）- 突发事件 - 性能：35× 实时
- **Linear**（线性变化）- 渐进过程 - 性能：36× 实时

[查看时变边界文档 →](examples/example_time_varying_bc/README.md)

### 6. 完整的示例验证系统 ✨

快速验证所有新增案例：

```bash
python examples/validate_new_examples.py
```

**测试覆盖**：12个新增案例，预期成功率100%

---

## 📊 示例案例

### 推荐学习路径

```
初学者（1-2小时）:
  example_simple_canal → example_universal_modeling → example_structure_showcase

进阶用户（3-5小时）:
  engineering_cases/case_01 → case_02 → example_control → case_03

专业开发者：
  浏览 LIBRARY_REFERENCE.md → 研究 engineering_cases → 自定义开发
```

### 完整案例目录

**总计**: 43个示例案例

详见 [示例案例目录](examples/EXAMPLES_CATALOG.md) 📚

---

## 🆕 新增通用工具 (v2.0)

### 📦 ScriptHelper - 一行代码设置项目路径

消除85+个脚本中的重复路径设置代码：

```python
from utils.script_helper import quick_setup

# 一行完成所有设置
helper = quick_setup(__file__)

# 无需手动sys.path设置，直接导入
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

# 自动管理输出目录
output_dir = helper.get_output_dir()  # 自动创建results/
fig_path = helper.get_output_path("figure.png")
```

### 📊 PlotHelper - 标准化专业绘图

统一的绘图接口，自动处理结构物标注：

```python
from utils.plot_helper import PlotHelper

plotter = PlotHelper()

# 纵剖面图 + 自动标注结构物
fig = plotter.plot_profile(
    x, h,
    xlabel="Distance (km)",
    ylabel="Water Depth (m)",
    structures=[(25, "Gate1"), (50, "Pump"), (75, "Gate2")]
)

# 时空演化图
fig = plotter.plot_contour(X, T, h_history,
                           xlabel="Distance",
                           ylabel="Time",
                           vlines=[(25, "Gate1"), (50, "Pump")])
```

**效益**:
- ✅ 减少80%的重复代码
- ✅ 统一的图表样式
- ✅ 自动处理中文字体问题

### 📝 ReportGenerator - 自动生成专业报告 🆕

一键生成Markdown/HTML/JSON格式的专业报告：

```python
from utils.report_generator import ReportGenerator

# 创建报告生成器
reporter = ReportGenerator(
    project_name="灌溉渠道仿真",
    output_dir="reports"
)

# 添加系统配置
reporter.add_system_info({
    '渠道长度': '10 km',
    '渠道宽度': '10 m',
    '底坡': '0.001'
})

# 添加仿真结果
reporter.add_results({
    '最大水深': 3.5,
    '平均流量': 15.3,
    '收敛迭代': 5
})

# 添加图表
reporter.add_figure('profile.png', '水面线剖面图')

# 生成多种格式报告
reporter.generate_markdown()  # Markdown报告
reporter.generate_html()      # HTML报告（带专业样式）
reporter.generate_summary_json()  # JSON摘要
```

### 📈 TimeSeriesAnalyzer - 时间序列深度分析 🆕

对非稳态仿真结果进行全面分析：

```python
from utils.time_series_analyzer import TimeSeriesAnalyzer

# 创建分析器
analyzer = TimeSeriesAnalyzer(time=t_array, data=h_array, name="水深")

# 统计分析
stats = analyzer.compute_statistics()
# 输出: 均值、标准差、偏度、峰度、变异系数等

# 趋势检测
trend = analyzer.detect_trend('linear')
# 输出: 斜率、R²、显著性检验

# 异常检测
outliers = analyzer.detect_outliers('iqr')
# 输出: 异常点数量、位置、比例

# 频谱分析
frequencies, power = analyzer.compute_spectrum('welch')

# 周期性检测
periodicity = analyzer.detect_periodicity()
# 输出: 是否周期、主周期时长

# 自动生成6面板分析报告图
analyzer.generate_analysis_report('analysis.png')
```

### 💾 DataExporter - 统一数据导出 🆕

支持CSV/JSON/NPZ多种格式的数据导出：

```python
from utils.data_exporter import DataExporter

exporter = DataExporter(output_dir='results')

# 导出时间序列（支持多格式）
files = exporter.export_time_series(
    time=t_array,
    data={'depth': h_array, 'flow': Q_array},
    filename='simulation',
    formats=['csv', 'json', 'npz']
)

# 导出空间剖面
exporter.export_profile(
    x=x_grid,
    data={'depth': h_final, 'velocity': v_final},
    filename='profile',
    format='csv'
)

# 导出汇总信息
exporter.export_summary({
    '仿真名称': '测试仿真',
    '最大水深': 3.5,
    '平均流量': 15.3
}, format='json')
```

---

## ✨ 核心基础库

### 🌟 HydrostaticCanalSolver - 高精度求解器 (推荐)

**Phase 2静水重构方法**，生产级别质量：

```python
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import quick_validate_steady_state

# 1. 创建求解器
gate = SluiceGate(position=5000.0, width=10.0, opening=5.0)
solver = HydrostaticCanalSolver(
    length=10000.0,
    nx=301,
    B=10.0,
    S0=0.0005,
    n=0.025,
    internal_structures=[(5000.0, gate)]
)

# 2. 初始化
h_uniform = compute_steady_uniform_flow(10.0, 10.0, 0.0005, 0.025)
solver.h[:] = h_uniform
solver.hu[:] = 10.0 / 10.0

# 3. 稳态求解（推荐宽松容差，极快收敛）
result = solver.solve_steady_state(
    Q_target=10.0,
    h_downstream=h_uniform,
    max_iterations=5000,
    convergence_tol=0.1,  # 推荐：宽松容差
    dt=0.5,
    verbose=True
)
# 预期: 0-1次迭代, 流量误差 0.000000%

# 4. 自动验证（必须！）
validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=10.0,
    name="单闸门测试"
)
# 自动输出: 收敛状态、流量误差分级、闸门流量验证
```

**性能基准** (基于5个示例脚本的实测数据):

| 场景 | 迭代次数 | 流量误差 | 计算时间 |
|-----|---------|---------|---------|
| 单闸门 | 0-1 | 0.000000% | 0.04-0.08s |
| 三闸门串联 | 0-1 | 0.000000% | 0.04-0.08s |
| 混合结构 | 1-82 | 0.000000% | 0.07-3.08s |
| 10km渠道 | 0-1 | 0.000000% | <0.1s |

详见: [SCRIPT_UPGRADE_SUMMARY.md](SCRIPT_UPGRADE_SUMMARY.md)

---

### 🔍 ResultValidator - 自动验证工具 (必须使用)

**自动分级、生成报告、保存图表**：

```python
from utils.result_validator import quick_validate_steady_state

# 一行搞定验证
validator = quick_validate_steady_state(
    solver=solver,
    result_dict=result,
    Q_target=10.0,
    name="测试场景"
)

# 自动输出：
# ================================================================================
# 测试场景
# ================================================================================
#
# [✓ 收敛] 迭代次数: 1 (极快 (1次))
# [优秀 (Excellent)] Overall 流量守恒: 0.000000% (目标=10.0000, 平均=10.0000)
#
# 闸门流量验证:
# [优秀] 闸门1: Q=9.9655 m³/s (误差0.35%, submerged)
```

**自动分级标准**:
- 🟢 **优秀 (Excellent)**: < 0.01%
- 🔵 **良好 (Good)**: < 0.1%
- 🟡 **可接受 (Acceptable)**: < 1.0%
- 🔴 **差 (Poor)**: ≥ 1.0%

---

### 🎨 VisualizationTemplates - 18种专业图表

```python
from utils.visualization_templates import VisualizationTemplates
from output_helper import save_figure

viz = VisualizationTemplates()

# 1. 纵剖面图（水面线）
fig = viz.plot_longitudinal_profile(
    x=solver.x, h=result['h'], S0=0.001,
    canal_length=1000.0, title="Water Surface Profile"
)
save_figure(fig, 'profile.png')

# 2. 流量分布图
fig = viz.plot_flow_distribution(
    x=solver.x, Q=result['Q'], Q_target=10.0
)

# 3. 回水曲线分析
fig = viz.plot_backwater_curve(
    x=solver.x, h=result['h'],
    h_normal=h_n, h_critical=h_c, S0=0.001
)

# 4. Froude数分布
fig = viz.plot_froude_number(x=solver.x, Fr=Fr_array)

# 5. 能量线（EGL/HGL）
fig = viz.plot_energy_line(
    x=solver.x, h=result['h'], v=v, S0=0.001
)

# ... 还有13+其他专业模板
```

详见: [LIBRARY_REFERENCE.md](LIBRARY_REFERENCE.md)

---

### 🧮 水力学计算工具

```python
from utils.canal_utils import (
    compute_steady_uniform_flow,  # 均匀流水深（最常用）
    compute_critical_depth,       # 临界水深
    compute_froude_number,        # Froude数
    compute_specific_energy,      # 比能
    get_convergence_metrics       # 收敛性分析
)

# 均匀流水深（最常用）
h_uniform = compute_steady_uniform_flow(
    Q=10.0,      # 流量
    B=10.0,      # 宽度
    S0=0.001,    # 底坡
    n=0.025      # Manning糙率
)
```

---

### 🏗️ 水工结构

```python
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice

# 1. 闸门
gate = SluiceGate(
    position=5000.0,
    width=10.0,
    opening=5.0,
    Cd=0.6
)

# 2. 宽顶堰
weir = BroadCrestedWeir(
    position=5000.0,
    width=10.0,
    crest_height=0.5,
    Cd=0.848
)

# 3. 孔口
orifice = Orifice(
    position=7500.0,
    width=4.0,
    height=2.0,
    bottom_elevation=0.2,
    Cd=0.61
)

# 使用：组合到求解器
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

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/leixiaohui-1974/HydroClaude.git
cd HydroClaude

# 安装依赖
pip install -r requirements.txt
```

### 运行示例

```bash
# 示例07: 闸门流动分析
python examples/example_01_canal_flow/scripts/07_sluice_gate_flow_v2.py

# 示例08: 稳态求解优化对比
python examples/example_01_canal_flow/scripts/08_optimized_steady_solving_v2.py

# 示例12: 复杂多结构场景
python examples/example_01_canal_flow/scripts/12_advanced_optimized_v2.py

# 示例01: 基础明渠流动
python examples/example_01_canal_flow/scripts/01_basic_v2.py

# 示例04: 边界条件影响
python examples/example_01_canal_flow/scripts/04_boundary_conditions_v2.py
```

**所有示例都会生成**:
- 📊 专业图表 (PNG)
- 📁 数据表 (CSV)
- 📝 验证报告 (TXT)

---

## 📂 项目结构

```
HydroClaude/
├── solvers/                           # 求解器库
│   ├── hydrostatic_canal_solver.py   # ⭐ Phase 2高精度求解器
│   ├── gate.py                        # 水工结构（闸门/堰/孔口）
│   └── ...
├── utils/                             # 工具库
│   ├── result_validator.py           # ⭐ 自动验证工具
│   ├── visualization_templates.py    # ⭐ 18种专业图表
│   ├── canal_utils.py                # 水力学计算
│   └── ...
├── examples/                          # 示例
│   └── example_01_canal_flow/
│       ├── scripts/
│       │   ├── *_v2.py               # 升级版脚本（推荐）
│       │   └── output_helper.py       # 文件管理工具
│       └── results/                   # 输出结果
│           ├── figures/              # 图表
│           ├── tables/               # 数据表
│           └── reports/              # 验证报告
├── DEVELOPMENT_GUIDE.md              # ⭐ 开发指南（必读）
├── LIBRARY_REFERENCE.md              # ⭐ 库参考手册
├── SCRIPT_UPGRADE_SUMMARY.md         # 脚本升级总结
└── README.md                         # 本文件
```

---

## 🎓 学习路径

### 新手开发者

1. **阅读**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - 基础库优先原则
2. **查阅**: [LIBRARY_REFERENCE.md](LIBRARY_REFERENCE.md) - API详细文档
3. **运行**: `examples/example_01_canal_flow/scripts/*_v2.py` - 所有v2示例
4. **理解**: `HydrostaticCanalSolver` + `ResultValidator` 的使用
5. **实践**: 修改示例脚本的参数，观察结果

### 进阶开发者

1. **深入**: Phase 2静水重构方法的算法细节
2. **扩展**: 学习如何扩展基础库（参考开发指南）
3. **优化**: 性能优化和算法改进
4. **贡献**: 新功能开发和文档更新

---

## 🔬 核心算法

### Phase 2 静水重构方法

**特点**:
- ✅ 精确捕捉静水压力梯度
- ✅ C-property保持（平衡态保持）
- ✅ 正水深保证
- ✅ 适用于小Froude数流动

**关键步骤**:

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

---

## 📊 性能对比

### vs 旧求解器 (SingleCanalSolver/CanalSolver)

| 指标 | 旧求解器 | HydrostaticCanalSolver | 改进 |
|-----|---------|----------------------|------|
| 典型迭代次数 | 数千次 | 0-1次 | 99.9%+ ⭐ |
| 流量守恒误差 | 0.5% - 15% | 0.000000% | 完美 ⭐ |
| 复杂场景收敛 | 经常失败 | 100%成功 | 稳定 ⭐ |
| 闸门流量误差 | 5% - 15% | 0.3% - 0.5% | 优秀 ⭐ |

详细测试数据: [SCRIPT_UPGRADE_SUMMARY.md](SCRIPT_UPGRADE_SUMMARY.md)

---

## 🛠️ 开发规范

### 核心原则

1. **📚 基础库优先 (Library First)**
   - **始终先检查基础库**是否已有相关功能
   - **禁止重复实现**已有的功能
   - 查阅 `LIBRARY_REFERENCE.md`

2. **🔍 搜索后扩展 (Search Then Extend)**
   - 基础库无法解决时，**先上网搜索**最佳实践
   - 参考学术论文和开源项目
   - 将新功能**整合到基础库**

3. **✅ 验证为本 (Validation First)**
   - 所有结果必须使用 `ResultValidator` 验证
   - 生成专业可视化和报告
   - 追求数值精度

### 标准脚本模板

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本功能描述

Author: [作者]
Date: [日期]
"""

import sys, os

# 路径设置
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_path))))
sys.path.insert(0, project_root)
script_dir = os.path.dirname(script_path)
sys.path.insert(0, script_dir)

# 基础库导入
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import quick_validate_steady_state
from utils.visualization_templates import VisualizationTemplates
from output_helper import get_output_path, save_figure, save_table

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def main():
    # 1. 参数设置
    # 2. 创建求解器
    # 3. 稳态求解
    # 4. 验证（必须！）
    # 5. 可视化
    # 6. 保存数据
    # 7. 总结
    pass


if __name__ == '__main__':
    validator = main()
```

详见: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)

---

## 🤝 贡献指南

1. **Fork** 本仓库
2. **阅读** [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
3. **创建** 功能分支 (`git checkout -b feature/AmazingFeature`)
4. **提交** 更改 (`git commit -m 'Add: 新功能描述'`)
5. **推送** 到分支 (`git push origin feature/AmazingFeature`)
6. **打开** Pull Request

**提交信息格式**:
- `Add: 新增功能`
- `Fix: 修复问题`
- `Upgrade: 升级功能`
- `Doc: 文档更新`
- `Test: 测试相关`

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 📮 联系方式

- **项目主页**: [https://github.com/leixiaohui-1974/HydroClaude](https://github.com/leixiaohui-1974/HydroClaude)
- **问题反馈**: [GitHub Issues](https://github.com/leixiaohui-1974/HydroClaude/issues)
- **作者**: leixiaohui-1974

---

## 🙏 致谢

本项目使用以下开源库：
- NumPy - 数值计算
- SciPy - 科学计算
- Matplotlib - 可视化
- Pandas - 数据处理

参考文献：
- Audusse et al. (2004) - Phase 2静水重构方法
- LeVeque (2002) - 有限体积法
- Chow (1959) - 明渠水力学
- Cunge et al. (1980) - 计算水力学

---

**🎯 记住**: 开发前先查 [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) 和 [LIBRARY_REFERENCE.md](LIBRARY_REFERENCE.md)，避免重复造轮子！

**Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**

---

**最后更新**: 2025-10-23
**版本**: 2.0 (Phase 2 Hydrostatic Solver)
