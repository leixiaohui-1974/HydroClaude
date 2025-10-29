# 质量守恒问题深度调查报告

**日期**: 2025-10-29
**状态**: 🔴 **P0 BLOCKING ISSUE**
**影响**: 阻碍MacDonald Test 2和Test 4通过

---

## 🎯 问题概述

通过一系列诊断测试，发现**质量守恒问题与边界条件类型无关**，而是Godunov求解器内部通量计算的根本性问题。

### 测试结果汇总

| 测试 | 边界类型 | 边界值强制 | 质量守恒 | 流量守恒 |
|------|---------|-----------|----------|---------|
| Q-h简单边界 | Q=10, h=2.0 | ✅ 正确 | ✅ <1% | ✅ 正确 |
| Supercritical边界 | h=0.3, Q=10 | ✅ 正确 | ❌ 9.4% | ❌ **失败** |
| 急缓流转换 | supercritical→h | ✅ 正确 | ❌ 33-61% | ❌ **严重失败** |

---

## 🔬 详细发现

### 1. 边界条件强制 ✅

**结论**: 边界值被正确强制

```python
# 诊断测试：tests/diagnostic/test_boundary_enforcement.py
# 结果：
上游条件: h = 0.3 m, Q = 10.0 m³/s, Fr = 1.94 (急流 ✓)
完成50步时间推进:
  h[0] = 0.300000 m (目标: 0.3)
  Q[0] = 10.000000 m³/s (目标: 10.0)
  Fr[0] = 1.94 (目标: 1.94)
✅ 所有时间步边界条件都被正确强制
```

### 2. 边界通量计算 ✅ 部分正确

**结论**: 简单边界通量正确，supercritical边界通量不一致

```python
# 诊断测试：tests/diagnostic/test_mass_flux_analysis.py
步骤 1-10:
  流入: Q_up = 10.000000 m³/s  ✅
  流出: Q_out = 10.000000 m³/s ✅
  理论质量变化: 0.000 m³ (Q_in - Q_out = 0)
  实际质量变化: 3.5 → 56.3 m³  ❌ 严重不匹配
```

### 3. 内部流量守恒 ❌ 失败

**结论**: 流量在第一个内部单元就开始损失

```python
# 诊断测试：tests/diagnostic/test_froude_analysis.py
单元   h(m)    Q(m³/s)   状态
  0   0.3000  10.0000   急流  ← 边界单元，正确
  1   0.8011   8.5310   缓流  ← **流量损失15%！**
  2   1.1710   5.6816   缓流  ← 继续损失
  9   2.0000  10.0000   缓流  ← 边界单元，正确
```

**物理违背**: 在无摩阻（n=0）、水平床（slope=0）的情况下，流量应沿程保持恒定Q=10 m³/s。

### 4. 质量累积模式 ❌ 失败

**结论**: 单元2-7累积质量，单元8损失质量

```python
# 诊断测试：tests/diagnostic/test_cell_by_cell_mass.py
步骤 3后各单元质量变化:
  单元0: +0.000000 m³    (边界单元，不变 ✓)
  单元1: +8.796210 m³  ⚠️
  单元2: +22.288633 m³ ⚠️ 最大累积
  单元3: +18.537203 m³ ⚠️
  单元8: -20.398436 m³ ⚠️ 质量流失
  单元9: +0.000000 m³    (边界单元，不变 ✓)
```

---

## 🐛 根本原因分析

### 假设1: 边界单元时间推进问题 ❌

**尝试**: 设置dh_dt[0]=0, dQ_dt[0]=0 (边界单元不参与时间推进)

**结果**: 边界通量从不匹配（Q_in≠Q_out）变为匹配，但内部质量仍然累积

**结论**: 这不是根本原因

### 假设2: Ghost cell设置不一致 ❓

**分析**:
- `_extend_with_ghosts`设置h_ext[0]=0.3, Q_ext[0]=10 ✓
- 但单元0和单元1之间的通量F_0.5计算可能有问题
- 单元1的Q立即降到8.53，说明通量计算有误

**可能问题**:
```python
# 界面0.5（单元0和1之间）
h_L = h_ext[0] = 0.3  (ghost cell)
h_R = h_ext[1] = 0.3  (单元0)
Q_L = Q_ext[0] = 10   (ghost cell)
Q_R = Q_ext[1] = 10   (单元0)
```

