# 时变边界条件展示案例

## 概述

本案例展示HydroClaude UniversalModeler对**时变边界条件**的完整支持。通过三种不同类型的边界条件，演示如何模拟实际工程中的动态水力过程。

## 支持的边界条件类型

| # | 类型 | 用途 | 应用场景 |
|---|------|------|----------|
| 1 | **Sinusoidal**<br>正弦波动 | 周期性变化 | 潮汐、日用水量、周期调度 |
| 2 | **Step**<br>阶跃变化 | 突发事件 | 闸门开启、水库泄洪、应急 |
| 3 | **Linear**<br>线性变化 | 渐进过程 | 缓慢蓄水、计划泄洪、负荷斜坡 |

## 运行示例

### 方式1：运行所有案例
```bash
cd examples/example_time_varying_bc
python run_all.py
```

### 方式2：单独运行
```bash
# 正弦波动
python -m modeling.universal_modeler examples/example_time_varying_bc/config_sinusoidal.yaml

# 阶跃变化
python -m modeling.universal_modeler examples/example_time_varying_bc/config_step.yaml

# 线性变化
python -m modeling.universal_modeler examples/example_time_varying_bc/config_linear.yaml
```

## 案例1：正弦波动 (Sinusoidal)

### 场景描述

**场景**：模拟日周期性流量变化

**参数**：
- 基础流量：15 m³/s
- 波动幅度：±5 m³/s
- 周期：720秒（12分钟，模拟压缩时间）
- 流量范围：10-20 m³/s

### 配置示例

```yaml
simulation:
  type: unsteady
  dt: 1.0
  total_time: 1440.0    # 2个完整周期

  time_varying_bc:
    boundary: upstream
    type: sinusoidal

    # 正弦参数
    base: 15.0          # 基础值 (m³/s)
    amplitude: 5.0      # 振幅 (m³/s)
    period: 720.0       # 周期 (s)
    phase: 0.0          # 初相位 (弧度)
```

### 数学公式

```
Q(t) = base + amplitude × sin(2π×t/period + phase)
Q(t) = 15 + 5×sin(2π×t/720)
```

### 仿真结果

```
仿真时间: 37.48s
时间步数: 145
最终水深范围: 0.912 - 2.000 m
最终流速范围: 0.551 - 1.017 m/s
```

### 应用场景

1. **潮汐河道**
   - 受潮汐影响的河道流量
   - 周期：12小时（半日潮）

2. **日用水量变化**
   - 城市供水系统
   - 高峰时段vs谷时

3. **周期性水电调度**
   - 调峰水电站
   - 日调节水库

## 案例2：阶跃变化 (Step)

### 场景描述

**场景**：突发事件导致流量骤增

**参数**：
- 初始流量：12 m³/s
- 事件时刻：300秒（5分钟）
- 事件后流量：20 m³/s
- 流量增幅：+67%

### 配置示例

```yaml
simulation:
  type: unsteady
  dt: 1.0
  total_time: 600.0

  time_varying_bc:
    boundary: upstream
    type: step

    # 阶跃参数
    step_time: 300.0        # 阶跃时刻 (s)
    value_before: 12.0      # 阶跃前值 (m³/s)
    value_after: 20.0       # 阶跃后值 (m³/s)
```

### 数学公式

```
Q(t) = { value_before,  if t < step_time
       { value_after,   if t ≥ step_time

Q(t) = { 12 m³/s,  if t < 300s
       { 20 m³/s,  if t ≥ 300s
```

### 仿真结果

```
仿真时间: 17.13s
时间步数: 121
最终水深范围: 1.239 - 2.000 m
最终流速范围: 0.755 - 1.074 m/s
```

### 应用场景

1. **闸门突然开启**
   - 进水闸快速开启
   - 泄洪闸启动

2. **水库泄洪**
   - 应急泄洪
   - 防洪调度

3. **管道破裂**
   - 事故响应
   - 应急处置

4. **负荷突变**
   - 水电站负荷接入
   - 机组甩负荷

