import numpy as np
from typing import List, Dict, Optional
from core.component import HydraulicComponent
from core.control_device import ControlDevice
from core.water_body import WaterBody, Canal
from core.other_components import Pipe
from control.controller import Controller

class SimulationEngine:
    """仿真引擎 - 支持高保真和降阶模式"""

    def __init__(self, components: List[HydraulicComponent],
                 controller: Optional[Controller] = None,
                 dt: float = 60.0,
                 mode: str = 'reduced'):
        self.components = components
        self.controller = controller
        self.dt = dt
        self.mode = mode  # 'high_fidelity' or 'reduced'
        self.time = 0.0

        self.history = {
            'time': [],
            'states': {comp.name: [] for comp in components},
            'controls': {comp.name: [] for comp in components if isinstance(comp, ControlDevice)},
        }

    def run(self, duration: float, disturbances: Optional[Dict] = None):
        """运行仿真"""
        n_steps = int(duration / self.dt)

        print(f"\n{'='*60}")
        print(f"仿真模式: {'高保真' if self.mode == 'high_fidelity' else '降阶'}")
        print(f"时长={duration}s, 步长={self.dt}s, 总步数={n_steps}")
        print(f"组件数={len(self.components)}")
        print(f"{'='*60}\n")

        for step in range(n_steps):
            self.time = step * self.dt

            # 记录状态
            self.history['time'].append(self.time)
            for comp in self.components:
                self.history['states'][comp.name].append(comp.state.to_dict())

            # 控制计算
            if self.controller is not None:
                state = self._get_state_vector()
                reference = self._get_reference_vector()
                controls = self.controller.compute(state, reference, self.dt)
            else:
                controls = np.zeros(len(self.components))

            # 更新组件
            for i, comp in enumerate(self.components):
                inputs = self._prepare_inputs(comp, controls, disturbances)

                if self.mode == 'high_fidelity':
                    if isinstance(comp, Canal):
                        comp.update_state_high_fidelity(self.dt, inputs)
                    elif isinstance(comp, Pipe):
                        comp.update_state_high_fidelity(self.dt, inputs)
                    else:
                        comp.update_state(self.dt, inputs)
                else:
                    comp.update_state(self.dt, inputs)

                if isinstance(comp, ControlDevice):
                    self.history['controls'][comp.name].append(comp.state.flow)

            # 进度
            if step % max(1, n_steps // 20) == 0:
                print(f"进度: {100*step/n_steps:.0f}%")

        print("\n仿真完成!\n")
        return self.history

    def _get_state_vector(self) -> np.ndarray:
        states = []
        for comp in self.components:
            if isinstance(comp, WaterBody):
                states.append(comp.state.volume)
            elif isinstance(comp, ControlDevice):
                states.append(comp.state.flow)
        return np.array(states)

    def _get_reference_vector(self) -> np.ndarray:
        refs = []
        for comp in self.components:
            if isinstance(comp, WaterBody):
                refs.append((comp.volume_min + comp.volume_max) / 2)
            elif isinstance(comp, ControlDevice):
                refs.append((comp.flow_min + comp.flow_max) / 2)
        return np.array(refs)

    def _prepare_inputs(self, comp: HydraulicComponent,
                       controls: np.ndarray,
                       disturbances: Optional[Dict]) -> Dict[str, float]:
        inputs = {'time': self.time / 3600}

        if comp.upstream_components:
            inputs['inflow'] = sum(up.state.flow for up in comp.upstream_components)
            if comp.upstream_components:
                inputs['upstream_level'] = getattr(comp.upstream_components[0].state, 'level', 5.0)
                inputs['upstream_pressure'] = getattr(comp.upstream_components[0].state, 'pressure', 40.0)

        if comp.downstream_components:
            inputs['outflow'] = sum(down.state.flow for down in comp.downstream_components)
            if comp.downstream_components:
                inputs['downstream_level'] = getattr(comp.downstream_components[0].state, 'level', 4.0)

        idx = self.components.index(comp)
        if idx < len(controls):
            inputs['target_flow'] = controls[idx]
            inputs['target_head'] = 30.0

        if disturbances and comp.name in disturbances:
            inputs['disturbance'] = disturbances[comp.name](self.time)

        return inputs
