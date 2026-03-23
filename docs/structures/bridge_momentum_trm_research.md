# HEC-RAS Bridge Momentum Method 调研报告

## 概述

本报告基于 HEC-RAS Hydraulic Reference Manual (HRM) Chapter 5 "Bridge Hydraulics"
以及 HEC-RAS Technical Reference Manual (TRM)，整理桥梁动量法的完整计算步骤。
同时对照 HydroClaude 现有实现（`solvers/steady_profile_solver.py`）分析差异。

---

## 1. 四断面模型（Section 1/2/3/4）

HEC-RAS 桥梁模型采用四个控制断面：

| 断面 | 位置 | 用途 |
|------|------|------|
| Section 4 (最下游) | 距桥梁约 1 倍扩展长度下游 | 下游边界，标准步进法计算 |
| Section 3 (内侧下游面) | 桥梁下游桥面板底缘处 | 动量方程的"已知端" |
| Section 2 (内侧上游面) | 桥梁上游桥面板底缘处 | 动量方程的"求解端" |
| Section 1 (最上游) | 距桥梁约 1 倍收缩长度上游 | 上游边界，标准步进法计算 |

注意：HEC-RAS 计算方向为从下游向上游（逆流），因此：
- Section 3 = 下游桥面（已知 WSE）
- Section 2 = 上游桥面（求解 WSE）

HydroClaude 实现中的变量对应关系：
- `W_downstream` = Section 3 的水面高程（已知）
- `W3_trial` = Section 2 的水面高程（Newton-Raphson 迭代求解）
- `ds_xs_index` 对应 Section 3 断面几何
- `us_xs_index` 对应 Section 2 断面几何

---

## 2. 动量方程（完整形式）

### 2.1 HEC-RAS TRM 标准形式

在 Section 3（下游桥面）到 Section 2（上游桥面）之间建立动量平衡：

```
beta3 * rho * Q * V3 + P3 = beta2 * rho * Q * V2 + P2 + F_f + F_pier + W_x
```

各项定义：

| 符号 | 定义 | 单位 |
|------|------|------|
| beta2, beta3 | Boussinesq 动量修正系数（速度分布不均匀修正） | 无量纲 |
| rho | 水的密度 = 1000 | kg/m³ |
| Q | 通过桥孔的流量（扣除漫顶后） | m³/s |
| V2 | Section 2（上游面）的平均流速 = Q / A2_eff | m/s |
| V3 | Section 3（下游面）的平均流速 = Q / A3_eff | m/s |
| P2 | Section 2 的静水压力合力 = gamma * A2 * y_bar_2 | N |
| P3 | Section 3 的静水压力合力 = gamma * A3 * y_bar_3 | N |
| F_f | 河床和桥梁侧壁的摩擦力（Manning 公式） | N |
| F_pier | 桥墩拖曳力 | N |
| W_x | 控制体内水体重力在流向的分量 | N |

### 2.2 静水压力计算

```
P = gamma * A * y_bar_c
```

其中 y_bar_c 为断面形心到水面的距离。

矩形断面等效近似（HydroClaude 实现）：
```
y_bar_c ≈ A / (2 * T)
```
T 为水面宽度。

精确形式应为：
```
y_bar_c = integral(y * dA) / A
```

### 2.3 摩擦力

```
F_f = gamma * A_avg * Sf_avg * L_bridge
```

其中 Sf_avg 用平均断面的 Manning 公式计算：
```
Sf = (Q * n / (A * R^(2/3)))^2
```

### 2.4 桥墩拖曳力

```
F_pier = 0.5 * rho * C_D * A_pier_avg * V_avg^2
```

| 参数 | 说明 |
|------|------|
| C_D | 拖曳系数，依桥墩头部形状选取 |
| A_pier_avg | 平均桥墩迎水面积 = pier_w_total * min(h, pier_height) |
| V_avg | 控制体平均流速 = Q / A_avg |

