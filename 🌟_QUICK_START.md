# 🌟 HydroClaude 统一架构快速开始

**最后更新**: 2025-11-15  
**当前版本**: v1.0.0  
**状态**: ✅ 核心架构完成

---

## 🎉 重大更新

**HydroClaude已从"示例脚本集合"升级为"商业级统一软件"！**

### 主要变化

| 之前 | 现在 |
|------|------|
| ❌ 每个场景一个脚本 | ✅ **一个程序入口** |
| ❌ 手工修改Python代码 | ✅ **配置文件驱动** |
| ❌ 输出格式不统一 | ✅ **标准化输出** |
| ❌ 没有Web展示 | ✅ **统一Web查看器** |

---

## 🚀 5分钟上手

### 步骤1: 安装依赖

```bash
pip install numpy pandas matplotlib jsonschema
# 可选: pip install h5py
```

### 步骤2: 生成配置模板

```bash
# 生成简单渠道配置
python3 hydro_engine.py --template steady_canal
# 生成文件: config_template_steady_canal.json
```

### 步骤3: 运行仿真

```bash
# 运行示例配置
python3 hydro_engine.py examples_config/01_steady_canal.json

# 或运行刚生成的模板
python3 hydro_engine.py config_template_steady_canal.json
```

### 步骤4: 查看结果

```bash
# 在浏览器中打开Web查看器
open results/01_steady_canal/web/index.html

# 或查看JSON结果
cat results/01_steady_canal/results.json
```

---

## 📂 新的项目结构

```
HydroClaude/
├── hydro_engine.py           ⭐ 唯一程序入口
├── core/                      新增：核心引擎
│   ├── config_parser.py       配置解析
│   ├── simulation_engine.py   仿真引擎
│   └── output_manager.py      输出管理
├── examples_config/           新增：配置示例
│   ├── 01_steady_canal.json
│   ├── 02_gate_flow.json
│   └── 03_unsteady_flow.json
├── results/                   自动生成的结果
│   └── [case_name]/
│       ├── results.json       标准化结果
│       ├── data/              数据文件
│       ├── plots/             图表
│       └── web/index.html     Web查看器
└── solvers/                   原有求解器（不变）
    ├── hydrostatic_canal_solver.py
    └── godunov_fvm_solver.py
```

---

## 🎯 三种使用方式

### 方式1: 命令行（推荐）

```bash
# 基本用法
python3 hydro_engine.py config.json

# 详细输出
python3 hydro_engine.py config.json --verbose

# 只验证配置
python3 hydro_engine.py config.json --validate

# 查看摘要
python3 hydro_engine.py config.json --summary

# 自定义输出目录
python3 hydro_engine.py config.json -o my_results
```

### 方式2: Python脚本

```python
from core.config_parser import ConfigParser
from core.simulation_engine import SimulationEngine
from core.output_manager import OutputManager

# 解析配置
config = ConfigParser().parse('config.json')

# 运行仿真
results = SimulationEngine(config).run()

# 保存结果
OutputManager(config, results).save_all()
```

### 方式3: 生成模板后修改

```bash
# 1. 生成模板
python3 hydro_engine.py --template steady_canal

# 2. 编辑配置
vim config_template_steady_canal.json

# 3. 运行
python3 hydro_engine.py config_template_steady_canal.json
```

---

## 📋 配置文件格式

### 最简配置

```json
{
  "simulation": {
    "type": "steady",
    "mode": "single_canal"
  },
  "canal": {
    "length": 1000.0,
    "width": 10.0,
    "slope": 0.001,
    "manning_n": 0.025
  },
  "boundary_conditions": {
    "upstream": {"type": "flow", "value": 8.0},
    "downstream": {"type": "depth", "method": "uniform_flow"}
  },
  "solver": {
    "method": "hydrostatic"
  },
  "output": {
    "directory": "results/my_case"
  }
}
```

### 完整配置

参考 `examples_config/` 下的示例，或查看 `COMMERCIAL_ARCHITECTURE_V2.md`。

---

## 📊 结果文件说明

运行后，结果保存在 `results/[case_name]/`：

```
results/01_steady_canal/
├── results.json              # ⭐ 主结果文件（标准格式）
├── data/
│   ├── spatial_profile.csv   # CSV格式数据
│   └── results.h5            # HDF5格式（如果启用）
├── plots/
│   └── longitudinal_profile.png  # 自动生成的图表
├── reports/
│   └── validation_report.txt     # 验证报告
├── web/
│   └── index.html            # ⭐ Web查看器
└── FILES.txt                 # 文件清单
```

### results.json 格式

