# 混合流态求解器技术设计

**日期**: 2025-10-29
**目标**: 解决临界流（Fr≈1）不稳定问题
**参考**: HEC-RAS LPI方法, Toro (2001)

---

## 📋 问题背景

### 当前状态

**已识别的问题**：
1. MacDonald Test 4（无摩阻水跃）无法处理
2. 临界流测试失败（Fr≈1时崩溃）
3. 超临界→亚临界转换不稳定

**根本原因**：
- 标准Godunov+HLL方法在临界流区域数值振荡
- 无摩阻强激波缺乏物理耗散机制
- Fr≈1时特征值接近零导致数值不稳定

### 商业软件解决方案

**HEC-RAS**：
- 使用局部部分惯性（LPI - Local Partial Inertia）方法
- 在临界流区域切换到隐式格式
- 明确承认"标准方法在Fr≈1时不稳定"

**MIKE 11**：
- Abbott-Ionescu六点隐式格式
- 特殊的临界流处理
- 动量方程局部简化

---

## 🎯 设计目标

### 必须达成（P0）

1. ✅ 临界流（0.9 < Fr < 1.1）稳定计算
2. ✅ 质量守恒 < 5%
3. ✅ 无数值振荡

### 期望达成（P1）

4. ⏸️ MacDonald Test 4（无摩阻）通过
5. ⏸️ 超临界↔亚临界转换平滑
6. ⏸️ 性能影响 < 20%

### 可选达成（P2）

7. ⏸️ 自适应格式切换
8. ⏸️ 高阶精度维持

---

## 🔬 技术方案

### 方案A：Entropy修正 + 临界流检测（推荐）

**原理**：
- Harten-Hyman entropy fix处理sonic rarefaction
- 临界流区域特殊通量计算
- 保持显式格式框架

**优点**：
- 实现相对简单
- 不改变主体框架
- 计算效率高

**缺点**：
- 可能无法完全解决无摩阻水跃
- 精度可能略有损失

**实施难度**: ⭐⭐⭐ (中等)

### 方案B：LPI方法（参考HEC-RAS）

**原理**：
- 检测临界流区域
- 局部使用隐式求解或部分惯性近似
- 动态切换显式/隐式格式

**优点**：
- HEC-RAS验证的成熟方案
- 理论上最稳定

**缺点**：
- 实现复杂度高
- 需要隐式求解器
- 性能开销较大

**实施难度**: ⭐⭐⭐⭐⭐ (高)

### 方案C：混合Riemann求解器

**原理**：
- 在临界流区域使用HLLC或Roe求解器
- 其他区域使用HLL求解器
- 基于Fr动态选择

**优点**：
- 保持显式框架
- 实现难度适中

**缺点**：
- 需要实现多个Riemann求解器
- 格式切换可能引入误差

**实施难度**: ⭐⭐⭐⭐ (中高)

### 决策：采用方案A（阶段性）

**理由**：
1. 实现难度适中，可以快速验证效果
2. 不改变主体框架，风险低
3. 如果效果不理想，可以后续升级到方案B或C

**实施路径**：
```
Phase 1: Entropy修正 (3-4天)
Phase 2: 临界流检测 (2-3天)
Phase 3: 特殊通量处理 (3-4天)
Phase 4: 测试验证 (3-4天)
```

---

## 📐 数学原理

### 1. Froude数计算

```python
def compute_froude_number(h, Q, B, g=9.81):
    """
    计算Froude数

    Fr = u / sqrt(g*h)

    其中：
    - u = Q / A = Q / (B*h)  流速
    - c = sqrt(g*h)           波速
    """
    if h < 1e-6:
        return 0.0

    u = Q / (B * h)
    c = np.sqrt(g * h)
    Fr = u / c

    return Fr
```

### 2. 临界流检测

```python
def is_critical_flow(Fr, threshold=0.1):
    """
    检测临界流区域

    临界流：Fr ≈ 1
    阈值：通常取0.05-0.1
    """
    return abs(Fr - 1.0) < threshold
```

### 3. Harten-Hyman Entropy修正

**问题**：HLL求解器在稀疏波中过度耗散

**Entropy Fix原理**：

对于特征速度λ，如果 |λ| < δ（接近零），则：

```
λ_fixed = {
    λ                    if |λ| >= δ
    (λ² + δ²) / (2δ)    if |λ| < δ
}
```

其中δ是entropy修正参数，通常取：
- δ = 0.1 * max(|λ_L|, |λ_R|)

**作用**：
- 防止特征速度变号附近的数值振荡
- 保证熵条件满足
- 稳定sonic point附近的计算

**实现**：

