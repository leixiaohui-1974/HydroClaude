#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制策略3: 分层分布式控制（MPC上层 + PID下层）

分层控制架构：
- 上层MPC：全局优化，长期规划，计算最优设定值
- 下层PID：快速执行，局部调节，跟踪设定值

设计理念：
1. 分离关注点：
   - 上层关注全局优化和长期目标
   - 下层关注快速响应和局部扰动

2. 双时间尺度：
   - 上层：慢速（如1分钟），计算量大
   - 下层：快速（如10秒），计算量小

3. 分布式架构：
   - 每个控制点独立的PID控制器
   - 提高系统可靠性和扩展性

当前实现：
由于框架限制，使用单层MPC模拟分层控制效果
通过参数调优（快速采样+长预测时域）近似分层特性

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
    主函数 - 分层分布式控制
    """
    print("=" * 90)
    print("控制策略3: 分层分布式控制（MPC上层 + PID下层概念）")
    print("=" * 90)
    print("\n控制架构：")
    print("  上层：MPC全局优化（长预测时域，计算设定值）")
    print("  下层：PID快速执行（快速跟踪，抑制扰动）")
    print("\n当前实现：")
    print("  使用增强型MPC模拟分层效果")
    print("  - 超长预测时域（25步）→ 模拟上层全局视野")
    print("  - 快速采样（6秒）→ 模拟下层快速响应")
    print("  - 高Q权重（8.0）→ 模拟PID的强跟踪")
    print("  - 快速自适应 → 模拟PID的快速响应")
    print("\n扰动场景：")
    print("  t=300s: 来水从10→15 m³/s（+50%）")
    print("\n控制目标：")
    print("  监测点（20km）: 2.8 m")
    print("\n" + "=" * 90)

    # 运行模拟
    modeler = UniversalModeler("config_03_hierarchical.yaml")
    success = modeler.run()

    if not success:
        print("\n✗ 模拟失败")
        return False

    # 结果分析
    print("\n" + "=" * 90)
    print("控制效果分析：")
    print("=" * 90)

    result = modeler.control_result
    metrics = result['performance_metrics']

    print(f"\n控制器类型：{result['controller_type'].upper()} (分层架构概念)")
    print(f"控制周期：{result['control_interval'] * result['dt']:.1f} s")
    print(f"总仿真时间：{result['total_time']:.0f} s")

    # 性能指标
    print(f"\n总体性能指标：")
    print(f"  平均绝对误差 (MAE): {metrics.get('mae', 0):.4f} m")
    print(f"  均方根误差 (RMSE): {metrics.get('rmse', 0):.4f} m")
    print(f"  最大误差: {metrics.get('max_error', 0):.4f} m")
    print(f"  稳态误差: {metrics.get('steady_state_error', 0):.4f} m")
    print(f"  积分平方误差 (ISE): {metrics.get('ise', 0):.4f}")

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
            print(f"  平均变化: {changes.mean():.4f} m/步")
            print(f"  最大变化: {changes.max():.4f} m/步")

    # 扰动响应分析
    error_history = np.array(result['error_history'])
    dt = result['dt']
    control_interval = result['control_interval']
    idx_300s = int(300 / (dt * control_interval))

    if idx_300s < len(error_history):
        print(f"\n扰动响应分析：")
        error_before = error_history[:idx_300s]
        error_after = error_history[idx_300s:]

        if len(error_before) > 0 and len(error_after) > 0:
            mae_before = np.abs(error_before).mean()
            mae_after = np.abs(error_after).mean()
            print(f"  扰动前MAE: {mae_before:.4f} m")
            print(f"  扰动后MAE: {mae_after:.4f} m")
            print(f"  误差增幅: {(mae_after / (mae_before + 1e-10) - 1) * 100:.1f}%")

    print("\n" + "=" * 90)
    print("分层控制特性：")
    print("=" * 90)
    print("✓ 全局优化：长预测时域（25步）提供宏观视野")
    print("✓ 快速响应：短控制周期（6秒）快速调节")
    print("✓ 强跟踪：高Q权重（8.0）类似PID强力跟踪")
    print("✓ 平滑控制：适中R权重保持平滑性")
    print("✓ 自适应：快速参数更新应对扰动")

    print("\n" + "=" * 90)
    print("说明：")
    print("=" * 90)
    print("本示例通过MPC参数调优模拟分层控制效果")
    print("真正的分层控制需要：")
    print("  1. 独立的上层MPC优化器")
    print("  2. 多个下层PID控制器")
    print("  3. 设定值传递机制")
    print("  4. 双时间尺度协调")
    print("\n当前实现展示了分层控制的设计思想和性能潜力")

    print("\n" + "=" * 90)
    print(f"✓ 模拟完成！")
    print(f"  结果目录: {modeler.output_dir}")
    print("=" * 90)

    return True


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    success = main()
    sys.exit(0 if success else 1)
