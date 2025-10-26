#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
串联闸泵群系统 - 简化非恒定流测试

专注于：
1. 泵站启停响应
2. 时空演化可视化
3. 关键指标统计

作者: Claude AI
日期: 2025-10-26
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modeling.universal_modeler import UniversalModeler


def test_pump_station_response():
    """
    测试: 泵站启停响应
    
    场景：
    - 稳态：泵站运行
    - t=300s：泵站关闭
    - t=600s：泵站重启
    """
    print("\n" + "="*80)
    print("泵站启停响应测试")
    print("="*80)
    
    # 加载并初始化
    modeler = UniversalModeler("config_gate_pump_auto.yaml")
    modeler.setup_structures()
    x = modeler.setup_grid()
    solver = modeler.setup_solver(x)
    modeler.select_algorithm()
    
    # 稳态初始化
    print("\n[1/4] 稳态初始化...")
    result = modeler.run_steady_simulation()
    print(f"  ✓ 稳态收敛 (迭代{result['iterations']}次)")
    
    # 找到泵站
    pump_structure = None
    pump_position = None
    for position, struct in solver.internal_structures:
        if hasattr(struct, 'rated_head') and struct.rated_head > 0:
            pump_structure = struct
            pump_position = position
            break
    
    if pump_structure is None:
        print("❌ 未找到泵站")
        return
    
    pump_idx = np.argmin(np.abs(solver.x - pump_position))
    print(f"\n[2/4] 泵站信息")
    print(f"  位置: {pump_position/1000:.1f} km (索引{pump_idx})")
    print(f"  额定扬程: {pump_structure.rated_head:.2f} m")
    
    # 非恒定流模拟
    print(f"\n[3/4] 非恒定流模拟 (0-900秒)")
    
    dt = 2.0
    T_total = 900.0
    save_interval = 10
    
    n_steps = int(T_total / dt)
    n_saves = n_steps // save_interval + 1
    
    times = []
    h_upstream = []
    h_pump = []
    h_downstream = []
    pump_status = []
    
    # 监测点
    idx_up = max(pump_idx - 10, 0)
    idx_down = min(pump_idx + 10, len(solver.x) - 1)
    
    print(f"  监测点: 上游{solver.x[idx_up]/1000:.1f}km, 泵站{solver.x[pump_idx]/1000:.1f}km, 下游{solver.x[idx_down]/1000:.1f}km")
    
    for step in range(n_steps):
        t = step * dt
        
        # 控制泵站启停
        if t < 300:
            is_active = True
        elif t < 600:
            is_active = False
            if abs(t - 300) < dt:
                print(f"\n  t={t:.0f}s: [扰动] 泵站关闭")
        else:
            is_active = True
            if abs(t - 600) < dt:
                print(f"  t={t:.0f}s: [扰动] 泵站重启")
        
        # 更新泵站状态
        pump_structure.is_active = is_active
        
        # 时间步进
        try:
            solver.step(dt)
        except Exception as e:
            print(f"  ⚠ 步进失败 t={t:.1f}s: {e}")
            break
        
        # 记录
        if step % save_interval == 0:
            times.append(t)
            h_upstream.append(solver.h[idx_up])
            h_pump.append(solver.h[pump_idx])
            h_downstream.append(solver.h[idx_down])
            pump_status.append(1.0 if is_active else 0.0)
        
        if step % (n_steps // 10) == 0:
            print(f"  进度: {100*step//n_steps}% | t={t:.0f}s | 水深范围=[{solver.h.min():.2f}, {solver.h.max():.2f}] m")
    
    print(f"  ✓ 模拟完成 ({len(times)}个记录点)")
    
    # 分析结果
    print(f"\n[4/4] 生成图表...")
    
    times = np.array(times)
    h_upstream = np.array(h_upstream)
    h_pump = np.array(h_pump)
    h_downstream = np.array(h_downstream)
    head_diff = h_downstream - h_upstream
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    # 子图1: 水深时间历史
    ax = axes[0]
    ax.plot(times, h_upstream, 'b-', label=f'Upstream ({solver.x[idx_up]/1000:.1f}km)', linewidth=2)
    ax.plot(times, h_pump, 'g-', label=f'Pump ({solver.x[pump_idx]/1000:.1f}km)', linewidth=2)
    ax.plot(times, h_downstream, 'r-', label=f'Downstream ({solver.x[idx_down]/1000:.1f}km)', linewidth=2)
    ax.axvline(300, color='k', linestyle='--', alpha=0.4, label='Pump OFF')
    ax.axvline(600, color='k', linestyle='-.', alpha=0.4, label='Pump ON')
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Water Depth (m)', fontsize=11)
    ax.set_title('Pump Station On-Off Response', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)
    
    # 子图2: 扬程历史
    ax = axes[1]
    ax.plot(times, head_diff, 'b-', linewidth=2.5, label='Actual Head')
    ax.axhline(pump_structure.rated_head, color='r', linestyle='--', linewidth=1.5, label='Rated Head')
    ax.fill_between(times, 0, np.array(pump_status) * pump_structure.rated_head * 1.2, 
                     alpha=0.2, color='green', label='Pump ON')
    ax.axvline(300, color='k', linestyle='--', alpha=0.4)
    ax.axvline(600, color='k', linestyle='-.', alpha=0.4)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Head (m)', fontsize=11)
    ax.set_title('Pump Head Response', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    filename = 'test_pump_response_unsteady.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"  ✓ 保存: {filename}")
    plt.close()
    
    # 统计分析
    print(f"\n结果统计:")
    
    # 运行阶段 (0-300s)
    idx_on1 = times < 300
    print(f"  泵站运行阶段 (0-300s):")
    print(f"    平均扬程: {np.mean(head_diff[idx_on1]):.3f} m")
    print(f"    额定扬程: {pump_structure.rated_head:.3f} m")
    print(f"    相对误差: {abs(np.mean(head_diff[idx_on1]) - pump_structure.rated_head) / pump_structure.rated_head * 100:.2f}%")
    
    # 关闭阶段 (300-600s)
    idx_off = (times >= 300) & (times < 600)
    if np.any(idx_off):
        print(f"\n  泵站关闭阶段 (300-600s):")
        print(f"    初始扬程: {head_diff[idx_off][0]:.3f} m")
        print(f"    最终扬程: {head_diff[idx_off][-1]:.3f} m")
        print(f"    下降: {head_diff[idx_off][0] - head_diff[idx_off][-1]:.3f} m")
    
    # 重启阶段 (600-900s)
    idx_on2 = times >= 600
    if np.any(idx_on2):
        print(f"\n  泵站重启阶段 (600-900s):")
        print(f"    初始扬程: {head_diff[idx_on2][0]:.3f} m")
        print(f"    最终扬程: {head_diff[idx_on2][-1]:.3f} m")
        print(f"    恢复: {head_diff[idx_on2][-1] - head_diff[idx_on2][0]:.3f} m")


def main():
    """
    主函数
    """
    print("\n" + "="*90)
    print(" "*20 + "串联闸泵群系统 - 非恒定流测试")
    print("="*90)
    
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 执行测试
    test_pump_station_response()
    
    print("\n" + "="*90)
    print("✓ 测试完成！")
    print("="*90)


if __name__ == "__main__":
    main()
