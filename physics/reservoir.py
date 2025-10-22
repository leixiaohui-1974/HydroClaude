"""
水库组件 (Reservoir Component)

融合物理仿真与优化调度的完整水库模型

功能特性:
1. 物理仿真: 库容演算、水位计算、水量平衡
2. 优化调度: 支持基于优化的调度决策
3. 约束管理: 防洪、防旱、生态流量、死水位等
4. 库容-水位关系: 支持分段线性和非线性关系
5. 多时间尺度: 支持高保真和降阶模型
6. 调度规则: 防洪调度、兴利调度、生态调度

作者: HydroClaude Team
日期: 2025-10-22
"""

from typing import Optional, Callable, Dict, Tuple, List
from dataclasses import dataclass
import numpy as np
from scipy.interpolate import interp1d

from core.base import HydraulicComponent
from core.states import ComponentState
from core.enums import ComponentType


@dataclass
class ReservoirState(ComponentState):
    """
    水库状态数据类

    扩展ComponentState，增加水库专用状态变量
    """
    storage: float = 0.0              # 库容 (m³)
    water_level: float = 0.0          # 水位 (m)
    inflow: float = 0.0               # 入流 (m³/s)
    outflow: float = 0.0              # 出流 (m³/s)
    spillway_discharge: float = 0.0   # 溢洪道泄量 (m³/s)
    turbine_discharge: float = 0.0    # 水轮机发电流量 (m³/s)
    ecological_discharge: float = 0.0 # 生态流量 (m³/s)
    power_generation: float = 0.0     # 发电量 (MW)
    flood_control_capacity: float = 0.0  # 防洪库容 (m³)
    active_storage: float = 0.0       # 兴利库容 (m³)
    dead_storage: float = 0.0         # 死库容 (m³)


