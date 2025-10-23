# 泵站扬程实现问题诊断报告

## 问题现象

### 1. 稳态计算异常
- **泵站处形成巨大尖峰**：上游3.6m → 泵站12m → 下游4.7m
- **下游扬程效果不足**：
  - 期望：下游 = 上游 + 5m = 8.60m
  - 实际：下游 = 4.72m
  - 偏差：-3.88m

### 2. 非稳态计算扬程失效
- t=0s：泵站处9.4m（错误的初始稳态）
- t=600s：泵站扬程效果迅速消失（9.4m → 3.6m）
- t=7200s：上游3.54m，下游3.54m，扬程效果≈0
- **结论**：虽然数值"稳定"，但泵站完全不起作用

## 根本原因分析

### 问题1：与浅水方程动力学不一致

当前实现方式（`solvers/hydrostatic_canal_solver.py:420-433`）：

```python
# 在_apply_internal_bc中，流量收敛后：
if isinstance(structure, PumpStation) and structure.is_running:
    h_up_current = self.h[idx - 1]
    h_down_target = h_up_current + structure.rated_head
    self.h[idx + 1] = h_down_current + pump_relax * (h_down_target - h_down_current)
```

**问题**：
1. 直接修改水深`self.h`，但不修改动量`self.hu`
2. 这导致水深-流速不一致
3. 下一个时间步，浅水方程会根据动力学重新计算，抹平人为施加的水深

### 问题2：稳态求解中的强制流量守恒冲突

在`solve_steady`中（第606行）：

```python
# 每次迭代都强制全渠道流量相同
hu_new[:] = Q_target / self.B
```

**冲突**：
1. 强制所有点`hu = Q_target / B`（流量守恒）
2. 然后在`_apply_internal_bc`中修改泵站下游水深`h[idx+1]`
3. 但水深增加后，为保持`hu`不变，流速`u = hu/h`会减小
4. 这导致连续性方程不满足，形成尖峰

### 问题3：泵站扬程的物理意义未正确建模

泵站的作用是：
- **增加水流能量**（势能）
- 在上下游之间建立**水位差**
- 本质是在动量方程中引入**压力梯度源项**

当前实现把它当作"水深的后处理修改"，忽略了：
1. 能量守恒
2. 动量平衡
3. 与浅水方程的耦合

## 正确的实现方法

### 方法A：源项法（推荐）

在动量方程中加入泵站源项：

```python
# 动量方程：∂(hu)/∂t + ∂(hu²/h + 0.5gh²)/∂x = -ghS_f + S_pump

# S_pump = g * h * ΔH/Δx  （泵站扬程梯度）
# 其中 ΔH = rated_head, Δx为泵站作用范围
```

**实现位置**：`compute_fluxes_and_sources`中的`S_momentum`

**优点**：
- 与浅水方程动力学一致
- 能量守恒
- 稳态和非稳态都适用

### 方法B：内部边界条件法

把泵站视为内部边界，类似闸门：

```python
# 上游（idx-1）和下游（idx+1）之间建立关系：
# 1. 流量连续：Q_up = Q_down = Q_pump
# 2. 能量方程：H_down = H_up + ΔH
#    其中 H = h + u²/(2g) + z  （总水头）
#    ΔH = rated_head （扬程）

# 求解这两个方程得到h_up和h_down
```

**优点**：
- 物理意义明确
- 类似闸门实现，易理解

**缺点**：
- 需要求解非线性方程组
- 实现复杂

### 方法C：跃变条件法（最简单）

在泵站位置直接施加水深跃变：

```python
# 每个时间步后，强制下游水深：
h[idx+1] = h[idx-1] + rated_head

# 同时调整动量保持流量守恒：
Q = hu[idx-1] * B
hu[idx+1] = Q / B
```

**问题**：
- 仍然是"后处理"修改
- 可能引起数值不稳定
- 需要与时间步进同步

## 推荐方案

**采用方法A（源项法）**：

1. 在`PumpStation`类中添加方法：
   ```python
   def get_momentum_source(self, h, dx):
       """计算泵站引起的动量源项"""
       # S = g * h * rated_head / (pump_length)
       # pump_length 可设为2-3个网格间距
       return 9.81 * h * self.rated_head / (3 * dx)
   ```

2. 在`compute_fluxes_and_sources`中添加泵站源项：
   ```python
   for idx, structure in zip(self.structure_indices, self.structure_objects):
       if isinstance(structure, PumpStation) and structure.is_running:
           # 在泵站下游几个网格点施加源项
           S_momentum[idx:idx+3] += structure.get_momentum_source(h[idx], self.dx)
   ```

3. 移除`_apply_internal_bc`中的泵站水深修改逻辑

## 验证标准

修复后，应满足：

### 稳态验证
1. ✅ 泵站上游水深 ≈ 3.6m
2. ✅ 泵站下游水深 ≈ 8.6m（上游 + 5m扬程）
3. ✅ 水位变化平滑，无尖峰（梯度<5度）
4. ✅ 流量守恒误差<1%

### 非稳态验证
1. ✅ 扬程效果持续存在（不随时间消失）
2. ✅ 最终稳态与solve_steady结果一致
3. ✅ 泵站下游水位稳定在8.6m左右
4. ✅ 时间演化过程平滑

## 数值证据

从`analyze_pump_issue.py`输出：

```
稳态计算:
  上游1km处: 3.5976 m
  下游1km处: 4.7212 m  ❌ 应该是 8.5976 m
  偏差: -3.8764 m

非稳态计算:
  t=0s:    扬程效果 = 1.1236 m
  t=600s:  扬程效果 = -0.0519 m  ❌ 扬程消失
  t=7200s: 扬程效果 = -0.0033 m  ❌ 完全失效
```

## 后续行动

1. ✅ 诊断完成 - 本文档
2. ⏳ 实现方法A（源项法）
3. ⏳ 重新运行模拟验证
4. ⏳ 提交修复代码到git

---

**报告日期**: 2025-10-23
**问题严重性**: P0 - Critical
**修复优先级**: Immediate
