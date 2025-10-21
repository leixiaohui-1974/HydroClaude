from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
import numpy as np

class HydraulicComponent(ABC):
    """水力组件抽象基类"""

    def __init__(self, name: str, comp_type: str):
        self.name = name
        self.type = comp_type
        self.parameters = {}

        # 拓扑连接
        self.upstream_component: Optional['HydraulicComponent'] = None
        self.downstream_component: Optional['HydraulicComponent'] = None
        self.upstream_boundary = None
        self.downstream_boundary = None

    @abstractmethod
    def update_high_fidelity(self, dt: float, inputs: Dict) -> 'ComponentState':
        """高保真更新"""
        pass

    @abstractmethod
    def update_reduced_order(self, dt: float, inputs: Dict) -> 'ComponentState':
        """降阶模型更新"""
        pass

    @abstractmethod
    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        """获取约束"""
        pass

    def set_upstream(self, component: 'HydraulicComponent', boundary=None):
        """设置上游组件"""
        self.upstream_component = component
        self.upstream_boundary = boundary

    def set_downstream(self, component: 'HydraulicComponent', boundary=None):
        """设置下游组件"""
        self.downstream_component = component
        self.downstream_boundary = boundary
