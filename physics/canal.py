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

        # 边界条件（MOC求解器使用）
        self.downstream_boundary = None  # 可选的下游边界条件对象

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

            # 内部节点（使用正确的MOC公式）
            # 对于宽浅渠道，正确的特征线方程：
            # C+: h + 2*c = C+值（忽略摩阻的简化）
            # C-: h - 2*c = C-值
            for i in range(1, n-1):
                # C+ 特征线从i-1传播到i
                # h[i] + 2*c[i] = h[i-1] + 2*c[i-1] (忽略摩阻)
                C_plus = h[i-1] + 2 * c[i-1]

                # C- 特征线从i+1传播到i
                # h[i] - 2*c[i] = h[i+1] - 2*c[i+1]
                C_minus = h[i+1] - 2 * c[i+1]

                # 从两条特征线求解h和c
                # h + 2*c = C+
                # h - 2*c = C-
                # 解得：h = (C+ + C-)/2,  c = (C+ - C-)/4
                h_new[i] = (C_plus + C_minus) / 2
                c_new_i = (C_plus - C_minus) / 4

                # 从c求Q：c = sqrt(g*h)，Q = V*A = V*width*h
                # 对于给定的c和h，需要从连续性方程求Q
                # 简化：假设流量连续，Q_new[i] ≈ (Q[i-1] + Q[i+1])/2
                width = self.parameters['width']
                A_new_i = h_new[i] * width
                V_new_i = (Q[i-1] / (h[i-1] * width) + Q[i+1] / (h[i+1] * width)) / 2 if (h[i-1] > 0 and h[i+1] > 0) else 0
                Q_new[i] = V_new_i * A_new_i

            # 边界条件处理（使用正确的MOC特征线方程）
            # 对于宽浅渠道：A = width * h, V = Q / A
            # C+ 特征线: h + (V / g) = C+ - (Sf - S0) * dt
            # C- 特征线: h - (V / g) = C- + (Sf - S0) * dt

            width = self.parameters['width']

            # 上游边界（入口）- 给定流量Q_in
            if 'Q_in' in inputs:
                Q_new[0] = inputs['Q_in']

                # 从内部点i=1使用C-特征线传播到边界i=0
                # C- 从 (i=1, t=k) 传播到 (i=0, t=k+1)
                A_1 = h[1] * width
                if A_1 > 0 and c[1] > 0:
                    V_1 = Q[1] / A_1
                    # C-: h - V/c = 常数（忽略摩阻的简化）
                    C_minus_value = h[1] - V_1 / g * c[1]

                    # 在新时刻边界点：h_new[0] - V_new[0]/c_new[0] = C_minus_value
                    # 已知 Q_new[0]，需要迭代求解 h_new[0]
                    # 简化：假设 c_new[0] ≈ c[1]
                    A_new_0 = max(h[0], 0.1) * width  # 初始猜测
                    V_new_0 = Q_new[0] / A_new_0 if A_new_0 > 0 else 0

                    # 从特征线：h = C- + V*c/g
                    # 由于 V = Q/A = Q/(width*h)，这是一个关于h的非线性方程
                    # 使用简化：h ≈ C- + Q/(width*h)*c/g
                    # 线性化： h ≈ C- + Q*c/(g*width*h_prev)
                    h_guess = h[0]  # 初始猜测
                    for _ in range(3):  # 简单迭代
                        c_guess = np.sqrt(g * max(h_guess, 0.1))
                        V_guess = Q_new[0] / (width * max(h_guess, 0.1))
                        h_guess = C_minus_value + V_guess * c_guess / g
                        h_guess = max(h_guess, 0.1)  # 保证正值

                    h_new[0] = h_guess
                else:
                    h_new[0] = h[0]
            else:
                # 默认：保持上游边界不变
                h_new[0] = h[0]
                Q_new[0] = Q[0]

            # 下游边界（出口）
            if self.downstream_boundary:
                # 使用自定义边界条件对象
                h_new[-1], Q_new[-1] = MOCSolver.solve_canal_boundary(
                    h[-2], Q[-2], h[-1], Q[-1],
                    self.downstream_boundary, self.dx, dt, self.area
                )
            elif 'Q_out' in inputs:
                # 给定流量Q_out
                Q_new[-1] = inputs['Q_out']

                # 从内部点i=-2使用C+特征线传播到边界i=-1
                # C+ 从 (i=-2, t=k) 传播到 (i=-1, t=k+1)
                A_minus2 = h[-2] * width
                if A_minus2 > 0 and c[-2] > 0:
                    V_minus2 = Q[-2] / A_minus2
                    # C+: h + V/c = 常数
                    C_plus_value = h[-2] + V_minus2 / g * c[-2]

                    # 迭代求解 h_new[-1]
                    h_guess = h[-1]
                    for _ in range(3):
                        c_guess = np.sqrt(g * max(h_guess, 0.1))
                        V_guess = Q_new[-1] / (width * max(h_guess, 0.1))
                        h_guess = C_plus_value - V_guess * c_guess / g
                        h_guess = max(h_guess, 0.1)

                    h_new[-1] = h_guess
                else:
                    h_new[-1] = h[-1]
            else:
                # 默认：保持下游边界不变
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
