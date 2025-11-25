# -*- coding: utf-8 -*-
"""测试MPC控制方向"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from control.idz_model import IDZParameters
from control.mpc_controller import MPCController, MPCConfig

print("=" * 80)
print("测试MPC控制方向（K=-0.3）")
print("=" * 80)

# 创建MPC控制器
idz_params = IDZParameters(K=-0.3, tau_z=103.0, tau_d=206.0, theta=4.0)
mpc_config = MPCConfig(
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

controller = MPCController(idz_params, mpc_config, use_observer=True)

# 测试场景1：y=2.7m, setpoint=2.2m（水位过高）
print("\n【测试1】水位过高")
y_current = 2.7
setpoint = 2.2
error = y_current - setpoint

print(f"  当前水位 y = {y_current}m")
print(f"  目标水位 = {setpoint}m")
print(f"  误差 = {error:.1f}m (过高)")
print(f"\n  物理分析：")
print(f"    K=-0.3：Deltau=+1m -> Deltah=-0.3m")
print(f"    降低0.5m需要：Deltau = -0.5 / (-0.3) = +1.67m")
print(f"    所以应该：u ~= 2.0 + 1.67 = 3.67m")

u_optimal, diagnostics = controller.compute_control(y_current, setpoint)

print(f"\n  MPC输出：u_optimal = {u_optimal:.4f}m")

if u_optimal > 2.5:
    print(f"   MPC方向正确！(u > 2.5)")
else:
    print(f"   MPC方向错误！(u = {u_optimal:.2f}, 应该 > 2.5)")

# 测试场景2：y=2.0m, setpoint=2.2m（水位过低）
print("\n【测试2】水位过低")
y_current = 2.0
setpoint = 2.2
error = y_current - setpoint

print(f"  当前水位 y = {y_current}m")
print(f"  目标水位 = {setpoint}m")
print(f"  误差 = {error:.1f}m (过低)")
print(f"\n  物理分析：")
print(f"    K=-0.3：Deltau=-1m -> Deltah=+0.3m")
print(f"    提高0.2m需要：Deltau = -0.2 / (-0.3) = -0.67m")
print(f"    所以应该：u ~= 2.0 - 0.67 = 1.33m")

u_optimal, diagnostics = controller.compute_control(y_current, setpoint)

print(f"\n  MPC输出：u_optimal = {u_optimal:.4f}m")

if 1.0 < u_optimal < 2.0:
    print(f"   MPC方向正确！(1.0 < u < 2.0)")
else:
    print(f"   MPC方向错误！(u = {u_optimal:.2f}, 应该在1.0-2.0之间)")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)

# 检查状态空间矩阵
print(f"\nMPC内部状态空间矩阵：")
print(f"  A = \n{controller.A}")
print(f"  B = \n{controller.B.flatten()}")
print(f"  C = \n{controller.C.flatten()}")
print(f"  D = \n{controller.D.flatten()}")

print(f"\n关键问题诊断：")
print(f"  如果MPC输出始终是最小值(0.1)，可能原因：")
print(f"  1. 观测器估计错误")
print(f"  2. 预测模型方向错误")
print(f"  3. 优化目标函数配置不当")
print(f"  4. 约束过于严格")
