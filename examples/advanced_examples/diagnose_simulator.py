# -*- coding: utf-8 -*-
"""
诊断SimplifiedCanalSimulator的问题

分析为什么基准测试中所有控制器误差都超过70000m
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import numpy as np
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from control.idz_model import IDZParameters, IDZModel

print("=" * 80)
print("SimplifiedCanalSimulator诊断")
print("=" * 80)

# 测试1：IDZ模型的基本行为
print("\n测试1：IDZ模型的基本输出特性")
print("-" * 80)

idz_params = IDZParameters(K=100.0, tau_z=200.0, tau_d=300.0, theta=20.0)
dt = 2.0
model = IDZModel(idz_params, dt=dt)

print(f"IDZ参数: K={idz_params.K}, tau_z={idz_params.tau_z}s, tau_d={idz_params.tau_d}s")
print(f"采样时间: {dt}s")

# 测试常值输入
u = 2.0  # 闸门开度
print(f"\n常值输入u={u}m，观察输出：")

model.reset()
for i in range(10):
    y = model.step(u)
    print(f"  步骤 {i+1}: y = {y:10.4f} m")

print("\n观察：IDZ模型输出y是持续增长的（积分器特性）")
print("      这是水位的绝对值，不是增量！")

# 测试2：SimplifiedCanalSimulator的问题
print("\n" + "=" * 80)
print("测试2：SimplifiedCanalSimulator的实现问题")
print("-" * 80)

print("\n当前实现（错误）：")
print("  dy = self.model.step(u_total)")
print("  self.y = dy                      #  直接覆盖，丢失历史")
print("  y_absolute = self.base_level + self.y")
print()
print("问题：")
print("  1. IDZ模型输出y已经是水位的累积值（从0开始）")
print("  2. 不应该再加base_level，否则会导致水位持续偏高")
print("  3. 扰动处理也不正确：u_control + disturbance * 0.01")

# 测试3：模拟错误实现的效果
print("\n测试3：错误实现的模拟效果")
print("-" * 80)

model.reset()
base_level = 2.2
setpoint = 2.2
u_control = 2.0

print(f"目标水位: {setpoint} m")
print(f"初始控制量: {u_control} m")
print(f"基准水位: {base_level} m")
print()

for i in range(20):
    dy = model.step(u_control)
    y = dy  # 当前错误实现
    y_absolute = base_level + y  # 再加base_level
    error = y_absolute - setpoint

    if i < 5 or i % 5 == 0:
        print(f"步骤 {i+1:2d}: dy={dy:8.4f}, y={y:8.4f}, "
              f"y_absolute={y_absolute:8.4f}, error={error:8.4f}")

print("\n结果：水位持续增长，误差越来越大！")

# 测试4：正确实现
print("\n" + "=" * 80)
print("测试4：正确的实现方式")
print("-" * 80)

print("\n方案A：IDZ模型直接输出绝对水位")
print("  y = self.model.step(u)")
print("  return y  # 不需要base_level")
print()
print("方案B：使用水位增量")
print("  dy = self.model_incremental.step(u - u_nominal)")
print("  self.y += dy")
print("  return base_level + self.y")

# 测试方案A
print("\n测试方案A：")
model.reset()
setpoint = 2.2
u_nominal = 0.022  # 名义控制量，使稳态输出~=2.2m

print(f"使用u_nominal={u_nominal} (根据K=100估算: y=K*u=2.2)")

for i in range(20):
    y = model.step(u_nominal)
    error = y - setpoint

    if i < 5 or i % 5 == 0:
        print(f"步骤 {i+1:2d}: y={y:8.4f}, error={error:8.4f}")

print("\n观察：需要合适的u_nominal使稳态输出~=目标水位")

# 总结
print("\n" + "=" * 80)
print("诊断总结")
print("=" * 80)
print("\n问题根源：")
print("  1.  IDZ模型输出是绝对水位，不应该再加base_level")
print("  2.  控制量u和扰动Q的关系不清晰")
print("  3.  没有明确的稳态工作点")
print()
print("解决方案：")
print("  选项1：重新设计IDZ模型接口，使用增量形式")
print("  选项2：调整SimplifiedCanalSimulator，正确处理IDZ输出")
print("  选项3：使用更真实的渠道模拟器（SimplifiedCanalDynamics）")
print()
print("推荐：选项3 - 使用SimplifiedCanalDynamics")
print("  优点：物理意义清晰（水量平衡）")
print("  优点：有明确的上游流量和闸门流量")
print("  优点：更贴近实际工程应用")
