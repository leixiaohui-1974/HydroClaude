#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
串联闸泵群系统 - 完整非恒定流测试

测试内容：
1. 泵站启停响应测试
2. 时空演化分析（水深、流量）
3. 多扰动组合测试
4. 动画生成
5. 关键指标统计

作者: Claude AI
日期: 2025-10-26
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def test_pump_on_off():
    """
    测试1: 泵站启停响应
    
    场景：
    - 初始稳态：泵站运行
    - t=300s：泵站关闭
    - t=600s：泵站重启
    
    观测：水位、流量的响应特性
    """
    print("\n" + "="*80)
    print("测试1: 泵站启停响应")
    print("="*80)
    
    # 加载配置
    modeler = UniversalModeler("config_gate_pump_auto.yaml")
    modeler.setup_structures()
    x = modeler.setup_grid()
    solver = modeler.setup_solver(x)
    modeler.select_algorithm()
    
    # 稳态初始化
    print("\n[1/5] 稳态初始化...")
    result = modeler.run_steady_simulation()
    print(f"  ✓ 稳态收敛 (迭代{result['iterations']}次)")
    
    # 找到泵站索引
    pump_idx = None
    pump_structure = None
    if hasattr(solver, 'internal_structures'):
        for position, struct in solver.internal_structures:
            if hasattr(struct, 'rated_head') and struct.rated_head > 0:
                pump_idx = np.argmin(np.abs(solver.x - position))
                pump_structure = struct
                break
    else:
        for struct in modeler.structures:
            if hasattr(struct, 'rated_head') and struct.rated_head > 0:
                pump_idx = np.argmin(np.abs(solver.x - struct.position))
                pump_structure = struct
                break
    
    if pump_idx is None:
        print("❌ 未找到泵站")
        return None
    
    print(f"\n[2/5] 泵站信息")
    print(f"  位置: {pump_structure.position/1000:.1f} km (索引{pump_idx})")
    print(f"  额定扬程: {pump_structure.rated_head:.2f} m")
    
    # 非恒定流模拟
    print(f"\n[3/5] 非恒定流模拟 (0-900秒)")
    
    # 参数设置
    dt = 2.0  # 时间步长
    T_total = 900.0  # 总时长
    save_interval = 5  # 保存间隔
    
    n_steps = int(T_total / dt)
    n_saves = n_steps // save_interval
    
    # 存储数组
    times = np.zeros(n_saves)
    h_saves = np.zeros((n_saves, len(solver.x)))
    q_saves = np.zeros((n_saves, len(solver.x)))
    
    # 关键点索引
    idx_upstream = pump_idx - 5
    idx_pump = pump_idx
    idx_downstream = pump_idx + 5
    
    h_upstream_history = []
    h_pump_history = []
    h_downstream_history = []
    pump_status_history = []
    
    # 时间步进
    save_count = 0
    for step in range(n_steps):
        t = step * dt
        
        # 控制泵站启停
        if t < 300:
            pump_on = True
        elif t < 600:
            pump_on = False
            if t == 300:
                print(f"\n  t={t:.0f}s: [扰动] 泵站关闭")
        else:
            pump_on = True
            if t == 600:
                print(f"  t={t:.0f}s: [扰动] 泵站重启")
        
        # 更新泵站状态
        pump_structure.is_active = pump_on
        
        # 时间步进
        solver.step(dt)
        
        # 记录历史
        h_upstream_history.append(solver.h[idx_upstream])
        h_pump_history.append(solver.h[idx_pump])
        h_downstream_history.append(solver.h[idx_downstream])
        pump_status_history.append(1.0 if pump_on else 0.0)
        
        # 保存
        if step % save_interval == 0:
            times[save_count] = t
            h_saves[save_count, :] = solver.h.copy()
            q_saves[save_count, :] = (solver.hu / solver.h).copy()
            save_count += 1
            
            if step % (n_steps // 10) == 0:
                print(f"  进度: {100*step//n_steps}% | t={t:.0f}s | 水深范围=[{solver.h.min():.2f}, {solver.h.max():.2f}] m")
    
    print(f"  ✓ 模拟完成")
    
    # 分析结果
    print(f"\n[4/5] 结果分析")
    
    # 泵站上下游水深差
    head_diff_history = np.array(h_downstream_history) - np.array(h_upstream_history)
    
    # 稳态阶段（0-200s）
    steady_start = head_diff_history[:100]
    print(f"\n  泵站运行阶段 (0-300s):")
    print(f"    上游水深: {np.mean(h_upstream_history[:150]):.3f} m")
    print(f"    下游水深: {np.mean(h_downstream_history[:150]):.3f} m")
    print(f"    实际扬程: {np.mean(head_diff_history[:150]):.3f} m")
    print(f"    额定扬程: {pump_structure.rated_head:.3f} m")
    
    # 关闭阶段（300-600s）
    off_period = head_diff_history[150:300]
    print(f"\n  泵站关闭阶段 (300-600s):")
    print(f"    初始扬程: {head_diff_history[150]:.3f} m")
    print(f"    最终扬程: {head_diff_history[299]:.3f} m")
    print(f"    下降幅度: {head_diff_history[150] - head_diff_history[299]:.3f} m")
    
    # 重启阶段（600-900s）
    restart_period = head_diff_history[300:]
    print(f"\n  泵站重启阶段 (600-900s):")
    print(f"    初始扬程: {head_diff_history[300]:.3f} m")
    print(f"    最终扬程: {head_diff_history[-1]:.3f} m")
    print(f"    恢复幅度: {head_diff_history[-1] - head_diff_history[300]:.3f} m")
    
    # 生成图表
    print(f"\n[5/5] 生成图表...")
    
    # 时间历史
    t_full = np.arange(len(h_upstream_history)) * dt
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # 子图1: 水深时间历史
    ax = axes[0]
    ax.plot(t_full, h_upstream_history, 'b-', label=f'上游 ({solver.x[idx_upstream]/1000:.1f}km)', linewidth=1.5)
    ax.plot(t_full, h_pump_history, 'g-', label=f'泵站 ({solver.x[idx_pump]/1000:.1f}km)', linewidth=1.5)
    ax.plot(t_full, h_downstream_history, 'r-', label=f'下游 ({solver.x[idx_downstream]/1000:.1f}km)', linewidth=1.5)
    ax.axvline(300, color='k', linestyle='--', alpha=0.3, label='泵站关闭')
    ax.axvline(600, color='k', linestyle='-.', alpha=0.3, label='泵站重启')
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Water Depth (m)', fontsize=11)
    ax.set_title('Pump On-Off Response: Water Depth History', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 子图2: 扬程时间历史
    ax = axes[1]
    ax.plot(t_full, head_diff_history, 'b-', linewidth=2, label='Actual Head')
    ax.axhline(pump_structure.rated_head, color='r', linestyle='--', linewidth=1.5, label='Rated Head')
    ax.axvline(300, color='k', linestyle='--', alpha=0.3)
    ax.axvline(600, color='k', linestyle='-.', alpha=0.3)
    ax.fill_between(t_full, 0, pump_status_history, alpha=0.2, color='green', label='Pump Status')
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Head (m)', fontsize=11)
    ax.set_title('Pump Station Head Response', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # 子图3: 时空演化（水深）
    ax = axes[2]
    X, T = np.meshgrid(solver.x / 1000, times)
    contour = ax.contourf(X, T, h_saves, levels=20, cmap='Blues')
    ax.axvline(pump_structure.position / 1000, color='r', linestyle='--', linewidth=2, label='Pump Station')
    cbar = plt.colorbar(contour, ax=ax)
    cbar.set_label('Water Depth (m)', fontsize=10)
    ax.set_xlabel('Distance (km)', fontsize=11)
    ax.set_ylabel('Time (s)', fontsize=11)
    ax.set_title('Spatiotemporal Evolution: Water Depth', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    
    plt.tight_layout()
    filename = 'test_pump_on_off.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"  ✓ 保存: {filename}")
    plt.close()
    
    # 返回数据
    return {
        'times': times,
        'x': solver.x,
        'h_saves': h_saves,
        'q_saves': q_saves,
        'h_upstream': h_upstream_history,
        'h_downstream': h_downstream_history,
        'head_diff': head_diff_history,
        'pump_status': pump_status_history,
        't_full': t_full
    }


def test_multi_disturbance():
    """
    测试2: 多扰动组合
    
    场景：
    - t=200s：上游流量从10→15 m³/s
    - t=400s：闸门1开度减小50%
    - t=600s：泵站关闭
    - t=800s：闸门2开度增大50%
    
    观测：系统的综合响应
    """
    print("\n" + "="*80)
    print("测试2: 多扰动组合")
    print("="*80)
    
    # 加载配置
    modeler = UniversalModeler("config_gate_pump_auto.yaml")
    modeler.setup_structures()
    x = modeler.setup_grid()
    solver = modeler.setup_solver(x)
    modeler.select_algorithm()
    
    # 稳态初始化
    print("\n[1/4] 稳态初始化...")
    result = modeler.run_steady_simulation()
    print(f"  ✓ 稳态收敛")
    
    # 找到结构物
    gate1, pump, gate2 = None, None, None
    if hasattr(solver, 'internal_structures'):
        for position, struct in solver.internal_structures:
            if hasattr(struct, 'rated_head') and struct.rated_head > 0:
                pump = struct
            elif hasattr(struct, 'gate_opening'):
                if gate1 is None:
                    gate1 = struct
                else:
                    gate2 = struct
    else:
        for struct in modeler.structures:
            if hasattr(struct, 'rated_head') and struct.rated_head > 0:
                pump = struct
            elif hasattr(struct, 'gate_opening'):
                if gate1 is None:
                    gate1 = struct
                else:
                    gate2 = struct
    
    if not all([gate1, pump, gate2]):
        print("❌ 结构物未完全找到")
        return None
    
    # 记录初始状态
    Q_initial = solver.hu[0] / solver.h[0]
    gate1_initial = gate1.gate_opening
    gate2_initial = gate2.gate_opening
    
    print(f"\n[2/4] 初始状态")
    print(f"  上游流量: {Q_initial:.2f} m³/s")
    print(f"  闸门1开度: {gate1_initial:.2f} m @ {gate1.position/1000:.1f} km")
    print(f"  闸门2开度: {gate2_initial:.2f} m @ {gate2.position/1000:.1f} km")
    print(f"  泵站扬程: {pump.rated_head:.2f} m @ {pump.position/1000:.1f} km")
    
    # 非恒定流模拟
    print(f"\n[3/4] 非恒定流模拟 (0-1000秒)")
    
    dt = 2.0
    T_total = 1000.0
    save_interval = 5
    
    n_steps = int(T_total / dt)
    n_saves = n_steps // save_interval
    
    times = np.zeros(n_saves)
    h_saves = np.zeros((n_saves, len(solver.x)))
    q_saves = np.zeros((n_saves, len(solver.x)))
    
    # 监测点
    monitor_points = [0, len(solver.x)//4, len(solver.x)//2, 3*len(solver.x)//4, -1]
    h_monitors = {i: [] for i in monitor_points}
    
    save_count = 0
    for step in range(n_steps):
        t = step * dt
        
        # 应用扰动
        if t >= 200 and t < 200 + dt:
            # 上游流量增加
            solver.hu[0] = 15.0 * solver.h[0]
            print(f"\n  t={t:.0f}s: [扰动1] 上游流量 {Q_initial:.1f} → 15.0 m³/s")
        
        if t >= 400 and t < 400 + dt:
            # 闸门1减小
            gate1.gate_opening = gate1_initial * 0.5
            print(f"  t={t:.0f}s: [扰动2] 闸门1开度 {gate1_initial:.2f} → {gate1.gate_opening:.2f} m")
        
        if t >= 600 and t < 600 + dt:
            # 泵站关闭
            pump.is_active = False
            print(f"  t={t:.0f}s: [扰动3] 泵站关闭")
        
        if t >= 800 and t < 800 + dt:
            # 闸门2增大
            gate2.gate_opening = gate2_initial * 1.5
            print(f"  t={t:.0f}s: [扰动4] 闸门2开度 {gate2_initial:.2f} → {gate2.gate_opening:.2f} m")
        
        # 时间步进
        solver.step(dt)
        
        # 监测点记录
        for idx in monitor_points:
            h_monitors[idx].append(solver.h[idx])
        
        # 保存
        if step % save_interval == 0:
            times[save_count] = t
            h_saves[save_count, :] = solver.h.copy()
            q_saves[save_count, :] = (solver.hu / solver.h).copy()
            save_count += 1
            
            if step % (n_steps // 10) == 0:
                print(f"  进度: {100*step//n_steps}% | t={t:.0f}s")
    
    print(f"  ✓ 模拟完成")
    
    # 生成图表
    print(f"\n[4/4] 生成图表...")
    
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # 子图1: 时空演化（水深）
    ax1 = fig.add_subplot(gs[0, :])
    X, T = np.meshgrid(solver.x / 1000, times)
    contour = ax1.contourf(X, T, h_saves, levels=20, cmap='Blues')
    ax1.axvline(gate1.position / 1000, color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
    ax1.axvline(pump.position / 1000, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    ax1.axvline(gate2.position / 1000, color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
    ax1.axhline(200, color='white', linestyle=':', alpha=0.5)
    ax1.axhline(400, color='white', linestyle=':', alpha=0.5)
    ax1.axhline(600, color='white', linestyle=':', alpha=0.5)
    ax1.axhline(800, color='white', linestyle=':', alpha=0.5)
    cbar = plt.colorbar(contour, ax=ax1)
    cbar.set_label('Water Depth (m)', fontsize=10)
    ax1.set_xlabel('Distance (km)', fontsize=11)
    ax1.set_ylabel('Time (s)', fontsize=11)
    ax1.set_title('Spatiotemporal Evolution: Water Depth (Multi-Disturbance)', fontsize=12, fontweight='bold')
    
    # 子图2: 时空演化（流量）
    ax2 = fig.add_subplot(gs[1, :])
    contour = ax2.contourf(X, T, q_saves, levels=20, cmap='RdYlGn')
    ax2.axvline(gate1.position / 1000, color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
    ax2.axvline(pump.position / 1000, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    ax2.axvline(gate2.position / 1000, color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
    cbar = plt.colorbar(contour, ax=ax2)
    cbar.set_label('Flow Rate (m³/s)', fontsize=10)
    ax2.set_xlabel('Distance (km)', fontsize=11)
    ax2.set_ylabel('Time (s)', fontsize=11)
    ax2.set_title('Spatiotemporal Evolution: Flow Rate', fontsize=12, fontweight='bold')
    
    # 子图3-4: 监测点水深历史
    t_full = np.arange(len(h_monitors[0])) * dt
    
    ax3 = fig.add_subplot(gs[2, 0])
    for idx in [0, len(solver.x)//4, len(solver.x)//2]:
        label = f'{solver.x[idx]/1000:.0f} km'
        ax3.plot(t_full, h_monitors[idx], label=label, linewidth=1.5)
    ax3.axvline(200, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax3.axvline(400, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax3.axvline(600, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax3.axvline(800, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax3.set_xlabel('Time (s)', fontsize=10)
    ax3.set_ylabel('Water Depth (m)', fontsize=10)
    ax3.set_title('Upstream Monitoring Points', fontsize=11, fontweight='bold')
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)
    
    ax4 = fig.add_subplot(gs[2, 1])
    for idx in [len(solver.x)//2, 3*len(solver.x)//4, -1]:
        label = f'{solver.x[idx]/1000:.0f} km'
        ax4.plot(t_full, h_monitors[idx], label=label, linewidth=1.5)
    ax4.axvline(200, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax4.axvline(400, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax4.axvline(600, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax4.axvline(800, color='k', linestyle='--', alpha=0.3, linewidth=0.8)
    ax4.set_xlabel('Time (s)', fontsize=10)
    ax4.set_ylabel('Water Depth (m)', fontsize=10)
    ax4.set_title('Downstream Monitoring Points', fontsize=11, fontweight='bold')
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)
    
    filename = 'test_multi_disturbance.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"  ✓ 保存: {filename}")
    plt.close()
    
    return {
        'times': times,
        'x': solver.x,
        'h_saves': h_saves,
        'q_saves': q_saves,
        'h_monitors': h_monitors,
        't_full': t_full
    }


def generate_animation(data, filename='animation.gif'):
    """
    生成动画
    """
    print("\n" + "="*80)
    print("生成动画")
    print("="*80)
    
    fig, ax = plt.subplots(figsize=(12, 4))
    
    x = data['x'] / 1000
    h_saves = data['h_saves']
    times = data['times']
    
    # 初始化
    line, = ax.plot([], [], 'b-', linewidth=2, label='Water Surface')
    ax.plot(x, np.zeros_like(x), 'k-', linewidth=1, label='Channel Bottom')
    
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(0, h_saves.max() * 1.2)
    ax.set_xlabel('Distance (km)', fontsize=11)
    ax.set_ylabel('Elevation (m)', fontsize=11)
    ax.set_title('Water Surface Animation', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes, fontsize=10, verticalalignment='top')
    
    def init():
        line.set_data([], [])
        time_text.set_text('')
        return line, time_text
    
    def animate(i):
        line.set_data(x, h_saves[i])
        time_text.set_text(f'Time: {times[i]:.0f} s')
        return line, time_text
    
    anim = FuncAnimation(fig, animate, init_func=init, frames=len(times), 
                        interval=50, blit=True, repeat=True)
    
    print(f"  正在生成动画... (共{len(times)}帧)")
    anim.save(filename, writer='pillow', fps=20, dpi=100)
    print(f"  ✓ 保存: {filename}")
    plt.close()


def main():
    """
    主函数
    """
    print("\n" + "="*90)
    print(" "*25 + "串联闸泵群系统 - 完整非恒定流测试")
    print("="*90)
    
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 测试1: 泵站启停
    data1 = test_pump_on_off()
    
    # 测试2: 多扰动组合
    data2 = test_multi_disturbance()
    
    # 生成动画
    if data1 is not None:
        try:
            generate_animation(data1, 'animation_pump_on_off.gif')
        except Exception as e:
            print(f"  ⚠ 动画生成失败: {e}")
    
    if data2 is not None:
        try:
            generate_animation(data2, 'animation_multi_disturbance.gif')
        except Exception as e:
            print(f"  ⚠ 动画生成失败: {e}")
    
    print("\n" + "="*90)
    print("✓ 所有测试完成！")
    print("="*90)
    print("\n生成的文件:")
    print("  - test_pump_on_off.png")
    print("  - test_multi_disturbance.png")
    print("  - animation_pump_on_off.gif (如果成功)")
    print("  - animation_multi_disturbance.gif (如果成功)")
    print("="*90)


if __name__ == "__main__":
    main()
