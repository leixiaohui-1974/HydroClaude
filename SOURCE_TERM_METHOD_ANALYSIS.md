# 源项法诊断报告

## 问题发现

源项已正确添加到动量方程（0.123 N/m³），但没有产生扬程效果。

## 根本原因

**稳态求解方法 `solve_steady_state()` 与源项法存在根本性冲突**：

```python
# solve_steady_state() 中的流量强制设置
for iteration in range(max_iterations):
    h_new, hu_new = self.step_preissmann(dt)  # 源项在这里起作用
    
    # ❌ 问题：强制覆盖所有节点的流量
    hu_new[:] = Q_target / self.B  # 这会抵消源项的效果！
    
    self.h = h_new
    self.hu = hu_new
```

### 为什么会冲突？

1. **源项法的作用机制**：
   - 源项 `S_pump = g * H / Δx` 添加到动量方程
   - 通过Preissmann求解器，源项改变动量(hu)
   - 动量变化导致水位抬升

2. **稳态求解的强制约束**：
   - 每次迭代后强制 `hu[:] = Q_target / B`
   - 这会**完全覆盖**源项产生的动量变化
   - 源项的效果被抹掉

3. **结果**：
   - 源项虽然存在，但效果被稳态求解方法抵消
   - 水位无法抬升

## 解决方案

### 方案A：修改稳态求解，排除泵站节点（当前已实现）

```python
# 获取泵站区域掩码
pump_mask = self._get_pump_region_mask()

# 只在非泵站区域强制流量
if pump_mask.any():
    self.hu[~pump_mask] = Q_target / self.B
else:
    self.hu[:] = Q_target / self.B
```

**问题**：这仍然不够，因为泵站节点的hu会被_apply_pump_internal_bc设置。

### 方案B：源项法需要真正的瞬态演化

源项法的正确使用方式：
1. 从初始条件开始
2. 真正的时间推进（不是伪时间步）
3. 让源项逐渐累积效果
4. 最终达到稳态

**在瞬态求解中测试源项法：**

```python
# 瞬态模拟
for t in range(t_end):
    h_new, hu_new = solver.step_preissmann(dt)
    # 不强制流量！让源项自然起作用
    solver.h = h_new
    solver.hu = hu_new
```

### 方案C：回到内部边界条件法（最简单）

源项法虽然理论上最严格，但在稳态求解中不适用。

**内部边界条件法**更适合稳态问题：
- 直接施加跳跃条件
- 不依赖时间演化
- 立即达到稳态

## 结论

**源项法不适合当前的稳态求解器**！

建议：
1. **稳态问题**：使用内部边界条件法
2. **瞬态问题**：可以使用源项法

如果用户坚持使用源项法，需要：
1. 完全重写稳态求解方法
2. 或者只在瞬态模拟中使用源项法
