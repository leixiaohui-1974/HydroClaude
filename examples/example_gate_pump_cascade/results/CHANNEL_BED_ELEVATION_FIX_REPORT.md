# 渠底高程显示修复报告

**日期**: 2025-10-26  
**示例**: 明渠串联闸泵群系统 (example_gate_pump_cascade)  
**问题类型**: 可视化缺陷

---

## 问题描述

在之前的纵断面动画图（`06_longitudinal_profile_animation.gif`）中，渠底高程没有正确显示泵站处的底床抬高。

**具体问题**：
- 泵站位于50km处，根据"山区调水泵站"场景设定，泵后底床应抬高5.0m
- 但动画中的渠底高程线是平滑的，没有显示这个跳跃
- 这导致水位变化的物理意义不清楚

---

## 根本原因

在 `utils/visualization_templates.py` 的 `create_longitudinal_animation` 函数中，渠底高程是根据坡度重新计算的：

```python
z_bed = (canal_length - x) * S0  # 简单的线性计算
```

这个计算方式忽略了求解器中已经设置的底床跳跃（在泵站处）。而实际的底床高程数组 `solver.z` 已经包含了泵站处的跳跃：

```python
# 在 gate_pump_cascade_system.py 中
solver.z[pump_idx:] += pump_rated_head  # 泵后底床抬高5.0m
```

---

## 修复方案

### 1. 修改可视化模板函数

在 `utils/visualization_templates.py` 的 `create_longitudinal_animation` 函数中：

**修改前**：
```python
def create_longitudinal_animation(
    self,
    x: np.ndarray,
    h_snapshots: List[np.ndarray],
    Q_snapshots: List[np.ndarray],
    time_snapshots: List[float],
    S0: float,
    canal_length: float,
    Q_target: float,
    gate_positions: Optional[List[float]] = None,
    h_uniform: Optional[float] = None,
    # ... 其他参数
):
    # 总是重新计算渠底高程
    z_bed = (canal_length - x) * S0
```

**修改后**：
```python
def create_longitudinal_animation(
    self,
    x: np.ndarray,
    h_snapshots: List[np.ndarray],
    Q_snapshots: List[np.ndarray],
    time_snapshots: List[float],
    S0: float,
    canal_length: float,
    Q_target: float,
    gate_positions: Optional[List[float]] = None,
    h_uniform: Optional[float] = None,
    z_bed: Optional[np.ndarray] = None,  # ✓ 新增参数
    # ... 其他参数
):
    # 如果提供了实际的底床高程，使用它；否则重新计算
    if z_bed is None:
        z_bed = (canal_length - x) * S0
```

### 2. 修改主程序调用

在 `examples/example_gate_pump_cascade/gate_pump_cascade_system.py` 中：

**修改前**：
```python
fig_anim, anim = viz_anim.create_longitudinal_animation(
    x=solver.x,
    h_snapshots=h_snapshots,
    Q_snapshots=Q_snapshots,
    time_snapshots=time_snapshots,
    S0=S0,
    canal_length=L_total,
    Q_target=Q_step,
    gate_positions=[gate1_pos, pump_pos, gate2_pos],
    h_uniform=h_uniform,
    # 没有传递实际的底床高程
    title_prefix="Gate-Pump Cascade System",
    filename="06_longitudinal_profile_animation.gif",
    fps=2,
    dpi=80
)
```

**修改后**：
```python
fig_anim, anim = viz_anim.create_longitudinal_animation(
    x=solver.x,
    h_snapshots=h_snapshots,
    Q_snapshots=Q_snapshots,
    time_snapshots=time_snapshots,
    S0=S0,
    canal_length=L_total,
    Q_target=Q_step,
    gate_positions=[gate1_pos, pump_pos, gate2_pos],
    h_uniform=h_uniform,
    z_bed=solver.z,  # ✓ 传递实际的底床高程数组（包含泵站处的跳跃）
    title_prefix="Gate-Pump Cascade System",
    filename="06_longitudinal_profile_animation.gif",
    fps=2,
    dpi=80
)
```

---

## 验证结果

修复后重新运行仿真，生成的所有图表都正确显示了渠底高程：

### 1. 稳态纵断面图 (`01_steady_state_profile.png`)
- ✓ 底床高程在50km处有明显的5.0m跳跃
- ✓ 水位也相应抬升，但水深基本保持不变
- ✓ 符合"山区调水泵站"的物理特性

### 2. 水位时空演化图 (`02_water_level_spacetime.png`)
- ✓ 水位计算使用了 `solver.z`，正确反映了底床跳跃的影响

### 3. 纵断面动画 (`06_longitudinal_profile_animation.gif`)
- ✓ **主要修复目标**：动画中渠底高程线在50km处有清晰的5.0m跳跃
- ✓ 水位和水深的动态变化更容易理解
- ✓ 泵站的作用一目了然

### 4. 其他图表
- ✓ 流量时空演化图、关键位置时间序列图等均正常

---

## 影响范围

**修改的文件**：
1. `utils/visualization_templates.py` - 可视化模板库
2. `examples/example_gate_pump_cascade/gate_pump_cascade_system.py` - 主程序

**优点**：
- 向后兼容：新增的 `z_bed` 参数是可选的，不影响其他现有代码
- 通用性好：其他需要显示底床跳跃的案例也可以使用这个修复

---

## 物理意义说明

### 山区调水泵站场景（SCENARIO = "mountain"）

**物理配置**：
- 泵前底床：保持原始高程
- 泵后底床：抬高 5.0m（实际地形高差）
- 下游边界：低水位

**物理过程**：
- 泵站克服地形高差 ΔH = 5.0m
- 扬程主要用于克服地形，而非增加水深

**预期结果**（已验证）：
- 泵后水深基本不变（~3m）
- 水位抬升约5.0m（由于底床抬高）
- 流量连续性得到保持

---

## 总结

本次修复解决了纵断面动画中渠底高程显示不正确的问题，使得：
1. 泵站处的底床跳跃清晰可见
2. 水位和水深的变化更容易理解
3. 物理意义表达更准确
4. 修复方案通用且向后兼容

所有结果图表均已重新生成并验证正确。

---

**修复完成**: 2025-10-26  
**验证状态**: ✓ 通过
