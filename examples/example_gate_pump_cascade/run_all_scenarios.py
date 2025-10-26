#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键运行所有工况

运行5个标准化工况测试，生成完整的纵剖面动画和分析图表
"""

import os
import sys
import time
import subprocess


def run_scenario(scenario_file):
    """运行单个工况"""
    scenario_name = os.path.basename(scenario_file).replace('.py', '')
    
    print("\n" + "="*100)
    print(f"开始运行: {scenario_name}".center(100))
    print("="*100)
    
    start_time = time.time()
    
    # 运行脚本
    result = subprocess.run(
        [sys.executable, scenario_file],
        capture_output=False
    )
    
    elapsed = time.time() - start_time
    
    if result.returncode == 0:
        print(f"\n✓ {scenario_name} 完成 (耗时: {elapsed:.1f}s)")
        return True
    else:
        print(f"\n✗ {scenario_name} 失败")
        return False


def main():
    """主函数"""
    print("\n" + "="*100)
    print("串联明渠闸泵群系统 - 非恒定流工况测试套件".center(100))
    print("="*100)
    print("\n将运行5个标准化工况:")
    print("  1. 上游流量阶跃 (30→55 m³/s)")
    print("  2. 下游水位阶跃 (2.0→3.5 m)")
    print("  3. 闸门开度阶跃 (0.709→1.2 m)")
    print("  4. 泵站能力测试 (30→45 m³/s)")
    print("  5. 组合扰动 (流量+闸门+水位)")
    print("\n每个工况输出:")
    print("  - 水位纵剖面动画 (animation_water_level.gif)")
    print("  - 流量纵剖面动画 (animation_flow_rate.gif)")
    print("  - 时空演化图 (spatiotemporal.png)")
    print("  - 稳态纵剖面 (steady_state_profile.png)")
    print("  - 完整数据 (data.npz)")
    print("="*100)
    
    # 确认运行
    response = input("\n是否开始运行所有工况？(y/n): ")
    if response.lower() != 'y':
        print("取消运行")
        return
    
    # 工况列表
    scenarios_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios")
    scenarios = [
        os.path.join(scenarios_dir, "scenario_01_upstream_flow_step.py"),
        os.path.join(scenarios_dir, "scenario_02_downstream_level_step.py"),
        os.path.join(scenarios_dir, "scenario_03_gate_opening_step.py"),
        os.path.join(scenarios_dir, "scenario_04_pump_capacity_test.py"),
        os.path.join(scenarios_dir, "scenario_05_combined_disturbances.py"),
    ]
    
    # 运行所有工况
    total_start = time.time()
    results = []
    
    for scenario_file in scenarios:
        if os.path.exists(scenario_file):
            success = run_scenario(scenario_file)
            results.append((os.path.basename(scenario_file), success))
        else:
            print(f"\n✗ 文件不存在: {scenario_file}")
            results.append((os.path.basename(scenario_file), False))
    
    total_elapsed = time.time() - total_start
    
    # 打印总结
    print("\n" + "="*100)
    print("运行总结".center(100))
    print("="*100)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    print(f"\n成功: {success_count}/{total_count}")
    print(f"总耗时: {total_elapsed/60:.1f} 分钟\n")
    
    for scenario_name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {scenario_name}")
    
    print("\n" + "="*100)
    
    if success_count == total_count:
        print("✓ 所有工况运行成功！".center(100))
        print("\n结果位置: results_scenarios/".center(100))
    else:
        print("⚠ 部分工况运行失败".center(100))
    
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
