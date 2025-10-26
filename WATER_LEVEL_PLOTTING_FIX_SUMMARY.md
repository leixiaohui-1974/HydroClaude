# 串联明渠闸泵群水位绘图修复总结

## 问题

在串联明渠闸泵群系统的仿真结果中，部分图表在绘制水位时只使用了水深（h），没有加上渠底高程（z），导致显示的不是真实的水位。

**正确公式：** `水位 η = 渠底高程 z + 水深 h`

## 修复文件

### 1. `examples/example_gate_pump_cascade/test_disturbances_simple.py`
- **位置：** 第163-179行，`plot_results` 函数
- **修复：** 添加水位计算 `eta_history = z_bed[None, :] + h_history`
- **影响：** 水位时空演化图

### 2. `examples/example_gate_pump_cascade/test_unsteady_complete.py`
- **位置1：** 第209-222行，`test_pump_on_off` 函数
- **位置2：** 第376-394行，`test_multi_disturbance` 函数
- **修复：** 添加水位计算 `eta_saves = z_bed[None, :] + h_saves`
- **影响：** 两处水位时空演化图

## 修复技术细节

```python
# 获取底床高程（包含泵站处的高程跳跃）
z_bed = solver.z

# 计算水位历史（使用NumPy广播）
eta_history = z_bed[None, :] + h_history  # (1, nx) + (nt, nx) = (nt, nx)

# 绘制水位时空演化图
im = ax.contourf(x, times, eta_history, levels=20, cmap='viridis')
plt.colorbar(im, ax=ax, label='水位 (m)')
```

## 验证结果

✅ **所有修复文件通过验证：**
- `test_disturbances_simple.py` - 通过
- `test_unsteady_complete.py` - 通过
- Python语法检查 - 通过

## 其他文件状态

以下文件已检查，**无需修复**：

- ✅ `gate_pump_cascade_system.py` - 已正确处理水位
- ✅ `test_unsteady_simple.py` - 无水位时空图，仅水深时间序列
- ✅ `utils/visualization_templates.py` - 已正确处理水位
- ✅ `control_strategies/*.py` - 无水位时空图
- ✅ `analyze_*.py` - 绘制水深是合理的（用于分析）

## 影响范围

本次修复确保以下类型的图表正确显示水位（水面高程）：
- 水位时空演化图（contourf）
- 纵剖面水位动态图

以下类型的图表保持不变（绘制水深是合理的）：
- 水深时间序列图
- 泵站精度分析图
- 稳定性分析图

## 修复日期

2025-10-26

## 详细说明

详细的修复说明和代码对比请参阅：
`examples/example_gate_pump_cascade/水位绘图修复说明.md`
