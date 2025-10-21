import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager

def set_cjk_font():
    """Set a CJK font if available."""
    # List of common CJK fonts
    cjk_fonts = ['Noto Sans CJK JP', 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS']

    for font in cjk_fonts:
        try:
            # Check if the font is available
            matplotlib.font_manager.findfont(font)
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False
            print(f"Using font: {font}")
            return
        except:
            continue
    print("Warning: No CJK font found. Chinese characters may not display correctly.")

set_cjk_font()

from physics.canal_hf import CanalHighFidelity
from physics.pipe_hf import PipeHighFidelity

def example_preissmann_vs_fvm():
    """示例：Preissmann vs FVM对比"""
    import matplotlib.pyplot as plt

    print("\n" + "="*60)
    print("示例：Preissmann四点格式 vs 有限体积法对比")
    print("="*60)

    # 系统参数
    length = 5000.0
    width = 10.0
    n_sections = 51
    dt = 1.0
    n_steps = 100

    # Preissmann格式
    print("\n运行Preissmann格式...")
    canal_p = CanalHighFidelity(
        "明渠_Preissmann", length, width, 5000, 10000,
        method='preissmann', n_sections=n_sections
    )

    history_p = []
    for step in range(n_steps):
        bc = {'upstream_level': 5.0 + 0.5*np.sin(2*np.pi*step/50),
              'downstream_flow': 5.0}
        state = canal_p.step(dt, bc)
        history_p.append(state)

    # FVM格式
    print("\n运行有限体积法...")
    canal_f = CanalHighFidelity(
        "明渠_FVM", length, width, 5000, 10000,
        method='fvm', n_sections=n_sections
    )

    history_f = []
    for step in range(n_steps):
        bc = {'upstream_level': 5.0 + 0.5*np.sin(2*np.pi*step/50),
              'downstream_flow': 5.0}
        state = canal_f.step(dt, bc)
        history_f.append(state)

    # 可视化
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.arange(n_steps) * dt / 60  # 转为分钟

    # 平均水位
    ax = axes[0, 0]
    levels_p = [s['level'] for s in history_p]
    levels_f = [s['level'] for s in history_f]
    ax.plot(time, levels_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(time, levels_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('平均水位 (m)')
    ax.set_title('水位时间历程')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 平均流量
    ax = axes[0, 1]
    flows_p = [s['flow'] for s in history_p]
    flows_f = [s['flow'] for s in history_f]
    ax.plot(time, flows_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(time, flows_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('平均流量 (m³/s)')
    ax.set_title('流量时间历程')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 空间分布（最后时刻）
    ax = axes[1, 0]
    x_p, h_p, Q_p = canal_p.get_profile()
    x_f, h_f, Q_f = canal_f.get_profile()
    ax.plot(x_p, h_p, 'b-', linewidth=2, label='Preissmann')
    ax.plot(x_f, h_f, 'r--', linewidth=2, label='FVM')
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('水深 (m)')
    ax.set_title('水深空间分布（最终时刻）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 误差分析
    ax = axes[1, 1]
    errors = np.array(levels_p) - np.array(levels_f)
    ax.plot(time, errors, 'k-', linewidth=2)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (分钟)')
    ax.set_ylabel('水位差 (m)')
    rmse = np.sqrt(np.mean(errors**2))
    ax.set_title(f'两种方法差异 (RMSE={rmse:.6f}m)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('preissmann_vs_fvm.png', dpi=150, bbox_inches='tight')
    print("\n✓ 图表已保存: preissmann_vs_fvm.png")
    print(f"✓ 两种方法的RMSE: {rmse:.6f} m")
    print(f"✓ 最大差异: {np.max(np.abs(errors)):.6f} m")

def example_pipe_rk4():
    """示例：管道RK4高精度求解"""
    import matplotlib.pyplot as plt

    print("\n" + "="*60)
    print("示例：管道水击RK4高精度求解")
    print("="*60)

    # 创建管道
    pipe = PipeHighFidelity(
        "管道1", length=3000, diameter=1.0,
        wave_speed=1000, n_sections=51, method='rk4'
    )

    # 仿真：阀门突然关闭
    n_steps = 200
    dt = 0.1
    history = []

    print("\n运行仿真...")
    for step in range(n_steps):
        # 模拟阀门关闭
        if step < 100:
            bc = {'downstream_flow': 5.0}
        else:
            bc = {'downstream_flow': 0.5}  # 突然减小

        state = pipe.step(dt, bc)
        history.append(state)

        if step % 50 == 0:
            print(f"  步数 {step}/{n_steps}")

    # 可视化
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time = np.arange(n_steps) * dt

    # 平均压力
    ax = axes[0, 0]
    pressures = [s['pressure'] for s in history]
    ax.plot(time, pressures, 'b-', linewidth=2)
    ax.axvline(x=10, color='r', linestyle='--', alpha=0.5, label='阀门关闭')
    ax.set_xlabel('时间 (秒)')
    ax.set_ylabel('压力 (m)')
    ax.set_title('平均压力变化')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 平均流量
    ax = axes[0, 1]
    flows = [s['flow'] for s in history]
    ax.plot(time, flows, 'g-', linewidth=2)
    ax.axvline(x=10, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (秒)')
    ax.set_ylabel('流量 (m³/s)')
    ax.set_title('平均流量变化')
    ax.grid(True, alpha=0.3)

    # 压力分布
    ax = axes[1, 0]
    x, H, Q = pipe.get_profile()
    ax.plot(x, H, 'b-', linewidth=2)
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('压力水头 (m)')
    ax.set_title('压力空间分布（最终时刻）')
    ax.grid(True, alpha=0.3)

    # 流量分布
    ax = axes[1, 1]
    ax.plot(x, Q, 'g-', linewidth=2)
    ax.set_xlabel('距离 (m)')
    ax.set_ylabel('流量 (m³/s)')
    ax.set_title('流量空间分布（最终时刻）')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('pipe_rk4_waterhammer.png', dpi=150, bbox_inches='tight')
    print("\n✓ 图表已保存: pipe_rk4_waterhammer.png")
    print(f"✓ 最大压力: {np.max(pressures):.2f} m")
    print(f"✓ 压力波动: {np.max(pressures) - np.min(pressures):.2f} m")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("水网控制系统 - 高精度数值方法 V3.2")
    print("="*60)
    print("\n实现的方法:")
    print("✓ Preissmann四点隐式格式 (θ=0.6)")
    print("✓ 有限体积法 (HLL通量 + TVD限制器)")
    print("✓ 四阶Runge-Kutta法")
    print("✓ Newton-Raphson非线性求解")

    # 运行示例
    try:
        example_preissmann_vs_fvm()
    except Exception as e:
        print(f"\n示例1出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_pipe_rk4()
    except Exception as e:
        print(f"\n示例2出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print("\n精度对比:")
    print("• Preissmann: 二阶精度，无条件稳定")
    print("• FVM+HLL: 二阶精度，守恒性好")
    print("• RK4: 四阶精度，适合ODE")
    print("\n推荐配置:")
    print("• 明渠: Preissmann (θ=0.6) 或 FVM+Minmod")
    print("• 管道: RK4 + 中心差分")
    print("• 激波问题: FVM + TVD限制器")
