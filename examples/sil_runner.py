import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

from physics.canal import Canal
from core.water_body import Reservoir, SettlingBasin, StorageTank
from core.control_device import Gate, Valve, Pump
from core.other_components import Pipe, DistributionPoint
from simulation.plant_simulator import PlantSimulator
from sil_platform.platform import SILTestPlatform
from sensor.simulator import SensorConfig, SensorFault
from actuator.simulator import ActuatorConfig, ActuatorFault
from disturbance.generator import DisturbanceConfig, DisturbanceType

def example_sil_basic_test():
    """基础SIL测试"""
    print("\n" + "="*60)
    print("示例: 基础软件在环测试")
    print("="*60)

    # 创建平台
    platform = SILTestPlatform(plant_mode='high_fidelity')

    # 添加组件
    canal1 = Canal("渠池1", 5000, 10000, 300, 5000)
    pump1 = Pump("泵站1", 0, 8, 15, 35)
    tank1 = StorageTank("水池1", 1000, 5000, 150)

    platform.add_component(canal1)
    platform.add_component(pump1)
    platform.add_component(tank1)

    # 添加传感器
    platform.add_sensor("渠池1", SensorConfig("水位计1", "level", noise_std=0.02))
    platform.add_sensor("泵站1", SensorConfig("流量计1", "flow", noise_std=0.05))

    # 添加执行器
    platform.add_actuator("泵站1", ActuatorConfig("泵站执行器", "pump",
                                                  response_time=2.0, max_rate=0.5))

    # 添加扰动
    platform.add_disturbance("渠池1", DisturbanceConfig(
        "用水扰动1", DisturbanceType.SINE, base_value=0.5,
        amplitude=0.3, frequency=0.01
    ))

    # 简单控制器
    def simple_controller(twin_states, measurements, time):
        controls = {}
        # 简单比例控制
        if "泵站1" in twin_states:
            target = 5.0
            current = twin_states["泵站1"].flow
            controls["泵站1"] = target + 0.5 * (target - current)
        return controls

    # 运行测试
    history = platform.run_test(duration=3600, dt=60,
                                control_func=simple_controller,
                                enable_identification=True)

    # 可视化
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    time = np.array(history['time']) / 3600

    # 1. 本体vs孪生状态
    ax = axes[0, 0]
    plant_volumes = [s["渠池1"].volume for s in history['plant_states']]
    twin_volumes = [s["渠池1"].volume for s in history['twin_states']]
    ax.plot(time, plant_volumes, 'b-', linewidth=2, label='本体')
    ax.plot(time, twin_volumes, 'r--', linewidth=2, label='孪生')
    ax.set_ylabel('蓄水量 (m³)')
    ax.set_title('本体 vs 孪生')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. 测量值
    ax = axes[0, 1]
    measurements = [m.get("渠池1", np.nan) for m in history['measurements']]
    ax.plot(time, measurements, 'g.', markersize=3, label='测量值')
    ax.plot(time, [s['渠池1'].volume for s in history['plant_states']], 'b-', alpha=0.5, label='真值')
    ax.set_ylabel('水位 (m)')
    ax.set_title('传感器测量')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('sil_basic_test.png', dpi=100, bbox_inches='tight')
    print("✓ 图表已保存: sil_basic_test.png")

def example_sil_fault_test():
    """故障测试"""
    print("\n" + "="*60)
    print("示例: 传感器和执行器故障测试")
    print("="*60)

    platform = SILTestPlatform(plant_mode='reduced')

    # 组件
    canal1 = Canal("渠池1", 5000, 10000, 300, 5000)
    gate1 = Gate("闸门1", 0, 10)

    platform.add_component(canal1)
    platform.add_component(gate1)

    # 传感器
    platform.add_sensor("渠池1", SensorConfig("水位计", "level", noise_std=0.01))

    # 执行器
    platform.add_actuator("闸门1", ActuatorConfig("闸门执行器", "gate",
                                                  response_time=1.0, max_rate=1.0))

    # 控制器
    def fault_tolerant_controller(twin_states, measurements, time):
        controls = {}
        target = 6.0

        # 容错逻辑
        if "渠池1" in measurements:
            error = 7.0 - measurements["渠池1"]  # 目标水位7m
            controls["闸门1"] = target + 0.3 * error
        else:
            # 传感器失效时使用孪生状态
            if "渠池1" in twin_states:
                error = 7.0 - twin_states["渠池1"].level
                controls["闸门1"] = target + 0.3 * error

        return controls

    # 运行测试
    history = platform.run_test(duration=1800, dt=30,
                                control_func=fault_tolerant_controller)

    # 注入故障
    time_points = np.array(history['time'])

    # 600秒时传感器漂移
    if len(time_points) > 20:
        platform.inject_sensor_fault("渠池1", SensorFault.DRIFT,
                                    {'drift_rate': 0.01})

    # 1200秒时执行器响应变慢
    if len(time_points) > 40:
        platform.inject_actuator_fault("闸门1", ActuatorFault.SLOW_RESPONSE,
                                      {'slowdown_factor': 5})

    # 继续运行
    history2 = platform.run_test(duration=1800, dt=30,
                                 control_func=fault_tolerant_controller)

    print("✓ 故障测试完成")
