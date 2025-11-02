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

### 5. `performance_profiler.py` - 性能分析工具

对模拟性能进行全面分析，识别性能瓶颈并提供优化建议。

**用法:**

**基本性能分析:**
```bash
python tools/performance_profiler.py
```

**完整性能分析（包括所有测试）:**
```bash
python tools/performance_profiler.py --full
```

**分析内容:**

1. **网格规模基准测试**
   - 测试不同网格尺寸（50, 100, 200, 500 cells）
   - 计算每步耗时
   - 分析规模扩展性

2. **Numba 加速效果**
   - 对比启用/禁用 Numba 的性能
   - 计算加速比
   - 评估编译开销

3. **模块级性能分析**
   - 识别计算瓶颈
   - 分析各模块耗时占比
   - 提供优化建议

**输出示例:**
```
======================================================================
网格规模基准测试
======================================================================
规模                  网格数      每步耗时        加速比
----------------------------------------------------------
小规模 (50网格)         50       2.12  ms    1694343.1x
中规模 (100网格)        100      3.81  ms    944354.7x
大规模 (200网格)        200      7.29  ms    493677.9x
超大规模 (500网格)      500      17.84 ms    201750.8x

✓ 结论: 性能随网格数近似线性扩展
```

**性能建议:**
- 小规模模拟 (< 100 cells): 不需要 Numba
- 中规模模拟 (100-500 cells): 建议启用 Numba
- 大规模模拟 (> 500 cells): 必须启用 Numba

---

### 6. `batch_runner.py` - 批量场景分析工具

自动运行多个模拟场景，支持参数采样、并行执行和敏感性分析。

**用法:**

**网格采样（推荐用于少量参数）:**
```python
from tools.batch_runner import BatchRunner, create_default_model_function

# 定义参数范围
param_ranges = {
    'kd_20': (0.10, 0.30),
    'SOD_20': (0.5, 2.0)
}

# 创建批量运行器
runner = BatchRunner(
    model_function=create_default_model_function(),
    param_ranges=param_ranges
)

# 生成网格采样场景
scenarios = runner.generate_grid_samples(
    param_ranges,
    resolution_per_param=3  # 每个参数3个值 → 总共3×3=9个场景
)

# 运行所有场景
results = runner.run_batch(scenarios)

# 分析结果
sensitivity = runner.analyze_sensitivity(results)
```

**拉丁超立方采样（推荐用于多参数）:**
```python
# 需要安装 scipy
# pip install scipy

# 生成 LHS 采样场景
scenarios = runner.generate_lhs_samples(param_ranges, n_samples=50)
results = runner.run_batch(scenarios)
```

**蒙特卡洛采样（用于不确定性分析）:**
```python
# 生成蒙特卡洛采样场景
scenarios = runner.generate_monte_carlo_samples(param_ranges, n_samples=100)
results = runner.run_batch(scenarios)
```

**并行执行（加速大批量任务）:**
```python
# 使用4个进程并行运行
results = runner.run_batch(scenarios, n_workers=4)
```

**功能特点:**

1. **多种采样方法**
   - 网格采样: 系统探索参数空间
   - 拉丁超立方 (LHS): 高效覆盖高维参数空间
   - 蒙特卡洛: 不确定性量化

2. **自动敏感性分析**
   - 参数-输出相关性分析
   - 参数变化范围统计
   - 敏感性指数计算

3. **并行执行支持**
   - 多进程并行
   - 自动负载均衡
   - 进度实时显示

4. **结果可视化**
   - 参数散点图
   - 敏感性热图
   - 统计分布图

**输出:**
- `batch_results.json`: 所有场景结果
- `batch_sensitivity.png`: 敏感性分析图
- `batch_scatter.png`: 参数-输出散点图

---

### 7. `calibration.py` - 参数校准工具

使用观测数据自动校准模型参数，支持多种优化算法和不确定性分析。

**用法:**

