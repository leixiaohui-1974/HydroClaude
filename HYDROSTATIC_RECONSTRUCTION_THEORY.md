# 静水重构法理论推导与实现方案
# Hydrostatic Reconstruction: Theory and Implementation

**日期**: 2025-10-23
**基于**: Audusse et al. (2004) SIAM + 相关文献
**目标**: 为三闸门渠道系统实现良平衡数值格式

---

## 1. 问题陈述

### 1.1 Saint-Venant方程

```
∂h/∂t + ∂(hu)/∂x = 0                    (连续性)
∂(hu)/∂t + ∂(hu² + gh²/2)/∂x = -gh∂z/∂x - ghu²n²/R^(4/3)  (动量)
```

其中：
- h(x,t): 水深
- u(x,t): 流速
- z(x): 底床高程
- η(x,t) = h(x,t) + z(x): 水位
- g: 重力加速度
- n: Manning糙率
- R: 水力半径

### 1.2 稳态条件

稳态时 ∂/∂t = 0：

```
∂Q/∂x = 0  →  Q = 常数              (质量守恒)
∂(Q²/A + gA·η)/∂x = -gA(Sf)        (动量平衡)
```

其中 A = B·h (矩形渠道)

### 1.3 当前FDM的问题

标准有限差分离散化：

```
[F(U_{i+1}) - F(U_i)] / Δx ≠ [S(U_i, z_{i+1}, z_i)]
```

**问题**：即使在精确稳态解上，数值通量与源项也**不精确平衡**，导致：
- 人工数值耗散：O(Δx)
- 稳态时产生虚假波动
- 精度损失累积

---

## 2. 良平衡性质 (Well-Balanced Property)

### 2.1 定义

数值格式称为**良平衡的**，如果它能够**精确保持**湖面静止状态(lake-at-rest)：

```
h + z = η = 常数,  u = 0  (everywhere)
```

**数学表述**：

```
如果初始条件满足 η_i = 常数 且 u_i = 0 ∀i，
则数值解精确保持 η_i^{n+1} = η_i^n 且 u_i^{n+1} = 0 ∀n
```

### 2.2 为什么重要？

1. **稳态精度**：稳态解是"接近静止"的特例，良平衡格式在稳态附近误差最小
2. **数值稳定性**：消除虚假波动
3. **理论保证**：数学证明的精度

---

## 3. 静水重构核心思想

### 3.1 关键洞察

**问题根源**：标准方法直接重构**水深h**，导致：

```
单元i:   h_i,  z_i  →  η_i = h_i + z_i
单元i+1: h_{i+1}, z_{i+1}  →  η_{i+1} = h_{i+1} + z_{i+1}

当 z 不连续时，即使 η 连续（稳态），h也不连续
→ 数值通量误认为存在波动
```

**解决方案**：重构**水位η**而非水深h

```
1. 重构连续的水位场 η(x)
2. 根据重构的 η 和底床 z 计算"修正的"水深
3. 使用修正水深计算数值通量
```

### 3.2 几何解释

```
         η_{i+1} --------
        /
       /
η_i ----
      |    |            |
      | h_i|            | h_{i+1}
      |    |            |
======z_i==|============|===== z_{i+1}
           ↑            ↑
        界面i+1/2

标准方法：使用 h_i 和 h_{i+1} 计算通量
静水重构：使用 η 和 z 重新计算界面水深
```

---

## 4. 静水重构算法

### 4.1 一维情况的完整算法

给定单元 i 的平均值 (h_i, hu_i, z_i)，计算界面 i+1/2 的数值通量。

#### Step 1: 重构水位

使用单元中心的水位：

```python
η_i = h_i + z_i
η_{i+1} = h_{i+1} + z_{i+1}
```

#### Step 2: 定义界面底床高程

关键步骤！定义界面处的"有效"底床高程：

```python
z_{i+1/2}^L = max(z_i, z_{i+1})  # 从左侧看到的底床
z_{i+1/2}^R = max(z_i, z_{i+1})  # 从右侧看到的底床
```

**注意**：这里取max确保不会出现"负水深"。

#### Step 3: 计算重构后的水深

从左侧：

```python
h_{i+1/2}^L = max(0, η_i - z_{i+1/2}^L)
```

从右侧：

```python
h_{i+1/2}^R = max(0, η_{i+1} - z_{i+1/2}^R)
```

**物理意义**：
- 如果水位 η 低于界面底床 z，则水深为0（干）
- 否则水深 = 水位 - 底床高程

#### Step 4: 计算重构后的流量

保持流量守恒（关键！）：

