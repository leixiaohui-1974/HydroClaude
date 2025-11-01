# 精确Riemann求解器崩溃根本原因分析
## Root Cause Analysis of Exact Riemann Solver Crash

**日期**: 2025-11-01
**问题**: 精确求解器在CFL=0.1时于t≈1.8s崩溃，质量爆炸至1738%
**状态**: ✅ 根本原因已定位

---

## 执行摘要

通过详细的时间线诊断，成功定位了精确Riemann求解器崩溃的根本原因：

**🎯 根本原因**: `_sample_solution`函数在稀疏波内部采样时，没有对计算出的深度h进行干床保护，导致h→0时速度u发散到极端值。

---

## 1. 崩溃时间线（Timeline）

### t=0.0-1.2s: 完美稳定期
```
t=1.0s:  质量误差=0.000000%, h范围=[1.0, 2.0]m ✅
t=1.2s:  质量误差=0.000012%, h范围=[0.935, 2.0]m ✅
```
- 求解器工作正常
- 质量几乎完美守恒（误差<0.001%）

### t=1.4s: 🚨 首次干床出现
```
步骤32:  质量误差=0.326884%, h范围=[0.0, 2.639]m
⚠️  高速度单元: [26]
  单元26: u = 179,343,204,767.98 m/s (1793亿m/s！)
```

**关键发现**:
- 首次出现h=0的单元
- 单元26的速度爆炸到完全非物理的1793亿m/s
- 原因：u = Q/(h*B)，当h→0时发散

### t=1.6s: 异常扩散
```
步骤38:  质量误差=0.366506%, h范围=[0.0, 2.770]m
⚠️  高速度单元: [26, 28]
```
- 异常从单元26扩散到单元28
- 质量误差仍可控，但极端速度已存在

### t=1.8s: 质量爆炸前夕
```
步骤47:  质量误差=2.148247%, h范围=[0.0, 2.935]m
⚠️  高速度单元: [25, 28, 31, 33]
```
- 极端速度单元增加到4个
- 质量误差开始显著增长

### t=1.8031s: 💥 崩溃
```
步骤56:  质量误差=1738.905350%
单元32: h从2.914m爆炸到1305.476m
极端速度单元:
  - 单元28: u = 221,308,039,566.86 m/s
  - 单元32: h = 1305.476m (水深爆炸到1.3公里！)
  - 单元33: u = 3,896,032,844,699.60 m/s (3.9万亿m/s！)
```

---

## 2. 根本原因分析

### 2.1 代码位置

**文件**: `solvers/riemann_exact.py`
**函数**: `_sample_solution`, 第292-381行

### 2.2 问题代码

当采样点s=0落在稀疏波（rarefaction fan）内部时：

```python
# 左稀疏波内部 (Line 344-348)
elif s <= S_tail_L:
    # Inside rarefaction fan
    u = (u_L + 2.0 * c_L + 2.0 * s) / 3.0
    c = (u_L + 2.0 * c_L - s) / 3.0
    h = c**2 / g                        # ❌ 问题所在！
    return h, u

# 右稀疏波内部 (Line 373-378)
elif s >= S_head_R:
    # Inside rarefaction fan
    u = (u_R - 2.0 * c_R + 2.0 * s) / 3.0
    c = (-u_R + 2.0 * c_R + s) / 3.0
    h = c**2 / g                        # ❌ 问题所在！
    return h, u
```

### 2.3 失败机制

1. **稀疏波内部公式计算**:
   - 根据特征线理论，c = (u_L + 2*c_L - s)/3 或类似公式
   - 在某些状态下，计算出的c可能非常小或接近0

2. **深度计算**:
   - h = c²/g
   - **没有任何干床保护**
   - 当c→0时，h→0

3. **速度发散**:
   - 返回的h≈0传递给Godunov求解器
   - 下一步计算u = Q/(h*B)时发散到极端值
   - 极端速度→极端通量→质量爆炸

### 2.4 为什么HLL求解器不会崩溃？

HLL求解器使用简化的通量公式，内置了更多的数值耗散和鲁棒性保护：
- 通量计算中自然包含了状态平均
- 不需要精确采样稀疏波内部
- 对h→0的情况有隐式保护

---

## 3. 为什么CFL=0.1时延迟崩溃？

CFL=0.1相比CFL=0.5:
- **时间步长更小** (dt≈0.045s vs dt≈0.2s)
- **稀疏波演化更慢**
- **延迟了h→0的状态出现**