class Reservoir(HydraulicComponent):
    """
    水库组件 - 融合物理仿真与优化调度

    模型基础:
    - 连续性方程: dV/dt = Q_in - Q_out
    - 库容-水位关系: V = f(Z)
    - 泄流计算: Q_out = Q_turbine + Q_spillway + Q_ecological

    约束条件:
    - 水位约束: Z_min ≤ Z ≤ Z_max
    - 库容约束: V_dead ≤ V ≤ V_total
    - 泄流约束: Q_min ≤ Q_out ≤ Q_max
    - 防洪约束: V ≤ V_flood_limit (汛期)
    - 生态约束: Q_out ≥ Q_ecological

    应用场景:
    - 防洪调度
    - 水电站调度
    - 供水调度
    - 灌溉调度
    - 梯级水库联合调度
    """

    def __init__(
        self,
        reservoir_id: str,
        total_capacity: float,
        dead_storage: float,
        min_level: float,
        normal_level: float,
        flood_limit_level: float,
        design_level: float,
        storage_curve: Optional[Callable[[float], float]] = None,
        storage_curve_data: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        catchment_area: float = 0.0,
        ecological_flow: float = 0.0,
        max_discharge: float = float('inf'),
        has_spillway: bool = True,
        has_turbine: bool = False,
        turbine_capacity: float = 0.0,
        hydraulic_head: float = 0.0,
        turbine_efficiency: float = 0.85,
        **kwargs
    ):
        """
        初始化水库组件

        参数:
            reservoir_id: 水库ID
            total_capacity: 总库容 (m³)
            dead_storage: 死库容 (m³)
            min_level: 死水位 (m)
            normal_level: 正常蓄水位 (m)
            flood_limit_level: 防洪限制水位 (m)
            design_level: 设计洪水位 (m)
            storage_curve: 库容-水位关系函数 V=f(Z)
            storage_curve_data: 库容-水位关系数据点 (levels, storages)
            catchment_area: 集水面积 (km²)
            ecological_flow: 生态流量 (m³/s)
            max_discharge: 最大泄流能力 (m³/s)
            has_spillway: 是否有溢洪道
            has_turbine: 是否有水轮机
            turbine_capacity: 水轮机装机容量 (MW)
            hydraulic_head: 水头 (m)
            turbine_efficiency: 水轮机综合效率
        """
        super().__init__(component_id=reservoir_id, component_type=ComponentType.RESERVOIR, **kwargs)

        # 水库特征参数
        self.reservoir_id = reservoir_id
        self.total_capacity = total_capacity
        self.dead_storage = dead_storage
        self.active_storage = total_capacity - dead_storage  # 兴利库容

        # 特征水位
        self.min_level = min_level              # 死水位
        self.normal_level = normal_level        # 正常蓄水位
        self.flood_limit_level = flood_limit_level  # 防洪限制水位
        self.design_level = design_level        # 设计洪水位

        # 库容-水位关系
        self.storage_curve = storage_curve
        if storage_curve_data is not None:
            levels, storages = storage_curve_data
            # 使用scipy的interp1d创建插值函数（双向）
            self.level_to_storage = interp1d(levels, storages,
                                            kind='cubic',
                                            fill_value='extrapolate')
            self.storage_to_level = interp1d(storages, levels,
                                            kind='cubic',
                                            fill_value='extrapolate')
        else:
            # 默认使用线性关系
            self.level_to_storage = lambda z: dead_storage + (z - min_level) / (design_level - min_level) * (total_capacity - dead_storage)
            self.storage_to_level = lambda v: min_level + (v - dead_storage) / (total_capacity - dead_storage) * (design_level - min_level)

        # 水库参数
        self.catchment_area = catchment_area
        self.ecological_flow = ecological_flow
        self.max_discharge = max_discharge

        # 水电设施
        self.has_spillway = has_spillway
        self.has_turbine = has_turbine
        self.turbine_capacity = turbine_capacity
        self.hydraulic_head = hydraulic_head
        self.turbine_efficiency = turbine_efficiency

        # 状态初始化
        initial_storage = (dead_storage + total_capacity) / 2  # 默认半库
        initial_level = float(self.storage_to_level(initial_storage))

        self.state = ReservoirState(
            volume=initial_storage,
            level=initial_level,
            storage=initial_storage,
            water_level=initial_level,
            dead_storage=dead_storage,
            active_storage=self.active_storage,
            flood_control_capacity=total_capacity - self.level_to_storage(flood_limit_level)
        )

        # 历史数据
        self.inflow_history = []
        self.outflow_history = []
        self.level_history = []
        self.storage_history = []

    def update_high_fidelity(self, dt: float, inputs: Dict) -> ReservoirState:
        """
        高保真物理仿真

        使用精确的水量平衡方程和库容-水位关系

        参数:
            dt: 时间步长 (s)
            inputs: 输入字典
                - inflow: 入流 (m³/s)
                - outflow_target: 目标出流 (m³/s)，可选
                - turbine_discharge: 水轮机流量 (m³/s)，可选
                - spillway_opening: 溢洪道开度 (0-1)，可选

        返回:
            更新后的水库状态
        """
        # 获取输入
        inflow = inputs.get('inflow', 0.0)
        outflow_target = inputs.get('outflow_target', None)
        turbine_discharge = inputs.get('turbine_discharge', 0.0)
        spillway_opening = inputs.get('spillway_opening', 0.0)

        # 当前状态
        current_storage = self.state.storage
        current_level = self.state.water_level

        # 计算出流
        if outflow_target is not None:
            # 指定出流
            outflow = self._constrain_outflow(outflow_target)
            turbine_discharge = min(turbine_discharge, outflow)
            spillway_discharge = outflow - turbine_discharge
        else:
            # 根据水位和开度计算出流
            spillway_discharge = self._calculate_spillway_discharge(current_level, spillway_opening)
            turbine_discharge = self._constrain_turbine_discharge(turbine_discharge)
            outflow = spillway_discharge + turbine_discharge

        # 生态流量约束
        if outflow < self.ecological_flow:
            outflow = self.ecological_flow
            spillway_discharge = max(0, outflow - turbine_discharge)

        # 水量平衡: V(t+dt) = V(t) + (Q_in - Q_out) * dt
        new_storage = current_storage + (inflow - outflow) * dt

        # 库容约束
        if new_storage < self.dead_storage:
            new_storage = self.dead_storage
            # 重新计算实际出流
            outflow = max(0, inflow + (current_storage - self.dead_storage) / dt)
        elif new_storage > self.total_capacity:
            new_storage = self.total_capacity
            # 超出库容部分作为溢流
            spillway_discharge += (new_storage - self.total_capacity) / dt
            outflow = inflow + (current_storage - self.total_capacity) / dt

        # 计算新水位
        new_level = float(self.storage_to_level(new_storage))

        # 计算发电量
        if self.has_turbine and turbine_discharge > 0:
            # P = η * ρ * g * Q * H (单位: W)
            # 简化: P = 9.81 * Q * H * η / 1000 (单位: MW)
            head = self.hydraulic_head if self.hydraulic_head > 0 else (new_level - self.min_level)
            power = 9.81 * turbine_discharge * head * self.turbine_efficiency / 1000.0
            power = min(power, self.turbine_capacity)
        else:
            power = 0.0

        # 更新状态
        self.state = ReservoirState(
            volume=new_storage,
            level=new_level,
            storage=new_storage,
            water_level=new_level,
            inflow=inflow,
            outflow=outflow,
            spillway_discharge=spillway_discharge,
            turbine_discharge=turbine_discharge,
            ecological_discharge=self.ecological_flow,
            power_generation=power,
            dead_storage=self.dead_storage,
            active_storage=self.active_storage,
            flood_control_capacity=self.total_capacity - self.level_to_storage(self.flood_limit_level)
        )

        # 记录历史
        self.inflow_history.append(inflow)
        self.outflow_history.append(outflow)
        self.level_history.append(new_level)
        self.storage_history.append(new_storage)

        return self.state

    def update_reduced_order(self, dt: float, inputs: Dict) -> ReservoirState:
        """
        降阶模型仿真

        使用简化的水量平衡方程，忽略高阶项
        适用于长时间尺度仿真（小时级、日级）

        参数:
            dt: 时间步长 (通常为1小时或1天)
            inputs: 输入字典

        返回:
            更新后的水库状态
        """
        # 降阶模型使用相同的物理模型，但可以使用更大的时间步长
        # 在这里简化为直接调用高保真模型
        # 实际应用中可以使用更粗糙的数值格式或查表法
        return self.update_high_fidelity(dt, inputs)

    def _calculate_spillway_discharge(self, level: float, opening: float) -> float:
        """
        计算溢洪道泄量

        使用堰流公式: Q = C * L * opening * H^(3/2)
        其中 C = 流量系数, L = 堰长, H = 堰上水头

        参数:
            level: 当前水位 (m)
            opening: 溢洪道开度 (0-1)

        返回:
            溢洪道泄量 (m³/s)
        """
        if not self.has_spillway or opening <= 0:
            return 0.0

        # 超过防洪限制水位才泄洪
        if level <= self.flood_limit_level:
            return 0.0

        # 堰上水头
        head = level - self.flood_limit_level

        # 简化的堰流公式
        # Q = C * L * opening * H^(3/2)
        # 这里使用简化系数，实际应用中应根据水库特性校准
        discharge_coefficient = 2.0  # 流量系数
        weir_length = 50.0  # 假设堰长50m

        discharge = discharge_coefficient * weir_length * opening * (head ** 1.5)

        return min(discharge, self.max_discharge)

    def _constrain_outflow(self, outflow: float) -> float:
        """
        约束出流在可行范围内

        参数:
            outflow: 目标出流 (m³/s)

        返回:
            约束后的出流 (m³/s)
        """
        # 生态流量下限
        outflow = max(outflow, self.ecological_flow)
        # 最大泄流能力上限
        outflow = min(outflow, self.max_discharge)
        return outflow

    def _constrain_turbine_discharge(self, discharge: float) -> float:
        """
        约束水轮机流量在可行范围内

        参数:
            discharge: 目标水轮机流量 (m³/s)

        返回:
            约束后的流量 (m³/s)
        """
        if not self.has_turbine:
            return 0.0

        # 根据水轮机容量计算最大流量
        # P = 9.81 * Q * H * η / 1000
        # Q_max = P_max * 1000 / (9.81 * H * η)
        head = self.hydraulic_head if self.hydraulic_head > 0 else (self.state.water_level - self.min_level)
        if head > 0:
            max_turbine_flow = self.turbine_capacity * 1000.0 / (9.81 * head * self.turbine_efficiency)
            discharge = min(discharge, max_turbine_flow)

        return max(0, discharge)

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        """
        获取约束条件

        返回:
            约束字典，格式为 {变量名: (下界, 上界)}
        """
        return {
            'storage': (self.dead_storage, self.total_capacity),
            'water_level': (self.min_level, self.design_level),
            'outflow': (self.ecological_flow, self.max_discharge),
            'turbine_discharge': (0.0, self._get_max_turbine_flow()),
            'power_generation': (0.0, self.turbine_capacity)
        }

    def _get_max_turbine_flow(self) -> float:
        """获取水轮机最大流量"""
        if not self.has_turbine:
            return 0.0
        head = self.hydraulic_head if self.hydraulic_head > 0 else (self.state.water_level - self.min_level)
        if head > 0:
            return self.turbine_capacity * 1000.0 / (9.81 * head * self.turbine_efficiency)
        return 0.0

    def check_flood_control(self) -> bool:
        """
        检查防洪约束

        返回:
            True如果满足防洪约束，False否则
        """
        return self.state.water_level <= self.flood_limit_level

    def check_drought_control(self) -> bool:
        """
        检查抗旱约束

        返回:
            True如果满足抗旱约束，False否则
        """
        return self.state.storage >= self.dead_storage

    def check_ecological_flow(self) -> bool:
        """
        检查生态流量约束

        返回:
            True如果满足生态流量约束，False否则
        """
        return self.state.outflow >= self.ecological_flow

    def get_operation_status(self) -> Dict[str, any]:
        """
        获取运行状态报告

        返回:
            包含运行状态的字典
        """
        return {
            'reservoir_id': self.reservoir_id,
            'storage': self.state.storage,
            'storage_percent': self.state.storage / self.total_capacity * 100,
            'water_level': self.state.water_level,
            'inflow': self.state.inflow,
            'outflow': self.state.outflow,
            'power_generation': self.state.power_generation,
            'flood_control_ok': self.check_flood_control(),
            'drought_control_ok': self.check_drought_control(),
            'ecological_flow_ok': self.check_ecological_flow(),
            'active_storage_used': (self.state.storage - self.dead_storage) / self.active_storage * 100,
            'flood_control_capacity_used': (self.total_capacity - self.state.storage) / self.state.flood_control_capacity * 100
        }

    def reset(self, initial_storage: Optional[float] = None):
        """
        重置水库状态

        参数:
            initial_storage: 初始库容 (m³)，如果为None则使用默认值
        """
        if initial_storage is None:
            initial_storage = (self.dead_storage + self.total_capacity) / 2

        initial_level = float(self.storage_to_level(initial_storage))

        self.state = ReservoirState(
            volume=initial_storage,
            level=initial_level,
            storage=initial_storage,
            water_level=initial_level,
            dead_storage=self.dead_storage,
            active_storage=self.active_storage,
            flood_control_capacity=self.total_capacity - self.level_to_storage(self.flood_limit_level)
        )

        self.inflow_history = []
        self.outflow_history = []
        self.level_history = []
        self.storage_history = []


