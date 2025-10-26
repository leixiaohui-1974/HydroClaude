#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
泵站扬程精度分析脚本

根据高精度算法v3.0的验证方法，正确分析泵站扬程效果。

关键：
- 上游参考点：泵站上游3km处（远离过渡区）
- 下游测量点：泵站下游2km处（平台区中心）
- 实际扬程 = 下游水深 - 上游水深

作者: Claude
日期: 2025-10-24
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def analyze_pump_head_precision():
    """
    分析泵站扬程精度
    """
    print("=" * 90)
    print("泵站扬程精度分析")
    print("=" * 90)

    # 加载数据
    data_file = "results_gate_pump_auto/gate_pump_auto_data.npz"

    if not os.path.exists(data_file):
        print(f"\n✗ 数据文件不存在: {data_file}")
        print("  请先运行 run_gate_pump_auto.py")
        return False

    data = np.load(data_file)
    x = data['x']
    h = data['h']

    print(f"\n✓ 数据已加载")
    print(f"  网格点数: {len(x)}")
    print(f"  渠道长度: {x[-1]/1000:.1f} km")

    # 泵站配置
    pump_position = 50000.0  # 50 km
    rated_head = 5.0  # m

    # 根据v3.0高精度算法的验证方法：
    # - 上游参考点：泵站上游3km（远离过渡区，代表真实上游水深）
    # - 下游测量点：泵站下游1km（平台区中心，保持100%扬程）
    # 注意：平台区范围是+0到+2km，中心在+1km

    upstream_ref_distance = -3000.0  # -3 km
    downstream_measure_distance = 1000.0  # +1 km (平台区中心)

    # 找到测量点索引
    upstream_x = pump_position + upstream_ref_distance
    downstream_x = pump_position + downstream_measure_distance

    idx_upstream = np.argmin(np.abs(x - upstream_x))
    idx_downstream = np.argmin(np.abs(x - downstream_x))
    idx_pump = np.argmin(np.abs(x - pump_position))

    # 读取水深
    h_upstream = h[idx_upstream]
    h_downstream = h[idx_downstream]
    h_pump = h[idx_pump]

    # 计算扬程
    actual_head = h_downstream - h_upstream
    head_error_abs = actual_head - rated_head
    head_error_percent = (head_error_abs / rated_head) * 100
    head_accuracy = (actual_head / rated_head) * 100

    # 精度分级
    if abs(head_error_percent) < 0.1:
        grade = "PERFECT (完美)"
        grade_emoji = "🏆"
    elif abs(head_error_percent) < 2.0:
        grade = "EXCELLENT (优秀)"
        grade_emoji = "⭐"
    elif abs(head_error_percent) < 5.0:
        grade = "GOOD (良好)"
        grade_emoji = "✓"
    elif abs(head_error_percent) < 10.0:
        grade = "ACCEPTABLE (可接受)"
        grade_emoji = "○"
    else:
        grade = "POOR (差)"
        grade_emoji = "✗"

    print("\n" + "=" * 90)
    print("扬程精度验证结果（v3.0方法）")
    print("=" * 90)

    print(f"\n【测量点位置】")
    print(f"  泵站位置: {pump_position/1000:.1f} km")
    print(f"  上游参考点: {upstream_x/1000:.1f} km (泵站上游3km)")
    print(f"  下游测量点: {downstream_x/1000:.1f} km (泵站下游1km, 平台区中心)")

    print(f"\n【水深分布】")
    print(f"  上游参考水深: {h_upstream:.4f} m")
    print(f"  泵站处水深:   {h_pump:.4f} m")
    print(f"  下游平台水深: {h_downstream:.4f} m")

    print(f"\n【扬程分析】")
    print(f"  额定扬程:     {rated_head:.3f} m")
    print(f"  实际扬程:     {actual_head:.4f} m")
    print(f"  绝对误差:     {head_error_abs:+.4f} m")
    print(f"  相对误差:     {head_error_percent:+.2f}%")
    print(f"  扬程准确度:   {head_accuracy:.2f}%")

    print(f"\n【精度评级】")
    print(f"  {grade_emoji} {grade}")

    # 详细纵向分析
    print(f"\n【纵向水深分析】")
    print(f"  {'位置(km)':<12} {'距泵站(km)':<12} {'水深(m)':<10} {'说明'}")
    print("-" * 90)

    # 上游区域
    for dist_km in [-5, -3, -2, -1]:
        dist_m = dist_km * 1000
        idx = np.argmin(np.abs(x - (pump_position + dist_m)))
        print(f"  {x[idx]/1000:<12.1f} {dist_km:<12.1f} {h[idx]:<10.4f} "
              f"{'上游参考点 ⭐' if dist_km == -3 else '上游正常流动' if dist_km <= -5 else '上游过渡区'}")

    # 泵站
    print(f"  {x[idx_pump]/1000:<12.1f} {0.0:<12.1f} {h[idx_pump]:<10.4f} 泵站中心")

    # 下游区域
    for dist_km in [1, 2, 3, 5]:
        dist_m = dist_km * 1000
        idx = np.argmin(np.abs(x - (pump_position + dist_m)))
        print(f"  {x[idx]/1000:<12.1f} {+dist_km:<12.1f} {h[idx]:<10.4f} "
              f"{'下游平台区 ⭐' if dist_km == 2 else '下游平台区' if dist_km == 1 else '下游过渡区' if dist_km == 3 else '下游正常流动'}")

    # 计算梯度
    print(f"\n【纵向梯度分析】")
    print(f"  {'位置(km)':<12} {'距泵站(km)':<12} {'梯度(‰)':<12} {'区域'}")
    print("-" * 90)

    for i, dist_km in enumerate([-5, -3, -2, -1, 0, 1, 2, 3, 5]):
        dist_m = dist_km * 1000
        idx = np.argmin(np.abs(x - (pump_position + dist_m)))

        if idx > 0 and idx < len(x) - 1:
            dx = x[idx+1] - x[idx-1]
            dh = h[idx+1] - h[idx-1]
            gradient = (dh / dx) * 1000  # 转换为‰

            # 区域判断
            if dist_km <= -3:
                region = "上游正常"
            elif dist_km < 0:
                region = "上游过渡"
            elif dist_km == 0:
                region = "泵站中心"
            elif dist_km <= 2:
                region = "下游平台"
            elif dist_km <= 3:
                region = "下游过渡"
            else:
                region = "下游正常"

            print(f"  {x[idx]/1000:<12.1f} {dist_km:<12.1f} {gradient:<12.3f} {region}")

    # 验证平台区稳定性
    print(f"\n【平台区稳定性验证】")
    # 平台区：泵站后1-2km
    platform_start = pump_position + 1000
    platform_end = pump_position + 2000
    platform_mask = (x >= platform_start) & (x <= platform_end)
    h_platform = h[platform_mask]

    platform_mean = np.mean(h_platform)
    platform_std = np.std(h_platform)
    platform_cv = (platform_std / platform_mean) * 100

    print(f"  平台区范围: {platform_start/1000:.1f} - {platform_end/1000:.1f} km")
    print(f"  平台区点数: {np.sum(platform_mask)}")
    print(f"  平均水深: {platform_mean:.4f} m")
    print(f"  标准差: {platform_std:.6f} m")
    print(f"  变异系数: {platform_cv:.4f}%")
    print(f"  稳定性: {'✓ 优秀 (CV<0.1%)' if platform_cv < 0.1 else '✓ 良好 (CV<1%)' if platform_cv < 1 else '○ 一般'}")

    # 生成详细图表
    print(f"\n" + "=" * 90)
    print("生成详细分析图表...")
    print("=" * 90)

    fig = plt.figure(figsize=(16, 10))

    # 子图1：整体纵剖面
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(x/1000, h, 'b-', linewidth=2, label='水深')

    # 标记泵站
    ax1.axvline(pump_position/1000, color='red', linestyle='--', alpha=0.5, label='泵站')

    # 标记测量点
    ax1.plot(upstream_x/1000, h_upstream, 'go', markersize=12, label=f'上游参考点 (-3km): {h_upstream:.4f}m', zorder=5)
    ax1.plot(downstream_x/1000, h_downstream, 'mo', markersize=12, label=f'下游测量点 (+2km): {h_downstream:.4f}m', zorder=5)

    # 标记平台区
    ax1.axvspan((pump_position+1000)/1000, (pump_position+2000)/1000, alpha=0.2, color='yellow', label='下游平台区')

    # 标记扬程
    ax1.annotate('', xy=(downstream_x/1000, h_downstream), xytext=(downstream_x/1000, h_upstream),
                arrowprops=dict(arrowstyle='<->', color='red', lw=2))
    ax1.text(downstream_x/1000+2, (h_upstream+h_downstream)/2,
            f'扬程={actual_head:.3f}m\n({head_accuracy:.1f}%)',
            fontsize=12, color='red', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax1.set_xlabel('距离 (km)', fontsize=12)
    ax1.set_ylabel('水深 (m)', fontsize=12)
    ax1.set_title('串联闸泵群系统 - 水深纵剖面图', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=10)

    # 子图2：泵站附近局部放大
    ax2 = plt.subplot(2, 1, 2)

    # 选择泵站±10km范围
    zoom_range = 10000  # 10km
    zoom_mask = (x >= pump_position - zoom_range) & (x <= pump_position + zoom_range)
    x_zoom = x[zoom_mask]
    h_zoom = h[zoom_mask]

    ax2.plot(x_zoom/1000, h_zoom, 'b-', linewidth=2, label='水深')

    # 标记泵站
    ax2.axvline(pump_position/1000, color='red', linestyle='--', alpha=0.5, label='泵站')

    # 标记测量点
    ax2.plot(upstream_x/1000, h_upstream, 'go', markersize=14,
            label=f'上游参考点: {h_upstream:.4f}m', zorder=5)
    ax2.plot(downstream_x/1000, h_downstream, 'mo', markersize=14,
            label=f'下游测量点: {h_downstream:.4f}m', zorder=5)
    ax2.plot(pump_position/1000, h_pump, 'ro', markersize=14,
            label=f'泵站处: {h_pump:.4f}m', zorder=5)

    # 标记关键区域
    ax2.axvspan((pump_position-3000)/1000, (pump_position-2000)/1000, alpha=0.15, color='green', label='上游参考区')
    ax2.axvspan((pump_position-2000)/1000, (pump_position)/1000, alpha=0.15, color='orange', label='上游过渡区')
    ax2.axvspan((pump_position)/1000, (pump_position+1000)/1000, alpha=0.15, color='red', label='泵站过渡区')
    ax2.axvspan((pump_position+1000)/1000, (pump_position+2000)/1000, alpha=0.25, color='yellow', label='下游平台区 ⭐')
    ax2.axvspan((pump_position+2000)/1000, (pump_position+4000)/1000, alpha=0.15, color='cyan', label='下游过渡区')

    # 添加扬程标注
    ax2.annotate('', xy=(downstream_x/1000, h_downstream), xytext=(downstream_x/1000, h_upstream),
                arrowprops=dict(arrowstyle='<->', color='red', lw=3))
    ax2.text(downstream_x/1000+0.5, (h_upstream+h_downstream)/2,
            f'实际扬程\n{actual_head:.4f}m\n\n目标扬程\n{rated_head:.3f}m\n\n精度\n{head_accuracy:.2f}%',
            fontsize=11, color='red', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

    ax2.set_xlabel('距离 (km)', fontsize=12)
    ax2.set_ylabel('水深 (m)', fontsize=12)
    ax2.set_title(f'泵站附近局部放大图 (±10km) | 精度等级: {grade}', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best', fontsize=9, ncol=2)

    plt.tight_layout()

    # 保存图表
    output_file = "results_gate_pump_auto/pump_head_precision_analysis.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"  ✓ 图表已保存: {output_file}")

    plt.close()

    # 生成详细报告
    report_file = "results_gate_pump_auto/pump_head_precision_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 90 + "\n")
        f.write("泵站扬程精度分析报告\n")
        f.write("=" * 90 + "\n")
        f.write(f"\n生成时间: {np.datetime64('now', 's')}\n")
        f.write(f"数据文件: {data_file}\n")

        f.write(f"\n【系统配置】\n")
        f.write(f"  渠道长度: {x[-1]/1000:.1f} km\n")
        f.write(f"  泵站位置: {pump_position/1000:.1f} km\n")
        f.write(f"  额定扬程: {rated_head:.3f} m\n")
        f.write(f"  网格点数: {len(x)}\n")

        f.write(f"\n【测量方法（v3.0高精度算法）】\n")
        f.write(f"  上游参考点: 泵站上游3km（远离过渡区）\n")
        f.write(f"  下游测量点: 泵站下游1km（平台区中心）\n")
        f.write(f"  扬程计算: 下游水深 - 上游水深\n")

        f.write(f"\n【水深数据】\n")
        f.write(f"  上游参考水深 ({upstream_x/1000:.1f}km): {h_upstream:.6f} m\n")
        f.write(f"  泵站处水深 ({pump_position/1000:.1f}km):   {h_pump:.6f} m\n")
        f.write(f"  下游平台水深 ({downstream_x/1000:.1f}km): {h_downstream:.6f} m\n")

        f.write(f"\n【扬程分析】\n")
        f.write(f"  额定扬程:   {rated_head:.6f} m\n")
        f.write(f"  实际扬程:   {actual_head:.6f} m\n")
        f.write(f"  绝对误差:   {head_error_abs:+.6f} m\n")
        f.write(f"  相对误差:   {head_error_percent:+.4f}%\n")
        f.write(f"  扬程准确度: {head_accuracy:.4f}%\n")

        f.write(f"\n【精度评级】\n")
        f.write(f"  {grade}\n")

        f.write(f"\n【平台区稳定性】\n")
        f.write(f"  平台区范围: {platform_start/1000:.1f} - {platform_end/1000:.1f} km\n")
        f.write(f"  平均水深: {platform_mean:.6f} m\n")
        f.write(f"  标准差: {platform_std:.6f} m\n")
        f.write(f"  变异系数: {platform_cv:.6f}%\n")

        f.write(f"\n【结论】\n")
        if abs(head_error_percent) < 2.0:
            f.write(f"  ✓ 泵站扬程精度优秀，达到高精度要求\n")
            f.write(f"  ✓ v3.0高精度算法工作正常\n")
        elif abs(head_error_percent) < 5.0:
            f.write(f"  ○ 泵站扬程精度良好，在可接受范围内\n")
        else:
            f.write(f"  ✗ 泵站扬程精度偏差较大，需要优化\n")

        f.write("\n" + "=" * 90 + "\n")

    print(f"  ✓ 报告已保存: {report_file}")

    print(f"\n" + "=" * 90)
    print("分析完成！")
    print("=" * 90)
    print(f"\n关键结论: {grade_emoji} {grade}")
    print(f"  实际扬程: {actual_head:.4f} m (目标: {rated_head:.3f} m)")
    print(f"  精度: {head_accuracy:.2f}% (误差: {head_error_percent:+.2f}%)")
    print("=" * 90)

    return True


if __name__ == "__main__":
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 运行分析
    success = analyze_pump_head_precision()

    sys.exit(0 if success else 1)
