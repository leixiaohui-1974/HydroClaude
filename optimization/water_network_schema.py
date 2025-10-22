"""
通用水网调度模型的数据结构定义。

本文件基于 TypedDict 约束节点、边、时间序列及多目标权重，
保证最小测试网络与复杂拓扑共用同一套接口，并为 IDE/静态分析提供类型提示。
"""

from typing import Dict, List, Literal, Optional, Tuple, TypedDict


class NodeStateSpec(TypedDict, total=False):
    """
    节点状态变量配置。

    - initial: 初始值，用于初始化库存或水位等状态；
    - bounds: 上下界（下界, 上界），缺省时由模型自行处理；
    - piecewise: 分段线性化设置，键为输出状态名，值为 (自变量列表, 函数值列表)；
    - role: 状态变量角色，storage 表示参与质量守恒，level/auxiliary 表示辅助变量。
    """

    initial: float
    bounds: Tuple[Optional[float], Optional[float]]
    piecewise: Dict[str, Tuple[List[float], List[float]]]
    role: Literal["storage", "level", "auxiliary"]


class NodeAttrSpec(TypedDict, total=False):
    """
    节点属性配置。

    - elevation: 节点代表的水位或高程基准；
    - storage_curve: 库容-水位分段线性数据；
    - demand_profile: 需求时间序列名称（对应全局时间序列库的键）；
    - shortage_penalty: 节点缺水惩罚系数，未提供时回退到全局权重；
    - misc: 其他扩展属性，统一以键值对形式存储。
    """

    elevation: float
    storage_curve: Tuple[List[float], List[float]]
    demand_profile: str
    shortage_penalty: float
    misc: Dict[str, float]


class NodeSpec(TypedDict, total=False):
    """
    节点定义。

    - id: 全局唯一标识；
    - name: 便于识别的名称；
    - kind: 节点类型，用于匹配模型模板；
    - states: 节点状态变量映射，例如库容、泵站水位等；
    - attributes: 节点参数化属性；
    - exogenous_series: 与节点直接相关的外生时间序列键列表。
    """

    id: str
    name: str
    kind: Literal[
        "reservoir",
        "junction",
        "demand",
        "source",
        "sink",
        "pump_station",
        "gate",
        "hydropower",
        "storage_pool",
    ]
    states: Dict[str, NodeStateSpec]
    attributes: NodeAttrSpec
    exogenous_series: List[str]


class EdgeAttrSpec(TypedDict, total=False):
    """
    边属性配置。

    - length: 输水距离或管道长度；
    - loss_factor: 线性水头损失系数；
    - capacity: 流量容量上限；
    - efficiency_curve: 分段线性效率曲线（流量, 效率）；
    - control_mode: 控制模式，例如“自由泄流”“阀门开度”“泵转速”；
    - energy_cost: 单位流量的能耗（正值）或收益（负值）系数。
    """

    length: float
    loss_factor: float
    capacity: float
    efficiency_curve: Tuple[List[float], List[float]]
    control_mode: str
    energy_cost: float


class EdgeSpec(TypedDict, total=False):
    """
    边定义。

    - id: 全局唯一标识；
    - name: 便于识别的名称；
    - kind: 边类型，用于加载对应的约束模板；
    - from_node: 起点节点 id；
    - to_node: 终点节点 id；
    - attributes: 边参数集合；
    - exogenous_series: 与该边相关的外生时间序列键列表。
    """

    id: str
    name: str
    kind: Literal[
        "open_channel",
        "pipeline",
        "pump",
        "gate_flow",
        "turbine",
        "spillway",
        "gravity",
    ]
    from_node: str
    to_node: str
    attributes: EdgeAttrSpec
    exogenous_series: List[str]


class SeriesSpec(TypedDict, total=False):
    """
    时间序列配置。

    - times: 时间索引列表，需与模型调度步长一致；
    - values: 数值序列；
    - default: 当时间轴超出给定长度时的默认填充值；
    - units: 单位说明，方便报表展示。
    """

    times: List[str]
    values: List[float]
    default: float
    units: str


class ObjectiveWeightSpec(TypedDict, total=False):
    """
    多目标权重配置。

    - energy_revenue: 水电收益权重；
    - pumping_cost: 泵站能耗成本权重；
    - shortage_penalty: 供水缺额惩罚；
    - flood_risk: 防洪风险惩罚；
    - ecological: 生态需求惩罚；
    - navigation: 通航水位偏差惩罚。
    """

    energy_revenue: float
    pumping_cost: float
    shortage_penalty: float
    flood_risk: float
    ecological: float
    navigation: float


class PolicySpec(TypedDict, total=False):
    """
    控制策略与运行约束配置。

    - ramp_limits: 各边或机组的爬坡率约束；
    - min_up_down: 泵站或机组最小开停机时间；
    - reserve_margin: 安全储备或备用水位要求；
    - priority: 供水优先级，便于分层求解或目标分段。
    """

    ramp_limits: Dict[str, float]
    min_up_down: Dict[str, Tuple[int, int]]
    reserve_margin: Dict[str, float]
    priority: Dict[str, int]


class NetworkConfig(TypedDict, total=False):
    """
    水网整体配置入口。

    - metadata: 元信息，如名称、版本、作者等；
    - horizon: 时间范围描述（起始、步长、单位或离散序列）；
    - nodes: 节点列表；
    - edges: 边列表；
    - series: 时间序列库；
    - objective_weights: 多目标权重；
    - policies: 运行策略集合。
    """

    metadata: Dict[str, str]
    horizon: Dict[str, str]
    nodes: List[NodeSpec]
    edges: List[EdgeSpec]
    series: Dict[str, SeriesSpec]
    objective_weights: ObjectiveWeightSpec
    policies: PolicySpec


class MPCConfig(TypedDict, total=False):
    """
    串联闸泵群模型预测控制配置。

    - sample_time: 采样时间步长；
    - prediction_horizon: 预测窗口长度；
    - control_horizon: 控制窗口长度；
    - state_weight: 状态误差权重；
    - control_weight: 控制增量权重。
    """

    sample_time: float
    prediction_horizon: int
    control_horizon: int
    state_weight: float
    control_weight: float


class ScenarioConfig(TypedDict, total=False):
    """
    情景模拟配置。

    - name: 情景名称；
    - overrides: 对基础配置的覆盖字典，可递归生效；
    - probability: 情景概率，用于期望值或风险度量。
    """

    name: str
    overrides: Dict[str, object]
    probability: float


class DeploymentConfig(TypedDict, total=False):
    """
    部署与接口配置。

    - realtime_endpoint: 实时数据接口地址；
    - control_channels: 控制命令下发通道列表；
    - logging: 日志与回溯设置。
    """

    realtime_endpoint: str
    control_channels: List[str]
    logging: Dict[str, str]


class WaterNetworkModelPack(TypedDict, total=False):
    """
    通用水网模型整体包络。

    - network: 基础网络配置；
    - scenarios: 情景列表；
    - mpc: 串联闸泵 MPC 配置；
    - deployment: 部署相关设置。
    """

    network: NetworkConfig
    scenarios: List[ScenarioConfig]
    mpc: MPCConfig
    deployment: DeploymentConfig

