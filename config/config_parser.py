#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件解析器

实现YAML配置文件驱动的自动化建模。

核心功能：
1. 解析YAML配置文件
2. 自动验证参数
3. 一键创建模型
4. 一键运行模拟

使用示例：
    >>> from config import HydraulicModelConfig
    >>> 
    >>> config = HydraulicModelConfig("my_canal.yaml")
    >>> result = config.run_simulation()  # 一行完成！
    >>> 
    >>> # 自动生成图表和报告

目标：工程师无需编写代码，仅配置参数即可完成模拟。

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import os
import sys
from typing import Dict, Any, Optional, List
import yaml

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入求解器
from solvers.v1_wellbalanced_fdm import (
    EnergyEquationSolver,
    WellBalancedCanalSolver
)
from solvers.v2_hybrid_fvfd import (
    HybridCanalSolver,
    UnsteadySolver,
    ConstantBC,
    TimeSeriesBC
)
from solvers.v3_dg_high_order import DGCanalSolver

# 导入结构物
from solvers.v1_wellbalanced_fdm.structures import (
    SluiceGate,
    PumpStation,
    BroadCrestedWeir
)


class ConfigValidator:
    """配置文件验证器"""
    
    @staticmethod
    def validate_canal(canal_config: Dict) -> None:
        """验证渠道配置"""
        required = ['length', 'width', 'slope', 'manning']
        for key in required:
            if key not in canal_config:
                raise ValueError(f"渠道配置缺少必需参数: {key}")
        
        # 数值范围检查
        if canal_config['length'] <= 0:
            raise ValueError(f"渠道长度必须>0，得到: {canal_config['length']}")
        if canal_config['width'] <= 0:
            raise ValueError(f"渠道宽度必须>0，得到: {canal_config['width']}")
        if canal_config['slope'] < 0:
            raise ValueError(f"渠底坡度必须>=0，得到: {canal_config['slope']}")
        if canal_config['manning'] <= 0:
            raise ValueError(f"Manning糙率必须>0，得到: {canal_config['manning']}")
    
    @staticmethod
    def validate_structures(structures: List[Dict]) -> None:
        """验证结构物配置"""
        if not structures:
            print("⚠️  警告：未配置结构物")
            return
        
        for i, struct in enumerate(structures):
            if 'type' not in struct:
                raise ValueError(f"结构物{i}缺少type字段")
            if 'position' not in struct:
                raise ValueError(f"结构物{i}缺少position字段")
            
            # 根据类型验证
            if struct['type'] == 'gate':
                if 'opening' not in struct:
                    raise ValueError(f"闸门{i}缺少opening字段")
            elif struct['type'] == 'pump':
                if 'rated_head' not in struct:
                    raise ValueError(f"泵站{i}缺少rated_head字段")
    
    @staticmethod
    def validate_boundary(boundary: Dict) -> None:
        """验证边界条件"""
        if 'upstream' not in boundary:
            raise ValueError("缺少上游边界条件")
        if 'downstream' not in boundary:
            raise ValueError("缺少下游边界条件")
        
        for bc_name in ['upstream', 'downstream']:
            bc = boundary[bc_name]
            if 'type' not in bc:
                raise ValueError(f"{bc_name}边界条件缺少type字段")
            if bc['type'] not in ['flow', 'depth']:
                raise ValueError(f"{bc_name}边界条件type必须是flow或depth")
            
            # 检查值
            if 'value' not in bc and 'timeseries' not in bc:
                raise ValueError(f"{bc_name}边界条件必须有value或timeseries")


