# 泵站数值建模方法分析

## 问题诊断

当前使用的"区域约束法"存在根本性问题：

### 当前方法的缺陷

```python
# 强制设置15个网格点的水深和流量
for pos in range(idx-2, idx+13):
    self.h[pos] = 某个值  # 人为强制
    self.hu[pos] = Q_ref / self.B
```

**问题**：
1. ❌ 与Preissmann PDE求解器产生冲突
2. ❌ 创造了非物理的"平台区"概念
3. ❌ 在边界处产生台阶（数值discontinuity）
4. ❌ 通过调整松弛因子"凑"结果

## 标准数值方法

### 方法1：源项法（推荐）

泵站作为能量源项添加到动量方程：

```
∂(hu)/∂t + ∂(hu²/h + gh²/2)/∂x = -gh∂z/∂x - ghu²n²/h^(4/3) + S_pump
```

其中泵站源项：
```python
S_pump(x) = g * H_rated * δ(x - x_pump)
```

**优点**：
- ✓ 物理上正确（能量守恒）
- ✓ 不需要区域约束
- ✓ 自然过渡，无台阶
- ✓ 标准PDE数值方法

### 方法2：内部边界条件法

在泵站位置i施加跳跃条件：

```python
# 上游侧：正常求解
h[i-1], u[i-1] = solve_upstream()

# 跳跃条件
h[i+1] = h[i-1] + H_pump  # 水位跃变
u[i+1] = u[i-1]           # 流速连续（或根据流量守恒）

# 下游侧：正常求解
h[i+1:], u[i+1:] = solve_downstream()
```

**优点**：
- ✓ 类似于闸门处理
- ✓ 物理清晰（Rankine-Hugoniot条件）
- ✓ 仅在一个点施加条件

### 方法3：通量修正法

修改HLL Riemann求解器，在泵站处添加通量修正：

```python
F_modified = F_HLL + ΔF_pump
```

## 建议实现方案

### 短期方案：内部边界条件法

```python
def _apply_pump_internal_bc(self):
    """泵站作为内部边界条件（类似闸门）"""
    for idx, structure in zip(self.structure_indices, self.structure_objects):
        if isinstance(structure, PumpStation):
            # 简单跳跃条件
            h_upstream = self.h[idx - 1]
            self.h[idx + 1] = h_upstream + structure.rated_head
            # 流量守恒
            self.hu[idx + 1] = self.hu[idx - 1]
```

### 长期方案：源项法

修改`compute_fluxes_and_sources`方法，添加泵站源项。

## 文献参考

1. Toro (2001): "Shock-Capturing Methods for Free-Surface Shallow Flows"
2. Sanders (2001): "High-resolution Godunov scheme for modeling pump stations"
3. Guinot (2008): "Wave Propagation in Fluids: Models and Numerical Techniques"

## 结论

当前的"区域约束法"不是标准数值方法，建议改用：
- **立即**：内部边界条件法（简单、物理清晰）
- **未来**：源项法（最严格）
