#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 统一仿真引擎主入口
Unified Simulation Engine Entry Point

这是HydroClaude的唯一程序入口，所有仿真都通过这个程序执行。

功能:
1. 解析配置文件
2. 执行仿真
3. 输出结果

对标商业软件: HEC-RAS, MIKE 11/21, InfoWorks ICM

用法:
    python hydro_engine.py config.json
    python hydro_engine.py config.json --validate
    python hydro_engine.py config.json -o results/my_case --verbose

Author: HydroClaude Development Team
Date: 2025-11-15
Version: 1.0.0
"""

import argparse
import sys
import os
import time
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.config_parser import ConfigParser
from core.simulation_engine import SimulationEngine
from core.output_manager import OutputManager


__version__ = "1.0.0"
__author__ = "HydroClaude Development Team"


def print_banner():
    """打印程序横幅"""
    banner = """
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║    ██╗  ██╗██╗   ██╗██████╗ ██████╗  ██████╗  ██████╗██╗      █████╗     ║
║    ██║  ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██╔═══██╗██╔════╝██║     ██╔══██╗    ║
║    ███████║ ╚████╔╝ ██║  ██║██████╔╝██║   ██║██║     ██║     ███████║    ║
║    ██╔══██║  ╚██╔╝  ██║  ██║██╔══██╗██║   ██║██║     ██║     ██╔══██║    ║
║    ██║  ██║   ██║   ██████╔╝██║  ██║╚██████╔╝╚██████╗███████╗██║  ██║    ║
║    ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝    ║
║                                                                            ║
║                   Commercial-Grade Open Source Hydraulics                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

    Version: {version}
    Authors: {author}
    
    对标商业软件: HEC-RAS | MIKE 11/21 | InfoWorks ICM
    特点: 统一入口 | 标准化I/O | 现代化Web展示 | 完全开源
    
""".format(version=__version__, author=__author__)
    
    print(banner)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='HydroClaude 统一仿真引擎 - 商业级开源水力学软件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本用法
    python hydro_engine.py config.json
    
    # 仅验证配置文件
    python hydro_engine.py config.json --validate
    
    # 指定输出目录
    python hydro_engine.py config.json -o results/my_case
    
    # 详细输出
    python hydro_engine.py config.json --verbose
    
    # 生成配置模板
    python hydro_engine.py --template steady_canal
    
更多信息: https://github.com/HydroClaude/HydroClaude
        """
    )
    
    parser.add_argument(
        'config',
        type=str,
        nargs='?',
        help='配置文件路径 (JSON格式)'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='仅验证配置文件，不运行仿真'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='覆盖配置文件中的输出目录'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'HydroClaude v{__version__}'
    )
    
    parser.add_argument(
        '--template',
        type=str,
        choices=['steady_canal', 'unsteady_canal', 'gate', 'weir', 'complex'],
        help='生成配置文件模板'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='仅显示配置摘要，不运行仿真'
    )
    
    return parser.parse_args()


def generate_template(template_type: str):
    """生成配置文件模板"""
    templates = {
        'steady_canal': {
            "metadata": {
                "title": "Simple Canal Steady Flow",
                "description": "基础明渠稳态流动计算",
                "author": "User",
                "version": "1.0"
            },
            "simulation": {
                "type": "steady",
                "mode": "single_canal"
            },
            "canal": {
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "grid": {
                    "nx": 201,
                    "type": "uniform"
                }
            },
            "boundary_conditions": {
                "upstream": {
                    "type": "flow",
                    "value": 8.0
                },
                "downstream": {
                    "type": "depth",
                    "value": None,
                    "method": "uniform_flow"
                }
            },
            "solver": {
                "method": "hydrostatic",
                "parameters": {
                    "max_iterations": 5000,
                    "convergence_tol": 0.1
                }
            },
            "initial_conditions": {
                "depth": "uniform_flow",
                "flow": 8.0
            },
            "output": {
                "directory": "results/steady_canal",
                "formats": ["json", "csv"],
                "variables": ["depth", "flow", "velocity", "elevation"],
                "plots": {
                    "enabled": True,
                    "types": ["profile"]
                }
            }
        },
        
        'unsteady_canal': {
            "metadata": {
                "title": "Unsteady Canal Flow",
                "description": "非恒定流渠道计算"
            },
            "simulation": {
                "type": "unsteady",
                "mode": "single_canal",
                "time": {
                    "start": 0.0,
                    "end": 100.0,
                    "dt": 0.5,
                    "output_interval": 1.0
                }
            },
            "canal": {
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "grid": {"nx": 201}
            },
            "boundary_conditions": {
                "upstream": {"type": "flow", "value": 8.0},
                "downstream": {"type": "depth", "method": "uniform_flow"}
            },
            "solver": {
                "method": "godunov",
                "parameters": {"cfl": 0.5, "order": 1}
            },
            "output": {
                "directory": "results/unsteady_canal",
                "formats": ["json", "csv"],
                "plots": {
                    "enabled": True,
                    "types": ["profile", "time_series"]
                }
            }
        },
        
        'gate': {
            "metadata": {
                "title": "Sluice Gate Flow",
                "description": "闸门控制流动"
            },
            "simulation": {"type": "steady", "mode": "single_canal"},
            "canal": {
                "length": 10000.0,
                "width": 10.0,
                "slope": 0.0005,
                "manning_n": 0.025,
                "grid": {"nx": 201}
            },
            "structures": [
                {
                    "type": "sluice_gate",
                    "name": "Gate_1",
                    "position": 5000.0,
                    "parameters": {
                        "width": 10.0,
                        "opening": 2.0
                    }
                }
            ],
            "boundary_conditions": {
                "upstream": {"type": "flow", "value": 50.0},
                "downstream": {"type": "normal_depth"}
            },
            "solver": {
                "method": "hydrostatic",
                "parameters": {
                    "max_iterations": 10000,
                    "convergence_tol": 0.1
                }
            },
            "output": {
                "directory": "results/gate_flow",
                "formats": ["json", "csv"]
            }
        }
    }
    
    if template_type in templates:
        import json
        filename = f'config_template_{template_type}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(templates[template_type], f, indent=2, ensure_ascii=False)
        print(f"✅ 配置模板已生成: {filename}")
        return True
    else:
        print(f"❌ 未知的模板类型: {template_type}")
        return False


