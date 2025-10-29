#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 配置驱动仿真工具

一站式命令行工具，通过JSON配置文件运行水力学仿真

用法:
    python simulate.py config.json

示例:
    # 运行溃坝模拟
    python simulate.py examples/config_driven/dam_break.json

    # 运行均匀流验证
    python simulate.py examples/config_driven/uniform_flow.json

作者: HydroClaude Team
日期: 2025-10-28
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from engine.simulation_engine import SimulationEngine


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    config_file = sys.argv[1]

    if not Path(config_file).exists():
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)

    try:
        # 创建并运行仿真引擎
        engine = SimulationEngine(config_file)
        engine.initialize()
        engine.run()
        engine.save_results()
        engine.validate()

        print("\n" + "="*80)
        print("✅ 仿真完成！")
        print("="*80)

    except KeyboardInterrupt:
        print("\n\n⚠️  仿真被用户中断")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ 仿真失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
