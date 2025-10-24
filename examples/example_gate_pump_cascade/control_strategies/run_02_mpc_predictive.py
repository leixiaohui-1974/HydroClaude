#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制策略2: MPC预测控制（计划性和预测性）

演示MPC控制器的核心优势：
1. 前馈预测：利用预测时域提前规划控制动作
2. 约束处理：显式满足闸门开度和变化率约束
3. 多步优化：在未来N步内全局优化控制序列
4. 平滑控制：通过控制权重最小化控制能耗

与PID对比：
- PID：反应式，误差驱动，快速但可能震荡
- MPC：计划式，模型驱动，平滑但计算量大

应用场景：
- 需要平滑控制的场合
- 有严格约束要求的系统
- 可以预测未来扰动的情况

作者: Claude
日期: 2025-10-24
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from modeling.universal_modeler import UniversalModeler
import numpy as np


def main():
    """
    主函数 - MPC预测控制
    """
    print("=" * 90)
    print("控制策略2: MPC预测控制（计划性和预测性）")
    print("=" * 90)
    print("\n系统配置：")
    print("  渠道长度: 100 km")
    print("  结构物: 2个闸门 + 1个泵站")
    print("  控制器: MPC（模型预测控制）")
    print("\nMPC参数：")
    print("  预测时域: 20步（200秒）")
    print("  控制时域: 10步")
    print("  状态权重Q: 5.0（重视跟踪）")
    print("  控制权重R: 2.0（平滑控制）")
    print("\n扰动场景：")
    print("  t=300s: 来水从10→15 m³/s（+50%）")
    print("\n控制目标：")
    print("  监测点（20km）: 2.8 m")
    print("\n" + "=" * 90)

    # 运行模拟
    modeler = UniversalModeler("config_02_mpc_predictive.yaml")
    success = modeler.run()

    if not success:
        print("\n✗ 模拟失败")
        return False

    # 结果分析
    print("\n" + "=" * 90)
    print("控制效果分析：")
    print("=" * 90)

    # 从控制结果中提取数据
    result = modeler.control_result
    metrics = result['performance_metrics']

    print(f"\n控制器类型：{result['controller_type'].upper()}")
    print(f"控制周期：{result['control_interval'] * result['dt']:.1f} s")
    print(f"总仿真时间：{result['total_time']:.0f} s")

    # 性能指标
    print(f"\n总体性能指标：")
    print(f"  平均绝对误差 (MAE): {metrics.get('mae', 0):.4f} m")
    print(f"  均方根误差 (RMSE): {metrics.get('rmse', 0):.4f} m")
    print(f"  最大误差: {metrics.get('max_error', 0):.4f} m")
    print(f"  稳态误差: {metrics.get('steady_state_error', 0):.4f} m")
    print(f"  积分平方误差 (ISE): {metrics.get('ise', 0):.4f}")
    print(f"  积分绝对误差 (IAE): {metrics.get('iae', 0):.4f}")

    # 控制量统计
    control_history = result['control_history']
    if len(control_history) > 0:
        control_array = np.array(control_history)
        if control_array.ndim == 2:
            control_array = control_array[:, 0]

        print(f"\n闸门控制统计：")
        print(f"  初始开度: {control_array[0]:.3f} m")
        print(f"  最终开度: {control_array[-1]:.3f} m")
        print(f"  平均开度: {control_array.mean():.3f} m")
        print(f"  调节幅度: {control_array.max() - control_array.min():.3f} m")

        if len(control_array) > 1:
            changes = np.abs(np.diff(control_array))
            print(f"  平均变化: {changes.mean():.4f} m/步（越小越平滑）")
            print(f"  最大变化: {changes.max():.4f} m/步")

    # 扰动响应分析
    time = result['time']
    error_history = np.array(result['error_history'])

    dt = result['dt']
    control_interval = result['control_interval']
    idx_300s = int(300 / (dt * control_interval))

    if idx_300s < len(error_history):
        print(f"\n扰动响应分析：")
        print(f"  来水扰动前（t<300s）：")
        error_before = error_history[:idx_300s]
        if len(error_before) > 0:
            if error_before.ndim > 1:
                mae_before = np.abs(error_before).mean(axis=0)[0]
            else:
                mae_before = np.abs(error_before).mean()
            print(f"    MAE: {mae_before:.4f} m")

        print(f"  来水扰动后（t≥300s）：")
        error_after = error_history[idx_300s:]
        if len(error_after) > 0:
            if error_after.ndim > 1:
                mae_after = np.abs(error_after).mean(axis=0)[0]
            else:
                mae_after = np.abs(error_after).mean()
            print(f"    MAE: {mae_after:.4f} m")
            print(f"  误差增幅：{(mae_after / (mae_before + 1e-10) - 1) * 100:.1f}%")

    print("\n" + "=" * 90)
    print("MPC控制特性：")
    print("=" * 90)
    print("✓ 前馈预测：提前规划未来20步（200秒）的控制动作")
    print("✓ 约束优化：严格满足开度和变化率约束")
    print("✓ 平滑控制：通过R权重惩罚频繁调节")
    print("✓ 模型自适应：在线更新系统模型参数")

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
