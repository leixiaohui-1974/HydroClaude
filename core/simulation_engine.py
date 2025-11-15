#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
仿真引擎 (Simulation Engine)

功能:
1. 根据配置选择求解器
2. 初始化求解器参数
3. 执行仿真
4. 收集结果
5. 生成通用数据模型

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import numpy as np
import time
from typing import Dict, Any, Optional
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.godunov_fvm_solver import GodunvFVMSolver
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice, PumpStation
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth
from utils.result_validator import quick_validate_steady_state


class SimulationEngine:
    """
    仿真引擎
    
    根据配置自动选择求解器并执行仿真
    """
    
    def __init__(self, config: Dict[str, Any], verbose: bool = False):
        """
        初始化仿真引擎
        
        Args:
            config: 配置字典（来自ConfigParser）
            verbose: 是否输出详细信息
        """
        self.config = config
        self.verbose = verbose
        self.solver = None
        self.results = None
        self.start_time = None
        self.end_time = None
        
    def run(self) -> Dict[str, Any]:
        """
        运行仿真
        
        Returns:
            标准化的结果字典（通用数据模型）
        """
        if self.verbose:
            print("\n" + "=" * 80)
            print("开始仿真")
            print("=" * 80)
        
        self.start_time = time.time()
        
        # 1. 创建求解器
        if self.verbose:
            print("\n1. 创建求解器...")
        self.solver = self._create_solver()
        
        # 2. 创建水工结构
        if self.verbose:
            print("\n2. 创建水工结构...")
        structures = self._create_structures()
        
        # 3. 设置初始条件
        if self.verbose:
            print("\n3. 设置初始条件...")
        self._set_initial_conditions()
        
        # 4. 执行仿真
        if self.verbose:
            print("\n4. 执行仿真...")
        
        simulation_type = self.config['simulation']['type']
        
        if simulation_type == 'steady':
            raw_results = self._run_steady_simulation()
        elif simulation_type == 'unsteady':
            raw_results = self._run_unsteady_simulation()
        else:
            raise ValueError(f"未知的仿真类型: {simulation_type}")
        
        self.end_time = time.time()
        
        # 5. 转换为通用数据模型
        if self.verbose:
            print("\n5. 生成标准化结果...")
        self.results = self._convert_to_universal_model(raw_results, structures)
        
        if self.verbose:
            print(f"\n✅ 仿真完成！用时: {self.end_time - self.start_time:.2f} 秒")
            print("=" * 80)
        
        return self.results
    
    def _create_solver(self):
        """根据配置创建求解器"""
        solver_config = self.config['solver']
        canal_config = self.config['canal']
        
        method = solver_config['method']
        params = solver_config['parameters']
        
        if method == 'hydrostatic':
            # 创建HydrostaticCanalSolver
            solver = HydrostaticCanalSolver(
                length=canal_config['length'],
                nx=canal_config['grid']['nx'],
                B=canal_config['width'],
                S0=canal_config['slope'],
                n=canal_config['manning_n'],
                internal_structures=[],  # 稍后添加
                theta=params.get('theta', 0.6),
                omega=params.get('omega', 0.95)
            )
            
            if self.verbose:
                print(f"  ✅ 创建 HydrostaticCanalSolver")
                print(f"     - 长度: {canal_config['length']} m")
                print(f"     - 网格数: {canal_config['grid']['nx']}")
                print(f"     - 宽度: {canal_config['width']} m")
                print(f"     - 坡度: {canal_config['slope']}")
            
            return solver
            
        elif method == 'godunov':
            # 创建GodunvFVMSolver
            solver = GodunvFVMSolver(
                width=canal_config['width'],
                length=canal_config['length'],
                n_cells=canal_config['grid']['nx'] - 1,  # GodunvFVM使用单元数
                manning_n=canal_config['manning_n'],
                slope=canal_config['slope'],
                cfl=params.get('cfl', 0.5),
                order=params.get('order', 1)
            )
            
            if self.verbose:
                print(f"  ✅ 创建 GodunvFVMSolver")
                print(f"     - 长度: {canal_config['length']} m")
                print(f"     - 单元数: {canal_config['grid']['nx'] - 1}")
                print(f"     - CFL: {params.get('cfl', 0.5)}")
            
            return solver
            
        else:
            raise ValueError(f"未知的求解器方法: {method}")
    
    def _create_structures(self) -> list:
        """创建水工结构"""
        structures_config = self.config.get('structures', [])
        
        if not structures_config:
            if self.verbose:
                print("  无水工结构")
            return []
        
        structures = []
        
        for struct_config in structures_config:
            struct_type = struct_config['type']
            position = struct_config['position']
            params = struct_config['parameters']
            name = struct_config.get('name', f'{struct_type}_{position}')
            
            if struct_type == 'sluice_gate':
                structure = SluiceGate(
                    position=position,
                    width=params['width'],
                    opening=params['opening'],
                    discharge_coefficient=params.get('discharge_coefficient', 0.6)
                )
            elif struct_type == 'weir':
                structure = BroadCrestedWeir(
                    position=position,
                    width=params['width'],
                    crest_height=params['crest_height'],
                    discharge_coefficient=params.get('discharge_coefficient', 1.7)
                )
            elif struct_type == 'orifice':
                structure = Orifice(
                    position=position,
                    area=params['area'],
                    discharge_coefficient=params.get('discharge_coefficient', 0.6)
                )
            elif struct_type == 'pump':
                structure = PumpStation(
                    position=position,
                    capacity=params['capacity'],
                    head=params.get('head', 0.0)
                )
            else:
                raise ValueError(f"未知的结构类型: {struct_type}")
            
            # 添加名称属性
            structure.name = name
            structure.type = struct_type
            
            structures.append(structure)
            
            if self.verbose:
                print(f"  ✅ 创建 {struct_type} @ {position} m")
        
        # 将结构添加到求解器
        if hasattr(self.solver, 'internal_structures'):
            self.solver.internal_structures = [(s.position, s) for s in structures]
            self.solver._setup_internal_structures()
        
        return structures
    
    def _set_initial_conditions(self):
        """设置初始条件"""
        initial_config = self.config.get('initial_conditions', {})
        canal_config = self.config['canal']
        
        # 获取初始水深
        depth_spec = initial_config.get('depth', 'uniform_flow')
        
        if depth_spec == 'uniform_flow':
            # 使用预计算的均匀流水深
            if '_computed' in self.config and 'uniform_depth' in self.config['_computed']:
                h_initial = self.config['_computed']['uniform_depth']
            else:
                # 重新计算
                bc = self.config.get('boundary_conditions', {})
                Q = bc.get('upstream', {}).get('value', 8.0)
                B = canal_config['width']
                S0 = canal_config['slope'] if isinstance(canal_config['slope'], (int, float)) else np.mean(canal_config['slope'])
                n = canal_config['manning_n']
                h_initial = compute_steady_uniform_flow(Q, B, S0, n)
        elif isinstance(depth_spec, (int, float)):
            h_initial = depth_spec
        elif depth_spec == 'dry':
            h_initial = 1e-6
        else:
            raise ValueError(f"未知的初始水深规范: {depth_spec}")
        
        # 获取初始流量
        flow_spec = initial_config.get('flow', None)
        if flow_spec is None:
            # 从上游边界条件获取
            bc = self.config.get('boundary_conditions', {})
            flow_spec = bc.get('upstream', {}).get('value', 8.0)
        
        Q_initial = flow_spec
        
        # 设置到求解器
        if hasattr(self.solver, 'h'):
            self.solver.h[:] = h_initial
            self.solver.hu[:] = Q_initial / canal_config['width']
        elif hasattr(self.solver, 'initialize'):
            # GodunvFVMSolver使用initialize方法
            n_cells = canal_config['grid']['nx'] - 1
            h_init = np.ones(n_cells) * h_initial
            Q_init = np.ones(n_cells) * Q_initial
            
            bc = self.config.get('boundary_conditions', {})
            bc_left = {'type': 'Q', 'value': Q_initial}
            bc_right = {'type': 'h', 'value': h_initial}
            
            self.solver.initialize(h_init, Q_init, bc_left, bc_right)
        
        if self.verbose:
            print(f"  初始水深: {h_initial:.4f} m")
            print(f"  初始流量: {Q_initial:.4f} m³/s")
    
    def _run_steady_simulation(self) -> Dict[str, Any]:
        """运行稳态仿真"""
        bc = self.config['boundary_conditions']
        solver_params = self.config['solver']['parameters']
        
        Q_target = bc['upstream']['value']
        h_downstream = bc['downstream']['value']
        
        if self.verbose:
            print(f"  上游流量: {Q_target} m³/s")
            print(f"  下游水深: {h_downstream} m")
        
        # 执行稳态求解
        result = self.solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_downstream,
            max_iterations=solver_params['max_iterations'],
            convergence_tol=solver_params['convergence_tol'],
            dt=solver_params.get('dt', 0.5),
            verbose=self.verbose
        )
        
        if self.verbose:
            print(f"\n  收敛: {'是' if result['converged'] else '否'}")
            print(f"  迭代次数: {result['iterations']}")
            print(f"  流量误差: {result['Q_error_percent']:.6f}%")
        
        # 验证
        validator = quick_validate_steady_state(
            solver=self.solver,
            result_dict=result,
            Q_target=Q_target,
            name=self.config['metadata']['title']
        )
        
        # 整合验证结果
        result['validation'] = {
            'validator': validator,
            'score': validator.overall_score,
            'grade': validator.overall_grade
        }
        
        return result
    
    def _run_unsteady_simulation(self) -> Dict[str, Any]:
        """运行非恒定流仿真"""
        time_config = self.config['simulation']['time']
        bc = self.config['boundary_conditions']
        
        t_start = time_config['start']
        t_end = time_config['end']
        dt = time_config['dt']
        output_interval = time_config.get('output_interval', dt)
        
        n_steps = int((t_end - t_start) / dt)
        n_outputs = int((t_end - t_start) / output_interval)
        
        if self.verbose:
            print(f"  时间范围: {t_start} - {t_end} s")
            print(f"  时间步长: {dt} s")
            print(f"  总步数: {n_steps}")
            print(f"  输出步数: {n_outputs}")
        
        # 存储时间历史
        output_times = []
        h_history = []
        Q_history = []
        
        current_time = t_start
        output_counter = 0
        
        for step in range(n_steps):
            current_time += dt
            
            # 执行一步
            if hasattr(self.solver, 'step'):
                # GodunvFVMSolver
                self.solver.step()
            elif hasattr(self.solver, 'step_preissmann'):
                # HydrostaticCanalSolver
                Q_in = bc['upstream']['value']
                h_out = bc['downstream']['value']
                
                h_new, hu_new = self.solver.step_preissmann(
                    dt=dt,
                    max_iter=10,
                    enforce_bc=True,
                    Q_in=Q_in,
                    h_out=h_out
                )
                
                self.solver.h = h_new
                self.solver.hu = hu_new
                self.solver.current_time = current_time
            
            # 保存输出
            if step % int(output_interval / dt) == 0:
                output_times.append(current_time)
                h_history.append(self.solver.h.copy())
                Q_history.append((self.solver.hu * self.config['canal']['width']).copy())
                output_counter += 1
            
            # 打印进度
            if self.verbose and (step + 1) % (n_steps // 10) == 0:
                progress = (step + 1) / n_steps * 100
                print(f"  进度: {progress:.0f}%")
        
        # 整理结果
        result = {
            'converged': True,
            'n_steps': n_steps,
            'time': np.array(output_times),
            'h': np.array(h_history),  # shape: (n_outputs, nx)
            'Q': np.array(Q_history),
            'x': self.solver.x
        }
        
        if self.verbose:
            print(f"\n  ✅ 非恒定流仿真完成")
            print(f"  输出了 {len(output_times)} 个时间步")
        
        return result
    
    def _convert_to_universal_model(self, raw_results: Dict[str, Any], structures: list) -> Dict[str, Any]:
        """
        将求解器的原始结果转换为通用数据模型
        
        这是关键函数，确保所有场景的结果都是统一格式
        """
        simulation_type = self.config['simulation']['type']
        canal_config = self.config['canal']
        
        # 基础信息
        universal_result = {
            'hydro_result': {
                'version': '2.0',
                'format': 'standard',
                'created': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'software': {
                    'name': 'HydroClaude',
                    'version': '1.0.0',
                    'solver': self.config['solver']['method']
                }
            },
            
            'simulation': {
                'id': f"sim_{time.strftime('%Y%m%d_%H%M%S')}",
                'type': simulation_type,
                'mode': self.config['simulation']['mode'],
                'status': 'completed' if raw_results.get('converged', True) else 'failed',
                'duration_seconds': self.end_time - self.start_time,
            },
            
            'geometry': self._extract_geometry(raw_results),
            'variables': self._extract_variables(raw_results, simulation_type),
            'structures': self._extract_structures(structures, raw_results),
            'boundary_conditions': self.config.get('boundary_conditions', {}),
            'metadata': self.config['metadata']
        }
        
        # 添加收敛信息（稳态）
        if simulation_type == 'steady':
            universal_result['simulation']['convergence'] = {
                'converged': raw_results['converged'],
                'iterations': raw_results['iterations'],
                'final_residual': raw_results.get('max_change', 0.0)
            }
        
        # 添加验证信息（如果有）
        if 'validation' in raw_results:
            validator = raw_results['validation']['validator']
            universal_result['validation'] = {
                'mass_conservation': {
                    'error_absolute': validator.Q_error_abs,
                    'error_percent': validator.Q_error_pct,
                    'grade': validator.Q_grade,
                    'threshold': 0.01
                },
                'overall_score': validator.overall_score,
                'overall_grade': validator.overall_grade
            }
        
        # 添加可视化建议
        universal_result['visualization'] = self._generate_visualization_config(simulation_type)
        
        return universal_result
    
    def _extract_geometry(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """提取几何信息"""
        canal_config = self.config['canal']
        simulation_type = self.config['simulation']['type']
        
        x = raw_results.get('x', self.solver.x)
        
        geometry = {
            'type': '1d_canal',
            'coordinate_system': 'local',
            'dimensions': {
                'spatial': {
                    'type': 'x',
                    'unit': 'm',
                    'count': len(x),
                    'values': x.tolist()
                }
            },
            'properties': {
                'length': canal_config['length'],
                'width': canal_config['width'],
                'slope': canal_config['slope'],
                'manning_n': canal_config['manning_n']
            }
        }
        
        # 添加床面高程
        if hasattr(self.solver, 'z'):
            geometry['properties']['bed_elevation'] = self.solver.z.tolist()
        
        # 添加时间维度（非恒定流）
        if simulation_type == 'unsteady':
            t = raw_results.get('time', np.array([0.0]))
            geometry['dimensions']['temporal'] = {
                'type': 'unsteady',
                'unit': 's',
                'count': len(t),
                'values': t.tolist(),
                'start': float(t[0]),
                'end': float(t[-1]),
                'dt': float(t[1] - t[0]) if len(t) > 1 else 0.0
            }
        else:
            geometry['dimensions']['temporal'] = {
                'type': 'steady',
                'count': 1,
                'values': [0.0]
            }
        
        return geometry
    
    def _extract_variables(self, raw_results: Dict[str, Any], simulation_type: str) -> Dict[str, Any]:
        """提取变量数据"""
        variables = {}
        
        # 水深
        h = raw_results.get('h', self.solver.h)
        if h.ndim == 1:
            h = h[np.newaxis, :]  # 添加时间维度
        
        variables['depth'] = {
            'name': 'Water Depth',
            'symbol': 'h',
            'unit': 'm',
            'type': 'scalar',
            'dimensions': ['time', 'space'],
            'data_shape': list(h.shape),
            'data': h.tolist(),
            'statistics': {
                'min': float(np.min(h)),
                'max': float(np.max(h)),
                'mean': float(np.mean(h)),
                'std': float(np.std(h))
            }
        }
        
        # 流量
        Q = raw_results.get('Q')
        if Q is None:
            # 从hu计算
            B = self.config['canal']['width']
            Q = self.solver.hu * B
        
        if Q.ndim == 1:
            Q = Q[np.newaxis, :]
        
        variables['flow'] = {
            'name': 'Flow Rate',
            'symbol': 'Q',
            'unit': 'm³/s',
            'type': 'scalar',
            'dimensions': ['time', 'space'],
            'data_shape': list(Q.shape),
            'data': Q.tolist(),
            'statistics': {
                'min': float(np.min(Q)),
                'max': float(np.max(Q)),
                'mean': float(np.mean(Q)),
                'std': float(np.std(Q))
            }
        }
        
        # 流速
        v = Q / (self.config['canal']['width'] * h)
        variables['velocity'] = {
            'name': 'Flow Velocity',
            'symbol': 'v',
            'unit': 'm/s',
            'type': 'scalar',
            'dimensions': ['time', 'space'],
            'data_shape': list(v.shape),
            'data': v.tolist(),
            'statistics': {
                'min': float(np.min(v)),
                'max': float(np.max(v)),
                'mean': float(np.mean(v)),
                'std': float(np.std(v))
            }
        }
        
        # Froude数
        g = 9.81
        Fr = v / np.sqrt(g * h)
        variables['froude'] = {
            'name': 'Froude Number',
            'symbol': 'Fr',
            'unit': '-',
            'type': 'scalar',
            'dimensions': ['time', 'space'],
            'data_shape': list(Fr.shape),
            'data': Fr.tolist(),
            'statistics': {
                'min': float(np.min(Fr)),
                'max': float(np.max(Fr)),
                'mean': float(np.mean(Fr)),
                'std': float(np.std(Fr))
            }
        }
        
        # 水面高程
        if hasattr(self.solver, 'z'):
            z_bed = self.solver.z
            elevation = h + z_bed[np.newaxis, :]
            variables['elevation'] = {
                'name': 'Water Surface Elevation',
                'symbol': 'WSE',
                'unit': 'm',
                'type': 'scalar',
                'dimensions': ['time', 'space'],
                'data_shape': list(elevation.shape),
                'data': elevation.tolist(),
                'statistics': {
                    'min': float(np.min(elevation)),
                    'max': float(np.max(elevation)),
                    'mean': float(np.mean(elevation)),
                    'std': float(np.std(elevation))
                }
            }
        
        return variables
    
    def _extract_structures(self, structures: list, raw_results: Dict[str, Any]) -> list:
        """提取水工结构信息"""
        if not structures:
            return []
        
        result_structures = []
        
        for struct in structures:
            # 找到结构位置的索引
            x = raw_results.get('x', self.solver.x)
            idx = np.argmin(np.abs(x - struct.position))
            
            # 获取上下游水深
            h = raw_results.get('h', self.solver.h)
            if h.ndim == 1:
                h_up = h[max(0, idx - 1)]
                h_down = h[min(len(h) - 1, idx + 1)]
            else:
                h_up = h[-1, max(0, idx - 1)]  # 最后时刻
                h_down = h[-1, min(h.shape[1] - 1, idx + 1)]
            
            # 获取流量
            Q = raw_results.get('Q')
            if Q is None:
                Q = self.solver.hu * self.config['canal']['width']
            
            if Q.ndim == 1:
                Q_struct = Q[idx]
            else:
                Q_struct = Q[-1, idx]
            
            # 计算流速
            B = self.config['canal']['width']
            v_up = Q_struct / (B * h_up) if h_up > 0 else 0
            v_down = Q_struct / (B * h_down) if h_down > 0 else 0
            
            struct_data = {
                'id': f'struct_{len(result_structures):03d}',
                'type': struct.type,
                'name': struct.name,
                'position': {
                    'x': float(struct.position),
                    'index': int(idx)
                },
                'parameters': struct.__dict__.copy(),  # 结构参数
                'results': {
                    'upstream_depth': float(h_up),
                    'downstream_depth': float(h_down),
                    'flow': float(Q_struct),
                    'velocity_upstream': float(v_up),
                    'velocity_downstream': float(v_down),
                    'head_loss': float(h_up - h_down)
                }
            }
            
            # 清理parameters中的非序列化字段
            for key in ['name', 'type']:
                struct_data['parameters'].pop(key, None)
            
            result_structures.append(struct_data)
        
        return result_structures
    
    def _generate_visualization_config(self, simulation_type: str) -> Dict[str, Any]:
        """生成可视化配置"""
        viz_config = {
            'recommended_plots': []
        }
        
        # 纵剖面图（所有场景）
        viz_config['recommended_plots'].append({
            'type': 'longitudinal_profile',
            'title': 'Longitudinal Water Surface Profile',
            'x_variable': 'space',
            'y_variables': ['elevation', 'bed_elevation'],
            'time_index': -1  # 最后时刻（或唯一时刻）
        })
        
        # 流量分布图
        viz_config['recommended_plots'].append({
            'type': 'spatial_distribution',
            'title': 'Flow Distribution',
            'x_variable': 'space',
            'y_variable': 'flow',
            'time_index': -1
        })
        
        # 非恒定流特有图表
        if simulation_type == 'unsteady':
            # 时间序列
            viz_config['recommended_plots'].append({
                'type': 'time_series',
                'title': 'Water Depth Evolution',
                'x_variable': 'time',
                'y_variable': 'depth',
                'locations': [0, 'middle', -1]  # 上游、中游、下游
            })
            
            # 时空等值线
            viz_config['recommended_plots'].append({
                'type': 'contour',
                'title': 'Depth Contour (Space-Time)',
                'x_variable': 'space',
                'y_variable': 'time',
                'z_variable': 'depth'
            })
        
        return viz_config


def main():
    """测试仿真引擎"""
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='测试仿真引擎')
    parser.add_argument('config', type=str, help='配置文件路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('-o', '--output', type=str, help='结果输出路径')
    
    args = parser.parse_args()
    
    # 导入ConfigParser
    from config_parser import ConfigParser
    
    # 解析配置
    config_parser = ConfigParser(verbose=args.verbose)
    config = config_parser.parse(args.config)
    
    # 运行仿真
    engine = SimulationEngine(config, verbose=args.verbose)
    results = engine.run()
    
    # 保存结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 结果已保存: {args.output}")


if __name__ == '__main__':
    main()
