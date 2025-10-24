#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MPC水位控制示例

演示使用自适应MPC控制器自动调节闸门开度，维持下游水位恒定

场景：
- 渠道中有一个闸门（位于3km处）
- 目标：维持监测点（3.75km处）水位在2.5m
- 控制方法：调节闸门开度（0.2-2.0m）
- 控制器：自适应MPC（模型预测控制）
  - 预测时域：10步
  - 控制时域：5步
  - 在线模型辨识和自适应

MPC vs PID：
- MPC优势：
  1. 显式处理约束（开度限制、变化率限制）
  2. 前馈预测，提前规划控制动作
  3. 在线模型辨识，适应系统变化
  4. 多目标优化（跟踪精度 vs 控制能耗）
- PID优势：
  1. 计算简单，实时性好
  2. 参数调节直观
  3. 无需系统模型

作者: Claude
日期: 2025-10-24
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def main():
    """
    主函数 - MPC水位控制示例
    """
    print("=" * 90)
    print("示例：MPC水位控制（模型预测控制）")
    print("=" * 90)
    print("\n本示例演示：")
    print("  1. 使用自适应MPC控制器自动调节闸门开度")
    print("  2. 维持下游水位恒定（目标：2.5m）")
    print("  3. 在线模型辨识和参数自适应")
    print("  4. 显式处理约束（开度限制、变化率限制）")
    print("  5. 控制周期：10秒")
    print("  6. 预测时域：10步（100秒）")
    print("  7. 总时间：10分钟")
    print("\n" + "=" * 90)

    # 运行模拟
    modeler = UniversalModeler("config_mpc_water_level.yaml")
    success = modeler.run()

    if not success:
        print("\n✗ 模拟失败")
        return False

    # 结果分析
    print("\n" + "=" * 90)
    print("控制效果分析：")
    print("=" * 90)

    # 从控制结果中提取性能指标
    result = modeler.control_result
    metrics = result['performance_metrics']

    print(f"\n控制器类型：{result['controller_type'].upper()}")
    print(f"设定值：{result['setpoint']:.2f} m")
    print(f"\n性能指标：")
    print(f"  平均绝对误差 (MAE): {metrics.get('mae', 0):.4f} m")
    print(f"  均方根误差 (RMSE): {metrics.get('rmse', 0):.4f} m")
    print(f"  最大误差: {metrics.get('max_error', 0):.4f} m")
    print(f"  稳态误差: {metrics.get('steady_state_error', 0):.4f} m")
    print(f"  积分平方误差 (ISE): {metrics.get('ise', 0):.4f}")
    print(f"  积分绝对误差 (IAE): {metrics.get('iae', 0):.4f}")

    # 控制量统计
    import numpy as np
    control_history = result['control_history']
    if len(control_history) > 0:
        control_array = np.array(control_history)
        if control_array.ndim == 2:
            control_array = control_array[:, 0]

        print(f"\n控制量统计（闸门开度）：")
        print(f"  初始值: {control_array[0]:.3f} m")
        print(f"  最终值: {control_array[-1]:.3f} m")
        print(f"  平均值: {control_array.mean():.3f} m")
        print(f"  最小值: {control_array.min():.3f} m")
        print(f"  最大值: {control_array.max():.3f} m")

        # 控制平滑度（变化率）
        if len(control_array) > 1:
            control_changes = np.diff(control_array)
            print(f"\n控制平滑度：")
            print(f"  平均变化幅度: {np.abs(control_changes).mean():.4f} m/步")
            print(f"  最大变化幅度: {np.abs(control_changes).max():.4f} m/步")

    print("\n" + "=" * 90)
    print("MPC特性：")
    print("=" * 90)
    print("✓ 在线模型辨识 - 自适应系统动态变化")
    print("✓ 显式约束处理 - 严格满足物理限制")
    print("✓ 前馈预测控制 - 提前规划控制动作")
    print("✓ 多目标优化 - 平衡跟踪精度与控制能耗")

    print("\n" + "=" * 90)
    print(f"✓ 模拟完成！")
    print(f"  结果目录: {modeler.output_dir}")
    print("=" * 90)

    return True


if __name__ == "__main__":
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 运行
    success = main()

    # 返回状态码
    sys.exit(0 if success else 1)
