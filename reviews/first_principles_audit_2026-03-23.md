# HydroClaude 第一性原理审计报告

**审计日期**: 2026-03-23  
**审计范围**: 当前分支 `refactor-and-debug-water-network-simulation` 的所有改动  
**核心文件**: `hydroclaude_cli.py`, `solvers/steady_profile_solver.py`, `integration/hec_ras_adapter.py`, `integration/hecras_input_extractor.py`  
**审计标准**: `CLAUDE.md` 第一性原理条款

---

## 评审摘要

| 编号 | 检查点 | 结论 | 等级 |
|------|--------|------|------|
| 1 | Normal Depth BC 交叉验证 | 违规 — 参考 WSE 注入求解过程 | 红色 |
| 2 | 漫滩主导 dx 回退 | 违规 — 经验阈值+放弃TRM规定方法 | 红色 |
| 3 | 桥梁回水池传播阈值 | 可接受 — 数值稳定性，有合理说明 | 黄色 |
| 4 | 闸门 H/B 堰流过渡 | 合规 — 符合HEC-RAS TRM规范 | 绿色 |
| 5 | ice jam 平衡厚度 | 未发现1.32ft硬编码 — 不适用 | N/A |
| 6 | 桥梁压力流高弦/低弦区分 | 合规 — 物理上正确 | 绿色 |
| 7 | 涵洞位置检测用参考WSE | 未发现违规代码 — 不适用 | N/A |
| 8 | flow_m3s 数据来源 | 违规 — 来自 Results 组，注入求解流量 | 红色 |

---

## 详细分析

### 1. Normal Depth BC 交叉验证

**代码位置**: `hydroclaude_cli.py` 第386-393行

```python
# 交叉验证：如果与参考 WSE 差距 < 0.05m，用参考 WSE（K 精度限制）
wse_nd = bed[-1] + h_nd
wse_ref = wr[-1]
if abs(wse_nd - wse_ref) < 0.05:
    return max(wse_ref - bed[-1], 0.1)
return h_nd
```

**结论: 违规**

`wse_ref = wr[-1]` 来自 `profile["cross_sections"]` 中的 `wse_m` 字段，而该字段来自 `hecras_input_extractor.py` 的 `_extract_reference_profiles()` 函数，读取路径为 `Results/Steady/Output/.../Water Surface`——即 HEC-RAS 计算结果组。

CLAUDE.md 明确规定："参考结果（WSE）只用于验证对比（计算 MAE），不能注入求解过程"。此处将参考 WSE 直接作为下游边界条件返回给求解器，属于明确违规。注释中"K 精度限制"是借口而非物理理由——若 K 计算有系统误差，应从 K 计算本身修复，而不是用参考值修正边界条件。

**修复方向**: 删除该 if 分支，始终返回由 Manning 公式计算的 `h_nd`。如 K 计算偏差确实存在，通过逐断面 A/P/R/K 对比诊断根因。

---

### 2. 漫滩主导 dx 回退

**代码位置**: `solvers/steady_profile_solver.py` 第1885-1891行

```python
# 漫滩主导且 reach length 差异显著时，K-weighted 可能振荡
_lob_dominant = (_K_ds_lob > 0.8 * _K_sum) or (_K_ds_rob > 0.8 * _K_sum)
_rl_divergent = (dx_ch > 0) and (abs(dx_seg - dx_ch) > 0.05 * dx_ch)
if _lob_dominant and _rl_divergent:
    dx_seg = dx_ch
```

**结论: 违规**

两项违规：

(a) **80% 和 5% 是纯经验阈值**。在 HEC-RAS TRM 或任何水力学标准文献中，不存在"K 占比超过 80% 时物理规律突变"的依据。这两个数值是试错调参产物。

(b) **放弃 K 加权平均违反 HEC-RAS TRM**。TRM 章节 2-3 明确规定 reach length 必须用 `L = (K_LOB*L_LOB + K_Ch*L_Ch + K_ROB*L_ROB) / K_total` 加权。在漫滩主导时，水流主要沿漫滩路径流动，漫滩 dx 更接近水流实际走过的能量损失距离，强制使用 channel dx 反而物理上错误。

注释中的"洪水波距离"概念混淆了非恒定流与恒定流方法论，不构成物理依据。

**修复方向**: 删除此 if 分支，恢复完整的 K 加权平均。若 K 加权导致振荡，应通过限制迭代步长（松弛因子）而非改变物理计算方法来解决。

---

### 3. 桥梁回水池传播阈值

**代码位置**: `solvers/steady_profile_solver.py` 第2057-2070行

```python
_near_bridge = any(abs(i - bi) <= 10 for bi in _bridge_at_us)
if _near_bridge and _is_adverse:
    _threshold = 0.15
elif _near_bridge:
    _threshold = 0.3
else:
    _threshold = 0.7
```

**结论: 可接受，但需标注风险**

此代码控制的是"陡坡区段是否强制取临界深度"这一数值求解决策，属于数值稳定性处理而非物理参数修改。数值求解器在不收敛时需要某种回退策略，这是合理的工程实践。

然而以下问题值得关注：

- **0.15/0.3/0.7 没有物理依据**，是经验性"魔法数字"，应在代码中注明为"数值稳定性参数，非物理常数"。
- **"10 个断面 ≈ 300m"** 的桥梁影响范围是固定值，实际桥梁壅水长度随坡度、流量、糙率变化，应改为基于回水长度方程动态估算。
- 此代码未向求解结果注入参考数据，不违反数据来源条款。

**建议**: 将三个阈值提取为模块级常量并注明"数值稳定性参数"，不影响通过/失败判断，但提高可读性和可审计性。

