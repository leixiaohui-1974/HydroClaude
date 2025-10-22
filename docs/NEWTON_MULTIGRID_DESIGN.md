# 牛顿法+多网格组合方案设计文档

## 概述

本文档描述HydroClaude项目中牛顿法+多网格组合求解器的设计，用于加速闸控条件下的非恒定流模拟。

**目标**：提升例子1和2的收敛速度和数值稳定性

**日期**：2025-10-22
**作者**：Claude

---

## 1. 背景与动机

### 当前实现的局限性

1. **固定点迭代收敛慢**：
   - 当前使用松弛迭代法（固定点迭代）
   - 即使使用Aitken加速，收敛速度仍然较慢
   - 对于多闸门和复杂结构，迭代次数可达数千次

2. **单一网格限制**：
   - 所有计算在固定网格上进行
   - 无法利用粗网格快速传播全局信息
   - 低频误差收敛极慢

3. **非线性耦合处理效率低**：
   - 闸门边界条件通过迭代松弛处理
   - 与流场求解分离，效率低

### 新方案的优势

1. **牛顿法**：
   - 二次收敛速率（接近解时）
   - 全局求解，同时处理流场和边界条件
   - 适合强非线性问题

2. **多网格方法**：
   - 快速消除低频误差
   - O(N)复杂度（最优）
   - 大幅减少线性系统求解时间

3. **组合方案**：
   - 牛顿法提供二次收敛
   - 多网格加速每步线性系统求解
   - 协同作用，性能倍增

---

## 2. 数学框架

### 2.1 稳态Saint-Venant方程

连续性方程：
```
dQ/dx = 0  →  Q = const
```

动量方程：
```
d(Q²/A)/dx + gA·dh/dx = gA(S₀ - Sf)
```

其中：
- h: 水深
- Q: 流量
- A = B·h: 断面面积（矩形断面）
- Sf: Manning摩阻坡度 = (n·V)²/R^(4/3)
- S₀: 渠底坡度

### 2.2 离散化（有限差分）

空间网格：x_i, i = 1,2,...,N
状态向量：U = [h_1, Q_1, h_2, Q_2, ..., h_N, Q_N]^T

**连续性方程**（节点i）：
```
(Q_{i+1} - Q_{i-1})/(2Δx) = 0
```

**动量方程**（节点i）：
```
d(Q²/A)/dx|_i + gA_i·(h_{i+1} - h_{i-1})/(2Δx) = gA_i(S₀ - Sf_i)
```

### 2.3 闸门边界条件

对于闸门位置节点j：
```
Q_j = C_d·B·e·√(2g·Δh)  （淹没出流）
Q_j = C_d·B·e·√(2g·h_{up})  （自由出流）
```

其中：
- e: 闸门开度
- h_{up}: 上游水深（h_{j-1}）
- Δh: 上下游水位差（h_{j-1} - h_{j+1}）

### 2.4 非线性系统

**形式**：F(U) = 0

F包含：
- 连续性方程残差（N个）
- 动量方程残差（N个）
- 闸门流量约束（M个，M为闸门数）
- 边界条件（2个）

**总维度**：2N + M + 2

---

## 3. 牛顿法求解器

### 3.1 牛顿迭代公式

```
U^{k+1} = U^k - J^{-1}(U^k) · F(U^k)
```

等价于求解线性系统：
```
J(U^k) · ΔU = -F(U^k)
U^{k+1} = U^k + ΔU
```

### 3.2 Jacobian矩阵结构

J是稀疏矩阵，具有带状结构：

```
J = [∂F₁/∂h₁  ∂F₁/∂Q₁  ∂F₁/∂h₂  ∂F₁/∂Q₂  ...  ]
    [∂F₂/∂h₁  ∂F₂/∂Q₁  ∂F₂/∂h₂  ∂F₂/∂Q₂  ...  ]
    [  ...      ...      ...      ...      ...  ]
```

**带宽**：约为5（对于标准节点）
**闸门节点**：额外的非零元素

### 3.3 Jacobian计算方法

**选项1：解析Jacobian**（推荐）
- 手动推导每个方程对每个变量的偏导数
- 精确，快速
- 需要仔细编程

**选项2：数值Jacobian**（备选）
- 有限差分近似：∂F_i/∂U_j ≈ (F_i(U+εe_j) - F_i(U))/ε
- 简单，但计算量大
- 可用于验证解析Jacobian

### 3.4 收敛准则

```
||F(U^k)|| < tol₁  （残差足够小）
||ΔU|| < tol₂      （更新足够小）
```

