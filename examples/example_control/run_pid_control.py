#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PID水位控制示例

演示使用PID控制器自动调节闸门开度，维持下游水位恒定

场景：
- 渠道中有一个闸门（位于3km处）
- 目标：维持监测点（3.75km处）水位在2.5m
- 控制方法：调节闸门开度（0.2-2.0m）
- 控制器：PID控制器

作者: Claude
日期: 2025-10-24
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def main():
    """
    主函数 - PID水位控制示例
    """
    print("=" * 90)
    print("示例：PID水位控制")
    print("=" * 90)
    print("\n本示例演示：")
    print("  1. 使用PID控制器自动调节闸门开度")
    print("  2. 维持下游水位恒定（目标：2.5m）")
    print("  3. 控制周期：5秒")
    print("  4. 总时间：10分钟")
    print("\n" + "=" * 90)

    # 运行模拟
    modeler = UniversalModeler("config_pid_water_level.yaml")
    success = modeler.run()

    if not success:
        print("\n 模拟失败")
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

    print("\n" + "=" * 90)
    print(f" 模拟完成！")
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
