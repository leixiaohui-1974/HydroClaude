# HydroClaude 示例集

本目录包含HydroClaude水利仿真框架的各类示例，涵盖明渠流动、管道系统、水电站、控制策略等多个领域。

## 目录结构

每个示例都遵循统一的目录结构：

```
example_XX_name/
├── README.md              # 示例说明文档
├── code/                  # 核心脚本
│   ├── 01_*.py           # 主要示例脚本
│   └── 02_*.py           # 扩展示例
├── outputs/               # 输出文件
│   ├── figures/          # 静态图表（PNG）
│   ├── animations/       # 动画文件（GIF）
│   └── data/             # 数据文件（CSV等）
├── docs/                  # 详细文档
├── tests/                 # 测试脚本（如有）
└── archive/               # 归档文件（如有）
```

## 示例分类

### 一、明渠与开放水流系统

| 编号 | 名称 | 主题 | 难度 |
|------|------|------|------|
| [01](example_01_canal_flow/) | **明渠非恒定流仿真** | Saint-Venant方程、数值方法比较 | ⭐⭐ |
| [02](example_02_spillway_cascade/) | **溢洪道级联系统** | 堰流、跌水、能量耗散 | ⭐⭐ |
| [16](example_16_weirs_application/) | **堰闸应用** | 堰流公式、流量计算 | ⭐ |

### 二、管道与压力系统

| 编号 | 名称 | 主题 | 难度 |
|------|------|------|------|
| [02](example_02_pump_system/) | **泵站系统仿真** | 水锤效应、泵站启停 | ⭐⭐ |
| [09](example_09_pipe_rk4/) | **管道系统RK4求解** | MOC方法、时间积分 | ⭐⭐⭐ |
| [10](example_10_series_network/) | **串联管网系统** | 串联管道、压力传递 | ⭐⭐ |
| [11](example_11_tree_network/) | **树状管网系统** | 分岔节点、流量分配 | ⭐⭐⭐ |
| [12](example_12_loop_network/) | **环状管网系统** | Hardy-Cross、流量平差 | ⭐⭐⭐ |
| [22](example_22_water_hammer/) | **水锤效应** | 水锤计算、防护措施 | ⭐⭐⭐ |

### 三、水电站系统

| 编号 | 名称 | 主题 | 难度 |
|------|------|------|------|
| [03](example_03_turbine_demo/) | **水轮机调节系统** | 水轮机、PID调速器 | ⭐⭐ |
| [04](example_04_hydropower_system/) | **水电站系统仿真** | 完整水电站、多物理场耦合 | ⭐⭐⭐ |
| [05](example_05_transient_analysis/) | **甩负荷暂态分析** | 负荷突变、转速响应 | ⭐⭐⭐ |
| [08](example_08_load_acceptance/) | **接受负荷暂态** | 负荷增加、频率调节 | ⭐⭐⭐ |
| [18](example_18_cascade_hydropower/) | **梯级水电站** | 梯级调度、出力优化 | ⭐⭐⭐⭐ |

### 四、控制与优化

| 编号 | 名称 | 主题 | 难度 |
|------|------|------|------|
| [06](example_06_sil_basic/) | **SIL仿真基础** | 软件在环、实时仿真 | ⭐⭐⭐ |
| [07](example_07_fault_test/) | **故障测试** | 故障工况、保护动作 | ⭐⭐⭐ |
| [13](example_13_adaptive_timescale/) | **自适应时间尺度** | 时间步长自适应、误差控制 | ⭐⭐⭐ |
| [14](example_14_adaptive_mpc/) | **自适应模型预测控制** | MPC、在线优化 | ⭐⭐⭐⭐ |
| [15](example_15_rls_identification/) | **RLS参数辨识** | 系统辨识、自适应滤波 | ⭐⭐⭐ |
| [23](example_23_control_comparison/) | **控制策略比较** | PID、MPC、模糊控制 | ⭐⭐⭐ |
| [24](example_24_multi_objective_optimization/) | **多目标优化** | Pareto前沿、决策支持 | ⭐⭐⭐⭐ |

### 五、水资源系统

| 编号 | 名称 | 主题 | 难度 |
|------|------|------|------|
| [17](example_17_reservoir_basic/) | **水库基础模型** | 水量平衡、调度规则 | ⭐⭐ |
| [19](example_19_water_transfer/) | **跨流域调水** | 长距离输水、多级泵站 | ⭐⭐⭐ |
| [20](example_20_urban_water_supply/) | **城市供水系统** | 管网优化、压力管理 | ⭐⭐⭐ |
| [21](example_21_irrigation_optimization/) | **灌溉优化** | 配水计划、节水灌溉 | ⭐⭐⭐ |

## 快速开始

### 1. 运行单个示例

```bash
# 进入示例目录
cd examples/example_01_canal_flow

# 设置Python路径并运行
PYTHONPATH=../.. python code/01_basic.py
```

### 2. 批量运行所有示例

```bash
cd examples
python run_all_examples.py
```

### 3. 生成动画和报告

```bash
cd examples
python generate_animations.py
```

## 输出文件说明

每个示例运行后会在其`outputs/`目录下生成：

- **静态图表** (`figures/`): PNG格式的分析图表
- **动画文件** (`animations/`): GIF格式的动态演示
- **数据文件** (`data/`): CSV等格式的原始数据
- **报告** (某些示例): 详细的分析报告

## 示例难度说明

- ⭐ **入门级**: 基础概念，适合初学者
- ⭐⭐ **初级**: 单一物理过程，基本数值方法
- ⭐⭐⭐ **中级**: 多物理耦合，高级数值方法
- ⭐⭐⭐⭐ **高级**: 复杂系统，优化与控制

## 技术栈

示例使用的主要技术和库：

- **数值方法**: 有限差分、有限体积、MOC特征线法
- **求解器**: SciPy、NumPy
- **可视化**: Matplotlib、动画生成
- **控制**: PID、MPC、自适应控制
- **优化**: NSGA-II、多目标优化

## 贡献指南

欢迎贡献新的示例！请遵循以下规范：

1. 使用统一的目录结构
2. 提供详细的README说明
3. 代码注释清晰
4. 生成可视化结果
5. 包含运行说明

## 常见问题

### Q: 如何选择适合的示例？

A: 根据你的需求选择：
- 学习基础：从⭐和⭐⭐示例开始
- 工程应用：参考对应领域的示例
- 研究开发：查看⭐⭐⭐⭐高级示例

### Q: 示例运行失败怎么办？

A: 检查以下几点：
1. 是否正确设置了PYTHONPATH
2. 依赖包是否全部安装
3. Python版本是否兼容（推荐3.8+）
4. 查看示例的README了解特殊要求

### Q: 如何生成GIF动画？

A: 大部分示例会自动生成GIF，或者运行对应的`*_animation.py`脚本。

## 更新日志

- **2025-10-22**: 目录结构标准化，批量生成README
- **2025-10-21**: 重构示例代码，统一接口
- **2025-10-20**: 添加新示例和文档

## 联系方式

- 项目主页: [GitHub Repository](https://github.com/leixiaohui-1974/HydroClaude)
- 文档: [完整文档](../docs/)
- 问题反馈: [Issues](https://github.com/leixiaohui-1974/HydroClaude/issues)

---

*Happy simulating! 🌊*
