import numpy as np

from core.base import HydraulicComponent
from core.boundary_conditions import GateBoundary
from core.enums import ComponentType
from core.states import ComponentState


class Gate(HydraulicComponent):
    """闸门 - 作为边界条件"""

    def __init__(self, name: str, width: float = 5.0,
                 opening: float = 2.0, Cd: float = 0.6):
        super().__init__(name, ComponentType.GATE)
        self.width = width
        self.state.opening = opening
        self.Cd = Cd

        # 创建边界条件对象
        self.boundary_condition = GateBoundary(width, Cd, opening)

    def update_high_fidelity(self, dt: float, mode: str = 'implicit') -> ComponentState:
        """高保真：边界条件已在连接的组件中处理"""
        # 更新边界条件参数
        self.boundary_condition.opening = self.state.opening
        return self.state

    def update_reduced_order(self, dt: float) -> ComponentState:
        """降阶模型"""
        return self.state

    def set_opening(self, opening: float):
        """设置开度"""
        self.state.opening = np.clip(opening, 0, 5.0)
