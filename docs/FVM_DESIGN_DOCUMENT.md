# 有限体积法（FVM）设计文档

**目标**: 实现严格守恒的有限体积法求解器，达到0.5%精度

**作者**: Claude
**日期**: 2025-10-23

---

## 1. 理论基础

### 1.1 Saint-Venant方程积分形式

**守恒形式**:
```
∂U/∂t + ∂F(U)/∂x = S(U)
```

其中：
```
U = [A, Q]ᵀ  （守恒变量）
F = [Q, Q²/A + gI₁]ᵀ  （通量函数）
S = [0, gA(S₀ - Sf)]ᵀ  （源项）
```

- A = B·h：断面面积 (m²)
- Q：流量 (m³/s)
- I₁ = A·h_c：水深中心矩（矩形断面：I₁ = A·h/2）

### 1.2 有限体积离散

**控制体积Vᵢ**: [xᵢ₋₁/₂, xᵢ₊₁/₂]

**积分形式**:
```
d/dt ∫[Vᵢ] U dx + F(U)|ₓᵢ₊₁/₂ - F(U)|ₓᵢ₋₁/₂ = ∫[Vᵢ] S(U) dx
```

**半离散形式**:
```
dUᵢ/dt = -1/Δxᵢ [Fᵢ₊₁/₂ - Fᵢ₋₁/₂] + Sᵢ
```

其中：
- Uᵢ：单元平均值
- Fᵢ₊₁/₂：单元界面通量（需用Riemann求解器计算）
- Δxᵢ：单元尺寸

---

## 2. Riemann求解器

### 2.1 HLL求解器

**Harten-Lax-van Leer求解器**适用于浅水方程。

**界面通量**:
```
         ⎧ F_L                    if 0 ≤ s_L
F_HLL = ⎨ F* = (s_R·F_L - s_L·F_R + s_L·s_R·(U_R - U_L)) / (s_R - s_L)   if s_L < 0 < s_R
         ⎩ F_R                    if s_R ≤ 0
```

**波速估计**:
```
s_L = min(u_L - c_L, ũ - c̃)
s_R = max(u_R + c_R, ũ + c̃)
```

其中：
- u = Q/A：流速 (m/s)
- c = √(gA/B)：波速 (m/s)（矩形断面）
- ũ, c̃：Roe平均速度和波速

**Roe平均**:
```
ũ = (√A_L·u_L + √A_R·u_R) / (√A_L + √A_R)
h̃ = (√A_L·h_L + √A_R·h_R) / (√A_L + √A_R)  （对矩形断面）
c̃ = √(g·h̃)
```

### 2.2 HLLC求解器（可选，更精确）

包含接触间断的三波模型，精度更高但计算量更大。

---

## 3. 空间重构

### 3.1 Godunov一阶格式

**分段常数重构**:
```
U(x) = Uᵢ,  x ∈ [xᵢ₋₁/₂, xᵢ₊₁/₂]
```

**界面值**:
```
U_L = Uᵢ
U_R = Uᵢ₊₁
```

**精度**: O(Δx)

**优点**:
- 简单稳定
- 严格单调（无振荡）

**缺点**:
- 一阶精度，过度耗散

### 3.2 MUSCL二阶格式

**分段线性重构**:
```
U(x) = Uᵢ + σᵢ·(x - xᵢ)
```

其中σᵢ是限制后的斜率。

**界面值**:
```
U_L = Uᵢ + 0.5·Δxᵢ·σᵢ
U_R = Uᵢ₊₁ - 0.5·Δxᵢ₊₁·σᵢ₊₁
```

**精度**: O(Δx²)

### 3.3 Slope限制器

为保证TVD（Total Variation Diminishing）性质，需要限制斜率。

**Minmod限制器**:
```
σᵢ = minmod(θ·∇U_backward, ∇U_central, θ·∇U_forward)

where:
  ∇U_backward = (Uᵢ - Uᵢ₋₁) / Δxᵢ
  ∇U_central = (Uᵢ₊₁ - Uᵢ₋₁) / (Δxᵢ + Δxᵢ₊₁)
  ∇U_forward = (Uᵢ₊₁ - Uᵢ) / Δxᵢ₊₁
  θ ∈ [1, 2]  (通常取1.5)
```

**minmod函数**:
```python
def minmod(a, b, c):
    if a > 0 and b > 0 and c > 0:
        return min(a, b, c)
    elif a < 0 and b < 0 and c < 0:
        return max(a, b, c)
    else:
        return 0.0
```

**Van Leer限制器**（更平滑）:
```
σᵢ = (r·|∇U| + |∇U|·r) / (1 + r)
where r = ∇U_backward / ∇U_forward
```

---

## 4. 时间积分

### 4.1 显式Euler（一阶）

```python
U^(n+1) = U^n + Δt·RHS(U^n)
```

简单但需要小时间步长。

### 4.2 SSP-RK2（二阶）

**强稳定性保持Runge-Kutta**:
```python
U* = U^n + Δt·RHS(U^n)
U^(n+1) = 0.5·U^n + 0.5·(U* + Δt·RHS(U*))
```

**优点**:
- 二阶精度
- 保持单调性
- CFL条件更宽松

### 4.3 CFL条件

```
Δt ≤ CFL · min(Δxᵢ / (|uᵢ| + cᵢ))
```

通常取CFL = 0.5（一阶）或0.9（二阶RK）。

