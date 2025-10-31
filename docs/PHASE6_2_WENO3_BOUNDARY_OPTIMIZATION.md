# Phase 6.2: WENO3边界处理优化 - 技术方案

**日期**: 2025-10-31
**预计工作量**: 5-7天
**优先级**: 高
**依赖**: Phase 6.1完成 ✅

---

## 📋 执行摘要

WENO3高阶格式在边界处由于缺少足够的模板点，精度会退化到一阶。本方案通过**Ghost Cell方法**和**高阶边界外推**，将边界处理精度提升到与内部一致的3阶。

### 预期收益

- ✅ 边界精度从1阶提升到3阶
- ✅ 减少边界误差向内部传播
- ✅ 提升长时间积分精度
- ✅ 为WENO5等更高阶格式铺路

---

## 🎯 问题分析

### 当前问题

#### 1. 精度退化

WENO3需要5点模板进行重构：
```
    i-2   i-1    i    i+1   i+2
     •     •     •     •     •
     └─────┴─────┴─────┴─────┘
        WENO3 5-point stencil
```

**边界处**:
```
边界   i=0   i=1   i=2
 |      •     •     •

缺少 i=-2, i=-1 的点！
→ 精度退化到1阶
```

#### 2. 误差传播

边界误差会向内部传播，影响整体精度：
```
边界误差(1阶) → 传播 → 降低整体精度
```

#### 3. 长时间积分

边界误差累积，影响长时间模拟的稳定性。

---

## 🔧 技术方案

### 方案1: Ghost Cell方法（推荐）

#### 1.1 基本原理

在物理域外添加虚拟单元（Ghost Cells），使边界处也能使用完整的5点模板。

**数据结构**:
```
Ghost   Physical Domain   Ghost
 •  •   •  •  •  •  •  •   •  •
-2 -1   0  1  2  ... n-2 n-1  n  n+1
```

#### 1.2 实现步骤

**Step 1: 扩展数组**

```python
def setup_ghost_cells(self, h, hu, z_b):
    """
    添加ghost cells

    Args:
        h, hu, z_b: 物理域数组 [n_cells]

    Returns:
        h_ext, hu_ext, z_ext: 扩展数组 [n_cells + 4]
    """
    n = len(h)

    # 左右各加2个ghost cells
    h_ext = np.zeros(n + 4)
    hu_ext = np.zeros(n + 4)
    z_ext = np.zeros(n + 4)

    # 复制物理域 (索引2 to n+1)
    h_ext[2:-2] = h
    hu_ext[2:-2] = hu
    z_ext[2:-2] = z_b

    return h_ext, hu_ext, z_ext
```

**Step 2: 填充Ghost Cells**

根据边界条件类型填充：

```python
def fill_ghost_cells(self, h_ext, hu_ext, bc_left, bc_right):
    """填充ghost cells"""

    # 左边界 ghost cells (索引0, 1)
    if bc_left == 'transmissive':
        # 外推（零梯度）
        h_ext[0] = h_ext[2]
        h_ext[1] = h_ext[2]
        hu_ext[0] = hu_ext[2]
        hu_ext[1] = hu_ext[2]

    elif bc_left == 'reflective':
        # 镜像（对称）
        h_ext[0] = h_ext[4]
        h_ext[1] = h_ext[3]
        hu_ext[0] = -hu_ext[4]  # 流量反向
        hu_ext[1] = -hu_ext[3]

    elif bc_left == 'extrapolate':
        # 线性外推
        h_ext[1] = 2*h_ext[2] - h_ext[3]
        h_ext[0] = 2*h_ext[1] - h_ext[2]
        # hu类似

    # 右边界 ghost cells (索引-2, -1)
    if bc_right == 'transmissive':
        h_ext[-1] = h_ext[-3]
        h_ext[-2] = h_ext[-3]
        hu_ext[-1] = hu_ext[-3]
        hu_ext[-2] = hu_ext[-3]

    elif bc_right == 'reflective':
        h_ext[-1] = h_ext[-5]
        h_ext[-2] = h_ext[-4]
        hu_ext[-1] = -hu_ext[-5]
        hu_ext[-2] = -hu_ext[-4]

    elif bc_right == 'extrapolate':
        h_ext[-2] = 2*h_ext[-3] - h_ext[-4]
        h_ext[-1] = 2*h_ext[-2] - h_ext[-3]

    return h_ext, hu_ext
```

**Step 3: WENO重构**

现在可以在整个扩展域上使用统一的WENO重构：

```python
def weno3_reconstruction(self, u_ext):
    """
    WENO3重构（支持ghost cells）

    Args:
        u_ext: 扩展数组 [n_cells + 4]

    Returns:
        u_L, u_R: 界面左右状态 [n_cells + 1]
    """
    n_phys = len(u_ext) - 4
    u_L = np.zeros(n_phys + 1)
    u_R = np.zeros(n_phys + 1)

    # 对每个界面 (包括边界)
    for i in range(n_phys + 1):
        # 物理索引i对应扩展索引i+2
        idx = i + 2

        # 5点模板: [idx-2, idx-1, idx, idx+1, idx+2]
        u_L[i] = weno3_reconstruct_left(u_ext[idx-2:idx+3])
        u_R[i] = weno3_reconstruct_right(u_ext[idx-2:idx+3])

    return u_L, u_R
```

#### 1.3 优点

- ✅ 边界和内部统一处理
- ✅ 代码简洁
- ✅ 3阶精度一致
- ✅ 易于扩展到WENO5

#### 1.4 缺点

- ⚠️ 内存增加（+4单元，可忽略）
- ⚠️ 需要修改索引逻辑

---

### 方案2: 高阶边界外推（备选）

