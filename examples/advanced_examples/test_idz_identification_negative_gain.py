"""
测试IDZ在线辨识对负增益系统的修复

验证修复后的IDZIdentifier能够正确辨识反向作用系统（K<0）

作者：HydroClaude Team
日期：2025-10-24
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
import matplotlib.pyplot as plt
from control.idz_model import IDZParameters
from control.online_identification import IDZIdentifier, IdentificationMethod
from linearized_canal_simulator import LinearizedCanalSimulator

print("=" * 80)
print("测试IDZ在线辨识对负增益系统的修复")
print("=" * 80)

# 创建线性化渠道仿真器（真实系统）
dt = 2.0
h_work = 2.5
a_work = 2.0

simulator = LinearizedCanalSimulator(h_work=h_work, a_work=a_work, dt=dt, use_linear=True)
simulator.reset()

# 获取真实系统参数
K_true, tau_true = simulator.get_system_params()
print(f"\n真实系统参数:")
print(f"  K = {K_true:.4f} m/m  ← 负值（反向作用）")
print(f"  τ = {tau_true:.1f}s")

# 创建在线辨识器
identifier = IDZIdentifier(dt=dt, method=IdentificationMethod.FORGETTING_RLS, use_scipy=False)

print(f"\n开始在线辨识测试...")
print(f"  采样时间: dt={dt}s")
print(f"  测试时长: 600s (300步)")
print(f"  激励信号: 阶跃+正弦波")

# 仿真参数
n_steps = 300
setpoint = 2.2

# 记录
time_hist = []
h_hist = []
u_hist = []
K_est_hist = []
tau_est_hist = []

# 初始化
simulator.h = h_work  # 从工作点开始
simulator.set_disturbance(20.0)

for k in range(n_steps):
    t = k * dt

    # 激励信号设计（用于参数辨识）
    if t < 100:
        # 阶段1：阶跃激励（0-100s）
        u = 2.5  # 从工作点2.0跳到2.5
    elif t < 200:
        # 阶段2：正弦激励（100-200s）
        u = 2.0 + 0.5 * np.sin(2 * np.pi * t / 100.0)
    elif t < 300:
        # 阶段3：方波激励（200-300s）
        u = 2.5 if (t // 20) % 2 == 0 else 1.5
    else:
        # 阶段4：随机激励（300-600s）
        u = 2.0 + 0.8 * (np.random.rand() - 0.5)

    # 约束控制量
    u = np.clip(u, 0.1, 4.0)

    # 仿真一步
    h = simulator.step(u)

    # 在线辨识更新
    idz_params = identifier.update(u, h)

    # 记录
    time_hist.append(t)
    h_hist.append(h)
    u_hist.append(u)

    if idz_params is not None:
        K_est_hist.append(idz_params.K)
        tau_est_hist.append(idz_params.tau_d)
    else:
        K_est_hist.append(np.nan)
        tau_est_hist.append(np.nan)

    # 显示进度
    if k % 50 == 0 and idz_params is not None:
        print(f"  t={t:.0f}s: K_est={idz_params.K:.4f}, τ_est={idz_params.tau_d:.1f}s")

# 最终辨识结果
print(f"\n" + "=" * 80)
print("辨识结果")
print("=" * 80)

final_idz = identifier.get_idz_parameters()
if final_idz is not None:
    print(f"\n最终辨识参数:")
    print(f"  K_est = {final_idz.K:.4f} m/m")
    print(f"  τ_z_est = {final_idz.tau_z:.1f}s")
    print(f"  τ_d_est = {final_idz.tau_d:.1f}s")
    print(f"  θ_est = {final_idz.theta:.1f}s")

    print(f"\n真实参数:")
    print(f"  K_true = {K_true:.4f} m/m")
    print(f"  τ_true = {tau_true:.1f}s")

    print(f"\n辨识误差:")
    K_error = abs(final_idz.K - K_true) / abs(K_true) * 100
    tau_error = abs(final_idz.tau_d - tau_true) / tau_true * 100
    print(f"  K误差 = {K_error:.1f}%")
    print(f"  τ误差 = {tau_error:.1f}%")

    # 评估辨识质量
    print(f"\n辨识质量评估:")
    if K_error < 20:
        print(f"  K辨识: ✅ 优秀 (误差<20%)")
    elif K_error < 50:
        print(f"  K辨识: ⭕ 可接受 (误差<50%)")
    else:
        print(f"  K辨识: ❌ 较差 (误差>{K_error:.1f}%)")

    # 检查符号
    if np.sign(final_idz.K) == np.sign(K_true):
        print(f"  K符号: ✅ 正确 (均为{'负' if K_true < 0 else '正'}值)")
    else:
        print(f"  K符号: ❌ 错误 (辨识={np.sign(final_idz.K)}, 真实={np.sign(K_true)})")
else:
    print("⚠️ 辨识未收敛")

# 绘图
fig, axes = plt.subplots(4, 1, figsize=(12, 12))

# 子图1：水位和控制量
ax1 = axes[0]
ax1_twin = ax1.twinx()
ax1.plot(time_hist, h_hist, 'b-', linewidth=2, label='Water level h')
ax1_twin.plot(time_hist, u_hist, 'g-', linewidth=1.5, alpha=0.7, label='Control u')
ax1.set_ylabel('Water level (m)', fontsize=12, color='b')
ax1_twin.set_ylabel('Gate opening (m)', fontsize=12, color='g')
ax1.set_title('Online Identification Test: Water Level and Control Input', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')
ax1_twin.legend(loc='upper right')

# 子图2：K估计
ax2 = axes[1]
ax2.plot(time_hist, K_est_hist, 'r-', linewidth=2, label='K_est (online)')
ax2.axhline(K_true, color='k', linestyle='--', linewidth=2, label=f'K_true={K_true:.4f}')
ax2.set_ylabel('Gain K (m/m)', fontsize=12)
ax2.set_title('Gain Identification (K)', fontsize=13, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 在图上标注关键区域
ax2.axvspan(0, 100, alpha=0.1, color='blue', label='Step')
ax2.axvspan(100, 200, alpha=0.1, color='green', label='Sine')
ax2.axvspan(200, 300, alpha=0.1, color='orange', label='Square')

# 子图3：τ估计
ax3 = axes[2]
ax3.plot(time_hist, tau_est_hist, 'purple', linewidth=2, label='τ_d_est (online)')
ax3.axhline(tau_true, color='k', linestyle='--', linewidth=2, label=f'τ_true={tau_true:.1f}s')
ax3.set_ylabel('Time constant τ_d (s)', fontsize=12)
ax3.set_title('Time Constant Identification (τ)', fontsize=13, fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 子图4：辨识误差收敛曲线
ax4 = axes[3]
K_error_hist = [abs(K_est - K_true) / abs(K_true) * 100 if not np.isnan(K_est) else np.nan
                for K_est in K_est_hist]
tau_error_hist = [abs(tau_est - tau_true) / tau_true * 100 if not np.isnan(tau_est) else np.nan
                  for tau_est in tau_est_hist]

ax4.plot(time_hist, K_error_hist, 'r-', linewidth=2, label='K error (%)')
ax4.plot(time_hist, tau_error_hist, 'purple', linewidth=2, label='τ error (%)')
ax4.axhline(20, color='orange', linestyle='--', alpha=0.5, label='20% threshold')
ax4.set_ylabel('Relative error (%)', fontsize=12)
ax4.set_xlabel('Time (s)', fontsize=12)
ax4.set_title('Identification Error Convergence', fontsize=13, fontweight='bold')
ax4.legend()
ax4.grid(True, alpha=0.3)
ax4.set_ylim([0, 200])

plt.tight_layout()
plt.savefig('idz_identification_negative_gain_test.png', dpi=150, bbox_inches='tight')
print(f"\n✅ 图片已保存: idz_identification_negative_gain_test.png")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)

if final_idz is not None and np.sign(final_idz.K) == np.sign(K_true):
    print("✅ 修复成功：IDZIdentifier现在能够正确辨识负增益系统！")
else:
    print("❌ 仍有问题：需要进一步调试")

print("=" * 80)