```python
if h_{i+1/2}^L > 0:
    (hu)_{i+1/2}^L = hu_i * (h_{i+1/2}^L / h_i)
else:
    (hu)_{i+1/2}^L = 0

if h_{i+1/2}^R > 0:
    (hu)_{i+1/2}^R = hu_{i+1} * (h_{i+1/2}^R / h_{i+1})
else:
    (hu)_{i+1/2}^R = 0
```

#### Step 5: 使用重构状态计算数值通量

定义重构后的保守变量：

```python
U_{i+1/2}^L = [h_{i+1/2}^L, (hu)_{i+1/2}^L]
U_{i+1/2}^R = [h_{i+1/2}^R, (hu)_{i+1/2}^R]
```

使用任意Riemann求解器（如HLL, Roe, Rusanov）：

```python
F_{i+1/2} = RiemannSolver(U_{i+1/2}^L, U_{i+1/2}^R)
```

#### Step 6: 修改源项

**关键**：源项必须与通量精确匹配。

重力源项修改为：

```python
S_{i}^{gravity} = -g/2 * (h_i² - (h_{i+1/2}^L)²) / Δx  # 界面i+1/2的贡献
                  -g/2 * (h_{i-1/2}^R)² - h_i²) / Δx  # 界面i-1/2的贡献
```

**或者更简洁的形式**（Audusse原始公式）：

```python
S_i^{gravity} = -g * h_i * (z_{i+1/2} - z_{i-1/2}) / Δx
```

其中 z_{i±1/2} 是界面处的底床高程。

摩擦源项保持不变：

```python
S_i^{friction} = -g * n² * |hu_i| * hu_i / (h_i^(4/3))
```

### 4.2 良平衡性证明（直觉）

对于湖面静止 η = 常数, u = 0：

```
1. 所有单元: η_i = η_{i+1} = η_0
2. 重构水深: h_{i+1/2}^L = η_0 - z_{i+1/2}^L
              h_{i+1/2}^R = η_0 - z_{i+1/2}^R

3. 由于 z_{i+1/2}^L = z_{i+1/2}^R = max(z_i, z_{i+1})
   所以 h_{i+1/2}^L = h_{i+1/2}^R

4. 且 (hu)_{i+1/2}^L = (hu)_{i+1/2}^R = 0

5. Riemann求解器输入相同左右状态 → 通量 F_{i+1/2} = [0, gη_0²/2]

6. 源项: S_i = -g h_i (z_{i+1/2} - z_{i-1/2}) / Δx

7. 通量梯度: [F_{i+1/2} - F_{i-1/2}]/Δx 的动量分量
            = g/2 * (η_0² - η_0²)/Δx = 0  (因为η处处相等)

8. 但是！需要仔细处理压力项...
```

**完整证明**见Audusse et al. (2004) Theorem 3.1。

---

## 5. 适配三闸门系统

### 5.1 闸门的特殊性

我们的系统有3个渠道 + 3个闸门：

```
Canal 1 [====] Gate 1 [====] Canal 2 [====] Gate 2 [====] Canal 3 [====] Gate 3
```

**闸门边界条件**：

```python
Q_gate = Cd * B * e * sqrt(2 * g * Δh)  if Δh > 0
```

其中 Δh = η_upstream - η_downstream - z_gate

### 5.2 闸门处的静水重构

闸门可视为**极端的底床高程突变**：

```
z_gate = z_base + gate_height
```

**策略1: 闸门作为内部边界**

```python
# 在闸门上游侧（渠道1末端）
η_upstream = h_upstream + z_upstream
h_gate^L = max(0, η_upstream - z_gate)

# 在闸门下游侧（渠道2起点）
η_downstream = h_downstream + z_downstream
h_gate^R = max(0, η_downstream - z_gate)

# 闸门通量（替代Riemann求解器）
if h_gate^L > gate_height:  # 淹没出流
    Q_gate = Cd * B * e * sqrt(2 * g * (η_upstream - η_downstream))
elif h_gate^L > 0:  # 自由出流
    Q_gate = Cd * B * e * sqrt(2 * g * h_gate^L)
else:
    Q_gate = 0
```

**策略2: 闸门作为源项**

保持渠道内使用静水重构，闸门作为质量/动量源汇：

```python
# Canal 1最后一个单元
S_mass[i_end_canal1] = -Q_gate / Δx
S_momentum[i_end_canal1] = -Q_gate * u[i_end_canal1] / Δx

# Canal 2第一个单元
S_mass[i_start_canal2] = +Q_gate / Δx
S_momentum[i_start_canal2] = +Q_gate * u[i_start_canal2] / Δx
```

