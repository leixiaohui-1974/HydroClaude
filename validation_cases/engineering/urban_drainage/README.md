# 案例 4: 城市排水管网系统
# Case Study 4: Urban Drainage System

## 概述 / Overview

### 中文描述

本案例展示了城市排水管网系统的水力模拟，包括暴雨径流计算、排水渠演算、涵洞过流和内涝风险评估。系统模拟3条排水渠、2个涵洞和3个汇水区对设计暴雨的响应。

**关键特性**:
- ✅ 排水网络拓扑建模
- ✅ 设计暴雨生成 (芝加哥雨型)
- ✅ 径流计算 (推理公式法)
- ✅ 河道演算 (马斯京根法)
- ✅ 涵洞水力计算
- ✅ 排水能力评估

### English Description

This case study demonstrates urban drainage network hydraulic simulation, including storm runoff computation, channel routing, culvert hydraulics, and flooding risk assessment. The system simulates 3 drainage channels, 2 culverts, and 3 catchment areas responding to a design storm.

**Key Features**:
- ✅ Drainage network topology modeling
- ✅ Design storm generation (Chicago method)
- ✅ Runoff computation (rational method)
- ✅ Channel routing (Muskingum method)
- ✅ Culvert hydraulics
- ✅ Drainage capacity assessment

---

## 系统配置 / System Configuration

### 网络拓扑 / Network Topology

```
汇水区A → 排水渠1 → 涵洞1 → 排水渠2 → 涵洞2 → 排水渠3 → 出口
  ↓           ↓                    ↓                    ↓
CATCH-A     CH-1    CULV-1       CH-2    CULV-2       CH-3    Outlet
            (800m)   (50m)       (600m)   (80m)      (1000m)
                        ↑                    ↑
                    汇水区B              汇水区C
                    CATCH-B              CATCH-C
```

### 排水渠参数 / Channel Parameters

#### CH-1: 上游排水渠 / Upper Drainage Channel

| 参数 Parameter | 数值 Value | 单位 Unit | 说明 Description |
|---------------|-----------|-----------|------------------|
| 类型 Type | 梯形 Trapezoidal | - | - |
| 长度 Length | 800 | m | - |
| 底宽 Bottom Width | 2.0 | m | - |
| 边坡 Side Slope | 1.5 | H:V | - |
| 底坡 Bed Slope | 0.005 | m/m | 0.5% |
| 糙率 Manning's n | 0.015 | - | 混凝土 Concrete |

#### CH-2: 中游排水渠 / Middle Drainage Channel

| 参数 Parameter | 数值 Value | 单位 Unit | 说明 Description |
|---------------|-----------|-----------|------------------|
| 类型 Type | 不规则 Irregular | - | 带边墩 With bench |
| 长度 Length | 600 | m | - |
| 底坡 Bed Slope | 0.004 | m/m | 0.4% |
| 糙率 Manning's n | 0.016 | - | - |

#### CH-3: 下游排水渠 / Lower Drainage Channel

| 参数 Parameter | 数值 Value | 单位 Unit | 说明 Description |
|---------------|-----------|-----------|------------------|
| 类型 Type | 梯形 Trapezoidal | - | - |
| 长度 Length | 1000 | m | - |
| 底宽 Bottom Width | 3.0 | m | 较大 Larger |
| 边坡 Side Slope | 2.0 | H:V | - |
| 底坡 Bed Slope | 0.003 | m/m | 0.3% |
| 糙率 Manning's n | 0.015 | - | 混凝土 Concrete |

### 涵洞参数 / Culvert Parameters

#### CULV-1: CH-1 → CH-2

| 参数 Parameter | 数值 Value | 单位 Unit |
|---------------|-----------|-----------|
| 直径 Diameter | 1.2 | m |
| 长度 Length | 50 | m |
| 进口高程 Inlet Elevation | 0.0 | m |
| 出口高程 Outlet Elevation | -0.1 | m |
| 进口损失系数 Entrance Loss | 0.5 | - |
| 出口损失系数 Exit Loss | 1.0 | - |
| 糙率 Manning's n | 0.013 | - |

