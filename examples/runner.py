import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

from core.water_body import Canal, Reservoir, SettlingBasin, StorageTank
from core.control_device import Gate, Valve, Pump
from core.other_components import Pipe, DistributionPoint
from control.controller import PIDController
from simulation.engine import SimulationEngine
from validation.validator import ModelValidator

def example_1_simple_canal():
    """示例1: 简单明渠 + 模型对比"""
    print("\n" + "="*60)
    print("示例1: 简单明渠系统 - 高保真vs降阶模型对比")
    print("="*60)

    canal = Canal("渠池1", 5000, 10000, 300, 5000, slope=0.0002, method='fvm')
    gate = Gate("闸门1", 0, 10, width=5.0)
    gate.add_upstream(canal)

    pid = PIDController(0.5, 0.1, 0.05, (0, 10))

    # 降阶模式
    engine_reduced = SimulationEngine([canal, gate], pid, dt=60, mode='reduced')
    history_reduced = engine_reduced.run(3600 * 2)

    # 高保真模式
    canal2 = Canal("渠池2", 5000, 10000, 300, 5000, slope=0.0002, method='fvm')
    gate2 = Gate("闸门2", 0, 10, width=5.0)
    gate2.add_upstream(canal2)

    engine_high = SimulationEngine([canal2, gate2], pid, dt=60, mode='high_fidelity')
    history_high = engine_high.run(3600 * 2)

    # 对比可视化
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    time_r = np.array(history_reduced['time']) / 3600
    time_h = np.array(history_high['time']) / 3600

    # 水量对比
    ax = axes[0, 0]
    vol_r = [s['volume'] for s in history_reduced['states']['渠池1']]
    vol_h = [s['volume'] for s in history_high['states']['渠池2']]
    ax.plot(time_r, vol_r, 'b-', linewidth=2, label='降阶模型')
    ax.plot(time_h, vol_h, 'r--', linewidth=2, label='高保真模型')
    ax.set_ylabel('蓄水量 (m³)')
    ax.set_title('水量对比')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 水位对比
    ax = axes[0, 1]
    level_r = [s['level'] for s in history_reduced['states']['渠池1']]
    level_h = [s['level'] for s in history_high['states']['渠池2']]
    ax.plot(time_r, level_r, 'b-', linewidth=2, label='降阶')
    ax.plot(time_h, level_h, 'r--', linewidth=2, label='高保真')
    ax.set_ylabel('水位 (m)')
    ax.set_title('水位对比')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 流量对比
    ax = axes[1, 0]
    if '闸门1' in history_reduced['controls']:
        flow_r = history_reduced['controls']['闸门1']
        flow_h = history_high['controls']['闸门2']
        ax.plot(time_r, flow_r, 'g-', linewidth=2, label='降阶')
        ax.plot(time_h, flow_h, 'm--', linewidth=2, label='高保真')
    ax.set_xlabel('时间 (小时)')
    ax.set_ylabel('流量 (m³/s)')
    ax.set_title('闸门流量对比')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 误差分析
    ax = axes[1, 1]
    error = np.array(level_r) - np.array(level_h)
    ax.plot(time_r, error, 'k-', linewidth=2)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel('时间 (小时)')
    ax.set_ylabel('水位误差 (m)')
    ax.set_title(f'模型误差 (RMSE={np.sqrt(np.mean(error**2)):.4f}m)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('example1_model_comparison.png', dpi=100, bbox_inches='tight')
    print("✓ 图表已保存: example1_model_comparison.png")

def example_2_pump_characteristics():
    """示例2: 泵站特性曲线验证"""
    print("\n" + "="*60)
    print("示例2: 泵站特性曲线与效率分析")
    print("="*60)

    pump = Pump("测试泵站", 0, 10, 15, 45,
                rated_flow=6.0, rated_head=30.0,
                rated_power=150.0, efficiency=0.80)

    # 验证模型
    ModelValidator.validate_pump_model(pump)

    # 绘制特性曲线
    flows = np.linspace(0, pump.flow_max, 50)
    heads = []
    powers = []
    efficiencies = []

    for Q in flows:
        pump.update_state(1.0, {'target_flow': Q})
        heads.append(pump.state.head)
        powers.append(pump.state.power)
        efficiencies.append(pump.state.efficiency)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # H-Q曲线
    axes[0].plot(flows, heads, 'b-', linewidth=2)
    axes[0].axhline(y=pump.rated_head, color='r', linestyle='--', alpha=0.5, label='额定扬程')
    axes[0].axvline(x=pump.rated_flow, color='r', linestyle='--', alpha=0.5, label='额定流量')
    axes[0].set_xlabel('流量 (m³/s)')
    axes[0].set_ylabel('扬程 (m)')
    axes[0].set_title('H-Q特性曲线')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # P-Q曲线
    axes[1].plot(flows, powers, 'g-', linewidth=2)
    axes[1].axhline(y=pump.rated_power, color='r', linestyle='--', alpha=0.5, label='额定功率')
    axes[1].set_xlabel('流量 (m³/s)')
    axes[1].set_ylabel('功率 (kW)')
    axes[1].set_title('P-Q功率曲线')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # η-Q曲线
    axes[2].plot(flows, np.array(efficiencies)*100, 'r-', linewidth=2)
    axes[2].axvline(x=pump.rated_flow, color='b', linestyle='--', alpha=0.5, label='额定工况点')
    axes[2].set_xlabel('流量 (m³/s)')
    axes[2].set_ylabel('效率 (%)')
    axes[2].set_title('η-Q效率曲线')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('example2_pump_characteristics.png', dpi=100, bbox_inches='tight')
    print("✓ 图表已保存: example2_pump_characteristics.png")

def example_3_complex_network_with_pumps():
    """示例3: 完整复杂水网（包含泵站分支）"""
    print("\n" + "="*60)
    print("示例3: 复杂水网系统 - 主线+泵站分支")
    print("="*60)

    # 主线组件
    reservoir = Reservoir("水库", 80000, 120000, 5000)
    inlet_gate = Gate("入口闸", 0, 15, width=6.0)
    canal1 = Canal("上游渠池", 6000, 12000, 400, 8000, method='preissmann')
    upstream_gate = Gate("上游闸", 0, 15, width=6.0)
    canal2 = Canal("中游渠池", 5000, 10000, 350, 7000, method='preissmann')
    midstream_gate = Gate("中游闸", 0, 15, width=6.0)
    settling_basin = SettlingBasin("稳流池", 3000, 8000, 200)
    middle_valve = Valve("中间阀", 0, 12, diameter=1.2)
    terminal_valve = Valve("末端阀", 0, 12, diameter=1.0)
    elevated_tank = StorageTank("高位水池", 1000, 5000, 150)

    # 泵站分支
    pump1 = Pump("一级泵站", 0, 8, 15, 35, rated_flow=5.0, rated_head=25.0, efficiency=0.78)
    canal_branch1 = Canal("分支渠道1", 2000, 5000, 150, 4000, method='preissmann')
    pump2 = Pump("二级泵站", 0, 6, 15, 30, rated_flow=4.0, rated_head=22.0, efficiency=0.75)
    canal_branch2 = Canal("分支渠道2", 1500, 4000, 120, 3000, method='preissmann')

    # 连接拓扑
    inlet_gate.add_upstream(reservoir)
    canal1.add_upstream(inlet_gate)
    upstream_gate.add_upstream(canal1)
    canal2.add_upstream(upstream_gate)
    midstream_gate.add_upstream(canal2)
    settling_basin.add_upstream(midstream_gate)

    middle_valve.add_upstream(settling_basin)
    terminal_valve.add_upstream(middle_valve)
    elevated_tank.add_upstream(terminal_valve)

    pump1.add_upstream(settling_basin)
    canal_branch1.add_upstream(pump1)
    pump2.add_upstream(canal_branch1)
    canal_branch2.add_upstream(pump2)

    components = [
        reservoir, inlet_gate, canal1, upstream_gate, canal2,
        midstream_gate, settling_basin, middle_valve, terminal_valve,
        elevated_tank, pump1, canal_branch1, pump2, canal_branch2
    ]

    # 简单PID控制
    pid = PIDController(0.5, 0.1, 0.05, (0, 15))

    # 降阶模式仿真（快速）
    engine = SimulationEngine(components, pid, dt=60, mode='reduced')
    history = engine.run(3600 * 8)  # 8小时

    # 可视化
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
    time = np.array(history['time']) / 3600

    # 1. 主线蓄水单元
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(time, [s['volume'] for s in history['states']['水库']], 'b-', linewidth=2, label='水库')
    ax1.plot(time, [s['volume'] for s in history['states']['高位水池']], 'r-', linewidth=2, label='高位水池')
    ax1.set_ylabel('蓄水量 (m³)')
    ax1.set_title('主线蓄水单元')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 明渠渠池
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(time, [s['volume'] for s in history['states']['上游渠池']], label='上游')
    ax2.plot(time, [s['volume'] for s in history['states']['中游渠池']], label='中游')
    ax2.set_ylabel('蓄水量 (m³)')
    ax2.set_title('明渠渠池')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 稳流池
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(time, [s['volume'] for s in history['states']['稳流池']], 'g-', linewidth=2)
    ax3.set_ylabel('蓄水量 (m³)')
    ax3.set_title('稳流池')
    ax3.grid(True, alpha=0.3)

    # 4. 闸门流量
    ax4 = fig.add_subplot(gs[1, 0])
    if '入口闸' in history['controls']:
        ax4.plot(time, history['controls']['入口闸'], label='入口闸')
    if '上游闸' in history['controls']:
        ax4.plot(time, history['controls']['上游闸'], label='上游闸')
    if '中游闸' in history['controls']:
        ax4.plot(time, history['controls']['中游闸'], label='中游闸')
    ax4.set_ylabel('流量 (m³/s)')
    ax4.set_title('闸门流量')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. 阀门流量
    ax5 = fig.add_subplot(gs[1, 1])
    if '中间阀' in history['controls']:
        ax5.plot(time, history['controls']['中间阀'], 'g-', label='中间阀')
    if '末端阀' in history['controls']:
        ax5.plot(time, history['controls']['末端阀'], 'm-', label='末端阀')
    ax5.set_ylabel('流量 (m³/s)')
    ax5.set_title('阀门流量')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. 泵站流量
    ax6 = fig.add_subplot(gs[1, 2])
    if '一级泵站' in history['controls']:
        ax6.plot(time, history['controls']['一级泵站'], 'b-', linewidth=2, label='一级泵站')
    if '二级泵站' in history['controls']:
        ax6.plot(time, history['controls']['二级泵站'], 'r-', linewidth=2, label='二级泵站')
    ax6.set_ylabel('流量 (m³/s)')
    ax6.set_title('泵站流量')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # 7. 泵站扬程
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.plot(time, [s['head'] for s in history['states']['一级泵站']], 'b-', label='一级')
    ax7.plot(time, [s['head'] for s in history['states']['二级泵站']], 'r-', label='二级')
    ax7.set_ylabel('扬程 (m)')
    ax7.set_title('泵站扬程')
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # 8. 泵站功率
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.plot(time, [s['power'] for s in history['states']['一级泵站']], 'b-', label='一级')
    ax8.plot(time, [s['power'] for s in history['states']['二级泵站']], 'r-', label='二级')
    ax8.set_ylabel('功率 (kW)')
    ax8.set_title('泵站功率')
    ax8.legend()
    ax8.grid(True, alpha=0.3)

    # 9. 泵站效率
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.plot(time, [s['efficiency']*100 for s in history['states']['一级泵站']], 'b-', label='一级')
    ax9.plot(time, [s['efficiency']*100 for s in history['states']['二级泵站']], 'r-', label='二级')
    ax9.set_ylabel('效率 (%)')
    ax9.set_title('泵站效率')
    ax9.legend()
    ax9.grid(True, alpha=0.3)

    # 10. 分支渠道
    ax10 = fig.add_subplot(gs[3, 0])
    ax10.plot(time, [s['volume'] for s in history['states']['分支渠道1']], label='分支1')
    ax10.plot(time, [s['volume'] for s in history['states']['分支渠道2']], label='分支2')
    ax10.set_xlabel('时间 (小时)')
    ax10.set_ylabel('蓄水量 (m³)')
    ax10.set_title('分支渠道')
    ax10.legend()
    ax10.grid(True, alpha=0.3)

    # 11. 系统能耗
    ax11 = fig.add_subplot(gs[3, 1])
    total_power = np.array([s['power'] for s in history['states']['一级泵站']]) + \
                  np.array([s['power'] for s in history['states']['二级泵站']])
    cumulative_energy = np.cumsum(total_power) * (1/60)  # kWh
    ax11.plot(time, cumulative_energy, 'r-', linewidth=2)
    ax11.set_xlabel('时间 (小时)')
    ax11.set_ylabel('累计能耗 (kWh)')
    ax11.set_title(f'系统总能耗: {cumulative_energy[-1]:.1f} kWh')
    ax11.grid(True, alpha=0.3)

    # 12. 系统拓扑
    ax12 = fig.add_subplot(gs[3, 2])
    ax12.text(0.5, 0.95, '系统拓扑结构', ha='center', fontsize=12, fontweight='bold')
    ax12.text(0.05, 0.80, '主线:', fontsize=10, fontweight='bold')
    ax12.text(0.05, 0.70, '  水库→闸→渠→闸→渠→闸→稳流池', fontsize=8)
    ax12.text(0.05, 0.60, '  稳流池→阀→阀→高位水池', fontsize=8)
    ax12.text(0.05, 0.45, '分支:', fontsize=10, fontweight='bold')
    ax12.text(0.05, 0.35, '  稳流池→泵→渠→泵→渠', fontsize=8)
    ax12.text(0.05, 0.20, f'组件总数: {len(components)}', fontsize=9)
    ax12.text(0.05, 0.10, f'仿真时长: {time[-1]:.1f} 小时', fontsize=9)
    ax12.set_xlim(0, 1)
    ax12.set_ylim(0, 1)
    ax12.axis('off')

    plt.savefig('example3_complex_network.png', dpi=100, bbox_inches='tight')
    print("✓ 图表已保存: example3_complex_network.png")

    # 统计信息
    print("\n" + "="*60)
    print("仿真统计")
    print("="*60)
    print(f"总能耗: {cumulative_energy[-1]:.1f} kWh")
    print(f"平均功率: {np.mean(total_power):.1f} kW")
    print(f"一级泵站平均效率: {np.mean([s['efficiency'] for s in history['states']['一级泵站']]):.2%}")
    print(f"二级泵站平均效率: {np.mean([s['efficiency'] for s in history['states']['二级泵站']]):.2%}")
    print("="*60)