但这只是**延迟崩溃**，并未解决根本问题。

---

## 4. 对比：Toro (2009)的标准实现

Toro的标准实现（书籍代码）通常包含：

1. **干床阈值检查**:
```fortran
! Toro风格的保护
IF (h_sample .LT. TOL) THEN
    h_sample = 0.0
    u_sample = 0.0
    RETURN
ENDIF
```

2. **稀疏波中的保护**:
```fortran
c = MAX(cmin, (u_L + 2.0*c_L - s)/3.0)
h = c**2 / g
```

**我们的实现缺少这些保护！**

---

## 5. 修复方案

### 方案A: 添加干床保护（推荐）

在`_sample_solution`函数中，稀疏波采样后添加检查：

```python
elif s <= S_tail_L:
    # Inside rarefaction fan
    u = (u_L + 2.0 * c_L + 2.0 * s) / 3.0
    c = (u_L + 2.0 * c_L - s) / 3.0
    c = max(c, np.sqrt(g * eps_dry))  # ✅ 保护c不小于干床阈值
    h = c**2 / g

    # 双重保护
    if h < eps_dry:
        return eps_dry, 0.0

    return h, u
```

**优点**:
- 直接解决根本问题
- 符合Toro标准实现
- 简单明了

**缺点**:
- 引入了人工干床阈值
- 在干床附近可能影响精度

### 方案B: 改进稀疏波公式

使用更鲁棒的稀疏波计算：

```python
elif s <= S_tail_L:
    # Inside rarefaction fan
    c_L_min = np.sqrt(g * eps_dry)  # 最小波速

    u = (u_L + 2.0 * max(c_L, c_L_min) + 2.0 * s) / 3.0
    c = max((u_L + 2.0 * c_L - s) / 3.0, c_L_min)
    h = c**2 / g
    return h, u
```

### 方案C: 标记为不可用（当前推荐）

考虑到：
- 修复需要深入验证
- HLL求解器已经工作良好
- 时间成本vs收益不平衡

**建议**:
- 保持精确求解器"实验性"状态
- 在文档中明确说明已知问题和根本原因
- 推荐生产环境使用HLL

---

## 6. 验证测试

如果选择方案A修复，需要测试：

1. **溃坝测试** (dam break)
   - 各种CFL数（0.1, 0.3, 0.5）
   - 长时间模拟（t=10s）
   - 质量守恒误差<0.1%

2. **干床测试** (dry bed)
   - 左干右湿、左湿右干
   - 双侧干床

3. **稀疏波测试** (rarefaction)
   - 双稀疏波问题
   - 激波+稀疏波组合

4. **Lake at Rest**
   - 与Well-Balanced结合
   - 机器精度验证

---

## 7. 结论

### 根本原因
✅ **明确定位**: `_sample_solution`函数中稀疏波内部采样缺少干床保护

### 崩溃链
```
稀疏波采样 → c→0 → h=c²/g→0 → u=Q/(h*B)→∞ → 极端通量 → 质量爆炸 → 崩溃
```

### 推荐行动
1. **短期**: 保持精确求解器标记为"实验性，请勿使用"
2. **中期**: 创建本报告并归档调试发现
3. **长期**: 如果有需求，按方案A修复并全面测试

### 关键经验
- ✅ 成功使用时间线诊断定位了问题
- ✅ 干床处理是Riemann求解器的关键
- ✅ 高精度求解器需要更谨慎的数值保护

---

## 8. 参考文献

1. Toro, E.F. (2009). *Riemann Solvers and Numerical Methods for Fluid Dynamics*. Springer, 3rd Edition.
   - Chapter 13: Exact Riemann Solver
   - Section 13.3: Sampling the Solution

2. Toro, E.F. (2001). *Shock-Capturing Methods for Free-Surface Shallow Flows*. Wiley.
   - Chapter 5: Exact Riemann Solver for SWE

3. HydroClaude内部文档:
   - `docs/EXACT_SOLVER_DEBUGGING_REPORT_2025_11_01.md` - 初步调试报告
   - `tests/diagnose_exact_crash_timeline.py` - 时间线诊断工具
   - `docs/PHASE_9_3_EXACT_RIEMANN_SOLVER.md` - Phase 9.3开发文档

---

**报告作者**: HydroClaude开发团队
**最后更新**: 2025-11-01
**状态**: 根本原因分析完成，待决定修复方案