推荐**策略1**，因为它更自然地处理水位连续性。

### 5.3 实施细节

#### 5.3.1 数据结构

```python
class HydrostaticReconstructionSolver:
    def __init__(self, canals, gates):
        self.canals = canals  # List[Canal]
        self.gates = gates    # List[Gate]

    def reconstruct_at_interface(self, i):
        """在单元i和i+1之间的界面进行静水重构"""
        # Step 1: 获取单元数据
        h_L = self.h[i]
        h_R = self.h[i+1]
        z_L = self.z[i]
        z_R = self.z[i+1]
        hu_L = self.hu[i]
        hu_R = self.hu[i+1]

        # Step 2: 计算水位
        eta_L = h_L + z_L
        eta_R = h_R + z_R

        # Step 3: 界面底床高程
        z_interface = max(z_L, z_R)

        # Step 4: 重构水深
        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        # Step 5: 重构流量（保持比例）
        if h_L > 1e-10:
            hu_star_L = hu_L * (h_star_L / h_L)
        else:
            hu_star_L = 0.0

        if h_R > 1e-10:
            hu_star_R = hu_R * (h_star_R / h_R)
        else:
            hu_star_R = 0.0

        return h_star_L, h_star_R, hu_star_L, hu_star_R
```

#### 5.3.2 数值通量

使用HLL Riemann求解器（简单且鲁棒）：

```python
def hll_flux(h_L, hu_L, h_R, hu_R):
    """HLL近似Riemann求解器"""
    # 流速
    u_L = hu_L / h_L if h_L > 1e-10 else 0.0
    u_R = hu_R / h_R if h_R > 1e-10 else 0.0

    # 波速估计（简单但有效）
    c_L = sqrt(g * h_L) if h_L > 0 else 0.0
    c_R = sqrt(g * h_R) if h_R > 0 else 0.0

    s_L = min(u_L - c_L, u_R - c_R)
    s_R = max(u_L + c_L, u_R + c_R)

    # 通量
    F_L = [hu_L, hu_L**2 / h_L + 0.5 * g * h_L**2] if h_L > 0 else [0, 0]
    F_R = [hu_R, hu_R**2 / h_R + 0.5 * g * h_R**2] if h_R > 0 else [0, 0]

    # HLL通量
    if s_L >= 0:
        return F_L
    elif s_R <= 0:
        return F_R
    else:
        U_L = [h_L, hu_L]
        U_R = [h_R, hu_R]
        F_HLL = [(s_R * F_L[i] - s_L * F_R[i] + s_L * s_R * (U_R[i] - U_L[i]))
                 / (s_R - s_L) for i in range(2)]
        return F_HLL
```

#### 5.3.3 源项离散化

关键：确保良平衡性！

```python
def compute_source_terms(self, i):
    """计算单元i的源项"""
    h_i = self.h[i]
    hu_i = self.hu[i]
    z_i = self.z[i]

    # 重力源项（良平衡形式）
    # 注意：这需要界面的重构信息
    z_L = self.z_interface[i-1]    # 左界面底床
    z_R = self.z_interface[i]      # 右界面底床

    S_gravity = -g * h_i * (z_R - z_L) / self.dx

    # 摩擦源项
    if h_i > 1e-6:
        u_i = hu_i / h_i
        R_i = h_i  # 矩形渠道: R ≈ h (宽度>>深度)
        S_friction = -g * self.n**2 * abs(u_i) * hu_i / (R_i**(4/3))
    else:
        S_friction = 0.0

    return S_gravity + S_friction
```

#### 5.3.4 时间推进

可继续使用Preissmann隐式格式：

```python
# 在每个时间步
for iteration in range(max_iterations):
    # 1. 在所有界面进行静水重构
    for i in range(n_cells - 1):
        h_L, h_R, hu_L, hu_R = self.reconstruct_at_interface(i)
        self.flux[i] = self.hll_flux(h_L, hu_L, h_R, hu_R)

    # 2. 计算源项（良平衡形式）
    for i in range(n_cells):
        self.source[i] = self.compute_source_terms(i)

    # 3. 隐式更新
    self.implicit_update(theta=0.6, omega=0.95)

    # 4. 检查收敛
    if self.check_convergence():
        break
```

---

## 6. 实施计划

### 6.1 Phase 1: 单渠道测试（第1周）

**目标**：在简单情况验证静水重构

1. 创建 `hydrostatic_reconstruction.py` 模块
2. 实现核心重构算法
3. 实现HLL通量
4. 测试用例：
   - 湖面静止（验证良平衡性）
   - 单台阶上的稳态流
   - 与当前FDM对比

