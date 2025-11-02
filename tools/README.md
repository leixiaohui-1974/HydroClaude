# HydroClaude 工具集

本目录包含 HydroClaude 的辅助工具，用于配置驱动模拟、参数敏感性分析和数据导出。

## 工具列表

### 1. `run_from_config.py` - 配置驱动模拟

从 JSON 配置文件运行 HydroClaude 模拟，无需编写 Python 代码。

**用法:**
```bash
python tools/run_from_config.py config/example_winter_simulation.json
```

**配置文件示例:**
```json
{
  "simulation_name": "Winter River Simulation",
  "domain": {
    "length": 10000.0,
    "n_cells": 100,
    "dx": 100.0
  },
  "hydraulics": {
    "velocity": 0.3,
    "depth": 2.5,
    "manning_n": 0.03
  },
  "simulation_time": {
    "duration_days": 30,
    "time_step_seconds": 3600
  },
  "meteorology": {
    "air_temperature_initial": 0.0,
    "air_temperature_final": -15.0,
    "solar_radiation": 100.0,
    "wind_speed": 5.0,
    "relative_humidity": 0.7
  },
  "initial_conditions": {
    "water_temperature": 2.0,
    "dissolved_oxygen": 12.0,
    "ice_thickness": 0.0,
    "NH4": 0.3,
    "NO3": 1.2,
    "PO4": 0.08,
    "chlorophyll_a": 12.0
  },
  "solver_parameters": {
    "temperature": {"use_numba": false},
    "dissolved_oxygen": {"kd_20": 0.15, "SOD_20": 1.0},
    "nutrients": {"use_numba": false},
    "phytoplankton": {"use_numba": false}
  },
  "output": {
    "directory": "outputs",
    "filename": "simulation_results.npz",
    "save_format": "npz",
    "create_plots": true
  }
}
```

**输出:**
- NPZ 格式的模拟结果
- 自动生成的可视化图表（如果 `create_plots: true`）

---

### 2. `sensitivity_analysis.py` - 参数敏感性分析

量化关键参数对模拟结果的影响，为参数校准和不确定性分析提供依据。

**用法:**
```bash
python tools/sensitivity_analysis.py
```

**分析内容:**

1. **BOD 降解系数 (kd_20) 敏感性**
   - 范围: 0.05 - 0.40 1/day
   - 影响: 溶解氧浓度
   - 灵敏度: 中等

2. **藻类最大增长率 (mu_max_20) 敏感性**
   - 范围: 0.5 - 4.0 1/day
   - 影响: 叶绿素 a 浓度
   - 灵敏度: 高（指数增长）

3. **光照强度 (I_0) 敏感性**
   - 范围: 10 - 400 W/m²
   - 影响: 藻类生长
   - 灵敏度: 非线性（Steele 公式）

**输出:**
- `outputs/sensitivity_analysis_*.png`: 可视化图表
- 控制台输出: 定量敏感性指标

**解释:**
- **敏感性指数 > 1**: 高度敏感，需要精确校准
- **敏感性指数 0.1-1**: 中等敏感，需要合理估计
- **敏感性指数 < 0.1**: 低敏感，可以使用文献值

---

### 3. `export_data.py` - 数据导出工具

将 NPZ 格式的模拟结果导出为多种易用格式。

**用法:**

**导出为 CSV（时间序列）:**
```bash
python tools/export_data.py outputs/simulation_results.npz --format csv
```

**导出为 JSON（元数据 + 统计摘要）:**
```bash
python tools/export_data.py outputs/simulation_results.npz --format json
```

**导出空间分布数据:**
```bash
python tools/export_data.py outputs/simulation_results.npz --format spatial --time-index -1
```

**导出所有格式:**
```bash
python tools/export_data.py outputs/simulation_results.npz --format all
```

**高级选项:**

```bash
# 导出特定变量
python tools/export_data.py outputs/simulation_results.npz --format csv \
    --variables water_temperature dissolved_oxygen ice_thickness

# JSON 包含完整数组数据（大文件警告）
python tools/export_data.py outputs/simulation_results.npz --format json \
    --include-arrays

# 指定输出文件路径
python tools/export_data.py outputs/simulation_results.npz --format csv \
    --output my_results.csv
```

**输出格式:**

**CSV 格式:**
```csv
Time (days),water_temperature,dissolved_oxygen,ice_thickness,chlorophyll_a
0.0000,2.000000,12.000000,0.000000,12.000000
0.9583,2.151292,12.246782,0.000000,11.029820
1.9583,2.175752,12.423165,0.000000,10.137017
...
```

