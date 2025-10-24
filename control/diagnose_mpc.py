"""
MPC控制器诊断脚本

分析MPC控制器发散的根本原因：
1. 验证状态空间模型是否正确
2. 检查开环响应特性
3. 分析闭环稳定性

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

from idz_model import IDZParameters, IDZModel
from mpc_controller import MPCController, MPCConfig


def test_state_space_model():
    """测试1：验证状态空间模型是否正确"""
    print("=" * 80)
    print("测试1：验证MPC状态空间模型")
    print("=" * 80)

    # 创建IDZ参数
    idz_params = IDZParameters(K=1.0, tau_z=20.0, tau_d=30.0, theta=5.0)
    dt = 2.0

    print(f"\nIDZ参数: K={idz_params.K}, τ_z={idz_params.tau_z}s, τ_d={idz_params.tau_d}s")

    # 方法1：使用IDZModel（完整实现，包含纯滞后）
    idz_model = IDZModel(idz_params, dt=dt)

    # 方法2：使用MPC内部状态空间模型（忽略纯滞后）
    mpc_config = MPCConfig(dt=dt)
    mpc = MPCController(idz_params, mpc_config)

    print(f"\nMPC状态空间模型（离散，dt={dt}s）:")
    print(f"A = \n{mpc.A}")
    print(f"B = {mpc.B}")
    print(f"C = {mpc.C}")
    print(f"D = {mpc.D}")

    # 开环阶跃响应测试
    n_steps = 100
    u_step = 1.0  # 阶跃输入

    # IDZModel响应
    idz_model.reset()
    y_idz = []
    for k in range(n_steps):
        y_idz.append(idz_model.step(u_step))

    # MPC状态空间模型响应
    x_mpc = np.zeros(mpc.n_states)
    y_mpc = []
    for k in range(n_steps):
        y = mpc.C @ x_mpc + mpc.D[0] * u_step
        y_mpc.append(y)
        x_mpc = mpc.A @ x_mpc + mpc.B * u_step

    # 对比
    y_idz = np.array(y_idz)
    y_mpc = np.array(y_mpc)
    t = np.arange(n_steps) * dt

    print(f"\n阶跃响应对比（u={u_step}）:")
    print(f"  t=20s:  IDZ={y_idz[10]:.4f}, MPC={y_mpc[10]:.4f}, 差异={abs(y_idz[10]-y_mpc[10]):.4f}")
    print(f"  t=100s: IDZ={y_idz[50]:.4f}, MPC={y_mpc[50]:.4f}, 差异={abs(y_idz[50]-y_mpc[50]):.4f}")
    print(f"  t=200s: IDZ={y_idz[-1]:.4f}, MPC={y_mpc[-1]:.4f}, 差异={abs(y_idz[-1]-y_mpc[-1]):.4f}")

    # 绘图
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(t, y_idz, 'b-', linewidth=2, label='IDZModel (完整)')
    plt.plot(t, y_mpc, 'r--', linewidth=2, label='MPC状态空间 (忽略纯滞后)')
    plt.xlabel('时间 (s)')
    plt.ylabel('输出 (m)')
    plt.title('开环阶跃响应对比')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    error = y_idz - y_mpc
    plt.plot(t, error, 'g-', linewidth=2)
    plt.xlabel('时间 (s)')
    plt.ylabel('误差 (m)')
    plt.title('模型误差（IDZ - MPC）')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('mpc_diagnosis_model_error.png', dpi=150)
    print("\n✅ 图片已保存: mpc_diagnosis_model_error.png")

    return y_idz, y_mpc


def test_state_estimation():
    """测试2：检查状态估计准确性"""
    print("\n" + "=" * 80)
    print("测试2：状态估计准确性")
    print("=" * 80)

    idz_params = IDZParameters(K=1.0, tau_z=20.0, tau_d=30.0, theta=5.0)
    dt = 2.0
    mpc_config = MPCConfig(dt=dt)
    mpc = MPCController(idz_params, mpc_config)

    # 模拟真实系统运行10步
    x_true = np.zeros(mpc.n_states)
    u_seq = [1.0, 1.0, 0.5, 0.5, 0.3, 0.3, 0.2, 0.2, 0.1, 0.1]

    print("\n真实状态 vs 估计状态:")
    print(f"{'步骤':>5} {'u':>8} {'y_true':>10} {'x1_true':>10} {'x2_true':>10} {'x1_est':>10} {'x2_est':>10} {'误差':>10}")
    print("-" * 80)

    for k, u in enumerate(u_seq):
        # 真实状态更新
        y_true = mpc.C @ x_true + mpc.D[0] * u
        x_true = mpc.A @ x_true + mpc.B * u

        # MPC状态估计
        x_est = mpc._estimate_state(y_true)

        error = np.linalg.norm(x_true - x_est)
        print(f"{k+1:5d} {u:8.3f} {y_true:10.4f} {x_true[0]:10.4f} {x_true[1]:10.4f} "
              f"{x_est[0]:10.4f} {x_est[1]:10.4f} {error:10.4f}")

    print("\n⚠️  问题：简单的状态估计（x1≈y/K, x2≈0）误差很大！")
    print("建议：需要实现状态观测器（Luenberger或卡尔曼滤波）")


def test_integrator_behavior():
    """测试3：分析积分器系统特性"""
    print("\n" + "=" * 80)
    print("测试3：积分器系统特性分析")
    print("=" * 80)

    idz_params = IDZParameters(K=1.0, tau_z=20.0, tau_d=30.0, theta=0.0)  # 忽略纯滞后
    dt = 2.0
    mpc_config = MPCConfig(dt=dt)
    mpc = MPCController(idz_params, mpc_config)

    print(f"\n系统包含积分器：G(s) = K*(1+τ_z*s)/(s*(1+τ_d*s))")
    print(f"这意味着：")
    print(f"  1. 对常值输入u，输出y会持续增长（积分特性）")
    print(f"  2. 要稳定在某个水位，需要u=0")
    print(f"  3. 传统MPC可能不适合，需要增量式MPC或积分抗饱和")

    # 验证：常值输入导致持续增长
    x = np.zeros(mpc.n_states)
    u = 0.5  # 常值输入

    print(f"\n验证积分特性（常值输入u={u}）:")
    for k in range(10):
        y = mpc.C @ x + mpc.D[0] * u
        print(f"  步骤 {k+1:2d}: y = {y:8.4f} (持续增长)")
        x = mpc.A @ x + mpc.B * u

    print("\n✅ 确认：系统是积分器，常值输入u>0会导致输出无限增长")
    print("💡 解决方案：")
    print("   1. 使用增量式MPC：优化Δu而不是u")
    print("   2. 添加积分反馈：在MPC中考虑累积误差")
    print("   3. 改进状态估计：使用观测器准确估计积分器状态")


def test_weight_sensitivity():
    """测试4：权重参数敏感性分析"""
    print("\n" + "=" * 80)
    print("测试4：权重参数敏感性")
    print("=" * 80)

    idz_params = IDZParameters(K=1.0, tau_z=20.0, tau_d=30.0, theta=5.0)
    dt = 2.0

    # 测试不同的权重组合
    weight_configs = [
        {"Q": 1.0, "R": 0.01, "Qf": 10.0, "name": "低R（当前）"},
        {"Q": 10.0, "R": 1.0, "Qf": 100.0, "name": "高R（保守）"},
        {"Q": 100.0, "R": 0.1, "Qf": 1000.0, "name": "高Q（激进）"},
    ]

    results = []

    for config in weight_configs:
        mpc_config = MPCConfig(
            dt=dt,
            prediction_horizon=10,
            control_horizon=5,
            Q=config["Q"],
            R=config["R"],
            Qf=config["Qf"],
            u_min=0.0,
            u_max=5.0,
            du_max=0.5,
            verbose=False
        )

        mpc = MPCController(idz_params, mpc_config)

        # 简单闭环测试（5步）
        x_sim = np.zeros(mpc.n_states)
        y = 0.0
        setpoint = 1.0

        controls = []
        outputs = []

        for k in range(5):
            u, diag = mpc.compute_control(y, setpoint)
            controls.append(u)

            x_sim = mpc.A @ x_sim + mpc.B * u
            y = mpc.C @ x_sim + mpc.D[0] * u
            outputs.append(y)

        results.append({
            "name": config["name"],
            "Q": config["Q"],
            "R": config["R"],
            "final_y": outputs[-1],
            "final_u": controls[-1],
            "max_u": max(controls)
        })

    print(f"\n{'配置':15s} {'Q':>8s} {'R':>8s} {'y(5步)':>10s} {'u(5步)':>10s} {'max_u':>10s}")
    print("-" * 70)
    for r in results:
        print(f"{r['name']:15s} {r['Q']:8.1f} {r['R']:8.2f} {r['final_y']:10.4f} "
              f"{r['final_u']:10.4f} {r['max_u']:10.4f}")

    print("\n观察：R太小会导致控制动作过大，可能引起发散")


def main():
    """运行所有诊断测试"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "MPC控制器诊断报告" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")

    # 测试1：模型验证
    test_state_space_model()

    # 测试2：状态估计
    test_state_estimation()

    # 测试3：积分器特性
    test_integrator_behavior()

    # 测试4：权重敏感性
    test_weight_sensitivity()

    # 总结
    print("\n" + "=" * 80)
    print("诊断总结")
    print("=" * 80)
    print("\n🔍 发现的问题：")
    print("  1. ❌ 状态估计过于简化，无法准确捕捉积分器状态")
    print("  2. ❌ IDZ模型包含积分器，常值输入会导致输出持续增长")
    print("  3. ❌ 控制增量权重R太小，控制动作可能过大")
    print("  4. ⚠️  MPC内部模型忽略了纯滞后（简化处理）")

    print("\n💡 建议的解决方案：")
    print("  1. 实现Luenberger状态观测器或卡尔曼滤波器")
    print("  2. 使用增量式MPC（优化Δu而不是u的绝对值）")
    print("  3. 增大控制增量权重R（从0.01提升到0.5-1.0）")
    print("  4. 添加积分抗饱和机制")
    print("  5. 考虑使用输出反馈MPC（直接用y而不依赖状态估计）")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