def create_reservoir_from_config(config: Dict) -> Reservoir:
    """
    从配置字典创建水库对象

    参数:
        config: 配置字典

    返回:
        Reservoir对象
    """
    # 提取必需参数
    reservoir_id = config['id']
    total_capacity = config['total_capacity']
    dead_storage = config['dead_storage']
    min_level = config['min_level']
    normal_level = config['normal_level']
    flood_limit_level = config['flood_limit_level']
    design_level = config['design_level']

    # 提取可选参数
    storage_curve_data = config.get('storage_curve_data', None)
    catchment_area = config.get('catchment_area', 0.0)
    ecological_flow = config.get('ecological_flow', 0.0)
    max_discharge = config.get('max_discharge', float('inf'))
    has_spillway = config.get('has_spillway', True)
    has_turbine = config.get('has_turbine', False)
    turbine_capacity = config.get('turbine_capacity', 0.0)
    hydraulic_head = config.get('hydraulic_head', 0.0)
    turbine_efficiency = config.get('turbine_efficiency', 0.85)

    return Reservoir(
        reservoir_id=reservoir_id,
        total_capacity=total_capacity,
        dead_storage=dead_storage,
        min_level=min_level,
        normal_level=normal_level,
        flood_limit_level=flood_limit_level,
        design_level=design_level,
        storage_curve_data=storage_curve_data,
        catchment_area=catchment_area,
        ecological_flow=ecological_flow,
        max_discharge=max_discharge,
        has_spillway=has_spillway,
        has_turbine=has_turbine,
        turbine_capacity=turbine_capacity,
        hydraulic_head=hydraulic_head,
        turbine_efficiency=turbine_efficiency
    )
