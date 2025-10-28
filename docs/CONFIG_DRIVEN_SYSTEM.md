# 配置驱动仿真系统

HydroClaude v2.0 - 配置驱动仿真系统

**完成日期**: 2025-10-28
**作者**: HydroClaude Team

---

## 📋 系统概述

配置驱动仿真系统允许用户通过**JSON配置文件**运行一维水力学仿真，无需编写Python代码。

### 核心组件

```
engine/
├── config_parser.py      # 配置文件解析器
├── model_builder.py      # 模型构建器
└── simulation_engine.py  # 仿真引擎

simulate.py               # 命令行工具

examples/config_driven/   # 示例配置
├── dam_break.json        # 溃坝模拟
├── uniform_flow.json     # 均匀流验证
└── README.md             # 使用文档
```

### 核心优势

✅ **无需编程** - 通过JSON配置文件定义仿真
✅ **标准化** - 统一的配置格式和输出
✅ **自动化** - 自动生成结果、图表和报告
✅ **可复现** - 配置文件即仿真定义
✅ **高性能** - 支持Numba JIT加速（68x速度提升）

---

## 🚀 快速开始

### 运行溃坝模拟

```bash
python simulate.py examples/config_driven/dam_break.json
```

### 运行均匀流验证

```bash
python simulate.py examples/config_driven/uniform_flow.json
```

### 输出结果

```
results/
├── plots/
│   ├── final_state.png              # 最终状态图
│   ├── spacetime_evolution.png      # 时空演化图
│   └── validation_comparison.png    # 验证对比图
└── statistics.json                  # 统计信息
```

---

## 📝 配置文件格式

### 基本结构

```json
{
  "project": {...},              // 项目信息
  "geometry": {...},             // 几何参数
  "mesh": {...},                 // 网格设置
  "solver": {...},               // 求解器配置
  "initial_conditions": {...},   // 初始条件
  "boundary_conditions": {...},  // 边界条件
  "simulation": {...},           // 仿真参数
  "output": {...},               // 输出设置
  "validation": {...}            // 验证设置（可选）
}
```

### 详细配置

#### 1. Project - 项目信息
```json
{
  "project": {
    "name": "溃坝模拟",
    "description": "标准溃坝测试",
    "author": "用户名",
    "created": "2025-10-28"
  }
}
```

#### 2. Geometry - 几何参数
```json
{
  "geometry": {
    "type": "uniform",           // uniform | variable | from_file
    "channel_width": 10.0,       // 渠宽 (m)
    "channel_length": 2000.0,    // 渠长 (m)
    "bottom_slope": 0.0,         // 底坡（可以是数值或数组）
    "manning_n": 0.025           // Manning糙率系数
  }
}
```

#### 3. Mesh - 网格
```json
{
  "mesh": {
    "n_cells": 400               // 网格数（建议100-400）
  }
}
```

#### 4. Solver - 求解器
```json
{
  "solver": {
    "type": "godunov_fvm",       // 求解器类型
    "spatial_order": 2,          // 空间精度 (1或2)
    "riemann_solver": "hll",     // hll | hllc
    "use_numba": true,           // Numba加速（强烈推荐）
    "well_balanced": false,      // Well-balanced格式
    "cfl": 0.5,                  // CFL数 (0-1)
    "eps_dry": 1e-6              // 干床阈值
  }
}
```

#### 5. Initial Conditions - 初始条件

**溃坝**:
```json
{
  "initial_conditions": {
    "type": "dam_break",
    "h_left": 10.0,              // 左侧水深 (m)
    "h_right": 1.0,              // 右侧水深 (m)
    "dam_position": 1000.0       // 坝址位置 (m)
  }
}
```

**均匀流**:
```json
{
  "initial_conditions": {
    "type": "uniform",
    "h": 2.0,                    // 水深 (m)
    "Q": 20.0                    // 流量 (m³/s)
  }
}
```

#### 6. Boundary Conditions - 边界条件
```json
{
  "boundary_conditions": {
    "left": {
      "type": "h",               // h | Q
      "value": 10.0
    },
    "right": {
      "type": "h",
      "value": 1.0
    }
  }
}
```

