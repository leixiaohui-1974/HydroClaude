# 边界条件与质量守恒问题深度分析

**日期**: 2025-10-29
**状态**: 🟡 部分解决，需要进一步研究
**影响**: MacDonald Test 2和4的质量守恒误差2-3%

---

## 🎯 问题总结

通过6个诊断测试的深入分析，发现质量守恒问题的**根本原因**：

**在RK2时间积分中，边界单元的通量演化与边界条件强制产生冲突，导致质量"泄漏"**

---

## 🔬 核心发现

### 1. Ghost Cell与Riemann求解器 ✅ 正确

**测试**: `test_ghost_cell_consistency.py`

```
边界设置: supercritical, h=0.3m, Q=10m³/s

Ghost cell:     h_ext[0] = 0.3000, Q_ext[0] = 10.0000
边界单元:       h_ext[1] = 0.3000, Q_ext[1] = 10.0000
差异:           Δh = 0.000000, ΔQ = 0.000000  ✓

HLL通量:        F[0] = 10.000000 m³/s  ✓
理论通量:       F_theory = 10.000000 m³/s
误差:           0.00%  ✓✓✓
```

**结论**: Ghost cell设置正确，Riemann求解器计算的边界通量精确匹配边界条件。

### 2. 内部界面通量 ⚠️ 物理正确但引发质量泄漏

**测试**: `test_flux_values.py`

```
界面0 (ghost|单元0):    F[0] = 10.000 m³/s  ← 边界通量 ✓
界面1 (单元0|单元1):    F[1] =  9.959 m³/s  ← 内部通量
净流入单元0:            ΔF  =  0.041 m³/s
→ dh[0]/dt = 0.002 m/s (应该使h[0]增长)
→ 但边界条件强制 h[0]=0.3 (固定)
→ 质量泄漏 = 0.412 m³/s ❌
```

**关键观察**:
- F[1] < F[0] 是**物理正确的**（因为单元1的h=0.5 > 单元0的h=0.3，存在压力梯度）
- 在无摩阻、水平床情况下，初始条件不是稳态，质量会重新分布
- 但这个重分布被边界条件强制"阻止"了

### 3. 质量泄漏机制 ❌ 确认

**在每个RK2步骤**:
```python
# 第1步：计算RHS
dh_dt[0] = -(F[1] - F[0]) / dx = -(9.959 - 10.0) / 20 = +0.002 m/s

# 第2步：更新状态
h_star[0] = h[0] + dt * dh[0] = 0.3 + 1.58 * 0.002 = 0.303 m

# 第3步：强制边界条件
h_star[0] = 0.3  ← 质量"消失"！
```

**累积效果**: 10步后质量误差达到2.9%

---

## 💡 解决方案探索

### 方案A：取消边界单元强制 ✗ 失败

**实施**: 修改`_apply_bc`，对supercritical边界不强制值

**结果**:
```
步骤5后:
  h[0] = 2.397 m  (目标: 0.3 m) ❌
  Q[0] = -8.104 m³/s (目标: 10 m³/s) ❌ (甚至变成负值！)
```

**结论**: 边界单元完全失控，数值崩溃

### 方案B：强制边界通量 ⚠️ 部分改善

**实施**: 实现`_enforce_boundary_fluxes()`方法，覆盖Riemann求解器的边界通量

**结果**:
- 质量误差从9%降到2.9% ✓
- 但仍未达到<1%目标
- 且可能破坏数值稳定性（未充分测试）

### 方案C：边界导数置零 ✗ 理论错误

**实施**: 设置`dh[0]/dt = 0`和`dQ[0]/dt = 0`

**问题**: 阻止质量进出边界，违背质量守恒原理

### 方案D：特征分解方法 🔬 需要研究

**理论基础**: LeVeque (2002), Toro (2009)

