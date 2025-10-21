from typing import List, Dict
from core.base import HydraulicComponent
from core.states import ComponentState

class PlantSimulator:
    """本体仿真器 - 支持双模式"""

    def __init__(self, components: List[HydraulicComponent],
                 mode: str = 'high_fidelity'):
        self.components = {comp.name: comp for comp in components}
        self.mode = mode  # 'high_fidelity' or 'reduced'
        self.time = 0.0
        self._build_topology()

        print(f"本体仿真器初始化: 模式={mode}, 组件数={len(components)}")

    def _build_topology(self):
        """自动建立拓扑连接"""
        # 简化实现：假设组件按顺序连接
        comp_list = list(self.components.values())
        for i in range(len(comp_list) - 1):
            current = comp_list[i]
            next_comp = comp_list[i + 1]
            current.set_downstream(next_comp)
            next_comp.set_upstream(current)

    def step(self, dt: float, control_inputs: Dict = None) -> Dict[str, ComponentState]:
        """单步仿真"""
        control_inputs = control_inputs or {}
        states = {}

        inputs = self._prepare_inputs(control_inputs)

        for name, comp in self.components.items():
            comp_inputs = inputs.get(name, {})

            if self.mode == 'high_fidelity':
                state = comp.update_high_fidelity(dt, comp_inputs)
            else:
                state = comp.update_reduced_order(dt, comp_inputs)

            states[name] = state

        self.time += dt
        return states

    def _prepare_inputs(self, control_inputs: Dict) -> Dict:
        """准备输入"""
        inputs = {}
        for name, comp in self.components.items():
            inflow = 5.0  # Default for first component
            if comp.upstream_component:
                inflow = comp.upstream_component.state.flow

            inputs[name] = {
                'inflow': inflow,
                'outflow': 4.0, # This is still hardcoded, but better
                'control': control_inputs.get(name, 0)
            }
        return inputs

    def switch_mode(self, new_mode: str):
        """切换模式"""
        if new_mode in ['high_fidelity', 'reduced']:
            self.mode = new_mode
            print(f"模式切换为: {new_mode}")
