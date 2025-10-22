from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
import numpy as np

class HydraulicComponent(ABC):
    """
    水力组件抽象基类

    支持灵活的参数命名，兼容 name/component_id 和 comp_type/component_type
    """

    def __init__(self, name: str = None, comp_type: str = None,
                 component_id: str = None, component_type: str = None, **kwargs):
        """
        初始化水力组件

        Args:
            name: 组件名称（推荐）
            comp_type: 组件类型（推荐）
            component_id: 组件ID（备选，与name等效）
            component_type: 组件类型（备选，与comp_type等效）
            **kwargs: 其他参数（被忽略，用于兼容性）
        """
        # 支持多种参数名称，向后兼容
        self.name = name or component_id
        self.id = component_id or name  # 添加id属性
        self.type = comp_type or component_type

        # 参数验证
        if self.name is None:
            raise ValueError("组件名称不能为空 (name 或 component_id)")
        if self.type is None:
            raise ValueError("组件类型不能为空 (comp_type 或 component_type)")

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
