#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制系统接口

为HydroClaude模拟器提供标准化的控制接口，支持：
- PID控制
- MPC控制
- 自适应控制
- 多点协调控制

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ControlConfig:
    """控制配置基类"""
    control_interval: int = 10      # 控制周期（模拟步数）
    monitoring_points: List[int] = None  # 监测点索引
    control_points: List[int] = None     # 控制点索引（结构物位置）

    # 性能记录
    save_history: bool = True

    # 安全限制
    enable_safety_limits: bool = True


class BaseController(ABC):
    """控制器基类"""

    @abstractmethod
    def compute_control(self, measurement: np.ndarray,
                       setpoint: np.ndarray,
                       dt: float) -> np.ndarray:
        """
        计算控制输出

        Args:
            measurement: 当前测量值
            setpoint: 设定值
            dt: 时间间隔

        Returns:
            控制输出
        """
        pass

    @abstractmethod
    def reset(self):
        """重置控制器状态"""
        pass


class ControlLoop:
    """
    控制循环管理器

    将控制器与水力模拟器集成，实现闭环控制
    """

    def __init__(self,
                 solver,
                 controller: BaseController,
                 config: ControlConfig):
        """
        初始化控制循环

        Args:
            solver: 水力求解器
            controller: 控制器实例
            config: 控制配置
        """
        self.solver = solver
        self.controller = controller
        self.config = config

        # 历史记录
        self.time_history = []
        self.measurement_history = []
        self.setpoint_history = []
        self.control_history = []
        self.error_history = []

        # 统计
        self.step_count = 0
        self.control_count = 0

    def get_measurement(self) -> np.ndarray:
        """
        从求解器获取测量值

        Returns:
            测量值数组
        """
        if self.config.monitoring_points is None:
            # 默认：所有点的水深
            return self.solver.h.copy()
        else:
            # 指定监测点
            return self.solver.h[self.config.monitoring_points].copy()

    def apply_control(self, control_action: np.ndarray):
        """
        应用控制动作到求解器

        Args:
            control_action: 控制动作（如闸门开度、泵站流量等）
        """
        if self.config.control_points is None:
            return

        # 根据结构物类型应用控制
        for i, (idx, control_val) in enumerate(zip(self.config.control_points, control_action)):
            if hasattr(self.solver, 'structure_objects') and self.solver.structure_objects:
                # 找到对应的结构物
                structure = self.solver.structure_objects[i]

                # 根据结构物类型设置控制参数
                if hasattr(structure, 'opening'):
                    # 闸门：设置开度
                    structure.opening = float(control_val)
                elif hasattr(structure, 'rated_flow'):
                    # 泵站：设置流量
                    structure.rated_flow = float(control_val)

    def step(self, current_time: float, dt: float, setpoint: np.ndarray) -> Dict:
        """
        执行一步控制

        Args:
            current_time: 当前时间
            dt: 时间步长
            setpoint: 设定值

        Returns:
            控制信息字典
        """
        # 获取测量值
        measurement = self.get_measurement()

        # 计算控制输出
        control_action = self.controller.compute_control(measurement, setpoint, dt)

        # 应用控制
        self.apply_control(control_action)

        # 计算误差
        if np.isscalar(setpoint):
            error = setpoint - measurement
        else:
            error = np.array(setpoint) - measurement

        # 记录历史
        if self.config.save_history:
            self.time_history.append(current_time)
            self.measurement_history.append(measurement.copy())
            # 处理标量setpoint
            if np.isscalar(setpoint):
                self.setpoint_history.append(setpoint)
            else:
                self.setpoint_history.append(np.array(setpoint).copy())
            self.control_history.append(control_action.copy())
            # 处理标量error
            if np.isscalar(error):
                self.error_history.append(error)
            else:
                self.error_history.append(error.copy())

        self.control_count += 1

        return {
            'measurement': measurement,
            'setpoint': setpoint,
            'control': control_action,
            'error': error,
            'time': current_time
        }

    def should_control(self, step: int) -> bool:
        """
        判断是否应该执行控制

        Args:
            step: 当前仿真步数

        Returns:
            是否执行控制
        """
        return step % self.config.control_interval == 0

    def get_performance_metrics(self) -> Dict:
        """
        计算控制性能指标

        Returns:
            性能指标字典
        """
        if not self.error_history:
            return {}

        errors = np.array(self.error_history)

        # MAE - 平均绝对误差
        mae = np.mean(np.abs(errors))

        # RMSE - 均方根误差
        rmse = np.sqrt(np.mean(errors**2))

        # 最大误差
        max_error = np.max(np.abs(errors))

        # 稳态误差（最后10%）
        n_steady = max(int(len(errors) * 0.1), 10)
        steady_errors = errors[-n_steady:]
        steady_state_error = np.mean(np.abs(steady_errors))

        # ISE - 误差平方积分
        ise = np.sum(errors**2)

        # IAE - 误差绝对值积分
        iae = np.sum(np.abs(errors))

        return {
            'mae': float(mae),
            'rmse': float(rmse),
            'max_error': float(max_error),
            'steady_state_error': float(steady_state_error),
            'ise': float(ise),
            'iae': float(iae),
            'control_count': self.control_count
        }

    def reset(self):
        """重置控制循环"""
        self.controller.reset()
        self.time_history.clear()
        self.measurement_history.clear()
        self.setpoint_history.clear()
        self.control_history.clear()
        self.error_history.clear()
        self.step_count = 0
        self.control_count = 0


