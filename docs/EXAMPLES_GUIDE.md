# HydroClaude 示例应用指南

## 概述

HydroClaude 提供了丰富的示例应用，涵盖从基础组件到复杂系统的完整案例。本指南将帮助您快速了解和使用这些示例。

## 示例目录

### 水库与调度系列（新增）

#### 示例17: 单水库基础仿真 ⭐ 入门推荐
- **位置**: `examples/example_17_reservoir_basic/`
- **难度**: ⭐⭐
- **时长**: 5-10分钟
- **内容**:
  - 水库物理仿真基础
  - 库容演算和水位计算
  - 发电功率计算
  - 溢洪道泄流
  - 约束检查

**运行方式**:
```bash
cd examples/example_17_reservoir_basic
python demo_reservoir.py
```

**预期输出**:
- 72小时洪水过程仿真
- 水位、流量、库容、发电过程图
- 约束满足性验证

**适用场景**:
- 学习水库基本概念
- 理解库容-水位关系
- 掌握物理仿真方法

---

#### 示例18: 三级梯级水电站调度 ⭐⭐ 进阶推荐
- **位置**: `examples/example_18_cascade_hydropower/`
- **难度**: ⭐⭐⭐
- **时长**: 10-15分钟
- **内容**:
  - 三级梯级系统（R1→R2→R3）
  - 水流传递和时间延迟
  - 联合优化运行
  - 峰谷电价调度
  - 防洪协调控制

**运行方式**:
```bash
cd examples/example_18_cascade_hydropower
python demo_cascade.py
```

**系统配置**:
- R1: 1亿m³, 200MW, 水头80m
- R2: 5000万m³, 150MW, 水头60m
- R3: 2000万m³, 100MW, 水头40m
- 总装机: 450MW

**预期输出**:
- 7天联合运行仿真
- 梯级水位、流量、发电过程
- 防洪控制策略
- 发电效益分析

**适用场景**:
- 梯级水库调度
- 水电站优化运行
- 防洪协调控制

---

#### 示例19: 长距离调水工程 ⭐⭐⭐ 综合应用
- **位置**: `examples/example_19_water_transfer/`
- **难度**: ⭐⭐⭐⭐
- **时长**: 15-20分钟
- **内容**:
  - 大型源水库（200亿m³）
  - 三级泵站（总提升150m）
  - 长距离输水（500km）
  - 末端调蓄池
  - 峰谷电价优化

**运行方式**:
```bash
cd examples/example_19_water_transfer
python demo_water_transfer.py
```

**系统配置**:
- 源水库: 200亿m³（类似丹江口）
- 泵站1: 提升50m, 200MW
- 泵站2: 提升60m, 230MW
- 泵站3: 提升40m, 150MW
- 总距离: 500km

**预期输出**:
- 7天调水运行仿真
- 源水库、泵站、调蓄池状态
- 能耗和电费分析
- 错峰运行效果

**适用场景**:
- 南水北调工程
- 引江济淮工程
- 跨流域调水
- 能耗优化

---

#### 示例20: 城市供水管网 ⭐⭐⭐⭐ 综合应用
- **位置**: `examples/example_20_urban_water_supply/`
- **难度**: ⭐⭐⭐⭐
- **时长**: 15-20分钟
- **内容**:
  - 多水源联合调度（地表水+地下水+外调水）
  - 水处理厂优化运行
  - 高位水池调节
  - 多需水点供水
  - 成本最小化

**运行方式**:
```bash
cd examples/example_20_urban_water_supply
python demo_urban_supply.py
```

**系统配置**:
- 服务人口: 500万
- 水源数: 3个（总能力160 m³/s）
- 水处理厂: 3个（总能力160 m³/s）
- 高位水池: 4个（总容积17万m³）
- 需水节点: 6个（居民+工业+商业）

**预期输出**:
- 7天供水运行仿真
- 多水源分配策略
- 水厂流量和成本
- 高位水池调节
- 供水保证率分析

**适用场景**:
- 城市供水调度
- 供水公司优化
- 多水源管理
- 成本控制

---

## 示例对比

| 示例 | 难度 | 时长 | 核心技术 | 应用领域 |
|-----|------|------|---------|---------|
| 示例17 | ⭐⭐ | 5-10分钟 | 水库物理仿真 | 单水库调度 |
| 示例18 | ⭐⭐⭐ | 10-15分钟 | 梯级协调、优化 | 梯级水电站 |
| 示例19 | ⭐⭐⭐⭐ | 15-20分钟 | 泵站优化、调水 | 跨流域调水 |
| 示例20 | ⭐⭐⭐⭐ | 15-20分钟 | 多水源、管网 | 城市供水 |

## 学习路径

### 初学者路径
1. **示例17**: 掌握水库基础概念
2. **示例18**: 理解梯级系统
3. 阅读文档了解优化原理
4. **示例19/20**: 综合应用

### 工程师路径
1. 快速浏览所有示例
2. 根据实际需求选择相关示例
3. 修改参数适配自己的场景
4. 扩展功能或集成到项目

### 研究者路径
1. 深入研究核心算法
2. 对比不同方法性能
3. 开发新的优化算法
4. 发表研究成果

## 快速开始

### 环境准备

1. **安装依赖**:
```bash
pip install -r requirements_reservoir.txt
```

必需依赖:
- numpy >= 1.20.0
- scipy >= 1.7.0
- matplotlib >= 3.3.0

可选依赖（用于优化）:
- pyomo >= 6.7.0
- pandas >= 1.3.0

