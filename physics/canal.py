import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState, HydraulicState
from core.constants import PhysicsConstants, CanalDefaults, NumericalDefaults
from physics.moc_solver import MOCSolver
from physics.numerical_methods.preissmann_solver import PreissmannSolver
from physics.numerical_methods.fvm_solver import FVMSolver

class Canal(HydraulicComponent):
    """
    明渠组件 - Saint-Venant方程求解

    支持多种数值方法：MOC, Preissmann, FVM
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

        # 初始化求解器
        if self.method == 'preissmann':
            theta = NumericalDefaults.PREISSMANN_THETA
            self.solver = PreissmannSolver(theta=theta)
        elif self.method == 'fvm':
            flux_scheme = NumericalDefaults.FVM_FLUX_SCHEME
            limiter = NumericalDefaults.FVM_LIMITER
            self.solver = FVMSolver(flux_scheme=flux_scheme, limiter=limiter)

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """高保真MOC求解"""
        if self.method == 'moc':
            # 使用实例变量而不是硬编码
            g = self.g
            n = self.n_sections

            h = self.hydraulic_state.h.copy()
            Q = self.hydraulic_state.Q.copy()
            h_new = np.zeros(n)
            Q_new = np.zeros(n)
            c = np.sqrt(g * h)

            # 内部节点
            for i in range(1, n-1):
                n_manning = self.parameters['manning_n']
                width = self.parameters['width']
                A_section = h[i] * width
                P = width + 2 * h[i]
                R = A_section / P if P > 0 else 0

                Sf = 0
                if R > 0 and Q[i] > 0:
                    V = Q[i] / A_section
                    Sf = (n_manning * V)**2 / (R**(4/3))

                C_plus = h[i-1] + ((Q[i-1]/A_section + c[i-1]) / g) * Q[i-1] \
                        - c[i-1] * (Sf - self.slope) * dt
                C_minus = h[i+1] - ((c[i+1] - Q[i+1]/A_section) / g) * Q[i+1] \
                         + c[i+1] * (Sf - self.slope) * dt

                h_new[i] = (C_plus + C_minus) / 2
                Q_new[i] = (g / (2 * c[i])) * (C_plus - C_minus) if c[i] > 0 else Q[i]

            # 边界
            if self.downstream_boundary:
                h_new[-1], Q_new[-1] = MOCSolver.solve_canal_boundary(
                    h[-2], Q[-2], h[-1], Q[-1],
                    self.downstream_boundary, self.dx, dt, self.area
                )
            else:
                h_new[0] = h[0]
                Q_new[0] = Q[0]
                h_new[-1] = h[-1]
                Q_new[-1] = Q[-1]

            # 使用配置的约束范围而不是硬编码
            self.hydraulic_state.h = np.clip(h_new, self.h_min, self.h_max)
            self.hydraulic_state.Q = np.clip(Q_new, self.q_min, self.q_max)

            self.state.level = np.mean(self.hydraulic_state.h)
            self.state.volume = self.state.level * self.area
            self.state.flow = np.mean(self.hydraulic_state.Q)

        elif self.method == 'preissmann':
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
            self.hydraulic_state.h, self.hydraulic_state.Q = self.solver.solve_canal_step(
                self.hydraulic_state.h, self.hydraulic_state.Q, dt, self.dx,
                self.parameters['width'], self.parameters['manning_n'], self.slope,
                boundary_conditions
            )
            self.state.level = np.mean(self.hydraulic_state.h)
            self.state.flow = np.mean(self.hydraulic_state.Q)

        elif self.method == 'fvm':
            A = self.hydraulic_state.h * self.parameters['width']
            self.hydraulic_state.h, self.hydraulic_state.Q = self.solver.solve_canal_step(
                A, self.hydraulic_state.Q, dt, self.dx,
                self.parameters['width'], self.parameters['manning_n'], self.slope
            )
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