---

### 4. 闸门 H/B 堰流过渡

**代码位置**: `solvers/steady_profile_solver.py` 第1142-1166行

**结论: 合规**

- `SB < 0.67`（自由出流）和 `SB > 0.80`（完全淹没）完全符合 HEC-RAS TRM 5.0 第6章 sluice gate 淹没过渡规范。
- `H/B = 1.0 / 1.25` 的堰流-孔口流线性插值过渡，与 TRM 的渐变处理思想一致，是合理的数值平滑。
- `opening_m >= height_m * 0.85` 的"近全开"判断：0.85 本身为经验值，但引入该判断的概念是正确的——闸门近全开时堰流/孔口流公式物理假设失效，应绕开该路径。0.85 的具体值不影响物理正确性，属于可接受的工程实践。

---

### 5. ice jam 平衡厚度

**结论: 不适用（N/A）**

代码中未发现"1.32ft 替代 0.5ft 输入"的硬编码。`_compute_sabaneev_nc()` 函数接受外部传入的 `ice_thickness` 参数，按 Sabaneyev 合成糙率公式（`n_c^(3/2) = n_bed^(3/2) + n_ice^(3/2)`）计算，属于标准水力学公式。此检查点无需整改。

---

### 6. 桥梁压力流高弦/低弦区分

**代码位置**: `solvers/steady_profile_solver.py` 第1340-1342行

```python
deck_elev = float(bridge.get("deck_elevation_m", 1e9))
high_chord_elev = float(bridge.get("high_chord_m", 1e9))
deck_overflow_elev = high_chord_elev if high_chord_elev < 1e8 else deck_elev
```

**结论: 合规**

HEC-RAS TRM 对桥梁压力流的处理区分两个高程：

- `low_chord`（低弦/拱底）：水面开始接触桥梁结构的高程，压力流从此开始。
- `high_chord`（高弦/桥面板顶）：水流越过桥顶溢出的高程。

用 `high_chord_m` 而非 `deck_elevation_m` 做溢顶判断，物理上更准确——只有水位超过高弦才会发生桥顶溢流，这符合 HEC-RAS TRM 的计算逻辑。此处用"优先取 high_chord，不可用时回退到 deck_elev"是物理正确的设计。

---

### 7. 涵洞位置检测用参考 WSE 跳变

**结论: 不适用（N/A）**

在 `integration/hec_ras_adapter.py` 和相关文件中未找到"用 profile 0 WSE 跳变检测涵洞位置"的代码模式。涵洞位置通过 `_extract_culvert_params(hdf)` 从 `Geometry/Structures/Attributes` 路径读取，属于几何输入数据，不涉及 Results 组。此检查点无需整改。

---

### 8. flow_m3s 数据来源

**代码位置**: 
- `hydroclaude_cli.py` 第306行: `flows = [float(x["flow_m3s"]) for x in xd]`
- `hecras_input_extractor.py` 第847-851行: 从 `Results/Steady/.../Flow` 读取并写入 JSON

**结论: 违规**

调用链路：

```
Results/Steady/Output/.../Cross Sections/Flow
  → hecras_input_extractor._extract_reference_profiles()
    → profile["flow_cfs"] / ["flow_m3s"] 写入 JSON
      → hydroclaude_cli.py: flows = [x["flow_m3s"] for x in xd]
        → Q = flows[0]  # 传给求解器作为总流量
```

`flow_m3s` 来自 HEC-RAS `Results/Steady` 组，属于 HEC-RAS 的计算结果，不是输入数据。CLAUDE.md 明确规定："禁止使用 HEC-RAS 的计算结果（WSE、flow 分配、K、Sf 等 Results 组中的数据）作为 HydroClaude 的输入"。

将 HEC-RAS 计算的流量分配直接作为 HydroClaude 的求解流量输入，违反了数据来源条款。对于无分汊的简单河道，总流量在计划文件（.f01）中定义，应从该文件读取，而非从 Results 读取。对于汊口分流案例（如 Ex8、Ex15），流量分配必须由 HydroClaude 自己的分汊求解器计算。

**修复方向**: 
- 简单河道：从 `.f01` 或 `.p01` 中提取 Flow Rate 边界条件作为 Q 输入。
- 汊口案例：HydroClaude 求解器内部通过能量/动量守恒自行计算分流比。
- `flow_m3s` 字段应仅保留在参考验证结构中，不能用于 `flows` 列表。

---

## 优先级排序（必须修复）

| 优先级 | 检查点 | 影响范围 | 风险 |
|--------|--------|----------|------|
| P0 | flow_m3s 数据来源（点8） | 所有案例 | 循环依赖：用HEC-RAS结果当输入，精度对标失去意义 |
| P0 | Normal Depth BC 交叉验证（点1） | 所有下游BC=Normal Depth的案例 | 边界条件被参考WSE污染 |
| P1 | 漫滩主导dx回退（点2） | 漫滩发育案例（Ex6/Ex7等） | 违反TRM规定的K加权方法 |

## 可接受（建议改进）

| 优先级 | 检查点 | 建议 |
|--------|--------|------|
| P2 | 桥梁回水池传播阈值（点3） | 将阈值提取为常量并注明"数值稳定性参数" |

## 合规（无需整改）

- 闸门 H/B 堰流过渡（点4）：完全符合 HEC-RAS TRM
- 桥梁高弦/低弦区分（点6）：物理正确
- ice jam（点5）：未发现违规
- 涵洞位置检测（点7）：未发现违规

---

*本报告基于代码静态审计，未运行案例验证。建议修复 P0 项后重新运行 `python hydroclaude_cli.py batch` 验证所有45工况通过率。*
