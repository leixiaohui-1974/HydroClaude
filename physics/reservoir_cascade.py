"""
梯级水库系统 (Reservoir Cascade System)

梯级水库联合优化调度系统

功能特性:
1. 多水库拓扑管理
2. 水流传递和时间延迟
3. 梯级联合优化调度
4. 防洪协调控制
5. 发电优化协调

作者: HydroClaude Team
日期: 2025-10-22
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

from physics.reservoir import Reservoir, ReservoirState


@dataclass
class CascadeTopology:
    """
    梯级拓扑结构

    定义水库之间的上下游关系
    """
    reservoir_ids: List[str]
    connections: Dict[str, List[str]]  # {上游水库ID: [下游水库ID列表]}
    travel_times: Dict[Tuple[str, str], float]  # {(上游ID, 下游ID): 传播时间(小时)}
    lateral_inflows: Dict[str, float]  # {水库ID: 区间入流(m³/s)}


class ReservoirCascade:
    """
    梯级水库系统

    管理多个水库的联合运行和优化调度

    模型基础:
    - 水流传递: Q_down(t+τ) = Q_up(t) + Q_lateral
    - 水量守恒: ΣQ_in = ΣQ_out
    - 梯级协调: 上游调度影响下游边界条件

    应用场景:
    - 梯级水电站联合调度
    - 流域防洪协调
    - 梯级供水优化
    """

    def __init__(
        self,
        cascade_id: str,
        reservoirs: List[Reservoir],
        topology: CascadeTopology
    ):
        """
        初始化梯级水库系统

        参数:
            cascade_id: 梯级系统ID
            reservoirs: 水库列表
            topology: 梯级拓扑结构
        """
        self.cascade_id = cascade_id
        self.reservoirs = {r.reservoir_id: r for r in reservoirs}
        self.topology = topology

        # 验证拓扑
        self._validate_topology()

        # 计算拓扑序（从上游到下游）
        self.topological_order = self._compute_topological_order()

        # 水流传递缓冲区
        self.flow_buffers = defaultdict(list)  # {(上游ID, 下游ID): [历史流量队列]}

    def _validate_topology(self):
        """验证拓扑结构的有效性"""
        # 检查所有水库ID是否存在
        for res_id in self.topology.reservoir_ids:
            if res_id not in self.reservoirs:
                raise ValueError(f"水库 {res_id} 在拓扑中定义但未提供实例")

        # 检查连接关系
        for upstream, downstreams in self.topology.connections.items():
            if upstream not in self.reservoirs:
                raise ValueError(f"上游水库 {upstream} 不存在")
            for downstream in downstreams:
                if downstream not in self.reservoirs:
                    raise ValueError(f"下游水库 {downstream} 不存在")

    def _compute_topological_order(self) -> List[str]:
        """
        计算拓扑序（从上游到下游）

        使用深度优先搜索确定计算顺序

        返回:
            拓扑序列表
        """
        # 计算入度
        in_degree = {res_id: 0 for res_id in self.topology.reservoir_ids}
        for upstream, downstreams in self.topology.connections.items():
            for downstream in downstreams:
                in_degree[downstream] += 1

        # 找到所有源节点（入度为0）
        queue = [res_id for res_id, degree in in_degree.items() if degree == 0]
        order = []

        while queue:
            # 取出一个源节点
            current = queue.pop(0)
            order.append(current)

            # 更新下游节点的入度
            if current in self.topology.connections:
                for downstream in self.topology.connections[current]:
                    in_degree[downstream] -= 1
                    if in_degree[downstream] == 0:
                        queue.append(downstream)

        # 检查是否存在环
        if len(order) != len(self.topology.reservoir_ids):
            raise ValueError("梯级拓扑存在环，无法计算拓扑序")

        return order

    def simulate_cascade(
        self,
        dt: float,
        inflows: Dict[str, float],
        outflow_targets: Optional[Dict[str, float]] = None,
        turbine_discharges: Optional[Dict[str, float]] = None,
        high_fidelity: bool = True
    ) -> Dict[str, ReservoirState]:
        """
        仿真梯级水库系统

        参数:
            dt: 时间步长 (s)
            inflows: 各水库入流字典 {水库ID: 入流(m³/s)}
            outflow_targets: 目标出流字典（可选）
            turbine_discharges: 水轮机流量字典（可选）
            high_fidelity: 是否使用高保真模型

        返回:
            各水库状态字典
        """
        states = {}

        # 按拓扑序更新
        for res_id in self.topological_order:
            reservoir = self.reservoirs[res_id]

            # 计算总入流 = 区间入流 + 上游水库出流
            total_inflow = inflows.get(res_id, 0.0) + self.topology.lateral_inflows.get(res_id, 0.0)

            # 添加上游出流
            upstream_outflow = self._get_upstream_outflow(res_id, dt)
            total_inflow += upstream_outflow

            # 构建输入
            inputs = {'inflow': total_inflow}
            if outflow_targets and res_id in outflow_targets:
                inputs['outflow_target'] = outflow_targets[res_id]
            if turbine_discharges and res_id in turbine_discharges:
                inputs['turbine_discharge'] = turbine_discharges[res_id]

            # 更新水库状态
            if high_fidelity:
                state = reservoir.update_high_fidelity(dt, inputs)
            else:
                state = reservoir.update_reduced_order(dt, inputs)

            states[res_id] = state

            # 更新水流传递缓冲区
            self._update_flow_buffers(res_id, state.outflow, dt)

        return states

    def _get_upstream_outflow(self, reservoir_id: str, dt: float) -> float:
        """
        获取上游水库的出流（考虑时间延迟）

        参数:
            reservoir_id: 水库ID
            dt: 时间步长 (s)

        返回:
            上游总出流 (m³/s)
        """
        total_upstream_outflow = 0.0

        # 遍历所有上游水库
        for upstream_id, downstreams in self.topology.connections.items():
            if reservoir_id in downstreams:
                # 获取传播时间
                travel_time = self.topology.travel_times.get((upstream_id, reservoir_id), 0.0)
                delay_steps = int(travel_time * 3600 / dt)  # 转换为时间步数

                # 从缓冲区获取延迟后的流量
                buffer_key = (upstream_id, reservoir_id)
                if buffer_key in self.flow_buffers and len(self.flow_buffers[buffer_key]) > delay_steps:
                    delayed_flow = self.flow_buffers[buffer_key][-delay_steps-1]
                else:
                    # 如果缓冲区不足，使用当前流量
                    delayed_flow = self.reservoirs[upstream_id].state.outflow

                total_upstream_outflow += delayed_flow

        return total_upstream_outflow

    def _update_flow_buffers(self, reservoir_id: str, outflow: float, dt: float):
        """
        更新水流传递缓冲区

        参数:
            reservoir_id: 水库ID
            outflow: 当前出流 (m³/s)
            dt: 时间步长 (s)
        """
        # 为该水库的所有下游连接更新缓冲区
        if reservoir_id in self.topology.connections:
            for downstream_id in self.topology.connections[reservoir_id]:
                buffer_key = (reservoir_id, downstream_id)
                self.flow_buffers[buffer_key].append(outflow)

                # 限制缓冲区大小（最多保留24小时数据）
                max_buffer_size = int(24 * 3600 / dt)
                if len(self.flow_buffers[buffer_key]) > max_buffer_size:
                    self.flow_buffers[buffer_key].pop(0)

    def get_cascade_status(self) -> Dict[str, Dict]:
        """
        获取梯级系统状态

        返回:
            梯级状态字典
        """
        status = {
            'cascade_id': self.cascade_id,
            'reservoir_count': len(self.reservoirs),
            'reservoirs': {}
        }

        for res_id in self.topological_order:
            status['reservoirs'][res_id] = self.reservoirs[res_id].get_operation_status()

        # 计算总发电量
        total_power = sum(r.state.power_generation for r in self.reservoirs.values())
        status['total_power_generation'] = total_power

        # 计算总库容
        total_storage = sum(r.state.storage for r in self.reservoirs.values())
        total_capacity = sum(r.total_capacity for r in self.reservoirs.values())
        status['total_storage'] = total_storage
        status['total_capacity'] = total_capacity
        status['total_storage_percent'] = total_storage / total_capacity * 100

        return status

    def check_cascade_constraints(self) -> Dict[str, bool]:
        """
        检查梯级约束

        返回:
            约束检查结果
        """
        results = {}

        # 检查每个水库的约束
        for res_id, reservoir in self.reservoirs.items():
            results[f'{res_id}_flood_control'] = reservoir.check_flood_control()
            results[f'{res_id}_drought_control'] = reservoir.check_drought_control()
            results[f'{res_id}_ecological_flow'] = reservoir.check_ecological_flow()

        # 检查水量平衡
        total_inflow = sum(r.state.inflow for r in self.reservoirs.values())
        total_outflow = sum(r.state.outflow for r in self.reservoirs.values())
        storage_change = sum(
            (r.state.storage - r.storage_history[-2]) if len(r.storage_history) >= 2 else 0
            for r in self.reservoirs.values()
        )

        # 水量平衡检查（允许1%误差）
        balance_error = abs(total_inflow - total_outflow - storage_change) / max(total_inflow, 1e-6)
        results['water_balance'] = balance_error < 0.01

        return results

    def reset(self, initial_storages: Optional[Dict[str, float]] = None):
        """
        重置梯级系统

        参数:
            initial_storages: 初始库容字典 {水库ID: 库容(m³)}
        """
        if initial_storages is None:
            initial_storages = {}

        for res_id, reservoir in self.reservoirs.items():
            initial_storage = initial_storages.get(res_id, None)
            reservoir.reset(initial_storage)

        # 清空缓冲区
        self.flow_buffers.clear()

    def get_upstream_reservoirs(self, reservoir_id: str) -> List[str]:
        """
        获取指定水库的所有上游水库

        参数:
            reservoir_id: 水库ID

        返回:
            上游水库ID列表
        """
        upstream = []
        for upstream_id, downstreams in self.topology.connections.items():
            if reservoir_id in downstreams:
                upstream.append(upstream_id)
        return upstream

    def get_downstream_reservoirs(self, reservoir_id: str) -> List[str]:
        """
        获取指定水库的所有下游水库

        参数:
            reservoir_id: 水库ID

        返回:
            下游水库ID列表
        """
        return self.topology.connections.get(reservoir_id, [])

    def get_cascade_topology_graph(self) -> Dict:
        """
        获取梯级拓扑图

        返回:
            拓扑图字典，可用于可视化
        """
        graph = {
            'nodes': [],
            'edges': []
        }

        # 添加节点
        for res_id in self.topological_order:
            reservoir = self.reservoirs[res_id]
            graph['nodes'].append({
                'id': res_id,
                'storage': reservoir.state.storage,
                'level': reservoir.state.water_level,
                'capacity': reservoir.total_capacity,
                'power': reservoir.state.power_generation
            })

        # 添加边
        for upstream_id, downstreams in self.topology.connections.items():
            for downstream_id in downstreams:
                travel_time = self.topology.travel_times.get((upstream_id, downstream_id), 0.0)
                graph['edges'].append({
                    'from': upstream_id,
                    'to': downstream_id,
                    'flow': self.reservoirs[upstream_id].state.outflow,
                    'travel_time': travel_time
                })

        return graph


def create_cascade_from_config(config: Dict) -> ReservoirCascade:
    """
    从配置字典创建梯级水库系统

    参数:
        config: 配置字典

    返回:
        ReservoirCascade对象
    """
    from physics.reservoir import create_reservoir_from_config

    # 创建水库列表
    reservoirs = []
    for res_config in config['reservoirs']:
        reservoir = create_reservoir_from_config(res_config)
        reservoirs.append(reservoir)

    # 创建拓扑
    topology = CascadeTopology(
        reservoir_ids=config['topology']['reservoir_ids'],
        connections=config['topology']['connections'],
        travel_times=config['topology'].get('travel_times', {}),
        lateral_inflows=config['topology'].get('lateral_inflows', {})
    )

    cascade_id = config.get('cascade_id', 'cascade_system')

    return ReservoirCascade(
        cascade_id=cascade_id,
        reservoirs=reservoirs,
        topology=topology
    )


class CascadeFloodControl:
    """
    梯级防洪协调控制

    实现梯级水库的防洪协调调度
    """

    def __init__(self, cascade: ReservoirCascade):
        """
        初始化防洪控制器

        参数:
            cascade: 梯级水库系统
        """
        self.cascade = cascade

    def compute_flood_control_strategy(
        self,
        forecast_inflows: Dict[str, np.ndarray],
        forecast_horizon: int
    ) -> Dict[str, np.ndarray]:
        """
        计算防洪控制策略

        参数:
            forecast_inflows: 预报入流字典 {水库ID: 入流序列}
            forecast_horizon: 预报时段数

        返回:
            优化后的出流策略 {水库ID: 出流序列}
        """
        # 这里可以实现更复杂的优化算法
        # 简化版本：根据防洪限制水位计算出流

        strategies = {}

        for res_id in self.cascade.topological_order:
            reservoir = self.cascade.reservoirs[res_id]
            inflow_forecast = forecast_inflows.get(res_id, np.zeros(forecast_horizon))

            outflows = np.zeros(forecast_horizon)

            # 简单策略：维持水位不超过防洪限制水位
            for t in range(forecast_horizon):
                current_storage = reservoir.state.storage
                inflow = inflow_forecast[t]

                # 计算防洪所需出流
                flood_limit_storage = reservoir.level_to_storage(reservoir.flood_limit_level)

                if current_storage > flood_limit_storage:
                    # 需要泄洪
                    outflows[t] = inflow + (current_storage - flood_limit_storage) / 3600
                else:
                    # 正常出流
                    outflows[t] = max(inflow * 0.8, reservoir.ecological_flow)

            strategies[res_id] = outflows

        return strategies


class CascadePowerOptimization:
    """
    梯级发电优化

    实现梯级水电站的联合优化调度
    """

    def __init__(self, cascade: ReservoirCascade):
        """
        初始化发电优化器

        参数:
            cascade: 梯级水库系统
        """
        self.cascade = cascade

    def optimize_power_generation(
        self,
        electricity_prices: np.ndarray,
        horizon: int,
        constraints: Optional[Dict] = None
    ) -> Dict[str, np.ndarray]:
        """
        优化发电调度

        参数:
            electricity_prices: 电价序列 (元/kWh)
            horizon: 优化时段数
            constraints: 额外约束

        返回:
            优化后的水轮机流量策略 {水库ID: 流量序列}
        """
        # 这里可以调用优化引擎（如Pyomo）
        # 简化版本：峰期多发电，谷期少发电

        strategies = {}

        for res_id in self.cascade.topological_order:
            reservoir = self.cascade.reservoirs[res_id]

            if not reservoir.has_turbine:
                strategies[res_id] = np.zeros(horizon)
                continue

            turbine_flows = np.zeros(horizon)

            # 简单策略：电价高时多发电
            for t in range(horizon):
                if electricity_prices[t] > np.mean(electricity_prices):
                    # 高电价，增加发电
                    turbine_flows[t] = reservoir._get_max_turbine_flow() * 0.9
                else:
                    # 低电价，减少发电
                    turbine_flows[t] = reservoir._get_max_turbine_flow() * 0.5

                # 确保满足生态流量
                turbine_flows[t] = max(turbine_flows[t], reservoir.ecological_flow)

            strategies[res_id] = turbine_flows

        return strategies
