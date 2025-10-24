"""
EPANET集成模块

本模块提供与EPANET的集成，用于供水管网水力和水质模拟

EPANET是EPA开发的供水管网模拟软件，是行业标准工具

安装WNTR (Water Network Tool for Resilience):
pip install wntr

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import json

# WNTR可选导入
try:
    import wntr
    EPANET_AVAILABLE = True
except ImportError:
    EPANET_AVAILABLE = False
    print("警告: wntr未安装。请使用 'pip install wntr' 安装")


@dataclass
class EPANETResults:
    """EPANET模拟结果"""
    node_pressure: Dict[str, np.ndarray]  # 节点压力
    node_demand: Dict[str, np.ndarray]  # 节点需求
    node_quality: Dict[str, np.ndarray]  # 节点水质
    link_flow: Dict[str, np.ndarray]  # 管道流量
    link_velocity: Dict[str, np.ndarray]  # 管道流速
    link_quality: Dict[str, np.ndarray]  # 管道水质
    time: np.ndarray  # 时间序列


class EPANETAdapter:
    """
    EPANET适配器

    提供HydroClaude与EPANET的集成接口
    """

    def __init__(self, inp_file: Optional[str] = None):
        """
        初始化EPANET适配器

        参数：
            inp_file: EPANET输入文件(.inp)
        """
        if not EPANET_AVAILABLE:
            raise ImportError("wntr未安装，无法使用EPANET功能")

        self.inp_file = inp_file
        self.wn = None

        if inp_file:
            self.load_network(inp_file)

    def load_network(self, inp_file: str):
        """加载EPANET网络文件"""
        self.inp_file = inp_file
        self.wn = wntr.network.WaterNetworkModel(inp_file)

        print(f"已加载EPANET网络: {inp_file}")
        print(f"  节点数: {len(self.wn.node_name_list)}")
        print(f"  管道数: {len(self.wn.link_name_list)}")
        print(f"  水库数: {len(self.wn.reservoir_name_list)}")
        print(f"  水箱数: {len(self.wn.tank_name_list)}")

    def create_simple_network(self):
        """创建简单测试网络"""
        self.wn = wntr.network.WaterNetworkModel()

        # 添加节点
        self.wn.add_junction('J1', base_demand=0.01, elevation=100)
        self.wn.add_junction('J2', base_demand=0.015, elevation=95)
        self.wn.add_junction('J3', base_demand=0.02, elevation=90)

        # 添加水库
        self.wn.add_reservoir('R1', base_head=120)

        # 添加管道
        self.wn.add_pipe('P1', 'R1', 'J1', length=1000, diameter=0.3, roughness=100)
        self.wn.add_pipe('P2', 'J1', 'J2', length=800, diameter=0.25, roughness=100)
        self.wn.add_pipe('P3', 'J2', 'J3', length=600, diameter=0.2, roughness=100)

        print("已创建简单测试网络")

    def run_hydraulic_simulation(self, duration: int = 86400) -> EPANETResults:
        """
        运行水力模拟

        参数：
            duration: 模拟时长 (秒)

        返回：
            EPANETResults对象
        """
        if self.wn is None:
            raise ValueError("未加载网络，请先加载或创建网络")

        print("\n运行水力模拟...")

        # 设置模拟选项
        self.wn.options.time.duration = duration
        self.wn.options.time.hydraulic_timestep = 3600  # 1小时
        self.wn.options.time.pattern_timestep = 3600

        # 运行模拟
        sim = wntr.sim.EpanetSimulator(self.wn)
        results = sim.run_sim()

        print("水力模拟完成！")

        # 提取结果
        return EPANETResults(
            node_pressure={},  # 稍后填充
            node_demand={},
            node_quality={},
            link_flow={},
            link_velocity={},
            link_quality={},
            time=results.node['pressure'].index.to_numpy()
        )

    def run_quality_simulation(self, species: str = 'chlorine',
                              initial_quality: float = 1.0,
                              decay_coefficient: float = -0.5) -> EPANETResults:
        """
        运行水质模拟

        参数：
            species: 物质类型
            initial_quality: 初始浓度 (mg/L)
            decay_coefficient: 衰减系数 (1/day)
        """
        if self.wn is None:
            raise ValueError("未加载网络")

        print("\n运行水质模拟...")

        # 设置水质参数
        self.wn.options.quality.parameter = 'CHEMICAL'

        # 设置初始水质
        for name in self.wn.reservoir_name_list:
            reservoir = self.wn.get_node(name)
            reservoir.initial_quality = initial_quality

        # 设置全局反应系数
        self.wn.options.quality.bulk_reaction_coefficient = decay_coefficient

        # 运行模拟
        sim = wntr.sim.EpanetSimulator(self.wn)
        results = sim.run_sim()

        print("水质模拟完成！")

        # 提取和转换结果
        epanet_results = self._extract_results(results)

        return epanet_results

    def _extract_results(self, wntr_results) -> EPANETResults:
        """提取WNTR结果"""
        results = EPANETResults(
            node_pressure={},
            node_demand={},
            node_quality={},
            link_flow={},
            link_velocity={},
            link_quality={},
            time=wntr_results.node['pressure'].index.to_numpy()
        )

        # 节点结果
        for node_name in self.wn.junction_name_list:
            if node_name in wntr_results.node['pressure'].columns:
                results.node_pressure[node_name] = wntr_results.node['pressure'][node_name].to_numpy()
                results.node_demand[node_name] = wntr_results.node['demand'][node_name].to_numpy()

                if 'quality' in wntr_results.node:
                    results.node_quality[node_name] = wntr_results.node['quality'][node_name].to_numpy()

        # 管道结果
        for link_name in self.wn.pipe_name_list:
            if link_name in wntr_results.link['flowrate'].columns:
                results.link_flow[link_name] = wntr_results.link['flowrate'][link_name].to_numpy()
                results.link_velocity[link_name] = wntr_results.link['velocity'][link_name].to_numpy()

                if 'quality' in wntr_results.link:
                    results.link_quality[link_name] = wntr_results.link['quality'][link_name].to_numpy()

        return results

    def plot_network(self, save_path: Optional[str] = None):
        """绘制管网图"""
        if self.wn is None:
            raise ValueError("未加载网络")

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 10))

        # 绘制管网
        wntr.graphics.plot_network(
            self.wn,
            node_attribute=None,
            link_attribute=None,
            ax=ax,
            node_size=40,
            link_width=2
        )

        ax.set_title('Water Network Layout', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"管网图已保存: {save_path}")

        return fig, ax

    def plot_results(self, results: EPANETResults, save_path: Optional[str] = None):
        """绘制模拟结果"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        time_hours = results.time / 3600.0

        # 1. 节点压力
        ax1 = axes[0, 0]
        for node_name, pressure in list(results.node_pressure.items())[:5]:
            ax1.plot(time_hours, pressure, '-', label=node_name, linewidth=2)
        ax1.set_xlabel('Time (hours)')
        ax1.set_ylabel('Pressure (m)')
        ax1.set_title('Node Pressure', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 节点水质
        ax2 = axes[0, 1]
        for node_name, quality in list(results.node_quality.items())[:5]:
            ax2.plot(time_hours, quality, '-', label=node_name, linewidth=2)
        ax2.set_xlabel('Time (hours)')
        ax2.set_ylabel('Quality (mg/L)')
        ax2.set_title('Node Quality', fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. 管道流量
        ax3 = axes[1, 0]
        for link_name, flow in list(results.link_flow.items())[:5]:
            ax3.plot(time_hours, flow * 1000, '-', label=link_name, linewidth=2)
        ax3.set_xlabel('Time (hours)')
        ax3.set_ylabel('Flow (L/s)')
        ax3.set_title('Link Flow', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. 管道流速
        ax4 = axes[1, 1]
        for link_name, velocity in list(results.link_velocity.items())[:5]:
            ax4.plot(time_hours, velocity, '-', label=link_name, linewidth=2)
        ax4.set_xlabel('Time (hours)')
        ax4.set_ylabel('Velocity (m/s)')
        ax4.set_title('Link Velocity', fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"结果图已保存: {save_path}")

        return fig, axes

    def export_to_hydroclaud(self) -> Dict:
        """导出为HydroClaude格式"""
        if self.wn is None:
            raise ValueError("未加载网络")

        network_data = {
            'nodes': [],
            'links': []
        }

        # 导出节点
        for name in self.wn.junction_name_list:
            junction = self.wn.get_node(name)
            network_data['nodes'].append({
                'id': name,
                'x': junction.coordinates[0] if junction.coordinates else 0,
                'y': junction.coordinates[1] if junction.coordinates else 0,
                'elevation': junction.elevation,
                'base_demand': junction.base_demand
            })

        # 导出管道
        for name in self.wn.pipe_name_list:
            pipe = self.wn.get_link(name)
            network_data['links'].append({
                'id': name,
                'from': pipe.start_node_name,
                'to': pipe.end_node_name,
                'length': pipe.length,
                'diameter': pipe.diameter,
                'roughness': pipe.roughness
            })

        return network_data


# 导出
__all__ = [
    'EPANETAdapter',
    'EPANETResults',
    'EPANET_AVAILABLE',
]
