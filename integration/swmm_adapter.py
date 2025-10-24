"""
EPA SWMM (Storm Water Management Model) 集成模块

本模块提供与PySWMM的深度集成，用于城市雨洪模拟。

主要功能：
- SWMM模型的加载和运行
- 实时获取节点、管道、泵站等对象状态
- 与HydroClaude的控制系统集成
- 模拟结果的提取和可视化

安装PYSWMM:
pip install pyswmm

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Callable
from enum import Enum
import json
import os

# PYSWMM可选导入
try:
    from pyswmm import Simulation, Nodes, Links, SystemStats
    from pyswmm.swmm5 import PySWMM
    PYSWMM_AVAILABLE = True
except ImportError:
    PYSWMM_AVAILABLE = False
    print("警告: pyswmm未安装。请使用 'pip install pyswmm' 安装")


class SWMMObjectType(Enum):
    """SWMM对象类型"""
    NODE = "node"          # 节点（检查井、出水口等）
    LINK = "link"          # 连接（管道、堰等）
    SUBCATCHMENT = "subcatchment"  # 子汇水区
    PUMP = "pump"          # 泵站
    WEIR = "weir"          # 堰
    ORIFICE = "orifice"    # 孔口
    STORAGE = "storage"    # 调蓄单元


@dataclass
class SWMMNodeState:
    """SWMM节点状态"""
    id: str
    depth: float = 0.0  # 水深(m)
    head: float = 0.0  # 水头(m)
    volume: float = 0.0  # 体积(m³)
    lateral_inflow: float = 0.0  # 侧向入流(m³/s)
    total_inflow: float = 0.0  # 总入流(m³/s)
    flooding: float = 0.0  # 溢流量(m³/s)


@dataclass
class SWMMLinkState:
    """SWMM管道状态"""
    id: str
    flow: float = 0.0  # 流量(m³/s)
    depth: float = 0.0  # 水深(m)
    velocity: float = 0.0  # 流速(m/s)
    volume: float = 0.0  # 体积(m³)
    capacity: float = 0.0  # 充满度(0-1)


@dataclass
class SWMMPumpState:
    """SWMM泵站状态"""
    id: str
    flow: float = 0.0  # 流量(m³/s)
    status: int = 0  # 状态(0=关，1=开)
    power: float = 0.0  # 功率(kW)
    energy: float = 0.0  # 累计能耗(kWh)


@dataclass
class SWMMSystemState:
    """SWMM系统状态"""
    time: float  # 模拟时间(秒)
    routing_time: float = 0.0  # 总汇流时间(秒)
    runoff: float = 0.0  # 总径流量(m³/s)
    infiltration: float = 0.0  # 总下渗量(m³/s)
    evaporation: float = 0.0  # 总蒸发量(m³/s)
    rainfall: float = 0.0  # 总降雨量(mm)


class SWMMAdapter:
    """
    SWMM适配器类

    提供HydroClaude与SWMM模型的集成接口
    """

    def __init__(self, inp_file: str, rpt_file: Optional[str] = None, out_file: Optional[str] = None):
        """
        初始化SWMM适配器

        参数：
            inp_file: SWMM输入文件(.inp)
            rpt_file: 报告文件(.rpt)，可选
            out_file: 输出文件(.out)，可选
        """
        if not PYSWMM_AVAILABLE:
            raise ImportError("pyswmm未安装，无法使用SWMM功能")

        if not os.path.exists(inp_file):
            raise FileNotFoundError(f"SWMM输入文件不存在: {inp_file}")

        self.inp_file = inp_file
        self.rpt_file = rpt_file if rpt_file else inp_file.replace('.inp', '.rpt')
        self.out_file = out_file if out_file else inp_file.replace('.inp', '.out')

        self.sim = None
        self.is_running = False

        # 缓存对象
        self.nodes: Dict[str, Any] = {}
        self.links: Dict[str, Any] = {}
        self.pumps: Dict[str, Any] = {}

        # 状态历史
        self.time_history: List[float] = []
        self.node_states: Dict[str, List[SWMMNodeState]] = {}
        self.link_states: Dict[str, List[SWMMLinkState]] = {}
        self.pump_states: Dict[str, List[SWMMPumpState]] = {}
        self.system_states: List[SWMMSystemState] = []

        # 控制器
        self.controllers: Dict[str, Callable] = {}

    def initialize(self):
        """初始化SWMM模拟"""
        self.sim = Simulation(self.inp_file)
        self.sim.start()
        self.is_running = True

        # 获取所有对象
        self._load_objects()

    def _load_objects(self):
        """加载SWMM模型中的所有对象"""
        # 加载节点
        nodes = Nodes(self.sim)
        for node_id in nodes:
            self.nodes[node_id] = nodes[node_id]
            self.node_states[node_id] = []

        # 加载管道
        links = Links(self.sim)
        for link_id in links:
            link_obj = links[link_id]
            self.links[link_id] = link_obj
            self.link_states[link_id] = []

            # 识别泵站
            if hasattr(link_obj, 'type_name') and link_obj.type_name == 'PUMP':
                self.pumps[link_id] = link_obj
                self.pump_states[link_id] = []

    def step(self, dt: Optional[float] = None) -> bool:
        """
        执行一个时间步

        参数：
            dt: 时间步长(秒)，如果为None则使用SWMM的默认步长

        返回：
            bool: 是否继续模拟
        """
        if not self.is_running:
            raise RuntimeError("模拟未初始化，请先调用initialize()")

        # 执行控制逻辑
        current_time = self.sim.current_time
        for controller_id, controller in self.controllers.items():
            controller(self, current_time)

        # 推进时间步
        self.sim.step()

        # 记录状态
        self._record_states()

        # 检查是否结束
        if self.sim.current_time >= self.sim.end_time:
            self.is_running = False
            return False

        return True

    def _record_states(self):
        """记录当前时刻的状态"""
        current_time = self.sim.current_time.timestamp()
        self.time_history.append(current_time)

        # 记录节点状态
        for node_id, node in self.nodes.items():
            state = SWMMNodeState(
                id=node_id,
                depth=node.depth,
                head=node.head,
                volume=node.volume,
                lateral_inflow=node.lateral_inflow,
                total_inflow=node.total_inflow,
                flooding=node.flooding
            )
            self.node_states[node_id].append(state)

        # 记录管道状态
        for link_id, link in self.links.items():
            state = SWMMLinkState(
                id=link_id,
                flow=link.flow,
                depth=link.depth,
                velocity=link.velocity,
                volume=link.volume,
                capacity=link.capacity
            )
            self.link_states[link_id].append(state)

        # 记录泵站状态
        for pump_id, pump in self.pumps.items():
            state = SWMMPumpState(
                id=pump_id,
                flow=pump.flow,
                status=1 if pump.current_setting > 0 else 0,
                power=getattr(pump, 'power', 0.0),
                energy=getattr(pump, 'energy', 0.0)
            )
            self.pump_states[pump_id].append(state)

        # 记录系统状态
        system_stats = SystemStats(self.sim)
        state = SWMMSystemState(
            time=current_time,
            routing_time=system_stats.routing_time,
            runoff=system_stats.runoff,
            infiltration=system_stats.infiltration,
            evaporation=system_stats.evaporation,
            rainfall=system_stats.rainfall
        )
        self.system_states.append(state)

    def run_simulation(self, callback: Optional[Callable] = None):
        """
        运行完整模拟

        参数：
            callback: 每个时间步后的回调函数
        """
        self.initialize()

        while self.is_running:
            should_continue = self.step()

            if callback:
                callback(self, self.sim.current_time)

            if not should_continue:
                break

        self.finalize()

    def finalize(self):
        """结束模拟"""
        if self.sim:
            self.sim.close()
        self.is_running = False

    def get_node_state(self, node_id: str, time_index: int = -1) -> SWMMNodeState:
        """
        获取节点状态

        参数：
            node_id: 节点ID
            time_index: 时间索引（-1表示最新）
        """
        if node_id not in self.node_states:
            raise ValueError(f"节点 {node_id} 不存在")

        return self.node_states[node_id][time_index]

    def get_link_state(self, link_id: str, time_index: int = -1) -> SWMMLinkState:
        """
        获取管道状态

        参数：
            link_id: 管道ID
            time_index: 时间索引（-1表示最新）
        """
        if link_id not in self.link_states:
            raise ValueError(f"管道 {link_id} 不存在")

        return self.link_states[link_id][time_index]

    def get_pump_state(self, pump_id: str, time_index: int = -1) -> SWMMPumpState:
        """
        获取泵站状态

        参数：
            pump_id: 泵站ID
            time_index: 时间索引（-1表示最新）
        """
        if pump_id not in self.pump_states:
            raise ValueError(f"泵站 {pump_id} 不存在")

        return self.pump_states[pump_id][time_index]

    def set_pump_setting(self, pump_id: str, setting: float):
        """
        设置泵站运行状态

        参数：
            pump_id: 泵站ID
            setting: 设置值（0-1，0表示关闭，1表示全开）
        """
        if pump_id not in self.pumps:
            raise ValueError(f"泵站 {pump_id} 不存在")

        setting = np.clip(setting, 0.0, 1.0)
        self.pumps[pump_id].target_setting = setting

    def add_controller(self, controller_id: str, controller: Callable):
        """
        添加控制器

        参数：
            controller_id: 控制器ID
            controller: 控制函数，签名为 controller(adapter, current_time)
        """
        self.controllers[controller_id] = controller

    def remove_controller(self, controller_id: str):
        """移除控制器"""
        if controller_id in self.controllers:
            del self.controllers[controller_id]

    def export_results(self, output_file: str):
        """
        导出模拟结果到JSON文件

        参数：
            output_file: 输出文件路径
        """
        results = {
            'time': self.time_history,
            'nodes': {},
            'links': {},
            'pumps': {},
            'system': []
        }

        # 导出节点数据
        for node_id, states in self.node_states.items():
            results['nodes'][node_id] = {
                'depth': [s.depth for s in states],
                'head': [s.head for s in states],
                'flooding': [s.flooding for s in states],
            }

        # 导出管道数据
        for link_id, states in self.link_states.items():
            results['links'][link_id] = {
                'flow': [s.flow for s in states],
                'velocity': [s.velocity for s in states],
                'capacity': [s.capacity for s in states],
            }

        # 导出泵站数据
        for pump_id, states in self.pump_states.items():
            results['pumps'][pump_id] = {
                'flow': [s.flow for s in states],
                'status': [s.status for s in states],
                'energy': [s.energy for s in states],
            }

        # 导出系统数据
        results['system'] = [{
            'time': s.time,
            'runoff': s.runoff,
            'rainfall': s.rainfall,
        } for s in self.system_states]

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"模拟结果已导出到: {output_file}")


class SWMMPIDController:
    """
    SWMM泵站PID控制器

    用于根据水位控制泵站运行
    """

    def __init__(self, pump_id: str, target_node_id: str,
                 setpoint: float, kp: float = 1.0, ki: float = 0.1, kd: float = 0.05):
        """
        初始化PID控制器

        参数：
            pump_id: 泵站ID
            target_node_id: 目标节点ID（监测点）
            setpoint: 水位设定值(m)
            kp, ki, kd: PID参数
        """
        self.pump_id = pump_id
        self.target_node_id = target_node_id
        self.setpoint = setpoint
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.integral = 0.0
        self.last_error = 0.0

    def __call__(self, adapter: SWMMAdapter, current_time):
        """执行控制"""
        # 获取当前水位
        node = adapter.nodes[self.target_node_id]
        current_depth = node.depth

        # 计算误差
        error = current_depth - self.setpoint

        # PID计算
        self.integral += error
        derivative = error - self.last_error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        # 转换为泵站设置（0-1）
        setting = np.clip(output, 0.0, 1.0)

        # 设置泵站
        adapter.set_pump_setting(self.pump_id, setting)

        self.last_error = error


def create_simple_swmm_model(output_file: str):
    """
    创建一个简单的SWMM模型用于测试

    参数：
        output_file: 输出INP文件路径
    """
    inp_content = """[TITLE]
