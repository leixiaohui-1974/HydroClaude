"""
模型预测控制器（MPC）

使用CVXPY实现凸优化MPC控制器，用于IDZ模型的水位控制。

主要特性：
- 基于IDZ模型的多步预测
- 显式约束处理（控制量、变化率、状态量）
- 二次规划（QP）优化
- 软约束终端惩罚
- 可配置预测/控制时域

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import cvxpy as cp
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from scipy import signal

try:
    from idz_model import IDZParameters, IDZModel
except ImportError:
    from control.idz_model import IDZParameters, IDZModel


@dataclass
class MPCConfig:
    """MPC控制器配置"""
    # 时域参数
    prediction_horizon: int = 10  # 预测时域 Np
    control_horizon: int = 5      # 控制时域 Nc
    dt: float = 10.0              # 采样时间 (s)

    # 权重参数
    Q: float = 1.0                # 状态误差权重
    R: float = 0.01               # 控制增量权重
    Qf: float = 10.0              # 终端状态权重（软约束）

    # 约束
    u_min: float = 0.5            # 最小控制量 (m)
    u_max: float = 4.0            # 最大控制量 (m)
    du_max: float = 0.5           # 最大控制增量 (m)

    y_min: Optional[float] = None # 最小水位 (m)
    y_max: Optional[float] = None # 最大水位 (m)

    # 求解器设置
    solver: str = 'OSQP'          # CVXPY求解器: OSQP, ECOS, SCS
    verbose: bool = False         # 显示求解器输出


class MPCController:
    """
    模型预测控制器（基于IDZ模型）

    使用CVXPY求解二次规划问题：

    min  Σ Q*(y[k] - r[k])² + Σ R*Δu[k]² + Qf*(y[Np] - r[Np])²

    s.t. 模型约束：y[k+1] = f(y[k], u[k])  (IDZ模型)
         控制约束：u_min ≤ u[k] ≤ u_max
         变化率约束：|Δu[k]| ≤ du_max
         状态约束：y_min ≤ y[k] ≤ y_max (可选)
    """

    def __init__(self, idz_params: IDZParameters, config: MPCConfig, use_observer: bool = True):
        """
        初始化MPC控制器

        Args:
            idz_params: IDZ模型参数
            config: MPC配置
            use_observer: 是否使用Luenberger观测器（推荐True）
        """
        self.idz_params = idz_params
        self.config = config
        self.use_observer = use_observer

        # 构建IDZ离散状态空间模型
        self._build_state_space_model()

        # 初始化状态估计
        self.x_hat = np.zeros(self.n_states)  # 状态估计值
        self.u_prev = 2.0  # 上一步控制量 (初始开度)
        self.y_prev = 0.0  # 上一步测量输出

        # 构建Luenberger观测器
        if self.use_observer:
            self._design_observer()

        # 优化问题（延迟构建）
        self.prob = None

        # 诊断信息
        self.solve_time_history = []
        self.objective_history = []

    def _build_state_space_model(self):
        """
        构建IDZ离散状态空间模型

        连续IDZ: G(s) = K*(1 + τ_z*s) / (s*(1 + τ_d*s)) * exp(-θ*s)

        使用Controller Canonical Form (CCF)：
        G(s) = (b1*s + b0) / (s^2 + a1*s + a0)

        状态空间：
        dx/dt = A*x + B*u
        y = C*x + D*u

        其中：
        A = [[0, 1], [-a0, -a1]]
        B = [[0], [1]]
        C = [b0, b1]
        D = 0
        """
        dt = self.config.dt
        K = self.idz_params.K
        tau_z = self.idz_params.tau_z
        tau_d = self.idz_params.tau_d

        # IDZ传递函数: G(s) = K*(1 + τ_z*s) / (s*(1 + τ_d*s))
        # 展开分母: s*(1 + τ_d*s) = τ_d*s^2 + s
        # 标准形式: (K*τ_z*s + K) / (τ_d*s^2 + s)
        # 除以τ_d归一化: (K*τ_z/τ_d*s + K/τ_d) / (s^2 + s/τ_d)

        # 系数
        a1 = 1.0 / tau_d
        a0 = 0.0  # 积分器导致没有常数项
        b1 = K * tau_z / tau_d
        b0 = K / tau_d

        # 连续状态空间（Controller Canonical Form）
        A_c = np.array([
            [0, 1],
            [-a0, -a1]
        ])
        B_c = np.array([[0], [1]])
        C_c = np.array([[b0, b1]])
        D_c = np.array([[0]])

        # 离散化（零阶保持）
        sys_c = signal.StateSpace(A_c, B_c, C_c, D_c)
        sys_d = sys_c.to_discrete(dt)

        self.A = sys_d.A
        self.B = sys_d.B.flatten()
        self.C = sys_d.C.flatten()
        self.D = sys_d.D.flatten()
        self.n_states = self.A.shape[0]

    def _design_observer(self):
        """
        设计Luenberger状态观测器

        观测器动态方程：
        x_hat[k+1] = A*x_hat[k] + B*u[k] + L*(y[k] - C*x_hat[k])

        其中L是观测器增益矩阵，通过极点配置法设计。
        观测器极点应比系统极点快2-5倍，以快速收敛到真实状态。
        """
        # 计算系统极点
        sys_poles = np.linalg.eigvals(self.A)

        # 设计观测器极点（比系统极点快2-3倍，更保守以提高数值稳定性）
        # 从0.3改为0.5，牺牲一些响应速度换取稳定性
        observer_poles = sys_poles * 0.5

        # 确保极点在单位圆内（稳定性），更保守的上限
        observer_poles = np.clip(np.abs(observer_poles), 0, 0.85) * np.exp(1j * np.angle(observer_poles))

        # 使用极点配置法设计观测器增益L
        # 对偶系统：(A', C')，设计K使得A'-K*C'有期望极点
        # 则L = K'
        try:
            from scipy import linalg
            K = linalg.place_poles(self.A.T, self.C.reshape(-1, 1), observer_poles).gain_matrix.T
            self.L = K
        except:
            # 如果极点配置失败，使用简单的增益
            # L = [l1, l2]^T，手动调整
            self.L = np.array([[2.0], [1.0]])  # 经验值

        print(f"Luenberger观测器增益 L = {self.L.flatten()}")
        print(f"观测器极点: {observer_poles}")

    def _update_observer(self, y_measured: float, u_applied: float):
        """
        更新Luenberger观测器状态（带数值保护）

        Args:
            y_measured: 测量输出
            u_applied: 施加的控制量
        """
        # 检查当前状态是否有效
        if np.any(np.isnan(self.x_hat)) or np.any(np.isinf(self.x_hat)):
            # 状态无效，重置为简单估计
            print(f"Warning: Observer state invalid, resetting...")
            self.x_hat = self._estimate_state(y_measured)
            return

        # 预测步骤：x_hat_pred = A*x_hat + B*u
        x_hat_pred = self.A @ self.x_hat + self.B * u_applied

        # 状态饱和保护（防止累积）
        x_hat_pred = np.clip(x_hat_pred, -1e6, 1e6)

        # 输出预测：y_hat = C*x_hat_pred + D*u
        y_hat = self.C @ x_hat_pred + self.D[0] * u_applied

        # 输出误差（限制最大误差，避免观测器过度校正）
        y_error = y_measured - y_hat
        y_error = np.clip(y_error, -10.0, 10.0)  # 限制误差在±10m

        # 校正步骤：x_hat = x_hat_pred + L*(y - y_hat)
        correction = (self.L @ np.array([[y_error]])).flatten()
        correction = np.clip(correction, -100.0, 100.0)  # 限制校正量
        self.x_hat = x_hat_pred + correction

        # 最终饱和保护
        self.x_hat = np.clip(self.x_hat, -1e6, 1e6)

        # 二次检查
        if np.any(np.isnan(self.x_hat)) or np.any(np.isinf(self.x_hat)):
            print(f"Warning: Observer state became invalid after update, resetting...")
            self.x_hat = self._estimate_state(y_measured)

    def _build_optimization_problem(self):
        """构建CVXPY优化问题"""
        Np = self.config.prediction_horizon
        Nc = self.config.control_horizon

        # 决策变量
        x = cp.Variable((self.n_states, Np + 1))  # 状态轨迹
        u = cp.Variable(Nc)                        # 控制序列

        # 参数（每次调用update时更新）
        x0 = cp.Parameter(self.n_states)           # 初始状态
        r = cp.Parameter(Np + 1)                   # 参考轨迹
        u_prev = cp.Parameter()                    # 上一步控制量

        # 代价函数
        cost = 0
        constraints = [x[:, 0] == x0]

        # 预测时域内的代价
        for k in range(Np):
            # 确定当前控制量
            if k < Nc:
                u_k = u[k]
            else:
                u_k = u[Nc - 1]

            # 状态预测误差（包含D项）
            y_pred = self.C @ x[:, k] + self.D[0] * u_k if self.D[0] != 0 else self.C @ x[:, k]
            cost += self.config.Q * cp.square(y_pred - r[k])

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

            # 状态约束（可选）
            if self.config.y_min is not None:
                constraints.append(y_pred >= self.config.y_min)
            if self.config.y_max is not None:
                constraints.append(y_pred <= self.config.y_max)

            # 模型约束（状态转移）
            constraints.append(x[:, k+1] == self.A @ x[:, k] + self.B * u_k)

        # 终端代价（软约束）
        y_final = self.C @ x[:, Np]
        cost += self.config.Qf * cp.square(y_final - r[Np])

        # 构建优化问题
        objective = cp.Minimize(cost)
        self.prob = cp.Problem(objective, constraints)

        # 保存参数引用
        self.opt_x0 = x0
        self.opt_r = r
        self.opt_u_prev = u_prev
        self.opt_x = x
        self.opt_u = u

    def compute_control(self, y_current: float, setpoint: float,
                       u_disturbance: float = 0.0) -> Tuple[float, Dict]:
        """
        计算MPC控制量

        Args:
            y_current: 当前水位 (m)
            setpoint: 目标水位 (m)
            u_disturbance: 上游流量扰动 (m³/s)，未使用

        Returns:
            (控制量, 诊断信息字典)
        """
        # 首次调用时构建优化问题
        if self.prob is None:
            self._build_optimization_problem()

        # 首次调用时初始化观测器状态（使用实际测量值）
        if np.allclose(self.x_hat, 0.0):
            self.x_hat = self._estimate_state(y_current)

        # 状态估计：使用Luenberger观测器或简单估计
        if self.use_observer:
            # 使用观测器更新状态估计
            self._update_observer(y_current, self.u_prev)
        else:
            # 简单估计（不推荐）
            self.x_hat = self._estimate_state(y_current)

        # 构建参考轨迹（恒定设定值）
        r_trajectory = np.full(self.config.prediction_horizon + 1, setpoint)

        # 参数验证和清理（确保无NaN/Inf）
        if np.any(np.isnan(self.x_hat)) or np.any(np.isinf(self.x_hat)):
            print(f"Warning: x_hat contains NaN/Inf, using fallback estimation")
            self.x_hat = self._estimate_state(y_current)

        if not np.isfinite(self.u_prev):
            print(f"Warning: u_prev is not finite, resetting to 2.0")
            self.u_prev = 2.0

        # 更新优化问题参数
        self.opt_x0.value = self.x_hat
        self.opt_r.value = r_trajectory
        self.opt_u_prev.value = self.u_prev

        # 求解优化问题
        try:
            if self.config.solver == 'OSQP':
                self.prob.solve(solver=cp.OSQP, verbose=self.config.verbose)
            elif self.config.solver == 'ECOS':
                self.prob.solve(solver=cp.ECOS, verbose=self.config.verbose)
            elif self.config.solver == 'SCS':
                self.prob.solve(solver=cp.SCS, verbose=self.config.verbose)
            else:
                self.prob.solve(verbose=self.config.verbose)

            # 检查求解状态
            if self.prob.status not in ['optimal', 'optimal_inaccurate']:
                print(f"Warning: MPC solver status: {self.prob.status}")
                # 退化：保持上一步控制量
                u_opt = self.u_prev
                success = False
            else:
                # 提取最优控制序列的第一个元素
                u_opt = self.opt_u.value[0]
                success = True

            # 记录诊断信息
            solve_time = self.prob.solver_stats.solve_time if self.prob.solver_stats else 0.0
            self.solve_time_history.append(solve_time)
            self.objective_history.append(self.prob.value if self.prob.value else 0.0)

            diagnostics = {
                'status': self.prob.status,
                'solve_time': solve_time,
                'objective': self.prob.value,
                'predicted_trajectory': self.C @ self.opt_x.value if success else None,
                'control_sequence': self.opt_u.value if success else None,
                'success': success
            }

        except Exception as e:
            print(f"MPC optimization failed: {e}")
            u_opt = self.u_prev  # 退化：保持上一步
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

        # 更新上一步控制量
        self.u_prev = u_opt

        return u_opt, diagnostics

    def _estimate_state(self, y_measured: float) -> np.ndarray:
        """
        从测量输出估计状态（简化方法）

        对于Controller Canonical Form:
        y = C @ x = [b0, b1] @ [x1, x2]
        其中 b0 = K/tau_d, b1 = K*tau_z/tau_d

        由于 |b1| >> |b0|（通常tau_z << tau_d），假设x2主导输出：
        y ≈ b1 * x2
        → x2 ≈ y / b1
        → x1 ≈ 0（或保持小值）

        Args:
            y_measured: 测量水位

        Returns:
            估计状态向量
        """
        # 使用C矩阵进行估计
        b0 = self.C[0]  # K / tau_d
        b1 = self.C[1]  # K * tau_z / tau_d

        # 如果b1接近0（tau_z很小），则使用b0
        if abs(b1) > abs(b0):
            # x2主导输出
            x2_est = y_measured / b1 if b1 != 0 else 0.0
            x1_est = 0.0
        else:
            # x1主导输出
            x1_est = y_measured / b0 if b0 != 0 else 0.0
            x2_est = 0.0

        x_est = np.array([x1_est, x2_est])

        return x_est

    def reset(self):
        """重置控制器状态"""
        self.x_hat = np.zeros(self.n_states)
        self.u_prev = 2.0
        self.y_prev = 0.0
        self.solve_time_history = []
        self.objective_history = []

    def update_model(self, new_params: IDZParameters):
        """
        更新IDZ模型参数（用于自适应MPC）

        Args:
            new_params: 新的IDZ参数
        """
        self.idz_params = new_params
        self._build_state_space_model()

        # 重新构建优化问题
        self.prob = None

    def get_diagnostics(self) -> Dict:
        """获取诊断信息"""
        return {
            'average_solve_time': np.mean(self.solve_time_history) if self.solve_time_history else 0.0,
            'max_solve_time': np.max(self.solve_time_history) if self.solve_time_history else 0.0,
            'average_objective': np.mean(self.objective_history) if self.objective_history else 0.0,
            'current_state': self.x_hat.copy(),
            'previous_control': self.u_prev,
            'use_observer': self.use_observer
        }


# ====================================================================================
# 测试代码
# ====================================================================================
def test_mpc_controller():
    """测试MPC控制器"""
    print("=" * 80)
    print("MPC控制器测试")
    print("=" * 80)

    # 创建IDZ参数（简化参数便于测试）
    idz_params = IDZParameters(K=1.0, tau_z=20.0, tau_d=30.0, theta=5.0)

    # 创建MPC配置
    mpc_config = MPCConfig(
        prediction_horizon=15,  # 增加预测时域
        control_horizon=10,     # 增加控制时域
        dt=2.0,
        Q=100.0,   # 大幅增大状态误差权重
        R=1.0,     # 增大控制增量权重（更保守）
        Qf=1000.0, # 大幅增大终端权重
        u_min=-2.0,  # 允许负控制量（用于降低水位）
        u_max=5.0,
        du_max=0.5,  # 减小最大变化率
        solver='OSQP',
        verbose=False
    )

    # 创建控制器
    controller = MPCController(idz_params, mpc_config)

    print("\nIDZ模型参数:")
    print(f"  K = {idz_params.K:.1f} m/(m³/s)")
    print(f"  τ_z = {idz_params.tau_z:.1f} s")
    print(f"  τ_d = {idz_params.tau_d:.1f} s")
    print(f"  θ = {idz_params.theta:.1f} s")

    print("\nMPC配置:")
    print(f"  预测时域 Np = {mpc_config.prediction_horizon}")
    print(f"  控制时域 Nc = {mpc_config.control_horizon}")
    print(f"  采样时间 dt = {mpc_config.dt} s")
    print(f"  控制约束: [{mpc_config.u_min}, {mpc_config.u_max}] m")
    print(f"  变化率约束: ±{mpc_config.du_max} m/step")

    # 仿真测试
    print("\n" + "-" * 80)
    print("闭环仿真测试")
    print("-" * 80)

    # 仿真参数
    setpoint = 1.0  # 目标水位 (m)
    n_steps = 100

    # 使用MPC自己的状态空间模型进行仿真（验证MPC算法）
    # 这样避免模型不匹配问题
    x_sim = np.zeros(controller.n_states)  # 仿真状态
    y = controller.C @ x_sim + controller.D[0] * 1.0  # 初始输出

    # 记录
    y_history = [y]
    u_history = [1.0]  # 初始控制量
    time_history = [0.0]

    print(f"\n初始水位: {y:.3f} m")
    print(f"目标水位: {setpoint:.3f} m")
    print(f"仿真步数: {n_steps}")
    print("\n使用MPC内部模型进行闭环仿真（验证算法正确性）")

    # 闭环仿真
    for k in range(n_steps):
        # MPC计算控制量
        u, diagnostics = controller.compute_control(y, setpoint)

        # 使用状态空间模型仿真（与MPC内部模型一致）
        x_sim = controller.A @ x_sim + controller.B * u
        y = controller.C @ x_sim + controller.D[0] * u

        # 记录
        y_history.append(y)
        u_history.append(u)
        time_history.append((k + 1) * mpc_config.dt)

        # 显示进度
        if (k + 1) % 10 == 0:
            error = y - setpoint
            print(f"  步骤 {k+1}: y={y:.3f} m, u={u:.3f} m, error={error:.4f} m, "
                  f"solve_time={diagnostics['solve_time']*1000:.1f} ms")

    # 性能评估
    y_array = np.array(y_history)
    u_array = np.array(u_history)
    error = y_array - setpoint

    mae = np.mean(np.abs(error))
    rmse = np.sqrt(np.mean(error**2))
    max_error = np.max(np.abs(error))
    steady_state_error = np.mean(np.abs(error[-10:]))  # 最后10步
    control_effort = np.sum(np.abs(np.diff(u_array)))

    print("\n性能指标:")
    print(f"  MAE (平均绝对误差):     {mae:.4f} m")
    print(f"  RMSE (均方根误差):      {rmse:.4f} m")
    print(f"  最大误差:               {max_error:.4f} m")
    print(f"  稳态误差:               {steady_state_error:.4f} m")
    print(f"  控制能耗:               {control_effort:.4f} m")

    # 诊断信息
    diag = controller.get_diagnostics()
    print("\nMPC诊断:")
    print(f"  平均求解时间: {diag['average_solve_time']*1000:.2f} ms")
    print(f"  最大求解时间: {diag['max_solve_time']*1000:.2f} ms")
    print(f"  平均目标函数值: {diag['average_objective']:.4f}")

    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)

    return {
        'time': time_history,
        'y': y_history,
        'u': u_history,
        'setpoint': setpoint,
        'metrics': {
            'mae': mae,
            'rmse': rmse,
            'max_error': max_error,
            'steady_state_error': steady_state_error
        }
    }


if __name__ == "__main__":
    test_mpc_controller()