如果h_L=h_R且Q_L=Q_R，通量应该恒定。但为什么单元1的Q会变化？

### 假设3: Riemann求解器在急缓流转换处不稳定 ⚠️

**分析**:
- 单元0: Fr=1.94 (急流)
- 单元1: Fr=0.38 (缓流)
- 激波/水跃应该在某处形成

**问题**: HLL求解器可能在急缓流转换处产生过度耗散，导致流量损失

### 假设4: RK2时间积分与边界强制不兼容 ⚠️

**分析**:
```python
# RK2步骤1
dh_dt, dQ_dt = _compute_rhs(h_n, Q_n)  # 基于初始值计算
h_star = h_n + dt * dh_dt              # 边界单元被推进
h_star, Q_star = _apply_bc(h_star, Q_star)  # 强制恢复边界值

# 这导致边界单元的质量"被修正"，但相邻单元不知道
```

---

## 💡 可能的解决方案

### 方案1: 修复边界通量计算 (优先级：P0)

**思路**: 边界单元的通量应该基于边界条件，而不是Riemann求解器

```python
def _compute_rhs(...):
    # 标准计算所有通量
    F_h, F_Q = compute_all_fluxes(...)

    # 强制边界通量
    if bc_left['type'] == 'supercritical':
        Q_bc = bc_left['Q']
        h_bc = bc_left['h']
        u_bc = Q_bc / (B * h_bc)
        # 左边界通量（流入）
        F_h[0] = Q_bc
        F_Q[0] = Q_bc * u_bc + 0.5 * g * h_bc^2 * B
```

### 方案2: 使用特征分解方法处理边界 (优先级：P1)

**参考**: LeVeque (2002) Chapter 7 - Boundary Conditions

基于特征速度λ的方向决定边界信息传播：
- 如果λ > 0: 信息从边界流入，需要指定边界值
- 如果λ < 0: 信息从内部流出，使用外推

### 方案3: 改用Strang splitting处理边界 (优先级：P2)

**思路**: 将边界条件与内部演化分开处理

---

## 📊 影响范围

### 直接影响

- ❌ MacDonald Test 2 (M2下降曲线): 质量误差33%
- ❌ MacDonald Test 4 (水跃): 质量误差61%
- ✅ MacDonald Test 1 (M1壅水): 仍然通过（缓流，无急缓转换）
- ✅ Lake at Rest测试: 仍然通过（静水）

### 项目影响

- **TRL等级**: 保持TRL 4-5（基础数值问题未解决）
- **MacDonald通过率**: 2/5 (40%) 无法提升
- **特征线边界条件**: 模块实现正确，但无法展示效果

---

## 🔄 后续行动

### 立即 (P0)

1. **测试方案1**: 强制边界通量
2. **验证简单案例**: 纯急流或纯缓流（避免水跃）
3. **文献调研**: 查阅标准Godunov FVM如何处理边界

### 短期 (P1)

4. **实现特征分解边界**: 基于特征速度方向
5. **添加诊断输出**: 记录每步的通量和质量流
6. **与商业软件对比**: HEC-RAS/SWMM如何处理

### 长期 (P2)

7. **考虑well-balanced格式**: 可能有助于急缓流转换
8. **尝试其他Riemann求解器**: HLLC/Roe等
9. **文献发表**: 如果发现新的数值现象

---

## 📝 技术债务

1. **CRITICAL**: 边界通量计算与Riemann求解器不一致
2. **HIGH**: 急缓流转换区域质量守恒失败
3. **MEDIUM**: 缺乏边界通量的单独测试
4. **LOW**: 警告信息过多（底高程变化）

---

## 📚 参考文献

1. LeVeque, R. (2002). *Finite Volume Methods for Hyperbolic Problems*. Chapter 7: Boundary Conditions
2. Toro, E. (2009). *Riemann Solvers and Numerical Methods for Fluid Dynamics*. Chapter 6: Boundary Conditions
3. Godlewski, E. & Raviart, P. (1996). *Numerical Approximation of Hyperbolic Systems of Conservation Laws*
4. Audusse, E. et al. (2004). *A fast and stable well-balanced scheme*. SIAM J. Sci. Comput.

---

**报告结束**
**下一步**: 测试方案1 - 强制边界通量计算
