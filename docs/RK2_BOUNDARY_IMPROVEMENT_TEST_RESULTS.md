# RK2边界处理改进测试结果

**日期**: 2025-10-29
**修改**: 只在RK2最后强制边界条件，不在中间步骤强制
**目的**: 减少边界强制导致的质量泄漏

---

## 📊 修改内容

### 代码修改

**文件**: `solvers/godunov_fvm_solver.py`

```python
# 原代码（step方法）:
# === 第1步：前向欧拉 ===
dh_dt, dQ_dt = self._compute_rhs(h_n, Q_n)
h_star = h_n + dt * dh_dt
Q_star = Q_n + dt * dQ_dt
h_star, Q_star = self._apply_bc(h_star, Q_star)  # ← 强制边界

# === 第2步：梯形修正 ===
dh_dt_star, dQ_dt_star = self._compute_rhs(h_star, Q_star)
self.h = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt_star
self.Q = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt_star
self.h, self.Q = self._apply_bc(self.h, self.Q)  # ← 强制边界
```

```python
# 新代码:
# === 第1步：前向欧拉 ===
dh_dt, dQ_dt = self._compute_rhs(h_n, Q_n)
h_star = h_n + dt * dh_dt
Q_star = Q_n + dt * dQ_dt
# ✗ 不在中间步骤强制边界条件

# === 第2步：梯形修正 ===
dh_dt_star, dQ_dt_star = self._compute_rhs(h_star, Q_star)
self.h = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt_star
self.Q = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt_star
self.h, self.Q = self._apply_bc(self.h, self.Q)  # ✓ 只在最后强制
```

### 理论依据

中间步骤的边界强制会"删除"通量演化产生的质量变化：

```
1. 通量计算：F[0]=10, F[1]=9.959 → 净流入单元0: 0.041 m³/s
2. 时间积分：h[0]应该增长
3. 边界强制：h[0]被重置为0.3 → 质量消失！
```

移除中间步骤强制，理论上应该减少质量泄漏。

---

## 📈 测试结果

### 测试1：诊断测试（Supercritical + h边界）

**设置**:
- 边界条件：左=supercritical (h=0.3, Q=10), 右=h (value=2.0)
- 单元数：50
- Manning n=0, Slope=0（无摩阻）

**结果**:

| 指标 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| 质量误差（10步） | 2.90% | 2.84% | ✓ 略有改善 (-0.06%) |
| 最终质量 | 11833.89 m³ | 11826.26 m³ | ✓ 略有改善 |

### 测试2：MacDonald Test 2（Q + h边界）

**设置**:
- 边界条件：左=Q (value=2.0 m³/s), 右=h (value=h_c)
- 渠道长度：5000 m
- 单元数：100
- Manning n=0.03, Slope=0.002

**结果**:

| 指标 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| 质量误差 | 33.17% | 33.17% | ✗ 无改善 |
| 流量守恒 | 失败 | 失败 | ✗ 无改善 |
| 平均流量 | ~1.85 m³/s | ~1.85 m³/s | ✗ 应为2.0 m³/s |

**具体数据**:
```
初始质量: 8075.30 m³
最终质量: 10753.51 m³
质量误差: 33.165362%

仿真统计:
  总步数: 682
  模拟时间: 3003.21 s

验证结果:
  ✅ 水面形态：正确
  ✅ Froude数分布：正确
  ✅ 下游边界：正确
  ✗ 流量守恒：1.848 ≠ 2.000
  ✗ 质量守恒：33% 误差
```

### 测试3：MacDonald Test 4（Supercritical + h边界）

**状态**: 已标记skip，误差61%（未在本次测试）

---

## 🔍 分析与结论

### 发现

1. **对Supercritical边界有微小改善**
   - 质量误差从2.90%降到2.84%
   - 改善幅度小（0.06%），未达到<1%目标

2. **对Q边界无效**
   - MacDonald Test 2质量误差仍为33%
   - 流量守恒失败（Q_avg=1.85 vs 目标2.0）

3. **不同边界类型有不同问题**
   - Supercritical边界：质量误差~3%
   - Q边界：质量误差~33%
   - 问题根源可能不同

### 结论

**RK2中间步骤的边界强制不是主要问题**

虽然理论上移除中间步骤强制可以减少质量泄漏，但实际效果：
- ✓ 对supercritical边界有微小改善（0.06%）
- ✗ 对Q边界完全无效（仍为33%误差）

这说明：
1. Supercritical边界的质量泄漏部分来自RK2强制，但这不是主因
2. Q边界的质量守恒问题有其他根源，可能与流量边界的实现方式有关

---

## 🎯 下一步研究方向

### 优先级P0：调查Q边界的质量泄漏

Q边界的33%误差远超supercritical边界的2.8%，应该是主要问题。

**可能原因**:
1. Q边界的ghost cell设置不当
2. Q边界单元的通量计算有误
3. Q边界与相邻单元的通量不匹配

**调查方法**:
- 创建专门的Q边界诊断测试
- 检查Q边界的ghost cell值
- 分析Q边界单元与相邻单元的通量平衡

### 优先级P1：改进Supercritical边界（2.8% → <1%）

虽然已有改善，但仍未达标。

**可能方案**:
1. Riemann invariants方法（基于特征分解）
2. 虚拟单元法（边界单元不参与质量守恒）
3. 通量修正法（调整边界通量）

### 优先级P2：系统化的边界处理框架

目前的边界处理是"临时补丁"式的。需要：
1. 文献调研（SWASHES, Basilisk, ANUGA等）
2. 设计统一的边界处理框架
3. 为每种边界类型实现严格的质量守恒

---

## 📚 参考

相关文档：
- `BOUNDARY_CONDITION_MASS_CONSERVATION.md` - 深度分析报告
- `MASS_CONSERVATION_INVESTIGATION.md` - 初步调查

诊断工具：
- `tests/diagnostic/test_mass_flux_analysis.py`
- `tests/diagnostic/test_ghost_cell_consistency.py`
- `tests/diagnostic/test_boundary_evolution.py`

---

*本文档记录了2025-10-29 RK2边界处理改进方案的测试结果*
