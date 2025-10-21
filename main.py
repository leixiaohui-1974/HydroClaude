# ==============================================================================
# 水网分层预测控制系统 - 主运行文件
# Water Network Hierarchical Predictive Control System - Main Runner
#
# V3.0 - 软件在环(SIL)测试平台 & 完整框架
# ==============================================================================

import matplotlib.pyplot as plt
import os
import sys

# Add the project root directory to the Python path to ensure modules are found
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import examples from the 'examples' directory
from examples.runner import run_framework_example
from examples.example_preissmann_vs_fvm import example_preissmann_vs_fvm
from examples.example_pipe_rk4 import example_pipe_rk4
from examples.sil_runner import example_sil_basic_test, example_sil_fault_test


def main():
    """
    主函数，用于运行所有示例和测试。
    """
    print("="*80)
    print("开始运行水网控制系统仿真与测试套件")
    print("="*80)

    # --- 设置 ---
    # 为matplotlib设置中文字体，以正确显示图表标签
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        print("✓ 中文字体 'SimHei' 加载成功。")
    except Exception as e:
        print(f"⚠️ 警告: 未找到中文字体 'SimHei'。图表标签可能无法正确显示。错误: {e}")
        print("   请安装 'SimHei' 字体或修改代码以使用您系统上可用的中文字体。")

    # --- 运行示例 ---

    # 1. 运行 V2.1 框架示例
    try:
        run_framework_example()
    except Exception as e:
        print(f"\n❌ V2.1 框架示例运行出错: {e}")
        import traceback
        traceback.print_exc()

    # 2. 运行 V3.0 SIL 基础测试
    try:
        example_sil_basic_test()
    except Exception as e:
        print(f"\n❌ V3.0 SIL 基础测试运行出错: {e}")
        import traceback
        traceback.print_exc()

    # 3. 运行 V3.0 SIL 故障注入测试
    try:
        example_sil_fault_test()
    except Exception as e:
        print(f"\n❌ V3.0 SIL 故障测试运行出错: {e}")
        import traceback
        traceback.print_exc()

    # 4. 运行 V3.2 高精度数值方法对比: Preissmann vs FVM
    try:
        example_preissmann_vs_fvm()
    except Exception as e:
        print(f"\n❌ 高精度方法对比 (Preissmann vs FVM) 运行出错: {e}")
        import traceback
        traceback.print_exc()

    # 5. 运行 V3.2 高精度管道水击仿真
    try:
        example_pipe_rk4()
    except Exception as e:
        print(f"\n❌ 高精度管道水击仿真 (RK4) 运行出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("所有测试运行完成！")
    print("="*80)
    print("\n生成的文件:")
    files = [f for f in os.listdir('.') if f.endswith('.png')]
    if files:
        for f in files:
            print(f"- {f}")
    else:
        print("- 未生成图表文件。")

main()
