# WENO方法理论与设计

**Phase 2 - 任务1**  
**日期**: 2025-10-27  
**作者**: HydroClaude Development Team

---

## 📚 1. WENO方法概述

### 1.1 什么是WENO？

**WENO**: Weighted Essentially Non-Oscillatory

**核心思想**：
- 使用多个模板（stencils）的凸组合进行高阶重构
- 根据局部光滑性动态调整权重
- 光滑区域自动达到高阶精度
- 间断处自动降阶，避免振荡

### 1.2 为什么需要WENO？

**Phase 1限制**：
- 当前使用1阶迎风格式
- 激波、间断处有数值耗散
- Dam Break等问题精度受限

**WENO优势**：
- 高阶精度（3-5阶）
- 激波捕捉准确
- 自动识别间断
- 无需人工切换

---

## 🔬 2. WENO-3 算法（3阶精度）

### 2.1 基本框架

对于守恒律方程：
\[
\frac{\partial U}{\partial t} + \frac{\partial F(U)}{\partial x} = S
\]

**空间离散**（WENO重构）：
\[
F_{i+1/2} = F(U^-_{i+1/2}, U^+_{i+1/2})
\]

其中 \(U^-_{i+1/2}\) 通过WENO重构从左侧值得到。

### 2.2 WENO-3 重构步骤

#### 步骤1: 定义2个模板

**模板1**（左偏）：使用 \(U_{i-1}, U_i\)
\[
p_1(x) = U_i + \frac{U_i - U_{i-1}}{\Delta x}(x - x_i)
\]

在 \(x_{i+1/2}\) 处：
\[
U^{(1)}_{i+1/2} = \frac{3}{2}U_i - \frac{1}{2}U_{i-1}
\]

**模板2**（右偏）：使用 \(U_i, U_{i+1}\)
\[
p_2(x) = U_i + \frac{U_{i+1} - U_i}{\Delta x}(x - x_i)
\]

在 \(x_{i+1/2}\) 处：
\[
U^{(2)}_{i+1/2} = \frac{1}{2}U_i + \frac{1}{2}U_{i+1}
\]

#### 步骤2: 计算光滑性指标

**光滑性指标** \(\beta_k\) 衡量模板内的光滑程度：

\[
\beta_1 = (U_i - U_{i-1})^2
\]

\[
\beta_2 = (U_{i+1} - U_i)^2
\]

#### 步骤3: 计算非线性权重

**理想权重**（光滑情况下）：
\[
d_1 = \frac{1}{3}, \quad d_2 = \frac{2}{3}
\]

**非线性权重**：
\[
\alpha_k = \frac{d_k}{(\epsilon + \beta_k)^2}
\]

\[
\omega_k = \frac{\alpha_k}{\sum_j \alpha_j}
\]

其中 \(\epsilon = 10^{-6}\) 是一个小量，防止分母为零。

#### 步骤4: WENO重构

\[
U^-_{i+1/2} = \omega_1 U^{(1)}_{i+1/2} + \omega_2 U^{(2)}_{i+1/2}
\]

### 2.3 WENO-3 特性

- **阶数**: 3阶精度
- **模板数**: 2个
- **模板宽度**: 2个格点
- **计算量**: 约为1阶的1.5-2倍

---

## 🔬 3. WENO-5 算法（5阶精度）

### 3.1 基本框架

使用3个模板，每个宽度3个格点。

### 3.2 WENO-5 重构步骤

#### 步骤1: 定义3个模板

**模板1**（最左）：使用 \(U_{i-2}, U_{i-1}, U_i\)
\[
U^{(1)}_{i+1/2} = \frac{1}{3}U_{i-2} - \frac{7}{6}U_{i-1} + \frac{11}{6}U_i
\]

**模板2**（中间）：使用 \(U_{i-1}, U_i, U_{i+1}\)
\[
U^{(2)}_{i+1/2} = -\frac{1}{6}U_{i-1} + \frac{5}{6}U_i + \frac{1}{3}U_{i+1}
\]

