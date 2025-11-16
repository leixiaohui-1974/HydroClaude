# HydroClaude 统一架构设计方案
# Unified Architecture Design for Commercial-Grade Backend

**版本**: 1.0  
**设计日期**: 2025-11-15  
**设计目标**: 将示例脚本集合转型为商业级软件产品

---

## 🎯 设计目标

### 核心原则
1. **单一程序入口** - 一个主程序处理所有计算场景
2. **配置驱动** - 通过JSON/YAML配置文件描述问题
3. **标准化输入/输出** - 统一的文件格式
4. **可扩展性** - 易于添加新功能
5. **商业软件级** - 对标HEC-RAS、MIKE系列

---

## 📐 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│  - 配置文件 (JSON)                                           │
│  - 命令行接口 (CLI)                                          │
│  - (未来) Web API                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    主程序入口                                │
│                  hydro_engine.py                             │
│  - 统一的程序入口点                                          │
│  - 参数验证                                                  │
│  - 任务调度                                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    核心引擎层                                │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ConfigParser │  │ SimulationEngine │ │ OutputManager│      │
│  │              │→│              │→│              │      │
│  │ 配置解析     │  │ 仿真引擎     │  │ 结果输出     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    求解器层                                  │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Hydrostatic      │  │ Godunov FVM      │                │
│  │ Canal Solver     │  │ Solver           │                │
│  │ (稳态)           │  │ (非恒定流)        │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    基础库层                                  │
│                                                              │
│  - canal_utils (水力学计算)                                  │
│  - gate (水工结构)                                           │
│  - result_validator (结果验证)                               │
│  - plot_helper (可视化)                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 输入配置文件格式

