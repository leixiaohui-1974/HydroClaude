#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构类型展示案例

展示UniversalModeler对所有7种水工结构类型的支持：
1. SluiceGate - 闸门
2. Transition - 过渡段
3. BroadCrestedWeir - 宽顶堰
4. Drop - 跌水
5. Spillway - 溢洪道
6. Orifice - 孔口
7. PumpStation - 泵站

运行示例：
    python run.py

或直接使用通用建模器：
    python -m modeling.universal_modeler config.yaml
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def print_structure_info(modeler):
    """打印结构物详细信息"""
    print()
    print("=" * 80)
    print("结构物详细信息")
    print("=" * 80)
    print()

    if not modeler.structures:
        print("  无结构物")
        return

    for i, (pos, struct) in enumerate(modeler.structures, 1):
        print(f"{i}. {struct.__class__.__name__} @ {pos/1000:.1f} km")

        # 根据类型打印特定参数
        struct_type = struct.__class__.__name__

        if struct_type == 'SluiceGate':
            opening = struct.opening if isinstance(struct.opening, (int, float)) else "time-varying"
            print(f"   - 开度: {opening} m")
            print(f"   - 流量系数: {struct.Cd}")

        elif struct_type == 'Transition':
            print(f"   - 长度: {struct.length} m")
            print(f"   - 上游宽度: {struct.width_upstream} m")
            print(f"   - 下游宽度: {struct.width_downstream} m")
            print(f"   - 损失系数: {struct.loss_coefficient}")

        elif struct_type == 'BroadCrestedWeir':
            print(f"   - 堰顶高程: {struct.crest_height} m")
            print(f"   - 流量系数: {struct.Cd}")

        elif struct_type == 'Drop':
            print(f"   - 跌水高度: {struct.drop_height} m")
            print(f"   - 流量系数: {struct.Cd}")

        elif struct_type == 'Spillway':
            print(f"   - 堰顶高程: {struct.crest_elevation} m")
            print(f"   - 设计水头: {struct.design_head} m")
            print(f"   - 流量系数: {struct.Cd}")

        elif struct_type == 'Orifice':
            print(f"   - 孔口高度: {struct.height} m")
            print(f"   - 底高程: {struct.invert_elevation} m")
            print(f"   - 流量系数: {struct.Cd}")

        elif struct_type == 'PumpStation':
            print(f"   - 额定流量: {struct.rated_flow} m^3/s")
            print(f"   - 额定扬程: {struct.rated_head} m")
            print(f"   - 效率: {struct.efficiency*100:.1f}%")

        print()


def print_hydraulic_analysis(modeler):
    """打印水力学分析结果"""
    if not hasattr(modeler, 'steady_result') or modeler.steady_result is None:
        return

    result = modeler.steady_result
    solver = modeler.solver

    print()
    print("=" * 80)
    print("水力学分析结果")
    print("=" * 80)
    print()

    # 整体流量
    print(f"流量分析:")
    print(f"  平均流量: {result['Q_mean']:.3f} m^3/s")
    # Q_std可能不存在，安全访问
    if 'Q_std' in result:
        print(f"  流量标准差: {result['Q_std']:.6f} m^3/s")
    elif 'Q' in result:
        import numpy as np
        Q_std = np.std(result['Q'])
        print(f"  流量标准差: {Q_std:.6f} m^3/s")
    print(f"  流量误差: {result['Q_error_percent']:.6f}%")
    print()

    # 水深范围
    print(f"水深分析:")
    if 'h_min' in result and 'h_max' in result:
        print(f"  最小水深: {result['h_min']:.3f} m")
        print(f"  最大水深: {result['h_max']:.3f} m")
        print(f"  水深范围: {result['h_max'] - result['h_min']:.3f} m")
    elif 'h' in result:
        import numpy as np
        h_min = np.min(result['h'])
        h_max = np.max(result['h'])
        print(f"  最小水深: {h_min:.3f} m")
        print(f"  最大水深: {h_max:.3f} m")
        print(f"  水深范围: {h_max - h_min:.3f} m")
    print()

    # 各结构物处流态
    if modeler.structures:
        print(f"各结构物流态:")
        import numpy as np

        for i, (pos, struct) in enumerate(modeler.structures):
            # 找到最近的网格点
            idx = np.argmin(np.abs(solver.x - pos))
            h_local = solver.h[idx]
            q_local = solver.hu[idx] * solver.B  # 转换为流量
            v_local = q_local / (solver.B * h_local)
            Fr = v_local / np.sqrt(solver.g * h_local)

            struct_name = struct.__class__.__name__
            print(f"  {i+1}. {struct_name} @ {pos/1000:.1f} km")
            print(f"     水深: {h_local:.3f} m, 流速: {v_local:.3f} m/s, Fr: {Fr:.3f}")


def main():
    """运行结构类型展示案例"""

    # 配置文件路径
    config_file = Path(__file__).parent / "config.yaml"

    print("=" * 80)
    print("结构类型展示案例")
    print("=" * 80)
    print()
    print("本案例展示UniversalModeler对所有7种水工结构类型的支持：")
    print()
    print("  1. SluiceGate     - 闸门（进水控制）")
    print("  2. Transition     - 过渡段（渠道收缩）")
    print("  3. BroadCrestedWeir - 宽顶堰（水位调节）")
    print("  4. Drop           - 跌水（消能）")
    print("  5. Spillway       - 溢洪道（泄洪）")
    print("  6. Orifice        - 孔口（出水）")
    print("  7. PumpStation    - 泵站（提水）")
    print()
    print("工程场景：综合水利枢纽工程（15 km输水线路）")
    print()
    print("-" * 80)

    # 创建建模器
    modeler = UniversalModeler(str(config_file))

    # 打印结构物信息
    print_structure_info(modeler)

    # 运行仿真
    print("=" * 80)
    print("开始稳态仿真...")
    print("=" * 80)
    print()

    result = modeler.run()

    # 打印水力学分析
    print_hydraulic_analysis(modeler)

    # 输出文件位置
    output_dir = modeler.config.get_output_config()['directory']
    print()
    print("=" * 80)
    print(f"结果已保存到: {output_dir}/")
    print("=" * 80)
    print()

    return result


if __name__ == "__main__":
    main()