**模板3**（最右）：使用 \(U_i, U_{i+1}, U_{i+2}\)
\[
U^{(3)}_{i+1/2} = \frac{1}{3}U_i + \frac{5}{6}U_{i+1} - \frac{1}{6}U_{i+2}
\]

#### 步骤2: 计算光滑性指标

**Jiang & Shu (1996) 公式**：

\[
\beta_1 = \frac{13}{12}(U_{i-2} - 2U_{i-1} + U_i)^2 + \frac{1}{4}(U_{i-2} - 4U_{i-1} + 3U_i)^2
\]

\[
\beta_2 = \frac{13}{12}(U_{i-1} - 2U_i + U_{i+1})^2 + \frac{1}{4}(U_{i-1} - U_{i+1})^2
\]

\[
\beta_3 = \frac{13}{12}(U_i - 2U_{i+1} + U_{i+2})^2 + \frac{1}{4}(3U_i - 4U_{i+1} + U_{i+2})^2
\]

#### 步骤3: 计算非线性权重

**理想权重**：
\[
d_1 = \frac{1}{10}, \quad d_2 = \frac{6}{10}, \quad d_3 = \frac{3}{10}
\]

**非线性权重**（同WENO-3）：
\[
\alpha_k = \frac{d_k}{(\epsilon + \beta_k)^2}, \quad \omega_k = \frac{\alpha_k}{\sum_j \alpha_j}
\]

#### 步骤4: WENO重构

\[
U^-_{i+1/2} = \omega_1 U^{(1)}_{i+1/2} + \omega_2 U^{(2)}_{i+1/2} + \omega_3 U^{(3)}_{i+1/2}
\]

### 3.3 WENO-5 特性

- **阶数**: 5阶精度
- **模板数**: 3个
- **模板宽度**: 3个格点（需要2层ghost cells）
- **计算量**: 约为1阶的2-3倍

---

## 🏗️ 4. 实现设计

### 4.1 总体架构

```
GodunvFVMWENO
├── __init__()         # 初始化（继承Phase 1）
├── weno_reconstruct() # WENO重构（新增）⭐
├── compute_fluxes()   # 通量计算（修改）
└── step()             # 时间推进（保持）
```

### 4.2 WENO重构接口设计

```python
def weno_reconstruct(self, U: np.ndarray, order: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    WENO重构
    
    Args:
        U: 守恒变量数组（包含ghost cells）
        order: WENO阶数（3 or 5）
    
    Returns:
        U_left: 界面左侧重构值 U^-_{i+1/2}
        U_right: 界面右侧重构值 U^+_{i+1/2}
    """
    if order == 3:
        return self._weno3_reconstruct(U)
    elif order == 5:
        return self._weno5_reconstruct(U)
    else:
        raise ValueError(f"Unsupported WENO order: {order}")
```

### 4.3 WENO-3 实现框架

```python
def _weno3_reconstruct(self, U: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    WENO-3 重构（3阶精度）
    
    模板:
        Stencil 1 (左偏): U_{i-1}, U_i
        Stencil 2 (右偏): U_i, U_{i+1}
    
    理想权重: d1=1/3, d2=2/3
    """
    n = len(U) - 2  # 去除ghost cells
    U_left = np.zeros(n + 1)  # 界面左侧值
    U_right = np.zeros(n + 1)  # 界面右侧值
    
    epsilon = 1e-6  # 防止除零
    
    # 对每个界面 i+1/2 进行重构
    for i in range(1, n + 1):  # i对应U[i]（包含ghost cell）
        # === 左侧重构 U^-_{i+1/2} ===
        
        # 模板1: U_{i-1}, U_i
        U1 = 1.5 * U[i] - 0.5 * U[i-1]
        
        # 模板2: U_i, U_{i+1}
        U2 = 0.5 * U[i] + 0.5 * U[i+1]
        
        # 光滑性指标
        beta1 = (U[i] - U[i-1])**2
        beta2 = (U[i+1] - U[i])**2
        
        # 非线性权重
        alpha1 = (1.0/3.0) / (epsilon + beta1)**2
        alpha2 = (2.0/3.0) / (epsilon + beta2)**2
        
        sum_alpha = alpha1 + alpha2
        omega1 = alpha1 / sum_alpha
        omega2 = alpha2 / sum_alpha
        
        # WENO重构
        U_left[i] = omega1 * U1 + omega2 * U2
        
        # === 右侧重构 U^+_{i+1/2} (镜像过程) ===
        # (从i+1侧重构)
        U1_r = 1.5 * U[i+1] - 0.5 * U[i+2]
        U2_r = 0.5 * U[i+1] + 0.5 * U[i]
        
        beta1_r = (U[i+1] - U[i+2])**2
        beta2_r = (U[i] - U[i+1])**2
        
        alpha1_r = (1.0/3.0) / (epsilon + beta1_r)**2
        alpha2_r = (2.0/3.0) / (epsilon + beta2_r)**2
        
        sum_alpha_r = alpha1_r + alpha2_r
        omega1_r = alpha1_r / sum_alpha_r
        omega2_r = alpha2_r / sum_alpha_r
        
        U_right[i] = omega1_r * U1_r + omega2_r * U2_r
    
    return U_left, U_right
```

