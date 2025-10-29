# HydroClaude 配置文件规范 v1.0

## 设计目标

打造商业级一维水力学模型引擎的配置文件系统，参考：
- HEC-RAS: 文本配置文件
- MIKE 11: .m11 文件
- InfoWorks ICM: 数据库驱动

## 配置文件结构（JSON格式）

```json
{
  "project": {
    "name": "河道溃坝模拟",
    "description": "基于Godunov方法的溃坝波传播",
    "author": "HydroClaude User",
    "created": "2025-10-28",
    "version": "1.0"
  },

  "geometry": {
    "type": "uniform",  // uniform | variable | from_file
    "channel_width": 10.0,
    "channel_length": 2000.0,
    "bottom_slope": 0.0,  // 可以是数值或数组
    "manning_n": 0.025,
    "cross_sections": null  // 真实断面数据路径
  },

  "mesh": {
    "n_cells": 200,
    "cell_distribution": "uniform",  // uniform | adaptive
    "refinement_regions": []
  },

  "solver": {
    "type": "godunov_fvm",
    "spatial_order": 2,
    "time_integration": "tvd_rk2",
    "riemann_solver": "hll",  // hll | hllc
    "use_numba": true,
    "well_balanced": false,
    "cfl": 0.5,
    "eps_dry": 1e-6
  },

  "initial_conditions": {
    "type": "dam_break",  // dam_break | uniform | from_file | expression
    "h_left": 10.0,
    "h_right": 1.0,
    "Q_initial": 0.0,
    "dam_position": 1000.0,
    "expression": null  // 可选：Python表达式
  },

  "boundary_conditions": {
    "left": {
      "type": "h",  // h | Q | rating_curve | hydrograph
      "value": 10.0,
      "time_series": null
    },
    "right": {
      "type": "h",
      "value": 1.0,
      "time_series": null
    }
  },

  "simulation": {
    "start_time": 0.0,
    "end_time": 30.0,
    "max_steps": 1000000,
    "output_interval": 1.0,  // 输出间隔（秒）
    "checkpoint_interval": 10.0
  },

  "output": {
    "directory": "./results",
    "formats": ["csv", "hdf5"],  // csv | hdf5 | netcdf | vtk
    "variables": ["h", "Q", "u", "Fr"],
    "statistics": true,  // 输出统计信息
    "plots": {
      "enabled": true,
      "format": "png",
      "dpi": 300
    }
  },

  "validation": {
    "enabled": true,
    "analytical_solution": "ritter",  // ritter | uniform_flow | backwater
    "tolerance": {
      "h_rmse": 0.5,
      "Q_rmse": 10.0,
      "mass_error": 0.1
    }
  },

  "logging": {
    "level": "INFO",  // DEBUG | INFO | WARNING | ERROR
    "file": "./logs/simulation.log",
    "console": true
  }
}
```

## 配置文件示例

### 1. 溃坝模拟

```json
{
  "project": {
    "name": "标准溃坝测试",
    "description": "与Ritter解析解对比"
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
    "spatial_order": 2,
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
    "output_interval": 1.0
  },
  "output": {
    "directory": "./results/dam_break",
    "formats": ["csv", "hdf5"]
  },
  "validation": {
    "enabled": true,
    "analytical_solution": "ritter"
  }
}
```

### 2. 真实河道模拟

```json
{
  "project": {
    "name": "长江某段洪水演进",
    "description": "基于实测断面数据"
  },
  "geometry": {
    "type": "from_file",
    "cross_sections": "./data/river_cross_sections.csv",
    "manning_n": 0.030
  },
  "mesh": {
    "n_cells": 500,
    "cell_distribution": "adaptive"
  },
  "solver": {
    "type": "godunov_fvm",
    "riemann_solver": "hll",
    "use_numba": true
  },
  "initial_conditions": {
    "type": "from_file",
    "file": "./data/initial_state.csv"
  },
  "boundary_conditions": {
    "left": {
      "type": "hydrograph",
      "time_series": "./data/upstream_flow.csv"
    },
    "right": {
      "type": "rating_curve",
      "file": "./data/downstream_rating.csv"
    }
  },
  "simulation": {
    "end_time": 86400.0,
    "output_interval": 3600.0
  },
  "output": {
    "directory": "./results/river_flood",
    "formats": ["hdf5", "netcdf"]
  }
}
```

### 3. 均匀流验证

```json
{
  "project": {
    "name": "均匀流验证",
    "description": "验证Manning公式"
  },
  "geometry": {
    "type": "uniform",
    "channel_width": 10.0,
    "channel_length": 1000.0,
    "bottom_slope": 0.001,
    "manning_n": 0.025
  },
  "mesh": {
    "n_cells": 100
  },
  "solver": {
    "type": "godunov_fvm",
    "use_numba": true
  },
  "initial_conditions": {
    "type": "uniform",
    "h": 2.0,
    "Q": 20.0
  },
  "boundary_conditions": {
    "left": {"type": "Q", "value": 20.0},
    "right": {"type": "h", "value": 2.0}
  },
  "simulation": {
    "end_time": 1000.0,
    "output_interval": 100.0
  },
  "validation": {
    "enabled": true,
    "analytical_solution": "uniform_flow"
  }
}
```

## 配置文件验证规则

### 必需字段
- `project.name`
- `geometry.type`
- `mesh.n_cells`
- `solver.type`
- `initial_conditions.type`
- `boundary_conditions.left`
- `boundary_conditions.right`
- `simulation.end_time`

### 数据类型检查
- 数值字段：必须为正数
- 字符串字段：从允许列表选择
- 路径字段：文件必须存在
- 时间序列：格式正确

### 一致性检查
- CFL < 1.0
- end_time > start_time
- output_interval < end_time
- n_cells > 0

## 扩展性设计

### 插件式求解器
```json
{
  "solver": {
    "type": "godunov_fvm",  // 可扩展：finite_element, finite_difference
    "options": {
      // 求解器特定参数
    }
  }
}
```

### 多段河道
```json
{
  "geometry": {
    "type": "multi_reach",
    "reaches": [
      {
        "name": "上游段",
        "length": 1000.0,
        "width": 10.0
      },
      {
        "name": "下游段",
        "length": 2000.0,
        "width": 15.0
      }
    ]
  }
}
```

### 结构物
```json
{
  "structures": [
    {
      "type": "weir",
      "position": 1500.0,
      "crest_elevation": 5.0,
      "discharge_coefficient": 0.6
    },
    {
      "type": "gate",
      "position": 2500.0,
      "opening": "time_series.csv"
    }
  ]
}
```

## 实现计划

### Phase 1: 基础配置系统
- ConfigParser类
- 基本验证
- dam_break案例

### Phase 2: 高级特性
- 时间序列支持
- 多种输出格式
- 真实断面

### Phase 3: 商业化
- 结构物
- 多段河道
- 参数优化

## 参考标准

- JSON Schema 2020-12
- CF Conventions (气候预报约定)
- HEC-RAS数据标准
- OpenFOAM配置文件风格

---

**状态**: Draft v1.0
**作者**: HydroClaude Team
**日期**: 2025-10-28