2. **安装求解器**（可选，用于优化调度）:
```bash
# Ubuntu/Debian
sudo apt-get install glpk-utils

# 或安装HiGHS（推荐）
pip install highspy
```

### 运行第一个示例

```bash
# 切换到示例目录
cd examples/example_17_reservoir_basic

# 运行示例
python demo_reservoir.py

# 查看结果
ls *.png  # 可视化图表
```

### 理解输出

每个示例都会产生：

1. **控制台输出**:
   - 系统参数
   - 仿真进度
   - 统计结果

2. **可视化图表**（PNG格式）:
   - 水位、流量、库容过程
   - 发电功率
   - 成本分析

3. **性能指标**:
   - 供水量、发电量
   - 约束满足情况
   - 优化效果

## 常见问题

### Q1: 示例运行失败，提示"ModuleNotFoundError"

**A**: 需要安装依赖库:
```bash
pip install numpy scipy matplotlib
```

### Q2: 优化调度不工作

**A**: 需要安装Pyomo和求解器:
```bash
pip install pyomo
sudo apt-get install glpk-utils  # 或 pip install highspy
```

### Q3: 如何修改参数？

**A**: 直接编辑示例文件中的参数配置:
```python
# 例如修改水库库容
reservoir = Reservoir(
    total_capacity=10000e4,  # 修改为1亿m³
    ...
)
```

### Q4: 如何可视化自己的数据？

**A**: 参考示例中的可视化代码:
```python
import matplotlib.pyplot as plt

plt.plot(time, data)
plt.xlabel('时间')
plt.ylabel('数据')
plt.savefig('output.png')
```

### Q5: 示例能否用于实际工程？

**A**:
- 示例代码仅供学习和原型开发
- 实际工程需要:
  - 详细的参数校准
  - 完整的数据验证
  - 安全性评估
  - 专业工程师指导

### Q6: 如何获得技术支持？

**A**:
- 查阅文档: `/docs/INTEGRATION_DESIGN.md`
- GitHub Issues: 报告问题和建议
- 阅读README: 每个示例都有详细说明

## 参数配置指南

### 水库参数
```python
Reservoir(
    reservoir_id="my_reservoir",
    total_capacity=5000e4,       # 总库容 (m³)
    dead_storage=500e4,          # 死库容 (m³)
    min_level=100.0,             # 死水位 (m)
    normal_level=150.0,          # 正常蓄水位 (m)
    flood_limit_level=145.0,     # 防洪限制水位 (m)
    design_level=155.0,          # 设计洪水位 (m)
    has_turbine=True,            # 是否有水轮机
    turbine_capacity=100.0,      # 装机容量 (MW)
    hydraulic_head=50.0,         # 水头 (m)
    ecological_flow=10.0         # 生态流量 (m³/s)
)
```

### 梯级拓扑
```python
CascadeTopology(
    reservoir_ids=["R1", "R2", "R3"],
    connections={"R1": ["R2"], "R2": ["R3"]},
    travel_times={("R1", "R2"): 2.0, ("R2", "R3"): 1.0},
    lateral_inflows={"R1": 50.0, "R2": 30.0, "R3": 20.0}
)
```

## 性能优化建议

### 1. 时间步长选择
- 瞬态分析: dt = 1-60秒
- 日常调度: dt = 3600秒（1小时）
- 长期规划: dt = 86400秒（1天）

### 2. 仿真时长
- 测试: 24-72小时
- 正式仿真: 7-30天
- 长期规划: 1-12月

### 3. 求解器选择
- 快速测试: GLPK
- 中等规模: HiGHS
- 大规模: CPLEX/Gurobi（商业）

## 扩展开发

### 添加自定义组件
```python
from physics.reservoir import Reservoir

class MyReservoir(Reservoir):
    def custom_method(self):
        # 自定义功能
        pass
```

### 修改控制策略
```python
# 自定义调度规则
if water_level > flood_limit:
    outflow = max_discharge
elif water_level < normal_level:
    outflow = ecological_flow
else:
    outflow = inflow * 0.8
```

### 集成优化算法
```python
from optimization.reservoir_scheduler import ReservoirScheduler

scheduler = ReservoirScheduler(reservoir)
result = scheduler.optimize_schedule(
    horizon_hours=24,
    inflow_forecast=forecast,
    electricity_prices=prices
)
```

## 参考资料

### 核心文档
- 融合设计文档: `/docs/INTEGRATION_DESIGN.md`
- 实施总结: `/docs/RESERVOIR_IMPLEMENTATION_SUMMARY.md`
- API文档: `/physics/README_RESERVOIR.md`

### 示例README
- 示例17: `/examples/example_17_reservoir_basic/README.md`
- 示例18: `/examples/example_18_cascade_hydropower/README.md`
- 示例19: `/examples/example_19_water_transfer/README.md`
- 示例20: `/examples/example_20_urban_water_supply/README.md`

### 学术参考
1. 水库调度原理与方法
2. 梯级水电站优化调度
3. 城市供水系统优化
4. 水利工程仿真技术

## 贡献指南

欢迎贡献新的示例！

### 示例要求
1. 清晰的文档说明
2. 完整的代码注释
3. 可视化输出
4. 性能基准测试
5. README文档

### 提交流程
1. Fork项目
2. 创建示例分支
3. 编写代码和文档
4. 提交Pull Request
5. 代码审查

---

**版本**: v2.0.0
**更新日期**: 2025-10-22
**维护者**: HydroClaude Team
