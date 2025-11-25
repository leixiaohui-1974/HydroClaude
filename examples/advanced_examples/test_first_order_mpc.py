# -*- coding: utf-8 -*-
"""测试一阶MPC控制方向"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig

print("=" * 80)
print("测试一阶MPC控制方向（H(s) = K/(taus+1)）")
print("=" * 80)

# 创建一阶MPC（基于物理线性化）
K = -0.3      # 稳态增益
tau = 206.0   # 时间常数

mpc_config = FirstOrderMPCConfig(
    prediction_horizon=15,
    control_horizon=10,
    dt=2.0,
    Q=100.0,
    R=1.0,
    Qf=1000.0,
    u_min=0.1,
    u_max=4.0,
    du_max=0.5
)

controller = FirstOrderMPC(K, tau, mpc_config)

# 测试场景1：y=2.7m, setpoint=2.2m（水位过高）
print("\n" + "=" * 80)
print("【测试1】水位过高")
print("=" * 80)

y_current = 2.7
setpoint = 2.2
error = y_current - setpoint

print(f"  当前水位 y = {y_current}m")
print(f"  目标水位 = {setpoint}m")
print(f"  误差 = {error:.1f}m (过高)")
print(f"\n  物理分析：")
print(f"    K=-0.3：Deltau=+1m -> Deltay_ss=-0.3m")
print(f"    降低0.5m需要：Deltau = -0.5 / (-0.3) = +1.67m")
print(f"    所以应该：u ~= 2.0 + 1.67 = 3.67m")
print(f"    （但受增量约束du_max=0.5限制，最大u=2.5m）")

u_optimal, diagnostics = controller.compute_control(y_current, setpoint)

print(f"\n  MPC输出：u_optimal = {u_optimal:.4f}m")
print(f"  求解状态：{diagnostics['status']}")

if diagnostics['success']:
    print(f"\n  预测轨迹（前5步）:")
    pred_traj = diagnostics['predicted_trajectory']
    ctrl_seq = diagnostics['control_sequence']
    for k in range(min(5, len(pred_traj)-1)):
        print(f"    k={k}: y_pred={pred_traj[k]:.4f}m, u={ctrl_seq[k]:.4f}m")

# 验证方向
if u_optimal > 2.0:
    print(f"\n   MPC方向正确！(u > u_prev=2.0, 增大闸门开度以降低水位)")
else:
    print(f"\n   MPC方向错误！(u = {u_optimal:.2f}, 应该 > 2.0)")

# 手动验证：一步预测
y_pred_manual = controller.a * y_current + controller.b * u_optimal
print(f"\n  手动验证（一阶模型）：")
print(f"    y[k+1] = a*y[k] + b*u[k]")
print(f"           = {controller.a:.6f} * {y_current} + {controller.b:.6f} * {u_optimal:.4f}")
print(f"           = {y_pred_manual:.4f}m")
print(f"    Deltay = {y_pred_manual - y_current:.4f}m")

if y_pred_manual < y_current:
    print(f"     水位下降，方向正确！")
else:
    print(f"     水位上升，方向错误！")

# 测试场景2：y=2.0m, setpoint=2.2m（水位过低）
print("\n" + "=" * 80)
print("【测试2】水位过低")
print("=" * 80)

controller.reset()

y_current = 2.0
setpoint = 2.2
error = y_current - setpoint

print(f"  当前水位 y = {y_current}m")
print(f"  目标水位 = {setpoint}m")
print(f"  误差 = {error:.1f}m (过低)")
print(f"\n  物理分析：")
print(f"    K=-0.3：Deltau=-1m -> Deltay_ss=+0.3m")
print(f"    提高0.2m需要：Deltau = -0.2 / (-0.3) = -0.67m")
print(f"    所以应该：u ~= 2.0 - 0.67 = 1.33m")
print(f"    （受增量约束限制，最小u=1.5m）")

u_optimal, diagnostics = controller.compute_control(y_current, setpoint)

print(f"\n  MPC输出：u_optimal = {u_optimal:.4f}m")
print(f"  求解状态：{diagnostics['status']}")

if diagnostics['success']:
    print(f"\n  预测轨迹（前5步）:")
    pred_traj = diagnostics['predicted_trajectory']
    ctrl_seq = diagnostics['control_sequence']
    for k in range(min(5, len(pred_traj)-1)):
        print(f"    k={k}: y_pred={pred_traj[k]:.4f}m, u={ctrl_seq[k]:.4f}m")

# 验证方向
if u_optimal < 2.0:
    print(f"\n   MPC方向正确！(u < u_prev=2.0, 减小闸门开度以提高水位)")
else:
    print(f"\n   MPC方向错误！(u = {u_optimal:.2f}, 应该 < 2.0)")

# 手动验证
y_pred_manual = controller.a * y_current + controller.b * u_optimal
print(f"\n  手动验证（一阶模型）：")
print(f"    y[k+1] = {controller.a:.6f} * {y_current} + {controller.b:.6f} * {u_optimal:.4f}")
print(f"           = {y_pred_manual:.4f}m")
print(f"    Deltay = {y_pred_manual - y_current:.4f}m")

if y_pred_manual > y_current:
    print(f"     水位上升，方向正确！")
else:
    print(f"     水位下降，方向错误！")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)
print("一阶MPC使用稳定的传递函数 H(s) = K/(taus+1)")
print("没有积分器，预测轨迹会收敛到稳态值")
print("适合建模水渠系统的线性化动态特性")
print("=" * 80)