class PIDControlWrapper(BaseController):
    """PID控制器包装器"""

    def __init__(self, pid_controllers: List):
        """
        Args:
            pid_controllers: PID控制器列表（每个控制点一个）
        """
        self.controllers = pid_controllers

    def compute_control(self, measurement: np.ndarray,
                       setpoint,
                       dt: float) -> np.ndarray:
        """计算控制输出"""
        n_control = len(self.controllers)
        control = np.zeros(n_control)

        # 将setpoint转换为数组
        if np.isscalar(setpoint):
            setpoint_array = np.full(n_control, setpoint)
        else:
            setpoint_array = np.array(setpoint)

        for i, controller in enumerate(self.controllers):
            # 设置目标
            if i < len(setpoint_array):
                controller.set_setpoint(float(setpoint_array[i]))

            # 计算控制
            if i < len(measurement):
                control[i] = controller.compute(float(measurement[i]), dt)

        return control

    def reset(self):
        """重置所有控制器"""
        for controller in self.controllers:
            controller.reset()


class MPCControlWrapper(BaseController):
    """MPC控制器包装器"""

    def __init__(self, mpc_controller):
        """
        Args:
            mpc_controller: MPC控制器实例（如AdaptiveMPC）
        """
        self.mpc = mpc_controller

    def compute_control(self, measurement: np.ndarray,
                       setpoint,
                       dt: float) -> np.ndarray:
        """计算控制输出"""
        # 确保是列向量
        x = measurement.reshape(-1, 1)

        # 处理标量或数组setpoint
        if np.isscalar(setpoint):
            ref = np.array([[setpoint]])
        else:
            ref = np.array(setpoint).reshape(-1, 1)

        # MPC计算
        u, info = self.mpc.step(x, ref)

        return u.flatten()

    def reset(self):
        """重置MPC"""
        # MPC通常不需要reset，但可以清空历史
        if hasattr(self.mpc, 'state_history'):
            self.mpc.state_history.clear()
        if hasattr(self.mpc, 'control_history'):
            self.mpc.control_history.clear()


def create_control_loop(solver,
                       controller_type: str,
                       controller_config: Dict,
                       control_config: ControlConfig) -> ControlLoop:
    """
    工厂函数：创建控制循环

    Args:
        solver: 水力求解器
        controller_type: 控制器类型 ('pid', 'mpc', 'adaptive_mpc')
        controller_config: 控制器配置
        control_config: 控制循环配置

    Returns:
        ControlLoop实例
    """
    if controller_type == 'pid':
        from control.pid_controller import PIDController, PIDConfig

        # 创建PID控制器
        n_control = len(control_config.control_points) if control_config.control_points else 1
        controllers = []

        for i in range(n_control):
            pid_cfg = PIDConfig(**controller_config)
            pid = PIDController(pid_cfg, name=f"PID_{i}")
            controllers.append(pid)

        controller = PIDControlWrapper(controllers)

    elif controller_type == 'mpc' or controller_type == 'adaptive_mpc':
        from control.adaptive_mpc import AdaptiveMPC, AdaptiveMPCConfig

        # 提取初始模型矩阵
        if 'initial_A' in controller_config and 'initial_B' in controller_config:
            A = np.array(controller_config['initial_A'])
            B = np.array(controller_config['initial_B'])
        else:
            # 默认单输入单输出系统
            A = np.array([[0.9]])
            B = np.array([[0.1]])

        # 处理权重矩阵：从标量转换为矩阵
        nx = A.shape[0]
        nu = B.shape[1] if len(B.shape) > 1 else 1

        Q = None
        R = None
        if 'Q_weight' in controller_config:
            Q = np.eye(nx) * controller_config['Q_weight']
        if 'R_weight' in controller_config:
            R = np.eye(nu) * controller_config['R_weight']

        # 创建MPC配置（排除initial_A, initial_B, Q_weight, R_weight）
        mpc_config_dict = {k: v for k, v in controller_config.items()
                          if k not in ['initial_A', 'initial_B', 'Q_weight', 'R_weight']}

        # 添加权重矩阵
        if Q is not None:
            mpc_config_dict['Q'] = Q
        if R is not None:
            mpc_config_dict['R'] = R

        mpc_cfg = AdaptiveMPCConfig(**mpc_config_dict)
        mpc = AdaptiveMPC(mpc_cfg, A, B)
        controller = MPCControlWrapper(mpc)

    else:
        raise ValueError(f"Unknown controller type: {controller_type}")

    return ControlLoop(solver, controller, control_config)


if __name__ == "__main__":
    print("控制系统接口模块")
    print("请通过create_control_loop()使用此模块")
