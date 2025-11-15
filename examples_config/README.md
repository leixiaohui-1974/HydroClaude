# HydroClaude 配置文件示例

本目录包含HydroClaude统一架构的配置文件示例。

## 📋 示例列表

| 文件 | 场景 | 说明 | 难度 |
|------|------|------|------|
| `01_steady_canal.json` | 简单渠道稳态流 | 最基础的场景，演示标准输入输出 | ⭐ |
| `02_gate_flow.json` | 闸门控制流动 | 演示水工结构功能 | ⭐⭐ |
| `03_unsteady_flow.json` | 非恒定流演化 | 演示时间序列功能 | ⭐⭐⭐ |

## 🚀 快速开始

### 1. 运行仿真

```bash
# 运行稳态流动
python hydro_engine.py examples_config/01_steady_canal.json

# 运行闸门流动（详细输出）
python hydro_engine.py examples_config/02_gate_flow.json --verbose

# 运行非恒定流
python hydro_engine.py examples_config/03_unsteady_flow.json
```

### 2. 验证配置

```bash
# 只验证配置，不运行仿真
python hydro_engine.py examples_config/01_steady_canal.json --validate
```

### 3. 查看配置摘要

```bash
# 显示配置摘要
python hydro_engine.py examples_config/01_steady_canal.json --summary
```

### 4. 指定输出目录

```bash
# 自定义输出目录
python hydro_engine.py examples_config/01_steady_canal.json -o my_results
```

## 📊 结果查看

运行完成后，结果保存在 `results/` 目录下（或自定义目录）。

### 文件结构

```
results/01_steady_canal/
├── results.json              # 完整结果（标准化格式）
├── data/
│   ├── spatial_profile.csv   # 空间剖面数据
│   └── results.h5            # HDF5格式（大数据）
├── plots/
│   └── longitudinal_profile.png  # 纵剖面图
├── reports/
│   └── validation_report.txt     # 验证报告
├── web/
│   └── index.html            # Web查看器
└── FILES.txt                 # 文件清单
```

### 查看Web结果

打开 `results/*/web/index.html` 即可在浏览器中查看交互式结果。

## 🔧 生成模板

```bash
# 生成稳态流模板
python hydro_engine.py --template steady_canal

# 生成非恒定流模板
python hydro_engine.py --template unsteady_canal

# 生成闸门流模板
python hydro_engine.py --template gate
```

## 📝 配置文件格式

所有配置文件遵循统一的JSON Schema格式。详见 `COMMERCIAL_ARCHITECTURE_V2.md`。

### 核心字段

- `metadata`: 元数据（标题、作者等）
- `simulation`: 仿真类型和模式
- `canal`: 渠道几何参数
- `structures`: 水工结构（可选）
- `boundary_conditions`: 边界条件
- `solver`: 求解器设置
- `initial_conditions`: 初始条件
- `output`: 输出设置

## 🎯 最佳实践

1. **从模板开始**: 使用 `--template` 生成基础模板
2. **逐步修改**: 基于模板修改参数
3. **先验证**: 使用 `--validate` 验证配置
4. **查看摘要**: 使用 `--summary` 确认参数
5. **详细输出**: 调试时使用 `--verbose`

## 📚 更多资源

- 完整文档: `COMMERCIAL_ARCHITECTURE_V2.md`
- API参考: `LIBRARY_REFERENCE.md`
- 开发指南: `DEVELOPMENT_GUIDE.md`

---

**HydroClaude Development Team**  
**Version 1.0.0**
