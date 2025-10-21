from typing import Dict, List

from actuator.gate import Gate
from actuator.pump import Pump
from core.base import HydraulicComponent
from core.states import ComponentState


class PlantSimulator:
    """本体仿真器 - 支持高保真/降阶双模式"""

    def __init__(self, components: List[HydraulicComponent], mode: str = 'high_fidelity'):
        """
        Args:
            components: 组件列表
            mode: 'high_fidelity' 或 'reduced'
        """
        self.components = {comp.name: comp for comp in components}
        self.mode = mode
        self.time = 0.0

        # 自动建立拓扑连接
        self._build_topology()

        print(f"本体仿真器初始化完成")
        print(f"  模式: {mode}")
        print(f"  组件数: {len(components)}")

    def _build_topology(self):
        """自动建立拓扑连接"""
        # 简化实现：假设组件按顺序连接
        comp_list = list(self.components.values())

        for i in range(len(comp_list) - 1):
            current = comp_list[i]
            next_comp = comp_list[i + 1]

            # 如果下一个是控制设备，设置为边界条件
            if isinstance(next_comp, (Gate, Pump)):
                current.set_downstream(next_comp, next_comp.boundary_condition)
                next_comp.set_upstream(current)

                # 跳过控制设备，连接到其下游
                if i + 2 < len(comp_list):
                    next_next = comp_list[i + 2]
                    next_comp.set_downstream(next_next)
                    next_next.set_upstream(next_comp, next_comp.boundary_condition)
            else:
                current.set_downstream(next_comp)
                next_comp.set_upstream(current)

    def step(self, dt: float, control_inputs: Dict[str, float] = None) -> Dict[str, ComponentState]:
        """
        单步仿真
        Args:
            dt: 时间步长
            control_inputs: 控制输入 {component_name: value}
        Returns:
            各组件状态
        """
        control_inputs = control_inputs or {}
        states = {}

        # 应用控制输入
        for name, value in control_inputs.items():
            if name in self.components:
                comp = self.components[name]
                if isinstance(comp, Gate):
                    comp.set_opening(value)

        # 更新所有组件
        for name, comp in self.components.items():
            if self.mode == 'high_fidelity':
                state = comp.update_high_fidelity(dt)
            else:
                state = comp.update_reduced_order(dt)
            states[name] = state

        self.time += dt
        return states

    def switch_mode(self, new_mode: str):
        """切换仿真模式"""
        if new_mode in ['high_fidelity', 'reduced']:
            self.mode = new_mode
            print(f"本体仿真模式切换为: {new_mode}")
        else:
            print(f"无效模式: {new_mode}")