### 4.4 Ghost Cells 处理

**WENO-3需要**：
- 左边界：1层ghost cell
- 右边界：1层ghost cell

**WENO-5需要**：
- 左边界：2层ghost cells
- 右边界：2层ghost cells

**Ghost cells填充策略**：
1. **透射边界**：外推（保持梯度）
2. **固定值边界**：直接赋值
3. **固定流量边界**：特殊处理

---

## 🏗️ 5. 集成到Godunov-FVM

### 5.1 修改compute_fluxes()

```python
def compute_fluxes(self):
    """
    计算界面通量（集成WENO重构）
    """
    if self.order >= 3:
        # WENO重构
        h_left, h_right = self.weno_reconstruct(self.h_with_ghost, self.order)
        Q_left, Q_right = self.weno_reconstruct(self.Q_with_ghost, self.order)
    else:
        # 1阶迎风（Phase 1）
        h_left = self.h[:-1]
        h_right = self.h[1:]
        Q_left = self.Q[:-1]
        Q_right = self.Q[1:]
    
    # HLL Riemann求解器（Phase 1已有）
    fluxes_h, fluxes_Q = self.hll_flux(h_left, h_right, Q_left, Q_right)
    
    return fluxes_h, fluxes_Q
```

### 5.2 数据结构调整

```python
def __init__(self, ..., order=1):
    """
    参数:
        order: 空间精度阶数
               1 = 一阶迎风（Phase 1）
               3 = WENO-3
               5 = WENO-5
    """
    self.order = order
    
    # 确定ghost cells层数
    if order == 1:
        self.n_ghost = 1
    elif order == 3:
        self.n_ghost = 1
    elif order == 5:
        self.n_ghost = 2
    else:
        raise ValueError(f"Unsupported order: {order}")
    
    # 扩展数组（包含ghost cells）
    self.h_with_ghost = np.zeros(n_cells + 2 * self.n_ghost)
    self.Q_with_ghost = np.zeros(n_cells + 2 * self.n_ghost)
```

---

## 🧪 6. 测试与验证

### 6.1 精度收敛性测试

**Sod激波管问题**（经典测试）：

不同网格下测试收敛率：
- N=50, 100, 200, 400, 800

理论收敛率：
- 1阶: slope = 1.0
- WENO-3: slope = 3.0
- WENO-5: slope = 5.0

### 6.2 Dam Break测试

**Phase 1基准**：
- 一阶HLL: ~90%精度
- HLLC: 97.5%精度

**WENO-3目标**: >98%
**WENO-5目标**: >99%

### 6.3 质量守恒测试

**要求**: 质量误差 < 1%（保持Phase 1水平）

---

## ⚙️ 7. 实现技巧

### 7.1 数值稳定性

**技巧1**: epsilon参数调优
- 标准值：\(\epsilon = 10^{-6}\)
- 如振荡：增大到 \(10^{-5}\)
- 如精度损失：减小到 \(10^{-7}\)

**技巧2**: 权重下限
```python
omega_k = max(omega_k, 1e-10)  # 避免极端小权重
```

