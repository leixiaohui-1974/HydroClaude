# 明渠串联闸泵群系统模拟 - 稳定性问题诊断报告

**日期**: 2025-10-23
**分析工具**: StabilityEvaluator + 详细纵剖面分析
**总体评分**: 89.7/100 (稳定)

---

## 执行摘要

通过使用基础库的`StabilityEvaluator`进行数值稳定性评估，发现了两个关键问题：

1. **闸门处空间尖峰** ⚠️ 中等严重性
2. **泵站扬程未实现** ❌ 高严重性（物理模型缺陷）

虽然总体稳定性评分为89.7/100（稳定），但存在物理建模不完整的问题。

---

## 问题1：闸门处检测到空间尖峰

### 🔍 问题描述

在Gate1和Gate2位置检测到显著的空间振荡：

| 位置 | 二阶差分值 | 状态 |
|------|-----------|------|
| 24.6 km (Gate1上游) | +0.01965 m | 超过3σ阈值 |
| 24.8 km (Gate1处) | -0.03986 m | **最大尖峰** |
| 25.0 km (Gate1下游) | +0.01965 m | 超过3σ阈值 |
| 74.6 km (Gate2上游) | +0.01968 m | 超过3σ阈值 |
| 74.8 km (Gate2处) | -0.03989 m | **最大尖峰** |

### 📊 稳定性指标

- **振荡指数**: 0.010390（略高于优秀标准0.01）
- **空间尖峰数量**: 6个
- **最大二阶差分**: 0.03989 m
- **标准差**: 0.00308 m

### 🔬 原因分析

1. **物理原因**：
   - 闸门造成的水位跃变（上下游水深差约0.012 m）
   - 淹没出流条件下的局部水力跃迁

2. **数值原因**：
   - 网格分辨率（Δx=200 m）可能不足以精细捕捉结构物附近的陡变
   - 结构物边界条件处理导致的局部振荡

### ✅ 评估结论

- **稳定性**: 可接受（尖峰幅度<0.04m，相对于平均水深3.3m仅1.2%）
- **物理合理性**: 合理（闸门确实会造成水位变化）
- **数值精度**: 良好（振荡未发散，保持在小范围内）

---

## 问题2：泵站扬程未正确实现（严重缺陷）

### ❌ 问题描述

**泵站参数**：
- 额定流量：30.0 m³/s
- **额定扬程：5.0 m**（关键参数）
- 最小吸入水头：2.0 m

**物理预期**：
- 泵站应该提升水位
- 下游水位 = 上游水位 + 扬程（5.0 m）
- 泵前水位应该**低于**泵后水位

**实际观察**：
- 泵站处（50 km）：
  - 上游水深（-1km）：3.3121 m
  - 泵站处水深：3.3061 m
  - 下游水深（+1km）：3.3001 m
- **水深跃变仅0.012 m**（应该是5.0 m的扬程！）
- 泵站前后水位**下降**而非上升

### 🐛 代码缺陷定位

#### 1. PumpStation类 (`solvers/gate.py:731-853`)

```python
class PumpStation(HydraulicStructure):
    def __init__(self, ..., rated_head: float = 5.0, ...):
        ...
        self.rated_head = rated_head  # ✅ 扬程已存储

    def calculate_discharge(self, h_upstream, h_downstream, t):
        ...
        # ❌ 问题：只计算流量，没有应用扬程！
        if h_upstream >= self.min_suction_head:
            discharge = self.rated_flow  # 只返回流量
            flow_type = 'rated'
        ...
        return discharge, flow_type
        # ❌ 缺失：没有修改下游水位
```

**缺陷**：泵站类只计算流量，**没有机制来提升水位**。

#### 2. HydrostaticCanalSolver (`solvers/hydrostatic_canal_solver.py:348-408`)

```python
def _apply_internal_bc(self, t, Q_target, ...):
    """应用内部边界条件（闸门等水工建筑物）"""

    for idx, structure in zip(self.structure_indices, self.structure_objects):
        h_up = self.h[idx - 1]
        h_down = self.h[idx + 1]

        # ✅ 计算流量
        Q_gate_current, _ = structure.calculate_discharge(h_up, h_down, t)

        # ✅ 调整上游水深以满足流量约束
        residual = Q_target - Q_gate_current
        dQ_dh_up, dQ_dh_down = structure.calculate_discharge_derivatives(...)
        if abs(dQ_dh_up) > 1e-6:
            dh_up = residual / dQ_dh_up
            self.h[idx - 1] = h_up + relax * dh_up

        # ❌ 缺失：没有应用泵站扬程！
        # 应该添加：
        # if isinstance(structure, PumpStation):
        #     self.h[idx + 1] = self.h[idx - 1] + structure.rated_head
```

**缺陷**：求解器只确保流量守恒，**完全忽略了泵站的扬程**。

### 🔧 修复方案

