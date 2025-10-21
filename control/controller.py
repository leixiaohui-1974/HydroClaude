import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List
from scipy.optimize import minimize, linprog
from physics.model import PhysicsModel
from core.base import HydraulicComponent
from core.control_device import Pump

class Controller(ABC):
    """控制器抽象基类"""

    @abstractmethod
    def compute(self, state: np.ndarray, reference: np.ndarray,
                dt: float) -> np.ndarray:
        """计算控制量"""
        pass

    @abstractmethod
    def reset(self):
        """重置控制器"""
        pass

class PIDController(Controller):
    """PID控制器"""

    def __init__(self, Kp: float, Ki: float, Kd: float,
                 output_limits: Tuple[float, float] = (0, 10)):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.output_min, self.output_max = output_limits
        self.integral = 0.0
        self.last_error = 0.0

    def compute(self, state: np.ndarray, reference: np.ndarray,
                dt: float) -> np.ndarray:
        """PID计算"""
        error = reference - state

        # 比例
        P = self.Kp * error

        # 积分
        self.integral += error * dt
        self.integral = np.clip(self.integral, -10, 10)
        I = self.Ki * self.integral

        # 微分
        D = self.Kd * (error - self.last_error) / (dt + 1e-6)
        self.last_error = error

        # 输出
        output = P + I + D
        output = np.clip(output, self.output_min, self.output_max)

        return output

    def reset(self):
        self.integral = 0.0
        self.last_error = 0.0

class MPCController(Controller):
    """模型预测控制器"""

    def __init__(self, model: PhysicsModel,
                 prediction_horizon: int = 10,
                 control_horizon: int = 3,
                 weights: Dict[str, float] = None):
        self.model = model
        self.P = prediction_horizon
        self.M = control_horizon
        self.weights = weights or {'tracking': 1.0, 'control': 0.1, 'slack': 100.0}

    def compute(self, state: np.ndarray, reference: np.ndarray,
                dt: float) -> np.ndarray:
        """MPC优化计算"""
        n_states = len(state)
        n_controls = n_states

        n_vars = self.M * n_controls + n_states

        def objective(x):
            dU = x[:self.M * n_controls].reshape(self.M, n_controls)
            slack = x[self.M * n_controls:]

            cost = 0.0
            current_state = state.copy()
            current_control = np.zeros(n_controls)

            for k in range(self.P):
                if k < self.M:
                    current_control += dU[k]

                A, B, _ = self.model.get_matrices()
                current_state = A @ current_state + B @ current_control

                tracking_error = current_state - reference
                cost += self.weights['tracking'] * np.sum(tracking_error**2)

                if k < self.M:
                    cost += self.weights['control'] * np.sum(dU[k]**2)

            cost += self.weights['slack'] * np.sum(slack**2)

            return cost

        bounds = []
        for _ in range(self.M * n_controls):
            bounds.append((-2.0, 2.0))
        for _ in range(n_states):
            bounds.append((0, 10))

        x0 = np.zeros(n_vars)

        result = minimize(objective, x0, method='SLSQP', bounds=bounds,
                         options={'maxiter': 100, 'ftol': 1e-4})

        if result.success:
            dU_optimal = result.x[:n_controls]
            return dU_optimal
        else:
            return np.zeros(n_controls)

    def reset(self):
        pass
