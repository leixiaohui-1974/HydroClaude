"""
水质模拟模块

本模块提供管网水质模拟功能，包括：
- 物质输运
- 反应动力学
- 混合与衰减
- 水龄追踪

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from enum import Enum


class ReactionType(Enum):
    """反应类型"""
    ZERO_ORDER = "zero"  # 零级反应
    FIRST_ORDER = "first"  # 一级反应
    LIMITING = "limiting"  # 限制性反应


class WaterQualitySpecies(Enum):
    """水质组分"""
    CHLORINE = "chlorine"  # 余氯
    FLUORIDE = "fluoride"  # 氟化物
    AGE = "age"  # 水龄
    TRACE = "trace"  # 示踪剂
    GENERIC = "generic"  # 通用物质


@dataclass
class ReactionConfig:
    """反应配置"""
    reaction_type: ReactionType
    bulk_coefficient: float = 0.0  # 主体反应系数 (1/day)
    wall_coefficient: float = 0.0  # 管壁反应系数 (m/day)
    limiting_concentration: float = 0.0  # 限制浓度


class WaterQualitySimulator:
    """
    水质模拟器

    使用一维对流-反应-扩散方程模拟管网水质
    """

    def __init__(self, nx: int, length: float, diameter: float):
        """
        初始化水质模拟器

        参数：
            nx: 空间网格数
            length: 管道长度 (m)
            diameter: 管道直径 (m)
        """
        self.nx = nx
        self.length = length
        self.diameter = diameter
        self.dx = length / (nx - 1)

        # 网格坐标
        self.x = np.linspace(0, length, nx)

        # 水质浓度 (mg/L)
        self.concentration = np.zeros(nx)

        # 水龄 (hours)
        self.age = np.zeros(nx)

        # 流速 (m/s)
        self.velocity = np.zeros(nx)

        # 反应配置
        self.reactions: Dict[str, ReactionConfig] = {}

    def set_initial_concentration(self, concentration: float):
        """设置初始浓度"""
        self.concentration[:] = concentration

    def set_velocity(self, velocity: float):
        """设置管道流速"""
        self.velocity[:] = velocity

    def add_reaction(self, species: str, config: ReactionConfig):
        """添加反应配置"""
        self.reactions[species] = config

    def compute_bulk_decay(self, concentration: np.ndarray, dt: float,
                          config: ReactionConfig) -> np.ndarray:
        """
        计算主体反应衰减

        参数：
            concentration: 当前浓度
            dt: 时间步长 (s)
            config: 反应配置

        返回：
            衰减后的浓度
        """
        kb = config.bulk_coefficient / 86400.0  # 转换为 1/s

        if config.reaction_type == ReactionType.FIRST_ORDER:
            # 一级反应: dC/dt = -kb * C
            decay_factor = np.exp(kb * dt)
            return concentration * decay_factor

        elif config.reaction_type == ReactionType.ZERO_ORDER:
            # 零级反应: dC/dt = kb
            return concentration + kb * dt

        elif config.reaction_type == ReactionType.LIMITING:
            # 限制性反应: dC/dt = kb * (Cl - C) * C / (Kl + C)
            Cl = config.limiting_concentration
            Kl = 1.0  # 半饱和常数
            rate = kb * (Cl - concentration) * concentration / (Kl + concentration)
            return concentration + rate * dt

        return concentration

    def compute_wall_decay(self, concentration: np.ndarray, dt: float,
                          config: ReactionConfig) -> np.ndarray:
        """
        计算管壁反应衰减

        参数：
            concentration: 当前浓度
            dt: 时间步长 (s)
            config: 反应配置
        """
        kw = config.wall_coefficient / 86400.0  # 转换为 m/s

        if kw == 0:
            return concentration

        # 管壁反应：dC/dt = -kw * (4/D) * C
        # 4/D 是表面积/体积比
        decay_rate = kw * (4.0 / self.diameter)
        decay_factor = np.exp(-decay_rate * dt)

        return concentration * decay_factor

    def advect_upwind(self, concentration: np.ndarray, dt: float) -> np.ndarray:
        """
        使用迎风格式计算对流

        参数：
            concentration: 当前浓度
            dt: 时间步长 (s)

        返回：
            对流后的浓度
        """
        new_concentration = concentration.copy()

        # CFL数
        cfl = self.velocity[0] * dt / self.dx

        if cfl > 1.0:
            print(f"警告: CFL数 = {cfl:.3f} > 1, 可能不稳定")

        # 一阶迎风格式
        for i in range(1, self.nx):
            if self.velocity[i] > 0:
                # 向前流动
                new_concentration[i] = (concentration[i] -
                    cfl * (concentration[i] - concentration[i-1]))

        return new_concentration

    def step(self, dt: float, inflow_concentration: float = None):
        """
        推进一个时间步

        参数：
            dt: 时间步长 (s)
            inflow_concentration: 入口浓度 (如果为None，使用边界值)
        """
        # 1. 对流
        self.concentration = self.advect_upwind(self.concentration, dt)

        # 2. 主体反应
        for species, config in self.reactions.items():
            self.concentration = self.compute_bulk_decay(
                self.concentration, dt, config
            )

            # 3. 管壁反应
            self.concentration = self.compute_wall_decay(
                self.concentration, dt, config
            )

        # 4. 边界条件（入口）
        if inflow_concentration is not None:
            self.concentration[0] = inflow_concentration

        # 5. 更新水龄
        self.age += dt / 3600.0  # 转换为小时

    def get_average_concentration(self) -> float:
        """获取平均浓度"""
        return np.mean(self.concentration)

    def get_outlet_concentration(self) -> float:
        """获取出口浓度"""
        return self.concentration[-1]


@dataclass
class NetworkNode:
    """管网节点"""
    id: str
    elevation: float = 0.0
    demand: float = 0.0  # 需水量 (m³/s)
    concentration: float = 0.0  # 浓度 (mg/L)


@dataclass
class NetworkPipe:
    """管网管道"""
    id: str
    from_node: str
    to_node: str
    length: float
    diameter: float
    roughness: float = 0.013
    flow: float = 0.0  # 流量 (m³/s)


class NetworkWaterQuality:
    """
    管网水质模拟

    简化的管网水质模型，用于演示
    """

    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.pipes: Dict[str, NetworkPipe] = {}
        self.pipe_simulators: Dict[str, WaterQualitySimulator] = {}

        # 全局反应配置
        self.reaction_config: Optional[ReactionConfig] = None

    def add_node(self, node: NetworkNode):
        """添加节点"""
        self.nodes[node.id] = node

    def add_pipe(self, pipe: NetworkPipe):
        """添加管道"""
        self.pipes[pipe.id] = pipe

        # 创建管道水质模拟器
        simulator = WaterQualitySimulator(
            nx=20,
            length=pipe.length,
            diameter=pipe.diameter
        )

        # 设置流速
        area = np.pi * (pipe.diameter / 2) ** 2
        velocity = pipe.flow / area if area > 0 else 0.0
        simulator.set_velocity(velocity)

        self.pipe_simulators[pipe.id] = simulator

    def set_reaction(self, reaction_config: ReactionConfig):
        """设置反应配置"""
        self.reaction_config = reaction_config

        # 应用到所有管道
        for simulator in self.pipe_simulators.values():
            simulator.add_reaction("main", reaction_config)

    def set_source_quality(self, node_id: str, concentration: float):
        """设置源水质"""
        if node_id in self.nodes:
            self.nodes[node_id].concentration = concentration

    def simulate(self, duration: float, dt: float = 300.0):
        """
        模拟管网水质

        参数：
            duration: 模拟时长 (s)
            dt: 时间步长 (s)
        """
        n_steps = int(duration / dt)

        print(f"开始管网水质模拟...")
        print(f"  模拟时长: {duration/3600:.1f} hours")
        print(f"  时间步长: {dt:.0f} s")
        print(f"  总步数: {n_steps}")

        for step in range(n_steps):
            # 更新每个管道的水质
            for pipe_id, pipe in self.pipes.items():
                simulator = self.pipe_simulators[pipe_id]

                # 获取上游节点浓度作为入口边界条件
                from_node = self.nodes[pipe.from_node]
                inflow_conc = from_node.concentration

                # 推进时间步
                simulator.step(dt, inflow_concentration=inflow_conc)

                # 更新下游节点浓度（简化处理）
                to_node = self.nodes[pipe.to_node]
                outlet_conc = simulator.get_outlet_concentration()
                to_node.concentration = outlet_conc

            if (step + 1) % 10 == 0:
                print(f"  步数 {step+1}/{n_steps} 完成")

        print("模拟完成！")

    def get_results(self) -> Dict:
        """获取模拟结果"""
        results = {
            'nodes': {},
            'pipes': {}
        }

        for node_id, node in self.nodes.items():
            results['nodes'][node_id] = {
                'concentration': node.concentration
            }

        for pipe_id, simulator in self.pipe_simulators.items():
            results['pipes'][pipe_id] = {
                'average_concentration': simulator.get_average_concentration(),
                'outlet_concentration': simulator.get_outlet_concentration(),
                'average_age': np.mean(simulator.age)
            }

        return results


# 导出
__all__ = [
    'WaterQualitySimulator',
    'NetworkWaterQuality',
    'NetworkNode',
    'NetworkPipe',
    'ReactionConfig',
    'ReactionType',
    'WaterQualitySpecies',
]
