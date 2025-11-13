#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单配置文件仿真运行器

用于批量仿真工具调用

用法:
    python simulate.py config.json

作者: HydroClaude Team
日期: 2025-10-28
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.simulation_engine import SimulationEngine


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python simulate.py config.json", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]

    try:
        # 创建仿真引擎
        engine = SimulationEngine(config_file)

        # 初始化
        engine.initialize_steady_state()

        # 运行仿真
        engine.run()

        # 保存结果
        engine.save_results()

        # 成功
        sys.exit(0)

    except Exception as e:
        print(f"仿真失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