### 标准 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HydroClaude Simulation Configuration",
  "type": "object",
  "required": ["simulation", "canal", "solver"],
  
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "author": {"type": "string"},
        "date": {"type": "string", "format": "date"},
        "version": {"type": "string"}
      }
    },
    
    "simulation": {
      "type": "object",
      "required": ["type", "mode"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["steady", "unsteady"],
          "description": "仿真类型"
        },
        "mode": {
          "type": "string",
          "enum": ["single_canal", "network", "coupled"],
          "description": "仿真模式"
        },
        "time": {
          "type": "object",
          "properties": {
            "start": {"type": "number"},
            "end": {"type": "number"},
            "dt": {"type": "number"},
            "output_interval": {"type": "number"}
          }
        }
      }
    },
    
    "canal": {
      "type": "object",
      "required": ["length", "width", "slope", "manning_n"],
      "properties": {
        "length": {"type": "number", "minimum": 0},
        "width": {"type": "number", "minimum": 0},
        "slope": {
          "oneOf": [
            {"type": "number"},
            {"type": "array", "items": {"type": "number"}}
          ]
        },
        "manning_n": {"type": "number", "minimum": 0},
        "grid": {
          "type": "object",
          "properties": {
            "nx": {"type": "integer", "minimum": 3},
            "type": {
              "type": "string",
              "enum": ["uniform", "custom"]
            },
            "x_positions": {
              "type": "array",
              "items": {"type": "number"}
            }
          }
        }
      }
    },
    
    "structures": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "position"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["sluice_gate", "weir", "orifice", "pump"]
          },
          "name": {"type": "string"},
          "position": {"type": "number"},
          "parameters": {"type": "object"}
        }
      }
    },
    
    "boundary_conditions": {
      "type": "object",
      "properties": {
        "upstream": {
          "type": "object",
          "required": ["type", "value"],
          "properties": {
            "type": {
              "type": "string",
              "enum": ["flow", "depth", "rating_curve", "time_series"]
            },
            "value": {
              "oneOf": [
                {"type": "number"},
                {"type": "array"},
                {"type": "string"}
              ]
            }
          }
        },
        "downstream": {
          "type": "object",
          "required": ["type", "value"],
          "properties": {
            "type": {
              "type": "string",
              "enum": ["depth", "rating_curve", "normal_depth", "critical_depth"]
            },
            "value": {
              "oneOf": [
                {"type": "number"},
                {"type": "array"},
                {"type": "string"}
              ]
            }
          }
        }
      }
    },
    
    "solver": {
      "type": "object",
      "required": ["method"],
      "properties": {
        "method": {
          "type": "string",
          "enum": ["hydrostatic", "godunov", "preissmann"]
        },
        "parameters": {
          "type": "object",
          "properties": {
            "max_iterations": {"type": "integer"},
            "convergence_tol": {"type": "number"},
            "cfl": {"type": "number"},
            "theta": {"type": "number"}
          }
        }
      }
    },
    
    "initial_conditions": {
      "type": "object",
      "properties": {
        "depth": {
          "oneOf": [
            {"type": "number"},
            {"type": "array"},
            {"type": "string", "enum": ["uniform_flow", "dry"]}
          ]
        },
        "flow": {
          "oneOf": [
            {"type": "number"},
            {"type": "array"}
          ]
        }
      }
    },
    
    "output": {
      "type": "object",
      "properties": {
        "directory": {"type": "string"},
        "formats": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["json", "csv", "hdf5", "vtk"]
          }
        },
        "variables": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["depth", "flow", "velocity", "froude", "elevation"]
          }
        },
        "plots": {
          "type": "object",
          "properties": {
            "enabled": {"type": "boolean"},
            "types": {
              "type": "array",
              "items": {
                "type": "string",
                "enum": ["profile", "time_series", "animation"]
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 📝 配置文件示例

### 示例1：简单渠道稳态流

```json
{
  "metadata": {
    "title": "Simple Canal Steady Flow",
    "description": "基础明渠稳态流动计算",
    "author": "User",
    "date": "2025-11-15",
    "version": "1.0"
  },
  
  "simulation": {
    "type": "steady",
    "mode": "single_canal"
  },
  
  "canal": {
    "length": 1000.0,
    "width": 10.0,
    "slope": 0.001,
    "manning_n": 0.025,
    "grid": {
      "nx": 201,
      "type": "uniform"
    }
  },
  
  "boundary_conditions": {
    "upstream": {
      "type": "flow",
      "value": 8.0
    },
    "downstream": {
      "type": "depth",
      "value": null,
      "method": "uniform_flow"
    }
  },
  
  "solver": {
    "method": "hydrostatic",
    "parameters": {
      "max_iterations": 5000,
      "convergence_tol": 0.1
    }
  },
  
  "initial_conditions": {
    "depth": "uniform_flow",
    "flow": 8.0
  },
  
  "output": {
    "directory": "results/case_01",
    "formats": ["json", "csv"],
    "variables": ["depth", "flow", "velocity", "elevation"],
    "plots": {
      "enabled": true,
      "types": ["profile"]
    }
  }
}
```

### 示例2：带闸门的非恒定流

```json
{
  "metadata": {
    "title": "Sluice Gate Unsteady Flow",
    "description": "闸门控制下的非恒定流",
    "author": "User",
    "date": "2025-11-15"
  },
  
  "simulation": {
    "type": "unsteady",
    "mode": "single_canal",
    "time": {
      "start": 0.0,
      "end": 1000.0,
      "dt": 0.5,
      "output_interval": 10.0
    }
  },
  
  "canal": {
    "length": 10000.0,
    "width": 10.0,
    "slope": 0.0005,
    "manning_n": 0.025,
    "grid": {
      "nx": 201,
      "type": "uniform"
    }
  },
  
  "structures": [
    {
      "type": "sluice_gate",
      "name": "Gate_1",
      "position": 5000.0,
      "parameters": {
        "width": 10.0,
        "opening": 2.0,
        "discharge_coefficient": 0.6
      }
    }
  ],
  
  "boundary_conditions": {
    "upstream": {
      "type": "flow",
      "value": 50.0
    },
    "downstream": {
      "type": "depth",
      "value": null,
      "method": "uniform_flow"
    }
  },
  
  "solver": {
    "method": "godunov",
    "parameters": {
      "cfl": 0.5,
      "order": 1
    }
  },
  
  "initial_conditions": {
    "depth": "uniform_flow",
    "flow": 50.0
  },
  
  "output": {
    "directory": "results/case_02_gate",
    "formats": ["json", "csv", "hdf5"],
    "variables": ["depth", "flow", "velocity", "froude"],
    "plots": {
      "enabled": true,
      "types": ["profile", "time_series", "animation"]
    }
  }
}
```

### 示例3：复杂场景（多结构）

```json
{
  "metadata": {
    "title": "Complex Multi-Structure System",
    "description": "多水工结构组合场景"
  },
  
  "simulation": {
    "type": "steady",
    "mode": "single_canal"
  },
  
  "canal": {
    "length": 20000.0,
    "width": 12.0,
    "slope": 0.0003,
    "manning_n": 0.025,
    "grid": {
      "nx": 401
    }
  },
  
  "structures": [
    {
      "type": "sluice_gate",
      "name": "Upstream_Gate",
      "position": 5000.0,
      "parameters": {
        "width": 12.0,
        "opening": 3.0
      }
    },
    {
      "type": "weir",
      "name": "Middle_Weir",
      "position": 12000.0,
      "parameters": {
        "width": 12.0,
        "crest_height": 0.5
      }
    },
    {
      "type": "pump",
      "name": "Pump_Station",
      "position": 18000.0,
      "parameters": {
        "capacity": 5.0,
        "head": 2.0
      }
    }
  ],
  
  "boundary_conditions": {
    "upstream": {
      "type": "flow",
      "value": 80.0
    },
    "downstream": {
      "type": "normal_depth"
    }
  },
  
  "solver": {
    "method": "hydrostatic",
    "parameters": {
      "max_iterations": 10000,
      "convergence_tol": 0.1
    }
  },
  
  "output": {
    "directory": "results/case_03_complex",
    "formats": ["json", "csv"],
    "plots": {
      "enabled": true,
      "types": ["profile"]
    }
  }
}
```

---

## 📤 输出格式规范

### 标准输出JSON格式

```json
{
  "metadata": {
    "simulation_id": "unique_id_timestamp",
    "config_file": "path/to/config.json",
    "software": "HydroClaude",
    "version": "1.0.0",
    "execution_time": "2025-11-15T10:30:00Z",
    "computation_time_seconds": 12.5
  },
  
  "simulation_info": {
    "type": "steady/unsteady",
    "mode": "single_canal/network",
    "status": "success/failed",
    "convergence": {
      "converged": true,
      "iterations": 125,
      "final_residual": 0.08
    }
  },
  
  "results": {
    "spatial_profile": {
      "x": [0, 5, 10, ...],
      "depth": [2.1, 2.15, 2.2, ...],
      "flow": [8.0, 8.0, 8.0, ...],
      "velocity": [0.38, 0.37, 0.36, ...],
      "froude": [0.08, 0.08, 0.08, ...],
      "elevation": [3.0, 2.995, 2.99, ...]
    },
    
    "time_series": {
      "time": [0, 0.5, 1.0, ...],
      "locations": {
        "x_500": {
          "depth": [2.0, 2.05, 2.1, ...],
          "flow": [7.9, 7.95, 8.0, ...]
        },
        "x_5000": {
          "depth": [2.5, 2.55, 2.6, ...],
          "flow": [7.8, 7.9, 8.0, ...]
        }
      }
    },
    
    "structures": [
      {
        "type": "sluice_gate",
        "name": "Gate_1",
        "position": 5000.0,
        "upstream_depth": 3.2,
        "downstream_depth": 1.8,
        "flow": 50.0,
        "velocity_upstream": 1.56,
        "velocity_downstream": 2.78
      }
    ]
  },
  
  "validation": {
    "mass_conservation": {
      "error_percent": 0.000001,
      "grade": "Excellent"
    },
    "energy_conservation": {
      "error_percent": 0.05,
      "grade": "Good"
    },
    "stability": {
      "max_froude": 0.85,
      "min_depth": 0.12,
      "status": "Stable"
    }
  },
  
  "files": {
    "results_csv": "results/case_01/spatial_profile.csv",
    "time_series_csv": "results/case_01/time_series.csv",
    "plots": [
      "results/case_01/longitudinal_profile.png",
      "results/case_01/time_evolution.png"
    ],
    "validation_report": "results/case_01/validation_report.txt"
  }
}
```

---

## 🔧 核心模块设计

### 1. 主程序入口 (`hydro_engine.py`)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 统一仿真引擎主入口
"""

import argparse
import sys
from core.config_parser import ConfigParser
from core.simulation_engine import SimulationEngine
from core.output_manager import OutputManager

def main():
    parser = argparse.ArgumentParser(
        description='HydroClaude 水力学仿真引擎',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'config',
        type=str,
        help='配置文件路径 (JSON格式)'
    )
    
    parser.add_argument(
        '-v', '--validate',
        action='store_true',
        help='仅验证配置文件，不运行仿真'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='覆盖配置文件中的输出目录'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    # 1. 解析配置
    config_parser = ConfigParser()
    config = config_parser.parse(args.config)
    
    if args.validate:
        print("✅ 配置文件验证通过")
        return 0
    
    # 2. 创建仿真引擎
    engine = SimulationEngine(config, verbose=args.verbose)
    
    # 3. 运行仿真
    results = engine.run()
    
    # 4. 输出结果
    output_manager = OutputManager(config, results)
    output_manager.save_all()
    
    print(f"\n✅ 仿真完成！结果保存在: {config['output']['directory']}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

### 2. 配置解析器 (`core/config_parser.py`)

负责：
- 读取JSON配置文件
- Schema验证
- 默认值填充
- 错误检查

### 3. 仿真引擎 (`core/simulation_engine.py`)

负责：
- 根据配置选择求解器
- 初始化求解器参数
- 执行仿真
- 收集结果

### 4. 输出管理器 (`core/output_manager.py`)

负责：
- 标准化结果格式
- 保存JSON/CSV/HDF5
- 生成图表
- 创建验证报告

---

## 🚀 使用方式

### 命令行界面

```bash
# 基本用法
python hydro_engine.py config.json

# 验证配置文件
python hydro_engine.py config.json --validate

# 指定输出目录
python hydro_engine.py config.json -o results/my_case

# 详细输出
python hydro_engine.py config.json --verbose
```

### Python API（未来）

```python
from hydro_engine import HydroSimulation

# 从配置文件
sim = HydroSimulation.from_config('config.json')
results = sim.run()

# 或直接传参
sim = HydroSimulation(
    canal_length=1000.0,
    canal_width=10.0,
    flow=8.0,
    solver='hydrostatic'
)
results = sim.run()
```

---

## 📊 与商业软件对比

| 特性 | HEC-RAS | MIKE 11 | HydroClaude |
|------|---------|---------|-------------|
| 单一入口点 | ✅ | ✅ | ✅ (新架构) |
| 配置文件驱动 | ✅ (DSS) | ✅ (M11) | ✅ (JSON) |
| 标准化输出 | ✅ | ✅ | ✅ |
| CLI支持 | ⚠️ (有限) | ⚠️ (有限) | ✅ |
| Python API | ❌ | ⚠️ (部分) | ✅ (计划中) |
| 开源 | ❌ | ❌ | ✅ |

---

## 📅 实施计划

### Phase 1: 核心架构 (优先)
- [ ] 设计并实现配置文件格式
- [ ] 实现ConfigParser
- [ ] 实现SimulationEngine（基础版）
- [ ] 实现OutputManager
- [ ] 创建hydro_engine.py主入口
- [ ] 编写3个测试配置文件

### Phase 2: 功能完善
- [ ] 支持所有求解器类型
- [ ] 支持所有水工结构
- [ ] 支持时间序列边界条件
- [ ] 实现HDF5输出
- [ ] 实现动画输出

### Phase 3: 高级特性
- [ ] 网络模拟支持
- [ ] 水质模拟集成
- [ ] Python API
- [ ] Web API (REST)

### Phase 4: 生态系统
- [ ] GUI工具
- [ ] 后处理工具
- [ ] 案例库
- [ ] 用户文档

---

## 💡 技术优势

1. **配置驱动** - 无需修改代码，只需编辑配置文件
2. **标准化** - 统一的输入/输出格式，便于集成
3. **可扩展** - 模块化设计，易于添加新功能
4. **自动化友好** - 支持批量运行、参数扫描
5. **版本控制** - 配置文件可纳入Git管理
6. **可重现性** - 配置文件完整记录所有参数

---

## 📝 配置文件最佳实践

1. **使用版本控制** - 将配置文件纳入Git
2. **模板化** - 为常见场景创建模板
3. **注释清晰** - 虽然JSON不支持注释，但可用"_comment"字段
4. **参数验证** - 运行前验证配置
5. **文档完整** - metadata部分详细描述场景

---

**设计者**: HydroClaude Development Team  
**审核者**: [待审核]  
**状态**: 待实施
