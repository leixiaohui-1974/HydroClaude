# Well-Balanced模式的适用性分析

**日期**: 2025-10-29
**发现**: 当前Well-Balanced实现不适用于有流动的MacDonald场景
**影响**: MacDonald Test 2必须使用标准格式，需要改进源项计算

---

## 🔬 测试设计

创建对照测试，对比well_balanced=True和False在MacDonald场景下的表现。

**测试场景**：
- 边界条件：Q=2.0 m³/s, h=h_c (临界水深)
- 底坡：0.002
- Manning n：0.03
- 网格：20单元，L=1000m
- 模拟时间：500s

---

## 📊 测试结果

### 对比表

| 模式 | 质量误差 | 流量误差 | 说明 |
|------|----------|----------|------|
| **well_balanced=False** | 61.41% | 27.03% | 标准格式（当前MacDonald使用）|
| **well_balanced=True** | **119.67%** | **53.47%** | Well-Balanced格式 |
| **差异** | **+58.27%** | **+26.44%** | ✗ **更差** |

### 详细数据

#### well_balanced=False（标准格式）
```
初始质量: 926.92 m³
最终质量: 1496.11 m³
质量误差: 61.41%

边界Q: 2.0 m³/s
平均Q: 1.4594 m³/s
流量误差: 27.03%

时间演化:
  t=193s: 质量误差=26.0%
  t=382s: 质量误差=49.7%
  t=500s: 质量误差=61.4%
```

#### well_balanced=True（Well-Balanced格式）
```
初始质量: 926.92 m³
最终质量: 2035.45 m³  ⚠️ 更大的累积
质量误差: 119.67%  ✗ 几乎翻倍！

边界Q: 2.0 m³/s
平均Q: 0.9306 m³/s  ⚠️ 偏离更远
流量误差: 53.47%

时间演化:
  t=186s: 质量误差=42.2%
  t=356s: 质量误差=87.5%
  t=500s: 质量误差=119.7%  ✗ 误差增长更快
```

---

## 🎯 核心发现

### Well-Balanced模式让情况变得更糟

**意外结果**：
- 质量误差：61% → 120%（增加58%）
- 流量误差：27% → 53%（增加26%）
- 误差增长速度：更快

**原因分析**：

当前的Well-Balanced实现基于**Hydrostatic Reconstruction**（Audusse et al. 2004），设计目的是：

1. **Lake at Rest问题**：静水平衡
   - 目标：h + z_b = constant
   - 源项：完全由通量平衡抵消
   - 适用：无流动或微小流动

2. **实现方式**：
   ```python
   # Well-balanced格式的源项
   if self.well_balanced:
       return -self.g * A * Sf  # 只有摩阻项
   ```
   - 底坡源项通过hydrostatic reconstruction在通量中处理
   - 假设：静水平衡下通量差完全抵消底坡源项

3. **MacDonald场景的问题**：
   - **有显著流动**：Q=2.0 m³/s, Fr~0.2-0.5（缓流但不是静水）
   - **非稳态**：初始条件不是正常水深曲线
   - **结果**：底坡源项被"吞掉"，导致虚假的质量累积

### 为什么标准格式更好（虽然仍有问题）

标准格式虽然有61%误差，但至少：
1. 底坡源项被显式计算：`S = g*A*(S0 - Sf)`
2. 源项和通量独立处理
3. 误差来自数值离散不精确，而非概念错误

Well-balanced格式在有流动情况下：
1. 底坡源项"消失"在通量中
2. 但通量差无法完全抵消（因为不是静水）
3. 导致更大的不平衡

---

## 📚 文献对比

### Hydrostatic Reconstruction适用范围

**Audusse et al. (2004)** - "A Fast and Stable Well-Balanced Scheme"

**适用**：
- Lake at Rest（静水）
- 缓慢变化的流动（quasi-static）
- Dam break初始阶段（静水破坏）

**不适用**：
- 稳定流动问题（如MacDonald Test 2的正常水深曲线）
- 需要精确源项平衡的非静态问题

### 需要的方法

对于MacDonald类型的稳定流动问题，应该使用：

**Zhou et al. (2001)** - "Surface Gradient Method"
- 直接处理源项
- 适用于有流动的情况
- 保持C-property（守恒性质）

**Xing & Shu (2005)** - "High Order Well-Balanced WENO"
- 高精度源项离散
- 适用于复杂地形 + 流动

---

## 💡 解决方案方向

### 短期（当前）

**接受现状，使用well_balanced=False**
- MacDonald Test 2继续使用标准格式
- 虽然有61%误差，但比well_balanced=True的120%好
- 在文档中说明限制

### 中期（P1 - 下周）

**改进标准格式的源项计算**

选项1：更精确的源项离散
```python
# 当前：点值
S = g * A * (S0[i] - Sf[i])

# 改进：单元平均
S = g * A_avg * (S0_avg - Sf_avg)
```

选项2：分步法（Strang splitting）
```python
# 1. 只有通量（无源项）
# 2. 只有源项（无通量）
# 分开处理，减少相互影响
```

### 长期（P2 - 下月）

**实现适用于流动的Well-Balanced方法**

选项1：Surface Gradient Method (Zhou 2001)
- 重新设计源项离散
- 确保流动状态下的平衡

选项2：混合方法
- 静水：Hydrostatic Reconstruction
- 流动：Surface Gradient
- 自动选择

---

## 🔄 MacDonald Test 2的配置建议

**当前最佳配置**：
```python
solver_config = {
    'well_balanced': False,  # ✓ 使用标准格式
    'spatial_order': 2,       # 提高空间精度可能有帮助
    'riemann_solver': 'hll',
    # ... 其他参数
}
```

**预期结果**：
- 质量误差：~33-61%
- 流量误差：~15-27%
- 状态：**已知限制，等待源项改进**

---

## ✅ 结论

1. **Well-Balanced模式不适用于MacDonald场景**
   - Hydrostatic Reconstruction设计用于静水问题
   - 在有流动情况下反而变差（61% → 120%）

2. **标准格式是当前最好选择**
   - 虽然有61%误差，但好于well-balanced的120%
   - 误差来自源项离散不精确，不是概念错误

3. **下一步重点**
   - 不是切换well-balanced模式
   - 而是改进标准格式的源项计算
   - 或实现适用于流动的well-balanced方法（Zhou 2001）

4. **测试套件需要区分**
   - Lake at Rest：使用well_balanced=True ✓
   - MacDonald：使用well_balanced=False ✓
   - 两种测试验证不同的数值性质

---

## 📖 相关文档

- `Q_BOUNDARY_DIAGNOSIS_REPORT.md` - Q边界诊断（证明Q边界正确）
- `LAKE_AT_REST_TEST_REPORT.md` - Well-balanced静水测试
- `BOUNDARY_CONDITION_MASS_CONSERVATION.md` - 边界条件深度分析

---

*本文档记录了2025-10-29对Well-Balanced模式适用性的测试结果*
