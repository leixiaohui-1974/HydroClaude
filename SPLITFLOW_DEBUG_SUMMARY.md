# Split-Flow Method 调试总结

## 日期
2026-03-21

## 已完成的修复

### 1. 混合流检测改进 ✓
**问题**：亚临界求解器计算的水深过大，导致 Froude 数偏小，混合流检测失败

**修复**：增加基于坡度的检测
- 检测 1：Froude 数 > 1（原有逻辑）
- 检测 2：陡坡段（S0 > Sc）（新增）
- 混合流标志 = 检测1 OR 检测2

**结果**：混合流检测成功触发 ✓

### 2. 超临界剖面能量方程修复 ✓
**问题**：局部损失符号错误，导致超临界水深过大

**修复前**：
```python
W_new = W_super[i - 1] + vh_us - vh_ds - dx_seg * Sf_avg + h_minor
```

**修复后**：
```python
W_new = W_super[i - 1] + vh_us - vh_ds - dx_seg * Sf_avg - h_minor
```

**结果**：超临界剖面计算改进，水深从 1.256 m 降到 1.138 m ✓

## 当前问题

### 问题：水跃位置过早
**现象**：
- 水跃定位在第 1 个断面（紧邻控制断面）
- 只有第 0 个断面是超临界，其余全是亚临界
- 最终 Froude 数最大值 0.930 < 1.0

**根本原因**：亚临界剖面在上游断面计算错误
```
断面 0: h_sub = 1.015 m
断面 1: h_sub = 1.015 m  ← 完全相同！
断面 2: h_sub = 1.015 m  ← 完全相同！
```

这导致：
1. 亚临界动量函数 M_sub 在前3个断面完全相同（9.586）
2. 超临界动量函数 M_sup 正常变化（8.000 → 10.273 → 13.454）
3. 动量函数差 delta_m 在第 0-1 断面之间发生符号变化
4. 水跃被错误地定位在第 1 个断面

### 问题分析

亚临界求解器（Standard Step Method）从下游向上游推进：
1. 下游边界条件：h_downstream = 1.454 m（正常深度）
2. 向上游推进时，水深应该逐渐变化
3. 但实际上前3个断面水深完全相同（1.015 m）

可能的原因：
1. **上游边界效应**：求解器在上游断面遇到数值问题
2. **迭代未收敛**：Standard Step 迭代在上游断面没有正确收敛
3. **床坡效应**：陡坡段导致能量方程求解困难

## 下一步修复方案

### 方案 A：改进亚临界求解器（推荐）
1. 检查 Standard Step Method 在陡坡段的数值稳定性
2. 改进上游断面的迭代初值
3. 增加迭代次数或调整收敛准则

### 方案 B：改进水跃定位逻辑
1. 排除亚临界剖面异常的断面
2. 使用更鲁棒的水跃判断准则（如 Froude 数跳变）
3. 增加水跃位置的合理性检查

### 方案 C：完整实现 HEC-RAS Split-Flow Method
1. 参考 HEC-RAS 手册的完整算法
2. 实现正常深度边界条件
3. 实现自动混合流检测

## 验证标准

根据 `MIXED_FLOW_VALIDATION_SUMMARY.md`：

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 混合流检测 | 触发 | ✓ 通过 |
| 超临界区识别 | 存在 | ✗ 失败（只有1个断面） |
| 水跃检测 | 正确位置 | ✗ 失败（位置过早） |
| 超临界区 MAE | < 0.1 m | N/A（无超临界区） |
| 总体 MAE | < 0.15 m | ✓ 通过（0.1172 m） |

## 调试输出示例

```
[DEBUG] Mixed Flow: control_sections = [0]
[DEBUG] Control section 0: bed=21.336, y_c=0.819, W_control=22.155
[DEBUG] Supercritical BC: control_idx=0, y_c=0.819, h_BC=0.778, W_BC=22.114
[DEBUG] Supercritical step 1: W_trial=22.064, W_new=22.169, h=1.138, y_c=0.819
[DEBUG] Supercritical profile computed: control_idx=0, seg_end=18
[DEBUG] W_super[0:19] = [22.114 22.117 22.067 22.017 21.967 21.917 ...]
[DEBUG] Jump search 0: h_sub=1.015, h_sup=0.778, M_sub=9.586, M_sup=8.000, delta=1.587
[DEBUG] Jump search 1: h_sub=1.015, h_sup=1.086, M_sub=9.586, M_sup=10.273, delta=-0.686
[DEBUG] Jump search 2: h_sub=1.015, h_sup=1.340, M_sub=9.586, M_sup=13.454, delta=-3.868
[DEBUG] Jump at idx=1 (sign change: 1.587 -> -0.686)
[DEBUG] Hydraulic jump located: jump_idx=1
```

## 修改的文件

- `solvers/steady_profile_solver.py`
  - 第 917-945 行：混合流检测逻辑（增加陡坡检测）
  - 第 1141 行：超临界能量方程（修复局部损失符号）
  - 多处添加调试输出

## 参考文献

1. HEC-RAS Hydraulic Reference Manual (Chapter 2: Basic Water Surface Profiles)
2. `MIXED_FLOW_VALIDATION_SUMMARY.md` - 问题诊断报告
3. `SPLITFLOW_FIX_SUMMARY.md` - 修复方案文档

---

**调试日期**: 2026-03-21
**状态**: 进行中
**下一步**: 修复亚临界求解器在上游断面的计算问题