;;Project Title/Notes
Simple SWMM Model for HydroClaude Integration Test

[OPTIONS]
;;Option             Value
FLOW_UNITS           CMS
INFILTRATION         HORTON
FLOW_ROUTING         DYNWAVE
LINK_OFFSETS         DEPTH
MIN_SLOPE            0
ALLOW_PONDING        NO
SKIP_STEADY_STATE    NO

START_DATE           01/01/2025
START_TIME           00:00:00
REPORT_START_DATE    01/01/2025
REPORT_START_TIME    00:00:00
END_DATE             01/01/2025
END_TIME             06:00:00
SWEEP_START          01/01
SWEEP_END            12/31
DRY_DAYS             0
REPORT_STEP          00:05:00
WET_STEP             00:05:00
DRY_STEP             01:00:00
ROUTING_STEP         0:00:20

[JUNCTIONS]
;;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded
;;-------------- ---------- ---------- ---------- ---------- ----------
J1               100        5          0          0          0
J2               95         5          0          0          0
J3               90         5          0          0          0

[OUTFALLS]
;;Name           Elevation  Type       Stage Data       Gated    Route To
;;-------------- ---------- ---------- ---------------- -------- ----------------
OUT1             85         FREE                        NO

[STORAGE]
;;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Name/Params            N/A      Fevap    Psi      Ksat     IMD
;;-------------- -------- ---------- ----------- ---------- ---------------------------- -------- --------          -------- --------
TANK1            100      10         0          TABULAR    TANK1_CURVE                  0        0