```json
{
  "hydro_result": {...},      // 软件版本信息
  "simulation": {...},        // 仿真状态
  "geometry": {               // 几何（时间+空间）
    "dimensions": {...}
  },
  "variables": {              // 变量数据
    "depth": {...},
    "flow": {...},
    "velocity": {...},
    ...
  },
  "structures": [...],        // 水工结构结果
  "validation": {...}         // 验证评分
}
```

**这个格式适配所有场景！** 稳态/非恒定流/有无结构都用同一格式。

---

## 🌐 Web查看器

### 特点

- ✅ 自动适配所有场景
- ✅ 交互式图表
- ✅ 响应式设计
- ✅ 数据导出

### 包含的组件

| 组件 | 功能 | 适用场景 |
|------|------|---------|
| 总览面板 | 基本信息、统计 | 所有 |
| 空间视图 | 纵剖面、分布图 | 所有 |
| 时间视图 | 时间序列、等值线 | 非恒定流 |
| 结构分析 | 上下游对比 | 有结构 |
| 验证报告 | 质量评分 | 所有 |

---

## 🔧 常见问题

### Q1: 如何修改参数？

**之前**: 修改Python脚本  
**现在**: 修改JSON配置文件

```bash
# 编辑配置
vim config.json

# 运行（无需修改代码）
python3 hydro_engine.py config.json
```

### Q2: 如何添加闸门？

在配置文件中添加 `structures` 字段：

```json
{
  "structures": [
    {
      "type": "sluice_gate",
      "position": 5000.0,
      "parameters": {
        "width": 10.0,
        "opening": 2.0
      }
    }
  ]
}
```

### Q3: 如何切换求解器？

修改 `solver.method`：

```json
{
  "solver": {
    "method": "hydrostatic"  // 或 "godunov"
  }
}
```

### Q4: 结果保存在哪里？

配置文件中的 `output.directory`：

```json
{
  "output": {
    "directory": "results/my_case"
  }
}
```

或使用 `-o` 参数覆盖：

```bash
python3 hydro_engine.py config.json -o custom_output
```

---

## 📚 深入学习

### 必读文档

1. **`COMMERCIAL_ARCHITECTURE_V2.md`** - 架构设计详解 ⭐⭐⭐
2. **`examples_config/README.md`** - 示例说明
3. **`ROADMAP_COMMERCIAL.md`** - 开发路线图
4. **`🎉_商业架构已完成_COMMERCIAL_READY.md`** - 完成总结

### 基础库参考

- **`LIBRARY_REFERENCE.md`** - 求解器API
- **`DEVELOPMENT_GUIDE.md`** - 开发规范

---

## 🎯 对比旧方式

### 旧方式（Phase 0）

```bash
# 运行基础示例
cd examples/example_01_canal_flow/scripts
python 01_basic_v2.py

# 运行闸门示例
python 07_sluice_gate_flow_v2.py

# 运行复杂示例
python 12_advanced_optimized_v2.py

# 问题：
# - 每个场景一个脚本
# - 修改参数需要改代码
# - 输出格式不统一
# - 没有统一的结果查看方式
```

### 新方式（Phase 1）✨

```bash
# 一个程序，所有场景
python3 hydro_engine.py examples_config/01_steady_canal.json
python3 hydro_engine.py examples_config/02_gate_flow.json
python3 hydro_engine.py examples_config/03_unsteady_flow.json

# 优点：
# ✅ 统一入口
# ✅ 配置驱动
# ✅ 标准化输出
# ✅ Web查看器
# ✅ 对标商业软件
```

---

## 🏆 关键成就

1. ✅ **单一程序入口** - 告别几十个脚本
2. ✅ **配置驱动** - 无需修改代码
3. ✅ **标准化** - 统一的输入输出格式
4. ✅ **通用数据模型** - 一套格式适配所有场景
5. ✅ **Web展示** - 现代化结果查看
6. ✅ **商业级质量** - 对标HEC-RAS/MIKE

---

## 📞 获取帮助

### 查看帮助

```bash
python3 hydro_engine.py -h
```

### 常用命令

```bash
# 验证配置
python3 hydro_engine.py config.json --validate

# 查看配置摘要
python3 hydro_engine.py config.json --summary

# 详细输出
python3 hydro_engine.py config.json --verbose

# 查看版本
python3 hydro_engine.py --version

# 生成模板
python3 hydro_engine.py --template steady_canal
```

---

## 🎊 开始使用

```bash
# 1. 安装依赖
pip install numpy pandas matplotlib jsonschema

# 2. 运行第一个示例
python3 hydro_engine.py examples_config/01_steady_canal.json

# 3. 查看结果
open results/01_steady_canal/web/index.html

# 🎉 完成！
```

---

**欢迎使用HydroClaude统一架构！**

**From Scripts to Commercial Software** ✨

---

**HydroClaude Development Team**  
**Version 1.0.0**  
**2025-11-15**