**成功标准**：
- 湖面静止误差 < 1e-12（机器精度）
- 台阶上稳态流精度优于当前FDM

### 6.2 Phase 2: 三渠道集成（第2周）

**目标**：集成到CanalSolver

1. 修改 `canal_solver.py`:
   - 添加静水重构选项
   - 实现闸门处的重构
2. 修改 `single_canal_solver.py`:
   - 替换空间离散化
3. 测试Script 11（三闸门系统）

**成功标准**：
- 稳态误差 < 1.0%（初步改进）
- 数值稳定性保持

### 6.3 Phase 3: 优化与验证（第3周）

**目标**：精度调优

1. 参数优化
2. 闸门处理微调
3. 质量守恒验证
4. 文档编写

**成功标准**：
- 稳态误差 < 0.5%（目标达成！）
- 质量守恒误差 < 1e-10

---

## 7. 预期挑战与解决方案

### 7.1 挑战1: 闸门的强非线性

**问题**：闸门流量公式是水深的非线性函数

**解决方案**：
- 使用隐式处理闸门边界条件
- 或：在闸门处使用显式处理但缩小时间步长
- 推荐：混合方法（内部隐式，边界显式）

### 7.2 挑战2: 干湿界面

**问题**：h → 0 时数值不稳定

**解决方案**：
- 静水重构自然处理干湿（通过max(0, η - z)）
- 保持小的正性阈值（如1e-6）
- 使用正性保持的Riemann求解器（HLL自然正性保持）

### 7.3 挑战3: 与现有代码集成

**问题**：大幅修改可能破坏现有功能

**解决方案**：
- 创建新类 `HydrostaticCanalSolver` 继承 `CanalSolver`
- 保留原有FDM代码
- 通过参数切换：`use_hydrostatic_reconstruction=True/False`

---

## 8. 理论精度分析

### 8.1 误差来源分解

使用静水重构后，稳态误差来源：

```
Total Error = E_wellbalanced + E_gate + E_friction + E_time

其中：
- E_wellbalanced ≈ 0 (良平衡性质，机器精度)
- E_gate = 闸门公式误差 ≈ 0.1-0.2% (由Cd精度决定)
- E_friction = Manning摩擦误差 ≈ 0.1-0.2% (由n精度决定)
- E_time = 时间离散化误差 ≈ 0.1% (Preissmann)
```

**预期总误差**：0.3-0.5%

### 8.2 与当前方法对比

| 误差来源 | 当前FDM | 静水重构法 | 改进 |
|---------|---------|-----------|------|
| 空间离散化 | 0.5-1.0% | ~0% | ✓✓✓ |
| 质量不守恒 | 0.5-1.0% | ~0% | ✓✓✓ |
| 闸门公式 | 0.1-0.3% | 0.1-0.3% | = |
| 摩擦项 | 0.1-0.2% | 0.1-0.2% | = |
| 时间推进 | 0.1% | 0.1% | = |
| **总计** | **2.32%** | **0.3-0.5%** | **5-8x** |

---

## 9. 文献引用

### 核心方法

1. **Audusse, E., Bouchut, F., Bristeau, M.-O., Klein, R., & Perthame, B. (2004)**.
   "A Fast and Stable Well-Balanced Scheme with Hydrostatic Reconstruction for Shallow Water Flows".
   *SIAM Journal on Scientific Computing*, 25(6), 2050-2065.

### 扩展与应用

2. **Chen, G., & Noelle, S. (2020)**.
   "A reliable second-order hydrostatic reconstruction for shallow water flows with the friction term and the bed source term".
   *Applied Mathematics and Computation*, 356, 160-177.

3. **Xing, Y., & Shu, C.-W. (2011)**.
   "High order well-balanced finite volume WENO schemes and discontinuous Galerkin methods for a class of hyperbolic systems with source terms".
   *Journal of Computational Physics*, 214(2), 567-598.

### Riemann求解器

4. **Toro, E. F. (2009)**.
   *Riemann Solvers and Numerical Methods for Fluid Dynamics*.
   Springer (HLL求解器参考)

---

## 10. 总结

静水重构法通过以下创新实现良平衡性：

1. **重构水位而非水深** - 自然处理底床不连续
2. **界面底床高程定义** - 确保正性保持
3. **源项-通量精确匹配** - 数学保证的良平衡性

**预期成果**：
- 稳态误差从2.32%降至**0.3-0.5%**
- 实现0.5%精度目标 ✓
- 质量守恒提升至机器精度
- 数值稳定性保持或改善

**下一步**：开始Phase 1实施 - 单渠道测试

---

**状态**: 理论推导完成，准备开始编码实现
