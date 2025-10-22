#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YAML配置文件支持

允许用户通过YAML文件配置系统参数，包括：
- 水库参数
- 渠道参数
- 控制器参数
- 优化参数
- 拓扑结构

作者: Claude
日期: 2025-10-22
"""

import yaml
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import numpy as np


@dataclass
class ReservoirConfig:
    """水库配置"""
    id: str
    total_capacity: float  # m³
    min_level: float  # m
    normal_level: float  # m
    flood_level: float  # m
    design_level: float  # m
    dead_storage: float = 0.0  # m³
    turbine_capacity: float = 0.0  # MW
    turbine_efficiency: float = 0.9
    ecological_flow: float = 0.0  # m³/s
    initial_storage: Optional[float] = None  # m³（默认=normal对应的库容）

    def __post_init__(self):
        """验证参数合法性"""
        if self.min_level >= self.normal_level:
            raise ValueError(f"{self.id}: min_level必须小于normal_level")
        if self.normal_level >= self.flood_level:
            raise ValueError(f"{self.id}: normal_level必须小于flood_level")
        if self.flood_level >= self.design_level:
            raise ValueError(f"{self.id}: flood_level必须小于design_level")
        if self.total_capacity <= 0:
            raise ValueError(f"{self.id}: total_capacity必须大于0")


@dataclass
class CanalConfig:
    """明渠配置"""
    id: str
    length: float  # m
    nx: int  # 网格点数
    width: float  # m
    slope: float  # S0
    roughness: float  # Manning's n
    initial_depth: Optional[float] = None  # m
    initial_flow: Optional[float] = None  # m³/s

    def __post_init__(self):
        """验证参数合法性"""
        if self.length <= 0:
            raise ValueError(f"{self.id}: length必须大于0")
        if self.nx < 3:
            raise ValueError(f"{self.id}: nx必须至少为3")
        if self.width <= 0:
            raise ValueError(f"{self.id}: width必须大于0")
        if self.slope <= 0:
            raise ValueError(f"{self.id}: slope必须大于0")
        if self.roughness <= 0:
            raise ValueError(f"{self.id}: roughness必须大于0")


@dataclass
class GateConfig:
    """闸门配置"""
    id: str
    position: float  # m
    width: float  # m
    opening: float  # m (或时间函数)
    discharge_coefficient: float = 0.6
    gate_type: str = "sluice"  # sluice, radial, vertical

    def __post_init__(self):
        """验证参数合法性"""
        if self.position < 0:
            raise ValueError(f"{self.id}: position必须非负")
        if self.width <= 0:
            raise ValueError(f"{self.id}: width必须大于0")
        if self.opening < 0:
            raise ValueError(f"{self.id}: opening必须非负")
        if not (0 < self.discharge_coefficient <= 1.0):
            raise ValueError(f"{self.id}: discharge_coefficient必须在(0, 1]范围内")


@dataclass
class PIDConfig:
    """PID控制器配置"""
    id: str
    Kp: float  # 比例系数
    Ki: float  # 积分系数
    Kd: float  # 微分系数
    setpoint: float  # 目标值
    output_min: float = 0.0  # 输出下限
    output_max: float = 1.0  # 输出上限
    anti_windup: bool = True  # 抗积分饱和

    def __post_init__(self):
        """验证参数合法性"""
        if self.output_min >= self.output_max:
            raise ValueError(f"{self.id}: output_min必须小于output_max")


@dataclass
class TopologyConnection:
    """拓扑连接配置"""
    from_node: str
    to_node: str
    travel_time: float = 0.0  # 秒
    connection_type: str = "direct"  # direct, canal, pipe

    def __post_init__(self):
        """验证参数合法性"""
        if self.travel_time < 0:
            raise ValueError(f"travel_time必须非负")


@dataclass
class SystemConfig:
    """
    系统总配置

    从YAML文件加载完整的系统配置
    """
    name: str
    description: str = ""
    reservoirs: List[ReservoirConfig] = field(default_factory=list)
    canals: List[CanalConfig] = field(default_factory=list)
    gates: List[GateConfig] = field(default_factory=list)
    controllers: List[PIDConfig] = field(default_factory=list)
    topology: List[TopologyConnection] = field(default_factory=list)
    optimization: Dict[str, Any] = field(default_factory=dict)
    simulation: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, filepath: Union[str, Path]) -> 'SystemConfig':
        """
        从YAML文件加载配置

        Args:
            filepath: YAML文件路径

        Returns:
            SystemConfig: 系统配置对象

        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML格式错误
            ValueError: 配置参数错误
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"配置文件不存在: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError(f"配置文件为空: {filepath}")

        return cls._parse(data)

    @classmethod
    def _parse(cls, data: Dict) -> 'SystemConfig':
        """解析YAML数据为配置对象"""
        # 系统基本信息
        name = data.get('name', 'Unnamed System')
        description = data.get('description', '')

        # 解析水库配置
        reservoirs = []
        for res_data in data.get('reservoirs', []):
            reservoirs.append(ReservoirConfig(**res_data))

        # 解析渠道配置
        canals = []
        for canal_data in data.get('canals', []):
            canals.append(CanalConfig(**canal_data))

        # 解析闸门配置
        gates = []
        for gate_data in data.get('gates', []):
            gates.append(GateConfig(**gate_data))

        # 解析控制器配置
        controllers = []
        for ctrl_data in data.get('controllers', []):
            controllers.append(PIDConfig(**ctrl_data))

        # 解析拓扑连接
        topology = []
        for conn_data in data.get('topology', []):
            topology.append(TopologyConnection(**conn_data))

        # 其他配置
        optimization = data.get('optimization', {})
        simulation = data.get('simulation', {})

        return cls(
            name=name,
            description=description,
            reservoirs=reservoirs,
            canals=canals,
            gates=gates,
            controllers=controllers,
            topology=topology,
            optimization=optimization,
            simulation=simulation
        )

    def to_yaml(self, filepath: Union[str, Path]):
        """
        保存配置到YAML文件

        Args:
            filepath: 输出文件路径
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 转换为字典
        data = {
            'name': self.name,
            'description': self.description,
            'reservoirs': [asdict(r) for r in self.reservoirs],
            'canals': [asdict(c) for c in self.canals],
            'gates': [asdict(g) for g in self.gates],
            'controllers': [asdict(ctrl) for ctrl in self.controllers],
            'topology': [asdict(t) for t in self.topology],
            'optimization': self.optimization,
            'simulation': self.simulation
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def create_system(self):
        """
        根据配置创建实际系统对象

        Returns:
            系统对象（具体类型取决于配置）

        注意: 这是一个工厂方法，根据配置创建合适的系统对象
        """
        # TODO: 实现系统创建逻辑
        # 这需要根据具体的系统类型（水库、渠道、混合等）创建相应对象
        raise NotImplementedError("System creation not yet implemented")

    def validate(self) -> List[str]:
        """
        验证配置完整性和一致性

        Returns:
            List[str]: 验证错误列表（空列表表示验证通过）
        """
        errors = []

        # 检查拓扑连接的节点是否存在
        all_nodes = set()
        all_nodes.update(r.id for r in self.reservoirs)
        all_nodes.update(c.id for c in self.canals)

        for conn in self.topology:
            if conn.from_node not in all_nodes:
                errors.append(f"拓扑连接错误: 节点'{conn.from_node}'不存在")
            if conn.to_node not in all_nodes:
                errors.append(f"拓扑连接错误: 节点'{conn.to_node}'不存在")

        # 检查闸门位置是否在对应渠道范围内
        canal_dict = {c.id: c for c in self.canals}
        for gate in self.gates:
            # 假设闸门id格式为 "canal_id_gate_name"
            # 或通过其他方式关联到渠道
            # 这里简化处理
            pass

        # 检查控制器setpoint合理性
        for ctrl in self.controllers:
            if ctrl.setpoint < ctrl.output_min or ctrl.setpoint > ctrl.output_max:
                errors.append(f"控制器'{ctrl.id}': setpoint超出输出范围")

        return errors

    def summary(self) -> str:
        """
        生成配置摘要

        Returns:
            str: 配置摘要文本
        """
        lines = []
        lines.append(f"系统配置: {self.name}")
        lines.append(f"描述: {self.description}")
        lines.append("")
        lines.append(f"组件数量:")
        lines.append(f"  - 水库: {len(self.reservoirs)}")
        lines.append(f"  - 渠道: {len(self.canals)}")
        lines.append(f"  - 闸门: {len(self.gates)}")
        lines.append(f"  - 控制器: {len(self.controllers)}")
        lines.append(f"  - 拓扑连接: {len(self.topology)}")
        lines.append("")

        if self.reservoirs:
            lines.append("水库列表:")
            for res in self.reservoirs:
                lines.append(f"  - {res.id}: 总库容{res.total_capacity/1e6:.2f}百万m³, "
                           f"装机{res.turbine_capacity:.1f}MW")

        if self.canals:
            lines.append("")
            lines.append("渠道列表:")
            for canal in self.canals:
                lines.append(f"  - {canal.id}: 长度{canal.length}m, 宽度{canal.width}m, "
                           f"{canal.nx}个节点")

        return "\n".join(lines)


def create_example_config(filepath: str = "config/example_system.yaml"):
    """
    创建示例配置文件

    Args:
        filepath: 输出文件路径
    """
    example_config = SystemConfig(
        name="三级梯级水电站示例",
        description="包含3个水库、2条渠道和2个闸门的梯级系统",
        reservoirs=[
            ReservoirConfig(
                id="R1_upstream",
                total_capacity=100e6,  # 100百万m³
                min_level=200.0,
                normal_level=260.0,
                flood_level=265.0,
                design_level=270.0,
                turbine_capacity=200.0,  # 200 MW
                ecological_flow=50.0  # 50 m³/s
            ),
            ReservoirConfig(
                id="R2_middle",
                total_capacity=50e6,
                min_level=150.0,
                normal_level=180.0,
                flood_level=185.0,
                design_level=190.0,
                turbine_capacity=100.0,
                ecological_flow=30.0
            ),
            ReservoirConfig(
                id="R3_downstream",
                total_capacity=30e6,
                min_level=100.0,
                normal_level=120.0,
                flood_level=125.0,
                design_level=130.0,
                turbine_capacity=50.0,
                ecological_flow=20.0
            ),
        ],
        canals=[
            CanalConfig(
                id="C1_R1_to_R2",
                length=5000.0,
                nx=51,
                width=15.0,
                slope=0.001,
                roughness=0.025
            ),
            CanalConfig(
                id="C2_R2_to_R3",
                length=3000.0,
                nx=31,
                width=12.0,
                slope=0.0008,
                roughness=0.025
            ),
        ],
        gates=[
            GateConfig(
                id="Gate_R1",
                position=0.0,  # 在R1出口
                width=10.0,
                opening=5.0,
                discharge_coefficient=0.6
            ),
            GateConfig(
                id="Gate_R2",
                position=0.0,  # 在R2出口
                width=8.0,
                opening=4.0,
                discharge_coefficient=0.6
            ),
        ],
        controllers=[
            PIDConfig(
                id="PID_R1_level",
                Kp=0.5,
                Ki=0.1,
                Kd=0.05,
                setpoint=260.0,  # 维持正常水位
                output_min=0.0,
                output_max=1.0
            ),
        ],
        topology=[
            TopologyConnection(
                from_node="R1_upstream",
                to_node="C1_R1_to_R2",
                travel_time=0,
                connection_type="direct"
            ),
            TopologyConnection(
                from_node="C1_R1_to_R2",
                to_node="R2_middle",
                travel_time=7200,  # 2小时
                connection_type="direct"
            ),
            TopologyConnection(
                from_node="R2_middle",
                to_node="C2_R2_to_R3",
                travel_time=0,
                connection_type="direct"
            ),
            TopologyConnection(
                from_node="C2_R2_to_R3",
                to_node="R3_downstream",
                travel_time=3600,  # 1小时
                connection_type="direct"
            ),
        ],
        optimization={
            'objective': 'maximize_power',
            'constraints': {
                'ecological_flow': True,
                'flood_control': True
            },
            'algorithm': 'dynamic_programming',
            'horizon': 24  # 小时
        },
        simulation={
            'duration': 86400,  # 1天（秒）
            'timestep': 300,  # 5分钟
            'solver': 'implicit'
        }
    )

    example_config.to_yaml(filepath)
    print(f"示例配置文件已创建: {filepath}")

    return example_config


def main():
    """测试配置模块"""
    print("="*80)
    print("YAML配置模块测试")
    print("="*80)
    print()

    # 创建示例配置
    print("创建示例配置文件...")
    config = create_example_config()
    print()

    # 打印摘要
    print(config.summary())
    print()

    # 验证配置
    print("验证配置...")
    errors = config.validate()
    if errors:
        print("发现错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ 配置验证通过")
    print()

    # 重新加载测试
    print("测试从YAML文件加载...")
    loaded_config = SystemConfig.from_yaml("config/example_system.yaml")
    print(f"✓ 成功加载配置: {loaded_config.name}")
    print(f"  包含 {len(loaded_config.reservoirs)} 个水库")
    print(f"  包含 {len(loaded_config.canals)} 条渠道")
    print()

    print("="*80)
    print("测试完成!")
    print("="*80)


if __name__ == "__main__":
    main()