```python
def entropy_fix(lambda_val, delta):
    """
    Harten-Hyman entropy修正

    参数:
        lambda_val: 特征速度
        delta: entropy修正参数
    """
    if abs(lambda_val) >= delta:
        return lambda_val
    else:
        return (lambda_val**2 + delta**2) / (2.0 * delta)


def hll_flux_with_entropy_fix(h_L, Q_L, h_R, Q_R, B, g, eps=1e-6):
    """
    带entropy修正的HLL通量
    """
    # 1. 计算左右状态
    u_L = Q_L / (B * h_L) if h_L > eps else 0.0
    u_R = Q_R / (B * h_R) if h_R > eps else 0.0

    c_L = np.sqrt(g * h_L) if h_L > eps else 0.0
    c_R = np.sqrt(g * h_R) if h_R > eps else 0.0

    # 2. 估算波速
    s_L = min(u_L - c_L, u_R - c_R)
    s_R = max(u_L + c_L, u_R + c_R)

    # 3. Entropy修正
    delta = 0.1 * max(abs(s_L), abs(s_R))
    s_L = entropy_fix(s_L, delta)
    s_R = entropy_fix(s_R, delta)

    # 4. HLL通量计算
    if s_L >= 0:
        # 完全左侧
        F_h = Q_L
        F_Q = Q_L**2 / (B * h_L) + 0.5 * g * B * h_L**2
    elif s_R <= 0:
        # 完全右侧
        F_h = Q_R
        F_Q = Q_R**2 / (B * h_R) + 0.5 * g * B * h_R**2
    else:
        # HLL中间状态
        U_L = np.array([h_L, Q_L])
        U_R = np.array([h_R, Q_R])

        F_L = np.array([Q_L, Q_L**2/(B*h_L) + 0.5*g*B*h_L**2])
        F_R = np.array([Q_R, Q_R**2/(B*h_R) + 0.5*g*B*h_R**2])

        F_star = (s_R * F_L - s_L * F_R + s_L * s_R * (U_R - U_L)) / (s_R - s_L)

        F_h = F_star[0]
        F_Q = F_star[1]

    return F_h, F_Q
```

### 4. 临界流特殊处理

**策略1：增加数值粘性**

在临界流区域，人为增加耗散：

```python
def critical_flow_flux(h_L, Q_L, h_R, Q_R, B, g, Fr_avg):
    """
    临界流区域的特殊通量
    """
    # 标准HLL通量
    F_h, F_Q = hll_flux_with_entropy_fix(h_L, Q_L, h_R, Q_R, B, g)

    # 如果接近临界流，增加耗散
    if 0.9 < Fr_avg < 1.1:
        # 计算额外耗散项
        alpha = 0.5 * (1.1 - abs(Fr_avg - 1.0)) / 0.1  # 0-0.5

        # Lax-Friedrichs耗散
        max_speed = max(abs(Q_L/(B*h_L)) + np.sqrt(g*h_L),
                       abs(Q_R/(B*h_R)) + np.sqrt(g*h_R))

        dissipation_h = alpha * max_speed * (h_R - h_L)
        dissipation_Q = alpha * max_speed * (Q_R - Q_L)

        F_h -= dissipation_h
        F_Q -= dissipation_Q

    return F_h, F_Q
```

**策略2：局部时间步长减小**

```python
def compute_dt_critical(h, Q, B, dx, cfl, g):
    """
    考虑临界流的时间步长
    """
    Fr = compute_froude_number(h, Q, B, g)

    # 标准CFL条件
    u = Q / (B * h)
    c = np.sqrt(g * h)
    max_speed = abs(u) + c
    dt_standard = cfl * dx / max_speed

    # 如果接近临界流，减小时间步长
    if 0.9 < Fr < 1.1:
        reduction_factor = 0.5  # 减半
        dt_critical = reduction_factor * dt_standard
    else:
        dt_critical = dt_standard

    return dt_critical
```

---

## 🧪 测试策略

### 测试案例设计

#### Test 1: 临界流通过喉部

**配置**：
- 渠道：变底高程，中间有喉部
- 初始：亚临界流
- 边界：上游恒定流量，下游自由出流

**预期**：
- Fr在喉部达到1.0
- 无数值振荡
- 质量守恒 < 1%

**成功标准**：
- ✅ 计算收敛（不崩溃）
- ✅ Fr在喉部 0.95-1.05
- ✅ 上下游过渡平滑

#### Test 2: 亚临界→超临界转换

**配置**：
- 渠道：陡坡段
- 初始：上游亚临界，Fr=0.5
- 边界：恒定流量

**预期**：
- Fr在陡坡上升
- 平滑过渡到Fr>1

**成功标准**：
- ✅ Fr连续变化
- ✅ 无振荡

#### Test 3: 超临界→亚临界转换（水跃）

