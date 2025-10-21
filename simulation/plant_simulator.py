from typing import List, Dict
from core.base import HydraulicComponent
from core.states import ComponentState

class PlantSimulator:
    """本体仿真器 - 支持双模式"""

    def __init__(self, components: List[HydraulicComponent],
                 mode: str = 'high_fidelity'):
        """
        Args:
            components: 组件列表
            mode: 'high_fidelity' 或 'reduced'
        """
        self.components = {comp.name: comp for comp in components}
        self.mode = mode
        self.time = 0.0

        # 验证所有组件都有必需的方法
        for comp in components:
            if not hasattr(comp, 'update_high_fidelity'):
                raise AttributeError(f"组件 '{comp.name}' 缺少 'update_high_fidelity' 方法")
            if not hasattr(comp, 'update_reduced_order'):
                raise AttributeError(f"组件 '{comp.name}' 缺少 'update_reduced_order' 方法")

        print(f"✓ 本体仿真器初始化: 模式={mode}, 组件数={len(components)}")

    def step(self, dt: float, control_inputs: Dict = None) -> Dict[str, ComponentState]:
        """
        单步仿真

        Args:
            dt: 时间步长
            control_inputs: 控制输入字典 {component_name: control_value}

        Returns:
            各组件的状态字典
        """
        control_inputs = control_inputs or {}
        states = {}

        # 准备输入
        inputs_dict = self._prepare_inputs(control_inputs)

        # 更新所有组件
        for name, comp in self.components.items():
            comp_inputs = inputs_dict.get(name, {})

            try:
                if self.mode == 'high_fidelity':
                    state = comp.update_high_fidelity(dt, comp_inputs)
                else:
                    state = comp.update_reduced_order(dt, comp_inputs)

                states[name] = state

            except AttributeError as e:
                print(f"错误: 组件 '{name}' (类型: {type(comp).__name__}) 方法调用失败")
                print(f"  模式: {self.mode}")
                print(f"  错误信息: {e}")
                print(f"  可用方法: {[m for m in dir(comp) if not m.startswith('_')]}")
                raise
            except Exception as e:
                print(f"警告: 组件 '{name}' 更新失败: {e}")
                # 使用旧状态
                states[name] = comp.state

        self.time += dt
        return states

    def _prepare_inputs(self, control_inputs: Dict) -> Dict[str, Dict]:
        """准备每个组件的输入"""
        inputs = {}

        for name, comp in self.components.items():
            comp_inputs = {
                'time': self.time,
                'control': control_inputs.get(name, 0),
            }

            # 从拓扑获取上下游流量
            if comp.upstream_component:
                comp_inputs['inflow'] = comp.upstream_component.state.flow
            else:
                comp_inputs['inflow'] = 5.0  # 默认值

            if comp.downstream_component:
                comp_inputs['outflow'] = comp.downstream_component.state.flow
            else:
                comp_inputs['outflow'] = 4.0  # 默认值

            comp_inputs['disturbance'] = 0.0  # 默认无扰动

            inputs[name] = comp_inputs

        return inputs

    def switch_mode(self, new_mode: str):
        """切换仿真模式"""
        if new_mode in ['high_fidelity', 'reduced']:
            old_mode = self.mode
            self.mode = new_mode
            print(f"✓ 模式切换: {old_mode} → {new_mode}")
        else:
            print(f"✗ 无效模式: {new_mode}")
