from typing import List, Dict, Optional, Callable
import numpy as np
from core.base import HydraulicComponent
import numpy as np
from identification.twin import DigitalTwin, OnlineIdentification, OfflineIdentification
from sensor.simulator import SensorSimulator, SensorConfig, SensorFault
from actuator.simulator import ActuatorSimulator, ActuatorConfig, ActuatorFault
from disturbance.generator import DisturbanceGenerator, DisturbanceConfig
from evaluation.evaluator import PerformanceEvaluator

class SILTestPlatform:
    """软件在环测试平台"""

    def __init__(self, plant_mode: str = 'high_fidelity'):
        self.plant_mode = plant_mode  # 'high_fidelity' or 'reduced'

        # 本体仿真
        self.plant_components: Dict[str, HydraulicComponent] = {}

        # 数字孪生
        self.twin_components: Dict[str, HydraulicComponent] = {}
        self.digital_twin: Optional[DigitalTwin] = None

        # 传感器层
        self.sensors: Dict[str, SensorSimulator] = {}

        # 执行器层
        self.actuators: Dict[str, ActuatorSimulator] = {}

        # 扰动生成器
        self.disturbance_generators: Dict[str, DisturbanceGenerator] = {}

        # 辨识器
        self.online_identifiers: Dict[str, OnlineIdentification] = {}
        self.offline_identifier = OfflineIdentification()

        # 评价器
        self.evaluator = PerformanceEvaluator()

        # 历史记录
        self.history = {
            'time': [],
            'plant_states': [],
            'twin_states': [],
            'measurements': [],
            'controls': [],
            'disturbances': [],
            'faults': []
        }

    def add_component(self, component: HydraulicComponent):
        """添加组件（同时创建本体和孪生）"""
        # 本体
        self.plant_components[component.name] = component

        # 孪生（深拷贝）
        import copy
        twin_comp = copy.deepcopy(component)
        self.twin_components[twin_comp.name] = twin_comp

    def add_sensor(self, component_name: str, config: SensorConfig):
        """添加传感器"""
        sensor = SensorSimulator(config)
        self.sensors[component_name] = sensor

    def add_actuator(self, component_name: str, config: ActuatorConfig):
        """添加执行器"""
        actuator = ActuatorSimulator(config)
        self.actuators[component_name] = actuator

    def add_disturbance(self, component_name: str, config: DisturbanceConfig):
        """添加扰动"""
        disturbance = DisturbanceGenerator(config)
        self.disturbance_generators[component_name] = disturbance

    def inject_sensor_fault(self, sensor_name: str,
                           fault_type: SensorFault,
                           fault_params: Dict = None):
        """注入传感器故障"""
        if sensor_name in self.sensors:
            sensor = self.sensors[sensor_name]
            sensor.config.fault_type = fault_type
            if fault_params:
                sensor.config.fault_params = fault_params

            self.history['faults'].append({
                'time': self.history['time'][-1] if self.history['time'] else 0,
                'type': 'sensor',
                'name': sensor_name,
                'fault': fault_type.value
            })

    def inject_actuator_fault(self, actuator_name: str,
                            fault_type: ActuatorFault,
                            fault_params: Dict = None):
        """注入执行器故障"""
        if actuator_name in self.actuators:
            actuator = self.actuators[actuator_name]
            actuator.config.fault_type = fault_type
            if fault_params:
                actuator.config.fault_params = fault_params

            self.history['faults'].append({
                'time': self.history['time'][-1] if self.history['time'] else 0,
                'type': 'actuator',
                'name': actuator_name,
                'fault': fault_type.value
            })

    def run_test(self, duration: float, dt: float,
                control_func: Callable,
                enable_identification: bool = True) -> Dict:
        """运行测试"""
        n_steps = int(duration / dt)

        # 初始化数字孪生
        self.digital_twin = DigitalTwin(list(self.twin_components.values()))

        # 初始化在线辨识器
        for name in self.plant_components.keys():
            self.online_identifiers[name] = OnlineIdentification(n_params=3)

        print(f"\n{'='*60}")
        print(f"软件在环测试")
        print(f"本体模式: {self.plant_mode}")
        print(f"时长: {duration}s, 步长: {dt}s")
        print(f"组件数: {len(self.plant_components)}")
        print(f"传感器数: {len(self.sensors)}")
        print(f"执行器数: {len(self.actuators)}")
        print(f"{'='*60}\n")

        for step in range(n_steps):
            time = step * dt
            self.history['time'].append(time)

            # ========== 1. 本体仿真 ==========
            plant_states = {}
            for name, comp in self.plant_components.items():
                # 获取执行器输出
                actuator_output = 0
                if name in self.actuators:
                    # 这里需要控制命令，稍后会有
                    actuator_output = self.actuators[name].current_value

                # 获取扰动
                disturbance = 0
                if name in self.disturbance_generators:
                    disturbance = self.disturbance_generators[name].generate(time)

                # 准备输入
                inputs = {
                    'target_flow': actuator_output,
                    'disturbance': disturbance,
                    'inflow': 5.0,  # 简化
                    'outflow': 4.0,
                    'upstream_level': 5.0
                }

                # 更新本体
                if self.plant_mode == 'high_fidelity':
                    state = comp.update_high_fidelity(dt, inputs)
                else:
                    state = comp.update_reduced_order(dt, inputs)

                plant_states[name] = state

            self.history['plant_states'].append(plant_states)

            # ========== 2. 传感器测量 ==========
            measurements = {}
            for name, sensor in self.sensors.items():
                if name in plant_states:
                    true_value = plant_states[name].volume
                    measured = sensor.measure(true_value, dt)
                    if measured is not None and not np.isnan(measured):
                        measurements[name] = measured

            self.history['measurements'].append(measurements)

            # ========== 3. 数字孪生更新 ==========
            twin_inputs = {}  # 简化
            twin_states = self.digital_twin.update(dt, twin_inputs)
            self.history['twin_states'].append(twin_states)

            # ========== 4. 在线辨识与同步 ==========
            if enable_identification and measurements:
                for name in measurements.keys():
                    if name in self.online_identifiers:
                        self.digital_twin.synchronize(
                            measurements,
                            self.online_identifiers[name],
                            name
                        )

            # ========== 5. 控制器计算 ==========
            # 基于孪生状态和测量值
            control_commands = control_func(twin_states, measurements, time)

            # ========== 6. 执行器执行 ==========
            actuator_outputs = {}
            for name, command in control_commands.items():
                if name in self.actuators:
                    output = self.actuators[name].execute(command, dt)
                    actuator_outputs[name] = output

            self.history['controls'].append(actuator_outputs)

            # 进度
            if step % max(1, n_steps // 20) == 0:
                print(f"进度: {100*step/n_steps:.0f}%")

        print("\n测试完成!\n")

        # ========== 性能评价 ==========
        metrics = self.evaluator.evaluate(
            self.history['plant_states'],
            self.history['twin_states'],
            self.history['controls'],
            list(self.disturbance_generators.values())
        )

        intelligence_level = metrics.compute_intelligence_level()

        print(f"{'='*60}")
        print(f"性能评价报告")
        print(f"{'='*60}")
        print(f"跟踪误差RMSE: {metrics.tracking_error_rmse:.4f}")
        print(f"约束违反次数: {metrics.constraint_violations}")
        print(f"总能耗: {metrics.total_energy:.2f} kWh")
        print(f"扰动抑制能力: {metrics.disturbance_rejection:.2%}")
        print(f"预测准确度: {metrics.prediction_accuracy:.2%}")
        print(f"\n智能化等级: {intelligence_level.name}")
        print(f"{'='*60}\n")

        return self.history