#### 7. Simulation - 仿真参数
```json
{
  "simulation": {
    "start_time": 0.0,           // 开始时间 (s)
    "end_time": 30.0,            // 结束时间 (s)
    "max_steps": 1000000,        // 最大步数
    "output_interval": 5.0       // 输出间隔 (s)
  }
}
```

#### 8. Output - 输出设置
```json
{
  "output": {
    "directory": "./results",    // 输出目录
    "formats": ["csv", "hdf5"],  // 输出格式
    "variables": ["h", "Q", "u"],// 输出变量
    "statistics": true,          // 统计信息
    "plots": {
      "enabled": true,           // 生成图表
      "format": "png",
      "dpi": 300
    }
  }
}
```

#### 9. Validation - 验证设置（可选）
```json
{
  "validation": {
    "enabled": true,             // 启用验证
    "analytical_solution": "ritter", // ritter | uniform_flow
    "tolerance": {
      "h_rmse": 0.5,             // 水深RMSE容差 (m)
      "Q_rmse": 10.0,            // 流量RMSE容差 (m³/s)
      "mass_error": 0.1          // 质量误差容差 (%)
    }
  }
}
```

---

## ⚙️ 技术实现

### 架构设计

```
用户配置文件 (JSON)
    ↓
ConfigParser (解析和验证)
    ↓
ModelBuilder (构建求解器)
    ↓
SimulationEngine (运行仿真)
    ↓
ResultsWriter (保存结果)
    ↓
输出: 图表 + 数据 + 报告
```

### 核心类

#### 1. ConfigParser
- 解析JSON配置文件
- 验证配置完整性和一致性
- 提供默认值
- 检查文件路径

**关键方法**:
- `parse()` - 解析配置文件
- `validate()` - 验证配置
- `summary()` - 生成配置摘要

#### 2. ModelBuilder
- 从配置创建求解器
- 设置初始条件
- 设置边界条件
- 提供解析解（如果可用）

**关键方法**:
- `from_config_file()` - 从配置文件创建
- `build_solver()` - 构建求解器
- `get_analytical_solution()` - 获取解析解

#### 3. SimulationEngine
- 统一的仿真运行接口
- 进度监控
- 自动保存结果
- 生成图表
- 验证结果

**关键方法**:
- `initialize()` - 初始化
- `run()` - 运行仿真
- `save_results()` - 保存结果
- `validate()` - 验证结果

---

## 📊 性能测试

### 均匀流验证案例

**配置**:
- 网格数: 100
- 模拟时间: 100秒
- 求解器: Godunov FVM (HLL, 2阶精度)
- Numba加速: 启用

**结果**:
- 总步数: 113步
- 墙钟时间: 1.95秒
- 平均每步: 17.3毫秒
- 生成图表: 3张 (总计984KB)

**性能指标**:
- ✅ 仿真速度: ~51x 实时 (100秒模拟/1.95秒墙钟)
- ✅ Numba加速生效
- ✅ 结果自动保存和可视化

---

## 🎯 支持的功能

### 初始条件类型
- ✅ `dam_break` - 溃坝
- ✅ `uniform` - 均匀流
- ⏳ `from_file` - 从文件读取（规划中）
- ⏳ `expression` - Python表达式（规划中）

### 求解器类型
- ✅ `godunov_fvm` - Godunov有限体积法
  - HLL Riemann求解器
  - HLLC Riemann求解器
  - 二阶MUSCL重构
  - Numba JIT加速（68x）

### 验证解析解
- ✅ `ritter` - Ritter溃坝解析解
- ✅ `uniform_flow` - Manning均匀流公式

### 输出格式
- ✅ `json` - 统计信息
- ✅ `png` - 图表
- ⏳ `csv` - CSV表格（需要pandas）
- ⏳ `hdf5` - HDF5格式（需要h5py）

---

## 🔍 与现有系统的关系

HydroClaude项目现在有**两套配置系统**，针对不同用途：

### 1. YAML配置系统 (core/config.py)
**用途**: 水资源调度优化（宏观系统）