**完整校准工作流示例:**
```python
from tools.calibration import ParameterCalibrator
import numpy as np

# 1. 准备观测数据
observed_data = {
    'DO': np.array([8.5, 8.2, 7.9, 7.8, 7.7, 7.6, 7.5]),  # 7天DO观测
    'BOD': np.array([5.0, 4.2, 3.5, 3.0, 2.6, 2.3, 2.0])  # 7天BOD观测
}

# 2. 定义模型函数
def my_model(params):
    """运行模型并返回模拟结果"""
    # 使用 params['kd_20'], params['SOD_20'] 等参数运行模型
    # 返回字典: {'DO': array, 'BOD': array}
    ...
    return {'DO': sim_DO, 'BOD': sim_BOD}

# 3. 定义参数范围
param_ranges = {
    'kd_20': (0.05, 0.50),   # BOD降解系数范围
    'SOD_20': (0.5, 3.0)     # 底泥耗氧范围
}

# 4. 创建校准器
calibrator = ParameterCalibrator(
    model_function=my_model,
    observed_data=observed_data,
    param_ranges=param_ranges,
    objective_function='RMSE'  # 可选: 'RMSE', 'NSE', 'MAE', 'PBIAS'
)

# 5. 运行校准
results = calibrator.calibrate_nelder_mead(max_iter=200)
# 或使用全局优化: results = calibrator.calibrate_differential_evolution()

# 6. 不确定性分析
uncertainty = calibrator.analyze_uncertainty(
    results['optimal_params'],
    n_samples=100
)

# 7. 保存结果
calibrator.save_results(results, uncertainty, 'calibration_results.json')
calibrator.plot_convergence('convergence.png')
calibrator.plot_parameter_uncertainty(uncertainty, 'uncertainty.png')
```

**支持的优化算法:**

1. **Nelder-Mead (局部优化)**
   - 适合: 参数较少（2-5个）、有合理初值
   - 优点: 收敛快，计算量小
   - 缺点: 可能陷入局部最优

2. **Differential Evolution (全局优化)**
   - 适合: 参数较多（> 5个）、无初值
   - 优点: 全局搜索，鲁棒性强
   - 缺点: 计算量大

**支持的目标函数:**

- **RMSE (均方根误差)**: 通用指标，单位与变量相同
- **NSE (Nash-Sutcliffe 效率)**: 水文常用，范围 [-∞, 1]，越大越好
- **MAE (平均绝对误差)**: 对异常值不敏感
- **PBIAS (百分比偏差)**: 评估系统性偏差

**输出:**

**校准结果 JSON:**
```json
{
  "calibration_info": {
    "objective_function": "RMSE",
    "observed_variables": ["DO", "BOD"]
  },
  "calibration_results": {
    "optimal_params": {
      "kd_20": 0.199347,
      "SOD_20": 1.402184
    },
    "objective_value": 0.144712,
    "n_iterations": 37,
    "n_evaluations": 73,
    "success": true
  },
  "uncertainty_analysis": {
    "parameter_stats": {
      "kd_20": {
        "optimal": 0.199347,
        "mean": 0.194515,
        "std": 0.038719,
        "ci_lower": 0.116572,
        "ci_upper": 0.280705
      }
    }
  }
}
```

**不确定性分析:**
- 参数统计: 均值、标准差、95% 置信区间
- 目标函数不确定性
- 参数相关性分析

**完整示例:**
```bash
# 运行内置示例（合成数据）
python tools/calibration.py

# 运行真实DO求解器校准示例
python examples/calibration_example.py
```

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

# 2. 准备观测数据（CSV 或 NPZ 格式）
# observation_data.csv:
#   time, DO, BOD, Chla, ...

# 3. 运行参数校准
python examples/calibration_example.py

# 4. 查看校准结果
cat do_calibration_results.json

# 5. 使用校准后的参数运行最终模拟
# 更新 config 文件中的参数为校准值
python tools/run_from_config.py config/my_simulation.json
```

### 批量场景分析工作流:

```bash
# 1. 运行批量场景分析（Python脚本）
python -c "
from tools.batch_runner import BatchRunner, create_default_model_function

param_ranges = {
    'kd_20': (0.10, 0.30),
    'SOD_20': (0.5, 2.0),
    'mu_max_20': (1.0, 3.0)
}

runner = BatchRunner(
    model_function=create_default_model_function(),
    param_ranges=param_ranges
)

# 生成 LHS 采样
scenarios = runner.generate_lhs_samples(param_ranges, n_samples=50)

# 并行运行
results = runner.run_batch(scenarios, n_workers=4)

# 敏感性分析
sensitivity = runner.analyze_sensitivity(results)
runner.save_results(results, 'batch_results.json')
"

# 2. 查看结果
cat batch_results.json

# 3. 导出所有场景的可视化
python tools/visualize_results.py batch_results.json --plot-type all
```

### 性能优化工作流:

```bash
# 1. 运行性能分析
python tools/performance_profiler.py --full

# 2. 根据建议启用 Numba（如果网格 > 100）
# 修改配置文件:
#   "solver_parameters": {
#     "temperature": {"use_numba": true},
#     "dissolved_oxygen": {"use_numba": true}
#   }

# 3. 重新测试性能
python tools/performance_profiler.py

# 4. 运行大规模模拟
python tools/run_from_config.py config/large_scale_simulation.json
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