**JSON 格式:**
```json
{
  "metadata": {
    "source_file": "outputs/simulation_results.npz",
    "export_time": "2025-11-02T09:37:45.181411",
    "variables": ["water_temperature", "dissolved_oxygen", ...],
    "n_time_points": 31
  },
  "summary": {
    "time_range": {
      "start": 0.0,
      "end": 29.96,
      "duration_days": 29.96
    },
    "water_temperature": {
      "mean": 0.609,
      "min": 0.0,
      "max": 2.176,
      "std": 0.828,
      "initial": 2.0,
      "final": 0.0
    },
    ...
  }
}
```

---

### 4. `visualize_results.py` - 结果可视化工具

为模拟结果生成专业级可视化图表，支持多种图表类型和自定义样式。

**用法:**

**生成所有图表:**
```bash
python tools/visualize_results.py outputs/simulation_results.npz --plot-type all
```

**仅生成时间序列图:**
```bash
python tools/visualize_results.py outputs/simulation_results.npz --plot-type timeseries
```

**生成综合仪表板:**
```bash
python tools/visualize_results.py outputs/simulation_results.npz --plot-type dashboard
```

**生成空间分布图（需要2D数据）:**
```bash
python tools/visualize_results.py outputs/simulation_results.npz --plot-type spatial --time-index -1
```

**高级选项:**

```bash
# 自定义输出目录
python tools/visualize_results.py outputs/simulation_results.npz \
    --plot-type all --output-dir my_figures/

# 仅绘制特定变量
python tools/visualize_results.py outputs/simulation_results.npz \
    --plot-type timeseries --variables water_temperature dissolved_oxygen ice_thickness

# 使用不同的绘图风格
python tools/visualize_results.py outputs/simulation_results.npz \
    --plot-type all --style ggplot
```

**可用图表类型:**

1. **时间序列图 (timeseries)**
   - 所有变量的时间演化
   - 多面板布局
   - 自动颜色编码

2. **综合仪表板 (dashboard)**
   - 6面板综合视图
   - 水温和冰盖动态（双Y轴）
   - 溶解氧变化（含低氧阈值线）
   - 营养盐动态（NH₄⁺, NO₃⁻, PO₄³⁻）
   - 叶绿素 a 面积图
   - 统计摘要表
   - 相关性矩阵热图

3. **空间分布图 (spatial)**
   - 沿河道的空间分布
   - 指定时间截面
   - 面积填充样式

**输出:**
- PNG 格式图片（300 DPI，适合出版）
- 默认保存在 `outputs/figures/` 目录
- 文件名: `timeseries.png`, `dashboard.png`, `spatial_t{index}.png`

**支持的Matplotlib样式:**
- `seaborn-v0_8-darkgrid` (默认)
- `ggplot`
- `bmh`
- `fivethirtyeight`
- 其他内置 matplotlib 样式

---

## 工作流示例

### 典型模拟工作流:

```bash
# 1. 创建配置文件
cp config/example_winter_simulation.json config/my_simulation.json
# 编辑 config/my_simulation.json 设置参数

# 2. 运行模拟
python tools/run_from_config.py config/my_simulation.json

# 3. 可视化结果
python tools/visualize_results.py outputs/simulation_results.npz --plot-type all

# 4. 导出结果为CSV/JSON
python tools/export_data.py outputs/simulation_results.npz --format all

# 5. 参数敏感性分析（可选）
python tools/sensitivity_analysis.py
```

### 参数校准工作流:

```bash
# 1. 运行敏感性分析，识别关键参数
python tools/sensitivity_analysis.py

# 2. 调整配置文件中的关键参数
nano config/my_simulation.json

# 3. 运行多个场景
for temp in -5 -10 -15; do
  # 修改配置文件中的气温
  sed -i "s/\"air_temperature_final\": .*/\"air_temperature_final\": $temp,/" config/my_simulation.json
  python tools/run_from_config.py config/my_simulation.json
  mv outputs/simulation_results.npz outputs/results_T${temp}.npz
done

# 4. 导出所有结果进行比较
for file in outputs/results_*.npz; do
  python tools/export_data.py $file --format csv
done
```

---

## 要求

- Python 3.7+
- NumPy
- Matplotlib
- HydroClaude 主模块（solvers/）

---

## 支持

如有问题或建议，请提交 GitHub Issue 或联系 HydroClaude 团队。

**文档:** 参见 `docs/` 目录获取更多详细信息
**示例:** 参见 `examples/` 目录获取应用案例
**配置:** 参见 `config/` 目录获取配置文件示例
