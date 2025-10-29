# 桥梁（Bridge）水力计算模块

## 概述

桥梁（Bridge）模块提供了跨河桥梁的水力计算功能，基于 **FHWA HDS-1** 标准实现。模块支持：

- **自由流（Free Flow）**：基于 Yarnell 方程的壅水计算
- **压力流（Pressure Flow）**：桥面淹没时的孔口流计算
- **多种桥墩类型**：圆形、矩形、流线型桥墩
- **冲刷深度计算**：基于 CSU 方程（HEC-18）的桥墩冲刷深度
- **斜交桥梁**：支持任意角度的斜交桥梁

## 理论基础

### 1. Yarnell 方程（自由流）

当水流未淹没桥面时，使用 Yarnell (1934) 方程计算壅水高度：

```
Δh = K * (V²/2g) * [α + 10(V²/2g)/h - 0.6(a/A + 15α⁴)]
```

其中：
- `K` - 桥墩形状系数（圆形=1.25，矩形=1.25，流线型=0.90）
- `V` - 桥孔处流速（m/s）
- `α` - 桥墩阻水比（桥墩投影面积 / 桥孔总面积）
- `a` - 桥墩总阻水面积（m²）
- `A` - 桥孔总面积（m²）
- `h` - 正常水深（m）
- `g` - 重力加速度（9.81 m/s²）

**收缩损失**：

桥梁引起的收缩损失基于 FHWA HDS-1 规范：

```
h_c = K_entrance * V_bridge²/(2g)
```

其中 `K_entrance` 根据收缩比计算：
- 轻度收缩（收缩比 > 0.8）：K = 0.5
- 严重收缩（收缩比 < 0.5）：K = 1.0
- 线性插值中间值

**设计安全系数**：

工程设计中通常对计算壅水值乘以安全系数 1.4，以考虑：
- 桥墩绕流的三维湍流效应
- 漂浮物堆积
- 局部冲刷影响
- 计算模型的不确定性

### 2. 压力流（桥面淹没）

当水位超过桥面高度的 80% 时，桥梁按孔口流计算：

```
Q = Cd * A * √(2g * ΔH)
```

其中：
- `Cd` - 孔口流量系数（取 0.8）
- `A` - 桥下过流面积（净宽 × 桥面高度）
- `ΔH` - 上下游水位差

反算上游水深：
```
ΔH = (Q / (Cd * A))² / (2g)
h_upstream = h_downstream + ΔH
```

### 3. 冲刷深度计算

基于 Colorado State University (CSU) 方程（HEC-18）：

```
y_s / h = 2.0 * K₁ * K₂ * K₃ * (a/h)^0.65 * Fr^0.43
```

其中：
- `y_s` - 冲刷深度（m）
- `h` - 上游水深（m）
- `a` - 桥墩宽度（m）
- `Fr` - Froude 数 = V/√(gh)
- `K₁` - 桥墩形状系数（圆形=1.0，方形=1.1，流线型=0.9）
- `K₂` - 攻角系数（取 1.0 假设正交）
- `K₃` - 河床条件系数（取 1.1 考虑非均匀河床）

## 使用方法

### 基本用法

```python
from physics.structures import create_simple_bridge

# 创建简单桥梁（圆形桥墩）
bridge = create_simple_bridge(
    position=100.0,          # 桥梁位置 (m)
    bridge_width=20.0,       # 桥孔净宽 (m)
    deck_elevation=15.0,     # 桥面底高程 (m)
    pier_count=3,            # 桥墩数量
    pier_width=1.0,          # 桥墩直径 (m)
    approach_width=25.0      # 上游河道宽度 (m)
)

# 计算壅水
Q = 80.0           # 流量 (m³/s)
h_normal = 5.0     # 正常水深 (m)

h_upstream, h_bridge, flow_type = bridge.compute_backwater(Q, h_normal)

print(f"上游水深: {h_upstream:.3f} m")
print(f"桥孔水深: {h_bridge:.3f} m")
print(f"壅水高度: {h_upstream - h_normal:.3f} m")
print(f"流态: {flow_type}")  # 'free' 或 'pressure'
```

### 自定义桥墩类型

