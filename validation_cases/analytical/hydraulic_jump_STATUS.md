# 水跃验证状态 (Hydraulic Jump Validation Status)

## 当前状态：⚠️ 需要进一步研究

**问题**：水跃数值模拟出现NaN（数值不稳定）

## 原因分析

水跃是明渠水流中的**激波（shock wave）**，具有以下特点：
1. 流态突变：超临界→亚临界
2. 水深突变：Fr1 > 1 → Fr2 < 1
3. 强能量耗散：ΔE = (y2-y1)³/(4y1y2)

这类问题对数值方法极具挑战性：
- 需要shock-capturing能力
- 需要well-balanced source term处理
- 需要positivity-preserving（保正性）

## 已尝试的方法

1. ✓ 实现空间变化坡度（S0数组）
2. ✓ 平滑初始条件（tanh profile）
3. ✓ 降低CFL数（0.3）
4. ✓ 一阶精度（更稳定）
5. ✓ 减小坡度差异
6. ✗ 仍然出现数值溢出和NaN

## 需要的高级技术

### 1. 更强的Riemann求解器
- HLLC（contact discontinuity分辨率）
- Roe求解器 + entropy fix
- Osher求解器

### 2. Well-Balanced格式
- Hydrostatic reconstruction
- Surface gradient method
- 精确处理源项平衡

### 3. 正性保持
- Positivity-preserving limiter
- 避免负水深
- Draining time step

### 4. 或使用稳态求解器
- Newton-Raphson
- 避免时间推进的稳定性问题

## 商业软件对比

| 软件 | 水跃处理 | 方法 |
|------|---------|-----|
| HEC-RAS | ✓ | Mixed flow regime solver |
| MIKE 11 | ✓ | 6-point implicit scheme |
| InfoWorks | ✓ | Preissmann slot |
| **HydroClaude** | ⚠️ | Godunov-FVM (需增强) |

## 推荐方案

### 短期（当前）
- 标记为已知限制
- 专注于其他验证案例
- 确保基础功能100%可靠

### 中期（1-2周）
- 实现HLLC求解器
- Well-balanced格式
- 专门的water jump solver

### 长期
- 研究商业软件方法
- 混合流态求解器
- 与实测数据对比

## 参考文献

1. Toro (2009) "Riemann Solvers and Numerical Methods for Fluid Dynamics"
2. Audusse et al. (2004) "A fast and stable well-balanced scheme"
3. Vukovic & Sopta (2002) "ENO and WENO schemes with the exact conservation property"
4. HEC-RAS Mixed Flow Regime Algorithm

## 结论

水跃验证失败**不影响**核心求解器的可靠性。其他验证案例（溃坝、MacDonald、恒定流）都通过，证明：
- ✓ 基础水动力学正确
- ✓ 质量守恒完美
- ✓ 激波捕捉（溃坝波）成功

水跃是**极端工况**，需要专门的high-order shock-capturing方法。

**优先级**：中等（有解决方案，需要时间实现）

---
**日期**：2025-10-28
**状态**：研究中
**下一步**：实现HLLC求解器或well-balanced格式
