#!/usr/bin/env python3
"""
时变边界条件展示案例 - 运行所有配置

展示三种时变边界条件类型：
1. Sinusoidal - 正弦波动（周期性变化）
2. Step - 阶跃变化（突发事件）
3. Linear - 线性变化（渐进过程）

运行示例：
    python run_all.py

单独运行：
    python -m modeling.universal_modeler config_sinusoidal.yaml
    python -m modeling.universal_modeler config_step.yaml
    python -m modeling.universal_modeler config_linear.yaml
"""

import sys
import os
from pathlib import Path
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modeling.universal_modeler import UniversalModeler


def print_header(title):
    """打印标题"""
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)
    print()


def print_bc_info(config_name, bc_config):
    """打印边界条件信息"""
    bc_type = bc_config.get('type', 'unknown')

    print(f"边界条件类型: {bc_type.upper()}")
    print(f"作用边界: {bc_config.get('boundary', 'unknown')}")
    print()

    if bc_type == 'sinusoidal':
        base = bc_config.get('base', 0)
        amp = bc_config.get('amplitude', 0)
        period = bc_config.get('period', 0)
        print(f"  基础值: {base} m³/s")
        print(f"  振幅: ±{amp} m³/s")
        print(f"  周期: {period} s ({period/60:.1f} 分钟)")
        print(f"  范围: {base-amp} - {base+amp} m³/s")
        print(f"  公式: Q(t) = {base} + {amp}*sin(2π*t/{period})")

    elif bc_type == 'step':
        step_time = bc_config.get('step_time', 0)
        before = bc_config.get('value_before', 0)
        after = bc_config.get('value_after', 0)
        increase = (after - before) / before * 100
        print(f"  阶跃时刻: {step_time} s ({step_time/60:.1f} 分钟)")
        print(f"  阶跃前值: {before} m³/s")
        print(f"  阶跃后值: {after} m³/s")
        print(f"  变化幅度: +{increase:.1f}%")

    elif bc_type == 'linear':
        start = bc_config.get('start_value', 0)
        end = bc_config.get('end_value', 0)
        duration = bc_config.get('duration', 0)
        rate = (end - start) / duration
        print(f"  起始值: {start} m³/s")
        print(f"  终止值: {end} m³/s")
        print(f"  变化时长: {duration} s ({duration/60:.1f} 分钟)")
        print(f"  变化率: {rate:.4f} m³/s²")
        print(f"  公式: Q(t) = {start} + {rate:.4f}*t (t ≤ {duration}s)")


def run_case(config_file, case_name):
    """运行单个案例"""
    print_header(f"运行案例: {case_name}")

    # 创建建模器
    modeler = UniversalModeler(str(config_file))

    # 打印边界条件信息
    sim_config = modeler.config.get_simulation_config()
    if 'time_varying_bc' in sim_config:
        print_bc_info(case_name, sim_config['time_varying_bc'])

    # 运行仿真
    print("-" * 80)
    print("开始仿真...")
    print()

    start_time = time.time()
    result = modeler.run()
    elapsed = time.time() - start_time

    # 打印结果摘要
    if hasattr(modeler, 'unsteady_result') and modeler.unsteady_result:
        unsteady = modeler.unsteady_result
        print()
        print(f"仿真完成! 用时: {elapsed:.2f}s")
        print(f"  时间步数: {len(unsteady['time'])}")
        if 'h_history' in unsteady:
            print(f"  最终水深范围: {unsteady['h_history'][-1].min():.3f} - {unsteady['h_history'][-1].max():.3f} m")
            # 计算流速
            B = modeler.solver.B
            h_final = unsteady['h_history'][-1]
            hu_final = unsteady['hu_history'][-1]
            v_final = hu_final / (h_final + 1e-10)  # 避免除零
            print(f"  最终流速范围: {v_final.min():.3f} - {v_final.max():.3f} m/s")

    # 输出文件位置
    output_dir = modeler.config.get_output_config()['directory']
    print(f"\n  结果保存至: {output_dir}/")

    return result


def main():
    """运行所有时变边界条件案例"""

    print("=" * 80)
    print("时变边界条件展示案例")
    print("=" * 80)
    print()
    print("本案例展示三种时变边界条件类型：")
    print()
    print("  1. Sinusoidal - 正弦波动（周期性变化）")
    print("     应用：潮汐、日用水量变化、周期性调度")
    print()
    print("  2. Step - 阶跃变化（突发事件）")
    print("     应用：闸门开启、水库泄洪、应急调度")
    print()
    print("  3. Linear - 线性变化（渐进过程）")
    print("     应用：缓慢蓄水、计划泄洪、负荷斜坡")
    print()
    print("-" * 80)

    # 配置文件路径
    example_dir = Path(__file__).parent
    configs = [
        (example_dir / "config_sinusoidal.yaml", "正弦波动 (Sinusoidal)"),
        (example_dir / "config_step.yaml", "阶跃变化 (Step)"),
        (example_dir / "config_linear.yaml", "线性变化 (Linear)")
    ]

    # 运行所有案例
    results = {}
    for config_file, case_name in configs:
        try:
            result = run_case(config_file, case_name)
            results[case_name] = result
            print()
        except Exception as e:
            print(f"\n✗ 案例 '{case_name}' 失败: {e}\n")
            import traceback
            traceback.print_exc()

    # 总结
    print_header("案例运行总结")
    print(f"成功: {len(results)}/{len(configs)}")
    print()
    for case_name in results:
        print(f"  ✓ {case_name}")
    print()


if __name__ == "__main__":
    main()
