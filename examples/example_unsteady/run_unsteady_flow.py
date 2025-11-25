#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
非稳态流动模拟示例

演示通用建模系统的非稳态模拟功能

作者: Claude
日期: 2025-10-24
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def main():
    """
    主函数 - 非稳态模拟示例
    """
    print("=" * 90)
    print("示例：非稳态流动模拟")
    print("=" * 90)
    print("\n本示例演示：")
    print("  1. 从稳态初值开始")
    print("  2. 时间步进求解（Preissmann隐式格式）")
    print("  3. 自动保存时间历史")
    print("  4. 生成时间序列图和最终状态图")
    print("\n" + "=" * 90)

    # ========================================================================
    # 一键运行非稳态模拟
    # ========================================================================
    print("\n运行非稳态模拟：")
    print("-" * 90)

    modeler = UniversalModeler("config_unsteady_flow.yaml")
    success = modeler.run()

    if not success:
        print("\n 模拟失败")
        return False

    # ========================================================================
    # 结果分析
    # ========================================================================
    print("\n" + "=" * 90)
    print("结果分析：")
    print("=" * 90)

    # 提取结果
    result = modeler.unsteady_result
    print(f"\n时间模拟信息：")
    print(f"  时间步数: {result['n_steps']}")
    print(f"  时间步长: {result['dt']} s")
    print(f"  总时间: {result['total_time']} s")
    print(f"  保存点数: {len(result['time'])}")

    # 水深统计
    h_final = result['h_history'][-1, :]
    print(f"\n最终时刻水深统计：")
    print(f"  最小值: {np.min(h_final):.4f} m")
    print(f"  最大值: {np.max(h_final):.4f} m")
    print(f"  平均值: {np.mean(h_final):.4f} m")

    # 检查是否达到稳态
    if len(result['time']) > 1:
        h_change = np.abs(result['h_history'][-1, :] - result['h_history'][-2, :])
        max_change = np.max(h_change)
        print(f"\n稳定性检查：")
        print(f"  最后两个时间步的最大水深变化: {max_change:.6f} m")
        if max_change < 0.001:
            print(f"  状态:  已基本达到稳态")
        else:
            print(f"  状态: >> 仍在演化中")

    print("\n" + "=" * 90)
    print(f" 模拟完成！")
    print(f"  结果目录: {modeler.output_dir}")
    print(f"  数据文件: {modeler.output_dir}/unsteady_flow_data.npz")
    print(f"  时间序列图: {modeler.output_dir}/unsteady_flow_time_series.png")
    print(f"  最终状态图: {modeler.output_dir}/unsteady_flow_final_profile.png")
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
