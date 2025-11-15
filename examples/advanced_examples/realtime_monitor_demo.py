# -*- coding: utf-8 -*-
"""
实时监控演示

展示如何使用实时监控工具进行渠道控制系统监控：
- 实时数据更新和显示
- 多变量动态监控
- 警报触发和清除
- 静态报告生成

模拟场景：
- 渠道水深控制
- 参考轨迹跟踪
- 扰动和警报

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.realtime_monitor import (
    RealtimeMonitor, StaticMonitorReport,
    MonitorVariable, AlarmConfig,
    create_canal_monitor, SimulationDataGenerator
)


def static_monitor_demo():
    """静态监控报告演示（事后分析）"""
    print("=" * 80)
    print("静态监控报告演示")
    print("=" * 80)

    # ===== 1. 参数设置 =====
    print("\n1. 参数设置...")

    dt = 1.0  # 采样时间
    n_steps = 300  # 仿真步数

    print(f"  采样时间: {dt} s")
    print(f"  仿真步数: {n_steps}")

    # ===== 2. 创建仿真器 =====
    print("\n2. 创建仿真器...")

    sim = SimulationDataGenerator(dt)

    print("   仿真数据生成器已创建")

    # ===== 3. 创建报告生成器 =====
    print("\n3. 创建报告生成器...")

    report = StaticMonitorReport()

    # 定义监控变量
    variables = [
        MonitorVariable('water_depth', 'm', 'Water Depth', color='blue'),
        MonitorVariable('flow_rate', 'm^3/s', 'Flow Rate', color='green'),
        MonitorVariable('control_input', 'm/s', 'Control Input', color='orange'),
        MonitorVariable('tracking_error', 'm', 'Tracking Error', color='red')
    ]

    # 定义警报
    alarms = [
        AlarmConfig('Low Water Level', 'water_depth', low_threshold=1.5),
        AlarmConfig('High Water Level', 'water_depth', high_threshold=3.5),
        AlarmConfig('High Tracking Error', 'tracking_error', high_threshold=0.5)
    ]

    print("   报告生成器已创建")
    print(f"  监控变量: {len(variables)}个")
    print(f"  警报配置: {len(alarms)}个")

    # ===== 4. 生成参考轨迹 =====
    print("\n4. 生成参考轨迹...")

    # 挑战性的参考轨迹
    reference_sequence = []
    for step in range(n_steps):
        if step < 80:
            r = 2.5
        elif step < 120:
            r = 3.3  # 接近上限（会触发警报）
        elif step < 180:
            r = 1.7  # 接近下限
        elif step < 240:
            r = 2.8
        else:
            r = 2.5

        reference_sequence.append(r)

    print("  场景设计：")
    print("    0-80步:   r = 2.5 m  (正常)")
    print("    80-120步: r = 3.3 m  (接近上限，触发警报)")
    print("    120-180步:r = 1.7 m  (接近下限)")
    print("    180-240步:r = 2.8 m  (正常)")
    print("    240-300步:r = 2.5 m  (正常)")

    # ===== 5. 运行仿真 =====
    print("\n5. 运行仿真...")

    alarm_count = 0
    alarm_active = False

    for step in range(n_steps):
        # 设置参考
        sim.set_reference(reference_sequence[step])

        # 仿真一步
        data = sim.step()

        # 记录数据
        report.add_data(sim.t, data)

        # 手动检查警报（用于统计）
        h = data['water_depth']
        if h > 3.5 or h < 1.5:
            if not alarm_active:
                alarm_count += 1
                alarm_active = True
                print(f"    步骤 {step}: 警报触发 (h={h:.3f}m)")
        else:
            if alarm_active:
                alarm_active = False
                print(f"    步骤 {step}: 警报清除 (h={h:.3f}m)")

        if step % 60 == 0:
            print(f"  进度: {step}/{n_steps} - "
                  f"h={h:.3f}m, "
                  f"q={data['flow_rate']:.2f}m^3/s, "
                  f"u={data['control_input']:.4f}m/s")

    print(f"\n  仿真完成! 总警报次数: {alarm_count}")

    # ===== 6. 生成报告 =====
    print("\n6. 生成监控报告...")

    output_path = os.path.join(os.path.dirname(__file__), 'realtime_monitor_report.png')
    report.generate_report(variables, alarms, output_path)

    print("\n   报告生成完成!")

    # ===== 7. 统计分析 =====
    print("\n7. 统计分析...")

    h_data = np.array(report.data_history['water_depth'])
    q_data = np.array(report.data_history['flow_rate'])
    u_data = np.array(report.data_history['control_input'])
    e_data = np.array(report.data_history['tracking_error'])

    print(f"\n  水深统计:")
    print(f"    平均值: {np.mean(h_data):.3f} m")
    print(f"    最小值: {np.min(h_data):.3f} m")
    print(f"    最大值: {np.max(h_data):.3f} m")
    print(f"    标准差: {np.std(h_data):.3f} m")

    print(f"\n  流量统计:")
    print(f"    平均值: {np.mean(q_data):.2f} m^3/s")
    print(f"    最小值: {np.min(q_data):.2f} m^3/s")
    print(f"    最大值: {np.max(q_data):.2f} m^3/s")

    print(f"\n  控制输入统计:")
    print(f"    平均值: {np.mean(u_data):.4f} m/s")
    print(f"    最大值: {np.max(np.abs(u_data)):.4f} m/s")
    print(f"    变化率: {np.sum(np.abs(np.diff(u_data))):.3f}")

    print(f"\n  跟踪误差统计:")
    print(f"    MAE: {np.mean(np.abs(e_data)):.4f} m")
    print(f"    RMSE: {np.sqrt(np.mean(e_data**2)):.4f} m")
    print(f"    最大误差: {np.max(np.abs(e_data)):.4f} m")

    # ===== 8. 总结 =====
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print(f"\n监控报告已生成，包含:")
    print(f"  - {len(variables)}个监控变量的时间序列")
    print(f"  - {len(alarms)}个警报阈值标注")
    print(f"  - 完整的统计信息")
    print(f"  - 警报事件记录（{alarm_count}次）")
    print(f"\n报告文件: {output_path}")
    print("\n" + "=" * 80)


def interactive_monitor_demo():
    """交互式实时监控演示

    注意：这个演示需要手动运行，因为它会打开交互式matplotlib窗口
    """
    print("\n" + "=" * 80)
    print("交互式实时监控演示（需要GUI支持）")
    print("=" * 80)
    print("\n说明: 此演示需要matplotlib的交互式后端")
    print("如果在无GUI环境中运行，请跳过此演示\n")

    response = "y"  # input() disabled for automated testing
    if response.lower() != 'y':
        print("已跳过交互式演示")
        return

    # 创建监控器
    monitor = create_canal_monitor(window_size=100)

    # 创建仪表盘
    monitor.create_dashboard(n_rows=2, n_cols=2)

    # 设置子图
    monitor.setup_plot(0, ['water_depth'], 'Water Depth', 'Depth (m)',
                      y_limits=(1.0, 4.0))
    monitor.setup_plot(1, ['flow_rate'], 'Flow Rate', 'Flow (m^3/s)')
    monitor.setup_plot(2, ['control_input'], 'Control Input', 'Input (m/s)')
    monitor.setup_plot(3, ['tracking_error'], 'Tracking Error', 'Error (m)')

    # 创建数据生成器
    sim = SimulationDataGenerator(dt=0.1)

    # 模拟数据更新函数
    def update_simulation():
        """更新仿真并向监控器推送数据"""
        # 动态改变参考值
        t = sim.t
        if t < 20:
            sim.set_reference(2.5)
        elif t < 40:
            sim.set_reference(3.2)
        elif t < 60:
            sim.set_reference(1.8)
        else:
            sim.set_reference(2.5)

        # 生成数据
        data = sim.step()

        # 更新监控器
        monitor.update_data(sim.t, data)

    # 定期更新（在动画中）
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.use('Agg')
    from matplotlib.animation import FuncAnimation

    def animation_update(frame):
        update_simulation()
        return monitor.update_plot(frame)

    anim = FuncAnimation(monitor.fig, animation_update,
                        interval=100, blit=True)

    print("\n启动实时监控...")
    print("关闭窗口以停止监控")

    # plt.show()  # Disabled for automated testing


def main():
    """主函数"""
    print("=" * 80)
    print("实时监控工具演示")
    print("=" * 80)

    # 运行静态监控演示
    static_monitor_demo()

    # 询问是否运行交互式演示
    # interactive_monitor_demo()


if __name__ == '__main__':
    main()
