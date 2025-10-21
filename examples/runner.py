import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

from physics.canal import Canal
from core.water_body import Reservoir, SettlingBasin, StorageTank
from core.control_device import Gate, Valve, Pump
from core.other_components import Pipe, DistributionPoint
from control.controller import PIDController
from simulation.plant_simulator import PlantSimulator
from validation.validator import ModelValidator
from core.control_device import ControlDevice

def example_1_simple_canal():
    """示例1: 简单明渠 + 模型对比"""
    print("\n" + "="*60)
    print("示例1: 简单明渠系统 - 高保真vs降阶模型对比")
    print("="*60)

    # 降阶模式
    canal_r = Canal("渠池1", 5000, 10000, 300, 5000)
    gate_r = Gate("闸门1", 0, 10, width=5.0)
    gate_r.set_upstream(canal_r)

    engine_reduced = PlantSimulator([canal_r, gate_r], mode='reduced')

    history_reduced = {'time': [], 'states': {'渠池1': [], '闸门1': []}, 'controls': {'闸门1': []}}
    for _ in range(120):
        states = engine_reduced.step(60)
        history_reduced['time'].append(engine_reduced.time)
        history_reduced['states']['渠池1'].append(states['渠池1'].to_dict())
        history_reduced['states']['闸门1'].append(states['闸门1'].to_dict())
        history_reduced['controls']['闸门1'].append(states['闸门1'].flow)

    # 高保真模式
    canal_h = Canal("渠池2", 5000, 10000, 300, 5000)
    gate_h = Gate("闸门2", 0, 10, width=5.0)
    gate_h.set_upstream(canal_h)

    engine_high = PlantSimulator([canal_h, gate_h], mode='high_fidelity')

    history_high = {'time': [], 'states': {'渠池2': [], '闸门2': []}, 'controls': {'闸门2': []}}
    for _ in range(120):
        states = engine_high.step(60)
        history_high['time'].append(engine_high.time)
        history_high['states']['渠池2'].append(states['渠池2'].to_dict())
        history_high['states']['闸门2'].append(states['闸门2'].to_dict())
        history_high['controls']['闸门2'].append(states['闸门2'].flow)

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
        pump.update_reduced_order(1.0, {'target_flow': Q})
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
    canal1 = Canal("上游渠池", 6000, 12000, 400, 8000)
    upstream_gate = Gate("上游闸", 0, 15, width=6.0)
    canal2 = Canal("中游渠池", 5000, 10000, 350, 7000)
    midstream_gate = Gate("中游闸", 0, 15, width=6.0)
    settling_basin = SettlingBasin("稳流池", 3000, 8000, 200)
    middle_valve = Valve("中间阀", 0, 12, diameter=1.2)
    terminal_valve = Valve("末端阀", 0, 12, diameter=1.0)
    elevated_tank = StorageTank("高位水池", 1000, 5000, 150)

    # 泵站分支
    pump1 = Pump("一级泵站", 0, 8, 15, 35, rated_flow=5.0, rated_head=25.0, efficiency=0.78)
    canal_branch1 = Canal("分支渠道1", 2000, 5000, 150, 4000)
    pump2 = Pump("二级泵站", 0, 6, 15, 30, rated_flow=4.0, rated_head=22.0, efficiency=0.75)
    canal_branch2 = Canal("分支渠道2", 1500, 4000, 120, 3000)

    # 连接拓扑
    inlet_gate.set_upstream(reservoir)
    canal1.set_upstream(inlet_gate)
    upstream_gate.set_upstream(canal1)
    canal2.set_upstream(upstream_gate)
    midstream_gate.set_upstream(canal2)
    settling_basin.set_upstream(midstream_gate)

    middle_valve.set_upstream(settling_basin)
    terminal_valve.set_upstream(middle_valve)
    elevated_tank.set_upstream(terminal_valve)

    pump1.set_upstream(settling_basin)
    canal_branch1.set_upstream(pump1)
    pump2.set_upstream(canal_branch1)
    canal_branch2.set_upstream(pump2)

    components = [
        reservoir, inlet_gate, canal1, upstream_gate, canal2,
        midstream_gate, settling_basin, middle_valve, terminal_valve,
        elevated_tank, pump1, canal_branch1, pump2, canal_branch2
    ]

    # 降阶模式仿真（快速）
    engine = PlantSimulator(components, mode='reduced')

    history = {
        'time': [],
        'states': {comp.name: [] for comp in components},
        'controls': {comp.name: [] for comp in components if isinstance(comp, ControlDevice)},
    }
    for _ in range(480):
        states = engine.step(60)
        history['time'].append(engine.time)
        for name, state in states.items():
            history['states'][name].append(state.to_dict())
            comp = engine.components[name]
            if isinstance(comp, ControlDevice):
                history['controls'][name].append(state.flow)

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
    ax4.plot(time, [s['flow'] for s in history['states']['入口闸']], label='入口闸')
    ax4.plot(time, [s['flow'] for s in history['states']['上游闸']], label='上游闸')
    ax4.plot(time, [s['flow'] for s in history['states']['中游闸']], label='中游闸')
    ax4.set_ylabel('流量 (m³/s)')
    ax4.set_title('闸门流量')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. 阀门流量
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(time, [s['flow'] for s in history['states']['中间阀']], 'g-', label='中间阀')
    ax5.plot(time, [s['flow'] for s in history['states']['末端阀']], 'm-', label='末端阀')
    ax5.set_ylabel('流量 (m³/s)')
    ax5.set_title('阀门流量')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. 泵站流量
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.plot(time, [s['flow'] for s in history['states']['一级泵站']], 'b-', linewidth=2, label='一级泵站')
    ax6.plot(time, [s['flow'] for s in history['states']['二级泵站']], 'r-', linewidth=2, label='二级泵站')
    ax6.set_ylabel('流量 (m³/s)')
    ax6.set_title('泵站流量')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('example3_complex_network.png', dpi=100, bbox_inches='tight')
    print("✓ 图表已保存: example3_complex_network.png")

def run_framework_example():
    """Runs all framework examples."""
    example_1_simple_canal()
    example_2_pump_characteristics()
    example_3_complex_network_with_pumps()
