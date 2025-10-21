from examples.runner import example_1_simple_canal, example_2_pump_characteristics, example_3_complex_network_with_pumps

if __name__ == "__main__":
    print("\n" + "="*60)
    print("通用水网分层预测控制系统框架 V2.1")
    print("Universal Water Network HPC Framework")
    print("="*60)
    print("\n功能特性:")
    print("✓ 完整高保真物理模型（Saint-Venant、水击方程）")
    print("✓ 支持整个水网的降阶模型仿真")
    print("✓ 泵站完整特性曲线（H-Q-η-P）")
    print("✓ 闸阀水力学方程（堰流/孔流）")
    print("✓ 模型验证和对比分析")
    print("✓ 灵活的仿真模式切换")

    # 运行示例
    try:
        example_1_simple_canal()
    except Exception as e:
        print(f"示例1出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_2_pump_characteristics()
    except Exception as e:
        print(f"示例2出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_3_complex_network_with_pumps()
    except Exception as e:
        print(f"示例3出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("所有示例运行完成！")
    print("="*60)
