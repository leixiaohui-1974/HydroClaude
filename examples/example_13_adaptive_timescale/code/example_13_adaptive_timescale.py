# -*- coding: utf-8 -*-
"""
示例13: 时间尺度自适应仿真
演示不同时间步长下自动选择合适的降阶模型
"""
import sys, os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from models.timescale_selector import AdaptiveCanalModel, TimeScaleSelector

def run_example():
    print("\n" + "="*70)
    print("示例13: 时间尺度自适应仿真")
    print("="*70)

    # 创建自适应明渠模型
    canal = AdaptiveCanalModel(
        length=5000.0,
        width=10.0,
        slope=0.0001,
        manning_n=0.025,
        nominal_depth=2.0
    )

    # 测试不同的时间步长
    test_cases = [
        (10.0, "10秒 - 高保真模型"),
        (120.0, "2分钟 - 传递函数模型"),
        (900.0, "15分钟 - IDZ模型"),
        (3600.0, "1小时 - 水量平衡模型")
    ]

    print("\n测试不同时间尺度的模型自动选择:")
    print("-" * 70)

    results = []

    for dt, description in test_cases:
        print(f"\n{description}:")
        print(f"  时间步长: {dt}s")

        # 推荐模型
        recommended = TimeScaleSelector.recommend_model(dt)
        print(f"  推荐模型: {recommended.value}")

        # 运行仿真
        n_steps = 10
        depths = []

        for i in range(n_steps):
            # 简单的入流和出流
            upstream_flow = 5.0 + 1.0 * np.sin(i * 0.1)
            downstream_flow = 5.0

            # 自适应更新
            state = canal.update(dt, upstream_flow, downstream_flow)
            depths.append(state['depth'])

            if i == 0:
                print(f"  实际使用模型: {state['model_type']}")

        print(f"  最终水深: {depths[-1]:.3f}m")
        print(f"  水深变化: {depths[-1] - depths[0]:.3f}m")

        results.append({
            'dt': dt,
            'description': description,
            'depths': depths,
            'model_type': state['model_type']
        })

    print("\n" + "="*70)
    print("时间尺度自适应仿真完成!")
    print(" 自动根据时间步长选择合适的降阶模型")
    print(" 从高保真模型到水量平衡模型无缝切换")

    # 可视化（如果有matplotlib）
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        axes = axes.flatten()

        for i, result in enumerate(results):
            ax = axes[i]
            time = np.arange(len(result['depths'])) * result['dt'] / 60  # 转换为分钟
            ax.plot(time, result['depths'], 'o-', linewidth=2, markersize=6)
            ax.set_xlabel('时间 (分钟)')
            ax.set_ylabel('水深 (m)')
            ax.set_title(f"{result['description']}\n模型: {result['model_type']}")
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('adaptive_timescale.png', dpi=150, bbox_inches='tight')
        print(f"\n图表已保存: adaptive_timescale.png")
    except Exception as e:
        print(f"\n可视化跳过: {e}")

if __name__ == "__main__":
    run_example()