#### CULV-2: CH-2 → CH-3

| 参数 Parameter | 数值 Value | 单位 Unit |
|---------------|-----------|-----------|
| 直径 Diameter | 1.5 | m |
| 长度 Length | 80 | m |
| 进口高程 Inlet Elevation | -0.1 | m |
| 出口高程 Outlet Elevation | -0.3 | m |
| 进口损失系数 Entrance Loss | 0.5 | - |
| 出口损失系数 Exit Loss | 1.0 | - |
| 糙率 Manning's n | 0.013 | - |

### 汇水区参数 / Catchment Parameters

#### CATCH-A: 居住区 / Residential Area

| 参数 Parameter | 数值 Value | 单位 Unit |
|---------------|-----------|-----------|
| 面积 Area | 25 | ha |
| 不透水率 Imperviousness | 60% | - |
| 汇流时间 Time of Concentration | 15 | min |
| 径流系数 Runoff Coefficient | 0.5 | - |
| 排入 Drains to | CH-1 | - |

#### CATCH-B: 商业区 / Commercial Area

| 参数 Parameter | 数值 Value | 单位 Unit |
|---------------|-----------|-----------|
| 面积 Area | 15 | ha |
| 不透水率 Imperviousness | 80% | - |
| 汇流时间 Time of Concentration | 10 | min |
| 径流系数 Runoff Coefficient | 0.7 | - |
| 排入 Drains to | CH-2 | - |

#### CATCH-C: 混合用地 / Mixed Use

| 参数 Parameter | 数值 Value | 单位 Unit |
|---------------|-----------|-----------|
| 面积 Area | 20 | ha |
| 不透水率 Imperviousness | 70% | - |
| 汇流时间 Time of Concentration | 12 | min |
| 径流系数 Runoff Coefficient | 0.6 | - |
| 排入 Drains to | CH-3 | - |

**总汇水面积 / Total Catchment Area**: 60 公顷 / hectares

---

## 技术实现 / Technical Implementation

### 核心模块 / Core Modules

```python
from geometry import TrapezoidalChannel, IrregularChannel
from network.culvert_structure import Culvert
from boundary import TimeSeriesBoundary
```

### 水文水力方法 / Hydrologic-Hydraulic Methods

#### 1. 设计暴雨 / Design Storm

**芝加哥雨型 / Chicago Hyetograph**:

```
i(t) = a / (t + b)^c
```

其中 where:
- `i`: 降雨强度 rainfall intensity (mm/hr)
- `t`: 时间 time (min)
- `a = 2000 × T^0.2`: 系数 coefficient
- `b = 10`: 常数 constant
- `c = 0.75`: 指数 exponent
- `T`: 重现期 return period (years)

峰值时间 / Peak time: `t_peak = 0.4 × duration`

#### 2. 径流计算 / Runoff Computation

**推理公式法 / Rational Method**:

```
Q = C × i × A / 360
```

其中 where:
- `Q`: 径流量 runoff (m³/s)
- `C`: 径流系数 runoff coefficient (0-1)
- `i`: 降雨强度 intensity (mm/hr)
- `A`: 汇水面积 catchment area (ha)

径流系数 / Runoff coefficients:
- 居住区 Residential: C = 0.5
- 商业区 Commercial: C = 0.7
- 混合区 Mixed use: C = 0.6

#### 3. 河道演算 / Channel Routing

**马斯京根法 / Muskingum Method**:

```
O_{i+1} = C_0 × I_{i+1} + C_1 × I_i + C_2 × O_i
```

系数 / Coefficients:
```
C_0 = (-Kx + 0.5Δt) / (K - Kx + 0.5Δt)
C_1 = (Kx + 0.5Δt) / (K - Kx + 0.5Δt)
C_2 = (K - Kx - 0.5Δt) / (K - Kx + 0.5Δt)
```