**配置**：
- 渠道：平底，下游有障碍物
- 初始：超临界流，Fr=2.0
- 边界：下游高水位

**预期**：
- 形成hydraulic jump
- Fr从>1跳到<1

**成功标准**：
- ✅ 水跃位置稳定
- ✅ 质量守恒 < 10%（有摩阻）

#### Test 4: MacDonald Test 4（无摩阻水跃）

**配置**：
- 按MacDonald标准配置
- n = 0（无摩阻）

**成功标准**（如果能通过）：
- ✅ 质量守恒 < 15%（放宽标准）
- ✅ 上游Fr > 1
- ✅ 下游Fr < 1

**备注**：这是最困难的测试，可能需要方案B（LPI）才能完全解决

---

## 📊 性能评估

### 计算开销估算

**Entropy修正**：
- 额外计算：~5%
- 内存：无增加

**临界流检测**：
- 额外计算：~2%
- 内存：无增加

**特殊通量**：
- 额外计算：~3%（仅临界流区域）
- 内存：无增加

**总计**：~10%计算开销（可接受）

### 与标准方法对比

| 方法 | 计算时间 | 稳定性 | 精度 |
|-----|---------|--------|------|
| 标准HLL | 1.0x | ❌ Fr≈1 | 中 |
| HLL + Entropy | 1.05x | ✅ | 中-高 |
| HLL + Entropy + Critical | 1.10x | ✅✅ | 高 |
| LPI（HEC-RAS） | 1.5-2.0x | ✅✅✅ | 高 |

---

## 🛠️ 实施计划

### Week 1: Entropy修正实现

**Day 1-2**:
- [ ] 实现entropy_fix函数
- [ ] 修改HLL求解器
- [ ] 单元测试

**Day 3-4**:
- [ ] 集成到Godunov FVM求解器
- [ ] 回归测试（确保不影响现有测试）
- [ ] Dam Break测试验证

**成功标准**：
- 所有现有测试继续通过
- Dam Break精度提升或保持

### Week 2: 临界流处理

**Day 5-7**:
- [ ] 实现临界流检测
- [ ] 实现特殊通量计算
- [ ] 创建临界流测试案例

**Day 8-9**:
- [ ] 测试临界流通过喉部
- [ ] 测试亚临界↔超临界转换
- [ ] 参数调优

**成功标准**：
- 临界流测试通过
- 无数值振荡

### Week 3: MacDonald Test 4验证

**Day 10-12**:
- [ ] 尝试MacDonald Test 4（无摩阻）
- [ ] 分析结果
- [ ] 如需要，实施额外改进

**Day 13-14**:
- [ ] 完整文档
- [ ] 性能测试
- [ ] 代码审查

**交付成果**：
- ✅ 混合流态求解器实现
- ✅ 临界流测试通过
- ✅ 技术文档完整
- ⏸️ MacDonald Test 4通过（尽力而为）

---

## 📚 参考文献

### 学术论文

1. **Toro (2001)**: Shock-Capturing Methods for Free-Surface Shallow Flows
   - Chapter 5: Riemann Solvers
   - Section 5.3: Entropy Fix

2. **Harten (1983)**: High Resolution Schemes for Hyperbolic Conservation Laws
   - Entropy condition
   - TVD schemes

3. **Audusse et al. (2004)**: A Fast and Stable Well-Balanced Scheme
   - Hydrostatic reconstruction
   - Source term treatment

### 商业软件文档

4. **HEC-RAS Hydraulic Reference Manual**
   - Chapter: Mixed Flow Regime
   - LPI method description

5. **MIKE 11 Reference Manual**
   - Abbott-Ionescu scheme
   - Critical flow handling

### 教材

6. **LeVeque (2002)**: Finite Volume Methods for Hyperbolic Problems
   - Chapter 12: Nonlinear Systems
   - Chapter 15: Riemann Problems

7. **Toro (2009)**: Riemann Solvers and Numerical Methods
   - Comprehensive coverage of all methods

---

## 🎯 成功标准总结

### 必须达成（P0）

| 标准 | 测试方法 | 目标值 |
|-----|---------|--------|
| 临界流稳定性 | 临界流通过喉部测试 | 计算收敛 |
| 质量守恒 | 所有测试 | < 5% |
| 无振荡 | 水深/流速曲线检查 | 无明显振荡 |
| 性能 | 与标准HLL对比 | < 20%开销 |

### 期望达成（P1）

| 标准 | 测试方法 | 目标值 |
|-----|---------|--------|
| Test 4通过 | MacDonald Test 4 | 质量误差 < 15% |
| 转换平滑 | 流态转换测试 | Fr连续 |

---

**文档创建**: 2025-10-29
**状态**: 设计阶段
**下次审查**: 实施前
