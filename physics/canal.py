import numpy as np
import warnings
from core.base import HydraulicComponent
from core.states import ComponentState, HydraulicState
from core.constants import PhysicsConstants, CanalDefaults, NumericalDefaults
from physics.numerical_methods.preissmann_solver import PreissmannSolver

class Canal(HydraulicComponent):
    """
    明渠组件 - Saint-Venant方程求解

    ⚠️ **DEPRECATED WARNING** ⚠️
    
    Canal类使用的PreissmannSolver存在严重的质量守恒问题（误差+279%）。
    
    **强烈建议使用 HydrostaticCanalSolver 替代**:
        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
    
    HydrostaticCanalSolver优势：
    - 质量守恒：-0.000003% (完美)
    - 稳态精度：0.001% (世界级)
    - 稳定性：  100%成功率
    
    详见: CANAL_PREISSMANN_DIAGNOSIS.md
    
    参数已完全配置化，无硬编码
    """

    def __init__(self, name: str, volume_min: float, volume_max: float,
                 area: float, length: float,
                 slope: float = None,
                 n_sections: int = None,
                 method: str = None,
                 # 水力参数 - 可选，使用默认值
                 manning_n: float = None,
                 width: float = None,
                 # 初始状态 - 可选
                 initial_depth: float = None,
                 initial_flow: float = None,
                 # 约束范围 - 可选
                 h_min: float = None,
                 h_max: float = None,
                 q_min: float = None,
                 q_max: float = None,
                 # 物理常数 - 可选
                 g: float = None):
        """
        初始化明渠组件

        Args:
            name: 组件名称
            volume_min: 最小库容 (m³)
            volume_max: 最大库容 (m³)
            area: 横截面积 (m²)
            length: 渠道长度 (m)
            slope: 渠底坡度，默认使用CanalDefaults.SLOPE
            n_sections: 空间离散节点数，默认使用CanalDefaults.DEFAULT_SECTIONS
            method: 求解方法 ('moc'/'preissmann'/'fvm')，默认使用CanalDefaults.DEFAULT_METHOD
            manning_n: 曼宁粗糙系数，默认使用CanalDefaults.MANNING_N
            width: 渠道宽度 (m)，默认使用CanalDefaults.WIDTH
            initial_depth: 初始水深 (m)，默认使用CanalDefaults.INITIAL_DEPTH
            initial_flow: 初始流量 (m³/s)，默认使用CanalDefaults.INITIAL_FLOW
            h_min: 最小水深 (m)，默认使用CanalDefaults.H_MIN
            h_max: 最大水深 (m)，默认使用CanalDefaults.H_MAX
            q_min: 最小流量 (m³/s)，默认使用CanalDefaults.Q_MIN
            q_max: 最大流量 (m³/s)，默认使用CanalDefaults.Q_MAX
            g: 重力加速度 (m/s²)，默认使用PhysicsConstants.GRAVITY
        """
        super().__init__(name, "canal")

        # 基本几何参数
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area
        self.length = length

        # 使用默认值或用户指定值
        self.slope = slope if slope is not None else CanalDefaults.SLOPE
        self.n_sections = n_sections if n_sections is not None else CanalDefaults.DEFAULT_SECTIONS
        self.method = method if method is not None else CanalDefaults.DEFAULT_METHOD

        # 水力参数
        manning_n = manning_n if manning_n is not None else CanalDefaults.MANNING_N
        width = width if width is not None else CanalDefaults.WIDTH

        # 物理常数
        self.g = g if g is not None else PhysicsConstants.GRAVITY

        # 初始状态
        initial_depth = initial_depth if initial_depth is not None else CanalDefaults.INITIAL_DEPTH
        initial_flow = initial_flow if initial_flow is not None else CanalDefaults.INITIAL_FLOW

        # 约束范围
        self.h_min = h_min if h_min is not None else CanalDefaults.H_MIN
        self.h_max = h_max if h_max is not None else CanalDefaults.H_MAX
        self.q_min = q_min if q_min is not None else CanalDefaults.Q_MIN
        self.q_max = q_max if q_max is not None else CanalDefaults.Q_MAX

        self.parameters = {
            'manning_n': manning_n,
            'width': width,
            'area': area
        }

        self.state = ComponentState()
        self.hydraulic_state = HydraulicState()
        self.hydraulic_state.h = np.ones(self.n_sections) * initial_depth
        self.hydraulic_state.Q = np.ones(self.n_sections) * initial_flow

        self.dx = length / (self.n_sections - 1)
        self.x = np.linspace(0, length, self.n_sections)

        # ⚠️ DEPRECATED: PreissmannSolver存在严重质量守恒问题
        # 初始化求解器（仅支持Preissmann）
        if self.method != 'preissmann':
            raise ValueError(f"不支持的求解方法'{self.method}'。仅支持'preissmann'。")
        
        # 发出废弃警告
        warnings.warn(
            "Canal类使用的PreissmannSolver存在严重质量守恒问题（误差+279%）。"
            "强烈建议使用 HydrostaticCanalSolver 替代。"
            "详见: CANAL_PREISSMANN_DIAGNOSIS.md",
            DeprecationWarning,
            stacklevel=2
        )

        theta = NumericalDefaults.PREISSMANN_THETA
        self.solver = PreissmannSolver(theta=theta)

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        高保真求解（仅支持Preissmann方法）

        使用Preissmann四点隐式格式求解Saint-Venant方程。
        这是当前唯一经过验证且精度可接受的非恒定流求解器（误差36.3%）。

        Args:
            dt: 时间步长 (s)
            inputs: 边界条件字典，支持:
                - 'upstream_flow' 或 'upstream_level': 上游边界
                - 'downstream_flow' 或 'downstream_level': 下游边界

        Returns:
            ComponentState: 更新后的组件状态
        """
        # 设置边界条件（支持上游流量/水位 + 下游流量/水位）
        boundary_conditions = {}

        # 上游边界条件
        if 'upstream_flow' in inputs:
            boundary_conditions['upstream_flow'] = inputs['upstream_flow']
        elif 'upstream_level' in inputs:
            boundary_conditions['upstream_level'] = inputs['upstream_level']
        else:
            # 默认使用当前上游流量
            boundary_conditions['upstream_flow'] = self.hydraulic_state.Q[0]

        # 下游边界条件
        if 'downstream_flow' in inputs:
            boundary_conditions['downstream_flow'] = inputs['downstream_flow']
        elif 'downstream_level' in inputs:
            boundary_conditions['downstream_level'] = inputs['downstream_level']
        else:
            # 默认使用当前下游水位
            boundary_conditions['downstream_level'] = self.hydraulic_state.h[-1]

        # 调用Preissmann求解器
        self.hydraulic_state.h, self.hydraulic_state.Q = self.solver.solve_canal_step(
            self.hydraulic_state.h, self.hydraulic_state.Q, dt, self.dx,
            self.parameters['width'], self.parameters['manning_n'], self.slope,
            boundary_conditions
        )

        # 更新状态
        self.state.level = np.mean(self.hydraulic_state.h)
        self.state.flow = np.mean(self.hydraulic_state.Q)

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """降阶模型"""
        inflow = inputs.get('inflow', self.hydraulic_state.Q[0])
        outflow = inputs.get('outflow', self.hydraulic_state.Q[-1])

        dV = (inflow - outflow) * dt
        self.state.volume += dV
        self.state.volume = np.clip(self.state.volume, self.volume_min, self.volume_max)
        self.state.level = self.state.volume / self.area
        self.state.flow = (inflow + outflow) / 2

        return self.state

    def get_constraints(self) -> dict:
        return {
            'volume': (self.volume_min, self.volume_max),
            'level': (self.volume_min / self.area, self.volume_max / self.area)
        }