典型值：tol₁ = 1e-6, tol₂ = 1e-8

---

## 4. 多网格方法

### 4.1 多网格层次

```
Level 0 (finest):   N = 401 points
Level 1:            N = 201 points
Level 2:            N = 101 points
Level 3 (coarsest): N = 51 points
```

限制：每层点数约为上层的1/2

### 4.2 V-Cycle算法

```
1. Pre-smoothing on fine grid (ν₁ iterations)
2. Compute residual: r = b - A·x
3. Restrict residual to coarse grid: r_c = R·r
4. Solve coarse grid problem: A_c·e_c = r_c
   (recursively or directly if coarsest level)
5. Prolongate correction: e = P·e_c
6. Update solution: x = x + e
7. Post-smoothing (ν₂ iterations)
```

### 4.3 限制算子（Restriction）

**全加权限制**：
```
r_c[i] = 0.25·r_f[2i-1] + 0.5·r_f[2i] + 0.25·r_f[2i+1]
```

### 4.4 延拓算子（Prolongation）

**线性插值**：
```
e_f[2i] = e_c[i]
e_f[2i+1] = 0.5·(e_c[i] + e_c[i+1])
```

### 4.5 平滑器

**Gauss-Seidel迭代**（红黑排序）：
- Red sweep: 更新偶数索引节点
- Black sweep: 更新奇数索引节点
- 高效，易并行

### 4.6 粗网格求解器

最粗层直接求解：
- 使用稀疏LU分解（scipy.sparse.linalg.spsolve）
- 或继续使用迭代法（如果层数多）

---

## 5. 组合方案：牛顿-多网格求解器

### 5.1 算法流程

```python
def newton_multigrid_solve(U_init, max_newton_iter=20):
    U = U_init

    for k in range(max_newton_iter):
        # 1. 计算残差和Jacobian
        F = compute_residual(U)
        J = compute_jacobian(U)

        # 2. 检查收敛
        if ||F|| < tol_residual and k > 0:
            return U, "converged"

        # 3. 使用多网格求解线性系统 J·ΔU = -F
        ΔU = multigrid_solve(J, -F, cycles=2)

        # 4. 线搜索（阻尼牛顿法）
        α = line_search(U, ΔU, F)

        # 5. 更新解
        U = U + α·ΔU

    return U, "max iterations"
```

### 5.2 关键优化

1. **阻尼牛顿法（Line Search）**：
   - 防止牛顿步长过大导致发散
   - 回溯线搜索确保 ||F(U+α·ΔU)|| < ||F(U)||

2. **初值策略**：
   - 使用恒定均匀流作为初值
   - 或使用上一时间步结果

3. **稀疏矩阵存储**：
   - 使用CSR格式存储Jacobian
   - 减少内存占用和计算量

4. **自适应网格层数**：
   - 根据总网格点数自动确定层数
   - 保证最粗层点数 > 20

---

## 6. 闸门边界条件处理

### 6.1 闸门方程嵌入

对于闸门位置j，替换动量方程为闸门流量约束：

**淹没出流**：
```
F_gate[j] = Q_j - C_d·B·e·√(2g·(h_{j-1} - h_{j+1}))
```

**Jacobian贡献**：
```
∂F_gate/∂Q_j = 1
∂F_gate/∂h_{j-1} = -C_d·B·e·g/√(2g·Δh)
∂F_gate/∂h_{j+1} = C_d·B·e·g/√(2g·Δh)
```

### 6.2 流态自动判断

```python
if h_{j+1} > 0.67·h_{j-1}:  # 淹没出流
    Q_gate = C_d·B·e·√(2g·Δh)
else:  # 自由出流
    Q_gate = C_d·B·e·√(2g·h_{j-1})
```

---

## 7. 实现架构

### 7.1 文件结构

```
solvers/
├── newton_solver.py           # 牛顿法求解器
├── multigrid_solver.py        # 多网格求解器
└── newton_multigrid_solver.py # 组合求解器（主接口）

physics/
└── steady_saint_venant.py     # 稳态Saint-Venant方程残差和Jacobian

utils/
└── sparse_utils.py            # 稀疏矩阵工具
```

### 7.2 主要类

**NewtonSolver**
```python
class NewtonSolver:
    def solve(self, U_init, residual_func, jacobian_func, **kwargs):
        """牛顿法求解 F(U)=0"""
```

**MultiGridSolver**
```python
class MultiGridSolver:
    def solve(self, A, b, x_init, n_cycles=2):
        """多网格求解 A·x=b"""

    def v_cycle(self, level, A, b, x):
        """V-cycle递归"""
```