**技巧3**: 限幅器结合
- WENO保证高阶
- TVD限幅器保证单调性
- 可选：WENO + minmod限幅器

### 7.2 计算效率优化

**优化1**: 向量化计算
```python
# ❌ 慢：循环
for i in range(n):
    beta[i] = (U[i] - U[i-1])**2

# ✅ 快：NumPy向量化
beta = (U[1:] - U[:-1])**2
```

**优化2**: 避免重复计算
```python
# 预计算光滑性指标，左右重构共用
beta = self._compute_smoothness(U)
```

**优化3**: 分段WENO
- 光滑区域：高阶WENO
- 间断区域：降至1阶或2阶
- 自动识别

---

## 📊 8. 预期性能

### 8.1 精度提升

| 测试 | Phase 1 (1阶) | WENO-3 | WENO-5 |
|------|--------------|--------|--------|
| **Dam Break** | ~90% | >98% | >99% |
| **激波管** | 低 | 中 | 高 |
| **收敛率** | 1.0 | 3.0 | 5.0 |

### 8.2 计算成本

| 求解器 | 相对时间 | 说明 |
|--------|---------|------|
| **Phase 1 (1阶)** | 1.0x | 基准 |
| **WENO-3** | 1.5-2.0x | 可接受 |
| **WENO-5** | 2.0-3.0x | 可接受 |

### 8.3 内存使用

| 求解器 | Ghost Cells | 内存增长 |
|--------|-------------|---------|
| **Phase 1** | 1层 | 1.0x |
| **WENO-3** | 1层 | ~1.0x |
| **WENO-5** | 2层 | ~1.02x |

---

## 🎯 9. 实现里程碑

### Milestone 1: WENO-3实现（Day 5-7）
- ✅ 2模板重构
- ✅ 光滑性指标
- ✅ 非线性权重
- ✅ 集成到FVM

### Milestone 2: WENO-5实现（Day 8-10）
- ✅ 3模板重构
- ✅ 复杂光滑性指标
- ✅ Ghost cells扩展

### Milestone 3: 验证完成（Day 12-14）
- ✅ 精度收敛性
- ✅ Dam Break >99%
- ✅ 质量守恒<1%

### Milestone 4: 文档完成（Day 15-16）
- ✅ 技术文档
- ✅ 使用手册
- ✅ 示例代码

---

## 📝 10. 开发检查清单

### 算法正确性
- [ ] WENO-3重构公式正确
- [ ] WENO-5重构公式正确
- [ ] 光滑性指标公式正确
- [ ] 理想权重正确

### 数值稳定性
- [ ] epsilon参数合理
- [ ] 无数值振荡
- [ ] 长时间稳定
- [ ] 质量守恒<1%

### 性能
- [ ] 计算时间可接受（<3倍）
- [ ] 内存使用合理
- [ ] 可向量化优化

### 易用性
- [ ] API清晰
- [ ] 文档完整
- [ ] 示例丰富
- [ ] 错误提示友好

---

## 🚀 下一步行动

### 即刻开始

**第1步**: 创建WENO-3求解器框架
- 文件：`solvers/godunov_fvm_weno3.py`
- 基础：复制`godunov_fvm_solver.py`
- 修改：添加WENO重构

**第2步**: 实现WENO-3重构函数
- 2模板重构
- 光滑性指标
- 非线性权重

**第3步**: 简单测试
- Sod激波管
- Dam Break
- 质量守恒

---

## 💡 关键要点

1. **渐进式开发** ✅
   - 先WENO-3，再WENO-5
   - 先简单测试，再复杂验证

2. **复用Phase 1** ✅
   - HLL Riemann求解器
   - TVD-RK2时间积分
   - 边界条件处理

3. **严格验证** ✅
   - 精度收敛性
   - Dam Break基准
   - 质量守恒

4. **文档先行** ✅
   - 理论推导
   - 实现细节
   - 使用指南

---

**Generated by**: HydroClaude Development Team  
**Date**: 2025-10-27  
**Status**: Phase 2 - WENO Development Started! 🚀

**下一步**: 创建WENO-3求解器框架
