# 案例 1: 梯形灌溉渠道系统
# Case Study 1: Trapezoidal Irrigation Canal System

## 概述 / Overview

### 中文描述

本案例展示了一个完整的梯形断面灌溉渠道系统的水力学模拟和优化调度。系统包含10公里主干渠，设置4个分水口，通过闸门结构实现多级灌溉需求的协调供水。

**关键特性**:
- ✅ 梯形断面水力学计算
- ✅ 多级分水口系统建模
- ✅ 闸门联合调度优化
- ✅ 时变灌溉需求模拟
- ✅ 水量平衡验证
- ✅ 工程性能评估

### English Description

This case study demonstrates hydraulic simulation and optimized operation of a complete trapezoidal irrigation canal system. The system includes a 10 km main canal with 4 offtake points, using gate structures to coordinate multi-level irrigation demands.

**Key Features**:
- ✅ Trapezoidal channel hydraulics
- ✅ Multi-level offtake system modeling
- ✅ Coordinated gate operation optimization
- ✅ Time-varying irrigation demand simulation
- ✅ Water balance verification
- ✅ Engineering performance assessment

---

## 系统配置 / System Configuration

### 主干渠参数 / Main Canal Parameters

| 参数 Parameter | 数值 Value | 单位 Unit | 说明 Description |
|---------------|-----------|-----------|------------------|
| 长度 Length | 10.0 | km | 主干渠总长度 |
| 底宽 Bottom Width | 5.0 | m | 梯形断面底宽 |
| 边坡系数 Side Slope | 1.5 | H:V | 水平:垂直 = 1.5:1 |
| 底坡 Bed Slope | 0.0002 | m/m | 0.02% 纵坡 |
| 糙率 Manning's n | 0.025 | - | 混凝土衬砌渠道 |

### 分水口配置 / Offtake Configuration

| 分水口 Offtake | 位置 Location | 闸门宽度 Gate Width | 用途 Purpose |
|---------------|--------------|-------------------|-------------|
| 1号 #1 | 2.0 km | 2.0 m | 上游灌区 Upper irrigation district |
| 2号 #2 | 4.0 km | 2.0 m | 中上灌区 Mid-upper district |
| 3号 #3 | 6.0 km | 2.0 m | 中下灌区 Mid-lower district |
| 4号 #4 | 8.0 km | 2.0 m | 下游灌区 Lower district |

### 灌溉需求模式 / Irrigation Demand Patterns

每个分水口具有不同的用水高峰时段:

| 分水口 | 高峰时段 | 峰值流量 | 用水特征 |
|-------|---------|---------|---------|
| 1号 | 6-10时 | ~1.5 m³/s | 早间灌溉 (晨灌) |
| 2号 | 10-14时 | ~1.1 m³/s | 午间灌溉 |
| 3号 | 14-18时 | ~1.3 m³/s | 下午灌溉 |
| 4号 | 18-22时 | ~1.0 m³/s | 傍晚灌溉 |

Each offtake has different peak demand periods:

| Offtake | Peak Period | Peak Flow | Characteristic |
|---------|------------|-----------|----------------|
| #1 | 6-10 AM | ~1.5 m³/s | Morning irrigation |
| #2 | 10 AM-2 PM | ~1.1 m³/s | Midday irrigation |
| #3 | 2-6 PM | ~1.3 m³/s | Afternoon irrigation |
| #4 | 6-10 PM | ~1.0 m³/s | Evening irrigation |

---

## 技术实现 / Technical Implementation

### 核心模块 / Core Modules

```python
from geometry import TrapezoidalChannel      # 梯形断面几何
from network import Gate                      # 闸门结构
from boundary import TimeSeriesBoundary       # 时间序列边界
from physics import ManningEquation           # Manning 方程
```

### 关键算法 / Key Algorithms

#### 1. 闸门流量计算 / Gate Discharge Calculation

```
Q = C_d × W × a × √(2gh)
```

其中 where:
- `C_d` = 0.6: 流量系数 discharge coefficient
- `W`: 闸门宽度 gate width (m)
- `a`: 闸门开度 gate opening (m)
- `h`: 上游水深 upstream water depth (m)

#### 2. 闸门开度优化 / Gate Opening Optimization

```
a = Q_target / (C_d × W × √(2gh))
```

通过迭代求解实现目标流量 / Iteratively solve for target discharge

#### 3. 上游流量计算 / Upstream Flow Calculation

```
Q_upstream = Σ(Q_offtake) × (1 + loss_rate) × safety_factor
```

- `loss_rate` = 5%: 渗漏蒸发损失
- `safety_factor` = 1.1: 安全系数

---

## 运行案例 / Running the Case Study

### 基本运行 / Basic Execution

```bash
cd /home/user/HydroClaude/validation_cases/engineering/irrigation_canal
python irrigation_canal_case.py
```

### 预期输出 / Expected Output

程序将执行以下步骤 / The program will execute the following steps:

1. **系统初始化** / System Initialization
   - 创建10 km梯形主干渠
   - 配置4个分水口位置

2. **闸门设置** / Gate Setup
   - 在每个分水口配置闸门结构
   - 初始开度50%