## 案例3：线性变化 (Linear)

### 场景描述

**场景**：流量逐步增加（模拟水库蓄水或缓慢泄洪）

**参数**：
- 起始流量：8 m³/s
- 终止流量：18 m³/s
- 变化时长：600秒（10分钟）
- 变化率：0.0167 m³/s²

### 配置示例

```yaml
simulation:
  type: unsteady
  dt: 1.0
  total_time: 800.0

  time_varying_bc:
    boundary: upstream
    type: linear

    # 线性参数
    start_value: 8.0        # 起始值 (m³/s)
    end_value: 18.0         # 终止值 (m³/s)
    duration: 600.0         # 变化持续时间 (s)
```

### 数学公式

```
Q(t) = { start_value + (end_value - start_value) × t/duration,  if t ≤ duration
       { end_value,                                              if t > duration

Q(t) = { 8 + 10×t/600 = 8 + 0.0167×t,  if t ≤ 600s
       { 18,                             if t > 600s
```

### 仿真结果

```
仿真时间: 22.44s
时间步数: 161
最终水深范围: 1.127 - 2.000 m
最终流速范围: 0.570 - 1.032 m/s
```

### 应用场景

1. **水库缓慢蓄水**
   - 调蓄水库
   - 渐进蓄水

2. **计划性泄洪**
   - 预泄调度
   - 控制下泄流量

3. **渐进式调度**
   - 水位抬升
   - 流量调节

4. **负荷斜坡变化**
   - 水电站启机
   - 渐增负荷

## 性能对比

| 边界条件类型 | 仿真时间 | 时间步数 | 总时长 | 性能 |
|-------------|---------|---------|--------|------|
| Sinusoidal | 37.48s | 145 | 1440s | 38.4× 实时 |
| Step | 17.13s | 121 | 600s | 35.0× 实时 |
| Linear | 22.44s | 161 | 800s | 35.7× 实时 |

**结论**：所有案例均达到 **30倍以上实时性能**，满足在线仿真需求。

## 技术实现

### 时变边界条件应用机制

在每个时间步，UniversalModeler会：

1. **计算当前边界值**
   ```python
   if bc_type == 'sinusoidal':
       value = base + amplitude * sin(2π * t / period + phase)
   elif bc_type == 'step':
       value = value_after if t >= step_time else value_before
   elif bc_type == 'linear':
       value = start_value + (end_value - start_value) * t / duration
   ```

2. **更新求解器边界条件**
   ```python
   if boundary == 'upstream':
       solver.Q_upstream = value
   elif boundary == 'downstream':
       solver.h_downstream = value
   ```

3. **执行Preissmann时间步进**
   ```python
   h_new, hu_new = solver.step_preissmann(...)
   ```

### 支持的边界类型

| 边界 | 变量 | 说明 |
|------|------|------|
| upstream | flow | 上游流量 (m³/s) |
| downstream | depth | 下游水深 (m) |

## 输出文件

每个案例生成以下文件：

```
results_<type>/
├── <type>_data.npz              # 数值数据
├── <type>_final_profile.png     # 最终纵剖面
└── <type>_time_series.png       # 时间序列
```

**时间序列图包含**：
- 水深历时曲线（多个监测点）
- 流速历时曲线
- 边界条件变化曲线

## 扩展应用

### 场景1：复合边界条件

将多个时变边界组合：

```python
# 自定义组合边界条件
# 上游：正弦波动
# 下游：线性抬升
```

### 场景2：多点扰动

在不同位置施加扰动：

```yaml
structures:
  - type: sluice_gate
    position: 5000.0
    # 闸门开度时变（未来功能）
```

### 场景3：实测数据驱动

```yaml
time_varying_bc:
  type: file
  filename: "measured_flow.csv"
  # 从文件读取实测流量数据
```

## 参数调节建议

### Sinusoidal 正弦波动

**周期 (period)**：
- 短周期（<100s）：高频扰动，需要小dt
- 中周期（100-1000s）：典型应用
- 长周期（>1000s）：低频变化