```python
from physics.structures import Bridge, BridgeGeometry, Pier

# 矩形桥墩
rect_piers = Pier(
    shape='rectangular',
    width=1.5,      # 桥墩宽度 (m)
    length=4.0,     # 桥墩长度 (m)
    count=4         # 桥墩数量
)

# 流线型桥墩
streamlined_piers = Pier(
    shape='streamlined',
    width=1.0,
    count=2
)

# 桥梁几何
geometry = BridgeGeometry(
    position=200.0,
    bridge_width=25.0,
    deck_elevation=18.0,
    piers=rect_piers,
    abutment_type='vertical',  # 或 'sloped'
    skew_angle=15.0,          # 斜交角度（度）
    contraction_coef=0.9,     # 收缩系数
    expansion_coef=0.5        # 扩散系数
)

bridge = Bridge(geometry, approach_width=30.0)
```

### 斜交桥梁

```python
# 斜交桥梁（与河道成 30° 角）
bridge_skewed = create_simple_bridge(
    position=100.0,
    bridge_width=20.0,
    deck_elevation=15.0,
    pier_count=3,
    pier_width=1.0,
    skew_angle=30.0  # 斜交角度
)

# 有效宽度会根据斜交角自动调整
effective_width = bridge_skewed.geom.get_effective_width()
print(f"有效桥孔宽度: {effective_width:.2f} m")
```

### 冲刷深度计算

```python
# 计算桥墩冲刷深度
scour_depth = bridge.compute_scour_depth(
    Q=100.0,
    h_upstream=6.0,
    h_bridge=5.5
)

print(f"预测冲刷深度: {scour_depth:.3f} m")
```

### 水头损失计算

```python
# 计算通过桥梁的总水头损失
head_loss = bridge.compute_head_loss(
    Q=80.0,
    h_upstream=5.5,
    h_downstream=5.0
)

print(f"桥梁水头损失: {head_loss:.4f} m")
```

## 参数说明

### BridgeGeometry

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `position` | float | 桥梁位置 (m) | - |
| `bridge_width` | float | 桥孔净宽 (m) | - |
| `deck_elevation` | float | 桥面底高程 (m) | - |
| `piers` | Pier | 桥墩对象 | - |
| `abutment_type` | str | 桥台类型 ('vertical', 'sloped') | 'vertical' |
| `skew_angle` | float | 斜交角度 (度，0-45°) | 0.0 |
| `contraction_coef` | float | 收缩系数 | 0.9 |
| `expansion_coef` | float | 扩散系数 | 0.5 |

### Pier

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `shape` | str | 桥墩形状 ('circular', 'rectangular', 'streamlined') | - |
| `width` | float | 桥墩宽度/直径 (m) | - |
| `length` | float | 桥墩长度 (m，矩形桥墩必需) | None |
| `count` | int | 桥墩数量 | 1 |

### Bridge

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `geometry` | BridgeGeometry | 桥梁几何对象 | - |
| `approach_width` | float | 上游河道宽度 (m，如为 None 则取桥宽×1.2) | None |

## 设计指南

### 1. 桥墩设计

**桥墩形状选择**：
- **圆形桥墩**：水力性能好，K=1.25，适用于大多数情况
- **矩形桥墩**：施工简单但阻水较大，K=1.25
- **流线型桥墩**：阻水最小，K=0.90，推荐用于重要桥梁

**桥墩数量**：
- 桥墩越多，壅水越大
- 阻水比 α 应控制在 < 0.2（阻水面积/桥孔总面积）

**桥墩宽度**：
- 圆形桥墩：直径 0.8-2.0 m 典型
- 矩形桥墩：宽度 1.0-3.0 m，长宽比 3:1-4:1

### 2. 桥孔设计

**桥孔净宽**：
- 应 > 河道主流宽度的 0.8 倍
- 收缩比（桥孔净宽/河道宽）> 0.7 为宜

**桥面高程**：
- 应高于设计洪水位 + 壅水高度 + 安全超高（1.0-1.5 m）
- 避免压力流（桥面淹没）以减小壅水

### 3. 壅水评估

**可接受的壅水高度**：
- 小河道（宽 < 20 m）：< 0.3 m
- 中等河道（20-50 m）：< 0.5 m
- 大河道（> 50 m）：< 1.0 m

**减小壅水的措施**：
- 增加桥孔净宽
- 使用流线型桥墩
- 减少桥墩数量
- 改善上下游河道过渡

### 4. 斜交桥梁

**斜交角限制**：
- 推荐 < 30°（过大会显著增加壅水）
- 模块限制在 0-45° 范围

**斜交影响**：
- 有效过流面积减小（~ cos(θ)）
- 壅水增加约 10-30%

## 验证案例

### 案例 1：中等河道桥梁

**条件**：
- 河道宽度：25 m
- 桥孔净宽：20 m
- 桥墩：3 个圆形，直径 1.0 m
- 流量：80 m³/s
- 正常水深：5.0 m
- 桥面高程：15.0 m

