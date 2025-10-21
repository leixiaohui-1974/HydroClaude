from typing import Callable, Dict, List, Optional

from core.base import HydraulicComponent
from simulation.plant_simulator import PlantSimulator


class SILTestPlatform:
    """软件在环测试平台"""

    def __init__(self, plant_mode: str = 'high_fidelity'):
        self.plant_simulator: Optional[PlantSimulator] = None
        self.plant_mode = plant_mode

        self.history = {
            'time': [],
            'plant_states': [],
            'controls': []
        }

    def setup(self, components: List[HydraulicComponent]):
        """设置系统"""
        self.plant_simulator = PlantSimulator(components, mode=self.plant_mode)

    def run_test(self, duration: float, dt: float,
                control_func: Callable) -> Dict:
        """运行测试"""
        n_steps = int(duration / dt)

        print(f"\n{'='*60}")
        print(f"SIL测试 - 本体模式: {self.plant_mode}")
        print(f"时长: {duration}s, 步长: {dt}s")
        print(f"{'='*60}\n")

        for step in range(n_steps):
            time = step * dt
            self.history['time'].append(time)

            # 控制
            controls = control_func(time)

            # 本体仿真
            states = self.plant_simulator.step(dt, controls)

            self.history['plant_states'].append(states)
            self.history['controls'].append(controls)

            if step % max(1, n_steps // 20) == 0:
                print(f"进度: {100*step/n_steps:.0f}%")

        print("\n测试完成!\n")
        return self.history

    def switch_plant_mode(self, new_mode: str):
        """切换本体仿真模式"""
        if self.plant_simulator:
            self.plant_simulator.switch_mode(new_mode)
            self.plant_mode = new_mode
