#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
明渠串联闸泵群系统 - 自动化建模示例

演示通用建模系统的完整功能：
- 自动网格生成（结构物附近自适应加密）
- 自动算法选择
- 自动稳态求解
- 自动多重验证
- 自动生成报告和图表

作者: Claude
日期: 2025-10-24
"""

import sys
import os
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def main():
    """
    主函数 - 自动化建模流程
    """
    print("=" * 90)
    print("示例：明渠串联闸泵群系统 - 自动化建模")
    print("=" * 90)
    print("\n本示例演示：")
    print("  1. 从YAML配置文件自动读取所有参数")
    print("  2. 自动生成网格（结构物附近自适应加密）")
    print("  3. 自动选择最优数值算法")
    print("  4. 自动执行稳态求解")
    print("  5. 自动进行多重验证")
    print("  6. 自动生成结果和报告")
    print("\n" + "=" * 90)

    # ========================================================================
    # 方法1：最简方式（一键运行）
    # ========================================================================
    print("\n【方法1】一键自动化建模：")
    print("-" * 90)

    modeler = UniversalModeler("config_gate_pump_auto.yaml")
    success = modeler.run()

    if not success:
        print("\n✗ 建模失败")
        return False

    # ========================================================================
    # 方法2：分步运行（可在每步后插入自定义分析）
    # ========================================================================
    print("\n\n【方法2】分步建模（高级用法）：")
    print("-" * 90)

    # 创建新的建模器
    modeler2 = UniversalModeler("config_gate_pump_auto.yaml")

    # 步骤1：设置结构物
    modeler2.setup_structures()

    # 步骤2：生成网格
    x = modeler2.setup_grid()
    print(f"\n  >> 网格信息：{len(x)}个点，间距范围 [{np.min(np.diff(x)):.1f}, {np.max(np.diff(x)):.1f}] m")

    # 步骤3：初始化求解器
    solver = modeler2.setup_solver(x)
    print(f"  >> 求解器已初始化")

    # 步骤4：选择算法
    recommendation = modeler2.select_algorithm()
    print(f"  >> 推荐算法：{recommendation['method']}")

    # 步骤5：运行稳态模拟
    result = modeler2.run_steady_simulation()
    print(f"  >> 稳态求解：{'成功' if result['converged'] else '未完全收敛'}")

    # 步骤6：验证结果
    validation = modeler2.validate_results()

    # 步骤7：生成输出
    modeler2.generate_outputs()

    # ========================================================================
    # 结果分析（示例）
    # ========================================================================
    print("\n" + "=" * 90)
    print("关键结果摘要：")
    print("=" * 90)

    # 提取泵站信息并验证扬程效果
    pump_structure = None
    pump_position = None

    # 从配置文件查找泵站
    structures_config = modeler.config.config.get('structures', [])
    for struct_cfg in structures_config:
        if struct_cfg.get('type') == 'pump_station':
            pump_structure = struct_cfg
            pump_position = struct_cfg['position']
            break

    if pump_structure and pump_position:
        # 找到泵站在网格上的索引
        pump_idx = np.argmin(np.abs(modeler.solver.x - pump_position))

        # 定义检查距离（10km）
        check_distance = 10000.0  # 10 km

        # 找到上下游检查点
        x = modeler.solver.x
        h = modeler.solver.h

        # 上游检查点：泵站前10km
        upstream_target_x = pump_position - check_distance
        upstream_idx = np.argmin(np.abs(x - upstream_target_x))

        # 下游检查点：泵站后10km
        downstream_target_x = pump_position + check_distance
        downstream_idx = np.argmin(np.abs(x - downstream_target_x))

        h_upstream = h[upstream_idx]
        h_downstream = h[downstream_idx]
        rated_head = pump_structure['rated_head']

        print(f"\n泵站扬程效果验证：")
        print(f"  泵站位置: {pump_position/1000:.1f} km")
        print(f"  上游水深（-{check_distance/1000:.0f}km）: {h_upstream:.4f} m")
        print(f"  下游水深（+{check_distance/1000:.0f}km）: {h_downstream:.4f} m")
        print(f"  实际扬程效果: {h_downstream - h_upstream:.4f} m")
        print(f"  额定扬程: {rated_head:.3f} m")
        print(f"  精度: {(h_downstream - h_upstream) / rated_head * 100:.1f}%")

    print("\n" + "=" * 90)
    print(f"✓ 建模完成！")
    print(f"  结果目录: {modeler.output_dir}")
    print(f"  验证报告: {modeler.output_dir}/validation_report.txt")
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