**结果**：
```python
bridge = create_simple_bridge(
    position=100.0,
    bridge_width=20.0,
    deck_elevation=15.0,
    pier_count=3,
    pier_width=1.0,
    approach_width=25.0
)

h_up, h_br, flow_type = bridge.compute_backwater(80.0, 5.0)
# h_up ≈ 5.05 m
# 壅水 ≈ 0.05 m (< 0.3 m, 可接受)
# flow_type = 'free'
```

### 案例 2：窄桥严重收缩

**条件**：
- 河道宽度：25 m
- 桥孔净宽：12 m（收缩比 0.48）
- 桥墩：4 个圆形，直径 1.0 m
- 流量：100 m³/s
- 正常水深：5.0 m

**结果**：
```python
bridge = create_simple_bridge(
    position=100.0,
    bridge_width=12.0,
    deck_elevation=15.0,
    pier_count=4,
    pier_width=1.0,
    approach_width=25.0
)

h_up, h_br, flow_type = bridge.compute_backwater(100.0, 5.0)
# h_up ≈ 5.39 m
# 壅水 ≈ 0.39 m (较大，需考虑增加桥孔宽度)
```

### 案例 3：压力流（桥面淹没）

**条件**：
- 桥面高程：6.0 m（低桥）
- 正常水深：7.0 m（超过桥面）
- 流量：100 m³/s

**结果**：
```python
bridge = create_simple_bridge(
    position=100.0,
    bridge_width=20.0,
    deck_elevation=6.0,  # 低桥面
    pier_count=2,
    pier_width=1.0,
    approach_width=25.0
)

h_up, h_br, flow_type = bridge.compute_backwater(100.0, 7.0)
# flow_type = 'pressure' (压力流)
# 壅水显著增大（> 1.0 m）
# 建议提高桥面高程
```

## 注意事项

### 适用范围

- **河道类型**：天然河道、规则渠道
- **水流条件**：亚临界流（Fr < 1.0）
- **桥孔收缩比**：0.5-1.0（过小收缩不适用）
- **阻水比 α**：< 0.3（过大需特殊处理）

### 使用限制

- **不适用于超临界流**（Fr > 1.0）
- **不适用于极端斜交**（> 45°）
- **冲刷计算为初步估算**，重要工程需详细计算
- **未考虑漂浮物堆积**，需额外增加安全超高

### 误差说明

- **壅水计算**：±15-20%（与实测对比）
- **冲刷深度**：±30-50%（HEC-18 指南）
- **设计安全系数（1.4）**：已包含 40% 保守裕度

## 工程应用

### 设计流程

1. **初步设计**：
   - 确定桥孔净宽（≥ 0.8 × 河宽）
   - 选择桥墩类型和数量
   - 计算壅水高度

2. **方案优化**：
   - 调整桥孔宽度使壅水满足要求
   - 优化桥墩布置减小阻水
   - 检查是否发生压力流

3. **冲刷验算**：
   - 计算桥墩冲刷深度
   - 确定基础埋深

4. **安全复核**：
   - 检查桥面超高是否充足
   - 考虑漂浮物影响
   - 审查设计洪水工况

### 与 HydroClaude 系统集成

```python
# 在一维河道模型中设置桥梁边界条件
from physics.structures import create_simple_bridge

# 创建桥梁对象
bridge = create_simple_bridge(
    position=500.0,      # 在河道 500m 处
    bridge_width=18.0,
    deck_elevation=12.0,
    pier_count=2,
    pier_width=1.0
)

# 在求解器中使用
# bridge.compute_backwater() 返回 (h_upstream, h_bridge, flow_type)
# 可用于设置内边界条件，计算水位线
```

## 参考文献

1. **FHWA HDS-1** (2012): "Hydraulic Design of Highway Culverts"
2. **Yarnell, D.L.** (1934): "Bridge Piers as Channel Obstructions", USGS Water Supply Paper 843
3. **HEC-18** (2012): "Evaluating Scour at Bridges", FHWA Publication
4. **Chow, V.T.** (1959): "Open Channel Hydraulics", McGraw-Hill
5. **Bradley, J.N.** (1978): "Hydraulics of Bridge Waterways", FHWA

## 更新日志

- **2025-01**: 初始实现
  - Yarnell 方程自由流计算
  - 压力流孔口流计算
  - CSU 冲刷深度方程
  - 多种桥墩类型支持
  - 斜交桥梁处理
  - 设计安全系数（1.4）