[CONDUITS]
;;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  InitFlow   MaxFlow
;;-------------- ---------------- ---------------- ---------- ---------- ---------- ---------- ---------- ----------
C1               J1               J2               200        0.013      0          0          0          0
C2               J2               J3               200        0.013      0          0          0          0
C3               J3               OUT1             200        0.013      0          0          0          0

[PUMPS]
;;Name           From Node        To Node          Pump Curve       Status   Sartup Shutdown
;;-------------- ---------------- ---------------- ---------------- ------ -------- --------
PUMP1            TANK1            J1               PUMP1_CURVE      ON       0        0

[XSECTIONS]
;;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    Culvert
;;-------------- ------------ ---------------- ---------- ---------- ---------- ---------- ----------
C1               CIRCULAR     1.0              0          0          0          1
C2               CIRCULAR     1.0              0          0          0          1
C3               CIRCULAR     1.0              0          0          0          1

[INFLOWS]
;;Node           Constituent      Time Series      Type     Mfactor  Sfactor  Baseline Pattern
;;-------------- ---------------- ---------------- -------- -------- -------- -------- --------
J1               FLOW             INFLOW_TS        FLOW     1.0      1.0

[CURVES]
;;Name           Type       X-Value    Y-Value
;;-------------- ---------- ---------- ----------
PUMP1_CURVE      Pump4      0          0.1
PUMP1_CURVE                 5          0.2
TANK1_CURVE      Storage    0          100
TANK1_CURVE                 5          500
TANK1_CURVE                 10         1000