class HydraulicModelConfig:
    """
    水力学模型配置类
    
    从YAML配置文件自动创建和运行水力学模型。
    
    配置文件格式见: config/example_canal_network.yaml
    
    核心功能：
    1. 解析YAML配置
    2. 自动验证参数
    3. 创建求解器和结构物
    4. 一键运行模拟
    5. 自动保存结果
    
    使用示例：
        >>> config = HydraulicModelConfig("my_canal.yaml")
        >>> result = config.run_simulation()  # 完成！
        >>> print(f"流量误差: {result['error']:.2f}%")
    """
    
    def __init__(self, config_file: str):
        """
        初始化配置
        
        Args:
            config_file: YAML配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        self._validate_config()
        
        # 解析后的配置
        self.canal_params = self.config['canal']
        self.structures_config = self.config.get('structures', [])
        self.boundary_config = self.config['boundary']
        self.solver_config = self.config.get('solver', {})
        self.output_config = self.config.get('output', {})
        
        # 求解器实例（延迟创建）
        self.solver = None
    
    def _load_config(self) -> Dict:
        """加载YAML配置文件"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _validate_config(self):
        """验证配置文件"""
        # 必需的顶层字段
        required_keys = ['canal', 'boundary']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"配置文件缺少必需字段: {key}")
        
        # 验证各部分
        ConfigValidator.validate_canal(self.config['canal'])
        ConfigValidator.validate_structures(self.config.get('structures', []))
        ConfigValidator.validate_boundary(self.config['boundary'])
        
        print("✅ 配置文件验证通过")
    
    def create_solver(self):
        """
        根据配置创建求解器
        
        Returns:
            solver: 求解器实例
        """
        # 求解器类型
        method = self.solver_config.get('method', 'hybrid_fvfd')
        
        # 基本参数
        length = self.canal_params['length']
        B = self.canal_params['width']
        S0 = self.canal_params['slope']
        n = self.canal_params['manning']
        
        # 网格参数
        mesh_config = self.config.get('mesh', {})
        n_cells = mesh_config.get('n_cells', 200)  # 默认200单元
        
        print(f"创建求解器: {method}")
        print(f"  渠道: L={length:.0f}m, B={B:.1f}m, S0={S0:.6f}, n={n:.3f}")
        print(f"  网格: {n_cells}单元")
        
        # 根据方法创建求解器
        if method == 'wellbalanced_fdm':
            # 方案A
            self.solver = WellBalancedCanalSolver(
                length=length,
                B=B,
                S0=S0,
                n=n,
                n_cells=n_cells
            )
        
        elif method == 'hybrid_fvfd':
            # 方案B（默认）
            # 判断是否需要非恒定流
            unsteady_config = self.solver_config.get('unsteady', {})
            if unsteady_config.get('enable', False):
                self.solver = UnsteadySolver(
                    length=length,
                    n_cells=n_cells,
                    B=B,
                    S0=S0,
                    n=n
                )
            else:
                self.solver = HybridCanalSolver(
                    length=length,
                    n_cells=n_cells,
                    B=B,
                    S0=S0,
                    n=n
                )
        
        elif method == 'dg_high_order':
            # 方案C
            n_elements = mesh_config.get('n_cells', 100)  # DG用更少单元
            order = self.solver_config.get('order', 3)
            
            self.solver = DGCanalSolver(
                length=length,
                n_elements=n_elements,
                order=order,
                B=B,
                S0=S0,
                n=n
            )
        
        else:
            raise ValueError(f"未知求解器类型: {method}")
        
        return self.solver
    
    def add_structures(self, solver):
        """
        添加结构物
        
        Args:
            solver: 求解器实例
        """
        if not self.structures_config:
            print("⚠️  无结构物")
            return
        
        print(f"\n添加结构物: {len(self.structures_config)}个")
        
        for struct_config in self.structures_config:
            struct_type = struct_config['type']
            position = struct_config['position']
            width = struct_config.get('width', self.canal_params['width'])
            name = struct_config.get('name', f"{struct_type}@{position:.0f}m")
            
            if struct_type == 'gate':
                # 闸门
                opening = struct_config['opening']
                structure = SluiceGate(
                    position=position,
                    width=width,
                    opening=opening,
                    name=name
                )
            
            elif struct_type == 'pump':
                # 泵站
                rated_flow = struct_config.get('rated_flow', 10.0)
                rated_head = struct_config['rated_head']
                structure = PumpStation(
                    position=position,
                    width=width,
                    rated_flow=rated_flow,
                    rated_head=rated_head,
                    name=name
                )
            
            elif struct_type == 'weir':
                # 堰
                crest_height = struct_config['crest_height']
                structure = BroadCrestedWeir(
                    position=position,
                    width=width,
                    crest_height=crest_height,
                    name=name
                )
            
            else:
                raise ValueError(f"未知结构物类型: {struct_type}")
            
            solver.add_structure(structure)
            print(f"  ✅ {name}")
    
    def set_boundary_conditions(self, solver):
        """
        设置边界条件
        
        Args:
            solver: 求解器实例
        """
        # 检查是否是非恒定流求解器
        if not hasattr(solver, 'boundary'):
            # 稳态求解器（方案A、B、C的稳态版本）
            # 边界条件通过solve()函数参数传入
            return
        
        print(f"\n设置边界条件:")
        
        # 上游边界
        upstream_config = self.boundary_config['upstream']
        if 'value' in upstream_config:
            # 恒定边界
            bc_upstream = ConstantBC(
                bc_type=upstream_config['type'],
                value=upstream_config['value']
            )
            print(f"  上游: 恒定{upstream_config['type']}={upstream_config['value']}")
        elif 'timeseries' in upstream_config:
            # 时间序列边界
            ts_file = upstream_config['timeseries']
            bc_upstream = TimeSeriesBC.from_csv(
                bc_type=upstream_config['type'],
                filename=ts_file
            )
            print(f"  上游: 时间序列{upstream_config['type']}（来自{ts_file}）")
        
        solver.boundary.set_upstream(bc_upstream)
        
        # 下游边界
        downstream_config = self.boundary_config['downstream']
        if 'value' in downstream_config:
            bc_downstream = ConstantBC(
                bc_type=downstream_config['type'],
                value=downstream_config['value']
            )
            print(f"  下游: 恒定{downstream_config['type']}={downstream_config['value']}")
        elif 'timeseries' in downstream_config:
            ts_file = downstream_config['timeseries']
            bc_downstream = TimeSeriesBC.from_csv(
                bc_type=downstream_config['type'],
                filename=ts_file
            )
            print(f"  下游: 时间序列{downstream_config['type']}（来自{ts_file}）")
        
        solver.boundary.set_downstream(bc_downstream)
    
    def build_model(self):
        """
        一键创建完整模型
        
        Returns:
            solver: 配置好的求解器
        """
        print("="*70)
        print("自动建模")
        print("="*70)
        print(f"配置文件: {self.config_file}")
        print("")
        
        # 创建求解器
        solver = self.create_solver()
        
        # 添加结构物
        self.add_structures(solver)
        
        # 设置边界条件
        self.set_boundary_conditions(solver)
        
        print("")
        print("="*70)
        print("✅ 模型创建完成")
        print("="*70)
        
        return solver
    
    def run_simulation(self, verbose: bool = True) -> Dict:
        """
        一键运行模拟
        
        自动：
        1. 创建模型
        2. 运行求解
        3. 保存结果
        4. 生成图表（如果配置）
        
        Args:
            verbose: 详细输出
        
        Returns:
            result: 求解结果字典
        """
        # 创建模型
        solver = self.build_model()
        
        # 判断稳态还是非恒定流
        solver_config = self.solver_config
        unsteady_config = solver_config.get('unsteady', {})
        
        if isinstance(solver, UnsteadySolver):
            # 非恒定流
            print("\n运行非恒定流模拟...")
            
            duration = unsteady_config.get('duration', 86400)
            dt_initial = unsteady_config.get('dt', 1.0)
            cfl = unsteady_config.get('cfl', 0.3)
            output_interval = unsteady_config.get('output_interval', 600)
            
            result = solver.solve_unsteady(
                duration=duration,
                dt_initial=dt_initial,
                cfl=cfl,
                output_interval=output_interval,
                verbose=verbose
            )
        
        else:
            # 稳态求解
            print("\n运行稳态求解...")
            
            # 从边界条件获取参数
            upstream_bc = self.boundary_config['upstream']
            downstream_bc = self.boundary_config['downstream']
            
            if upstream_bc['type'] != 'flow':
                raise ValueError("稳态求解需要上游流量边界条件")
            if downstream_bc['type'] != 'depth':
                raise ValueError("稳态求解需要下游水深边界条件")
            
            Q_target = upstream_bc['value']
            h_downstream = downstream_bc['value']
            
            steady_config = solver_config.get('steady_state', {})
            max_iter = steady_config.get('max_iter', 2000)
            tolerance = steady_config.get('tolerance', 0.01)
            
            # 根据求解器类型调用
            if isinstance(solver, EnergyEquationSolver):
                # 方案A：能量方程
                dx = self.config.get('mesh', {}).get('dx', 50.0)
                result = solver.solve(
                    Q=Q_target,
                    h_downstream=h_downstream,
                    dx=dx,
                    verbose=verbose
                )
            else:
                # 方案B/C：时间推进到稳态
                result = solver.solve_steady_state(
                    Q_target=Q_target,
                    h_downstream=h_downstream,
                    max_iter=max_iter,
                    tolerance=tolerance,
                    verbose=verbose
                )
        
        # 保存结果
        self.save_results(result)
        
        # 生成图表
        self.plot_results(result)
        
        return result
    
    def save_results(self, result: Dict):
        """
        保存结果到文件
        
        Args:
            result: 求解结果
        """
        output_config = self.output_config
        if not output_config:
            return
        
        output_dir = output_config.get('directory', 'results/')
        prefix = output_config.get('prefix', 'simulation')
        formats = output_config.get('formats', ['csv'])
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存为CSV
        if 'csv' in formats:
            import pandas as pd
            
            # 准备数据
            if 'x_center' in result:
                x = result['x_center']
            elif 'x' in result:
                x = result['x']
            else:
                x = result.get('x_face', np.arange(len(result['h'])))
            
            # 稳态结果
            if 'times' not in result:
                df = pd.DataFrame({
                    'x': x,
                    'h': result.get('h', []),
                    'z': result.get('z', []),
                    'eta': result.get('h', []) + result.get('z', []),
                })
                
                if 'Q' in result and len(result['Q']) == len(x):
                    df['Q'] = result['Q']
                
                csv_file = os.path.join(output_dir, f"{prefix}_steady.csv")
                df.to_csv(csv_file, index=False)
                print(f"\n✅ 结果已保存: {csv_file}")
            
            # 非恒定流结果
            else:
                # TODO: 保存时间序列数据
                print(f"\n⚠️  非恒定流结果保存待实现")
        
        print(f"输出目录: {output_dir}")
    
    def plot_results(self, result: Dict):
        """
        生成结果图表
        
        Args:
            result: 求解结果
        """
        output_config = self.output_config
        if not output_config or 'plots' not in output_config:
            return
        
        plots_to_generate = output_config['plots']
        
        # TODO: 实现自动绘图（Phase 2.3）
        print(f"\n⚠️  自动绘图功能将在Phase 2.3实现")
        print(f"  计划图表: {plots_to_generate}")
    
    def print_summary(self):
        """打印配置摘要"""
        print("="*70)
        print("配置摘要")
        print("="*70)
        print(f"配置文件: {self.config_file}")
        print(f"\n渠道参数:")
        for key, value in self.canal_params.items():
            print(f"  {key}: {value}")
        
        print(f"\n结构物: {len(self.structures_config)}个")
        for struct in self.structures_config:
            print(f"  - {struct['type']} @ {struct['position']:.0f}m")
        
        print(f"\n边界条件:")
        print(f"  上游: {self.boundary_config['upstream']}")
        print(f"  下游: {self.boundary_config['downstream']}")
        
        print(f"\n求解器: {self.solver_config.get('method', 'hybrid_fvfd')}")
        print("="*70)


# ========== 测试代码 ==========

def test_config_parser():
    """测试配置文件解析器"""
    print("\n" + "="*70)
    print("测试: 配置文件解析器")
    print("="*70)
    
    # 使用示例配置文件
    config_file = "config/example_canal_network.yaml"
    
    if not os.path.exists(config_file):
        print(f"⚠️  示例配置文件不存在: {config_file}")
        print("请先创建示例配置文件")
        return
    
    # 加载配置
    config = HydraulicModelConfig(config_file)
    
    # 打印摘要
    config.print_summary()
    
    # 创建模型
    print("\n测试模型创建...")
    solver = config.build_model()
    
    print(f"\n✓ 配置文件解析器测试完成")
    print(f"✓ 求解器类型: {type(solver).__name__}")
    print(f"✓ 结构物数量: {len(solver.structures)}")
    
    return config


if __name__ == '__main__':
    test_config_parser()
