# 跃变法失效原因诊断

## 问题现象

### 稳态
- 泵站处13.3m尖峰，但下游1km处只有5.1m（期望8.7m）
- 说明跃变被施加，但迅速被"平滑"

### 非稳态
- t=0有尖峰，t=600s后消失
- 扬程效果被时间演化抹平

## 根本原因：调用时机错误

### 稳态求解中的问题

当前调用顺序（`solve_steady`）：
```python
# 迭代循环
for iteration in range(max_iterations):
    h_old = self.h.copy()

    # 1. Preissmann步（计算h_new）
    h_new, hu_new = self.step_preissmann(dt)

    # 2. 强制流量守恒
    hu_new[:] = Q_target / self.B

    # 3. 更新状态
    self.h = h_new
    self.hu = hu_new

    # 4. ✅ 施加泵站跃变
    self._apply_pump_head_jump()  # h[idx+1] = h[idx-1] + 5.0

    # 5. ❌ 调整闸门水深（可能覆盖泵站下游水深）
    self._apply_internal_bc(...)  # 修改h[idx±1]

    # 6. 检查收敛
    dh_max = max|h - h_old|  # ❌ 包含了泵站跃变点，永远不收敛！
```

**问题1**：`_apply_internal_bc`在泵站跃变之后调用，可能修改泵站下游水深

**问题2**：收敛判断包含了泵站跃变点，导致：
- 泵站下游h[idx+1]被设为h[idx-1]+5.0
- 下一次迭代，Preissmann步会试图"修正"这个不连续
- dh_max包含这个5m的跃变，永远不会<1e-4

### 非稳态求解中的问题

当前调用顺序（`solve_transient`）：
```python
# 时间循环
for step in range(n_steps):
    # 1. Preissmann时间步
    h_new, hu_new = self.step_preissmann(dt, ...)  # 根据动力学计算新状态

    # 2. 更新状态
    self.h = h_new
    self.hu = hu_new

    # 3. ✅ 施加泵站跃变
    self._apply_pump_head_jump()  # h[idx+1] = h[idx-1] + 5.0

    # 4. ❌ 调整闸门（可能覆盖）
    self._apply_internal_bc(...)

    # 下一个时间步
    # ❌ step_preissmann会基于当前h计算通量，试图"平滑"跃变
```

**问题**：
- 每个时间步施加跃变后
- 下一个时间步的Preissmann求解器会根据浅水方程动力学重新计算
- 浅水方程倾向于平滑不连续，所以跃变被"修正"掉

## 解决方案

### 方案A：修改Preissmann求解器，跳过泵站点

在`step_preissmann`中，泵站下游点(idx+1)不更新，保持跃变：

```python
def step_preissmann(self, dt, ...):
    # ... 求解线性方程组 ...

    # 更新时跳过泵站下游点
    pump_downstream_indices = self._get_pump_downstream_indices()

    for i in range(self.nx):
        if i not in pump_downstream_indices:
            self.h[i] = h_new[i]
            self.hu[i] = hu_new[i]
```

**问题**：实现复杂，破坏数值方法的一致性

### 方案B：使用松弛因子，部分保持跃变

不完全覆盖，而是"推动"下游水深向目标靠近：

```python
def _apply_pump_head_jump(self):
    relax = 0.5  # 松弛因子

    h_down_target = h_up + rated_head
    self.h[idx+1] = (1-relax)*self.h[idx+1] + relax*h_down_target
```

**问题**：只是缓解，不能根本解决

### 方案C：修改收敛判断，排除泵站点（推荐用于稳态）

```python
# 稳态求解中
mask = np.ones(self.nx, dtype=bool)
for idx in pump_downstream_indices:
    mask[idx] = False

dh_max = np.max(np.abs(self.h[mask] - h_old[mask]))
```

并且在施加跃变后，立即在下一个Preissmann步前"预设"边界：

```python
# 在step_preissmann内部，使用泵站点作为固定边界条件
```

### 方案D：将泵站建模为特殊网格段（最正确）

不把泵站当作"点"，而是一个"段"：
- 泵站占据几个网格单元（如3个）
- 这几个单元不参与浅水方程求解
- 直接设置：h[idx-1:idx+2] = 线性插值(h_up, h_down)

## 推荐实施方案

**短期修复（稳态）**：
1. 在`_apply_internal_bc`中跳过泵站相关点
2. 修改收敛判断，排除泵站下游点
3. 增加跃变的"刚性"，每次迭代都强制施加

**短期修复（非稳态）**：
1. 使用更大的松弛因子（0.8-0.9）
2. 每个时间步多次施加跃变（如施加3次）

**长期方案**：
重新设计泵站为"段模型"而非"点模型"

## 立即实施

先尝试最简单的修复：
1. ✅ 在`_apply_internal_bc`中跳过泵站下游点
2. ✅ 在`_apply_pump_head_jump`中使用较大松弛因子（0.9）
3. ✅ 在每次施加跃变后，同时修改idx和idx+1点以建立"平台"
