# 配置驱动仿真系统

HydroClaude的配置驱动仿真系统，让您通过JSON配置文件运行水力学仿真，无需编写Python代码。

## 核心优势

✅ **无需编程** - 通过JSON配置文件定义仿真
✅ **标准化** - 统一的配置格式
✅ **自动化** - 自动生成结果、图表和报告
✅ **可复现** - 配置文件即仿真定义

## 快速开始

### 1. 运行溃坝模拟

```bash
python simulate.py examples/config_driven/dam_break.json
```

**结果**：
- `results/dam_break/csv/` - CSV数据
- `results/dam_break/plots/` - 图表
- `results/dam_break/statistics.json` - 统计信息

### 2. 运行均匀流验证

```bash
python simulate.py examples/config_driven/uniform_flow.json
```

## 配置文件结构

### 完整示例 (溃坝模拟)

```json
{
  "project": {
    "name": "标准溃坝测试",
    "description": "Godunov-FVM求解器 + Ritter解析解"
  },

  "geometry": {
    "type": "uniform",
    "channel_width": 10.0,
    "channel_length": 2000.0,
    "bottom_slope": 0.0,
    "manning_n": 0.0
  },

  "mesh": {
    "n_cells": 400
  },

  "solver": {
    "type": "godunov_fvm",
    "riemann_solver": "hll",
    "use_numba": true,
    "cfl": 0.5
  },

  "initial_conditions": {
    "type": "dam_break",
    "h_left": 10.0,
    "h_right": 1.0,
    "dam_position": 1000.0
  },

  "boundary_conditions": {
    "left": {"type": "h", "value": 10.0},
    "right": {"type": "h", "value": 1.0}
  },

  "simulation": {
    "end_time": 30.0,
    "output_interval": 5.0
  },

  "output": {
    "directory": "./results/dam_break",
    "formats": ["csv", "hdf5"],
    "plots": {"enabled": true}
  },

  "validation": {
    "enabled": true,
    "analytical_solution": "ritter"
  }
}
```

## 配置文件详解

### Project - 项目信息
```json
{
  "project": {
    "name": "项目名称",
    "description": "项目描述",
    "author": "作者",
    "created": "日期"
  }
}
```

### Geometry - 几何参数
```json
{
  "geometry": {
    "type": "uniform",              // uniform | variable | from_file
    "channel_width": 10.0,          // 渠宽 (m)
    "channel_length": 2000.0,       // 渠长 (m)
    "bottom_slope": 0.0,            // 底坡（标量或数组）
    "manning_n": 0.025              // Manning糙率系数
  }
}
```

### Mesh - 网格
```json
{
  "mesh": {
    "n_cells": 400,                 // 网格数（越多越精确）
    "cell_distribution": "uniform"  // uniform | adaptive
  }
}
```

### Solver - 求解器
```json
{
  "solver": {
    "type": "godunov_fvm",         // 求解器类型
    "spatial_order": 2,            // 空间精度 (1或2)
    "riemann_solver": "hll",       // hll | hllc
    "use_numba": true,             // 是否使用Numba加速 (推荐true)
    "well_balanced": false,        // 是否使用well-balanced格式
    "cfl": 0.5,                    // CFL数 (0-1)
    "eps_dry": 1e-6                // 干床阈值
  }
}
```

### Initial Conditions - 初始条件
```json
{
  "initial_conditions": {
    "type": "dam_break",           // dam_break | uniform | from_file | expression
    "h_left": 10.0,                // 左侧水深 (溃坝)
    "h_right": 1.0,                // 右侧水深 (溃坝)
    "dam_position": 1000.0         // 坝址位置 (m)
  }
}
```

或均匀流：
```json
{
  "initial_conditions": {
    "type": "uniform",
    "h": 2.0,                      // 均匀水深 (m)
    "Q": 20.0                      // 均匀流量 (m³/s)
  }
}
```

### Boundary Conditions - 边界条件
```json
{
  "boundary_conditions": {
    "left": {
      "type": "h",                 // h | Q
      "value": 10.0                // 水深或流量
    },
    "right": {
      "type": "h",
      "value": 1.0
    }
  }
}
```

### Simulation - 仿真参数
```json
{
  "simulation": {
    "start_time": 0.0,             // 开始时间 (s)
    "end_time": 30.0,              // 结束时间 (s)
    "max_steps": 1000000,          // 最大步数
    "output_interval": 5.0         // 输出间隔 (s)
  }
}
```

