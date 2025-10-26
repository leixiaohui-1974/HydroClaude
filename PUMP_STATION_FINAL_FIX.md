# 泵站数值建模彻底修复方案

**日期**: 2025-10-26  
**状态**: 待实施  
**优先级**: P0（最高）

---

## 📋 问题总结

### 当前实现的根本缺陷

当前代码使用"区域约束法"（v3.0），存在以下严重问题：

```python
# 当前方法：强制设置15个网格点
for pos in range(idx-2, idx+13):
    self.h[pos] = 某个计算值  # 人为强制
    self.hu[pos] = Q_ref / self.B
```

**致命缺陷**：
1. ❌ 与Preissmann PDE求解器产生根本性冲突
2. ❌ 创造非物理的"平台区"概念（实际不存在）
3. ❌ 在区域边界产生数值discontinuity（台阶）
4. ❌ 通过反复调整松弛因子"凑"结果（非科学）
5. ❌ 不是任何文献中的标准方法

### 观察到的症状

- ✗ 泵站下游51-52km处出现异常台阶（梯度-2.917‰）
- ✗ "平台区"水深波动大（标准差0.374m，应该≈0）
- ✗ 需要通过±10km测点才能测到正确扬程
- ✗ 水面线不连续、不平滑

---

## 📚 文献搜索结果

基于对以下资料的搜索：
- Toro (2009): "Riemann Solvers and Numerical Methods for Fluid Dynamics"
- HEC-RAS Hydraulic Reference Manual
- DHI MIKE 11 Reference Manual
- Sanders et al. (2010): "ParBreZo shallow-water code"
- Guinot (2008): "Wave Propagation in Fluids"

### 标准方法汇总

| 方法 | 描述 | 应用场景 | 复杂度 |
|------|------|----------|--------|
| **内部边界条件法** | 在泵站位置施加跳跃条件 | 👈 **推荐用于当前代码** | ⭐⭐ |
| 源项法 | 在动量方程中添加源项 | 最严格，需修改PDE | ⭐⭐⭐ |
| 耦合方程法 | 泵站特性曲线耦合求解 | 商业软件常用 | ⭐⭐⭐⭐ |

---

## ✅ 标准解决方案：内部边界条件法

### 物理原理

泵站在一维浅水方程中造成**水位跃变**（类似激波）：

```
      上游                泵站                下游
  ━━━━━━━━━━━━━━━━━━━━━━┃━━━━━━━━━━━━━━━━━━━
                          ┃ ↑
  h⁻, Q⁻                 ┃ │ H_pump (能量)    h⁺, Q⁺
                          ┃ │
  ═══════════════════════╬═══════════════════
                          ┃
```

**跳跃条件（Rankine-Hugoniot）**：

1. **质量守恒**：`Q⁺ = Q⁻` （流量连续）
2. **能量跃变**：`h⁺ = h⁻ + H_pump` （水位抬升）

### 数值实现（伪代码）

```python
def _apply_pump_internal_bc(self):
    """标准内部边界条件法"""
    
    for idx, pump in enumerate_pumps():
        # 获取上游状态
        h_up = h[idx - 1]
        Q_up = Q[idx - 1]
        
        # 施加跳跃条件
        h_down = h_up + H_pump      # 能量跃变
        Q_down = Q_up               # 流量守恒
        
        # 应用到下游节点
        h[idx + 1] = h_down
        Q[idx + 1] = Q_down
        
        # 泵站节点本身：线性插值
        h[idx] = 0.5 * (h_up + h_down)
        Q[idx] = Q_up
```

### 关键特点

✓ **仅影响3个节点**：`idx-1, idx, idx+1`  
✓ **其余节点由Preissmann自然求解**  
✓ **无人工"平台区"或"过渡区"**  
✓ **类似闸门的标准处理**  
✓ **物理清晰，数值稳定**  

---

## 🔧 完整实现代码

### 第1步：简化掩码方法

```python
def _get_pump_region_mask(self) -> np.ndarray:
    """
    获取泵站影响区域掩码
    
    返回：仅泵站直接影响的3个节点
    """
    mask = np.zeros(self.nx, dtype=bool)
    
    for idx, structure in zip(self.structure_indices, self.structure_objects):
        from solvers.gate import PumpStation
        
        if not isinstance(structure, PumpStation) or not structure.is_running:
            continue
        
        if idx <= 0 or idx >= self.nx - 1:
            continue
        
        # 标记3个节点：上游邻居、泵站、下游邻居
        mask[idx - 1] = True
        mask[idx] = True
        mask[idx + 1] = True
    
    return mask
```

### 第2步：实现标准内部边界条件

```python
def _apply_pump_internal_bc(self):
    """
    泵站作为内部边界条件（标准数值方法）
    
    参考文献：
    - Toro (2009): Riemann Solvers and Numerical Methods
    - HEC-RAS: Energy equation at structures
    """
    if not self.structure_indices or not self.structure_objects:
        return
    
    for idx, structure in zip(self.structure_indices, self.structure_objects):
        from solvers.gate import PumpStation
        
        if not isinstance(structure, PumpStation) or not structure.is_running:
            continue
        
        if idx <= 0 or idx >= self.nx - 1:
            continue
        
        # ===== 跳跃条件 =====
        
        # 上游状态
        h_upstream = self.h[idx - 1]
        hu_upstream = self.hu[idx - 1]
        
        # 跳跃
        h_downstream = h_upstream + structure.rated_head  # 能量
        hu_downstream = hu_upstream                       # 质量
        
        # 应用
        self.h[idx + 1] = h_downstream
        self.hu[idx + 1] = hu_downstream
        
        # 泵站节点：线性过渡
        self.h[idx] = 0.5 * (h_upstream + h_downstream)
        self.hu[idx] = hu_upstream
        
        # 确保正值
        self.h[idx] = max(self.eps_dry, self.h[idx])
        self.h[idx + 1] = max(self.eps_dry, self.h[idx + 1])
```