**振幅 (amplitude)**：
- 小振幅（<20%基础值）：微小扰动
- 中振幅（20-50%）：典型波动
- 大振幅（>50%）：剧烈变化

**相位 (phase)**：
- 0：初始为基础值，上升
- π/2：初始为最大值
- π：初始为基础值，下降
- 3π/2：初始为最小值

### Step 阶跃变化

**阶跃时刻 (step_time)**：
- 建议在 total_time 的 30-70% 之间
- 留出足够时间观察扰动传播

**阶跃幅度**：
- 小阶跃（<30%）：稳定性测试
- 中阶跃（30-100%）：典型应用
- 大阶跃（>100%）：极端工况

### Linear 线性变化

**变化时长 (duration)**：
- 快速（<total_time的30%）：类似阶跃
- 中速（30-70%）：典型渐变
- 慢速（>70%）：准稳态过程

**变化率**：
```
rate = (end_value - start_value) / duration
```
- 控制在 0.001-0.1 m³/s² 范围内

## 常见问题

### Q1: 如何选择合适的时间步长 (dt)？

**A**: 根据边界变化速率：
- 正弦波动：dt ≤ period/100
- 阶跃变化：dt = 0.5-2.0s（捕捉阶跃）
- 线性变化：dt = 1.0-5.0s

**经验法则**：
```
dt ≤ min(Δx/V_max, period/100)
```

### Q2: 为什么我的仿真不稳定？

**可能原因**：
1. dt过大 → 减小dt
2. 边界变化过快 → 增加duration
3. 初始条件不匹配 → 使用稳态初值

### Q3: 如何实现下游水深变化？

**A**: 修改配置：
```yaml
time_varying_bc:
  boundary: downstream  # 改为下游
  type: linear
  start_value: 2.0      # 初始水深
  end_value: 3.0        # 终止水深
```

### Q4: 支持同时施加多个时变边界吗？

**A**: 当前版本只支持单一时变边界。多个边界可通过：
1. 组合多次仿真
2. 自定义时变函数（代码级）

### Q5: 如何添加自定义时变函数？

**A**: 修改 `universal_modeler.py` 中的 `_apply_time_varying_bc()` 方法：

```python
elif bc_type == 'custom':
    # 自定义公式
    value = your_function(t)
```

## 实际工程应用案例

### 案例A：潮汐河道水位预测

**背景**：某沿海河道受潮汐影响

**配置**：
```yaml
time_varying_bc:
  type: sinusoidal
  base: 2.5           # 平均水位
  amplitude: 1.0      # 潮差
  period: 44700       # 12.42小时（半日潮）
```

### 案例B：水库应急泄洪

**背景**：上游水库超汛限，需紧急泄洪

**配置**：
```yaml
time_varying_bc:
  type: step
  step_time: 600      # 决策后10分钟执行
  value_before: 100
  value_after: 500    # 泄洪流量
```

### 案例C：调蓄水库蓄水过程

**背景**：新建水库初次蓄水

**配置**：
```yaml
time_varying_bc:
  type: linear
  start_value: 50
  end_value: 200
  duration: 86400     # 24小时渐进蓄水
```

## 相关案例

- **example_unsteady**: 基础非稳态模拟
- **example_control**: 控制系统（闭环）
- **engineering_cases/case_02**: 防洪应急响应
- **example_gate_pump_cascade**: 闸泵联合控制

## 参考文献

1. Chow, V. T. (1959). *Open-Channel Hydraulics*. McGraw-Hill.
2. Cunge, J. A., Holly, F. M., & Verwey, A. (1980). *Practical Aspects of Computational River Hydraulics*. Pitman.
3. Abbott, M. B., & Basco, D. R. (1989). *Computational Fluid Dynamics*. Longman Scientific & Technical.

## 许可证

本案例是HydroClaude项目的一部分，遵循项目许可证。

---

Generated with [Claude Code](https://claude.com/claude-code)

*案例完成于 2025-10-24*