其中 where:
- `K`: 蓄量常数 storage constant ≈ L/1000 (hours)
- `x`: 权重因子 weighting factor = 0.2
- `Δt`: 时间步长 time step (hours)
- `I`: 入流 inflow (m³/s)
- `O`: 出流 outflow (m³/s)

#### 4. 涵洞水力 / Culvert Hydraulics

**能量方程 / Energy Equation**:

```
H_upstream = H_downstream + h_f + h_e + h_ex
```

其中 where:
- `h_f`: 沿程损失 friction loss (Manning公式)
- `h_e`: 进口损失 entrance loss = K_e × v²/(2g)
- `h_ex`: 出口损失 exit loss = K_ex × v²/(2g)

---

## 运行案例 / Running the Case

### 基本运行 / Basic Execution

```bash
cd /home/user/HydroClaude/validation_cases/engineering/urban_drainage
python urban_drainage_case.py
```

### 执行步骤 / Execution Steps

1. **系统初始化** / System Initialization
   - 创建排水系统 (10年设计标准)

2. **网络拓扑** / Network Topology
   - 3条排水渠
   - 2个涵洞连接

3. **汇水区** / Catchments
   - 3个汇水区 (总60公顷)
   - 径流系数配置

4. **设计暴雨** / Design Storm
   - 芝加哥雨型
   - 历时120分钟
   - 时间步长5分钟

5. **系统模拟** / System Simulation
   - 径流计算
   - 河道演算
   - 涵洞过流
   - 水位计算

6. **能力评估** / Capacity Assessment
   - 检查排水能力
   - 识别风险点

7. **可视化** / Visualization
   - 6个综合图表

### 输出文件 / Output Files

```
validation_cases/engineering/urban_drainage/
├── urban_drainage_case.py          # 主程序
├── README.md                        # 本文档
└── results.png                      # 结果可视化
```

---

## 典型结果 / Typical Results

### 设计暴雨 (10年) / Design Storm (10-year)

- 历时 Duration: 120 分钟 minutes
- 峰值强度 Peak Intensity: ~60 mm/hr
- 总雨量 Total Rainfall: ~45 mm
- 峰值时间 Peak Time: ~48 分钟 minutes

### 径流响应 / Runoff Response

| 汇水区 Catchment | 峰值径流 Peak Runoff | 峰现时间 Time to Peak |
|-----------------|-------------------|---------------------|
| CATCH-A (25 ha) | ~2.0 m³/s | ~50 min |
| CATCH-B (15 ha) | ~1.8 m³/s | ~52 min |
| CATCH-C (20 ha) | ~1.5 m³/s | ~54 min |

### 排水渠流量 / Channel Discharges

| 排水渠 Channel | 峰值流量 Peak Flow | 峰现时间 Time to Peak | 演算效果 Routing Effect |
|---------------|------------------|---------------------|-------------------|
| CH-1 | ~1.9 m³/s | ~52 min | 轻微削减 Slight attenuation |
| CH-2 | ~3.4 m³/s | ~55 min | 叠加效应 Combined flow |
| CH-3 | ~4.5 m³/s | ~58 min | 系统总流量 System total |

### 排水能力评估 / Capacity Assessment

| 排水渠 Channel | 峰值水深 Peak Depth | 设计水深 Design Depth | 利用率 Utilization | 状态 Status |
|---------------|-------------------|---------------------|----------------|-----------|
| CH-1 | ~1.8 m | 2.5 m | 72% | ✓ 正常 OK |
| CH-2 | ~1.2 m | 1.5 m | 80% | ✓ 正常 OK |
| CH-3 | ~2.0 m | 2.5 m | 80% | ✓ 正常 OK |

**结论 / Conclusion**: 所有排水渠在10年设计标准下均未超过排水能力。

---

## 工程意义 / Engineering Significance

### 设计应用 / Design Applications

