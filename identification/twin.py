import numpy as np
from typing import List, Dict, Callable
from scipy.optimize import least_squares
from core.base import HydraulicComponent
from core.states import ComponentState

class OnlineIdentification:
    """在线辨识算法（递推最小二乘）"""

    def __init__(self, n_params: int, forgetting_factor: float = 0.98):
        self.n = n_params
        self.lambda_f = forgetting_factor  # 遗忘因子

        # 初始化
        self.theta = np.zeros(n_params)  # 参数估计
        self.P = np.eye(n_params) * 1000  # 协方差矩阵

        self.history = {
            'theta': [],
            'innovation': []
        }

    def update(self, phi: np.ndarray, y: float) -> np.ndarray:
        """
        递推更新
        Args:
            phi: 回归向量 (n,)
            y: 测量输出
        Returns:
            更新后的参数估计
        """
        # 预测输出
        y_pred = phi @ self.theta
        innovation = y - y_pred

        # 增益计算
        K = self.P @ phi / (self.lambda_f + phi @ self.P @ phi)

        # 参数更新
        self.theta += K * innovation

        # 协方差更新
        self.P = (self.P - np.outer(K, phi) @ self.P) / self.lambda_f

        # 记录
        self.history['theta'].append(self.theta.copy())
        self.history['innovation'].append(innovation)

        return self.theta

class OfflineIdentification:
    """离线辨识算法（批量最小二乘）"""

    def __init__(self):
        self.history = {
            'params': [],
            'cost': [],
            'residuals': []
        }

    def identify(self, measurements: np.ndarray,
                inputs: np.ndarray,
                model_func: Callable,
                initial_params: np.ndarray) -> np.ndarray:
        """
        批量辨识
        Args:
            measurements: 测量数据 (n_samples,)
            inputs: 输入数据 (n_samples, n_inputs)
            model_func: 模型函数 y = f(x, params)
            initial_params: 初始参数
        Returns:
            优化后的参数
        """
        def residual_func(params):
            predictions = np.array([model_func(u, params) for u in inputs])
            residuals = measurements - predictions
            return residuals

        # 最小二乘优化
        result = least_squares(residual_func, initial_params,
                              method='trf', verbose=0)

        if result.success:
            optimal_params = result.x
            self.history['params'].append(optimal_params)
            self.history['cost'].append(result.cost)
            self.history['residuals'].append(result.fun)

            return optimal_params
        else:
            return initial_params

class DigitalTwin:
    """数字孪生"""

    def __init__(self, components: List[HydraulicComponent]):
        self.components = {comp.name: comp for comp in components}
        self.state_history = []
        self.parameter_history = []

    def update(self, dt: float, inputs: Dict[str, Dict]) -> Dict[str, ComponentState]:
        """更新孪生状态（降阶模型）"""
        states = {}
        for name, comp in self.components.items():
            comp_inputs = inputs.get(name, {})
            state = comp.update_reduced_order(dt, comp_inputs)
            states[name] = state

        self.state_history.append(states)
        return states

    def synchronize(self, measurements: Dict[str, float],
                   identifier: OnlineIdentification,
                   component_name: str):
        """与本体同步（在线辨识）"""
        comp = self.components[component_name]

        # 构建回归向量（简化：使用当前状态）
        phi = comp.state.to_array()[:identifier.n]

        # 测量值
        y = measurements.get(component_name, comp.state.volume)

        # 在线辨识
        new_params = identifier.update(phi, y)

        # 更新孪生参数
        param_names = list(comp.get_identifiable_parameters().keys())[:identifier.n]
        for i, param_name in enumerate(param_names):
            comp.parameters[param_name] = new_params[i]

        self.parameter_history.append(comp.parameters.copy())

    def get_prediction(self, horizon: int, dt: float,
                      control_sequence: np.ndarray) -> np.ndarray:
        """预测未来状态"""
        predictions = []

        # 保存当前状态
        saved_states = {name: comp.state.to_array()
                       for name, comp in self.components.items()}

        # 前向预测
        for k in range(horizon):
            inputs = {}  # 简化：需要根据control_sequence构建
            states = self.update(dt, inputs)
            predictions.append([s.volume for s in states.values()])

        # 恢复状态
        for name, comp in self.components.items():
            pass

        return np.array(predictions)