### 2.5 重力分量

```
W_x = gamma * A_avg * S0_bridge * L_bridge
```

S0_bridge = (bed_us - bed_ds) / L_bridge（河底坡度，正值=顺坡）

---

## 3. Section 2 和 Section 3 的几何构造

### 3.1 Lid Profile（桥面板轮廓）的作用

HEC-RAS 在构造桥梁内侧断面时，将桥面板（Lid/Deck）叠加到河道断面上，
形成有效过流面积。

**低弦（Low Chord）** = 桥梁底板最低高程 = `deck_elevation_m`
- 自由水面流：水位低于 low chord，不扣减桥面面积
- 压力流：水位超过 low chord，桥面板截断水面，上部为固体边界

**高弦（High Chord）** = 桥面板顶部高程 = `high_chord_m`
- 水位超过 high chord：发生漫顶（堰流）

### 3.2 有效面积计算步骤

```
A_eff = A_bridge_face - A_pier
```

其中 A_bridge_face 的计算：

1. 优先方式：从断面实测坐标（distances/elevations）精确积分桥孔范围内面积
   - 桥孔范围 = [center - opening_w/2, center + opening_w/2]
   - 使用 `_segment_area_perimeter()` 在给定水位下积分

2. 回退（无实测坐标）：矩形近似
   - A_bridge_face = opening_w * (WSE - min_elevation)

3. 上限约束：A_eff 不超过全断面积 A_full

4. 下限约束：A_eff >= A_full * 0.05（防止零面积数值奇点）

### 3.3 压力流时的面积修正

当 EGL > deck_elev 时（压力流条件），扣减桥面板占据的面积：
```
A_eff = max(A_eff - (WSE - deck_elev) * T, A_full * 0.1)
```

注意：这里使用 EGL（能量梯度线）而非 WSE 判断压力流，
EGL = WSE + V^2 / (2g)。这与 HEC-RAS TRM 的判别准则一致。

---

## 4. 桥墩拖曳系数 C_D 的确定

### 4.1 HEC-RAS 推荐值（按桥墩头部形状）

| 桥墩头部形状 | C_D 推荐值 |
|------------|-----------|
| 方形（Square nose） | 2.0 |
| 圆形（Round nose） | 1.4 |
| 圆柱形（Circular） | 1.4 |
| 尖锐形（Sharp nose） | 1.2 |
| 流线型 | 0.7~1.0 |

### 4.2 HydroClaude 实现

```python
# 优先从 coefficients.momentum_cd 读取，其次用 pier_cd，默认 2.0
C_D = float(_coefs.get("momentum_cd", bridge.get("pier_cd", 2.0)))
```

默认值 2.0 对应方形桥墩（最保守估计）。

---

## 5. 压力流 vs 自由水面流判别

### 5.1 判别条件

HEC-RAS 使用 EGL 判别（非 WSE）：

```
if EGL_upstream > low_chord_elevation:
    → 压力流（或孔口流）
```

EGL = WSE + alpha * V^2 / (2g)

### 5.2 流态分类

| 流态类型 | 条件 | 计算方法 |
|---------|------|---------|
| Class A (自由水面流) | WSE < low chord | 能量法或动量法（自由水面） |
| Class B (压力流) | EGL > low chord，WSE < high chord | 动量法 + 压力流修正 |
| Class C (压力流+堰流) | EGL > low chord，WSE > high chord | 桥下压力流 + 桥上堰流并联 |

### 5.3 压力流方程

情形一：单侧淹没（Sluice Gate Flow，下游未淹没桥底）
```
Q_under = Cd * A * sqrt(2g * Y_u)
```
Y_u = 上游 WSE 与过流断面形心高程之差
Cd 典型值 = 0.5

情形二：双侧淹没（Orifice Flow，下下游均淹没桥底）
```
Q_under = Cd * A * sqrt(2g * delta_H)
```
delta_H = 上游 EGL - 下游 WSE
Cd 典型值 = 0.8

