"""
水库调度器 (Reservoir Scheduler)

基于优化的水库调度引擎，整合Test-Opt的优化能力

功能特性:
1. 单水库优化调度
2. 多目标优化（发电、防洪、供水、生态）
3. 约束管理和验证
4. Pyomo优化模型构建
5. 多求解器支持

作者: HydroClaude Team
日期: 2025-10-22
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

try:
    from optimization.water_network_generic import build_model, solve_model
    from optimization.water_network_schema import NetworkConfig, NodeSpec, EdgeSpec
    from optimization.validation import validate_config
    from optimization.feasibility import check_solution_feasibility
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    print("Warning: Optimization module not available. Install pyomo for optimization support.")


@dataclass
class SchedulingResult:
    """
    调度结果数据类
    """
    success: bool
    objective_value: float
    storage_schedule: np.ndarray
    level_schedule: np.ndarray
    inflow_schedule: np.ndarray
    outflow_schedule: np.ndarray
    turbine_schedule: np.ndarray
    spillway_schedule: np.ndarray
    power_schedule: np.ndarray
    solver_time: float
    solver_status: str


class ReservoirScheduler:
    """
    水库调度器

    使用优化方法求解水库最优调度方案

    优化目标:
    - 最大化发电效益
    - 最小化缺水损失
    - 满足防洪约束
    - 满足生态约束

    应用场景:
    - 水电站日前调度
    - 水库防洪预泄
    - 供水优化调度
    """

    def __init__(
        self,
        reservoir,
        solver: str = 'glpk',
        objective_weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化调度器

        参数:
            reservoir: 水库对象
            solver: 求解器名称 ('glpk', 'highs', 'cplex', 'gurobi')
            objective_weights: 目标权重 {'power': 1.0, 'shortage': 1000.0}
        """
        if not OPTIMIZATION_AVAILABLE:
            raise ImportError("Optimization module not available. Install pyomo and a solver.")

        self.reservoir = reservoir
        self.solver = solver
        self.objective_weights = objective_weights or {
            'power_cost': 1.0,
            'shortage': 1000.0
        }

    def optimize_schedule(
        self,
        horizon_hours: int,
        inflow_forecast: np.ndarray,
        electricity_prices: Optional[np.ndarray] = None,
        demand_forecast: Optional[np.ndarray] = None,
        constraints: Optional[Dict] = None
    ) -> SchedulingResult:
        """
        优化调度方案

        参数:
            horizon_hours: 优化时域（小时）
            inflow_forecast: 入流预测序列 (m³/s)
            electricity_prices: 电价序列 (元/kWh)
            demand_forecast: 需水预测序列 (m³/s)
            constraints: 额外约束

        返回:
            SchedulingResult对象
        """
        # 构建优化模型配置
        config = self._build_optimization_config(
            horizon_hours=horizon_hours,
            inflow_forecast=inflow_forecast,
            electricity_prices=electricity_prices,
            demand_forecast=demand_forecast,
            constraints=constraints
        )

        # 验证配置
        try:
            validate_config(config)
        except Exception as e:
            return SchedulingResult(
                success=False,
                objective_value=float('inf'),
                storage_schedule=np.zeros(horizon_hours),
                level_schedule=np.zeros(horizon_hours),
                inflow_schedule=inflow_forecast,
                outflow_schedule=np.zeros(horizon_hours),
                turbine_schedule=np.zeros(horizon_hours),
                spillway_schedule=np.zeros(horizon_hours),
                power_schedule=np.zeros(horizon_hours),
                solver_time=0.0,
                solver_status=f"Config validation failed: {e}"
            )

        # 构建Pyomo模型
        try:
            model = build_model(config)
        except Exception as e:
            return SchedulingResult(
                success=False,
                objective_value=float('inf'),
                storage_schedule=np.zeros(horizon_hours),
                level_schedule=np.zeros(horizon_hours),
                inflow_schedule=inflow_forecast,
                outflow_schedule=np.zeros(horizon_hours),
                turbine_schedule=np.zeros(horizon_hours),
                spillway_schedule=np.zeros(horizon_hours),
                power_schedule=np.zeros(horizon_hours),
                solver_time=0.0,
                solver_status=f"Model building failed: {e}"
            )

        # 求解模型
        try:
            import time
            start_time = time.time()
            results = solve_model(model, solver=self.solver)
            solver_time = time.time() - start_time

            # 提取结果
            return self._extract_results(model, results, horizon_hours, inflow_forecast, solver_time)

        except Exception as e:
            return SchedulingResult(
                success=False,
                objective_value=float('inf'),
                storage_schedule=np.zeros(horizon_hours),
                level_schedule=np.zeros(horizon_hours),
                inflow_schedule=inflow_forecast,
                outflow_schedule=np.zeros(horizon_hours),
                turbine_schedule=np.zeros(horizon_hours),
                spillway_schedule=np.zeros(horizon_hours),
                power_schedule=np.zeros(horizon_hours),
                solver_time=0.0,
                solver_status=f"Solver failed: {e}"
            )

    def _build_optimization_config(
        self,
        horizon_hours: int,
        inflow_forecast: np.ndarray,
        electricity_prices: Optional[np.ndarray],
        demand_forecast: Optional[np.ndarray],
        constraints: Optional[Dict]
    ) -> Dict:
        """
        构建优化配置

        将HydroClaude的水库对象转换为Test-Opt的配置格式
        """
        import datetime

        # 生成时间索引
        start_time = datetime.datetime.now()
        times = [start_time + datetime.timedelta(hours=i) for i in range(horizon_hours)]
        time_strings = [t.strftime("%Y-%m-%d %H:%M:%S") for t in times]

        # 如果没有提供电价，使用平价
        if electricity_prices is None:
            electricity_prices = np.ones(horizon_hours)

        # 如果没有提供需水预测，使用0
        if demand_forecast is None:
            demand_forecast = np.zeros(horizon_hours)

        # 构建节点配置（水库节点）
        reservoir_node: NodeSpec = {
            'id': self.reservoir.reservoir_id,
            'kind': 'reservoir',
            'states': {
                'storage': {
                    'initial': float(self.reservoir.state.storage),
                    'bounds': (float(self.reservoir.dead_storage), float(self.reservoir.total_capacity)),
                    'role': 'storage'
                }
            },
            'attributes': {}
        }

        # 构建需水节点
        demand_node: NodeSpec = {
            'id': 'demand_node',
            'kind': 'demand',
            'states': {},
            'attributes': {}
        }

        # 构建边配置（从水库到需水节点）
        if self.reservoir.has_turbine:
            # 使用分段线性效率曲线
            max_flow = self.reservoir._get_max_turbine_flow()
            n_segments = 10
            flow_points = np.linspace(0, max_flow, n_segments)

            # 计算每个流量点的发电成本（负值表示收益）
            cost_points = []
            for q in flow_points:
                head = self.reservoir.hydraulic_head if self.reservoir.hydraulic_head > 0 else 50.0
                power = 9.81 * q * head * self.reservoir.turbine_efficiency / 1000.0  # MW
                # 成本 = -功率 * 平均电价（负值表示收益）
                cost = -power * np.mean(electricity_prices)
                cost_points.append(cost)

            turbine_edge: EdgeSpec = {
                'id': 'turbine',
                'from_node': self.reservoir.reservoir_id,
                'to_node': 'demand_node',
                'attributes': {
                    'capacity': float(max_flow),
                    'efficiency_curve': (flow_points.tolist(), cost_points)
                }
            }
        else:
            turbine_edge: EdgeSpec = {
                'id': 'outlet',
                'from_node': self.reservoir.reservoir_id,
                'to_node': 'demand_node',
                'attributes': {
                    'capacity': float(self.reservoir.max_discharge)
                }
            }

        # 构建时间序列
        series = {
            'inflow_series': {
                'times': time_strings,
                'values': inflow_forecast.tolist(),
                'default': float(np.mean(inflow_forecast)),
                'units': 'm³/s'
            },
            'demand_series': {
                'times': time_strings,
                'values': demand_forecast.tolist(),
                'default': float(np.mean(demand_forecast)),
                'units': 'm³/s'
            }
        }

        # 将时间序列绑定到节点
        reservoir_node['series_map'] = {
            'inflow': 'inflow_series'
        }
        demand_node['series_map'] = {
            'demand': 'demand_series'
        }
        demand_node['shortage_penalty_factor'] = self.objective_weights['shortage']

        # 构建完整配置
        config: NetworkConfig = {
            'horizon': {
                'start': time_strings[0],
                'end': time_strings[-1],
                'step_hours': 1.0
            },
            'nodes': [reservoir_node, demand_node],
            'edges': [turbine_edge],
            'series': series,
            'objective_weights': {
                'pump_cost': self.objective_weights['power_cost'],
                'shortage': self.objective_weights['shortage']
            }
        }

        return config

    def _extract_results(
        self,
        model,
        results,
        horizon_hours: int,
        inflow_forecast: np.ndarray,
        solver_time: float
    ) -> SchedulingResult:
        """
        从Pyomo模型中提取结果
        """
        from pyomo.environ import value
        from pyomo.opt import TerminationCondition

        # 检查求解状态
        success = results.solver.termination_condition == TerminationCondition.optimal

        if success:
            # 提取目标值
            objective_value = value(model.obj)

            # 提取状态和流量
            storage_schedule = np.array([
                value(model.state[(self.reservoir.reservoir_id, 'storage'), t])
                for t in range(horizon_hours)
            ])

            outflow_schedule = np.array([
                value(model.flow['turbine', t])
                for t in range(horizon_hours)
            ])

            # 计算水位（使用库容-水位关系）
            level_schedule = np.array([
                float(self.reservoir.storage_to_level(s))
                for s in storage_schedule
            ])

            # 计算发电量
            power_schedule = np.zeros(horizon_hours)
            if self.reservoir.has_turbine:
                for t in range(horizon_hours):
                    q = outflow_schedule[t]
                    head = self.reservoir.hydraulic_head if self.reservoir.hydraulic_head > 0 else 50.0
                    power_schedule[t] = 9.81 * q * head * self.reservoir.turbine_efficiency / 1000.0

            # 暂时设置turbine和spillway为总出流
            turbine_schedule = outflow_schedule.copy()
            spillway_schedule = np.zeros(horizon_hours)

        else:
            objective_value = float('inf')
            storage_schedule = np.zeros(horizon_hours)
            level_schedule = np.zeros(horizon_hours)
            outflow_schedule = np.zeros(horizon_hours)
            turbine_schedule = np.zeros(horizon_hours)
            spillway_schedule = np.zeros(horizon_hours)
            power_schedule = np.zeros(horizon_hours)

        return SchedulingResult(
            success=success,
            objective_value=objective_value,
            storage_schedule=storage_schedule,
            level_schedule=level_schedule,
            inflow_schedule=inflow_forecast,
            outflow_schedule=outflow_schedule,
            turbine_schedule=turbine_schedule,
            spillway_schedule=spillway_schedule,
            power_schedule=power_schedule,
            solver_time=solver_time,
            solver_status=str(results.solver.termination_condition)
        )