def main():
    """主函数"""
    # 解析参数
    args = parse_arguments()
    
    # 打印横幅
    if not args.template:
        print_banner()
    
    # 生成模板
    if args.template:
        return 0 if generate_template(args.template) else 1
    
    # 检查配置文件
    if not args.config:
        print("❌ 错误: 未指定配置文件")
        print("用法: python hydro_engine.py config.json")
        print("或使用 -h 查看帮助")
        return 1
    
    if not os.path.exists(args.config):
        print(f"❌ 错误: 配置文件不存在: {args.config}")
        return 1
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # ====================================================================
        # 步骤1: 解析配置
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤 1/3: 解析配置文件")
        print("=" * 80)
        
        config_parser = ConfigParser(verbose=args.verbose)
        config = config_parser.parse(args.config)
        
        # 覆盖输出目录（如果指定）
        if args.output:
            config['output']['directory'] = args.output
            if args.verbose:
                print(f"  输出目录已覆盖: {args.output}")
        
        # 打印摘要
        if args.verbose or args.summary:
            config_parser.print_summary()
        
        # 如果只是验证或查看摘要，到此结束
        if args.validate:
            print("\n✅ 配置文件验证通过！")
            return 0
        
        if args.summary:
            return 0
        
        # ====================================================================
        # 步骤2: 运行仿真
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤 2/3: 运行仿真")
        print("=" * 80)
        
        engine = SimulationEngine(config, verbose=args.verbose)
        results = engine.run()
        
        # ====================================================================
        # 步骤3: 输出结果
        # ====================================================================
        print("\n" + "=" * 80)
        print("步骤 3/3: 保存结果")
        print("=" * 80)
        
        output_manager = OutputManager(config, results, verbose=args.verbose)
        output_manager.save_all()
        
        # ====================================================================
        # 完成
        # ====================================================================
        end_time = time.time()
        total_time = end_time - start_time
        
        print("\n" + "=" * 80)
        print("✅ 仿真完成!")
        print("=" * 80)
        
        print(f"\n📊 总结:")
        print(f"  标题: {config['metadata']['title']}")
        print(f"  类型: {config['simulation']['type']}")
        print(f"  状态: {results['simulation']['status']}")
        print(f"  计算时间: {results['simulation']['duration_seconds']:.2f} 秒")
        print(f"  总用时: {total_time:.2f} 秒")
        
        if 'validation' in results:
            print(f"\n  验证评分: {results['validation']['overall_score']:.1f} ({results['validation']['overall_grade']})")
        
        print(f"\n📁 结果位置:")
        print(f"  {os.path.abspath(config['output']['directory'])}")
        
        # 打印Web链接
        web_index = os.path.join(config['output']['directory'], 'web', 'index.html')
        if os.path.exists(web_index):
            print(f"\n🌐 Web查看器:")
            print(f"  file://{os.path.abspath(web_index)}")
        
        print("\n" + "=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 130
        
    except Exception as e:
        print(f"\n\n❌ 错误: {str(e)}")
        
        if args.verbose:
            import traceback
            print("\n详细错误信息:")
            traceback.print_exc()
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
