# HydroClaude 桥梁壅水计算精度问题技术分析报告

**文档编号：** HC-BRIDGE-2026-001  
**版本：** v1.0  
**日期：** 2026-03-21  
**适用范围：** Beaver Creek 桥梁案例（HEC-RAS Example 2）  

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [测试案例与桥梁参数](#2-测试案例与桥梁参数)
3. [壅水计算误差汇总](#3-壅水计算误差汇总)
4. [根本原因详细技术分析](#4-根本原因详细技术分析)
5. [代码层面问题定位](#5-代码层面问题定位)
6. [修复建议](#6-修复建议)
7. [暂未解决的 TODO](#7-暂未解决的-todo)

---

## 1. 执行摘要

HydroClaude 在对 HEC-RAS Example 2（Beaver Creek 桥梁案例）进行稳态水面线计算时，
桥梁壅水（backwater）计算结果与 HEC-RAS 参考解之间存在显著偏差，误差随流量工况呈非线性变化：

| 工况 | Q (m3/s) | HEC-RAS 壅水 (m) | HydroClaude 壅水 (m) | 绝对误差 (m) | 相对误差 |
|:---|:---:|:---:|:---:|:---:|:---:|
| 25 yr | 141.58 | 0.0871 | 0.2204 | **+0.1333** | +153% |
| 100 yr | 283.17 | 0.1987 | 0.1700 | **-0.0287** | -14% |
| May 74 flood | 396.44 | 0.5673 | 0.1568 | **-0.4105** | **-72%** |

**最严重缺陷：** May 74 flood 工况，HEC-RAS 壅水 0.567 m，HydroClaude 仅 0.157 m，
误差 **-0.41 m（-72.3%）**，已严重超出工程可接受阈值。

**根本原因优先级汇总：**

| 优先级 | 问题 | 影响工况 | 误差贡献估计 |
|:---:|:---|:---:|:---:|
| P1 | 桥面板溢顶堰流（Deck Overtopping）计算完全缺失 | May 74 | ~-0.35 m |
| P2 | 溢顶时过水面积计算物理不正确（全量 Q 过孔） | May 74 | 与 P1 耦合 |
| P3 | 下游断面误差向上游传播，抬高基准水位 | 全部 | ~+-0.1-0.6 m |
| P4 | 动量法 C_D=2.0 与 HEC-RAS pier_loss_coef=0 不一致 | 25 yr | ~+0.05-0.1 m |
| P5 | 全局水面线系统性偏高（mean_bias 约 +0.33 m） | 全部 | ~+0.3 m |
| P6 | _bridge_at_us 索引映射（已验证正确，排除为问题原因） | — | 0 |

---

## 2. 测试案例与桥梁参数

### 2.1 桥梁几何参数

| 参数 | 值 | 单位 |
|:---|:---:|:---:|
| 桥面板顶高程 (deck_elevation_m) | 65.7454 | m |
| 桥底低弦高程 (low_chord_elevation_m) | 60.9600 | m |
| 桥孔净高 (opening_height_m) | 4.7854 | m |
| 桥长沿水流方向 (bridge_length_m) | 9.1440 | m |
| 桥墩数量 (n_piers) | 9 | 根 |
| 桥墩总宽 (total_pier_width_m) | 6.8580 | m |
| 桥墩阻力系数 pier_loss_coef（HEC-RAS HDF） | **0.0** | — |
| 收缩损失系数 contraction_coef（HEC-RAS HDF） | **0.0** | — |
| 扩展损失系数 expansion_coef（HEC-RAS HDF） | **0.0** | — |

### 2.2 桥梁开口断面形状（bridge_opening_stations/elevations）

桥梁开口轮廓是完整河道断面在桥址处的投影，分三个区段：

| 区段 | 桩号范围 (m) | 控制高程 (m) | 物理含义 |
|:---|:---:|:---:|:---|
| 左侧滩地 | 0 – 137.16 | 60.96 | 低弦高程，开放过流区 |
| **桥面板跨度** | **137.16 – 197.21** | **65.7454** | **桥面板顶，溢顶堰流控制区** |
| 右侧滩地 | 197.21 – 609.60 | 60.96 | 低弦高程，开放过流区 |

**衍生关键参数：**

- 桥面板跨度 L_deck = 197.21 - 137.16 = **60.05 m**（堰流计算所需，**当前代码未提取**）
- 有效开口宽度（低弦以下）= 549.55 m
- 净开口宽度（扣除桥墩）= 542.69 m
- 桥墩阻塞率 = 6.858 / 549.55 ≈ **1.25%**（极低，桥墩不是主要阻力源）

### 2.3 各工况水流状态判定

| 工况 | Q (m3/s) | HEC-RAS US WSE (m) | 与桥面板关系 | 流态 |
|:---|:---:|:---:|:---|:---|
| 25 yr | 141.58 | 64.9314 | 低于桥面板 0.81 m | 桥孔压力流 |
| 100 yr | 283.17 | 65.5496 | 低于桥面板 0.196 m | 接近满管压力流 |
| May 74 flood | 396.44 | **66.2755** | **超出桥面板 0.5302 m** | **溢顶流 + 压力流** |

---

## 3. 壅水计算误差汇总

### 3.1 桥位断面误差对比（May 74 flood 重点）

| 断面 | 位置 | HEC-RAS WSE (m) | HC WSE (m) | 误差 (m) |
|:---|:---:|:---:|:---:|:---:|
| XS 5.41 | 桥上游（US face） | 66.2755 | 66.5278 | +0.252 |
| XS 5.39 | 桥下游（DS face） | 65.7083 | 66.3710 | **+0.663** |
| 壅水 (US - DS) | — | **0.5673** | **0.1568** | **-0.410** |

**关键异常：** DS 断面误差（+0.663 m）大于 US 断面误差（+0.252 m），
导致上下游水位差（壅水）被大幅压缩。这说明 **HC 桥下游基准水位被严重高估**。

### 3.2 全剖面误差分布（May 74 flood，从下游到上游）



### 3.3 误差随流量的变化规律

壅水误差在溢顶临界点前后发生质变：



误差随流量增大从正偏转为负偏，在溢顶流态下急剧恶化，
清晰指向**溢顶堰流模型缺失**为主导原因。

---

## 4. 根本原因详细技术分析

### 4.1 原因 P1：桥面板溢顶堰流计算完全缺失（最关键缺陷）

#### 4.1.1 物理机制

当 WSE_US > deck_elevation 时，HEC-RAS 按**复合流态**处理，将总流量分解为：



参数含义：

- C_w ≈ 1.66 m^(1/2)/s（广顶堰流量系数，公制单位）
- L_deck = 60.05 m（**桥面板跨度，从 bridge_opening_stations 可推导，当前代码未提取**）
- H_over = WSE_US - deck_elevation（超出桥面板的水头）

#### 4.1.2 May 74 flood 工况的堰流定量估算



HydroClaude 将全量 396.44 m³/s 强制通过桥孔，物理上是错误的。
桥孔面积很大（约 2600 m²），即使流量偏大，流速也极低（约 0.15 m/s），
导致动量差极小，无法产生足够的壅水。

### 4.1.3 溢顶时桥孔面积的不连续性

从 bridge_opening_stations 计算各 WSE 下的过流面积：

| WSE (m) | 过流面积 (m2) | 过流宽度 (m) | 说明 |
|:---:|:---:|:---:|:---|
| 65.708 | 2609 | 549.5 | DS WSE，略低于桥面板 |
| 65.745 | 2630 | 549.5 | 恰到桥面板高程 |
| 66.000 | 2785 | 609.6 | 超出桥面板 0.25m，宽度突增 60m |
| 66.276 | 2953 | 609.6 | US HEC-RAS WSE |

NaturalSection 正确体现了桥面板高程处的面积不连续跳变，
但 HydroClaude 把桥面板以上的面积也算作过流面积（仅面积扣减），
而 HEC-RAS 将桥面板以上部分处理为独立堰流通道（有独立水力损失方程）。

### 4.1.4 误差随流量变化的验证

| 工况 | WSE_US vs 桥面板 | 溢顶状态 | 壅水误差 |
|:---|:---:|:---:|:---:|
| 25 yr | 低于 0.81 m | 无溢顶 | +0.133 m（正偏）|
| 100 yr | 低于 0.196 m | 无溢顶（临界）| -0.029 m（几乎准确）|
| May 74 | **高于 0.530 m** | **溢顶** | **-0.410 m（严重低估）**|

误差在溢顶临界点前后发生质变，强有力地证实堰流缺失是主导误差源。

### 4.2 原因 P2：溢顶时过水面积计算物理不正确

HEC-RAS 的正确处理：
1. 用 Q_under 通过桥孔面积计算孔流速度和动量/能量
2. 用 Q_weir = Q_total - Q_under 约束堰流水头
3. 两者联立满足连续方程 Q_total = Q_under + Q_weir

HydroClaude 动量法路径的问题（，约第 426-539 行）：

EGL 壅水判断仅用于面积扣减，速度计算仍使用全量 Q：



HydroClaude 能量法路径的同样问题（，约第 541-683 行）：



### 4.3 原因 P3：下游断面误差传播

标准步法从下游边界向上游推进，各断面误差逐步积累。
May 74 flood 中，桥梁 DS 面的输入水位：

- HC 计算值：W[XS_5.39] = 66.3710 m
- HEC-RAS 参考：65.7083 m
- 误差：+0.663 m（严重偏高）

这一偏高的下游基准传入桥梁动量方程，使求解的 US WSE 也偏高，
但 DS 偏高幅度（+0.663 m）大于 US 偏高幅度（+0.252 m），
净效果是壅水（US - DS）被大幅压缩。

**量化说明：** 如果 HC 的 DS WSE 误差为 0（即 DS 基准正确），
则 HC 壅水将从 0.157 m 增加到约 0.157 + (0.663 - 0.252) = 0.568 m，
接近 HEC-RAS 的 0.567 m。这说明桥梁本身的计算精度在下游基准正确时
其实非常接近 HEC-RAS，主要误差来自 DS 基准偏高对壅水差值的压缩。

### 4.4 原因 P4：动量法 C_D 与 HEC-RAS pier_loss_coef 不一致

代码中（第 462 行）：



HEC-RAS HDF 数据：pier_loss_coef = 0.0

在当前 Beaver Creek 案例（流速约 0.15 m/s）中，桥墩拖曳力仅约 0.001% 的总压力，
影响可忽略。但在高流速或大桥墩情况下将产生明显误差，建议修复以保持参数一致性。

### 4.5 原因 P5：全局水面线系统性偏高

| 工况 | MAE (m) | RMSE (m) | mean_bias (m) |
|:---|:---:|:---:|:---:|
| 25 yr | 0.431 | 0.478 | +0.334 |
| 100 yr | 0.477 | 0.520 | +0.378 |
| May 74 flood | 0.408 | 0.447 | +0.326 |

全局约 +0.33 m 的系统性正偏差，可能原因：

1. **HEC-RAS Ineffective Flow Area**：HEC-RAS 将洪泛区部分区域标记为无效流动，
   有效减小过流面积，使水位更高；HydroClaude 未实现此功能
2. **NaturalSection 有效流动面积修正差异**
3. **LOB/ROB 分区 Manning n 加权公式差异**

### 4.6 原因 P6： 索引映射验证（已排除）

从 validation_results_beavcrek.json 确认：
us_rs=5.41 正确映射到 us_xs_index=7，ds_rs=5.39 正确映射到 ds_xs_index=8。
当求解到 i=7 时，i in _bridge_at_us 为 True，正确触发桥梁计算分支。
**结论：索引映射机制正确，排除为问题原因。**

---

## 5. 代码层面问题定位

### 5.1  的核心缺陷

**文件：** solvers/steady_profile_solver.py，第 426-539 行

**缺陷 1：完全缺少溢顶检测和堰流分流逻辑。**
在 40 次 Newton-Raphson 迭代中，完全没有检查 W3_trial > deck_elev 的情况。
即使最终收敛的 W3_trial 超过桥面板，代码也不会触发堰流计算。

**缺陷 2：C_D 硬编码 2.0，与 HEC-RAS pier_loss_coef=0 不一致（第 462 行）。**

### 5.2  的溢顶处理不完整

**文件：** solvers/steady_profile_solver.py，第 541-683 行

 函数（第 617-619 行）有面积扣减逻辑，但能量方程中
仍使用全量 Q 计算速度（第 635-636 行），未实现真正的流量分流。

### 5.3  缺少 deck_span_m 字段

**文件：** integration/hec_ras_adapter.py，第 1165-1341 行

当前已提取 bridge_opening_stations/elevations（第 1237-1238 行），
但未推导 deck_span_m（桥面板跨度），这是实现堰流计算的必要前置数据。

### 5.4 主循环桥梁调用位置（第 860-872 行）

桥梁动量方程以 W[i+1] 为已知下游水位，
但 W[i+1] 是 HC 自己计算的值，对于 May 74 flood 已有 +0.663 m 偏差。
这一误差传导至桥 US 面，但压缩了壅水差值。

---

## 6. 修复建议

### 修复 P1（最高优先级）：实现桥面板溢顶堰流分流计算

**步骤 1：** 在 integration/hec_ras_adapter.py 的 _extract_bridge_params() 中
推导并存储 deck_span_m（约在第 1237 行之后添加）：

从 bridge_opening_elevations 中找出控制高程接近 deck_elev 的区段，
累加其横向长度即为 L_deck（桥面板跨度），存入 bridge_dict["deck_span_m"]。

**步骤 2：** 在 _solve_bridge_momentum() 的迭代循环内，每步先计算堰流分流：

伪代码逻辑：


**步骤 3：** 在 _solve_bridge_energy() 中同样实现，使 V2、V3 使用 Q_under。

**预期效果：** May 74 flood 壅水误差从 -0.410 m 减小至约 -0.05 m 以内；
25 yr、100 yr 工况不受影响（无溢顶时 Q_weir=0）。

### 修复 P4：pier_loss_coef 到动量法 C_D 的映射

在 _solve_bridge_momentum() 中：当 pier_loss_coef=0 时，将 C_D 设为 0，
避免与 HEC-RAS 能量法参数定义不一致。

### 修复 P5（需独立调查）：全局水面线系统性偏高

1. 在 HEC-RAS HDF 中查找 Ineffective Flow Area 数据
2. 实现无效流动区域屏蔽，减小有效过流面积
3. 对比修复前后的全局 mean_bias

---

## 7. 暂未解决的 TODO

| 编号 | 优先级 | 说明 | 涉及文件 |
|:---|:---:|:---|:---|
| TODO-B01 | P1 必须 | 在 _solve_bridge_momentum() 中实现溢顶堰流分流计算 | steady_profile_solver.py |
| TODO-B02 | P1 必须 | 在 _solve_bridge_energy() 中实现溢顶堰流分流计算 | steady_profile_solver.py |
| TODO-B03 | P1 必须 | 在 _extract_bridge_params() 中提取 deck_span_m 字段 | hec_ras_adapter.py |
| TODO-B04 | P1 需确认 | 验证 May 74 flood 溢顶是自由堰流还是淹没堰流 | — |
| TODO-B05 | P4 应修复 | pier_loss_coef=0 时动量法 C_D 应设为 0 | steady_profile_solver.py |
| TODO-B06 | P5 需调查 | 调查全局 mean_bias 约 +0.33 m 的根本原因（候选：Ineffective Flow Area）| hec_ras_adapter.py |
| TODO-B07 | 架构建议 | 抽取公共函数 _compute_bridge_flow_split() 供两种方法共享 | steady_profile_solver.py |
| TODO-B08 | 测试 | 添加回归测试：验证溢顶检测逻辑（4 个场景）| tests/test_bridge_overtopping.py |

---

## 参考资料

1. US Army Corps of Engineers (2016). HEC-RAS Hydraulic Reference Manual, Version 5.0, Chapter 5: Bridges.
2. US Army Corps of Engineers (2016). HEC-RAS Users Manual, Section 6: Bridge Hydraulic Computations.
3. Chaudhry, M.H. (2008). Open Channel Hydraulics, 2nd Ed., Chapter 13: Bridge Flow.
4. Hydraulic Engineering Circular No. 18: Evaluating Scour at Bridges.

---

*报告生成于 2026-03-21，基于 validation_results_beavcrek.json 数据及代码静态分析。*
