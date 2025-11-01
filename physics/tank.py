from core.base import HydraulicComponent
from core.states import ComponentState

class Tank(HydraulicComponent):
    """
    水池/水库组件

    支持灵活的参数命名，兼容 name/tank_id
    """
    def __init__(self, name: str = None, volume_min: float = 0.0,
                 volume_max: float = 1000.0, area: float = 100.0,
                 # 额外参数支持（兼容性）
                 tank_id: str = None, **kwargs):
        """
        初始化水池组件

        Args:
            name: Tank name (or use tank_id)
            volume_min: Minimum volume (m³)
            volume_max: Maximum volume (m³)
            area: Surface area (m²)
            tank_id: Alternative parameter for name
            **kwargs: Other parameters for compatibility
        """
        # 参数兼容性处理
        actual_name = name or tank_id

        super().__init__(name=actual_name, comp_type="tank", **kwargs)
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area

        # 添加便捷属性（兼容性）
        self.tank_id = self.id  # 别名
        self.volume = (volume_min + volume_max) / 2  # 初始容积

        # Add level limits for convenience
        self.min_level = volume_min / area
        self.max_level = volume_max / area

        self.state = ComponentState()
        self.state.volume = self.volume
        self.state.level = self.state.volume / area

    def update(self, dt: float, inflow: float = 0.0, outflow: float = 0.0) -> ComponentState:
        """
        Simplified update method for convenience
        简化的更新方法，方便直接调用

        Args:
            dt: Time step (s)
            inflow: Inflow rate (m³/s)
            outflow: Outflow rate (m³/s)

        Returns:
            Updated component state
        """
        return self.update_reduced_order(dt, {'inflow': inflow, 'outflow': outflow})

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        return self.update_reduced_order(dt, inputs)

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        inflow = inputs.get('inflow', 0.0)
        outflow = inputs.get('outflow', 0.0)

        dV = (inflow - outflow) * dt
        self.state.volume = max(self.volume_min, min(self.volume_max, self.state.volume + dV))
        self.state.level = self.state.volume / self.area
        self.state.flow = outflow

        return self.state

    def get_constraints(self):
        return {
            'volume_min': self.volume_min,
            'volume_max': self.volume_max,
            'level_min': self.volume_min / self.area,
            'level_max': self.volume_max / self.area
        }
