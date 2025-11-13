"""
配置文件生成器 - Configuration Generator

提供交互式和编程式的配置文件生成功能，帮助用户快速创建
HydroClaude模拟配置文件，无需手动编写YAML。

主要功能：
- 交互式配置向导
- 基于模板的快速生成
- 参数验证
- 配置文件导出（YAML）
- 预定义场景模板

使用示例：
    from utils.config_generator import ConfigGenerator

    # 方式1：交互式向导
    gen = ConfigGenerator()
    gen.interactive_wizard()

    # 方式2：编程式生成
    config = gen.create_basic_canal(
        length=5000,
        nx=100,
        Q_in=20.0
    )
    gen.save_config(config, "my_config.yaml")

作者: Claude Code
创建日期: 2025-10-24
"""

import yaml
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json


class ConfigGenerator:
    """配置文件生成器"""

    # 预定义模板
    TEMPLATES = {
        'basic_canal': {
            'name': '基础渠道',
            'description': '简单的均匀渠道，稳态或非稳态模拟'
        },
        'canal_with_gate': {
            'name': '带闸门的渠道',
            'description': '渠道中包含一个闸门'
        },
        'canal_with_control': {
            'name': '带控制系统的渠道',
            'description': '渠道配置PID或MPC控制器'
        },
        'multi_structure': {
            'name': '多结构物渠道',
            'description': '包含多个结构物的复杂系统'
        }
    }

    def __init__(self):
        """初始化配置生成器"""
        self.config = {}

    def create_basic_canal(self, length: float, nx: int,
                          width: float = 10.0,
                          manning_n: float = 0.025,
                          slope: float = 0.0001,
                          Q_in: float = 20.0,
                          h_downstream: float = 2.0,
                          dt: float = 1.0,
                          T: float = 3600.0,
                          simulation_type: str = 'unsteady',
                          name: str = 'BasicCanalSimulation') -> Dict:
        """
        创建基础渠道配置

        Args:
            length: 渠道长度 (m)
            nx: 网格数量
            width: 渠道宽度 (m)
            manning_n: 曼宁糙率
            slope: 渠道坡度
            Q_in: 上游流量 (m³/s)
            h_downstream: 下游水深 (m)
            dt: 时间步长 (s)
            T: 模拟时间 (s)
            simulation_type: 模拟类型 ('steady' 或 'unsteady')
            name: 配置名称

        Returns:
            配置字典
        """
        config = {
            'simulation': {
                'name': name,
                'type': simulation_type,
                'dt': dt,
                'T': T if simulation_type == 'unsteady' else None,
                'save_interval': max(1, int(T / 100)) if simulation_type == 'unsteady' else None
            },
            'geometry': {
                'type': 'uniform_canal',
                'length': length,
                'nx': nx,
                'width': width,
                'manning_n': manning_n,
                'slope': slope
            },
            'boundary_conditions': {
                'upstream': {
                    'type': 'flow',
                    'value': Q_in
                },
                'downstream': {
                    'type': 'water_level',
                    'value': h_downstream
                }
            },
            'initial_conditions': {
                'type': 'uniform',
                'water_depth': h_downstream
            },
            'output': {
                'directory': 'output',
                'save_npz': True,
                'save_plots': True,
                'plot_interval': 10 if simulation_type == 'unsteady' else None
            }
        }

        # 移除None值
        config = self._remove_none_values(config)

        return config

    def add_structure(self, config: Dict, structure_type: str,
                     position: float, **params) -> Dict:
        """
        向配置添加结构物

        Args:
            config: 现有配置
            structure_type: 结构物类型
            position: 位置 (m)
            **params: 结构物参数

        Returns:
            更新后的配置
        """
        if 'structures' not in config:
            config['structures'] = []

        structure = {
            'type': structure_type,
            'position': position,
            **params
        }

        config['structures'].append(structure)

        return config

    def add_controller(self, config: Dict, controller_type: str,
                      target_level: float,
                      control_position: Optional[float] = None,
                      sensor_position: Optional[float] = None,
                      **params) -> Dict:
        """
        向配置添加控制器

        Args:
            config: 现有配置
            controller_type: 控制器类型 ('pid' 或 'mpc')
            target_level: 目标水位 (m)
            control_position: 控制点位置 (m)
            sensor_position: 传感器位置 (m)
            **params: 控制器参数

        Returns:
            更新后的配置
        """
        controller = {
            'type': controller_type,
            'target_level': target_level,
            'control_position': control_position,
            'sensor_position': sensor_position
        }

        # 添加特定控制器参数
        if controller_type == 'pid':
            controller.update({
                'Kp': params.get('Kp', 5.0),
                'Ki': params.get('Ki', 0.5),
                'Kd': params.get('Kd', 0.1),
                'output_limits': params.get('output_limits', [5.0, 30.0])
            })
        elif controller_type == 'mpc':
            controller.update({
                'horizon': params.get('horizon', 10),
                'Q': params.get('Q', 100.0),
                'R': params.get('R', 1.0),
                'u_limits': params.get('u_limits', [5.0, 30.0])
            })

        config['control'] = controller

        return config

    def add_time_varying_bc(self, config: Dict, bc_location: str,
                           bc_type: str, **params) -> Dict:
        """
        添加时变边界条件

        Args:
            config: 现有配置
            bc_location: 边界位置 ('upstream' 或 'downstream')
            bc_type: 边界类型 ('sinusoidal', 'step', 'linear', 'file')
            **params: 边界参数

        Returns:
            更新后的配置
        """
        if 'time_varying_bc' not in config:
            config['time_varying_bc'] = {}

        bc_config = {
            'type': bc_type,
            'boundary': bc_location
        }

        # 根据类型添加参数
        if bc_type == 'sinusoidal':
            bc_config.update({
                'base': params.get('base', 20.0),
                'amplitude': params.get('amplitude', 5.0),
                'period': params.get('period', 1800.0)
            })
        elif bc_type == 'step':
            bc_config.update({
                'initial': params.get('initial', 15.0),
                'final': params.get('final', 30.0),
                'step_time': params.get('step_time', 1800.0)
            })
        elif bc_type == 'linear':
            bc_config.update({
                'initial': params.get('initial', 15.0),
                'final': params.get('final', 25.0)
            })
        elif bc_type == 'file':
            bc_config.update({
                'file': params.get('file', 'flow_data.csv'),
                'column': params.get('column', 'flow')
            })

        config['time_varying_bc'][bc_location] = bc_config

        return config

    def validate_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """
        验证配置的有效性

        Args:
            config: 配置字典

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 检查必需的顶层键
        required_keys = ['simulation', 'geometry', 'boundary_conditions']
        for key in required_keys:
            if key not in config:
                errors.append(f"缺少必需的配置项: {key}")

        # 检查模拟参数
        if 'simulation' in config:
            sim = config['simulation']
            if 'type' not in sim:
                errors.append("simulation: 缺少'type'字段")
            elif sim['type'] == 'unsteady':
                if 'dt' not in sim or 'T' not in sim:
                    errors.append("simulation: 非稳态模拟需要'dt'和'T'")

        # 检查几何参数
        if 'geometry' in config:
            geom = config['geometry']
            required_geom = ['length', 'nx', 'width', 'manning_n', 'slope']
            for key in required_geom:
                if key not in geom:
                    errors.append(f"geometry: 缺少'{key}'字段")

            # 检查数值合理性
            if 'nx' in geom and geom['nx'] < 10:
                errors.append("geometry: nx应该至少为10")
            if 'manning_n' in geom and (geom['manning_n'] <= 0 or geom['manning_n'] > 0.1):
                errors.append("geometry: manning_n应该在(0, 0.1]范围内")

        # 检查边界条件
        if 'boundary_conditions' in config:
            bc = config['boundary_conditions']
            if 'upstream' not in bc or 'downstream' not in bc:
                errors.append("boundary_conditions: 需要定义上下游边界")

        return len(errors) == 0, errors

    def save_config(self, config: Dict, filename: str,
                   validate: bool = True) -> bool:
        """
        保存配置到YAML文件

        Args:
            config: 配置字典
            filename: 文件名
            validate: 是否验证配置

        Returns:
            是否成功
        """
        # 验证配置
        if validate:
            is_valid, errors = self.validate_config(config)
            if not is_valid:
                print(" 配置验证失败:")
                for error in errors:
                    print(f"  - {error}")
                return False

        # 保存文件
        output_path = Path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False,
                     allow_unicode=True, sort_keys=False)

        print(f" 配置已保存: {output_path}")
        return True

    def load_template(self, template_name: str) -> Dict:
        """
        加载预定义模板

        Args:
            template_name: 模板名称

        Returns:
            配置字典
        """
        if template_name == 'basic_canal':
            return self.create_basic_canal(
                length=5000, nx=100, Q_in=20.0, h_downstream=2.0
            )

        elif template_name == 'canal_with_gate':
            config = self.create_basic_canal(
                length=5000, nx=100, Q_in=20.0, h_downstream=2.0
            )
            config = self.add_structure(
                config, 'gate', position=2500,
                opening=0.8, width=10.0, height=3.0
            )
            return config

        elif template_name == 'canal_with_control':
            config = self.create_basic_canal(
                length=5000, nx=100, Q_in=20.0, h_downstream=2.0,
                simulation_type='unsteady'
            )
            config = self.add_structure(
                config, 'gate', position=2500,
                opening=0.8, width=10.0, height=3.0
            )
            config = self.add_controller(
                config, 'pid', target_level=2.5,
                sensor_position=3000, Kp=5.0, Ki=0.5, Kd=0.1
            )
            return config

        elif template_name == 'multi_structure':
            config = self.create_basic_canal(
                length=10000, nx=200, Q_in=25.0, h_downstream=2.5
            )
            config = self.add_structure(
                config, 'gate', position=3000,
                opening=0.9, width=12.0, height=4.0
            )
            config = self.add_structure(
                config, 'pump', position=6000,
                flow_rate=5.0, head=10.0
            )
            config = self.add_structure(
                config, 'weir', position=8000,
                crest_height=1.5, width=12.0
            )
            return config

        else:
            raise ValueError(f"未知模板: {template_name}")

    def interactive_wizard(self):
        """
        交互式配置向导
        """
        print("\n" + "="*70)
        print("  HydroClaude 配置文件生成向导")
        print("="*70 + "\n")

        print("选择配置方式:")
        print("1. 从模板开始")
        print("2. 从头创建")

        choice = input("\n请选择 (1/2): ").strip()

        if choice == '1':
            self._wizard_from_template()
        elif choice == '2':
            self._wizard_from_scratch()
        else:
            print("无效选择")

    def _wizard_from_template(self):
        """从模板开始的向导"""
        print("\n可用模板:")
        for i, (key, info) in enumerate(self.TEMPLATES.items(), 1):
            print(f"{i}. {info['name']}: {info['description']}")

        choice = input("\n选择模板 (1-4): ").strip()

        template_keys = list(self.TEMPLATES.keys())
        if choice.isdigit() and 1 <= int(choice) <= len(template_keys):
            template_name = template_keys[int(choice) - 1]
            config = self.load_template(template_name)

            print(f"\n 已加载模板: {self.TEMPLATES[template_name]['name']}")
            print("\n配置预览:")
            print(json.dumps(config, indent=2, ensure_ascii=False))

            # 询问是否保存
            filename = input("\n输入文件名 (如: config.yaml): ").strip()
            if filename:
                self.save_config(config, filename)
        else:
            print("无效选择")

    def _wizard_from_scratch(self):
        """从头创建的向导"""
        print("\n=== 基本参数 ===")

        try:
            length = float(input("渠道长度 (m) [5000]: ") or "5000")
            nx = int(input("网格数量 [100]: ") or "100")
            width = float(input("渠道宽度 (m) [10]: ") or "10")
            manning_n = float(input("曼宁糙率 [0.025]: ") or "0.025")
            slope = float(input("渠道坡度 [0.0001]: ") or "0.0001")

            print("\n=== 边界条件 ===")
            Q_in = float(input("上游流量 (m³/s) [20]: ") or "20")
            h_downstream = float(input("下游水深 (m) [2.0]: ") or "2.0")

            print("\n=== 模拟参数 ===")
            sim_type = input("模拟类型 (steady/unsteady) [unsteady]: ") or "unsteady"
            dt = float(input("时间步长 (s) [1.0]: ") or "1.0") if sim_type == 'unsteady' else 1.0
            T = float(input("模拟时间 (s) [3600]: ") or "3600") if sim_type == 'unsteady' else 3600

            # 创建配置
            config = self.create_basic_canal(
                length=length, nx=nx, width=width, manning_n=manning_n,
                slope=slope, Q_in=Q_in, h_downstream=h_downstream,
                dt=dt, T=T, simulation_type=sim_type
            )

            # 询问是否添加结构物
            add_struct = input("\n是否添加结构物? (y/n) [n]: ") or "n"
            if add_struct.lower() == 'y':
                struct_type = input("结构物类型 (gate/pump/weir): ").strip()
                struct_pos = float(input("位置 (m): "))
                config = self.add_structure(config, struct_type, struct_pos)

            # 询问是否添加控制器
            add_ctrl = input("\n是否添加控制器? (y/n) [n]: ") or "n"
            if add_ctrl.lower() == 'y':
                ctrl_type = input("控制器类型 (pid/mpc): ").strip()
                target = float(input("目标水位 (m): "))
                config = self.add_controller(config, ctrl_type, target)

            print("\n配置预览:")
            print(json.dumps(config, indent=2, ensure_ascii=False))

            # 保存配置
            filename = input("\n输入文件名 (如: config.yaml): ").strip()
            if filename:
                self.save_config(config, filename)

        except ValueError as e:
            print(f"输入错误: {e}")
        except KeyboardInterrupt:
            print("\n\n已取消")

    def _remove_none_values(self, d: Dict) -> Dict:
        """递归移除字典中的None值"""
        return {
            k: self._remove_none_values(v) if isinstance(v, dict) else v
            for k, v in d.items()
            if v is not None
        }


def main():
    """主函数 - 命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="HydroClaude 配置文件生成器")
    parser.add_argument("--template", type=str, choices=list(ConfigGenerator.TEMPLATES.keys()),
                       help="使用预定义模板")
    parser.add_argument("--output", type=str, default="config.yaml",
                       help="输出文件名")
    parser.add_argument("--interactive", action="store_true",
                       help="启动交互式向导")

    args = parser.parse_args()

    gen = ConfigGenerator()

    if args.interactive:
        gen.interactive_wizard()
    elif args.template:
        config = gen.load_template(args.template)
        gen.save_config(config, args.output)
    else:
        print("请使用 --interactive 或 --template 选项")
        print("示例:")
        print("  python config_generator.py --interactive")
        print("  python config_generator.py --template basic_canal --output my_config.yaml")


if __name__ == "__main__":
    main()