对于supercritical入口（Fr>1）:
- 两条特征线都向内（λ₁ > 0, λ₂ > 0）
- 边界值应完全由边界条件决定
- 内部扰动无法传播到边界

**潜在实现**:
```python
# 使用Riemann invariants
R_minus = u - 2*c  # 从边界条件
R_plus = u + 2*c   # 从边界条件
# 求解边界值，确保通量平衡
```

---

## 📊 当前性能评估

### MacDonald Test 2 (急缓流转换)

```
初始: supercritical入口 → 缓流 → h边界出口
结果: 质量误差 2.9% (目标: <1%)
```

### 影响分析

| 方面 | 状态 | 说明 |
|------|------|------|
| 数值稳定性 | ✅ | 求解器稳定，无崩溃 |
| 边界条件准确性 | ✅ | 边界值正确强制 |
| 边界通量准确性 | ✅ | Ghost cell→边界通量正确 |
| 内部通量准确性 | ✅ | Riemann求解器物理正确 |
| 质量守恒 | ⚠️ | 2.9%误差（可接受但未达到目标）|
| TRL评估 | TRL 3→4 | 原理验证 → 实验室验证（进行中） |

---

## 🔮 未来研究方向

### 短期（P0 - 本周）

1. **实现Riemann invariants边界处理**
   - 使用`CharacteristicBC`模块
   - 基于特征速度方向确定边界信息传播
   - 参考文献：Toro (2009) Section 6.3

2. **测试简化场景**
   - 纯supercritical流动（无急缓流转换）
   - 纯subcritical流动
   - 隔离急缓流转换的影响

### 中期（P1 - 下周）

3. **研究虚拟单元方法**
   - 边界单元仅作为缓冲，不参与物理演化
   - 真正的计算从第二个单元开始

4. **时间积分方法改进**
   - 考虑Strong Stability Preserving (SSP) RK方法
   - 研究边界处理的特殊时间积分

### 长期（P2 - 下月）

5. **Strang splitting方法**
   - 将边界条件与内部演化分开处理
   - 时间算子分裂：边界步 + 内部步

6. **文献调研**
   - 查阅SWASHES基准测试的实现
   - 研究Basilisk, ANUGA等成熟求解器的边界处理

---

## 📚 关键参考文献

1. **LeVeque, R.J. (2002)**. *Finite Volume Methods for Hyperbolic Problems*
   - Chapter 7: Boundary Conditions
   - Chapter 13: Nonlinear Systems

2. **Toro, E.F. (2009)**. *Riemann Solvers and Numerical Methods for Fluid Dynamics*
   - Section 6.3: Boundary Conditions
   - Section 6.4: Ghost Cell Methods

3. **Audusse et al. (2004)**. A Fast and Stable Well-Balanced Scheme
   - Boundary treatment for well-balanced schemes

4. **Delestre et al. (2013)**. SWASHES: A compilation of Shallow Water benchmarks
   - Standard boundary condition implementations

---

## 🛠️ 诊断工具

创建的测试文件（位于`tests/diagnostic/`）:

1. **test_boundary_enforcement.py** - 验证边界值强制
2. **test_mass_flux_analysis.py** - 追踪质量通量
3. **test_cell_by_cell_mass.py** - 逐单元质量分析
4. **test_froude_analysis.py** - Froude数和流态分析
5. **test_flux_values.py** - 详细通量值检查
6. **test_ghost_cell_consistency.py** - Ghost cell一致性测试
7. **test_boundary_evolution.py** - 边界单元演化测试

---

## ✅ 结论

**当前状态**: 已深入理解问题根源，质量误差从9%降到2.9%，但仍需进一步改进。

**核心挑战**: 在Godunov有限体积框架下，如何在保证边界条件准确性的同时实现严格的质量守恒。

**下一步**: 实现基于Riemann invariants的边界处理，并进行完整的MacDonald基准测试验证。

---

*本文档记录了2025-10-29对边界条件与质量守恒问题的深度调查结果*