[TIMESERIES]
;;Name           Date       Time       Value
;;-------------- ---------- ---------- ----------
INFLOW_TS                   0:00       0.05
INFLOW_TS                   1:00       0.15
INFLOW_TS                   2:00       0.25
INFLOW_TS                   3:00       0.15
INFLOW_TS                   4:00       0.10
INFLOW_TS                   5:00       0.05

[REPORT]
;;Reporting Options
SUBCATCHMENTS ALL
NODES ALL
LINKS ALL

[TAGS]

[MAP]
DIMENSIONS 0.000 0.000 10000.000 10000.000
Units      None

[COORDINATES]
;;Node           X-Coord            Y-Coord
;;-------------- ------------------ ------------------
J1               2000.000           8000.000
J2               4000.000           8000.000
J3               6000.000           8000.000
OUT1             8000.000           8000.000
TANK1            1000.000           9000.000

[VERTICES]
;;Link           X-Coord            Y-Coord
;;-------------- ------------------ ------------------

[END]
"""

    with open(output_file, 'w') as f:
        f.write(inp_content)

    print(f"SWMM模型已创建: {output_file}")


# 导出
__all__ = [
    'SWMMAdapter',
    'SWMMPIDController',
    'SWMMObjectType',
    'SWMMNodeState',
    'SWMMLinkState',
    'SWMMPumpState',
    'SWMMSystemState',
    'create_simple_swmm_model',
    'PYSWMM_AVAILABLE',
]