### 5.4 HydroClaude 实现

```python
# 压力流初始猜测：
_ds_submerged = W_downstream > deck_elev
_Cd_press = _sub_io_cd if _ds_submerged else _sub_inlet_cd  # 0.8 or 0.5
_H_eff = (Q / (_Cd_press * _A_opening)) ** 2 / (2.0 * self.g)
W3_pressure = W_downstream + _H_eff
```

---

## 6. 漫顶流量分配（Class C 混合流）

当 WSE > high_chord_elev 时，总流量分为桥下通流和桥面漫顶：
```
Q_total = Q_under + Q_weir
Q_weir = Cd_weir * L_weir * H^1.5    (H = WSE - high_chord)
Q_under = Q_total - Q_weir
```

迭代收敛后，动量方程仅用 Q_under 计算。

---

## 7. Newton-Raphson 迭代求解

HydroClaude 使用有限差分 Newton 法迭代求解 W3_trial（Section 2 上游水面）：

```python
# 数值微分
d_imb_dW = (imbalance_p - imbalance) / dW   # dW = 1e-3 m

# Newton 步长（限幅 ±0.5m）
step = clip(-imbalance / d_imb_dW, -0.5, 0.5)
W3_trial += step
```

收敛准则：`|imbalance| < max(1.0, |RHS| * 1e-5)` N

最大迭代次数：40

---

## 8. Low Chord 和 High Chord 在动量方程中的具体作用

### 8.1 Low Chord (deck_elevation_m)

1. **流态判别**：EGL > low chord → 压力流模式
2. **面积修正**：压力流时扣减桥面板占据的流通面积
3. **初始猜测**：提供压力流估算的参考水头
4. **漫顶堰高**：当 high_chord 未定义时，用 low chord 作为堰顶高程

### 8.2 High Chord (high_chord_m)

1. **堰流触发**：WSE > high chord → 启动漫顶堰流分流
2. **流量分配**：决定 Q_weir 和 Q_under 的分配
3. **桥面板顶边界**：高于 high chord 的面积进入堰流，不参与动量方程

---

## 9. HydroClaude 实现与 HEC-RAS TRM 的对比

| 项目 | HEC-RAS TRM | HydroClaude 实现 | 状态 |
|------|-------------|-----------------|------|
| 动量方程形式 | beta3*rho*Q*V3 + P3 = RHS | 相同 | 一致 |
| Section 命名 | Section 2/3 | us/ds bridge face | 等价 |
| 静水压力 | gamma*A*y_bar_c | gamma*A*(A/(2T)) 矩形近似 | 简化近似 |
| 面积构造 | Lid Profile 精确几何 | _bridge_face_area() 段积分+矩形回退 | 部分实现 |
| EGL 判别压力流 | EGL > low chord | 同 | 一致 |
| C_D 推荐值 | 按桥墩形状查表 | 默认 2.0（方形），可配置 | 可改进 |
| 漫顶分流 | Q_total = Q_under + Q_weir | _split_deck_overtopping_flow() | 一致 |
| 求解器 | 内部迭代 | Newton-Raphson 有限差分 | 合理 |

---

## 10. 参考文献

1. USACE HEC (2016). HEC-RAS River Analysis System, Hydraulic Reference Manual, Version 5.0. CPD-69.
   Chapter 5: Bridge Hydraulics, pp. 5-1 to 5-58.

2. USACE HEC (2021). HEC-RAS River Analysis System, Hydraulic Reference Manual, Version 6.0.
   Chapter 5: Bridge Hydraulics.
   URL: https://www.hec.usace.army.mil/confluence/rasdocs/ras1dtechref/latest

3. Bradley, J.N. (1978). Hydraulics of Bridge Waterways. FHWA Hydraulic Design Series No. 1.

4. Yarnell, D.L. (1934). Bridge Piers as Channel Obstructions. USGS Water Supply Paper 843.
