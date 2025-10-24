#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件边界条件示例

展示如何从CSV文件读取时间序列边界条件

运行: python run.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def main():
    """主函数"""
    print("=" * 90)
    print("文件边界条件示例")
    print("=" * 90)
    print()
    print("本示例展示:")
    print("  1. 从CSV文件读取时间序列边界条件")
    print("  2. 线性插值实现平滑边界变化")
    print("  3. 支持多列数据（flow、depth等）")
    print()

    # 创建建模器
    config_file = os.path.join(os.path.dirname(__file__), "config.yaml")
    modeler = UniversalModeler(config_file)

    # 运行模拟
    modeler.run()

    print()
    print("=" * 90)
    print("模拟完成！")
    print("=" * 90)
    print()
    print("结果文件:")
    print(f"  - results/profile.png       - 水面线剖面图")
    print(f"  - results/time_series.png   - 时间序列图")
    print()


if __name__ == "__main__":
    main()