#### 方案A：在`_apply_internal_bc`中添加泵站扬程逻辑

```python
def _apply_internal_bc(self, t, Q_target, ...):
    for idx, structure in zip(self.structure_indices, self.structure_objects):
        h_up = self.h[idx - 1]
        h_down = self.h[idx + 1]

        # 计算流量并调整水深
        Q_current, _ = structure.calculate_discharge(h_up, h_down, t)
        residual = Q_target - Q_current

        # 调整上游水深（所有结构物）
        dQ_dh_up, _ = structure.calculate_discharge_derivatives(h_up, h_down, t)
        if abs(dQ_dh_up) > 1e-6:
            dh_up = residual / dQ_dh_up
            self.h[idx - 1] = h_up + relax * dh_up

        # 🔧 新增：应用泵站扬程
        if isinstance(structure, PumpStation) and structure.is_running:
            # 泵站下游水位 = 上游水位 + 扬程
            self.h[idx + 1] = self.h[idx - 1] + structure.rated_head
```

#### 方案B：在PumpStation类中添加`get_head_rise`方法

```python
class PumpStation(HydraulicStructure):
    ...
    def get_head_rise(self) -> float:
        """
        返回泵站扬程

        Returns:
            扬程 (m)
        """
        if self.is_running:
            return self.rated_head
        else:
            return 0.0
```

然后在求解器中检查结构物是否有`get_head_rise`方法并应用。

### ⚠️ 影响评估

#### 对当前结果的影响

1. **水位分布错误**：
   - 泵站后应该有5m水位抬升
   - 整个下游段（50-100 km）水位应该整体抬高5m
   - 当前模拟的水位分布**不符合物理实际**

2. **闸门2工作点错误**：
   - 闸门2的上游水位应该更高（+5m）
   - 闸门2的流量计算基于错误的水位
   - 闸门2可能处于错误的流态（淹没/自由）

3. **流量守恒正确性**：
   - ✅ 流量守恒仍然满足（误差1.17%）
   - ❌ 但基于错误的水位分布

#### 对瞬态模拟的影响

1. **波动传播错误**：
   - 泵站应该改变上下游的波速关系
   - 当前模拟的波动传播特性不准确

2. **能量不守恒**：
   - 泵站应该增加系统总能量（5m扬程×流量）
   - 当前模拟**漏掉了泵站做功的能量**

---

## 综合评估

### 数值稳定性：✅ 良好 (89.7/100)

| 指标 | 值 | 标准 | 评价 |
|-----|-----|------|------|
| 振荡指数 | 0.010390 | <0.01优秀 | ⚠️ 略高 |
| 质量守恒误差 | 1.17% | <5%优秀 | ✅ 优秀 |
| 物理合理性 | 1.000 | >0.9优秀 | ✅ 优秀 |
| 收敛性指数 | 0.500 | >0.8优秀 | ⚠️ 一般 |

### 物理建模完整性：❌ 不完整

- **流量模型**：✅ 正确（闸门、泵站流量计算正确）
- **水位模型**：❌ 不完整（泵站扬程未实现）
- **能量模型**：❌ 缺失（泵站做功未计入）

---

## 建议措施

### 紧急措施（必须修复）

1. **实现泵站扬程逻辑**
   - 在`_apply_internal_bc`中添加泵站水位提升
   - 确保下游水位 = 上游水位 + 扬程
   - 测试稳态和瞬态情况

2. **验证修复效果**
   - 检查泵站前后水位差是否为5m
   - 验证闸门2的流态是否改变
   - 重新运行稳定性评估

### 优化措施（可选）

1. **减少闸门处振荡**
   - 增加空间网格分辨率（nx: 501 → 1001）
   - 使用更平滑的结构物边界处理
   - 调整松弛因子（relax: 0.5 → 0.3）

2. **提高收敛性**
   - 增加瞬态模拟时长（1小时 → 2小时）
   - 减小时间步长（dt: 1.0 → 0.5秒）
   - 使用更严格的收敛容差

3. **完善物理模型**
   - 考虑泵站效率曲线（非恒定扬程）
   - 添加泵站启停的瞬态过程
   - 考虑水锤效应

---

## 结论

1. **数值稳定性**：模拟结果在数值上是稳定的（89.7/100），闸门处的小幅振荡在可接受范围内。

2. **物理建模缺陷**：泵站扬程未实现是一个**严重的物理建模错误**，导致当前结果不符合实际。

3. **优先级**：
   - **P0（必须）**：修复泵站扬程缺陷
   - **P1（重要）**：减少闸门处振荡
   - **P2（可选）**：完善物理模型

4. **后续行动**：需要立即修复泵站扬程逻辑，然后重新运行模拟并重新评估稳定性。

---

**分析人员**: Claude
**审核状态**: 待修复
**下次评估**: 修复后重新运行`analyze_stability.py`