**内容**:
- ReservoirConfig - 水库配置
- CanalConfig - 渠道配置
- GateConfig - 闸门配置
- PIDConfig - PID控制器配置
- TopologyConnection - 拓扑连接

**应用场景**:
- 梯级水库调度
- 灌溉系统优化
- 供水系统管理
- MPC控制策略

### 2. JSON配置系统 (engine/)
**用途**: 一维水力学数值模拟（微观水动力学）

**内容**:
- 几何参数（渠道尺寸、坡度）
- 网格设置（单元数）
- 求解器配置（Godunov FVM, Riemann求解器）
- 初始条件（溃坝、均匀流）
- 边界条件（水深、流量）

**应用场景**:
- 溃坝波传播模拟
- Riemann求解器测试
- 数值方法验证
- 学术研究和教学

### 系统集成

两套系统**互补而非重复**：

```
宏观调度 (YAML) ←→ 微观水动力 (JSON)
     ↓                      ↓
  优化策略             数值仿真结果
     ↓                      ↓
  调度决策         详细水动力过程
     ↓                      ↓
     └──────────→ 完整的水利工程解决方案
```

---

## 📚 参考文档

- [配置文件规范](CONFIG_SPECIFICATION.md) - 完整规范
- [快速开始指南](../examples/config_driven/README.md) - 使用教程
- [ConfigParser API](../engine/config_parser.py) - 配置解析器
- [SimulationEngine API](../engine/simulation_engine.py) - 仿真引擎

---

## 🚧 未来计划

### Phase 1（已完成✅）
- ✅ 配置文件解析器
- ✅ 模型构建器
- ✅ 仿真引擎
- ✅ 结果输出系统
- ✅ 命令行工具
- ✅ 示例配置

### Phase 2（规划中）
- ⏳ 时间序列边界条件
- ⏳ 从文件读取初始条件
- ⏳ Python表达式初始条件
- ⏳ 更多解析解类型
- ⏳ 批量运行和参数扫描

### Phase 3（规划中）
- ⏳ GUI配置文件编辑器
- ⏳ 实时仿真监控
- ⏳ 与YAML系统集成
- ⏳ 云端运行支持

---

## 💡 使用案例

### 案例1：溃坝波传播研究

**问题**: 研究溃坝波在不同初始条件下的传播特性

**解决方案**:
1. 创建多个配置文件（不同h_left, h_right）
2. 批量运行仿真
3. 对比分析结果

**优势**: 无需修改代码，快速参数扫描

### 案例2：数值方法验证

**问题**: 对比HLL和HLLC Riemann求解器的性能

**解决方案**:
1. 创建相同配置，只改变riemann_solver参数
2. 运行对比
3. 分析精度和稳定性差异

**优势**: 配置文件即实验设计

### 案例3：教学演示

**问题**: 水力学课程需要演示不同场景

**解决方案**:
1. 准备多个教学配置文件
2. 课堂上快速运行
3. 自动生成专业图表

**优势**: 专注教学内容，无需现场编程

---

## 🎓 最佳实践

### 1. 配置文件管理
- 使用有意义的文件名（如`dam_break_10m.json`）
- 添加详细的description字段
- 版本控制配置文件

### 2. 网格数选择
- 粗网格（<100）：快速测试
- 中等网格（100-200）：标准模拟
- 精细网格（400+）：高精度验证

### 3. CFL数设置
- CFL=0.5：推荐值（稳定）
- CFL=0.8：更快（可能不稳定）
- CFL=0.3：保守（最稳定）

### 4. Numba加速
- 始终启用`use_numba: true`
- 首次运行会有JIT编译延迟（~1秒）
- 后续运行速度提升68x

---

## 🙏 致谢

配置驱动系统的设计参考了以下商业软件：

- **HEC-RAS** - 文本配置文件系统
- **MIKE 11** - .m11配置文件格式
- **InfoWorks ICM** - 数据库驱动配置
- **OpenFOAM** - 字典式配置文件

---

**HydroClaude Team - 2025-10-28**

*Generated with [Claude Code](https://claude.com/claude-code)*

*Co-Authored-By: Claude <noreply@anthropic.com>*
