#!/usr/bin/env python3
"""
串联闸泵群系统综合扰动测试
测试场景：
1. 上游流量阶跃（已测试）
2. 闸门动态调节（新增）
3. 泵站启停调控（新增）
4. 下游水位变化（新增）
5. 组合扰动（新增）
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import PillowWriter
import sys
import os

# 添加项目路径
sys.path.insert(0, '/workspace')

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStation


class ComprehensiveDisturbanceTest:
    """综合扰动测试类"""
    
    def __init__(self):
        self.setup_system()
        
    def setup_system(self):
        """建立系统"""
        print("\n" + "=" * 80)
        print("串联闸泵群系统 - 综合扰动测试")
        print("=" * 80)
        
        # 系统参数
        L = 100000  # 100 km
        nx = 501
        B = 10.0
        S0 = 0.0001
        n = 0.025
        
        # 创建结构物（4个闸门 + 2个泵站）
        self.gate1 = SluiceGate(position=20000, width=B, opening=1.5)
        self.pump1 = PumpStation(position=35000, width=B, rated_flow=10.0, rated_head=3.0)
        self.gate2 = SluiceGate(position=50000, width=B, opening=2.0)
        self.pump2 = PumpStation(position=65000, width=B, rated_flow=10.0, rated_head=4.0)
        self.gate3 = SluiceGate(position=80000, width=B, opening=1.8)
        
        structures = [
            (20000, self.gate1),
            (35000, self.pump1),
            (50000, self.gate2),
            (65000, self.pump2),
            (80000, self.gate3)
        ]
        
        # 创建求解器
        self.solver = HydrostaticCanalSolver(
            length=L,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            internal_structures=structures
        )
        
        print(f"\n系统配置:")
        print(f"  渠道长度: {L/1000:.1f} km")
        print(f"  网格点数: {nx}")
        print(f"  结构物数量: {len(structures)}")
        for pos, struct in structures:
            print(f"    - {type(struct).__name__} @ {pos/1000:.1f} km")
        
    def run_steady_state(self, Q_target=10.0, h_downstream=2.0):
        """稳态初始化"""
        print(f"\n稳态初始化...")
        print(f"  目标流量: {Q_target:.1f} m³/s")
        print(f"  下游水深: {h_downstream:.1f} m")
        
        result = self.solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_downstream,
            max_iterations=1000,
            convergence_tol=0.001,
            dt=0.5,
            verbose=False
        )
        
        print(f"  收敛: {result['converged']}")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  流量误差: {result['Q_error_percent']:.3f}%")
        
        return result
    
    def scenario_1_upstream_flow_jump(self):
        """场景1: 上游流量阶跃（10 → 15 m³/s）"""
        print("\n" + "-" * 80)
        print("场景1: 上游流量阶跃")
        print("-" * 80)
        
        # 稳态初始化
        self.run_steady_state(Q_target=10.0, h_downstream=2.0)
        
        # 记录数据
        nt = 200
        dt = 10.0  # 10s per step
        times = np.arange(nt) * dt
        h_history = np.zeros((nt, self.solver.nx))
        Q_history = np.zeros((nt, self.solver.nx))
        
        # 上游流量变化
        Q_in = 10.0
        
        print(f"\n非恒定流模拟:")
        print(f"  时长: {nt*dt:.0f}s = {nt*dt/60:.1f}min")
        print(f"  时间步长: {dt}s")
        
        for i in range(nt):
            # t=600s时流量跃变
            if i == 60:
                Q_in = 15.0
                print(f"  t={i*dt:.0f}s: 上游流量 {10.0} → {Q_in} m³/s")
            
            # Preissmann步
            h_new, hu_new = self.solver.step_preissmann(dt)
            
            # 应用边界条件
            h_new[0] = self.solver.h[0]  # 上游水深自然响应
            hu_new[0] = Q_in / self.solver.B  # 上游流量
            h_new[-1] = 2.0  # 下游水深固定
            
            # 更新状态
            self.solver.h = h_new
            self.solver.hu = hu_new
            
            # 应用内部边界条件
            self.solver._apply_pump_head_jump()
            if self.solver.structure_indices:
                self.solver._apply_internal_bc(t=i*dt, Q_target=Q_in)
            
            # 记录
            h_history[i, :] = self.solver.h
            Q_history[i, :] = self.solver.get_Q()
            
            if i % 50 == 0:
                Q_avg = np.mean(Q_history[i, :])
                print(f"  t={i*dt:.0f}s: Q_avg={Q_avg:.2f} m³/s, h_max={np.max(h_history[i,:]):.2f}m")
        
        return times, h_history, Q_history, "场景1_上游流量阶跃"
    
    def scenario_2_gate_regulation(self):
        """场景2: 闸门动态调节"""
        print("\n" + "-" * 80)
        print("场景2: 闸门动态调节")
        print("-" * 80)
        
        # 稳态初始化
        self.run_steady_state(Q_target=10.0, h_downstream=2.0)
        
        # 记录数据
        nt = 200
        dt = 10.0
        times = np.arange(nt) * dt
        h_history = np.zeros((nt, self.solver.nx))
        Q_history = np.zeros((nt, self.solver.nx))
        
        print(f"\n非恒定流模拟:")
        print(f"  时长: {nt*dt:.0f}s")
        
        for i in range(nt):
            # 闸门开度调节
            if i == 40:  # t=400s
                self.gate2.opening = 1.0  # 从2.0m关闭到1.0m
                print(f"  t={i*dt:.0f}s: 闸门2开度 2.0 → 1.0 m")
            
            if i == 100:  # t=1000s
                self.gate2.opening = 2.5  # 从1.0m打开到2.5m
                print(f"  t={i*dt:.0f}s: 闸门2开度 1.0 → 2.5 m")
            
            # Preissmann步
            h_new, hu_new = self.solver.step_preissmann(dt)
            
            # 边界条件
            hu_new[0] = 10.0 / self.solver.B
            h_new[-1] = 2.0
            
            # 更新
            self.solver.h = h_new
            self.solver.hu = hu_new
            
            # 内部边界条件
            self.solver._apply_pump_head_jump()
            if self.solver.structure_indices:
                self.solver._apply_internal_bc(t=i*dt, Q_target=10.0)
            
            # 记录
            h_history[i, :] = self.solver.h
            Q_history[i, :] = self.solver.get_Q()
            
            if i % 50 == 0:
                print(f"  t={i*dt:.0f}s: Q_avg={np.mean(Q_history[i,:]):.2f} m³/s")
        
        return times, h_history, Q_history, "场景2_闸门动态调节"
    
    def scenario_3_pump_control(self):
        """场景3: 泵站启停调控"""
        print("\n" + "-" * 80)
        print("场景3: 泵站启停调控")
        print("-" * 80)
        
        # 稳态初始化
        self.run_steady_state(Q_target=10.0, h_downstream=2.0)
        
        # 记录数据
        nt = 200
        dt = 10.0
        times = np.arange(nt) * dt
        h_history = np.zeros((nt, self.solver.nx))
        Q_history = np.zeros((nt, self.solver.nx))
        
        print(f"\n非恒定流模拟:")
        print(f"  时长: {nt*dt:.0f}s")
        
        for i in range(nt):
            # 泵站控制
            if i == 50:  # t=500s
                self.pump1.is_running = False
                print(f"  t={i*dt:.0f}s: 泵站1 关闭")
            
            if i == 120:  # t=1200s
                self.pump2.is_running = False
                print(f"  t={i*dt:.0f}s: 泵站2 关闭")
            
            # Preissmann步
            h_new, hu_new = self.solver.step_preissmann(dt)
            
            # 边界条件
            hu_new[0] = 10.0 / self.solver.B
            h_new[-1] = 2.0
            
            # 更新
            self.solver.h = h_new
            self.solver.hu = hu_new
            
            # 内部边界条件
            self.solver._apply_pump_head_jump()
            if self.solver.structure_indices:
                self.solver._apply_internal_bc(t=i*dt, Q_target=10.0)
            
            # 记录
            h_history[i, :] = self.solver.h
            Q_history[i, :] = self.solver.get_Q()
            
            if i % 50 == 0:
                print(f"  t={i*dt:.0f}s: Q_avg={np.mean(Q_history[i,:]):.2f} m³/s")
        
        return times, h_history, Q_history, "场景3_泵站启停调控"
    
    def scenario_4_downstream_disturbance(self):
        """场景4: 下游水位变化"""
        print("\n" + "-" * 80)
        print("场景4: 下游水位扰动")
        print("-" * 80)
        
        # 稳态初始化
        self.run_steady_state(Q_target=10.0, h_downstream=2.0)
        
        # 记录数据
        nt = 200
        dt = 10.0
        times = np.arange(nt) * dt
        h_history = np.zeros((nt, self.solver.nx))
        Q_history = np.zeros((nt, self.solver.nx))
        
        h_downstream = 2.0
        
        print(f"\n非恒定流模拟:")
        print(f"  时长: {nt*dt:.0f}s")
        
        for i in range(nt):
            # 下游水位变化
            if i == 60:  # t=600s
                h_downstream = 3.0
                print(f"  t={i*dt:.0f}s: 下游水位 2.0 → 3.0 m")
            
            if i == 140:  # t=1400s
                h_downstream = 1.5
                print(f"  t={i*dt:.0f}s: 下游水位 3.0 → 1.5 m")
            
            # Preissmann步
            h_new, hu_new = self.solver.step_preissmann(dt)
            
            # 边界条件
            hu_new[0] = 10.0 / self.solver.B
            h_new[-1] = h_downstream  # 下游水位变化
            
            # 更新
            self.solver.h = h_new
            self.solver.hu = hu_new
            
            # 内部边界条件
            self.solver._apply_pump_head_jump()
            if self.solver.structure_indices:
                self.solver._apply_internal_bc(t=i*dt, Q_target=10.0)
            
            # 记录
            h_history[i, :] = self.solver.h
            Q_history[i, :] = self.solver.get_Q()
            
            if i % 50 == 0:
                print(f"  t={i*dt:.0f}s: h_downstream={h_downstream:.1f}m, Q_avg={np.mean(Q_history[i,:]):.2f} m³/s")
        
        return times, h_history, Q_history, "场景4_下游水位扰动"
    
    def scenario_5_combined_disturbances(self):
        """场景5: 组合扰动（最复杂）"""
        print("\n" + "-" * 80)
        print("场景5: 组合扰动（上游流量+闸门+泵站+下游水位）")
        print("-" * 80)
        
        # 稳态初始化
        self.run_steady_state(Q_target=10.0, h_downstream=2.0)
        
        # 记录数据
        nt = 300
        dt = 10.0
        times = np.arange(nt) * dt
        h_history = np.zeros((nt, self.solver.nx))
        Q_history = np.zeros((nt, self.solver.nx))
        
        Q_in = 10.0
        h_downstream = 2.0
        
        print(f"\n非恒定流模拟:")
        print(f"  时长: {nt*dt:.0f}s = {nt*dt/60:.1f}min")
        
        for i in range(nt):
            # 组合扰动序列
            if i == 30:  # t=300s
                Q_in = 12.0
                print(f"  t={i*dt:.0f}s: [上游] 流量 10.0 → 12.0 m³/s")
            
            if i == 60:  # t=600s
                self.gate1.opening = 1.0
                print(f"  t={i*dt:.0f}s: [闸门1] 开度 1.5 → 1.0 m")
            
            if i == 90:  # t=900s
                self.pump1.is_running = False
                print(f"  t={i*dt:.0f}s: [泵站1] 关闭")
            
            if i == 120:  # t=1200s
                h_downstream = 2.5
                print(f"  t={i*dt:.0f}s: [下游] 水位 2.0 → 2.5 m")
            
            if i == 150:  # t=1500s
                self.gate2.opening = 2.5
                print(f"  t={i*dt:.0f}s: [闸门2] 开度 2.0 → 2.5 m")
            
            if i == 180:  # t=1800s
                self.pump1.is_running = True
                print(f"  t={i*dt:.0f}s: [泵站1] 启动")
            
            if i == 210:  # t=2100s
                Q_in = 8.0
                print(f"  t={i*dt:.0f}s: [上游] 流量 12.0 → 8.0 m³/s")
            
            if i == 240:  # t=2400s
                h_downstream = 1.8
                print(f"  t={i*dt:.0f}s: [下游] 水位 2.5 → 1.8 m")
            
            # Preissmann步
            h_new, hu_new = self.solver.step_preissmann(dt)
            
            # 边界条件
            hu_new[0] = Q_in / self.solver.B
            h_new[-1] = h_downstream
            
            # 更新
            self.solver.h = h_new
            self.solver.hu = hu_new
            
            # 内部边界条件
            self.solver._apply_pump_head_jump()
            if self.solver.structure_indices:
                self.solver._apply_internal_bc(t=i*dt, Q_target=Q_in)
            
            # 记录
            h_history[i, :] = self.solver.h
            Q_history[i, :] = self.solver.get_Q()
            
            if i % 60 == 0:
                print(f"  t={i*dt:.0f}s: Q_avg={np.mean(Q_history[i,:]):.2f} m³/s, h_avg={np.mean(h_history[i,:]):.2f}m")
        
        return times, h_history, Q_history, "场景5_组合扰动"
    
    def create_animation(self, times, h_history, Q_history, title, filename):
        """创建动画"""
        print(f"\n生成动画: {filename}")
        
        x = self.solver.x / 1000  # km
        z = 10.0 - 0.0001 * self.solver.x  # 河底高程
        
        # 结构物位置
        structures = [
            (20, "闸1"),
            (35, "泵1"),
            (50, "闸2"),
            (65, "泵2"),
            (80, "闸3")
        ]
        
        # 创建图形
        fig, axes = plt.subplots(2, 1, figsize=(16, 10))
        
        # 子图1：水面线
        ax1 = axes[0]
        line_water, = ax1.plot([], [], 'b-', linewidth=2, label='水面线')
        line_bed, = ax1.plot(x, z, 'k-', linewidth=1, label='河底')
        fill = ax1.fill_between(x, z, z, alpha=0.3, color='blue')
        
        # 标记结构物
        for pos, name in structures:
            ax1.axvline(pos, color='gray', linestyle='--', alpha=0.5)
            ax1.text(pos, ax1.get_ylim()[1]*0.95, name, ha='center', fontsize=9)
        
        ax1.set_xlim([0, 100])
        ax1.set_ylim([z.min()-0.5, z.max()+8])
        ax1.set_ylabel('高程 (m)', fontsize=11)
        ax1.set_title(title, fontsize=13, fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        time_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes,
                            verticalalignment='top', fontsize=11,
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # 子图2：流量分布
        ax2 = axes[1]
        line_Q, = ax2.plot([], [], 'g-', linewidth=2, label='流量')
        
        for pos, name in structures:
            ax2.axvline(pos, color='gray', linestyle='--', alpha=0.5)
        
        ax2.set_xlim([0, 100])
        ax2.set_ylim([0, 20])
        ax2.set_xlabel('距离 (km)', fontsize=11)
        ax2.set_ylabel('流量 (m³/s)', fontsize=11)
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        
        def init():
            line_water.set_data([], [])
            line_Q.set_data([], [])
            return line_water, line_Q
        
        def animate(frame):
            # 更新水面线
            water_surface = z + h_history[frame, :]
            line_water.set_data(x, water_surface)
            
            # 更新流量
            line_Q.set_data(x, Q_history[frame, :])
            
            # 更新时间
            time_text.set_text(f't = {times[frame]:.0f} s = {times[frame]/60:.1f} min')
            
            return line_water, line_Q
        
        # 创建动画
        from matplotlib.animation import FuncAnimation
        
        # 每5帧取1帧
        frames = range(0, len(times), 5)
        anim = FuncAnimation(fig, animate, init_func=init, frames=frames,
                           interval=100, blit=False)
        
        # 保存
        anim.save(filename, writer='pillow', fps=10, dpi=100)
        plt.close()
        
        print(f"  ✓ 动画已保存: {filename}")


def main():
    """主函数"""
    # 创建测试对象
    test = ComprehensiveDisturbanceTest()
    
    # 运行所有场景
    scenarios = [
        test.scenario_1_upstream_flow_jump,
        test.scenario_2_gate_regulation,
        test.scenario_3_pump_control,
        test.scenario_4_downstream_disturbance,
        test.scenario_5_combined_disturbances
    ]
    
    results = []
    
    for i, scenario_func in enumerate(scenarios, 1):
        print(f"\n{'=' * 80}")
        print(f"运行场景 {i}/{len(scenarios)}")
        print(f"{'=' * 80}")
        
        times, h_history, Q_history, title = scenario_func()
        results.append((times, h_history, Q_history, title))
        
        # 生成动画
        filename = f"animation_{title}.gif"
        test.create_animation(times, h_history, Q_history, title, filename)
        
        # 重新初始化系统（为下一个场景准备）
        if i < len(scenarios):
            test.setup_system()
    
    print(f"\n{'=' * 80}")
    print("全部场景测试完成！")
    print(f"{'=' * 80}")
    
    return results


if __name__ == "__main__":
    results = main()
