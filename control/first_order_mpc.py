"""
一阶模型预测控制器（First-Order MPC）

使用一阶传递函数 H(s) = K/(τ*s+1) 而不是二阶IDZ模型
适合线性化渠道系统（无积分器，稳定系统）

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import cvxpy as cp
from typing import Tuple, Dict
from dataclasses import dataclass
from scipy import signal


@dataclass
class FirstOrderMPCConfig:
    """一阶MPC配置"""
    # 时域参数
    prediction_horizon: int = 10
    control_horizon: int = 5
    dt: float = 10.0

    # 权重参数
    Q: float = 1.0
    R: float = 0.01
    Qf: float = 10.0

    # 约束
    u_min: float = 0.1
    u_max: float = 4.0
    du_max: float = 0.5

    y_min: float = None
    y_max: float = None

    # 求解器
    solver: str = 'OSQP'
    verbose: bool = False


class FirstOrderMPC:
    """
    一阶MPC控制器

    模型：H(s) = K / (τ*s + 1)

    状态空间（一阶）：
    dx/dt = -1/τ * x + K/τ * u
    y = x

    优化问题：
    min Σ Q*(y[k] - r[k])² + Σ R*Δu[k]² + Qf*(y[Np] - r[Np])²
    s.t. y[k+1] = a*y[k] + b*u[k]
         u_min ≤ u[k] ≤ u_max
         |Δu[k]| ≤ du_max
    """

    def __init__(self, K: float, tau: float, config: FirstOrderMPCConfig):
        """
        初始化一阶MPC控制器

        Args:
            K: 稳态增益 (m/m)
            tau: 时间常数 (s)
            config: MPC配置
        """
        self.K = K
        self.tau = tau
        self.config = config

        # 构建离散一阶模型
        self._build_discrete_model()

        # 状态
        self.y_prev = 0.0
        self.u_prev = 2.0

        # 优化问题
        self.prob = None

        # 诊断
        self.solve_time_history = []
        self.objective_history = []

        print(f"一阶MPC初始化:")
        print(f"  K = {self.K:.4f} m/m")
        print(f"  τ = {self.tau:.1f}s")
        print(f"  dt = {self.config.dt:.1f}s")
        print(f"  离散参数: a = {self.a:.6f}, b = {self.b:.6f}")

    def _build_discrete_model(self):
        """
        构建离散一阶模型

        连续：dx/dt = -x/τ + K/τ * u, y = x
        离散（ZOH）：y[k+1] = a*y[k] + b*u[k]
        其中：
        - a = exp(-dt/τ)
        - b = K * (1 - exp(-dt/τ))
        """
        dt = self.config.dt

        # 离散化参数
        self.a = np.exp(-dt / self.tau)
        self.b = self.K * (1 - np.exp(-dt / self.tau))

        # 验证稳态增益
        # y_ss = b*u_ss / (1 - a) = K*u_ss (应该等于)
        steady_state_gain = self.b / (1 - self.a)
        print(f"  稳态增益验证: K_discrete = {steady_state_gain:.4f} (理论值 = {self.K:.4f})")

    def _build_optimization_problem(self):
        """构建CVXPY优化问题"""
        Np = self.config.prediction_horizon
        Nc = self.config.control_horizon

        # 决策变量
        y = cp.Variable(Np + 1)  # 输出轨迹
        u = cp.Variable(Nc)       # 控制序列

        # 参数
        y0 = cp.Parameter()       # 初始输出
        r = cp.Parameter(Np + 1)  # 参考轨迹
        u_prev = cp.Parameter()   # 上一步控制量

        # 代价函数和约束
        cost = 0
        constraints = [y[0] == y0]

        # 预测时域
        for k in range(Np):
            # 确定当前控制量
            if k < Nc:
                u_k = u[k]
            else:
                u_k = u[Nc - 1]

            # 跟踪误差代价
            cost += self.config.Q * cp.square(y[k] - r[k])

            # 控制增量代价和约束
            if k < Nc:
                if k == 0:
                    du = u[k] - u_prev
                else:
                    du = u[k] - u[k-1]
                cost += self.config.R * cp.square(du)

                # 控制约束
                constraints.append(u[k] >= self.config.u_min)
                constraints.append(u[k] <= self.config.u_max)

                # 控制增量约束
                constraints.append(du >= -self.config.du_max)
                constraints.append(du <= self.config.du_max)

            # 输出约束
            if self.config.y_min is not None:
                constraints.append(y[k] >= self.config.y_min)
            if self.config.y_max is not None:
                constraints.append(y[k] <= self.config.y_max)

            # 模型约束：y[k+1] = a*y[k] + b*u[k]
            constraints.append(y[k+1] == self.a * y[k] + self.b * u_k)

        # 终端代价
        cost += self.config.Qf * cp.square(y[Np] - r[Np])

        # 构建优化问题
        objective = cp.Minimize(cost)
        self.prob = cp.Problem(objective, constraints)

        # 保存参数引用
        self.opt_y0 = y0
        self.opt_r = r
        self.opt_u_prev = u_prev
        self.opt_y = y
        self.opt_u = u

    def compute_control(self, y_current: float, setpoint: float) -> Tuple[float, Dict]:
        """
        计算MPC控制量

        Args:
            y_current: 当前输出 (m)
            setpoint: 目标值 (m)

        Returns:
            (控制量, 诊断信息)
        """
        # 首次调用时构建优化问题
        if self.prob is None:
            self._build_optimization_problem()

        # 构建参考轨迹
        r_trajectory = np.full(self.config.prediction_horizon + 1, setpoint)

        # 更新参数
        self.opt_y0.value = y_current
        self.opt_r.value = r_trajectory
        self.opt_u_prev.value = self.u_prev

        # 求解优化问题
        try:
            if self.config.solver == 'OSQP':
                self.prob.solve(solver=cp.OSQP, verbose=self.config.verbose)
            elif self.config.solver == 'ECOS':
                self.prob.solve(solver=cp.ECOS, verbose=self.config.verbose)
            else:
                self.prob.solve(verbose=self.config.verbose)

            # 检查求解状态
            if self.prob.status not in ['optimal', 'optimal_inaccurate']:
                print(f"Warning: MPC solver status: {self.prob.status}")
                u_opt = self.u_prev
                success = False
            else:
                u_opt = self.opt_u.value[0]
                success = True

            # 诊断信息
            solve_time = self.prob.solver_stats.solve_time if self.prob.solver_stats else 0.0
            self.solve_time_history.append(solve_time)
            self.objective_history.append(self.prob.value if self.prob.value else 0.0)

            diagnostics = {
                'status': self.prob.status,
                'solve_time': solve_time,
                'objective': self.prob.value,
                'predicted_trajectory': self.opt_y.value if success else None,
                'control_sequence': self.opt_u.value if success else None,
                'success': success
            }

        except Exception as e:
            print(f"MPC optimization failed: {e}")
            u_opt = self.u_prev
            diagnostics = {
                'status': 'failed',
                'solve_time': 0.0,
                'objective': np.inf,
                'predicted_trajectory': None,
                'control_sequence': None,
                'success': False,
                'error': str(e)
            }

        # 约束控制量
        u_opt = np.clip(u_opt, self.config.u_min, self.config.u_max)

        # 更新状态
        self.u_prev = u_opt
        self.y_prev = y_current

        return u_opt, diagnostics

    def reset(self):
        """重置控制器"""
        self.y_prev = 0.0
        self.u_prev = 2.0
        self.solve_time_history = []
        self.objective_history = []

    def get_diagnostics(self) -> Dict:
        """获取诊断信息"""
        return {
            'average_solve_time': np.mean(self.solve_time_history) if self.solve_time_history else 0.0,
            'max_solve_time': np.max(self.solve_time_history) if self.solve_time_history else 0.0,
            'average_objective': np.mean(self.objective_history) if self.objective_history else 0.0,
            'previous_control': self.u_prev
        }
