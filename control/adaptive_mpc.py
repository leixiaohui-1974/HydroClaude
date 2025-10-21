"""
自适应模型预测控制（Adaptive MPC）
在线更新模型参数，适应系统动态变化
"""
import numpy as np
from scipy.optimize import minimize
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass

@dataclass
class AdaptiveMPCConfig:
    """自适应MPC配置参数"""
    prediction_horizon: int = 10  # 预测时域
    control_horizon: int = 5  # 控制时域
    dt: float = 60.0  # 采样时间

    # 权重矩阵
    Q: np.ndarray = None  # 状态权重
    R: np.ndarray = None  # 控制权重

    # 约束
    u_min: float = -10.0  # 控制下界
    u_max: float = 10.0  # 控制上界
    du_max: float = 2.0  # 控制变化率限制

    # 自适应参数
    adaptation_rate: float = 0.01  # 参数更新速率
    forgetting_factor: float = 0.98  # 遗忘因子
    min_update_samples: int = 5  # 最小更新样本数

class AdaptiveMPC:
    """
    自适应MPC控制器

    特点：
    1. 在线参数辨识
    2. 模型自适应更新
    3. 处理系统不确定性
    4. 递推最小二乘（RLS）参数更新
    """

    def __init__(self, config: AdaptiveMPCConfig,
                 initial_A: np.ndarray, initial_B: np.ndarray):
        """
        Args:
            config: MPC配置
            initial_A: 初始状态矩阵
            initial_B: 初始输入矩阵
        """
        self.config = config

        # 状态空间模型: x[k+1] = A*x[k] + B*u[k]
        self.A = initial_A.copy()
        self.B = initial_B.copy()

        # 状态维度
        self.nx = self.A.shape[0]
        self.nu = self.B.shape[1] if len(self.B.shape) > 1 else 1

        # 默认权重矩阵
        if config.Q is None:
            self.Q = np.eye(self.nx)
        else:
            self.Q = config.Q

        if config.R is None:
            self.R = np.eye(self.nu) * 0.1
        else:
            self.R = config.R

        # RLS参数估计
        self.P_rls = np.eye(self.nx * (self.nx + self.nu)) * 1000  # 协方差矩阵
        self.theta = self._pack_parameters(self.A, self.B)  # 参数向量

        # 历史数据缓冲
        self.state_history = []
        self.control_history = []
        self.max_history = 100

        # 当前状态
        self.current_state = np.zeros((self.nx, 1))
        self.last_control = np.zeros((self.nu, 1))

        # 统计信息
        self.adaptation_count = 0
        self.prediction_errors = []

    def _pack_parameters(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """将A和B矩阵打包成参数向量"""
        return np.vstack([A.flatten().reshape(-1, 1),
                         B.flatten().reshape(-1, 1)])

    def _unpack_parameters(self, theta: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """将参数向量解包为A和B矩阵"""
        n_a = self.nx * self.nx
        A = theta[:n_a].reshape(self.nx, self.nx)
        B = theta[n_a:].reshape(self.B.shape)
        return A, B

    def update_model_rls(self, x_current: np.ndarray, u_current: np.ndarray,
                        x_next: np.ndarray):
        """
        使用递推最小二乘（RLS）更新模型参数

        Args:
            x_current: 当前状态
            u_current: 当前控制
            x_next: 下一状态（实际测量）
        """
        # 构造回归向量: phi = [x; u]
        phi = np.vstack([x_current, u_current])

        # RLS更新
        lambda_f = self.config.forgetting_factor

        # 对每个状态分量独立更新
        for i in range(self.nx):
            # 第i个状态的目标值
            y_i = x_next[i, 0]

            # 第i个状态对应的参数
            start_idx = i * (self.nx + self.nu)
            end_idx = start_idx + (self.nx + self.nu)
            theta_i = self.theta[start_idx:end_idx]
            P_i = self.P_rls[start_idx:end_idx, start_idx:end_idx]

            # 预测误差
            e = y_i - phi.T @ theta_i

            # 增益
            K = P_i @ phi / (lambda_f + phi.T @ P_i @ phi)

            # 参数更新
            theta_i = theta_i + K * e

            # 协方差更新
            P_i = (P_i - K @ phi.T @ P_i) / lambda_f

            # 更新全局参数
            self.theta[start_idx:end_idx] = theta_i
            self.P_rls[start_idx:end_idx, start_idx:end_idx] = P_i

        # 解包参数
        self.A, self.B = self._unpack_parameters(self.theta)

        # 更新统计
        self.adaptation_count += 1
        self.prediction_errors.append(float(np.linalg.norm(x_next - self.A @ x_current - self.B @ u_current)))

    def predict_trajectory(self, x0: np.ndarray, u_sequence: np.ndarray) -> np.ndarray:
        """
        预测未来轨迹

        Args:
            x0: 初始状态
            u_sequence: 控制序列 [N, nu]

        Returns:
            状态序列 [N+1, nx]
        """
        N = len(u_sequence)
        x_traj = np.zeros((N + 1, self.nx))
        x_traj[0] = x0.flatten()

        for k in range(N):
            u_k = u_sequence[k].reshape(-1, 1)
            x_k = x_traj[k].reshape(-1, 1)
            x_next = self.A @ x_k + self.B @ u_k
            x_traj[k + 1] = x_next.flatten()

        return x_traj

    def compute_control(self, current_state: np.ndarray,
                       reference: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        计算MPC控制律

        Args:
            current_state: 当前状态
            reference: 参考轨迹或目标状态

        Returns:
            (optimal_control, info_dict)
        """
        N = self.config.prediction_horizon
        M = self.config.control_horizon

        # 初始控制序列
        u0 = np.zeros(M * self.nu)

        # 定义代价函数
        def cost_function(u_flat):
            u_seq = u_flat.reshape(M, self.nu)

            # 扩展控制序列到预测时域
            u_extended = np.vstack([u_seq,
                                   np.tile(u_seq[-1], (N - M, 1))])

            # 预测轨迹
            x_traj = self.predict_trajectory(current_state, u_extended)

            # 计算代价
            cost = 0.0

            # 状态误差代价
            for k in range(N + 1):
                x_error = x_traj[k].reshape(-1, 1) - reference
                cost += float(x_error.T @ self.Q @ x_error)

            # 控制代价
            for k in range(M):
                u_k = u_seq[k].reshape(-1, 1)
                cost += float(u_k.T @ self.R @ u_k)

            # 控制变化率代价
            for k in range(M - 1):
                du = u_seq[k + 1] - u_seq[k]
                cost += 0.1 * np.sum(du**2)

            return cost

        # 约束
        bounds = [(self.config.u_min, self.config.u_max)] * (M * self.nu)

        # 优化求解
        result = minimize(cost_function, u0, method='SLSQP', bounds=bounds,
                         options={'maxiter': 100, 'ftol': 1e-6})

        # 提取第一个控制动作
        u_optimal = result.x[:self.nu].reshape(-1, 1)

        # 信息字典
        info = {
            'success': result.success,
            'cost': result.fun,
            'iterations': result.nit,
            'full_sequence': result.x.reshape(M, self.nu),
            'model_A': self.A.copy(),
            'model_B': self.B.copy(),
            'adaptation_count': self.adaptation_count,
            'avg_prediction_error': np.mean(self.prediction_errors[-10:]) if self.prediction_errors else 0.0
        }

        return u_optimal, info

    def step(self, current_state: np.ndarray, reference: np.ndarray,
             enable_adaptation: bool = True) -> Tuple[np.ndarray, Dict]:
        """
        执行一步MPC控制

        Args:
            current_state: 当前状态
            reference: 参考状态
            enable_adaptation: 是否启用自适应

        Returns:
            (control_action, info)
        """
        # 计算控制
        u, info = self.compute_control(current_state, reference)

        # 记录历史
        self.state_history.append(current_state.copy())
        self.control_history.append(u.copy())

        # 限制历史长度
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)
            self.control_history.pop(0)

        # 保存当前状态和控制
        self.current_state = current_state.copy()
        self.last_control = u.copy()

        return u, info

    def adapt_from_measurement(self, x_next_measured: np.ndarray):
        """
        从测量值适应模型

        Args:
            x_next_measured: 下一时刻的实际测量状态
        """
        if len(self.state_history) >= self.config.min_update_samples:
            # 使用最近的状态和控制进行RLS更新
            self.update_model_rls(
                self.current_state,
                self.last_control,
                x_next_measured
            )

    def get_model_parameters(self) -> Dict:
        """获取当前模型参数"""
        return {
            'A': self.A.copy(),
            'B': self.B.copy(),
            'adaptation_count': self.adaptation_count,
            'avg_prediction_error': np.mean(self.prediction_errors[-10:]) if self.prediction_errors else 0.0
        }
