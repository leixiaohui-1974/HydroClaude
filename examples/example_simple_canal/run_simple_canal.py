#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单明渠稳态流模拟 - 使用通用建模系统

这是最简单的示例，演示如何用3行代码完成完整建模流程。

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
    主函数 - 演示通用建模系统的最简用法
    """
    print("=" * 90)
    print("示例：简单明渠稳态流 - 自动化建模")
    print("=" * 90)

    # ========================================================================
    # 核心代码：仅需3行！
    # ========================================================================

    # 1. 创建建模器（自动加载配置）
    modeler = UniversalModeler("config_simple_canal.yaml")

    # 2. 运行完整建模流程（自动执行所有步骤）
    success = modeler.run()

    # 3. 输出结果路径
    if success:
        print(f"\n 建模成功！请查看结果目录: {modeler.output_dir}")
    else:
        print("\n 建模失败，请查看错误信息")

    # ========================================================================
    # 就这么简单！
    # ========================================================================

    return success


if __name__ == "__main__":
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 运行
    success = main()

    # 返回状态码
    sys.exit(0 if success else 1)
