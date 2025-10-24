# 串联闸泵群系统控制策略对比

本目录包含三种控制策略在串联闸泵群系统中的应用示例，用于对比不同控制方法在应对扰动时的性能。

## 系统配置

### 物理系统
- **渠道长度**：100 km
- **结构物**：
  - 闸门1（25 km处）
  - 泵站（50 km处）
  - 闸门2（75 km处）

### 扰动场景
- **来水扰动**：t=300s时，上游流量从10 m³/s突增至15 m³/s（+50%）
- **分水扰动**：（待实现）t=600s时，中游取水3 m³/s

### 控制目标
- 维持监测点（闸门1上游，约20km处）水位在2.8m

## 三种控制策略

### 策略1: PID控制 - 反应式控制

**文件**：
- 配置：`config_01_pid_disturbance.yaml`
- 脚本：`run_01_pid_disturbance.py`

**特点**：
- **控制方式**：反应式，误差驱动
- **响应速度**：快速
- **计算复杂度**：低
- **参数调节**：直观（Kp, Ki, Kd）

**适用场景**：
- 需要快速响应的场合
- 计算资源有限
- 系统动态变化不大

**典型性能**（测试结果）：
```
MAE: 0.5463 m
RMSE: 0.5545 m
最大误差: 0.7170 m
扰动响应: 误差增幅 33.5%
控制平滑度: 0.0044 m/步
```

**优点**：
- ✓ 响应快速
- ✓ 实现简单
- ✓ 鲁棒性好
- ✓ 无需系统模型

**缺点**：
- ✗ 可能震荡
- ✗ 无法预见性
- ✗ 约束处理困难
- ✗ 参数调节需经验

---

### 策略2: MPC预测控制 - 计划式控制

**文件**：
- 配置：`config_02_mpc_predictive.yaml`
- 脚本：`run_02_mpc_predictive.py`

**特点**：
- **控制方式**：计划式，模型驱动
- **预测能力**：20步（200秒）前瞻
- **优化方法**：多步优化
- **约束处理**：显式优化

**关键参数**：
```yaml
prediction_horizon: 20  # 预测时域
control_horizon: 10     # 控制时域
Q_weight: 5.0           # 状态权重
R_weight: 2.0           # 控制权重
```

**适用场景**：
- 需要平滑控制
- 有严格约束要求
- 可获得扰动预测
- 计算资源充足

**优点**：
- ✓ 前馈预测
- ✓ 约束优化
- ✓ 平滑控制
- ✓ 模型自适应

**缺点**：
- ✗ 计算复杂
- ✗ 需要模型
- ✗ 参数较多
- ✗ 调试复杂

---

### 策略3: 分层分布式控制 - 协同控制

**文件**：
- 配置：`config_03_hierarchical.yaml`
- 脚本：`run_03_hierarchical.py`

**设计思想**：
```
        上层MPC（慢速，全局优化）
              ↓ 设定值
   ┌──────────┼──────────┐
   PID1      PID2       PID3
  （快速，局部执行）
```

**特点**：
- **双时间尺度**：上层慢（1分钟），下层快（10秒）
- **分离关注**：上层优化，下层执行
- **分布式**：每个控制点独立PID

**当前实现**：
- 使用增强型MPC模拟分层效果
- 超长预测时域（25步）+ 快速采样（6秒）
- 高Q权重（8.0）+ 快速自适应

**适用场景**：
- 大规模多点控制
- 需要可靠性和扩展性
- 计算资源分布式
- 层次化决策

**优点**：
- ✓ 结合两者优势
- ✓ 计算负担分散
- ✓ 系统可靠性高
- ✓ 易于扩展

**缺点**：
- ✗ 架构复杂
- ✗ 参数协调困难
- ✗ 实现工作量大

## 性能对比

### 控制精度对比

| 指标 | PID | MPC | 分层控制 |
|------|-----|-----|----------|
| MAE | 0.546 m | 待测 | 待测 |
| RMSE | 0.555 m | 待测 | 待测 |
| 最大误差 | 0.717 m | 待测 | 待测 |
| 稳态误差 | 0.702 m | 待测 | 待测 |

