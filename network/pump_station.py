"""
泵站节点 (Pump Station Node)

将泵作为网络内部节点，用于提升水位、调节流量。

主要功能:
1. 水位提升（克服地形高差）
2. 流量调节（通过开/关、调速）
3. 控制策略（定流量、定水位、联动控制）
4. 效率计算和能耗统计

应用场景:
- 提水灌溉
- 泵站排水
- 跨流域调水
- 城市供水

Stage 3 - Task 3.3.3

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Optional, Tuple, Dict, List
from abc import ABC

from .topology import Node
from physics.pump import Pump


class PumpStationNode(Node):
    """
    泵站节点

    特点:
    - 可提升水位
    - 支持多台泵并联/串联
    - 控制策略（定流量/定水位/联动）
    - 效率计算

    属性:
        pumps: 泵列表
        control_mode: 控制模式 ('constant_flow', 'constant_head', 'auto')
        target_flow: 目标流量 (m³/s)
        target_head: 目标扬程 (m)
        total_head: 总扬程 (m)
        total_power: 总功率 (kW)
        total_energy: 累计能耗 (kWh)
    """

    def __init__(self,
                 node_id: str,
                 elevation: float,
                 x: float = 0.0,
                 y: float = 0.0,
                 control_mode: str = 'constant_flow',
                 target_flow: float = 100.0,
                 target_head: float = None):
        """
        初始化泵站节点

        Args:
            node_id: 节点ID
            elevation: 节点高程 (m)
            x, y: 平面坐标 (m)
            control_mode: 控制模式
                - 'constant_flow': 定流量（默认）
                - 'constant_head': 定扬程
                - 'auto': 自动调节
            target_flow: 目标流量 (m³/s)
            target_head: 目标扬程 (m)
        """
        # 使用'junction'类型，因为pump_station不是Node的有效类型
        super().__init__(node_id, "junction", elevation, x, y)

        # 控制参数
        self.control_mode = control_mode
        self.target_flow = target_flow
        self.target_head = target_head

        # 泵组
        self.pumps: List[Pump] = []
        self.pump_status: List[bool] = []  # 每台泵的运行状态

        # 状态变量
        self.total_head = 0.0  # 总扬程 (m)
        self.total_power = 0.0  # 总功率 (kW)
        self.total_efficiency = 0.0  # 总效率
        self.total_energy = 0.0  # 累计能耗 (kWh)

        # 统计
        self.operating_hours = 0.0  # 运行小时数
        self.start_count = 0  # 启动次数

    def add_pump(self,
                 rated_flow: float,
                 rated_head: float,
                 rated_speed: float = 1500.0,
                 max_efficiency: float = 0.85,
                 name: Optional[str] = None) -> Pump:
        """
        添加泵到泵站

        Args:
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            rated_speed: 额定转速 (rpm)
            max_efficiency: 最大效率
            name: 泵名称

        Returns:
            Pump实例
        """
        if name is None:
            name = f"{self.id}_Pump{len(self.pumps)+1}"

        pump = Pump(
            name=name,
            rated_flow=rated_flow,
            rated_head=rated_head,
            rated_speed=rated_speed,
            max_efficiency=max_efficiency
        )

        self.pumps.append(pump)
        self.pump_status.append(False)  # 初始关闭

        return pump

    def compute_pump_head(self, Q_total: float) -> float:
        """
        计算泵站总扬程

        考虑运行泵的特性曲线和并联/串联方式

        Args:
            Q_total: 总流量 (m³/s)

        Returns:
            总扬程 (m)
        """
        if not self.pumps:
            return 0.0

        # 统计运行泵数量
        n_running = sum(self.pump_status)

        if n_running == 0:
            return 0.0

        # 简化计算：假设所有泵并联运行，流量均分
        Q_per_pump = Q_total / n_running if n_running > 0 else 0.0

        # 计算第一台运行泵的扬程（并联时所有泵扬程相同）
        total_head = 0.0
        for i, pump in enumerate(self.pumps):
            if self.pump_status[i]:
                head = pump.calculate_head(Q_per_pump)
                total_head = head  # 并联时取相同扬程
                break

        self.total_head = total_head
        return total_head

    def compute_power_and_efficiency(self, Q_total: float, H: float) -> Tuple[float, float]:
        """
        计算总功率和效率

        Args:
            Q_total: 总流量 (m³/s)
            H: 扬程 (m)

        Returns:
            (total_power, total_efficiency): 总功率(kW), 总效率
        """
        if not self.pumps or Q_total <= 0:
            self.total_power = 0.0
            self.total_efficiency = 0.0
            return 0.0, 0.0

        n_running = sum(self.pump_status)
        if n_running == 0:
            self.total_power = 0.0
            self.total_efficiency = 0.0
            return 0.0, 0.0

        Q_per_pump = Q_total / n_running

        total_power = 0.0
        total_efficiency = 0.0

        for i, pump in enumerate(self.pumps):
            if self.pump_status[i]:
                eta = pump.calculate_efficiency(Q_per_pump)
                power = pump.calculate_power(Q_per_pump, H, eta)

                total_power += power
                total_efficiency += eta

        # 平均效率
        total_efficiency /= n_running if n_running > 0 else 1

        self.total_power = total_power / 1000.0  # W to kW
        self.total_efficiency = total_efficiency

        return self.total_power, self.total_efficiency

    def update_control(self, Q_available: float, h_upstream: float, h_downstream: float) -> Tuple[float, int]:
        """
        更新控制策略，决定运行泵数量

        Args:
            Q_available: 可用流量 (m³/s)
            h_upstream: 上游水位 (m)
            h_downstream: 下游水位 (m)

        Returns:
            (Q_pump, n_running): 泵站流量, 运行泵数
        """
        if not self.pumps:
            return 0.0, 0

        if self.control_mode == 'constant_flow':
            # 定流量模式：尽量达到目标流量
            Q_pump = min(self.target_flow, Q_available)

            # 计算需要多少台泵
            n_needed = 0
            for pump in self.pumps:
                if Q_pump > pump.rated_flow * n_needed:
                    n_needed += 1

            # 更新泵状态
            for i in range(len(self.pumps)):
                self.pump_status[i] = (i < n_needed)

            return Q_pump, n_needed

        elif self.control_mode == 'constant_head':
            # 定扬程模式：维持目标扬程
            if self.target_head is None:
                self.target_head = 50.0  # 默认50m

            # 根据扬程需求决定流量
            # 简化：假设泵特性曲线为 H = H0 - a*Q^2
            # Q = sqrt((H0 - H_target) / a)

            if len(self.pumps) > 0:
                pump0 = self.pumps[0]
                if pump0.a != 0:
                    Q_single = np.sqrt((pump0.H0 - self.target_head) / pump0.a)
                    Q_single = max(0, min(Q_single, pump0.rated_flow))

                    n_running = min(len(self.pumps), int(np.ceil(Q_available / Q_single)))
                    Q_pump = Q_single * n_running

                    # 更新泵状态
                    for i in range(len(self.pumps)):
                        self.pump_status[i] = (i < n_running)

                    return Q_pump, n_running

            return 0.0, 0

        elif self.control_mode == 'auto':
            # 自动模式：根据上下游水位差自动调节
            delta_h = h_downstream - h_upstream

            # 如果下游水位不足，启动泵
            if delta_h < 0:
                # 需要提升的高度
                required_head = abs(delta_h) + 5.0  # 额外5m裕度

                # 选择合适的泵数量
                n_running = 1
                for pump in self.pumps:
                    if pump.rated_head < required_head:
                        n_running += 1

                n_running = min(n_running, len(self.pumps))

                # 计算流量
                Q_pump = min(Q_available, sum([p.rated_flow for i, p in enumerate(self.pumps) if i < n_running]))

                # 更新泵状态
                for i in range(len(self.pumps)):
                    self.pump_status[i] = (i < n_running)

                return Q_pump, n_running

            return 0.0, 0

        return 0.0, 0

    def update_energy(self, dt: float):
        """
        更新累计能耗

        Args:
            dt: 时间步长 (s)
        """
        # 能耗 = 功率 × 时间
        energy_kwh = self.total_power * (dt / 3600.0)  # kWh
        self.total_energy += energy_kwh

        # 统计运行时间
        if sum(self.pump_status) > 0:
            self.operating_hours += dt / 3600.0

    def get_status(self) -> Dict:
        """获取泵站状态"""
        return {
            'node_id': self.id,
            'control_mode': self.control_mode,
            'n_pumps': len(self.pumps),
            'n_running': sum(self.pump_status),
            'pump_status': self.pump_status.copy(),
            'Q_in': sum(self.Q_in) if self.Q_in else 0.0,
            'Q_out': sum(self.Q_out) if self.Q_out else 0.0,
            'total_head': self.total_head,
            'total_power': self.total_power,
            'total_efficiency': self.total_efficiency,
            'total_energy': self.total_energy,
            'operating_hours': self.operating_hours,
        }

    def print_status(self):
        """打印泵站状态"""
        print(f"\n泵站状态: {self.id}")
        print(f"  控制模式: {self.control_mode}")
        print(f"  泵数量: {len(self.pumps)}")
        print(f"  运行泵数: {sum(self.pump_status)}")

        for i, (pump, status) in enumerate(zip(self.pumps, self.pump_status)):
            status_str = "运行" if status else "停止"
            print(f"    泵{i+1} ({pump.name}): {status_str}")

        print(f"  入流: {sum(self.Q_in) if self.Q_in else 0:.2f} m³/s")
        print(f"  出流: {sum(self.Q_out) if self.Q_out else 0:.2f} m³/s")
        print(f"  总扬程: {self.total_head:.2f} m")
        print(f"  总功率: {self.total_power:.2f} kW")
        print(f"  总效率: {self.total_efficiency*100:.1f}%")
        print(f"  累计能耗: {self.total_energy:.2f} kWh")
        print(f"  运行时间: {self.operating_hours:.1f} h")


# 便捷函数

def create_pump_station(node_id: str,
                        elevation: float,
                        n_pumps: int = 2,
                        pump_rated_flow: float = 50.0,
                        pump_rated_head: float = 50.0,
                        control_mode: str = 'constant_flow',
                        target_flow: float = 100.0,
                        **kwargs) -> PumpStationNode:
    """
    创建泵站节点（便捷函数）

    Args:
        node_id: 节点ID
        elevation: 高程 (m)
        n_pumps: 泵数量
        pump_rated_flow: 单泵额定流量 (m³/s)
        pump_rated_head: 单泵额定扬程 (m)
        control_mode: 控制模式
        target_flow: 目标流量 (m³/s)
        **kwargs: 其他参数

    Returns:
        PumpStationNode实例

    示例:
        pump_station = create_pump_station(
            "PS1",
            elevation=100.0,
            n_pumps=3,
            pump_rated_flow=50.0,
            pump_rated_head=80.0,
            control_mode='constant_flow',
            target_flow=120.0
        )
    """
    station = PumpStationNode(
        node_id=node_id,
        elevation=elevation,
        control_mode=control_mode,
        target_flow=target_flow,
        **kwargs
    )

    # 添加泵
    for i in range(n_pumps):
        station.add_pump(
            rated_flow=pump_rated_flow,
            rated_head=pump_rated_head,
            name=f"{node_id}_Pump{i+1}"
        )

    return station


if __name__ == "__main__":
    """简单测试"""
    print("Network Pump Station Module")
    print("Integrates pumps into network as special nodes")
    print()
    print("Main classes:")
    print("  - PumpStationNode: 泵站节点类")
    print()
    print("Features:")
    print("  - 水位提升")
    print("  - 流量调节")
    print("  - 控制策略（定流量/定扬程/自动）")
    print("  - 效率和能耗计算")
    print()
    print("Convenience functions:")
    print("  - create_pump_station()")
