# 混合求解器设计文档

## 作者
Claude

## 日期
2025-10-22

## 目标

设计一个混合求解器，结合迭代法和牛顿法的优势：
- **迭代法**：全局收敛性好，对初值不敏感，但速度慢
- **牛顿法**：局部收敛速度快（二次收敛），但对初值敏感

## 核心思想

**两阶段求解策略**：

```
初始猜测
    ↓
┌─────────────────────┐
│ 阶段1：迭代法粗求解 │
│  - 伪时间步进      │
│  - Aitken加速       │
│  - 宽松收敛判据    │
└─────────────────────┘
    ↓ (残差 < 切换阈值)
┌─────────────────────┐
│ 阶段2：Newton精细化 │
│  - 伪瞬态延拓      │
│  - 解析Jacobian     │
│  - 严格收敛判据    │
└─────────────────────┘
    ↓
  高精度解
```

## 设计参数

### 阶段1参数（迭代法）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `iter_max_iter` | 1000 | 最大迭代次数 |
| `iter_tol` | 0.05 | 相对残差容差（5%） |
| `adaptive_relax` | True | Aitken自适应松弛 |
| `switch_threshold` | 0.1 | 切换到Newton的残差阈值（10%） |

**目标**：快速收敛到解的邻域，不需要很精确

### 阶段2参数（Newton）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `newton_max_iter` | 20 | 最大迭代次数 |
| `newton_tol` | 1e-4 | 绝对残差容差 |
| `line_search` | True | 启用线搜索 |
| `pseudo_dt` | 0.1 | 伪时间步长 |

**目标**：从粗解快速收敛到高精度解

## 自适应切换策略

### 策略1：残差阈值切换（推荐）

当相对残差 `||R|| / ||R_0|| < switch_threshold` 时切换到Newton

**优点**：
- 简单直观
- 确保在解的邻域内切换
- 适用于大多数场景

**缺点**：
- 固定阈值可能不适合所有问题

### 策略2：收敛速率监控

监控最近N次迭代的收敛速率：
```
rate = ||R_k|| / ||R_{k-1}||
```

当 `rate > 0.95` 连续M次（收敛缓慢），切换到Newton

**优点**：
- 动态适应不同问题
- 避免在快速收敛时过早切换

**缺点**：
- 需要调整N和M参数
- 实现稍复杂

### 策略3：混合策略（最佳）

结合策略1和策略2：
```python
if residual_ratio < switch_threshold:
    switch to Newton
elif iteration > iter_min and convergence_rate > 0.95:
    switch to Newton
```

## API设计

### HybridSolver类

```python
class HybridSolver:
    """
    混合求解器：迭代法 + 牛顿法

    工作流程：
    1. 迭代法粗求解（快速到达解的邻域）
    2. 自动切换到Newton（快速精细化）
    """

    def __init__(self,
                 # 阶段1：迭代法
                 iter_max_iter: int = 1000,
                 iter_tol: float = 0.05,
                 switch_threshold: float = 0.1,
                 # 阶段2：Newton
                 newton_max_iter: int = 20,
                 newton_tol: float = 1e-4,
                 pseudo_dt: float = 0.1,
                 # 其他
                 verbose: bool = True):
        pass

    def solve(self, system, U_init: np.ndarray, t: float = 0.0):
        """
        求解非线性系统

        Args:
            system: SteadySaintVenantSystem实例
            U_init: 初值
            t: 时间

        Returns:
            U_solution: 解
            info: 求解信息
        """
        pass
```

### 求解信息

```python
info = {
    'converged': bool,
    'phase1_iterations': int,
    'phase2_iterations': int,
    'total_iterations': int,
    'phase1_time': float,
    'phase2_time': float,
    'total_time': float,
    'final_residual': float,
    'switched_at_iteration': int
}
```

## 实现细节

### 阶段1：迭代法（简化版）

