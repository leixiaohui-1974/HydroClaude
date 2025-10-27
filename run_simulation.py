#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键运行脚本

通过配置文件快速运行水力学模拟。

使用方法：
    python3 run_simulation.py config/examples/simple_canal.yaml
    python3 run_simulation.py config/examples/gate_pump_cascade.yaml

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os
import argparse

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HydraulicModelConfig


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='一键运行水力学模拟',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行简单明渠
  python3 run_simulation.py config/examples/simple_canal.yaml
  
  # 运行串联闸泵群
  python3 run_simulation.py config/examples/gate_pump_cascade.yaml
  
  # 运行非恒定流
  python3 run_simulation.py config/examples/unsteady_flood.yaml
        """
    )
    
    parser.add_argument('config_file', 
                       help='YAML配置文件路径')
    parser.add_argument('--quiet', '-q',
                       action='store_true',
                       help='静默模式（减少输出）')
    
    args = parser.parse_args()
    
    # 检查文件
    if not os.path.exists(args.config_file):
        print(f"❌ 错误：配置文件不存在: {args.config_file}")
        sys.exit(1)
    
    try:
        # 加载配置
        print("="*70)
        print("HydroClaude 一维水力学模拟")
        print("="*70)
        print(f"配置文件: {args.config_file}\n")
        
        config = HydraulicModelConfig(args.config_file)
        
        # 打印配置摘要
        if not args.quiet:
            config.print_summary()
        
        # 运行模拟
        print("\n" + "="*70)
        print("开始模拟")
        print("="*70)
        
        result = config.run_simulation(verbose=not args.quiet)
        
        # 打印结果摘要
        print("\n" + "="*70)
        print("模拟完成")
        print("="*70)
        
        if 'error' in result:
            print(f"流量误差: {result['error']:.4f}%")
        if 'conservation_error' in result:
            print(f"质量守恒: {result['conservation_error']:.2e}")
        if 'converged' in result:
            print(f"收敛状态: {'✓ 是' if result['converged'] else '✗ 否'}")
        if 'iterations' in result:
            print(f"迭代次数: {result['iterations']}")
        
        print("\n✅ 模拟成功完成！")
        print("="*70)
        
        return 0
    
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        if not args.quiet:
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