1. **排水系统设计** / Drainage System Design
   - 排水渠断面尺寸
   - 涵洞直径选择
   - 网络拓扑优化

2. **内涝风险评估** / Flood Risk Assessment
   - 识别薄弱环节
   - 超载预警
   - 应急预案

3. **运行管理** / Operation Management
   - 实时监控
   - 清淤计划
   - 维护优先级

### 设计准则 / Design Criteria

**中国规范** / Chinese Standards (GB 50014-2021):

| 区域 Area | 重现期 Return Period | 排水能力 Capacity |
|----------|-------------------|----------------|
| 中心城区 Central | 3-5年 years | 设计暴雨 Design storm |
| 一般城区 General | 2-3年 years | - |
| 重要区域 Important | 10-20年 years | 校核标准 Check standard |

**排水渠设计** / Channel Design:
- 设计水深 ≤ 80% 总深度
- 流速: 0.6-3.0 m/s
- 安全超高 ≥ 0.3 m

**涵洞设计** / Culvert Design:
- 最小直径 ≥ 0.4 m (城市)
- 覆土厚度 ≥ 0.7 m
- 最大流速 ≤ 5.0 m/s

---

## 扩展功能 / Extended Capabilities

### 可进一步扩展为 / Can be Extended to:

1. **SWMM集成** / SWMM Integration
   - 详细管网模拟
   - 地表漫流
   - 污染物输移

2. **低影响开发 (LID)** / Low Impact Development
   - 绿色屋顶 Green roofs
   - 雨水花园 Rain gardens
   - 透水铺装 Permeable pavement
   - 蓄水池 Detention ponds

3. **实时控制** / Real-Time Control
   - 智能闸门
   - 泵站调度
   - 预警系统

4. **气候变化适应** / Climate Change Adaptation
   - 未来降雨情景
   - 系统韧性评估
   - 升级改造方案

5. **水质模拟** / Water Quality
   - 初期冲刷 First flush
   - TSS, BOD, COD
   - 污染负荷削减

---

## 验证与校核 / Verification and Validation

### 物理约束 / Physical Constraints

- ✅ 质量守恒: 入流 = 出流 + 蓄水变化
- ✅ 流量单调性: 下游峰值滞后于上游
- ✅ 径流系数合理: 0 < C < 1
- ✅ 排水能力充足: 利用率 < 100%

### 经验公式对比 / Empirical Comparison

**推理公式适用条件** / Rational Method Applicability:
- 汇水面积 < 200 ha ✓
- 汇流时间 < 1 hour ✓
- 降雨均匀分布假设合理 ✓

**马斯京根参数校核** / Muskingum Parameter Check:
- 0 < x < 0.5 ✓ (x = 0.2)
- K > 0 ✓
- C0 + C1 + C2 = 1 ✓

### 工程合理性 / Engineering Reasonability

- ✅ 径流峰值滞后于降雨峰值 (汇流时间)
- ✅ 下游流量为上游叠加
- ✅ 河道演算产生削减和滞后效应
- ✅ 排水能力满足设计标准

---

## 参考文献 / References

### 技术标准 / Technical Standards

1. **GB 50014-2021**: 室外排水设计标准
2. **GB 50013-2018**: 室外给水设计标准
3. **CJJ 37-2012**: 城市道路工程设计规范
4. **GB/T 50378-2019**: 绿色建筑评价标准

### 学术文献 / Academic References

1. Chow, V. T., Maidment, D. R., & Mays, L. W. (1988). *Applied Hydrology*. McGraw-Hill.

2. Rossman, L. A. (2015). *Storm Water Management Model User's Manual, Version 5.1*. EPA.

3. Butler, D., & Davies, J. W. (2011). *Urban Drainage*. CRC Press.

4. Akan, A. O., & Houghtalen, R. J. (2003). *Urban Hydrology, Hydraulics, and Stormwater Quality*. John Wiley & Sons.

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