### 控制平滑度对比

| 指标 | PID | MPC | 分层控制 |
|------|-----|-----|----------|
| 平均变化 | 0.0044 m/步 | 待测 | 待测 |
| 最大变化 | 待测 | 待测 | 待测 |

### 扰动响应对比

| 指标 | PID | MPC | 分层控制 |
|------|-----|-----|----------|
| 扰动前MAE | 0.437 m | 待测 | 待测 |
| 扰动后MAE | 0.583 m | 待测 | 待测 |
| 误差增幅 | 33.5% | 待测 | 待测 |

### 计算复杂度对比

| 控制器 | 单步计算时间 | 内存占用 | 实时性 |
|--------|-------------|----------|--------|
| PID | O(1) | 低 | 优秀 |
| MPC | O(N³) | 高 | 良好 |
| 分层控制 | O(N³+M) | 中等 | 良好 |

注：N=预测时域，M=控制点数

## 运行示例

### 运行所有策略

```bash
cd examples/example_gate_pump_cascade/control_strategies

# 策略1: PID控制
python run_01_pid_disturbance.py

# 策略2: MPC预测控制
python run_02_mpc_predictive.py

# 策略3: 分层分布式控制
python run_03_hierarchical.py
```

### 批量对比运行

```bash
# 运行所有策略并保存结果
for script in run_*.py; do
    echo "Running $script..."
    python "$script"
done
```

### 结果分析

```python
import numpy as np
import matplotlib.pyplot as plt

# 加载结果
pid_result = np.load('results_pid_disturbance/pid_disturbance_data.npz', allow_pickle=True)
mpc_result = np.load('results_mpc_predictive/mpc_predictive_data.npz', allow_pickle=True)
hier_result = np.load('results_hierarchical/hierarchical_data.npz', allow_pickle=True)

# 对比绘图
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

# 控制性能对比
ax = axes[0]
ax.plot(pid_result['result'].item()['time'],
        pid_result['result'].item()['error_history'],
        label='PID')
ax.plot(mpc_result['result'].item()['time'],
        mpc_result['result'].item()['error_history'],
        label='MPC')
ax.plot(hier_result['result'].item()['time'],
        hier_result['result'].item()['error_history'],
        label='Hierarchical')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Error (m)')
ax.set_title('Control Performance Comparison')
ax.legend()
ax.grid(True, alpha=0.3)

# 控制量对比
ax = axes[1]
ax.plot(pid_result['result'].item()['control_history'], label='PID')
ax.plot(mpc_result['result'].item()['control_history'], label='MPC')
ax.plot(hier_result['result'].item()['control_history'], label='Hierarchical')
ax.set_xlabel('Control Step')
ax.set_ylabel('Control Action (m)')
ax.set_title('Control Action Comparison')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('control_comparison.png', dpi=150)
print("对比图已保存: control_comparison.png")
```

## 选择建议

### 选择PID，如果：
- 系统动态简单
- 需要快速响应
- 计算资源有限
- 无严格约束要求

### 选择MPC，如果：
- 需要平滑控制
- 有严格约束
- 可获得扰动预测
- 计算资源充足

### 选择分层控制，如果：
- 多点大规模系统
- 需要分布式架构
- 要求高可靠性
- 计算资源分布

## 扩展应用

### 1. 多点协同控制
```yaml
monitoring_points: [40, 90, 140]  # 3个监测点
control_points: [0, 2]            # 2个闸门
setpoint: [2.5, 3.0, 2.8]         # 各点目标
```

### 2. 扰动预测前馈
```yaml
# MPC配置中添加
disturbance_forecast:
  type: flow_forecast
  horizon: 10  # 预测10步
  source: weather_model
```

### 3. 自适应参数调节
```python
# 根据性能动态调整PID参数
if mae > 0.5:
    kp *= 1.1  # 增大比例增益
if oscillation_detected:
    kd *= 1.2  # 增大微分增益
```

## 参考文献

- 《模型预测控制》- Camacho & Bordons
- 《分层控制系统设计》- Mesarovic et al.
- 《自动控制原理》- 胡寿松

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
