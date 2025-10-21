"""
增益调度MPC（Gain-Scheduled MPC）
根据工作点切换不同的线性模型
适用于非线性系统的局部线性化控制
"""
import numpy as np
from scipy.optimize import minimize
from typing import List, Dict, Tuple, Callable, Optional
from dataclasses import dataclass

@dataclass
class OperatingPoint:
    """工作点定义"""
    name: str
    state_center: np.ndarray  # 工作点中心状态
    A: np.ndarray  # 线性化A矩阵
    B: np.ndarray  # 线性化B矩阵
    valid_range: Tuple[np.ndarray, np.ndarray]  # 有效范围 (min, max)

class GainScheduledMPC:
    """
    增益调度MPC控制器

    工作原理：
    1. 定义多个工作点
    2. 每个工作点有局部线性模型
    3. 根据当前状态选择合适的模型
    4. 平滑插值保证切换平稳
    """

    def __init__(self, operating_points: List[OperatingPoint],
                 prediction_horizon: int = 10,
                 control_horizon: int = 5,
                 dt: float = 60.0):
        """
        Args:
            operating_points: 工作点列表
            prediction_horizon: 预测时域
            control_horizon: 控制时域
            dt: 采样时间
        """
        self.operating_points = operating_points
        self.N = prediction_horizon
        self.M = control_horizon
        self.dt = dt

        # 状态和控制维度
        self.nx = operating_points[0].A.shape[0]
        self.nu = operating_points[0].B.shape[1] if len(operating_points[0].B.shape) > 1 else 1

        # 权重矩阵
        self.Q = np.eye(self.nx)
        self.R = np.eye(self.nu) * 0.1

        # 约束
        self.u_min = -10.0
        self.u_max = 10.0

        # 当前工作点
        self.current_op_index = 0
        self.current_weights = None

        # 平滑切换参数
        self.smoothing_factor = 0.1  # 模型切换平滑因子

    def _calculate_operating_point_weights(self, current_state: np.ndarray) -> np.ndarray:
        """
        计算每个工作点的权重（用于平滑插值）

        使用径向基函数（RBF）进行加权
        """
        n_points = len(self.operating_points)
        weights = np.zeros(n_points)

        for i, op in enumerate(self.operating_points):
            # 计算到工作点中心的距离
            distance = np.linalg.norm(current_state - op.state_center)

            # RBF权重（高斯核）
            sigma = 1.0  # 带宽参数
            weights[i] = np.exp(-(distance**2) / (2 * sigma**2))

        # 归一化权重
        weights /= (np.sum(weights) + 1e-10)

        return weights

    def _get_interpolated_model(self, weights: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        根据权重插值得到混合模型

        Args:
            weights: 各工作点权重

        Returns:
            (A_mixed, B_mixed)
        """
        A_mixed = np.zeros((self.nx, self.nx))
        B_mixed = np.zeros(self.operating_points[0].B.shape)

        for i, op in enumerate(self.operating_points):
            A_mixed += weights[i] * op.A
            B_mixed += weights[i] * op.B

        return A_mixed, B_mixed

    def predict_trajectory(self, x0: np.ndarray, u_sequence: np.ndarray,
                          A: np.ndarray, B: np.ndarray) -> np.ndarray:
        """
        预测未来轨迹

        Args:
            x0: 初始状态
            u_sequence: 控制序列
            A, B: 模型矩阵

        Returns:
            状态轨迹
        """
        N = len(u_sequence)
        x_traj = np.zeros((N + 1, self.nx))
        x_traj[0] = x0.flatten()

        for k in range(N):
            u_k = u_sequence[k].reshape(-1, 1)
            x_k = x_traj[k].reshape(-1, 1)
            x_next = A @ x_k + B @ u_k
            x_traj[k + 1] = x_next.flatten()

        return x_traj

    def compute_control(self, current_state: np.ndarray,
                       reference: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        计算增益调度MPC控制律

        Args:
            current_state: 当前状态
            reference: 参考状态

        Returns:
            (optimal_control, info)
        """
        # 计算工作点权重
        weights = self._calculate_operating_point_weights(current_state)

        # 平滑切换
        if self.current_weights is None:
            self.current_weights = weights
        else:
            self.current_weights = (1 - self.smoothing_factor) * self.current_weights + \
                                   self.smoothing_factor * weights

        # 获取插值模型
        A, B = self._get_interpolated_model(self.current_weights)

        # 初始控制序列
        u0 = np.zeros(self.M * self.nu)

        # 代价函数
        def cost_function(u_flat):
            u_seq = u_flat.reshape(self.M, self.nu)
            u_extended = np.vstack([u_seq, np.tile(u_seq[-1], (self.N - self.M, 1))])

            x_traj = self.predict_trajectory(current_state, u_extended, A, B)

            cost = 0.0
            for k in range(self.N + 1):
                x_error = x_traj[k].reshape(-1, 1) - reference
                cost += float(x_error.T @ self.Q @ x_error)

            for k in range(self.M):
                u_k = u_seq[k].reshape(-1, 1)
                cost += float(u_k.T @ self.R @ u_k)

            return cost

        # 约束
        bounds = [(self.u_min, self.u_max)] * (self.M * self.nu)

        # 优化求解
        result = minimize(cost_function, u0, method='SLSQP', bounds=bounds)

        u_optimal = result.x[:self.nu].reshape(-1, 1)

        # 信息
        dominant_op = np.argmax(self.current_weights)
        info = {
            'success': result.success,
            'cost': result.fun,
            'weights': self.current_weights.copy(),
            'dominant_operating_point': self.operating_points[dominant_op].name,
            'dominant_weight': self.current_weights[dominant_op],
            'model_A': A.copy(),
            'model_B': B.copy()
        }

        return u_optimal, info

    @staticmethod
    def create_canal_operating_points(width: float, length: float,
                                      slope: float, manning_n: float,
                                      dt: float) -> List[OperatingPoint]:
        """
        为明渠系统创建典型工作点

        Args:
            width, length, slope, manning_n: 明渠参数
            dt: 采样时间

        Returns:
            工作点列表
        """
        g = 9.81
        operating_points = []

        # 定义三个工作点：低水位、中水位、高水位
        depths = [0.5, 2.0, 5.0]  # 代表性水深

        for i, h in enumerate(depths):
            # 状态：[水深]
            state_center = np.array([[h]])

            # 线性化模型参数
            A = width * length
            v = (1/manning_n) * (width*h/(width+2*h))**(2/3) * slope**0.5
            c = np.sqrt(g * h)

            # 简化的线性化模型
            tau = length / v  # 时间常数
            K = length / width  # 增益

            # 离散化
            A_mat = np.array([[np.exp(-dt/tau)]])
            B_mat = np.array([[K * (1 - np.exp(-dt/tau))]])

            # 有效范围
            valid_range = (np.array([[h * 0.7]]), np.array([[h * 1.3]]))

            op = OperatingPoint(
                name=f"depth_{h:.1f}m",
                state_center=state_center,
                A=A_mat,
                B=B_mat,
                valid_range=valid_range
            )

            operating_points.append(op)

        return operating_points
