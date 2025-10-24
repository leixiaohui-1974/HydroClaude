# HydroClaude 控制系统示例

本目录包含HydroClaude控制系统的示例，演示如何使用PID和MPC控制器进行水位控制。

## 目录结构

```
example_control/
├── README.md                        # 本文件
├── config_pid_water_level.yaml     # PID水位控制配置
├── run_pid_control.py               # PID控制示例脚本
├── config_mpc_water_level.yaml     # MPC水位控制配置（基础版）
├── config_mpc_tuned.yaml            # MPC水位控制配置（调优版）
└── run_mpc_control.py               # MPC控制示例脚本
```

## 功能特性

### 1. PID控制器
- **经典反馈控制算法**
- 工业级实现，包含：
  - 抗饱和（Anti-windup）
  - 微分滤波（Derivative filtering）
  - 死区（Deadband）
  - 输出限制
- 参数直观，易于调节
- 实时性好，计算简单

### 2. MPC控制器（模型预测控制）
- **先进控制算法**
- 自适应功能，包含：
  - 在线模型辨识（RLS）
  - 参数自适应更新
  - 显式约束处理
  - 前馈预测控制
- 多目标优化（跟踪精度 vs 控制能耗）
- 适应系统动态变化

## 快速开始

### PID控制示例

```bash
cd examples/example_control
python run_pid_control.py
```

**场景**：
- 渠道长度：5 km
- 闸门位置：3 km
- 监测点：3.75 km
- 目标水位：2.5 m
- 控制周期：5 s

**性能**（典型值）：
- MAE: 0.79 m
- 稳态误差: 0.98 m
- 控制范围：0.2-2.0 m

### MPC控制示例

```bash
cd examples/example_control
python run_mpc_control.py  # 基础版
```

或使用调优版配置：

```bash
# 修改run_mpc_control.py中的配置文件名为config_mpc_tuned.yaml
```

**场景**：
- 相同的物理系统
- 预测时域：10-15步
- 控制时域：5-8步
- 在线模型辨识

**性能**（调优版）：
- MAE: 0.95 m（比基础版改善17%）
- 稳态误差: 1.29 m
- 控制平滑度：0.0085 m/步

## 配置文件说明

### PID控制配置

关键参数：

```yaml
control:
  type: pid
  setpoint: 2.5          # 目标水位 (m)
  control_interval: 5    # 控制周期（时间步数）

  controller:
    kp: 0.5              # 比例增益
    ki: 0.05             # 积分增益
    kd: 0.1              # 微分增益
    output_min: 0.2      # 输出下限 (m)
    output_max: 2.0      # 输出上限 (m)
    integral_min: -5.0   # 积分限制
    integral_max: 5.0
    derivative_filter: 0.1  # 微分滤波系数
    deadband: 0.01       # 死区 (m)
```

### MPC控制配置

关键参数：

```yaml
control:
  type: mpc
  setpoint: 2.3          # 目标水位 (m)
  control_interval: 5    # 控制周期（时间步数）

  controller:
    # 时域参数
    prediction_horizon: 15  # 预测时域
    control_horizon: 8      # 控制时域
    dt: 10.0                # MPC采样时间 (s)

    # 权重
    Q_weight: 1.0           # 状态跟踪权重
    R_weight: 1.0           # 控制权重

    # 约束
    u_min: 0.5              # 控制下限 (m)
    u_max: 1.8              # 控制上限 (m)
    du_max: 0.3             # 控制变化率限制

    # 自适应参数
    adaptation_rate: 0.02
    forgetting_factor: 0.95

    # 初始模型 (x[k+1] = A*x[k] + B*u[k])
    initial_A: [[0.9]]
    initial_B: [[0.1]]
```

## 控制器对比

| 特性 | PID | MPC |
|------|-----|-----|
| 计算复杂度 | 低 | 中等 |
| 参数调节 | 直观（3参数） | 较复杂（多参数） |
| 约束处理 | 简单限幅 | 显式优化 |
| 模型需求 | 无需模型 | 需要线性模型 |
| 预测能力 | 无 | 有（多步预测） |
| 自适应性 | 固定参数 | 在线辨识 |
| 实时性 | 优秀 | 良好 |
| 适用场景 | 单变量、简单系统 | 多变量、约束系统 |

## 参数调节指南

### PID调节

1. **比例增益 (Kp)**：
   - 增大：响应快，但可能震荡
   - 减小：稳定，但响应慢
   - 典型值：0.1-1.0

2. **积分增益 (Ki)**：
   - 作用：消除稳态误差
   - 过大：积分饱和
   - 典型值：0.01-0.1

3. **微分增益 (Kd)**：
   - 作用：抑制超调
   - 过大：噪声敏感
   - 典型值：0.05-0.2

### MPC调节

1. **权重矩阵**：
   - Q_weight大：追求精确跟踪
   - R_weight大：惩罚大控制量
   - 典型比例：Q/R = 1-100

2. **时域长度**：
   - prediction_horizon：10-20步
   - control_horizon：5-10步
   - 一般：control_horizon ≤ prediction_horizon/2

3. **自适应参数**：
   - adaptation_rate：0.01-0.05
   - forgetting_factor：0.9-0.99（越接近1越稳定）

## 输出文件

运行后生成：

```
results_[pid|mpc]_control/
├── [prefix]_data.npz              # 数值数据
├── [prefix]_control_performance.png  # 控制性能图
└── [prefix]_final_profile.png     # 最终纵剖面图
```

## 性能指标

系统自动计算：

- **MAE** (Mean Absolute Error): 平均绝对误差
- **RMSE** (Root Mean Square Error): 均方根误差
- **ISE** (Integral of Squared Error): 积分平方误差
- **IAE** (Integral of Absolute Error): 积分绝对误差
- **Steady-state Error**: 稳态误差

## 高级用法

### 自定义监测点和控制点

```yaml
control:
  monitoring_points: [50, 75, 90]  # 多点监测
  control_points: [0, 1]            # 多点控制
```

### 多结构物控制

```yaml
structures:
  - type: sluice_gate
    position: 2000.0
    # ...
  - type: sluice_gate
    position: 4000.0
    # ...

control:
  control_points: [0, 1]  # 控制两个闸门
```

## 故障排除

### 问题1：控制器无响应
- 检查`control_interval`是否合理
- 确认`monitoring_points`索引有效
- 验证`control_points`对应结构物

### 问题2：控制量饱和
- 放宽`u_min`和`u_max`
- 调整目标`setpoint`更保守
- 增大`du_max`（MPC）

### 问题3：震荡
- PID：减小Kp，增大Kd
- MPC：增大R_weight，减小Q_weight

### 问题4：稳态误差大
- PID：增大Ki（但注意积分饱和）
- MPC：减小R_weight，增大Q_weight
- 检查模型准确性（MPC）

## 扩展阅读

相关示例：
- `examples/example_14_adaptive_mpc/` - MPC基础示例
- `examples/example_23_control_comparison/` - 控制器对比

相关模块：
- `control/pid_controller.py` - PID控制器实现
- `control/adaptive_mpc.py` - 自适应MPC实现
- `control/control_interface.py` - 控制系统接口

## 许可证

本示例是HydroClaude项目的一部分，遵循项目许可证。

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