不添加ghost cells，而是在边界处使用高阶外推值。

#### 2.1 二阶外推

```python
# 左边界
u_minus2 = 3*u[0] - 3*u[1] + u[2]
u_minus1 = 2*u[0] - u[1]

# 右边界
u_plus1 = 2*u[-1] - u[-2]
u_plus2 = 3*u[-1] - 3*u[-2] + u[-3]
```

#### 2.2 三阶外推

```python
# 左边界
u_minus2 = 4*u[0] - 6*u[1] + 4*u[2] - u[3]
u_minus1 = 3*u[0] - 3*u[1] + u[2]
```

#### 2.3 优缺点

**优点**:
- ✅ 不增加内存
- ✅ 实现简单

**缺点**:
- ⚠️ 边界处理代码复杂
- ⚠️ 不同边界条件需要不同处理
- ⚠️ 难以扩展

**建议**: 作为方案1的补充，用于特殊边界条件。

---

## 📐 实现计划

### 第1天: 数据结构修改

**文件**: `solvers/godunov_fvm_weno3.py`

**任务**:
1. 修改`__init__`，添加ghost cells支持标志
2. 实现`setup_ghost_cells()`方法
3. 实现`fill_ghost_cells()`方法

**测试**:
```python
def test_ghost_cells_setup():
    """测试ghost cells创建"""
    h = np.array([1.0, 2.0, 3.0])
    h_ext = setup_ghost_cells(h)

    assert len(h_ext) == 7  # 3 + 4
    assert np.allclose(h_ext[2:5], h)
```

### 第2天: WENO重构修改

**任务**:
1. 修改`weno3_reconstruction()`支持扩展数组
2. 更新索引逻辑
3. 保持向后兼容

**测试**:
```python
def test_weno3_with_ghost_cells():
    """测试WENO3使用ghost cells"""
    # 创建测试数据
    u = np.linspace(0, 1, 100)

    # 使用ghost cells
    solver = GodunvFVMWENO3(use_ghost_cells=True)
    u_L, u_R = solver.weno3_reconstruction(u)

    # 验证边界精度
    ...
```

### 第3天: 边界条件整合

**任务**:
1. 为每种边界条件实现ghost cells填充
   - Transmissive
   - Reflective
   - Fixed h/Q
   - Extrapolate
2. 测试验证

### 第4天: 精度验证

**任务**:
1. 创建精度测试
2. 对比1阶vs3阶边界
3. 网格细化研究

**测试用例**:
```python
def test_boundary_accuracy():
    """测试边界精度"""
    # 光滑初场
    x = np.linspace(0, 1, 100)
    h = 1.0 + 0.1*np.sin(2*np.pi*x)

    # 1阶边界
    solver1 = GodunvFVMWENO3(boundary_order=1)
    error1 = solver1.compute_error()

    # 3阶边界
    solver3 = GodunvFVMWENO3(boundary_order=3)
    error3 = solver3.compute_error()

    # 验证精度提升
    assert error3 < 0.1 * error1
```

### 第5天: 稳定性测试

**任务**:
1. 长时间积分测试
2. 各种边界条件组合
3. 回归测试

### 第6天: 性能优化

**任务**:
1. Profiling分析
2. 向量化优化
3. 性能对比

### 第7天: 文档和总结

**任务**:
1. 技术文档
2. 使用示例
3. API文档更新
4. 会话总结报告

---

## ✅ 验收标准

### 功能验收

- [ ] Ghost cells正确创建和填充
- [ ] WENO3在边界处达到3阶精度
- [ ] 所有边界条件类型支持
- [ ] 向后兼容（use_ghost_cells=False时退回旧行为）

### 质量验收

- [ ] 边界精度测试通过
- [ ] 现有测试无破坏
- [ ] 代码有完整文档
- [ ] 性能无明显下降（<5%）

### 测试验收

- [ ] 10+新增边界测试
- [ ] 精度验证测试
- [ ] 稳定性测试
- [ ] 回归测试

---

## 📊 预期成果

### 定量指标

| 指标 | 当前 | 目标 | 提升 |
|-----|------|------|------|
| 边界精度 | 1阶 | 3阶 | 8-10x |
| 边界误差 | ~1e-3 | ~1e-8 | 10⁵x |
| 长时间精度 | 退化 | 保持 | ✅ |

### 定性收益

- ✅ 代码结构更清晰
- ✅ 为WENO5铺路
- ✅ 提升用户信心

---

## 🚧 风险和缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|------|------|---------|
| 性能下降 | 低 | 中 | Profiling驱动优化 |
| 破坏现有功能 | 低 | 高 | 充分回归测试 |
| 索引错误 | 中 | 高 | 单元测试覆盖 |
| 时间超预期 | 中 | 中 | 分阶段实现 |

---

## 📚 参考资料

1. **Jiang & Shu (1996)** - "Efficient Implementation of Weighted ENO Schemes"
2. **Shu (1998)** - "Essentially Non-Oscillatory and Weighted Essentially Non-Oscillatory Schemes for Hyperbolic Conservation Laws"
3. **LeVeque (2002)** - "Finite Volume Methods for Hyperbolic Problems", Chapter 6
4. **HEC-RAS Technical Reference** - Boundary condition handling

---

## 🚀 立即行动

**今日任务** (Day 1):

1. ✅ 创建技术方案文档
2. ⏭️ 修改godunov_fvm_weno3.py
3. ⏭️ 实现setup_ghost_cells()
4. ⏭️ 实现fill_ghost_cells()
5. ⏭️ 单元测试

**代码位置**:
- `solvers/godunov_fvm_weno3.py` - 主要修改
- `tests/numerical_methods/test_weno3_boundary.py` - 新测试

---

**🤖 Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**