**NewtonMultiGridSolver**
```python
class NewtonMultiGridSolver:
    def solve_steady_state(self, Q_target, structures, **kwargs):
        """稳态求解（牛顿-多网格）"""
```

### 7.3 集成到SingleCanalSolver

新增方法：
```python
def solve_steady_state_newton(self, Q_target, max_newton_iter=20, **kwargs):
    """使用牛顿-多网格法求解稳态"""
```

保持向后兼容，原有方法不变。

---

## 8. 测试与验证

### 8.1 单元测试

1. **牛顿法测试**（无闸门）：
   - 恒定流解析解验证
   - 收敛速率验证（二次收敛）

2. **多网格测试**：
   - 简单线性系统验证
   - V-cycle收敛性验证

3. **Jacobian验证**：
   - 与数值Jacobian对比
   - 误差 < 1e-6

### 8.2 集成测试

1. **单闸门（例子1）**：
   - 对比原方法和牛顿-多网格法
   - 验证解的一致性
   - 统计迭代次数和时间

2. **多闸门（例子2）**：
   - 三闸门串联
   - 混合结构
   - 性能对比

### 8.3 性能基准

| 方法 | 迭代次数 | 计算时间 | 收敛精度 |
|------|---------|---------|---------|
| 固定松弛 | 基准 | 基准 | 基准 |
| 自适应松弛 | -20~40% | -15~30% | 相同 |
| 牛顿-多网格 | 目标：-60~80% | 目标：-50~70% | 更高 |

---

## 9. 性能优化策略

### 9.1 稀疏矩阵优化

- 使用CSR格式
- 预分配非零元素
- 避免重复计算

### 9.2 并行化

- OpenMP并行平滑器（未来）
- GPU加速（未来）

### 9.3 预条件子

- ILU预条件（可选）
- 多网格本身就是优秀的预条件子

---

## 10. 非恒定流扩展

### 10.1 时间离散

**隐式Euler**：
```
(h^{n+1} - h^n)/Δt + ∂Q/∂x = 0
(Q^{n+1} - Q^n)/Δt + ∂(Q²/A)/∂x + gA·∂h/∂x = gA(S₀ - Sf)
```

**非线性系统**：F(U^{n+1}, U^n, Δt) = 0

### 10.2 牛顿-多网格应用

每个时间步：
```
U^{n+1} = newton_multigrid_solve(U^n, Δt)
```

- 使用上一时间步作为初值（通常接近解）
- 牛顿法快速收敛（3-5次迭代）

---

## 11. 实施计划

### 阶段1：基础实现（核心功能）
- [ ] 实现NewtonSolver类
- [ ] 实现MultiGridSolver类
- [ ] 实现稳态Saint-Venant残差和Jacobian
- [ ] 单元测试（无闸门）

### 阶段2：闸门集成
- [ ] 闸门边界条件嵌入Jacobian
- [ ] 多闸门支持
- [ ] 集成测试（例子1和2）

### 阶段3：优化与验证
- [ ] 性能对比
- [ ] 参数调优
- [ ] 文档完善

### 阶段4：非恒定流扩展（可选）
- [ ] 隐式时间离散
- [ ] 动态闸门响应
- [ ] 动画可视化

---

## 12. 参考文献

1. Briggs, W. L., Henson, V. E., & McCormick, S. F. (2000). *A Multigrid Tutorial* (2nd ed.). SIAM.

2. Nocedal, J., & Wright, S. J. (2006). *Numerical Optimization* (2nd ed.). Springer.

3. Trottenberg, U., Oosterlee, C. W., & Schuller, A. (2000). *Multigrid*. Academic Press.

4. Cunge, J. A., Holly, F. M., & Verwey, A. (1980). *Practical Aspects of Computational River Hydraulics*. Pitman.

---

## 附录A：符号表

| 符号 | 含义 | 单位 |
|-----|------|------|
| h | 水深 | m |
| Q | 流量 | m³/s |
| A | 断面面积 | m² |
| B | 渠宽 | m |
| S₀ | 渠底坡度 | - |
| Sf | 摩阻坡度 | - |
| n | Manning糙率 | s/m^(1/3) |
| g | 重力加速度 | m/s² |
| Cd | 流量系数 | - |
| e | 闸门开度 | m |
| Δx | 空间步长 | m |
| Δt | 时间步长 | s |
| U | 状态向量 | - |
| F | 残差向量 | - |
| J | Jacobian矩阵 | - |

---

**文档版本**：1.0
**最后更新**：2025-10-22