---

## 5. 源项处理

### 5.1 点隐式处理

摩阻源项Sf可能导致刚性，使用点隐式处理：

```python
S_friction^(n+1) = g·A^(n+1)·Sf(Q^(n+1), h^(n+1))
```

通过Newton迭代求解。

### 5.2 Well-balanced格式

为保证静水平衡，需要特殊处理：
```
S₀ = Sf  →  ∂h/∂x = 0
```

使用源项分裂或hydrostatic reconstruction。

---

## 6. 闸门边界处理

### 6.1 内部边界Riemann问题

闸门位置xₐ，划分为两个单元：
- 上游单元：[xₐ₋₁/₂, xₐ]
- 下游单元：[xₐ, xₐ₊₁/₂]

**闸门处通量**:
```
F_gate = Q_gate·[1, u_gate + g·h_c]ᵀ
```

其中Q_gate由闸门方程计算：
```
Q_gate = Cd·a·√(2g·Δh)
```

### 6.2 守恒通量修正

确保闸门处守恒：
```
F_left - F_gate = 0
F_gate - F_right = 0
```

通过迭代调整h_up和h_down。

---

## 7. 实现架构

### 7.1 类结构

```python
class FVMSolver:
    """有限体积法求解器"""

    def __init__(self, reconstruction='muscl', limiter='minmod'):
        self.reconstruction = reconstruction  # 'godunov' or 'muscl'
        self.limiter = limiter  # 'minmod', 'vanleer', 'superbee'

    def reconstruct(self, U, i):
        """空间重构，返回界面左右值"""
        if self.reconstruction == 'godunov':
            return self._reconstruct_godunov(U, i)
        else:
            return self._reconstruct_muscl(U, i)

    def riemann_solver(self, U_L, U_R):
        """HLL Riemann求解器，返回界面通量"""
        return self._hll_flux(U_L, U_R)

    def compute_rhs(self, U):
        """计算右端项 dU/dt"""
        # 1. 重构界面值
        # 2. 计算界面通量
        # 3. 计算源项
        # 4. 组装RHS
        pass

    def step(self, U, dt):
        """时间推进一步"""
        # SSP-RK2或Euler
        pass
```

### 7.2 与现有框架集成

```python
class CanalSolverFVM(CanalSolver):
    """FVM版本的CanalSolver"""

    def __init__(self, ..., use_fvm=True, fvm_order=2):
        super().__init__(...)
        if use_fvm:
            self.fvm = FVMSolver(
                reconstruction='muscl' if fvm_order == 2 else 'godunov',
                limiter='minmod'
            )
```

---

## 8. 验证测试

### 8.1 Dam Break（溃坝）

解析解存在，验证：
- 守恒性
- 激波捕捉
- 稀疏波分辨率

### 8.2 静水平衡

初始：h = h₀ - S₀·x, Q = 0

验证：
- Well-balanced性质
- 机器精度保持平衡

### 8.3 闸门测试

验证：
- 闸门边界处理
- 长时间守恒性
- 精度提升

---

## 9. 预期性能

### 9.1 精度预期

| 方法 | 空间精度 | 预期误差 |
|------|---------|---------|
| Godunov | O(Δx) | 0.5-1.0% |
| MUSCL-Minmod | O(Δx²) | 0.2-0.5% ✓ |
| MUSCL-Van Leer | O(Δx²) | 0.1-0.3% |

### 9.2 计算开销

相比当前Preissmann格式：
- 内存：约1.2x（存储重构数据）
- 计算：约2-3x（Riemann求解器+重构）
- 总体：可接受的开销换取精度提升

---

## 10. 实施计划

### Week 1: 基础框架（Godunov）

**Day 1-2**:
- 实现HLL Riemann求解器
- 单元测试（Riemann问题）

**Day 3-4**:
- 实现Godunov一阶FVM
- Dam break验证

**Day 5-7**:
- 静水平衡测试
- 闸门初步集成

### Week 2: MUSCL二阶

**Day 8-10**:
- 实现MUSCL重构
- Minmod限制器
- Van Leer限制器

**Day 11-12**:
- SSP-RK2时间积分
- 精度验证

**Day 13-14**:
- 性能优化
- 代码重构

### Week 3: 集成和测试

**Day 15-17**:
- 闸门FVM处理
- 守恒性验证

**Day 18-19**:
- 脚本11完整测试
- 精度对比

**Day 20-21**:
- 文档和报告
- 代码提交

---

## 11. 成功标准

✅ **必须达到**:
1. 守恒性：机器精度内满足质量守恒
2. 单调性：无非物理振荡
3. 精度：最大误差 < 0.5%
4. 稳定性：长时间运行不发散

✅ **期望达到**:
1. MUSCL二阶：最大误差 < 0.3%
2. 计算效率：< 5x当前方法
3. 通用性：适用于各种闸门配置

---

## 参考文献

1. Toro, E.F. (2009). Riemann Solvers and Numerical Methods for Fluid Dynamics
2. LeVeque, R.J. (2002). Finite Volume Methods for Hyperbolic Problems
3. Audusse et al. (2004). A Fast and Stable Well-Balanced Scheme for Shallow Water Equations
4. Castro-Díaz et al. (2013). Well-Balanced High Order Extensions of Godunov's Method

---

**状态**: 设计完成，准备实施
**下一步**: 实现HLL Riemann求解器