### Output - 输出设置
```json
{
  "output": {
    "directory": "./results",      // 输出目录
    "formats": ["csv", "hdf5"],    // csv | hdf5 | netcdf
    "variables": ["h", "Q", "u"],  // 输出变量
    "statistics": true,            // 是否输出统计信息
    "plots": {
      "enabled": true,             // 是否生成图表
      "format": "png",             // png | pdf
      "dpi": 300                   // 分辨率
    }
  }
}
```

### Validation - 验证设置
```json
{
  "validation": {
    "enabled": true,               // 是否启用验证
    "analytical_solution": "ritter", // ritter | uniform_flow
    "tolerance": {
      "h_rmse": 0.5,               // 水深RMSE容差 (m)
      "Q_rmse": 10.0,              // 流量RMSE容差 (m³/s)
      "mass_error": 0.1            // 质量误差容差 (%)
    }
  }
}
```

## 支持的功能

### 初始条件类型
- ✅ `dam_break` - 溃坝（左右不同水深）
- ✅ `uniform` - 均匀流（恒定水深和流量）
- ⏳ `from_file` - 从CSV文件读取（待实现）
- ⏳ `expression` - Python表达式（待实现）

### 求解器类型
- ✅ `godunov_fvm` - Godunov有限体积法
  - HLL Riemann求解器
  - HLLC Riemann求解器
  - 二阶MUSCL重构
  - Numba JIT加速（68x速度提升）

### 验证解析解
- ✅ `ritter` - Ritter溃坝解析解
- ✅ `uniform_flow` - Manning均匀流公式
- ⏳ `hydraulic_jump` - 水跃解析解（待实现）

### 输出格式
- ✅ `csv` - CSV表格（易于Excel处理）
- ✅ `hdf5` - HDF5科学数据格式（需要h5py）
- ⏳ `netcdf` - NetCDF格式（待实现）

## 输出文件结构

```
results/
├── csv/
│   ├── final_state.csv          # 最终状态
│   └── timeseries_x*.csv        # 关键位置时间序列
├── plots/
│   ├── final_state.png          # 最终状态图
│   ├── spacetime_evolution.png  # 时空演化图
│   └── validation_comparison.png # 验证对比图（如果启用）
├── results.h5                   # HDF5完整数据
└── statistics.json              # 统计信息
```

## 性能优化

### Numba加速
```json
{
  "solver": {
    "use_numba": true              // 启用Numba (推荐)
  }
}
```

**性能提升**：
- Numba ON: ~68x 速度提升
- Numba OFF: 纯Python模式（慢）

### 网格数选择
- 粗网格（<100）：快速测试
- 中等网格（100-200）：标准模拟
- 精细网格（400+）：高精度验证

### CFL数设置
- CFL=0.5：推荐值（稳定）
- CFL=0.8：更快（可能不稳定）
- CFL=0.3：保守（最稳定）

## 常见问题

### Q: 仿真卡住不动？
A: 可能是CFL瓶颈，尝试：
- 减少网格数
- 增加干床阈值 `eps_dry`
- 检查初始条件是否合理

### Q: 质量守恒误差大？
A: 检查：
- 边界条件是否正确
- 网格是否足够精细
- 时间步长是否过大

### Q: HDF5文件无法生成？
A: 安装h5py：
```bash
pip install h5py
```

## 扩展配置文件

### 自定义底坡（变化坡度）
```json
{
  "geometry": {
    "bottom_slope": [0.001, 0.002, 0.0015, ...]  // 每个单元的坡度
  }
}
```

### 从文件读取初始条件
```json
{
  "initial_conditions": {
    "type": "from_file",
    "file": "./data/initial_state.csv"
  }
}
```

CSV格式：
```csv
x,h,Q
0,2.0,10.0
10,2.1,10.5
...
```

## 完整配置文件规范

详见：[docs/CONFIG_SPECIFICATION.md](../../docs/CONFIG_SPECIFICATION.md)

## 相关文档

- 📚 [配置文件规范](../../docs/CONFIG_SPECIFICATION.md) - 完整的配置文件定义
- 🔧 [ConfigParser文档](../../engine/config_parser.py) - 配置解析器API
- 🚀 [SimulationEngine文档](../../engine/simulation_engine.py) - 仿真引擎API

## 技术支持

- GitHub Issues: [https://github.com/leixiaohui-1974/HydroClaude/issues](https://github.com/leixiaohui-1974/HydroClaude/issues)
- 示例代码：`examples/config_driven/`
- 文档：`docs/`

---

**HydroClaude Team - 2025-10-28**
