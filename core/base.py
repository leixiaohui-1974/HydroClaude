from abc import ABC, abstractmethod
from typing import Optional

from core.boundary_conditions import BoundaryCondition
from core.enums import ComponentType
from core.states import ComponentState, HydraulicState


class HydraulicComponent(ABC):
    """水力组件基类"""

    def __init__(self, name: str, comp_type: ComponentType):
        self.name = name
        self.type = comp_type
        self.state = ComponentState()
        self.hydraulic_state = HydraulicState()
        self.parameters = {}

        # 拓扑连接
        self.upstream_component: Optional['HydraulicComponent'] = None
        self.downstream_component: Optional['HydraulicComponent'] = None
        self.upstream_boundary: Optional[BoundaryCondition] = None
        self.downstream_boundary: Optional[BoundaryCondition] = None

    @abstractmethod
    def update_high_fidelity(self, dt: float, mode: str = 'implicit') -> ComponentState:
        """高保真更新（求解PDE）"""
        pass

    @abstractmethod
    def update_reduced_order(self, dt: float) -> ComponentState:
        """降阶模型更新"""
        pass

    def set_upstream(self, component: 'HydraulicComponent',
                    boundary: Optional[BoundaryCondition] = None):
        """设置上游组件和边界条件"""
        self.upstream_component = component
        self.upstream_boundary = boundary

    def set_downstream(self, component: 'HydraulicComponent',
                      boundary: Optional[BoundaryCondition] = None):
        """设置下游组件和边界条件"""
        self.downstream_component = component
        self.downstream_boundary = boundary