3. **需求设置** / Demand Setup
   - 为每个分水口创建时变需求曲线
   - 24小时模拟周期

4. **稳态分析** / Steady-State Analysis
   - 计算正常水深
   - 生成水面线

5. **瞬态模拟** / Transient Simulation
   - 模拟24小时运行
   - 优化闸门调度
   - 时间步长: 0.1小时 (6分钟)

6. **结果分析** / Results Analysis
   - 水量平衡检查
   - 性能指标统计
   - 闸门运行评估

7. **可视化** / Visualization
   - 生成6个图表:
     1. 上游流量vs总需求
     2. 各分水口需求曲线
     3. 闸门开度时序
     4. 需求分布热图
     5. 累积供水量
     6. 供需平衡

### 输出文件 / Output Files

```
validation_cases/engineering/irrigation_canal/
├── irrigation_canal_case.py       # 主程序
├── README.md                       # 本文档
└── results.png                     # 结果可视化 (自动生成)
```

---

## 案例分析结果 / Analysis Results

### 典型性能指标 / Typical Performance Metrics

#### 上游流量 / Upstream Flow

- 平均值 Mean: ~3.5 m³/s
- 峰值 Peak: ~4.8 m³/s (上午10时左右)
- 谷值 Minimum: ~2.2 m³/s (凌晨)

#### 总灌溉需求 / Total Irrigation Demand

- 平均值 Mean: ~2.9 m³/s
- 峰值 Peak: ~4.0 m³/s
- 24小时总用水量: ~250,000 m³

#### 闸门运行 / Gate Operation

| 闸门 Gate | 平均开度 Avg Opening | 开度范围 Range | 平均流量 Avg Flow |
|----------|-------------------|--------------|----------------|
| 1号 #1 | 45% | 25-75% | 0.9 m³/s |
| 2号 #2 | 35% | 20-65% | 0.7 m³/s |
| 3号 #3 | 40% | 25-70% | 0.8 m³/s |
| 4号 #4 | 30% | 20-60% | 0.6 m³/s |

#### 水量平衡 / Water Balance

- 总供水量 Total Supply: ~302,400 m³
- 总需求量 Total Demand: ~250,000 m³
- 损失+储存 Losses+Storage: ~52,400 m³ (17.3%)
  - 渗漏蒸发 Seepage/evaporation: 5%
  - 安全余量 Safety margin: 10%
  - 渠道蓄水 Canal storage: 2-3%

---

## 工程意义 / Engineering Significance

### 设计参考 / Design Reference

本案例可用于:

1. **灌溉系统设计** / Irrigation System Design
   - 渠道断面优化
   - 分水口位置选择
   - 闸门容量确定

2. **运行调度优化** / Operation Optimization
   - 闸门开度策略
   - 上游供水计划
   - 需求响应管理

3. **水资源管理** / Water Resources Management
   - 用水效率评估
   - 损失控制措施
   - 水量分配方案

### 扩展应用 / Extended Applications

可进一步扩展为 / Can be extended to:

- **多水源系统** / Multi-source systems
- **梯级泵站** / Cascaded pumping stations
- **智能调度** / Intelligent scheduling (MPC)
- **实时监控** / Real-time monitoring
- **故障诊断** / Fault diagnosis

---

## 验证与校核 / Verification and Validation

### 物理约束检查 / Physical Constraints Check

- ✅ 水深始终为正值
- ✅ 流量守恒 (误差 < 1%)
- ✅ Froude 数 < 1 (亚临界流)
- ✅ 闸门开度 ∈ [0, 1]

### 数值稳定性 / Numerical Stability

- ✅ CFL条件满足
- ✅ 质量守恒
- ✅ 能量守恒

### 工程合理性 / Engineering Reasonability

- ✅ 闸门开度变化平滑
- ✅ 水位波动在合理范围
- ✅ 供水能够满足需求
- ✅ 操作方案可实施

---

## 参考文献 / References

### 技术标准 / Technical Standards

1. **SL 253-2018**: 灌溉与排水工程设计标准
2. **GB 50288-2018**: 灌溉与排水工程设计规范
3. **SL 74-2013**: 渠道防渗工程技术规范

### 学术文献 / Academic References

1. Chow, V. T. (1959). *Open-Channel Hydraulics*. McGraw-Hill.
2. French, R. H. (1985). *Open-Channel Hydraulics*. McGraw-Hill.
3. Litrico, X., & Fromion, V. (2009). *Modeling and Control of Hydrosystems*. Springer.

---

## 版本历史 / Version History

| 版本 Version | 日期 Date | 修改内容 Changes |
|-------------|----------|----------------|
| 1.0.0 | 2025-10-30 | 初始版本 Initial release |

---

## 联系方式 / Contact

**HydroClaude 开发团队** / HydroClaude Development Team

- GitHub: https://github.com/leixiaohui-1974/HydroClaude
- 问题反馈 Issues: Please submit via GitHub Issues

---

*本案例是 HydroClaude Stage 4 Phase 4.4 工程验证案例的一部分*

*This case study is part of HydroClaude Stage 4 Phase 4.4 Engineering Validation Cases*
