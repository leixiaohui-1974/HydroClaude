#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时变边界条件示例 - 正弦波动流量

演示如何模拟时变的上游流量

作者: Claude
日期: 2025-10-24
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def main():
    """
    主函数 - 时变边界条件示例
    """
    print("=" * 90)
    print("示例时变边界条件 - 正弦波动流量")
    print("=" * 90)
    print("\n本示例演示")
    print("  1. 上游流量按正弦规律变化")
    print("  2. Q(t) = 10 + 3sin(2pit/600)")
    print("  3. 流量范围7 ~ 13 m^3/s")
    print("  4. 变化周期10分钟")
    print("\n" + "=" * 90)

    # 运行模拟
    modeler = UniversalModeler("config_time_varying_bc.yaml")
    success = modeler.run()

    if not success:
        print("\n 模拟失败")
        return False

    # 结果分析
    print("\n" + "=" * 90)
    print("结果分析")
    print("=" * 90)

    result = modeler.unsteady_result

    # 提取中点位置的水深时间历史
    nx = len(modeler.solver.x)
    mid_idx = nx // 2
    h_mid = result['h_history'][:, mid_idx]
    time = result['time']

    print(f"\n中点位置x={modeler.solver.x[mid_idx]/1000:.1f}km水深变化")
    print(f"  最小值: {np.min(h_mid):.4f} m")
    print(f"  最大值: {np.max(h_mid):.4f} m")
    print(f"  变化幅度: {np.max(h_mid) - np.min(h_mid):.4f} m")

    # 绘制边界条件时间历史
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # 子图1流量时间历史
    Q_bc = 10.0 + 3.0 * np.sin(2 * np.pi * time / 600.0)
    ax1.plot(time, Q_bc, 'b-', linewidth=2, label='Upstream Flow')
    ax1.set_xlabel('Time (s)', fontsize=12)
    ax1.set_ylabel('Flow Rate (m^3/s)', fontsize=12)
    ax1.set_title('Time-Varying Upstream Boundary Condition', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)

    # 子图2中点水深响应
    ax2.plot(time, h_mid, 'r-', linewidth=2, label=f'Water Depth at x={modeler.solver.x[mid_idx]/1000:.1f}km')
    ax2.set_xlabel('Time (s)', fontsize=12)
    ax2.set_ylabel('Water Depth (m)', fontsize=12)
    ax2.set_title('Water Depth Response at Mid-Point', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)

    plt.tight_layout()
    output_file = modeler.output_dir / "bc_and_response.png"
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n 边界条件和响应图已保存: {output_file}")
    plt.close()

    print("\n" + "=" * 90)
    print(f" 模拟完成")
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
