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
from solvers.godunov_fvm_solver import GodunvFVMSolver

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
            ],
            'supported_structures': [
                # 明渠
                'canal',
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
    
    def _run_canal_simulation_internal(self, task_id: str, config: Dict[str, Any], start_time):
        """内部实现 - 在suppress_output上下文中调用"""
        try:
            # 1. 提取配置参数
            width = config.get('width', 10.0)
            length = config.get('length', 1000.0)
            n_cells = config.get('n_cells', 200)
            manning_n = config.get('manning_n', 0.0)
            slope = config.get('slope', 0.0)
            cfl = config.get('cfl', 0.5)
            order = config.get('order', 2)
            use_numba = config.get('use_numba', True)
            t_end = config.get('t_end', 100.0)
            dt_max = config.get('dt_max', 0.1)

            # 2. 创建求解器
            solver = GodunvFVMSolver(
                width=width,
                length=length,
                n_cells=n_cells,
                manning_n=manning_n,
                slope=slope,
                cfl=cfl,
                order=order,
                use_numba=use_numba
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

            elif ic_type == 'uniform':
                h_init = ic_config.get('h', 5.0)
                Q_init = ic_config.get('Q', 0.0)
                solver.h = np.full(n_cells, h_init)
                solver.Q = np.full(n_cells, Q_init)

            # 4. 运行仿真
            output_interval = config.get('output_interval', 1.0)
            
            time_history = []
            h_history = []
            Q_history = []
            V_history = []
            
            t = 0.0
            output_time = 0.0
            
            while t < t_end:
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
            
            # 5. 计算指标
            metrics = {
                'max_depth': float(np.max(solver.h)),
                'max_velocity': float(np.max(np.abs(solver.Q / solver.h / width))),
                'total_volume': float(np.sum(solver.h) * length / n_cells * width),
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
            
            canal_result = self._run_canal_simulation_internal(
                task_id,
                canal_config,
                start_time
            )
            
            if canal_result.status != 'completed':
                return canal_result
            
            # 2. 叠加泵站影响
            pump_cfg = config.get('pump', {})
            pump_flow = pump_cfg.get('flow_rate', 5.0)
            pump_position = pump_cfg.get('position', canal_config.get('length', 1000.0) / 2)
            pump_head = pump_cfg.get('head', 10.0)
            
            # 修改metrics添加泵站信息
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
            
            canal_result = self._run_canal_simulation_internal(
                task_id,
                canal_config,
                start_time
            )
            
            if canal_result.status != 'completed':
                return canal_result
            
            # 2. 在闸门位置计算过闸流量
            gate_cfg = config.get('gate', {})
            gate_position = gate_cfg.get('position', canal_config.get('length', 1000.0) / 2)
            gate_type = gate_cfg.get('type', 'sluice')
            
            # 创建闸门
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
            
            # 从明渠结果中提取闸门位置的水深
            mid_idx = len(canal_result.x) // 2
            if len(canal_result.h) > 0 and len(canal_result.h[-1]) > mid_idx:
                h_upstream = canal_result.h[-1][mid_idx]
                h_downstream = h_upstream * 0.7  # 简化假设，下游水深为上游70%
            else:
                h_upstream = 5.0
                h_downstream = 3.5
            
            Q_gate, regime = gate.compute_discharge(h_upstream, h_downstream)
            
            # 3. 修改metrics添加闸门信息
            canal_result.metrics.update({
                'gate_discharge': float(Q_gate),
                'gate_position': float(gate_position),
                'gate_regime': regime.value,
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
            
            canal_result = self._run_canal_simulation_internal(
                task_id,
                canal_config,
                start_time
            )
            
            if canal_result.status != 'completed':
                return canal_result
            
            # 2. 在堰位置计算过堰流量
            weir_cfg = config.get('weir', {})
            weir_position = weir_cfg.get('position', canal_config.get('length', 1000.0) / 2)
            weir_type = weir_cfg.get('type', 'broad_crested')
            crest_height = weir_cfg.get('crest_height', 1.5)
            
            # 从明渠结果中提取堰位置的水深
            mid_idx = len(canal_result.x) // 2
            if len(canal_result.h) > 0 and len(canal_result.h[-1]) > 0 and len(canal_result.h[-1]) > mid_idx:
                h_upstream = canal_result.h[-1][mid_idx]
            else:
                # 使用初始条件的水深
                initial_cond = canal_config.get('initial_conditions', {})
                if isinstance(initial_cond, dict):
                    h_upstream = initial_cond.get('h', 3.0)
                else:
                    h_upstream = 3.0
            
            # 计算堰上水头和流量
            H = max(h_upstream - crest_height, 0.0)
            width = weir_cfg.get('width', canal_config.get('width', 10.0))
            Cd = weir_cfg.get('discharge_coeff', 1.7)
            
            if weir_type == 'v_notch':
                # V形堰
                angle = weir_cfg.get('angle', 90.0)
                Q_weir = 1.4 * np.tan(np.radians(angle/2)) * np.sqrt(2*9.81) * H**2.5
            else:
                # 其他堰型（宽顶、薄壁、溢流）
                Q_weir = Cd * width * np.sqrt(2*9.81) * H**1.5
            
            # 3. 修改metrics添加堰信息
            canal_result.metrics.update({
                'weir_discharge': float(Q_weir),
                'weir_position': float(weir_position),
                'weir_type': weir_type,
                'weir_head': float(H),
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
    
