def main():
    print("="*60)
    print("水网分层预测控制与SIL测试系统")
    print("="*60)

    # 导入示例
    try:
        from examples.example_01_simple_canal import run_example as example1
        print("\n运行示例1: 简单明渠系统")
        example1()
    except ImportError as e:
        print(f"导入示例1失败: {e}")

    try:
        from examples.example_08_preissmann_vs_fvm import example_preissmann_vs_fvm as example8
        print("\n运行示例8: Preissmann vs FVM")
        example8()
    except ImportError as e:
        print(f"导入示例8失败: {e}")

    try:
        from examples.example_09_pipe_rk4 import example_pipe_rk4 as example9
        print("\n运行示例9: Pipe RK4")
        example9()
    except ImportError as e:
        print(f"导入示例9失败: {e}")

    print("\n系统演示完成!")

if __name__ == "__main__":
    main()
