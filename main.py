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

    print("\n系统演示完成!")

if __name__ == "__main__":
    main()
