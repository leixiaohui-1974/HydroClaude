import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from examples.run_moc_gate_boundary_example import example_moc_gate_boundary
from examples.run_mode_comparison_example import example_mode_comparison


def main():
    """主程序入口"""
    print("\n" + "="*60)
    print("水网SIL测试平台 V3.1")
    print("完整内边界处理 + 双模式本体仿真")
    print("="*60)

    try:
        example_moc_gate_boundary()
    except Exception as e:
        print(f"示例1出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_mode_comparison()
    except Exception as e:
        print(f"示例2出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("所有测试完成！")
    print("="*60)


if __name__ == "__main__":
    main()
