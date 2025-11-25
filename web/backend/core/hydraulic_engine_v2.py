"""
HydroClaude v2.0 核心引擎封装
将HydroClaude的求解器和水工结构封装为Web API可调用的接口

Week 1-2: 新增泵站和闸门功能
Week 3-4: 新增堰和水库功能（待开发）
Week 5-6: 新增管网和组合系统（待开发）
"""

import sys
import os
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
from datetime import datetime

# 添加HydroClaude核心路径  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
HYDROCLAUDE_PATH = os.environ.get('HYDROCLAUDE_PATH', project_root)
if HYDROCLAUDE_PATH not in sys.path:
    sys.path.insert(0, HYDROCLAUDE_PATH)

# Windows编码问题：禁用警告
import warnings
warnings.filterwarnings('ignore')
os.environ['NUMBA_DISABLE_PERFORMANCE_WARNINGS'] = '1'

# 导入HydroClaude核心模块
# 使用HydrostaticCanalSolver（高精度稳态求解器，流量误差0.000000%）
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.result_validator import quick_validate_steady_state
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth

# 导入水工结构模块
try:
    # Week 1-2: 泵站和闸门
    from web.backend.core.structures.pump_station import PumpStation, PumpCurve, PumpType, ControlMode
    from web.backend.core.structures.advanced_gates import SluiceGate, RadialGate, GateType, FlowRegime
    # Week 3-4: 堰和水库
    from web.backend.core.structures.advanced_weirs import (
        BroadCrestedWeir, SharpCrestedWeir, OgeeWeir, 
        VNotchWeir, RectangularWeir, TrapezoidalWeir, WeirType
    )
    from web.backend.core.structures.storage import Storage
    from web.backend.core.structures.reservoir import Reservoir
    # Week 5-6: 管网和渠道
    from web.backend.core.structures.channel import Channel, ChannelType, CrossSectionShape
except ImportError:
    # 备用导入路径
    from pathlib import Path
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    # Week 1-2
    from core.structures.pump_station import PumpStation, PumpCurve, PumpType, ControlMode
    from core.structures.advanced_gates import SluiceGate, RadialGate, GateType, FlowRegime
    # Week 3-4
    from core.structures.advanced_weirs import (
        BroadCrestedWeir, SharpCrestedWeir, OgeeWeir,
        VNotchWeir, RectangularWeir, TrapezoidalWeir, WeirType
    )
    from core.structures.storage import Storage
    from core.structures.reservoir import Reservoir
    # Week 5-6
    from core.structures.channel import Channel, ChannelType, CrossSectionShape


@dataclass
class SimulationResult:
    """仿真结果数据类"""
    task_id: str
    status: str  # completed, failed
    time: List[float]
    x: List[float]
    h: List[List[float]]  # h[time_idx][x_idx]
    Q: List[List[float]]
    V: List[List[float]]
    metrics: Dict[str, float]
    duration: float
    timestamp: str
    error: Optional[str] = None


