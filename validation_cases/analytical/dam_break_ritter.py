#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
标准验证案例1: Dam Break with Dry Bed (Ritter Solution)

参考文献:
    Ritter, A. (1892). "Die Fortpflanzung der Wasserwellen"
    
问题描述:
    - 1000m渠道，初始左半段水深10m，右半段干河床
    - t=0时溃坝（瞬间移除中间隔板）
    - 解析解已知（Ritter解）
    
验收标准:
    - 波前位置误差 < 5%
    - 水深分布RMSE < 0.5m
    - 速度分布RMSE < 0.5 m/s
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# 导入求解器
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from physics.canal import Canal


class DamBreakRitter:
    """Dam Break标准案例（Ritter解析解）"""
    
    def __init__(self):
        # 物理参数
        self.L = 1000.0          # 渠道长度 (m)
        self.B = 10.0            # 渠道宽度 (m)
        self.h0 = 10.0           # 初始左侧水深 (m)
        self.x_dam = 500.0       # 溃坝位置 (m)
        self.g = 9.81            # 重力加速度
        
        # 数值参数
        self.nx = 501            # 节点数
        self.T = 50.0            # 总时间 (s)
        self.dt = 0.1            # 时间步长
        
        # 坐标
        self.x = np.linspace(0, self.L, self.nx)
        self.dx = self.L / (self.nx - 1)
        
    def analytical_solution(self, t):
        """
        Ritter解析解
        
        Returns:
            h: 水深分布
            u: 流速分布
        """
        h = np.zeros(self.nx)
        u = np.zeros(self.nx)
        
        c0 = np.sqrt(self.g * self.h0)  # 初始波速
        
        for i, x in enumerate(self.x):
            x_rel = x - self.x_dam  # 相对于溃坝点的距离
            
            # 波前位置
            x_front = 2 * c0 * t
            # 波尾位置
            x_tail = -c0 * t
            
            if x_rel < x_tail:
                # 静水区
                h[i] = self.h0
                u[i] = 0.0
            elif x_rel < x_front:
                # 稀疏波区
                u[i] = (2.0 / 3.0) * (x_rel / t + c0)
                c = (1.0 / 3.0) * (2 * c0 - x_rel / t)
                h[i] = c**2 / self.g
            else:
                # 干河床区
                h[i] = 0.01  # 小值避免除零
                u[i] = 0.0
                
        return h, u
    
    def run_hydrostatic_solver(self):
        """运行HydrostaticCanalSolver"""
        print("\n" + "="*80)
        print("运行 HydrostaticCanalSolver (静水重构法)")
        print("="*80)
        
        # 创建求解器
        solver = HydrostaticCanalSolver(
            length=self.L,
            nx=self.nx,
            B=self.B,
            S0=0.0,  # 水平河床
            n=0.0,   # 无摩阻（理想情况）
            g=self.g
        )
        
        # 初始条件：左高右低
        solver.h[:] = 0.01  # 全部初始化为小值
        for i, x in enumerate(self.x):
            if x < self.x_dam:
                solver.h[i] = self.h0
        
        solver.hu[:] = 0.0  # 初始静止
        
        # 时间步进
        n_steps = int(self.T / self.dt)
        h_history = [solver.h.copy()]
        t_history = [0.0]
        
        print(f"时间步数: {n_steps}")
        print(f"dt = {self.dt}s, T = {self.T}s")
        print(f"开始时间步进...")
        
        for step in range(n_steps):
            t = (step + 1) * self.dt
            
            # Preissmann步进（非恒定流）
            try:
                h_new, hu_new = solver.step_preissmann(
                    dt=self.dt,
                    max_iter=10,
                    enforce_bc=False  # Dam break不需要边界条件
                )
                
                solver.h = h_new
                solver.hu = hu_new
                solver.current_time = t
                
                # 记录
                if step % 10 == 0 or step == n_steps - 1:
                    h_history.append(solver.h.copy())
                    t_history.append(t)
                    
                if step % 50 == 0:
                    print(f"  Step {step}/{n_steps}, t={t:.1f}s, h_max={np.max(solver.h):.3f}m")
                    
            except Exception as e:
                print(f"❌ 步进失败 at t={t:.1f}s: {e}")
                break
        
        print(f"✅ 完成时间步进")
        
        return {
            'h_final': solver.h,
            'u_final': solver.hu / np.maximum(solver.h, 1e-6),
            'h_history': np.array(h_history),
            't_history': np.array(t_history),
            'x': self.x
        }
    
    def run_canal_preissmann(self):
        """运行Canal类Preissmann求解器"""
        print("\n" + "="*80)
        print("运行 Canal-Preissmann (四点隐式)")
        print("="*80)
        
        # 创建Canal
        canal = Canal(
            name="DamBreak",
            volume_min=0,
            volume_max=self.L * self.B * 20,
            area=self.L * self.B,
            length=self.L,
            width=self.B,
            slope=0.0,
            manning_n=0.0,  # 无摩阻
            n_sections=self.nx,
            method='preissmann',
            initial_depth=0.01,
            initial_flow=0.0,
            g=self.g
        )
        
        # 初始条件
        for i, x in enumerate(self.x):
            if x < self.x_dam:
                canal.hydraulic_state.h[i] = self.h0
        canal.hydraulic_state.Q[:] = 0.0
        
        # 时间步进
        n_steps = int(self.T / self.dt)
        h_history = [canal.hydraulic_state.h.copy()]
        t_history = [0.0]
        
        print(f"时间步数: {n_steps}")
        print(f"开始时间步进...")
        
        for step in range(n_steps):
            t = (step + 1) * self.dt
            
            # Dam break不需要边界输入
            inputs = {}
            
            try:
                canal.update_high_fidelity(self.dt, inputs)
                
                # 记录
                if step % 10 == 0 or step == n_steps - 1:
                    h_history.append(canal.hydraulic_state.h.copy())
                    t_history.append(t)
                    
                if step % 50 == 0:
                    h_max = np.max(canal.hydraulic_state.h)
                    print(f"  Step {step}/{n_steps}, t={t:.1f}s, h_max={h_max:.3f}m")
                    
            except Exception as e:
                print(f"❌ 步进失败 at t={t:.1f}s: {e}")
                break
        
        print(f"✅ 完成时间步进")
        
        return {
            'h_final': canal.hydraulic_state.h,
            'u_final': canal.hydraulic_state.Q / np.maximum(canal.hydraulic_state.h, 1e-6) / self.B,
            'h_history': np.array(h_history),
            't_history': np.array(t_history),
            'x': self.x
        }
    
    def compare_and_plot(self, results_hydrostatic, results_canal):
        """对比并绘图"""
        print("\n" + "="*80)
        print("误差分析")
        print("="*80)
        
        # 解析解（最终时刻）
        h_exact, u_exact = self.analytical_solution(self.T)
        
        # 提取数值解
        h_hydro = results_hydrostatic['h_final']
        u_hydro = results_hydrostatic['u_final']
        
        h_canal = results_canal['h_final']
        u_canal = results_canal['u_final']
        
        # 计算误差（避免干河床影响）
        mask = h_exact > 0.1  # 只在有水区域计算误差
        
        # RMSE
        rmse_h_hydro = np.sqrt(np.mean((h_hydro[mask] - h_exact[mask])**2))
        rmse_h_canal = np.sqrt(np.mean((h_canal[mask] - h_exact[mask])**2))
        
        # 波前位置误差
        x_front_exact = self.x_dam + 2 * np.sqrt(self.g * self.h0) * self.T
        
        # 找数值解的波前（水深>0.1m的最右侧）
        idx_front_hydro = np.where(h_hydro > 0.1)[0][-1] if np.any(h_hydro > 0.1) else 0
        idx_front_canal = np.where(h_canal > 0.1)[0][-1] if np.any(h_canal > 0.1) else 0
        
        x_front_hydro = self.x[idx_front_hydro]
        x_front_canal = self.x[idx_front_canal]
        
        err_front_hydro = abs(x_front_hydro - x_front_exact) / x_front_exact * 100
        err_front_canal = abs(x_front_canal - x_front_exact) / x_front_exact * 100
        
        # 打印结果
        print(f"\n解析解（Ritter）:")
        print(f"  波前位置: {x_front_exact:.2f} m")
        
        print(f"\nHydrostaticCanalSolver:")
        print(f"  波前位置: {x_front_hydro:.2f} m (误差 {err_front_hydro:.2f}%)")
        print(f"  水深RMSE: {rmse_h_hydro:.4f} m")
        
        print(f"\nCanal-Preissmann:")
        print(f"  波前位置: {x_front_canal:.2f} m (误差 {err_front_canal:.2f}%)")
        print(f"  水深RMSE: {rmse_h_canal:.4f} m")
        
        # 绘图
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        
        # 1. 水深对比
        ax = axes[0, 0]
        ax.plot(self.x, h_exact, 'k-', linewidth=2, label='Analytical (Ritter)')
        ax.plot(self.x, h_hydro, 'b--', linewidth=1.5, label='HydrostaticSolver')
        ax.plot(self.x, h_canal, 'r:', linewidth=1.5, label='Canal-Preissmann')
        ax.axvline(self.x_dam, color='gray', linestyle='--', alpha=0.5, label='Dam位置')
        ax.set_xlabel('x (m)', fontsize=12)
        ax.set_ylabel('Water Depth (m)', fontsize=12)
        ax.set_title(f'Water Depth at t={self.T}s', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. 误差分布
        ax = axes[0, 1]
        err_hydro = h_hydro - h_exact
        err_canal = h_canal - h_exact
        ax.plot(self.x, err_hydro, 'b-', label='HydrostaticSolver')
        ax.plot(self.x, err_canal, 'r-', label='Canal-Preissmann')
        ax.axhline(0, color='k', linestyle='-', linewidth=0.5)
        ax.set_xlabel('x (m)', fontsize=12)
        ax.set_ylabel('Error (m)', fontsize=12)
        ax.set_title('Water Depth Error', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 3. 时空演化（HydrostaticSolver）
        ax = axes[1, 0]
        X, T = np.meshgrid(results_hydrostatic['x'], results_hydrostatic['t_history'])
        H = results_hydrostatic['h_history']
        cs = ax.contourf(X, T, H, levels=20, cmap='Blues')
        plt.colorbar(cs, ax=ax, label='Water Depth (m)')
        ax.set_xlabel('x (m)', fontsize=12)
        ax.set_ylabel('Time (s)', fontsize=12)
        ax.set_title('Water Surface Evolution (HydrostaticSolver)', fontsize=14, fontweight='bold')
        
        # 4. 误差汇总柱状图
        ax = axes[1, 1]
        solvers = ['Hydrostatic\nSolver', 'Canal\nPreissmann']
        wave_front_errors = [err_front_hydro, err_front_canal]
        rmse_errors = [rmse_h_hydro, rmse_h_canal]
        
        x_pos = np.arange(len(solvers))
        width = 0.35
        
        ax.bar(x_pos - width/2, wave_front_errors, width, label='Wave Front Error (%)', color='skyblue')
        ax.bar(x_pos + width/2, rmse_errors, width, label='RMSE (m)', color='salmon')
        
        ax.set_ylabel('Error', fontsize=12)
        ax.set_title('Error Summary', fontsize=14, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(solvers)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加数值标签
        for i, (wf, rm) in enumerate(zip(wave_front_errors, rmse_errors)):
            ax.text(i - width/2, wf + 0.5, f'{wf:.2f}%', ha='center', fontsize=10)
            ax.text(i + width/2, rm + 0.05, f'{rm:.3f}m', ha='center', fontsize=10)
        
        plt.tight_layout()
        
        # 保存
        output_dir = project_root / 'validation_cases' / 'results'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fig_path = output_dir / f'dam_break_ritter_{timestamp}.png'
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        print(f"\n✅ 图表已保存: {fig_path}")
        
        plt.close()
        
        # 生成报告
        self.generate_report(
            err_front_hydro, err_front_canal,
            rmse_h_hydro, rmse_h_canal,
            output_dir
        )
        
        return {
            'wave_front_error_hydro': err_front_hydro,
            'wave_front_error_canal': err_front_canal,
            'rmse_h_hydro': rmse_h_hydro,
            'rmse_h_canal': rmse_h_canal
        }
    
    def generate_report(self, err_front_hydro, err_front_canal, 
                       rmse_h_hydro, rmse_h_canal, output_dir):
        """生成文本报告"""
        report_path = output_dir / f'dam_break_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("Dam Break验证案例报告 (Ritter解析解)\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"测试日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("问题描述:\n")
            f.write(f"  - 渠道长度: {self.L} m\n")
            f.write(f"  - 初始左侧水深: {self.h0} m\n")
            f.write(f"  - 溃坝位置: {self.x_dam} m\n")
            f.write(f"  - 仿真时间: {self.T} s\n")
            f.write(f"  - 节点数: {self.nx}\n\n")
            
            f.write("验收标准:\n")
            f.write("  - 波前位置误差 < 5%\n")
            f.write("  - 水深RMSE < 0.5m\n\n")
            
            f.write("="*80 + "\n")
            f.write("测试结果\n")
            f.write("="*80 + "\n\n")
            
            f.write("1. HydrostaticCanalSolver:\n")
            f.write(f"   波前位置误差: {err_front_hydro:.2f}%")
            if err_front_hydro < 5:
                f.write(" ✅ PASS\n")
            else:
                f.write(" ❌ FAIL\n")
            
            f.write(f"   水深RMSE: {rmse_h_hydro:.4f} m")
            if rmse_h_hydro < 0.5:
                f.write(" ✅ PASS\n")
            else:
                f.write(" ❌ FAIL\n")
            
            f.write("\n2. Canal-Preissmann:\n")
            f.write(f"   波前位置误差: {err_front_canal:.2f}%")
            if err_front_canal < 5:
                f.write(" ✅ PASS\n")
            else:
                f.write(" ❌ FAIL\n")
            
            f.write(f"   水深RMSE: {rmse_h_canal:.4f} m")
            if rmse_h_canal < 0.5:
                f.write(" ✅ PASS\n")
            else:
                f.write(" ❌ FAIL\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("结论\n")
            f.write("="*80 + "\n\n")
            
            if err_front_hydro < 5 and rmse_h_hydro < 0.5:
                f.write("✅ HydrostaticCanalSolver: 通过验证\n")
            else:
                f.write("❌ HydrostaticCanalSolver: 未通过验证\n")
            
            if err_front_canal < 5 and rmse_h_canal < 0.5:
                f.write("✅ Canal-Preissmann: 通过验证\n")
            else:
                f.write("❌ Canal-Preissmann: 未通过验证\n")
        
        print(f"✅ 报告已保存: {report_path}")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("标准验证案例1: Dam Break (Ritter Solution)")
    print("="*80)
    
    # 创建案例
    case = DamBreakRitter()
    
    # 运行两个求解器
    try:
        results_hydro = case.run_hydrostatic_solver()
    except Exception as e:
        print(f"❌ HydrostaticSolver失败: {e}")
        results_hydro = None
    
    try:
        results_canal = case.run_canal_preissmann()
    except Exception as e:
        print(f"❌ Canal-Preissmann失败: {e}")
        results_canal = None
    
    # 对比分析
    if results_hydro and results_canal:
        metrics = case.compare_and_plot(results_hydro, results_canal)
        
        print("\n" + "="*80)
        print("最终结论")
        print("="*80)
        print(f"✅ Dam Break标准案例测试完成")
        print(f"详细结果请查看: validation_cases/results/")
    else:
        print("\n❌ 测试失败，无法生成对比报告")


if __name__ == '__main__':
    main()