### 第3步：废弃旧方法

```python
def _apply_pump_region_constraints(self):
    """
    【已废弃】区域约束法（v3.0）
    
    此方法存在以下问题：
    - 与PDE求解器冲突
    - 创造非物理的"平台区"
    - 产生数值台阶
    
    已被标准内部边界条件法替代。
    """
    # 调用新方法
    self._apply_pump_internal_bc()

def _apply_pump_head_jump(self):
    """向后兼容"""
    self._apply_pump_region_constraints()
```

---

## 📊 预期效果

### 修复前（当前）

```
位置(km)    水深(m)      梯度(‰)      状态
51.46       7.3205       0.000        平台区末端
51.66       6.7371      -2.917        ✗ 异常台阶！
51.86       6.1538      -2.917        ✗ 异常台阶！
52.06       5.9491      -1.023        下游过渡
```

### 修复后（预期）

```
位置(km)    水深(m)      梯度(‰)      状态
49.90       2.29         +0.06        上游正常
50.00       4.65         +23.5        泵站中心
50.10       7.29         +26.4        下游（跃变后）
50.30       7.28         -0.05        ✓ 自然过渡
50.50       7.27         -0.04        ✓ 平滑下降
51.00       7.25         -0.04        ✓ 连续
52.00       7.20         -0.05        ✓ 无台阶
```

**关键改进**：
- ✅ 水位跃变集中在泵站处（3个节点）
- ✅ 下游自然平滑过渡（无人工台阶）
- ✅ 任意位置测量扬程都准确

---

## 🎯 实施步骤

### 步骤1：备份当前代码

```bash
cd /workspace
cp solvers/hydrostatic_canal_solver.py solvers/hydrostatic_canal_solver.py.v3_backup
```

### 步骤2：应用修复

将上述代码替换到`solvers/hydrostatic_canal_solver.py`中：
- 第425-453行：`_get_pump_region_mask()`
- 第456-532行：`_apply_pump_internal_bc()` + 废弃旧方法

### 步骤3：测试验证

```bash
cd /workspace/examples/example_gate_pump_cascade

# 1. 运行仿真
python3 run_gate_pump_auto.py

# 2. 精度分析
python3 analyze_pump_precision.py

# 3. 检查水面线
python3 -c "
import numpy as np
data = np.load('results_gate_pump_auto/gate_pump_auto_data.npz')
x, h = data['x'], data['h']
# 检查51-52km是否还有台阶
mask = (x >= 51000) & (x <= 52000)
print('51-52km water depths:', h[mask])
print('Gradient (permil):', np.gradient(h[mask], x[mask]) * 1000)
"
```

### 步骤4：更新文档

更新以下文档：
- `PUMP_HIGH_PRECISION_SUMMARY.md` → 标记v3.0已废弃
- `README.md` → 说明使用标准方法
- 添加参考文献列表

---

## ✅ 验收标准

| 指标 | 当前（v3.0） | 目标（v4.0） | 测试方法 |
|------|-------------|------------|----------|
| 扬程精度 | 73-100%（不稳定） | >95% | analyze_pump_precision.py |
| 异常台阶 | 2个（51.46, 51.66km） | 0个 | 梯度分析 |
| 平台区波动 | 标准差0.374m | <0.05m | 统计分析 |
| 过渡平滑性 | 梯度std=2.9‰ | <0.2‰ | 梯度分析 |
| 测量位置依赖 | 强（需±10km） | 无（任意位置） | 多点测试 |

---

## 📖 参考文献

1. **Toro, E. F. (2009)**. "Riemann Solvers and Numerical Methods for Fluid Dynamics: A Practical Introduction". Springer. (Chapter 10: Boundaries and source terms)

2. **HEC-RAS (2016)**. "Hydraulic Reference Manual". US Army Corps of Engineers. (Section on Pump Stations and Internal Boundaries)

3. **DHI (2017)**. "MIKE 11: A Modelling System for Rivers and Channels - Reference Manual". DHI Water & Environment.

4. **Sanders, B. F. et al. (2010)**. "ParBreZo: A parallel, unstructured grid, Godunov-type, shallow-water code for high-resolution flood inundation modeling at the regional scale". Advances in Water Resources, 33(12), 1456-1467.

5. **Guinot, V. (2008)**. "Wave Propagation in Fluids: Models and Numerical Techniques". John Wiley & Sons. (Chapter 9: Internal boundary conditions)

---

## 💡 关键启示

1. **不要发明新方法**：水力学数值方法已有50+年研究，标准方法已验证
2. **物理优先**：数值方法必须尊重物理规律（质量守恒、能量守恒）
3. **简单即美**：3个节点 vs 15个节点（5倍简化）
4. **避免调参**：如果需要反复调整参数，方法本身可能有问题

---

**结论**：当前的"区域约束法"应该被完全废弃，替换为标准的内部边界条件法。这不仅能解决台阶问题，还能使代码更简洁、更可靠、更易维护。
