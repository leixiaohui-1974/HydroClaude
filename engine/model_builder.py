#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型构建器

从配置文件自动构建水力学模型

作者: HydroClaude Team
日期: 2025-10-28
"""

import numpy as np
import sys
import os
from typing import Dict, Any, Tuple
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from solvers.godunov_fvm_weno3_enhanced import GodunvFVMWENO3Enhanced
from engine.config_parser import ConfigParser


class ModelBuilder:
    """
    模型构建器

    功能：
    1. 从配置文件创建求解器
    2. 设置初始条件
    3. 设置边界条件
    4. 准备模拟环境
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化模型构建器

        Args:
            config: 配置字典（由ConfigParser解析）
        """
        self.config = config
        self.solver = None
        self.analytical_solution = None
        self.z_b_from_file = None  # 从IC文件读取的底高程（如果有）

    @classmethod
    def from_config_file(cls, config_file: str):
        """
        从配置文件创建ModelBuilder

        Args:
            config_file: 配置文件路径

        Returns:
            ModelBuilder实例
        """
        parser = ConfigParser(config_file)
        config = parser.parse()

        # 打印配置摘要
        print(parser.summary())

        return cls(config)

    def build_solver(self) -> GodunvFVMSolver:
        """
        构建求解器

        Returns:
            配置好的求解器实例
        """
        geom = self.config['geometry']
        mesh = self.config['mesh']
        solver_cfg = self.config['solver']

        # 创建求解器
        if solver_cfg['type'] == 'godunov_fvm':
            # 处理底坡（标量或数组）
            slope = self._get_bottom_slope()

            # 根据spatial_order选择合适的求解器
            spatial_order = solver_cfg['spatial_order']

            if spatial_order == 3:
                # 使用WENO3求解器（3阶精度，激波捕捉）
                # 支持标准版和增强版
                use_enhanced = solver_cfg.get('weno3_enhanced', False)

                if use_enhanced:
                    # 增强版WENO3（适用于水跃、激波等强间断问题）
                    self.solver = GodunvFVMWENO3Enhanced(
                        width=geom['channel_width'],
                        length=geom['channel_length'],
                        n_cells=mesh['n_cells'],
                        manning_n=geom['manning_n'],
                        slope=slope,
                        g=9.81,
                        cfl=solver_cfg['cfl'],
                        eps_dry=solver_cfg['eps_dry'],
                        weno_epsilon=solver_cfg.get('weno_epsilon', 1e-6),
                        riemann_solver=solver_cfg['riemann_solver'],
                        well_balanced=solver_cfg['well_balanced'],
                        use_numba=solver_cfg['use_numba'],
                        dt_max=solver_cfg.get('dt_max', None),
                        entropy_fix=solver_cfg.get('entropy_fix', True),
                        critical_flow_treatment=solver_cfg.get('critical_flow_treatment', True),
                        adaptive_cfl=solver_cfg.get('adaptive_cfl', True),
                        cfl_shock=solver_cfg.get('cfl_shock', 0.2),
                        entropy_delta=solver_cfg.get('entropy_delta', 0.1)
                    )
                else:
                    # 标准版WENO3
                    self.solver = GodunvFVMWENO3(
                        width=geom['channel_width'],
                        length=geom['channel_length'],
                        n_cells=mesh['n_cells'],
                        manning_n=geom['manning_n'],
                        slope=slope,
                        g=9.81,
                        cfl=solver_cfg['cfl'],
                        eps_dry=solver_cfg['eps_dry'],
                        weno_epsilon=solver_cfg.get('weno_epsilon', 1e-6),
                        riemann_solver=solver_cfg['riemann_solver'],
                        well_balanced=solver_cfg['well_balanced'],
                        use_numba=solver_cfg['use_numba'],
                        dt_max=solver_cfg.get('dt_max', None),
                        entropy_fix=solver_cfg.get('entropy_fix', False),
                        critical_flow_treatment=solver_cfg.get('critical_flow_treatment', False)
                    )
            elif spatial_order in [1, 2]:
                # 使用标准Godunov FVM求解器（1阶或2阶MUSCL）
                self.solver = GodunvFVMSolver(
                    width=geom['channel_width'],
                    length=geom['channel_length'],
                    n_cells=mesh['n_cells'],
                    manning_n=geom['manning_n'],
                    slope=slope,
                    g=9.81,
                    cfl=solver_cfg['cfl'],
                    eps_dry=solver_cfg['eps_dry'],
                    order=spatial_order,
                    riemann_solver=solver_cfg['riemann_solver'],
                    well_balanced=solver_cfg['well_balanced'],
                    use_numba=solver_cfg['use_numba'],
                    dt_max=solver_cfg.get('dt_max', None),
                    entropy_fix=solver_cfg.get('entropy_fix', False),
                    critical_flow_treatment=solver_cfg.get('critical_flow_treatment', False)
                )
            else:
                raise ValueError(f"不支持的spatial_order: {spatial_order}. 支持: 1, 2, 3")
        else:
            raise ValueError(f"不支持的求解器类型: {solver_cfg['type']}")

        # 设置初始条件
        h_init, Q_init = self._get_initial_conditions()

        # 设置边界条件
        bc_left, bc_right = self._get_boundary_conditions()

        # 初始化求解器
        self.solver.initialize(h_init, Q_init, bc_left, bc_right)

        # 如果IC文件包含z_b，覆盖求解器的z_b
        if self.z_b_from_file is not None:
            self.solver.z_b = self.z_b_from_file.copy()

        return self.solver

    def _get_bottom_slope(self) -> Any:
        """获取底坡（标量或数组）"""
        geom = self.config['geometry']
        slope = geom['bottom_slope']

        # 如果是列表，转为numpy数组
        if isinstance(slope, list):
            return np.array(slope)
        else:
            return slope

    def _get_initial_conditions(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取初始条件

        Returns:
            h_init, Q_init
        """
        ic = self.config['initial_conditions']
        geom = self.config['geometry']
        mesh = self.config['mesh']
        n_cells = mesh['n_cells']

        # 获取单元中心坐标
        dx = geom['channel_length'] / n_cells
        x = np.linspace(0.5*dx, geom['channel_length'] - 0.5*dx, n_cells)

        if ic['type'] == 'dam_break':
            # 溃坝初始条件
            dam_pos = ic.get('dam_position', geom['channel_length'] / 2)
            h_L = ic['h_left']
            h_R = ic['h_right']
            Q_init_val = ic.get('Q_initial', 0.0)

            h_init = np.where(x < dam_pos, h_L, h_R)
            Q_init = np.ones(n_cells) * Q_init_val

        elif ic['type'] == 'uniform':
            # 均匀流初始条件
            h_init = np.ones(n_cells) * ic['h']
            Q_init = np.ones(n_cells) * ic['Q']

        elif ic['type'] == 'from_file':
            # 从文件读取
            file_path = ic['file']
            data = np.loadtxt(file_path, delimiter=',', skiprows=1)
            h_init = data[:, 1]  # 假设第2列是h
            Q_init = data[:, 2]  # 假设第3列是Q

            # 检查是否有第4列（z_b）
            if data.shape[1] >= 4:
                z_b_from_file = data[:, 3]
                # 保存到实例变量，稍后设置到求解器
                self.z_b_from_file = z_b_from_file
            else:
                self.z_b_from_file = None

            if len(h_init) != n_cells:
                raise ValueError(f"初始条件数据点数({len(h_init)})与网格单元数({n_cells})不匹配")

        elif ic['type'] == 'expression':
            # Python表达式
            expr = ic['expression']
            safe_globals = {"__builtins__": {}, "np": np, "x": x, "abs": abs, "max": max, "min": min}
            h_init = eval(expr['h'], safe_globals)
            Q_init = eval(expr['Q'], safe_globals)

        else:
            raise ValueError(f"不支持的初始条件类型: {ic['type']}")

        return h_init, Q_init

    def _get_boundary_conditions(self) -> Tuple[Dict, Dict]:
        """
        获取边界条件

        Returns:
            bc_left, bc_right
        """
        bc_cfg = self.config['boundary_conditions']

        # 左边界
        bc_left = self._parse_boundary_condition(bc_cfg['left'])

        # 右边界
        bc_right = self._parse_boundary_condition(bc_cfg['right'])

        return bc_left, bc_right

    def _parse_boundary_condition(self, bc_dict: Dict) -> Dict:
        """
        解析单个边界条件

        Args:
            bc_dict: 边界条件配置字典

        Returns:
            求解器接受的边界条件字典
        """
        bc_type = bc_dict['type']

        if bc_type in ['h', 'Q']:
            # 简单水深或流量边界
            value = bc_dict['value']

            # 如果有时间序列，创建插值函数
            if 'time_series' in bc_dict and bc_dict['time_series']:
                value = self._create_time_series_interpolator(bc_dict['time_series'], value)

            return {'type': bc_type, 'value': value}

        elif bc_type == 'critical':
            # 临界流边界条件（基于特征线方法）
            # 自动计算临界水深 h_c = (Q²/(g*B²))^(1/3)
            return {'type': 'critical'}

        elif bc_type == 'supercritical':
            # 急流边界条件（同时指定h和Q）
            h_value = bc_dict['h']
            Q_value = bc_dict['Q']
            return {'type': 'supercritical', 'h': h_value, 'Q': Q_value}

        elif bc_type == 'discharge':
            # 流量边界条件（discharge是flow的别名）
            Q_val = bc_dict.get('value', bc_dict.get('Q', 0.0))
            return {'type': 'Q', 'value': Q_val}

        elif bc_type == 'rating_curve':
            # 水位-流量关系: Q = C * (h - h0)^n 或离散表格
            return self._parse_rating_curve(bc_dict)

        elif bc_type == 'hydrograph':
            # 流量过程线: Q(t) 时间序列
            return self._parse_hydrograph(bc_dict)

        else:
            raise ValueError(f"不支持的边界条件类型: {bc_type}")

    def _create_time_series_interpolator(self, time_series, default_value):
        """
        创建时间序列插值函数

        Args:
            time_series: 时间序列数据，格式为:
                - dict: {'times': [...], 'values': [...]}
                - list: [[t0, v0], [t1, v1], ...]
                - str: CSV文件路径
            default_value: 默认值（超出范围时使用）

        Returns:
            插值函数 f(t) -> value
        """
        from scipy.interpolate import interp1d

        if isinstance(time_series, str):
            data = np.loadtxt(time_series, delimiter=',', skiprows=1)
            times = data[:, 0]
            values = data[:, 1]
        elif isinstance(time_series, dict):
            times = np.array(time_series['times'])
            values = np.array(time_series['values'])
        elif isinstance(time_series, list):
            arr = np.array(time_series)
            times = arr[:, 0]
            values = arr[:, 1]
        else:
            return default_value

        interp_func = interp1d(
            times, values,
            kind='linear',
            bounds_error=False,
            fill_value=(values[0], values[-1])
        )

        def bc_value(t):
            return float(interp_func(t))

        return bc_value

    def _parse_rating_curve(self, bc_dict: Dict) -> Dict:
        """
        解析水位-流量关系（Rating Curve）边界条件

        支持两种格式:
        1. 幂律公式: Q = coefficient * (h - datum)^exponent
        2. 离散表格: {'h_values': [...], 'Q_values': [...]}
        """
        from scipy.interpolate import interp1d

        if 'coefficient' in bc_dict:
            C = bc_dict['coefficient']
            h0 = bc_dict.get('datum', 0.0)
            n = bc_dict.get('exponent', 1.5)

            def rating_Q(h):
                dh = max(h - h0, 0.0)
                return C * dh ** n

            return {'type': 'rating_curve', 'func': rating_Q}

        elif 'h_values' in bc_dict and 'Q_values' in bc_dict:
            h_vals = np.array(bc_dict['h_values'])
            Q_vals = np.array(bc_dict['Q_values'])

            interp_func = interp1d(
                h_vals, Q_vals,
                kind='linear',
                bounds_error=False,
                fill_value=(Q_vals[0], Q_vals[-1])
            )

            def rating_Q_table(h):
                return float(interp_func(h))

            return {'type': 'rating_curve', 'func': rating_Q_table}

        else:
            raise ValueError(
                "Rating curve需要提供 'coefficient'+'exponent' 或 'h_values'+'Q_values'"
            )

    def _parse_hydrograph(self, bc_dict: Dict) -> Dict:
        """
        解析流量过程线（Hydrograph）边界条件

        格式:
        - times + values: 时间-流量序列
        - file: CSV文件路径 (两列: time, Q)
        """
        if 'file' in bc_dict:
            data = np.loadtxt(bc_dict['file'], delimiter=',', skiprows=1)
            times = data[:, 0]
            values = data[:, 1]
        elif 'times' in bc_dict and 'values' in bc_dict:
            times = np.array(bc_dict['times'])
            values = np.array(bc_dict['values'])
        else:
            raise ValueError(
                "Hydrograph需要提供 'times'+'values' 或 'file'"
            )

        Q_func = self._create_time_series_interpolator(
            {'times': times.tolist(), 'values': values.tolist()},
            default_value=values[0]
        )

        return {'type': 'Q', 'value': Q_func}

    def get_analytical_solution(self, t: float, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取解析解（如果可用）

        Args:
            t: 时间
            x: 空间坐标

        Returns:
            h_analytical, u_analytical
        """
        val_cfg = self.config['validation']

        if not val_cfg['enabled']:
            return None, None

        solution_type = val_cfg['analytical_solution']

        if solution_type == 'ritter':
            # Ritter溃坝解
            return self._ritter_solution(t, x)
        elif solution_type == 'uniform_flow':
            # 均匀流
            return self._uniform_flow_solution()
        else:
            return None, None

    def _ritter_solution(self, t: float, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Ritter溃坝解析解"""
        ic = self.config['initial_conditions']
        geom = self.config['geometry']

        h_L = ic['h_left']
        dam_pos = ic.get('dam_position', geom['channel_length'] / 2)
        g = 9.81

        c0 = np.sqrt(g * h_L)
        x_rel = x - dam_pos  # 相对于溃坝位置的坐标

        x_tail = -c0 * t
        x_front = 2.0 * c0 * t

        h = np.zeros_like(x_rel)
        u = np.zeros_like(x_rel)

        for i, xi in enumerate(x_rel):
            if xi <= x_tail:
                h[i] = h_L
                u[i] = 0.0
            elif xi < x_front:
                u[i] = (2.0/3.0) * (xi/t + c0)
                c = (1.0/3.0) * (2.0*c0 - xi/t)
                h[i] = c**2 / g
            else:
                h[i] = 0.0
                u[i] = 0.0

        return h, u

    def _uniform_flow_solution(self) -> Tuple[np.ndarray, np.ndarray]:
        """均匀流解析解（Manning公式）"""
        ic = self.config['initial_conditions']
        geom = self.config['geometry']
        mesh = self.config['mesh']

        h_val = ic['h']
        Q_val = ic['Q']
        B = geom['channel_width']
        S0 = geom['bottom_slope']
        n = geom['manning_n']
        n_cells = mesh['n_cells']

        # 验证是否满足Manning公式
        A = h_val * B
        P = B + 2 * h_val
        R = A / P
        Q_manning = (1/n) * A * R**(2/3) * np.sqrt(S0)

        print(f"  Manning公式验证:")
        print(f"    给定流量: {Q_val:.3f} m³/s")
        print(f"    Manning流量: {Q_manning:.3f} m³/s")
        print(f"    误差: {abs(Q_val - Q_manning)/Q_val*100:.2f}%")

        u_val = Q_val / A

        # 返回数组（均匀流在所有位置相同）
        h_array = np.ones(n_cells) * h_val
        u_array = np.ones(n_cells) * u_val

        return h_array, u_array


if __name__ == '__main__':
    print("模型构建器测试\n")

    # 创建测试配置
    import json

    test_config = {
        "project": {
            "name": "溃坝模拟测试",
            "description": "ModelBuilder测试"
        },
        "geometry": {
            "type": "uniform",
            "channel_width": 10.0,
            "channel_length": 2000.0,
            "bottom_slope": 0.0,
            "manning_n": 0.0
        },
        "mesh": {
            "n_cells": 200
        },
        "solver": {
            "type": "godunov_fvm",
            "riemann_solver": "hll",
            "use_numba": True,
            "cfl": 0.5
        },
        "initial_conditions": {
            "type": "dam_break",
            "h_left": 10.0,
            "h_right": 1.0,
            "dam_position": 1000.0
        },
        "boundary_conditions": {
            "left": {"type": "h", "value": 10.0},
            "right": {"type": "h", "value": 1.0}
        },
        "simulation": {
            "end_time": 30.0
        },
        "validation": {
            "enabled": True,
            "analytical_solution": "ritter"
        }
    }

    # 保存测试配置
    test_file = '/tmp/test_model_config.json'
    with open(test_file, 'w') as f:
        json.dump(test_config, f, indent=2)

    # 构建模型
    try:
        builder = ModelBuilder.from_config_file(test_file)
        solver = builder.build_solver()

        print("\n 模型构建成功！")
        print(f"  求解器类型: {type(solver).__name__}")
        print(f"  网格数: {solver.n_cells}")
        print(f"  初始质量: {solver.initial_mass:.2f} m³")

        # 测试解析解
        print("\n测试解析解...")
        x = solver.x
        h_ana, u_ana = builder.get_analytical_solution(t=10.0, x=x)
        if h_ana is not None:
            print(f"  t=10s时最大水深: {np.max(h_ana):.3f} m")
            print(f"   解析解可用")

    except Exception as e:
        print(f"\n 模型构建失败:\n{e}")
        import traceback
        traceback.print_exc()
