#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows中文环境 - 直接引擎测试脚本
绕过API后台任务，直接调用计算引擎进行测试

使用方法:
    python Windows直接引擎测试.py
"""

import sys
import os
import io

# ========== Windows UTF-8 设置 ==========
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# ========== 添加路径 ==========
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from datetime import datetime
import time

# 颜色输出
def print_success(msg: str):
    print(f"✅ {msg}")

def print_error(msg: str):
    print(f"❌ {msg}")

def print_info(msg: str):
    print(f"ℹ️  {msg}")

def print_header(msg: str):
    print("\n" + "="*70)
    print(f"  {msg}")
    print("="*70)


def main():
    """主函数"""
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " "*15 + "HydroClaude Web Windows直接引擎测试" + " "*18 + "║")
    print("╚" + "═"*68 + "╝\n")
    
    print_info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Python版本: {sys.version.split()[0]}")
    print_info(f"平台: {sys.platform}")
    print_info(f"编码: {sys.stdout.encoding}")
    
    # 测试1: 导入引擎
    print_header("测试 1/4: 导入计算引擎")
    try:
        from core.hydraulic_engine import HydraulicEngine
        print_success("成功导入 HydraulicEngine")
    except ImportError as e:
        print_error(f"导入失败: {e}")
        return 1
    
    # 测试2: 创建引擎实例
    print_header("测试 2/4: 创建引擎实例")
    try:
        engine = HydraulicEngine()
        print_success("引擎实例创建成功")
    except Exception as e:
        print_error(f"创建失败: {e}")
        return 1
    
    # 测试3: 运行中文名称仿真
    print_header("测试 3/4: 运行中文名称仿真")
    
    config = {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.025,
        "slope": 0.001,
        "t_end": 5.0,
        "dt_max": 0.1,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 10.0
        },
        "boundary_conditions": {
            "upstream": {"type": "Q", "value": 10.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    }
    
    print_info("配置参数:")
    print(f"    - 渠道宽度: {config['width']} m")
    print(f"    - 渠道长度: {config['length']} m")
    print(f"    - 网格数量: {config['n_cells']}")
    print(f"    - 糙率: {config['manning_n']}")
    print(f"    - 坡度: {config['slope']}")
    print()
    
    print_info("正在计算...")
    start_time = time.time()
    
    try:
        result = engine.run_canal_simulation("均匀流测试_中文环境", config)
        duration = time.time() - start_time
        
        if result.status == 'completed':
            print_success(f"仿真完成！(耗时: {duration:.2f}秒)")
            print()
            print_info("计算结果:")
            print(f"    - 状态: {result.status}")
            print(f"    - 质量守恒误差: {result.metrics['mass_conservation_error']:.8f}%")
            print(f"    - 收敛状态: {'✅ 已收敛' if result.metrics['converged'] else '❌ 未收敛'}")
            print(f"    - 最大水深: {result.metrics['max_depth']:.3f} m")
            print(f"    - 平均水深: {result.metrics['mean_depth_final']:.3f} m")
            print(f"    - 最大流速: {result.metrics['max_velocity']:.3f} m/s")
            print(f"    - 迭代次数: {result.metrics['total_iterations']}")
            
        else:
            print_error(f"仿真失败: {result.error_message}")
            return 1
            
    except Exception as e:
        print_error(f"仿真异常: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 测试4: 验证结果
    print_header("测试 4/4: 验证结果")
    
    passed = True
    
    # 检查质量守恒
    if result.metrics['mass_conservation_error'] < 0.01:
        print_success(f"质量守恒 < 0.01%")
    else:
        print_error(f"质量守恒误差过大: {result.metrics['mass_conservation_error']:.4f}%")
        passed = False
    
    # 检查收敛
    if result.metrics['converged']:
        print_success("仿真已收敛")
    else:
        print_error("仿真未收敛")
        passed = False
    
    # 检查水深合理性
    if 4.0 < result.metrics['mean_depth_final'] < 6.0:
        print_success(f"水深合理: {result.metrics['mean_depth_final']:.3f} m")
    else:
        print_error(f"水深异常: {result.metrics['mean_depth_final']:.3f} m")
        passed = False
    
    # 总结
    print_header("测试总结")
    
    if passed:
        print()
        print("  " + "="*66)
        print("  " + " "*20 + "🎉 所有测试通过！" + " "*25)
        print("  " + "="*66)
        print()
        print_success("HydroClaude Web 引擎在Windows中文环境下工作正常！")
        print()
        print_info("系统已验证功能:")
        print("    ✅ 引擎导入和实例化")
        print("    ✅ 中文名称支持")
        print("    ✅ 仿真计算正确")
        print("    ✅ 结果验证通过")
        print()
        return 0
    else:
        print()
        print("  " + "="*66)
        print("  " + " "*20 + "⚠️  部分测试失败" + " "*25)
        print("  " + "="*66)
        print()
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        print()
        # 只在Windows交互式环境等待
        if sys.platform == 'win32' and sys.stdin.isatty():
            input("按回车键退出...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n严重错误: {str(e)}")
        import traceback
        traceback.print_exc()
        if sys.platform == 'win32' and sys.stdin.isatty():
            input("\n按回车键退出...")
        sys.exit(1)