```python
def _solve_iterative_phase(self, system, U_init, t):
    """迭代法粗求解"""

    U = U_init.copy()
    h, Q = system.unpack_state(U)

    # Aitken参数
    alpha = 1.0
    alpha_prev = 1.0

    for k in range(self.iter_max_iter):
        # 计算残差
        F = system.compute_residual(U, t)
        residual_norm = np.linalg.norm(F)

        if k == 0:
            residual_0 = residual_norm

        residual_ratio = residual_norm / residual_0

        # 检查是否切换
        if residual_ratio < self.switch_threshold:
            return U, k, residual_norm

        # 检查收敛
        if residual_ratio < self.iter_tol:
            return U, k, residual_norm

        # 伪时间步进
        U_new = U - alpha * F * system.pseudo_dt

        # Aitken加速
        if k > 0:
            alpha = self._compute_aitken_alpha(U, U_new, U_prev, alpha_prev)

        U_prev = U.copy()
        alpha_prev = alpha
        U = U_new

    return U, self.iter_max_iter, residual_norm
```

### 阶段2：Newton精细化

直接调用NewtonSolver：

```python
def _solve_newton_phase(self, system, U_init, t):
    """Newton精细化"""

    newton = NewtonSolver(
        max_iter=self.newton_max_iter,
        tol_residual=self.newton_tol,
        line_search=True,
        verbose=False
    )

    U_sol, info = newton.solve(
        U_init=U_init,
        residual_func=lambda U: system.compute_residual(U, t),
        jacobian_func=lambda U: system.compute_jacobian(U, t)
    )

    return U_sol, info
```

## 性能分析

### 预期性能（三闸门场景）

| 方法 | 迭代次数 | 时间 | 说明 |
|------|---------|------|------|
| 纯迭代法 | ~6000 | ~10s | 收敛慢 |
| 纯Newton | ~5 | ~0.1s | 需要好初值 |
| 混合求解器 | 200+5 | ~0.5s | **兼顾鲁棒性和速度** |

**加速比**：
- 相比纯迭代法：20x
- 接近纯Newton（初值好时）

### 优势

1. **鲁棒性**：对初值不敏感（迭代法容忍差初值）
2. **效率**：比纯迭代法快20倍以上
3. **精度**：Newton保证高精度（1e-4级别）
4. **自动化**：自适应切换，无需手动调参

## 测试场景

### 测试1：均匀流初值（容易）
- 初值：均匀流（接近真解）
- 预期：快速切换，总迭代<50

### 测试2：零初值（困难）
- 初值：h=0.1m, Q=0 （远离真解）
- 预期：迭代法稳定收敛，切换后Newton快速完成

### 测试3：三闸门（实际场景）
- 初值：均匀流
- 预期：200次迭代 + 5次Newton ≈ 0.5s

### 测试4：极端初值（压力测试）
- 初值：h=10m, Q=100 （远远偏离）
- 预期：迭代法缓慢收敛，最终切换

## 扩展方向

### 1. 多级延拓

```
粗网格求解
    ↓
中等网格求解（插值粗网格解）
    ↓
细网格求解（插值中等网格解）
```

### 2. 自适应pseudo_dt

```python
if convergence_slow:
    pseudo_dt *= 0.5  # 减小时间步
elif convergence_fast:
    pseudo_dt *= 1.5  # 增大时间步
```

### 3. 智能重启

如果Newton失败，回退到迭代法继续：

```python
if not newton_converged:
    U = continue_iteration(U_phase1, more_iterations=500)
    retry_newton(U)
```

## 实现清单

- [ ] `solvers/hybrid_solver.py` - 主实现
- [ ] `tests/test_hybrid_solver.py` - 单元测试
- [ ] `tests/benchmark_hybrid.py` - 性能对比
- [ ] `examples/example_hybrid_solver.py` - 使用示例
- [ ] 更新文档

## 参考

1. Kelley, C.T. (1995). Iterative Methods for Linear and Nonlinear Equations
2. Knoll, D.A. & Keyes, D.E. (2004). Jacobian-free Newton-Krylov methods
3. 伪瞬态延拓：Kelley & Keyes (1998)

---

**版本**: v1.0
**状态**: 设计完成，待实现