class CascadeScheduler:
    """
    梯级水库调度器

    使用优化方法求解梯级水库联合调度方案
    """

    def __init__(
        self,
        cascade,
        solver: str = 'glpk',
        objective_weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化梯级调度器

        参数:
            cascade: 梯级水库系统
            solver: 求解器名称
            objective_weights: 目标权重
        """
        if not OPTIMIZATION_AVAILABLE:
            raise ImportError("Optimization module not available.")

        self.cascade = cascade
        self.solver = solver
        self.objective_weights = objective_weights or {
            'power_cost': 1.0,
            'shortage': 1000.0
        }

    def optimize_cascade_schedule(
        self,
        horizon_hours: int,
        inflow_forecasts: Dict[str, np.ndarray],
        electricity_prices: Optional[np.ndarray] = None,
        demand_forecasts: Optional[Dict[str, np.ndarray]] = None
    ) -> Dict[str, SchedulingResult]:
        """
        优化梯级调度方案

        参数:
            horizon_hours: 优化时域（小时）
            inflow_forecasts: 入流预测字典 {水库ID: 入流序列}
            electricity_prices: 电价序列
            demand_forecasts: 需水预测字典

        返回:
            调度结果字典 {水库ID: SchedulingResult}
        """
        # 构建梯级优化配置
        config = self._build_cascade_config(
            horizon_hours=horizon_hours,
            inflow_forecasts=inflow_forecasts,
            electricity_prices=electricity_prices,
            demand_forecasts=demand_forecasts
        )

        # 构建并求解模型
        try:
            model = build_model(config)
            import time
            start_time = time.time()
            results = solve_model(model, solver=self.solver)
            solver_time = time.time() - start_time

            # 提取每个水库的结果
            return self._extract_cascade_results(
                model, results, horizon_hours, inflow_forecasts, solver_time
            )

        except Exception as e:
            print(f"Cascade optimization failed: {e}")
            # 返回失败结果
            return {
                res_id: SchedulingResult(
                    success=False,
                    objective_value=float('inf'),
                    storage_schedule=np.zeros(horizon_hours),
                    level_schedule=np.zeros(horizon_hours),
                    inflow_schedule=inflow_forecasts.get(res_id, np.zeros(horizon_hours)),
                    outflow_schedule=np.zeros(horizon_hours),
                    turbine_schedule=np.zeros(horizon_hours),
                    spillway_schedule=np.zeros(horizon_hours),
                    power_schedule=np.zeros(horizon_hours),
                    solver_time=0.0,
                    solver_status=f"Failed: {e}"
                )
                for res_id in self.cascade.reservoirs.keys()
            }

    def _build_cascade_config(
        self,
        horizon_hours: int,
        inflow_forecasts: Dict[str, np.ndarray],
        electricity_prices: Optional[np.ndarray],
        demand_forecasts: Optional[Dict[str, np.ndarray]]
    ) -> Dict:
        """
        构建梯级优化配置
        """
        import datetime

        # 生成时间索引
        start_time = datetime.datetime.now()
        times = [start_time + datetime.timedelta(hours=i) for i in range(horizon_hours)]
        time_strings = [t.strftime("%Y-%m-%d %H:%M:%S") for t in times]

        if electricity_prices is None:
            electricity_prices = np.ones(horizon_hours)

        # 构建节点列表
        nodes = []
        edges = []
        series = {}

        # 为每个水库创建节点
        for res_id, reservoir in self.cascade.reservoirs.items():
            node: NodeSpec = {
                'id': res_id,
                'kind': 'reservoir',
                'states': {
                    'storage': {
                        'initial': float(reservoir.state.storage),
                        'bounds': (float(reservoir.dead_storage), float(reservoir.total_capacity)),
                        'role': 'storage'
                    }
                },
                'attributes': {},
                'series_map': {
                    'inflow': f'inflow_{res_id}'
                }
            }
            nodes.append(node)

            # 创建入流时间序列
            inflow = inflow_forecasts.get(res_id, np.zeros(horizon_hours))
            series[f'inflow_{res_id}'] = {
                'times': time_strings,
                'values': inflow.tolist(),
                'default': float(np.mean(inflow)),
                'units': 'm³/s'
            }

        # 创建梯级间的连接边
        for upstream_id, downstreams in self.cascade.topology.connections.items():
            for downstream_id in downstreams:
                edge: EdgeSpec = {
                    'id': f'{upstream_id}_to_{downstream_id}',
                    'from_node': upstream_id,
                    'to_node': downstream_id,
                    'attributes': {
                        'capacity': float(self.cascade.reservoirs[upstream_id].max_discharge)
                    }
                }
                edges.append(edge)

        # 创建需水节点
        demand_node: NodeSpec = {
            'id': 'final_demand',
            'kind': 'demand',
            'states': {},
            'attributes': {},
            'series_map': {
                'demand': 'demand_series'
            },
            'shortage_penalty_factor': self.objective_weights['shortage']
        }
        nodes.append(demand_node)

        # 从最后一个水库到需水节点的边
        last_reservoir_id = self.cascade.topological_order[-1]
        final_edge: EdgeSpec = {
            'id': 'final_outlet',
            'from_node': last_reservoir_id,
            'to_node': 'final_demand',
            'attributes': {
                'capacity': float(self.cascade.reservoirs[last_reservoir_id].max_discharge)
            }
        }
        edges.append(final_edge)

        # 需水序列
        if demand_forecasts and 'final' in demand_forecasts:
            demand = demand_forecasts['final']
        else:
            demand = np.zeros(horizon_hours)

        series['demand_series'] = {
            'times': time_strings,
            'values': demand.tolist(),
            'default': float(np.mean(demand)),
            'units': 'm³/s'
        }

        # 构建完整配置
        config: NetworkConfig = {
            'horizon': {
                'start': time_strings[0],
                'end': time_strings[-1],
                'step_hours': 1.0
            },
            'nodes': nodes,
            'edges': edges,
            'series': series,
            'objective_weights': {
                'pump_cost': self.objective_weights['power_cost'],
                'shortage': self.objective_weights['shortage']
            }
        }

        return config

    def _extract_cascade_results(
        self,
        model,
        results,
        horizon_hours: int,
        inflow_forecasts: Dict[str, np.ndarray],
        solver_time: float
    ) -> Dict[str, SchedulingResult]:
        """
        提取梯级调度结果
        """
        from pyomo.environ import value
        from pyomo.opt import TerminationCondition

        success = results.solver.termination_condition == TerminationCondition.optimal

        cascade_results = {}

        for res_id, reservoir in self.cascade.reservoirs.items():
            if success:
                # 提取该水库的结果
                storage_schedule = np.array([
                    value(model.state[(res_id, 'storage'), t])
                    for t in range(horizon_hours)
                ])

                # 计算出流（该水库所有出边的流量和）
                outflow_schedule = np.zeros(horizon_hours)
                for edge_id in model.E:
                    if edge_id.startswith(res_id):
                        outflow_schedule += np.array([
                            value(model.flow[edge_id, t])
                            for t in range(horizon_hours)
                        ])

                level_schedule = np.array([
                    float(reservoir.storage_to_level(s))
                    for s in storage_schedule
                ])

                power_schedule = np.zeros(horizon_hours)
                if reservoir.has_turbine:
                    for t in range(horizon_hours):
                        q = outflow_schedule[t]
                        head = reservoir.hydraulic_head if reservoir.hydraulic_head > 0 else 50.0
                        power_schedule[t] = 9.81 * q * head * reservoir.turbine_efficiency / 1000.0

            else:
                storage_schedule = np.zeros(horizon_hours)
                level_schedule = np.zeros(horizon_hours)
                outflow_schedule = np.zeros(horizon_hours)
                power_schedule = np.zeros(horizon_hours)

            cascade_results[res_id] = SchedulingResult(
                success=success,
                objective_value=value(model.obj) if success else float('inf'),
                storage_schedule=storage_schedule,
                level_schedule=level_schedule,
                inflow_schedule=inflow_forecasts.get(res_id, np.zeros(horizon_hours)),
                outflow_schedule=outflow_schedule,
                turbine_schedule=outflow_schedule.copy(),
                spillway_schedule=np.zeros(horizon_hours),
                power_schedule=power_schedule,
                solver_time=solver_time,
                solver_status=str(results.solver.termination_condition)
            )

        return cascade_results