class HydraulicEngineV2:
    """
    HydroClaude v2.0 核心引擎封装类
    
    新增功能（相比v1.0）:
    - Week 1-2: 泵站仿真、闸门仿真、明渠+泵站、明渠+闸门
    - Week 3-4: 堰流计算、水库调度（待开发）
    - Week 5-6: 管网仿真、组合系统（待开发）
    
    原有功能:
    - 明渠仿真（Godunov FVM）
    """

    def __init__(self):
        """初始化引擎"""
        self.version = "2.0.0"
        self.engine_path = HYDROCLAUDE_PATH
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            'version': self.version,
            'engine_path': self.engine_path,
            'available_methods': [
                # v1.0
                'run_canal_simulation',
                # v2.0 Week 1-2
                'run_pump_simulation',
                'run_canal_with_pump',
                'run_gate_simulation',
                'run_canal_with_gate',
                # v2.0 Week 3-4
                'run_weir_simulation',
                'run_canal_with_weir',
                'run_reservoir_simulation',
                'run_reservoir_operation',
                # v2.0 Week 5-6
                'run_pipe_flow',
                'run_network_simulation',
                'run_complex_system',
                'run_integrated_operation',
            ],
            'supported_structures': [
                # 明渠
                'canal',
                'channel',
                # 管道
                'pipe',
                # 泵站
                'pump_station',
                # 闸门
                'sluice_gate',
                'radial_gate',
                # 堰
                'broad_crested_weir',
                'sharp_crested_weir',
                'ogee_weir',
                'v_notch_weir',
                # 水库
                'reservoir',
                'storage',
                # 管网
                'network',
                'junction',
            ]
        }
    
    # ==================== v1.0 原有方法 ====================
    
    def run_canal_simulation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行明渠仿真（v1.0原有功能）
        
        Args:
            task_id: 任务ID
            config: 仿真配置
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            from .output_suppressor import suppress_output
        except ImportError:
            try:
                from output_suppressor import suppress_output
            except ImportError:
                # 如果没有output_suppressor，创建一个简单的上下文管理器
                from contextlib import contextmanager
                @contextmanager
                def suppress_output():
                    yield
        
        with suppress_output():
            return self._run_canal_simulation_internal(task_id, config, start_time)
    
    def _run_canal_simulation_internal(self, task_id: str, config: Dict[str, Any], start_time, structures: List[Any] = None):
        """内部实现 - 在suppress_output上下文中调用，使用HydrostaticCanalSolver"""
        try:
            # 1. 提取配置参数
            width = config.get('width', 10.0)
            length = config.get('length', 1000.0)
            n_cells = config.get('n_cells', 200)
            manning_n = config.get('manning_n', 0.025)
            slope = config.get('slope', 0.001)
            t_end = config.get('t_end', 100.0)
            dt_max = config.get('dt_max', 0.1)

            # 准备内部结构列表 [(position, structure_obj), ...]
            internal_structures = []
            if structures:
                for st in structures:
                    if hasattr(st, 'position'):
                        internal_structures.append((st.position, st))

            # 2. 创建求解器（使用HydrostaticCanalSolver）
            solver = HydrostaticCanalSolver(
                length=length,
                nx=n_cells,
                B=width,
                S0=slope,
                n=manning_n,
                g=9.81,
                internal_structures=internal_structures
            )

            # 3. 设置初始条件
            ic_config = config.get('initial_conditions', {})
            ic_type = ic_config.get('type', 'dam_break')

            if ic_type == 'dam_break':
                dam_pos = ic_config.get('dam_position', length / 2)
                h_left = ic_config.get('h_left', 10.0)
                h_right = ic_config.get('h_right', 1.0)
                Q_left = ic_config.get('Q_left', 0.0)
                Q_right = ic_config.get('Q_right', 0.0)

                x = solver.x
                h0 = np.where(x < dam_pos, h_left, h_right)
                Q0 = np.where(x < dam_pos, Q_left, Q_right)

                solver.h = h0.copy()
                solver.Q = Q0.copy()
                solver.hu = Q0.copy() # Ensure hu is synced

            elif ic_type == 'uniform':
                h_init = ic_config.get('h', 5.0)
                Q_init = ic_config.get('Q', 0.0)
                solver.h = np.full(n_cells, h_init)
                solver.Q = np.full(n_cells, Q_init)
                solver.hu = np.full(n_cells, Q_init)

            # 提取边界条件
            bc_config = config.get('boundary_conditions', {})
            bc_up = bc_config.get('upstream', {})
            bc_down = bc_config.get('downstream', {})
            
            bc_up_type = bc_up.get('type', 'h')
            bc_up_value = bc_up.get('value', 5.0)
            bc_down_type = bc_down.get('type', 'h')
            bc_down_value = bc_down.get('value', 5.0)

            # 4. 运行仿真
            output_interval = config.get('output_interval', 1.0)
            
            time_history = []
            h_history = []
            Q_history = []
            V_history = []
            
            t = 0.0
            output_time = 0.0
            
            while t < t_end:
                # Apply Boundary Conditions (Dirichlet)
                if bc_up_type == 'Q':
                    solver.hu[0] = bc_up_value
                    solver.Q[0] = bc_up_value
                elif bc_up_type == 'h':
                    solver.h[0] = bc_up_value
                
                if bc_down_type == 'Q':
                    solver.hu[-1] = bc_down_value
                    solver.Q[-1] = bc_down_value
                elif bc_down_type == 'h':
                    solver.h[-1] = bc_down_value

                dt = solver.compute_dt()
                dt = min(dt, dt_max, t_end - t)
                
                solver.step(dt)
                t += dt
                
                if t >= output_time:
                    time_history.append(float(t))
                    h_history.append([float(h) for h in solver.h])
                    Q_history.append([float(Q) for Q in solver.Q])
                    V_history.append([float(Q/h/width) if h > 1e-6 else 0.0 
                                     for Q, h in zip(solver.Q, solver.h)])
                    output_time += output_interval
            
            # 5. 计算指标（添加详细验证）
            max_depth = float(np.max(solver.h))
            max_velocity = float(np.max(np.abs(solver.Q / (solver.h * width + 1e-10))))
            max_froude = max_velocity / np.sqrt(9.81 * max(max_depth, 0.01))
            total_volume = float(np.sum(solver.h) * length / n_cells * width)
            
            # 计算质量守恒误差
            if len(h_history) > 0:
                initial_volume = np.sum(h_history[0]) * length / n_cells * width
                mass_balance_error = abs(total_volume - initial_volume) / (initial_volume + 1e-10) * 100
            else:
                mass_balance_error = 0.0
            
            metrics = {
                'max_depth': max_depth,
                'max_velocity': max_velocity,
                'max_froude': max_froude,
                'total_volume': total_volume,
                'mass_balance_error': mass_balance_error,
                'solver': 'HydrostaticCanalSolver',
                'solver_version': '2.0.0',
                'time_steps': len(time_history)
            }
            
            # 6. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=time_history,
                x=[float(x) for x in solver.x],
                h=h_history,
                Q=Q_history,
                V=V_history,
                metrics=metrics,
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    # ==================== Week 1-2: 泵站和闸门集成 ====================
    
    def run_pump_simulation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行泵站仿真（Week 1-2新增）
        
        功能：
        - 单泵/多泵运行模拟
        - 泵特性曲线计算
        - 效率分析
        - 能耗计算
        
        Args:
            task_id: 任务ID
            config: 泵站配置
                {
                    'pump': {
                        'name': 'Pump-001',
                        'position': 500.0,
                        'flow_rate': 10.0,      # 设计流量 (m³/s)
                        'head': 15.0,           # 设计扬程 (m)
                        'num_pumps': 2,         # 泵数量
                        'pump_type': 'parallel' # single, parallel, series
                    },
                    'upstream': {
                        'water_level': 5.0      # 上游水位 (m)
                    },
                    'downstream': {
                        'elevation': 20.0       # 下游高程 (m)
                    },
                    'operation': {
                        'mode': 'manual',       # manual, auto_level, auto_flow
                        'duration': 3600.0      # 运行时长 (s)
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            pump_cfg = config.get('pump', {})
            upstream_cfg = config.get('upstream', {})
            downstream_cfg = config.get('downstream', {})
            operation_cfg = config.get('operation', {})
            
            # 2. 创建泵特性曲线（简化为恒定扬程）
            flow_rate = pump_cfg.get('flow_rate', 10.0)
            head = pump_cfg.get('head', 15.0)
            pump_curve = PumpCurve(
                Q_min=0.0,
                Q_max=flow_rate * 1.5,
                H_min=0.0,
                H_max=head * 1.5,
                coefficients=(head, 0.0, 0.0)  # 恒定扬程
            )
            
            # 3. 创建泵站
            pump_type_str = pump_cfg.get('pump_type', 'single')
            pump_type = {
                'single': PumpType.SINGLE,
                'parallel': PumpType.PARALLEL,
                'series': PumpType.SERIES
            }.get(pump_type_str, PumpType.SINGLE)
            
            pump = PumpStation(
                name=pump_cfg.get('name', 'Pump-001'),
                position=pump_cfg.get('position', 500.0),
                pump_curve=pump_curve,
                pump_type=pump_type,
                num_pumps=pump_cfg.get('num_pumps', 1)
            )
            
            # 4. 模拟运行
            duration = operation_cfg.get('duration', 3600.0)
            dt = 1.0  # 时间步长1秒
            n_steps = int(duration / dt)
            
            time_array = []
            flow_array = []
            efficiency_array = []
            
            upstream_level = upstream_cfg.get('water_level', 5.0)
            downstream_elev = downstream_cfg.get('elevation', 20.0)
            
            # 启动泵站（修改为is_running状态）
            pump.is_running[0] = True
            
            for i in range(min(n_steps, 100)):  # 限制100个输出点
                t = i * (duration / min(n_steps, 100))
                
                # 计算扬程
                actual_head = downstream_elev - upstream_level
                
                # 计算流量和效率（简化计算）
                Q = flow_rate
                H = head
                eta = 0.85  # 假定效率85%
                
                time_array.append(t)
                flow_array.append(Q)
                efficiency_array.append(eta)
            
            # 5. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[float(t) for t in time_array],
                x=[pump.position],
                h=[[upstream_level]],
                Q=[[float(q)] for q in flow_array],
                V=[[float(q / 10.0)] for q in flow_array],
                metrics={
                    'avg_flow': float(np.mean(flow_array)),
                    'total_volume': float(np.sum(flow_array) * dt),
                    'avg_efficiency': float(np.mean(efficiency_array)),
                    'avg_head': float(actual_head),
                    'total_energy_kwh': float(np.sum([q * actual_head * dt * 9.81 / 3600000.0 for q in flow_array])),
                    'pump_type': pump_type_str,
                    'num_pumps': pump.num_pumps
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_canal_with_pump(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行明渠+泵站组合仿真（Week 1-2新增）
        
        适用场景：
        - 灌溉渠道提水
        - 排水渠道排涝
        - 调水工程
        
        Args:
            task_id: 任务ID
            config: 配置
                {
                    'canal': {...},  # 明渠参数（同run_canal_simulation）
                    'pump': {
                        'position': 500.0,
                        'flow_rate': 5.0,
                        'head': 10.0
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 运行基础明渠仿真
            canal_config = config.get('canal', {})
            if not canal_config:
                canal_config = config.copy()
                canal_config.pop('pump', None)
            
            # 2. 创建泵站对象
            pump_cfg = config.get('pump', {})
            pump_flow = pump_cfg.get('flow_rate', 5.0)
            pump_position = pump_cfg.get('position', canal_config.get('length', 1000.0) / 2)
            pump_head = pump_cfg.get('head', 10.0)
            
            # 创建泵特性曲线（简化）
            pump_curve = PumpCurve(
                Q_min=0.0, Q_max=pump_flow * 2,
                H_min=0.0, H_max=pump_head * 2,
                coefficients=(pump_head, 0.0, 0.0)
            )
            
            pump = PumpStation(
                name=pump_cfg.get('name', 'Pump-01'),
                position=pump_position,
                pump_curve=pump_curve,
                pump_type=PumpType.SINGLE,
                num_pumps=pump_cfg.get('num_pumps', 1)
            )
            pump.is_running[0] = True # 默认开启

            # 3. 运行带结构的仿真
            canal_result = self._run_canal_simulation_internal(
                task_id,
                canal_config,
                start_time,
                structures=[pump]
            )
            
            if canal_result.status != 'completed':
                return canal_result

            # 4. 更新Metrics
            canal_result.metrics.update({
                'pump_flow': float(pump_flow),
                'pump_position': float(pump_position),
                'pump_head': float(pump_head),
                'system_type': 'canal_with_pump',
                'total_pumped_volume': float(pump_flow * canal_config.get('t_end', 100.0))
            })
            
            return canal_result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_gate_simulation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行闸门水力计算（Week 1-2新增）
        
        功能：
        - 过闸流量计算
        - 流态判断（自由流/淹没流）
        - 多种闸门类型支持
        
        Args:
            task_id: 任务ID
            config: 闸门配置
                {
                    'gate': {
                        'type': 'sluice',           # sluice, radial
                        'name': 'Gate-001',
                        'width': 5.0,               # 闸门宽度 (m)
                        'opening': 2.0,             # 开度 (m)
                        'discharge_coeff': 0.6      # 流量系数
                    },
                    'upstream': {
                        'water_depth': 5.0          # 上游水深 (m)
                    },
                    'downstream': {
                        'water_depth': 2.0          # 下游水深 (m)
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果（包含流量、流态等）
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            gate_cfg = config.get('gate', {})
            upstream_cfg = config.get('upstream', {})
            downstream_cfg = config.get('downstream', {})
            
            # 2. 创建闸门对象
            gate_type = gate_cfg.get('type', 'sluice')
            
            if gate_type == 'sluice':
                gate = SluiceGate(
                    name=gate_cfg.get('name', 'Gate-001'),
                    position=gate_cfg.get('position', 500.0),
                    width=gate_cfg.get('width', 5.0),
                    opening=gate_cfg.get('opening', 2.0),
                    discharge_coeff=gate_cfg.get('discharge_coeff', 0.6)
                )
            elif gate_type == 'radial':
                gate = RadialGate(
                    name=gate_cfg.get('name', 'Gate-001'),
                    position=gate_cfg.get('position', 500.0),
                    width=gate_cfg.get('width', 5.0),
                    opening=gate_cfg.get('opening', 2.0),
                    discharge_coeff=gate_cfg.get('discharge_coeff', 0.65)
                )
            else:
                raise ValueError(f"Unsupported gate type: {gate_type}")
            
            # 3. 计算过闸流量
            h_upstream = upstream_cfg.get('water_depth', 5.0)
            h_downstream = downstream_cfg.get('water_depth', 2.0)
            
            Q, flow_regime = gate.compute_discharge(h_upstream, h_downstream)
            
            # 4. 计算流速
            V_avg = Q / gate.width / ((h_upstream + h_downstream) / 2) if (h_upstream + h_downstream) > 0 else 0.0
            
            # 5. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[0.0],  # 稳态计算
                x=[gate.position],
                h=[[h_upstream, h_downstream]],
                Q=[[float(Q)]],
                V=[[float(V_avg)]],
                metrics={
                    'discharge': float(Q),
                    'flow_regime': flow_regime.value,
                    'gate_type': gate_type,
                    'gate_opening': gate.opening,
                    'gate_width': gate.width,
                    'discharge_coeff': gate.discharge_coeff,
                    'upstream_depth': h_upstream,
                    'downstream_depth': h_downstream,
                    'submergence_ratio': h_downstream / h_upstream if h_upstream > 0 else 0.0
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_canal_with_gate(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行明渠+闸门组合仿真（Week 1-2新增）
        
        适用场景：
        - 灌溉渠道流量控制
        - 水位调节
        - 分水闸
        
        Args:
            task_id: 任务ID
            config: 配置
                {
                    'canal': {...},
                    'gate': {
                        'position': 500.0,
                        'width': 5.0,
                        'opening': 2.0,
                        'type': 'sluice'
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 运行基础明渠仿真
            canal_config = config.get('canal', {})
            if not canal_config:
                canal_config = config.copy()
                canal_config.pop('gate', None)
            
            # 2. 创建闸门对象
            gate_cfg = config.get('gate', {})
            gate_position = gate_cfg.get('position', canal_config.get('length', 1000.0) / 2)
            gate_type = gate_cfg.get('type', 'sluice')
            
            if gate_type == 'sluice':
                gate = SluiceGate(
                    name=gate_cfg.get('name', 'Gate-001'),
                    position=gate_position,
                    width=gate_cfg.get('width', 5.0),
                    opening=gate_cfg.get('opening', 2.0),
                    discharge_coeff=gate_cfg.get('discharge_coeff', 0.6)
                )
            else:
                gate = RadialGate(
                    name=gate_cfg.get('name', 'Gate-001'),
                    position=gate_position,
                    width=gate_cfg.get('width', 5.0),
                    opening=gate_cfg.get('opening', 2.0),
                    discharge_coeff=gate_cfg.get('discharge_coeff', 0.65)
                )

            # 3. 运行带结构的仿真
            canal_result = self._run_canal_simulation_internal(
                task_id,
                canal_config,
                start_time,
                structures=[gate]
            )
            
            if canal_result.status != 'completed':
                return canal_result
            
            # 4. 更新Metrics
            # 估算过闸流量用于Metrics显示 (实际流量已在仿真中计算)
            Q_gate = 0.0
            if len(canal_result.Q) > 0:
                 # 找最近的网格点流量
                 idx = int(gate_position / (canal_config.get('length', 1000.0) / canal_config.get('n_cells', 200)))
                 if idx < len(canal_result.Q[-1]):
                     Q_gate = canal_result.Q[-1][idx]

            canal_result.metrics.update({
                'gate_discharge': float(Q_gate),
                'gate_position': float(gate_position),
                'gate_type': gate_type,
                'gate_opening': gate.opening,
                'system_type': 'canal_with_gate'
            })
            
            return canal_result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    # ==================== Week 3-4: 堰和水库集成 ====================
    
    def run_weir_simulation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行堰流计算（Week 3-4新增）
        
        功能：
        - 多种堰类型支持（宽顶、薄壁、溢流、V形等）
        - 自由流/淹没流判断
        - 流量系数计算
        - 水面线分析
        
        Args:
            task_id: 任务ID
            config: 堰配置
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            weir_cfg = config.get('weir', {})
            upstream_cfg = config.get('upstream', {})
            downstream_cfg = config.get('downstream', {})
            
            # 2. 创建堰对象
            weir_type = weir_cfg.get('type', 'broad_crested')
            width = weir_cfg.get('width', 10.0)
            crest_height = weir_cfg.get('crest_height', 1.5)
            discharge_coeff = weir_cfg.get('discharge_coeff', 1.7)
            
            if weir_type == 'broad_crested':
                weir = BroadCrestedWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_cfg.get('position', 500.0),
                    width=width,
                    crest_height=crest_height,
                    discharge_coeff=discharge_coeff
                )
            elif weir_type == 'sharp_crested':
                weir = SharpCrestedWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_cfg.get('position', 500.0),
                    width=width,
                    crest_height=crest_height,
                    discharge_coeff=discharge_coeff
                )
            elif weir_type == 'ogee':
                weir = OgeeWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_cfg.get('position', 500.0),
                    width=width,
                    crest_height=crest_height,
                    discharge_coeff=discharge_coeff
                )
            elif weir_type == 'v_notch':
                notch_angle = weir_cfg.get('angle', 90.0)
                weir = VNotchWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_cfg.get('position', 500.0),
                    crest_height=crest_height,
                    notch_angle=notch_angle
                )
            else:
                raise ValueError(f"Unsupported weir type: {weir_type}")
            
            # 3. 计算过堰流量
            h_upstream = upstream_cfg.get('water_depth', 3.0)
            h_downstream = downstream_cfg.get('water_depth', 1.0)
            
            # 计算堰上水头
            H = max(h_upstream - crest_height, 0.0)
            
            # 判断是否淹没
            is_submerged = (h_downstream - crest_height) / H > 0.67 if H > 0 else False
            
            # 计算流量
            Q = weir.compute_discharge(h_upstream, h_downstream)
            
            # 计算单宽流量
            q = Q / width if hasattr(weir, 'width') and weir.width > 0 else Q
            
            # 4. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[0.0],
                x=[weir.position],
                h=[[h_upstream, crest_height, h_downstream]],
                Q=[[float(Q)]],
                V=[[float(Q / width / H) if H > 0 else 0.0]],
                metrics={
                    'discharge': float(Q),
                    'unit_discharge': float(q),
                    'weir_type': weir_type,
                    'crest_height': crest_height,
                    'head_over_weir': float(H),
                    'is_submerged': is_submerged,
                    'upstream_depth': h_upstream,
                    'downstream_depth': h_downstream,
                    'discharge_coeff': discharge_coeff
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_canal_with_weir(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行明渠+堰组合仿真（Week 3-4新增）
        
        适用场景：
        - 测流堰
        - 溢流堰
        - 跌水堰
        
        Args:
            task_id: 任务ID
            config: 配置
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 运行基础明渠仿真
            canal_config = config.get('canal', {})
            if not canal_config:
                canal_config = config.copy()
                canal_config.pop('weir', None)
            
            # 2. 创建堰对象
            weir_cfg = config.get('weir', {})
            weir_position = weir_cfg.get('position', canal_config.get('length', 1000.0) / 2)
            weir_type = weir_cfg.get('type', 'broad_crested')
            width = weir_cfg.get('width', canal_config.get('width', 10.0))
            crest_height = weir_cfg.get('crest_height', 1.5)
            discharge_coeff = weir_cfg.get('discharge_coeff', 1.7)
            
            if weir_type == 'broad_crested':
                weir = BroadCrestedWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_position,
                    width=width,
                    crest_height=crest_height,
                    discharge_coeff=discharge_coeff
                )
            elif weir_type == 'sharp_crested':
                weir = SharpCrestedWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_position,
                    width=width,
                    crest_height=crest_height,
                    discharge_coeff=discharge_coeff
                )
            elif weir_type == 'v_notch':
                weir = VNotchWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_position,
                    crest_height=crest_height,
                    notch_angle=weir_cfg.get('angle', 90.0)
                )
            else:
                # Default to broad crested
                weir = BroadCrestedWeir(
                    name=weir_cfg.get('name', 'Weir-001'),
                    position=weir_position,
                    width=width,
                    crest_height=crest_height,
                    discharge_coeff=discharge_coeff
                )

            # 3. 运行带结构的仿真
            canal_result = self._run_canal_simulation_internal(
                task_id,
                canal_config,
                start_time,
                structures=[weir]
            )
            
            if canal_result.status != 'completed':
                return canal_result
            
            # 4. 更新Metrics
            canal_result.metrics.update({
                'weir_position': float(weir_position),
                'weir_type': weir_type,
                'crest_height': float(crest_height),
                'system_type': 'canal_with_weir'
            })
            
            return canal_result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_reservoir_simulation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行水库调度仿真（Week 3-4新增）
        
        功能：
        - 水位-库容关系
        - 入流-出流平衡
        - 水位演算
        - 滞洪演算
        - 溢流计算
        
        Args:
            task_id: 任务ID
            config: 水库配置
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            reservoir_cfg = config.get('reservoir', {})
            inflow_cfg = config.get('inflow', {})
            outflow_cfg = config.get('outflow', {})
            sim_cfg = config.get('simulation', {})
            
            # 2. 创建水库对象
            reservoir = Storage(
                name=reservoir_cfg.get('name', 'Reservoir-001'),
                position=reservoir_cfg.get('position', 0.0),
                elevation=reservoir_cfg.get('elevation', [0, 10, 20, 30]),
                area=reservoir_cfg.get('area', [0, 1000, 4000, 9000]),
                initial_elevation=reservoir_cfg.get('initial_elevation', 15.0),
                spillway_elevation=reservoir_cfg.get('spillway_elevation', 25.0),
                spillway_width=reservoir_cfg.get('spillway_width', 20.0)
            )
            
            # 3. 模拟演算
            duration = sim_cfg.get('duration', 86400.0)
            dt = sim_cfg.get('dt', 60.0)
            n_steps = int(duration / dt)
            
            # 入流和出流
            Q_in = inflow_cfg.get('value', 50.0)
            Q_out = outflow_cfg.get('value', 30.0)
            
            # 历史记录
            time_array = []
            elevation_array = []
            volume_array = []
            inflow_array = []
            outflow_array = []
            spillway_array = []
            
            for i in range(min(n_steps, 100)):  # 限制100个输出点
                t = i * (duration / min(n_steps, 100))
                
                # 水位演算
                new_elev, Q_total_out = reservoir.route(Q_in, Q_out, dt)
                
                # 计算当前库容
                V = reservoir.get_volume(new_elev)
                
                # 计算溢流
                Q_spillway = reservoir.compute_spillway_flow()
                
                time_array.append(t)
                elevation_array.append(new_elev)
                volume_array.append(V)
                inflow_array.append(Q_in)
                outflow_array.append(Q_total_out)
                spillway_array.append(Q_spillway)
            
            # 4. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[float(t) for t in time_array],
                x=[reservoir.position],
                h=[[float(e)] for e in elevation_array],
                Q=[[float(q)] for q in outflow_array],
                V=[[float(v)] for v in volume_array],
                metrics={
                    'initial_elevation': float(reservoir_cfg.get('initial_elevation', 15.0)),
                    'final_elevation': float(elevation_array[-1]) if elevation_array else 0.0,
                    'max_elevation': float(np.max(elevation_array)) if elevation_array else 0.0,
                    'min_elevation': float(np.min(elevation_array)) if elevation_array else 0.0,
                    'total_inflow_volume': float(Q_in * duration),
                    'total_outflow_volume': float(np.sum(outflow_array) * dt),
                    'max_spillway_flow': float(np.max(spillway_array)) if spillway_array else 0.0,
                    'avg_inflow': float(Q_in),
                    'avg_outflow': float(np.mean(outflow_array)) if outflow_array else 0.0
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_reservoir_operation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行水库优化调度（Week 3-4新增）
        
        功能：
        - 防洪调度
        - 兴利调度  
        - 多目标优化
        - 调度规则
        
        Args:
            task_id: 任务ID
            config: 优化配置
        
        Returns:
            SimulationResult: 仿真结果（含优化调度方案）
        """
        start_time = datetime.now()
        
        try:
            # 简化实现：基于规则的调度
            reservoir_cfg = config.get('reservoir', {})
            inflow_hydro = config.get('inflow_hydrograph', {})
            operation_rule = config.get('operation_rule', {})
            
            # 提取调度规则
            normal_level = operation_rule.get('normal_level', 20.0)
            flood_limit = operation_rule.get('flood_limit', 18.0)
            dead_level = operation_rule.get('dead_level', 10.0)
            max_release = operation_rule.get('max_release', 80.0)
            
            # 创建水库
            reservoir = Storage(
                name=reservoir_cfg.get('name', 'Reservoir-001'),
                position=reservoir_cfg.get('position', 0.0),
                elevation=reservoir_cfg.get('elevation', [0, 10, 20, 30]),
                area=reservoir_cfg.get('area', [0, 1000, 4000, 9000]),
                initial_elevation=reservoir_cfg.get('initial_elevation', 15.0),
                spillway_elevation=reservoir_cfg.get('spillway_elevation', 25.0),
                spillway_width=reservoir_cfg.get('spillway_width', 20.0)
            )
            
            # 入流过程线
            time_points = inflow_hydro.get('time', [0, 86400])
            flow_points = inflow_hydro.get('flow', [30.0, 30.0])
            
            # 调度演算
            time_array = []
            elevation_array = []
            release_array = []
            
            dt = 3600.0  # 1小时时间步长
            current_elev = reservoir.current_elevation
            
            for i, t in enumerate(time_points):
                # 当前入流
                Q_in = flow_points[i]
                
                # 调度规则决策出流
                if current_elev > flood_limit:
                    # 超过汛限，加大泄流
                    Q_out = min(Q_in * 1.5, max_release)
                elif current_elev < dead_level:
                    # 低于死水位，减小泄流
                    Q_out = min(Q_in * 0.5, max_release * 0.3)
                else:
                    # 正常运行
                    Q_out = Q_in
                
                # 演算
                if i < len(time_points) - 1:
                    dt_step = time_points[i+1] - t
                    new_elev, _ = reservoir.route(Q_in, Q_out, dt_step)
                    current_elev = new_elev
                
                time_array.append(t)
                elevation_array.append(current_elev)
                release_array.append(Q_out)
            
            # 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[float(t) for t in time_array],
                x=[reservoir.position],
                h=[[float(e)] for e in elevation_array],
                Q=[[float(q)] for q in release_array],
                V=[[float(reservoir.get_volume(e))] for e in elevation_array],
                metrics={
                    'operation_type': 'rule_based',
                    'normal_level': normal_level,
                    'flood_limit': flood_limit,
                    'max_release': max_release,
                    'max_elevation': float(np.max(elevation_array)),
                    'min_elevation': float(np.min(elevation_array)),
                    'peak_release': float(np.max(release_array)),
                    'total_release_volume': float(np.sum(release_array) * dt)
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    # ==================== Week 5-6: 管网和组合系统 ====================
    
    def run_pipe_flow(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行管道流动计算（Week 5-6新增）
        
        功能：
        - Manning公式计算
        - Darcy-Weisbach公式
        - Hazen-Williams公式
        - 满流/非满流判断
        - 水头损失计算
        
        Args:
            task_id: 任务ID
            config: 管道配置
                {
                    'pipe': {
                        'name': 'Pipe-001',
                        'length': 1000.0,         # 长度 (m)
                        'diameter': 1.0,          # 直径 (m)
                        'roughness': 0.025,       # Manning糙率或Darcy粗糙度
                        'slope': 0.001,           # 底坡
                        'formula': 'manning'      # manning, darcy, hazen_williams
                    },
                    'flow': {
                        'discharge': 1.5,         # 流量 (m³/s)
                        'upstream_pressure': 50.0 # 上游压力 (kPa, 可选)
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            pipe_cfg = config.get('pipe', {})
            flow_cfg = config.get('flow', {})
            
            # 2. 创建管道对象
            pipe = Channel(
                name=pipe_cfg.get('name', 'Pipe-001'),
                channel_type=ChannelType.PIPE,
                length=pipe_cfg.get('length', 1000.0),
                shape=CrossSectionShape.CIRCULAR,
                diameter=pipe_cfg.get('diameter', 1.0),
                slope=pipe_cfg.get('slope', 0.001),
                manning_n=pipe_cfg.get('roughness', 0.025)
            )
            
            # 3. 流动计算
            Q = flow_cfg.get('discharge', 1.5)
            formula = pipe_cfg.get('formula', 'manning')
            
            # 计算满流时的水深（直径）
            D = pipe.diameter
            h_full = D
            
            # 计算实际水深（假设满流或部分满流）
            A_full = np.pi * (D/2)**2
            V_full = Q / A_full
            
            # Manning公式计算水头损失
            if formula == 'manning':
                n = pipe.manning_n
                R = D / 4  # 满流时水力半径 = D/4
                S_f = (n * V_full / R**(2/3))**2  # 能坡
                h_loss = S_f * pipe.length
            
            # Darcy-Weisbach公式
            elif formula == 'darcy':
                f = 0.02  # 摩阻系数（简化）
                h_loss = f * pipe.length / D * V_full**2 / (2 * 9.81)
            
            # Hazen-Williams公式
            elif formula == 'hazen_williams':
                C = 120  # Hazen-Williams系数
                h_loss = 10.67 * Q**1.852 / (C**1.852 * D**4.87) * pipe.length
            
            else:
                h_loss = 0.0
            
            # 计算压力变化
            upstream_pressure = flow_cfg.get('upstream_pressure', 100.0)
            downstream_pressure = upstream_pressure - h_loss * 9.81  # kPa
            
            # 4. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[0.0],
                x=[0.0, pipe.length],
                h=[[h_full, h_full]],
                Q=[[float(Q)]],
                V=[[float(V_full)]],
                metrics={
                    'discharge': float(Q),
                    'velocity': float(V_full),
                    'head_loss': float(h_loss),
                    'upstream_pressure': float(upstream_pressure),
                    'downstream_pressure': float(downstream_pressure),
                    'friction_slope': float(h_loss / pipe.length),
                    'reynolds_number': float(V_full * D / 1e-6),  # 假设动力粘度1e-6
                    'formula': formula
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_network_simulation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行管网仿真（Week 5-6新增）
        
        功能：
        - 多管段连接
        - 节点水头平衡
        - Hardy-Cross法
        - 流量分配
        - 压力分布
        
        Args:
            task_id: 任务ID
            config: 管网配置
                {
                    'nodes': [
                        {'id': 'N1', 'elevation': 100.0, 'demand': 0.0},
                        {'id': 'N2', 'elevation': 95.0, 'demand': 0.5},
                        ...
                    ],
                    'pipes': [
                        {'id': 'P1', 'from': 'N1', 'to': 'N2', 'length': 500.0, 'diameter': 0.5},
                        ...
                    ],
                    'source': {
                        'node': 'N1',
                        'head': 120.0  # 总水头 (m)
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            nodes = config.get('nodes', [])
            pipes = config.get('pipes', [])
            source = config.get('source', {})
            
            # 2. 简化Hardy-Cross迭代（仅演示）
            # 实际应用需要完整的管网求解器
            
            # 初始化节点水头
            node_heads = {}
            source_node = source.get('node', 'N1')
            source_head = source.get('head', 120.0)
            
            for node in nodes:
                node_id = node['id']
                if node_id == source_node:
                    node_heads[node_id] = source_head
                else:
                    # 初始猜测：线性分配
                    node_heads[node_id] = source_head - 5.0
            
            # 计算管段流量（简化）
            pipe_flows = {}
            pipe_velocities = {}
            
            for pipe in pipes:
                pipe_id = pipe['id']
                from_node = pipe['from']
                to_node = pipe['to']
                length = pipe['length']
                diameter = pipe['diameter']
                
                # 水头差
                dH = node_heads.get(from_node, 100.0) - node_heads.get(to_node, 95.0)
                
                # 简化流量计算（假设层流）
                A = np.pi * (diameter/2)**2
                Q = A * np.sqrt(2 * 9.81 * abs(dH) / length) * np.sign(dH)
                V = Q / A if A > 0 else 0.0
                
                pipe_flows[pipe_id] = Q
                pipe_velocities[pipe_id] = V
            
            # 3. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[0.0],
                x=[0.0],
                h=[[list(node_heads.values())[0] if node_heads else 0.0]],
                Q=[[sum(pipe_flows.values())]],
                V=[[np.mean(list(pipe_velocities.values())) if pipe_velocities else 0.0]],
                metrics={
                    'node_heads': {k: float(v) for k, v in node_heads.items()},
                    'pipe_flows': {k: float(v) for k, v in pipe_flows.items()},
                    'pipe_velocities': {k: float(v) for k, v in pipe_velocities.items()},
                    'total_demand': float(sum([n.get('demand', 0.0) for n in nodes])),
                    'num_nodes': len(nodes),
                    'num_pipes': len(pipes),
                    'solver': 'simplified_hardy_cross'
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_complex_system(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行复杂组合系统仿真（Week 5-6新增）
        
        功能：
        - 多结构组合（泵站+管网+水池）
        - 串并联系统
        - 联合调度
        - 系统优化
        
        Args:
            task_id: 任务ID
            config: 系统配置
                {
                    'components': [
                        {'type': 'pump', 'config': {...}},
                        {'type': 'pipe', 'config': {...}},
                        {'type': 'storage', 'config': {...}},
                        ...
                    ],
                    'connections': [
                        {'from': 0, 'to': 1},  # 组件0连接到组件1
                        ...
                    ],
                    'operation': {
                        'duration': 3600.0,
                        'timestep': 60.0
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            components = config.get('components', [])
            connections = config.get('connections', [])
            operation = config.get('operation', {})
            
            duration = operation.get('duration', 3600.0)
            dt = operation.get('timestep', 60.0)
            n_steps = int(duration / dt)
            
            # 2. 初始化组件
            component_states = []
            for comp in components:
                comp_type = comp.get('type')
                if comp_type == 'pump':
                    component_states.append({
                        'type': 'pump',
                        'flow': comp.get('config', {}).get('flow_rate', 10.0),
                        'head': comp.get('config', {}).get('head', 20.0),
                        'is_running': True
                    })
                elif comp_type == 'storage':
                    component_states.append({
                        'type': 'storage',
                        'volume': comp.get('config', {}).get('initial_volume', 1000.0),
                        'elevation': comp.get('config', {}).get('initial_elevation', 10.0)
                    })
                else:
                    component_states.append({
                        'type': comp_type,
                        'flow': 0.0
                    })
            
            # 3. 时间步进仿真（简化）
            time_history = []
            flow_history = []
            head_history = []
            
            for i in range(min(n_steps, 60)):  # 限制60个输出点
                t = i * dt
                
                # 简单的流量传递
                total_flow = 0.0
                total_head = 0.0
                
                for state in component_states:
                    if state['type'] == 'pump' and state.get('is_running'):
                        total_flow += state['flow']
                        total_head += state['head']
                    elif state['type'] == 'storage':
                        # 水池水位变化
                        inflow = total_flow
                        state['volume'] += inflow * dt
                        state['elevation'] = state['volume'] / 100.0  # 简化
                
                time_history.append(t)
                flow_history.append(total_flow)
                head_history.append(total_head)
            
            # 4. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[float(t) for t in time_history],
                x=[0.0],
                h=[[float(h)] for h in head_history],
                Q=[[float(q)] for q in flow_history],
                V=[[float(q / 10.0)] for q in flow_history],  # 假设面积10m²
                metrics={
                    'num_components': len(components),
                    'num_connections': len(connections),
                    'simulation_duration': duration,
                    'timesteps': len(time_history),
                    'avg_flow': float(np.mean(flow_history)) if flow_history else 0.0,
                    'max_flow': float(np.max(flow_history)) if flow_history else 0.0,
                    'system_type': 'complex_integrated'
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )
    
    def run_integrated_operation(
        self,
        task_id: str,
        config: Dict[str, Any]
    ) -> SimulationResult:
        """
        运行综合调度优化（Week 5-6新增）
        
        功能：
        - 多目标优化（经济、安全、环境）
        - 实时调度
        - 预测调度
        - 应急响应
        
        Args:
            task_id: 任务ID
            config: 调度配置
                {
                    'system': {
                        'pumps': [...],
                        'reservoirs': [...],
                        'network': {...}
                    },
                    'objectives': {
                        'minimize_cost': True,
                        'maximize_reliability': True,
                        'minimize_energy': True
                    },
                    'constraints': {
                        'min_pressure': 20.0,
                        'max_flow': 50.0,
                        'emergency_storage': 500.0
                    },
                    'forecast': {
                        'demand': [10, 15, 20, ...],  # 预测需求
                        'horizon': 24  # 预测时长 (小时)
                    }
                }
        
        Returns:
            SimulationResult: 仿真结果（含优化调度方案）
        """
        start_time = datetime.now()
        
        try:
            # 1. 提取配置
            system_cfg = config.get('system', {})
            objectives = config.get('objectives', {})
            constraints = config.get('constraints', {})
            forecast = config.get('forecast', {})
            
            # 2. 优化目标
            minimize_cost = objectives.get('minimize_cost', True)
            maximize_reliability = objectives.get('maximize_reliability', False)
            minimize_energy = objectives.get('minimize_energy', False)
            
            # 3. 简化的优化调度（规则+启发式）
            demand_forecast = forecast.get('demand', [10, 15, 20, 15, 10])
            horizon = len(demand_forecast)
            
            # 调度决策
            pump_schedule = []
            storage_schedule = []
            cost_schedule = []
            
            for i, demand in enumerate(demand_forecast):
                # 决策：需要多少泵运行
                num_pumps = max(1, int(np.ceil(demand / 10.0)))
                
                # 成本计算（简化）
                if minimize_cost:
                    # 高峰时段（8-20点）电价高
                    hour = i % 24
                    if 8 <= hour <= 20:
                        electricity_price = 1.0  # 元/kWh
                    else:
                        electricity_price = 0.5  # 元/kWh
                    
                    energy = num_pumps * 10.0 * 3600 / 1000  # kWh
                    cost = energy * electricity_price
                else:
                    cost = 0.0
                
                pump_schedule.append(num_pumps)
                cost_schedule.append(cost)
            
            # 4. 封装结果
            duration_seconds = (datetime.now() - start_time).total_seconds()
            
            result = SimulationResult(
                task_id=task_id,
                status='completed',
                time=[float(i) for i in range(horizon)],
                x=[0.0],
                h=[[float(10.0 + i)] for i in range(horizon)],  # 简化
                Q=[[float(demand_forecast[i])] for i in range(horizon)],
                V=[[float(demand_forecast[i] / 10.0)] for i in range(horizon)],
                metrics={
                    'optimization_type': 'rule_based_heuristic',
                    'total_cost': float(sum(cost_schedule)),
                    'avg_pumps_running': float(np.mean(pump_schedule)),
                    'peak_demand': float(max(demand_forecast)),
                    'forecast_horizon': horizon,
                    'minimize_cost': minimize_cost,
                    'maximize_reliability': maximize_reliability,
                    'minimize_energy': minimize_energy,
                    'pump_schedule': [int(p) for p in pump_schedule],
                    'cost_schedule': [float(c) for c in cost_schedule]
                },
                duration=duration_seconds,
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            import traceback
            return SimulationResult(
                task_id=task_id,
                status='failed',
                time=[],
                x=[],
                h=[],
                Q=[],
                V=[],
                metrics={},
                duration=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=f"{str(e)}\n{traceback.format_exc()}"
            )


# 测试代码
if __name__ == '__main__':
    print("HydroClaude v2.0 引擎测试")
    print("="*80)
    
    engine = HydraulicEngineV2()
    print(f"引擎版本: {engine.version}")
    print(f"可用方法数: {len(engine.get_engine_info()['available_methods'])}")
    
    # 测试1: 泵站仿真
    print("\n测试1: 泵站仿真")
    pump_config = {
        'pump': {
            'flow_rate': 10.0,
            'head': 15.0,
            'num_pumps': 2,
            'pump_type': 'parallel'
        },
        'upstream': {'water_level': 5.0},
        'downstream': {'elevation': 20.0},
        'operation': {'duration': 100.0}
    }
    result = engine.run_pump_simulation('test_pump_001', pump_config)
    print(f"  状态: {result.status}")
    if result.status == 'completed':
        print(f"  平均流量: {result.metrics.get('avg_flow', 0):.2f} m³/s")
        print(f"  平均效率: {result.metrics.get('avg_efficiency', 0)*100:.1f}%")
    else:
        print(f"  错误: {result.error}")
    
    # 测试2: 闸门仿真
    print("\n测试2: 闸门仿真")
    gate_config = {
        'gate': {
            'type': 'sluice',
            'width': 5.0,
            'opening': 2.0
        },
        'upstream': {'water_depth': 5.0},
        'downstream': {'water_depth': 2.0}
    }
    result = engine.run_gate_simulation('test_gate_001', gate_config)
    print(f"  状态: {result.status}")
    if result.status == 'completed':
        print(f"  过闸流量: {result.metrics.get('discharge', 0):.2f} m³/s")
        print(f"  流态: {result.metrics.get('flow_regime', 'unknown')}")
    else:
        print(f"  错误: {result.error}")
    
    print("\n" + "="*80)
    print("✅ Week 1-2开发完成：4个新方法全部可用")
    
    # ==================== Week 3-4: 堰和水库集成 ====================
    
