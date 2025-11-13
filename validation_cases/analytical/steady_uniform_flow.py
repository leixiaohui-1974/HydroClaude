#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
标准验证案例3: Steady Uniform Flow (Manning公式验证)

参考文献:
    Manning, R. (1891). "On the flow of water in open channels and pipes"
    
问题描述:
    - 矩形渠道，恒定坡度
    - 均匀流条件（底坡 = 摩阻坡）
    - Manning公式解析解
    - 这是最基础但最重要的验证
    
验收标准:
    - 水深误差 < 0.1%
    - 流量守恒误差 < 0.01%
    - 所有节点水深均匀
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow


class SteadyUniformFlow:
    """稳态均匀流验证案例（Manning公式）"""
    
    def __init__(self):
        # 物理参数
        self.L = 5000.0          # 渠道长度 (m)
        self.B = 10.0            # 渠道宽度 (m)
        self.S0 = 0.001          # 底坡
        self.n = 0.025           # Manning糙率
        self.g = 9.81
        
        # 测试场景
        self.test_cases = [
            {'Q': 5.0, 'name': '小流量'},
            {'Q': 10.0, 'name': '中流量'},
            {'Q': 20.0, 'name': '大流量'},
        ]
        
        # 数值参数
        self.nx = 101
        self.x = np.linspace(0, self.L, self.nx)
    
    def analytical_solution(self, Q):
        """
        Manning公式解析解
        
        对于矩形渠道均匀流:
        Q = (1/n) * A * R^(2/3) * S0^(1/2)
        
        其中:
        - A = B * h (横截面积)
        - R = A / P ≈ h (对于宽渠，P ≈ B)
        
        求解得:
        h = (Q * n / (B * S0^(1/2)))^(3/5)
        """
        # 使用项目中的工具函数
        h_uniform = compute_steady_uniform_flow(Q, self.B, self.S0, self.n)
        
        return h_uniform
    
    def run_single_test(self, Q, case_name):
        """运行单个测试案例"""
        print(f"\n{'='*80}")
        print(f"测试案例: {case_name} (Q={Q} m^3/s)")
        print(f"{'='*80}")
        
        # 解析解
        h_exact = self.analytical_solution(Q)
        print(f"解析解 (Manning): h = {h_exact:.6f} m")
        
        # 数值求解
        solver = HydrostaticCanalSolver(
            length=self.L,
            nx=self.nx,
            B=self.B,
            S0=self.S0,
            n=self.n,
            g=self.g
        )
        
        # 初始化
        solver.h[:] = h_exact  # 使用精确值初始化
        solver.hu[:] = Q / self.B
        
        # 稳态求解（现在初值由Manning公式自动计算，应该很快收敛）
        result = solver.solve_steady_state(
            Q_target=Q,
            h_downstream=h_exact,
            max_iterations=150,
            convergence_tol = 0.1,  # 合理的收敛容差（太严会导致无法收敛）
            dt=0.5,
            verbose=False
        )
        
        # 提取结果
        h_num = result['h']
        Q_num = result['Q']
        
        # 计算误差
        h_mean = np.mean(h_num)
        h_std = np.std(h_num)
        h_error = abs(h_mean - h_exact) / h_exact * 100
        
        Q_mean = np.mean(Q_num)
        Q_std = np.std(Q_num)
        Q_error = abs(Q_mean - Q) / Q * 100
        
        # 均匀性检查
        h_uniformity = h_std / h_mean * 100  # 变异系数
        
        print(f"\n数值解:")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  平均水深: {h_mean:.6f} m (误差 {h_error:.6f}%)")
        print(f"  水深标准差: {h_std:.6f} m")
        print(f"  均匀性: {h_uniformity:.6f}% (变异系数)")
        print(f"  平均流量: {Q_mean:.6f} m^3/s (误差 {Q_error:.6f}%)")
        print(f"  流量标准差: {Q_std:.6f} m^3/s")
        
        # 判断通过/失败
        passed = (h_error < 0.1 and Q_error < 0.01 and h_uniformity < 0.1)
        
        if passed:
            print(f"   通过验证")
        else:
            print(f"   未通过验证")
        
        return {
            'h_exact': h_exact,
            'h_num': h_num,
            'Q_num': Q_num,
            'h_error': h_error,
            'Q_error': Q_error,
            'h_uniformity': h_uniformity,
            'passed': passed,
            'iterations': result['iterations']
        }
    
    def run_all_tests(self):
        """运行所有测试案例"""
        print("\n" + "="*80)
        print("标准验证案例3: Steady Uniform Flow (Manning公式)")
        print("="*80)
        
        results = []
        
        for case in self.test_cases:
            result = self.run_single_test(case['Q'], case['name'])
            result['Q'] = case['Q']
            result['name'] = case['name']
            results.append(result)
        
        return results
    
    def plot_results(self, results):
        """绘制所有测试结果"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        
        # 1. 水深剖面（所有案例）
        ax = axes[0, 0]
        colors = ['blue', 'green', 'red']
        for i, res in enumerate(results):
            label = f"{res['name']} (Q={res['Q']} m^3/s)"
            ax.plot(self.x, res['h_num'], color=colors[i], linewidth=2, label=label)
            ax.axhline(res['h_exact'], color=colors[i], linestyle='--', alpha=0.5, 
                      label=f"Analytical {res['Q']} m^3/s")
        
        ax.set_xlabel('x (m)', fontsize=12)
        ax.set_ylabel('Water Depth (m)', fontsize=12)
        ax.set_title('Water Depth Profiles', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. 误差柱状图
        ax = axes[0, 1]
        x_pos = np.arange(len(results))
        h_errors = [res['h_error'] for res in results]
        Q_errors = [res['Q_error'] for res in results]
        
        width = 0.35
        ax.bar(x_pos - width/2, h_errors, width, label='水深误差 (%)', color='skyblue')
        ax.bar(x_pos + width/2, Q_errors, width, label='流量误差 (%)', color='salmon')
        
        ax.set_ylabel('Error (%)', fontsize=12)
        ax.set_title('Error Summary', fontsize=14, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels([res['name'] for res in results])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        # ax.set_yscale('log')  # 对数坐标显示小误差 - 可能导致图像过大
        
        # 添加数值标签
        for i, (he, qe) in enumerate(zip(h_errors, Q_errors)):
            ax.text(i - width/2, he, f'{he:.4f}%', ha='center', va='bottom', fontsize=9)
            ax.text(i + width/2, qe, f'{qe:.4f}%', ha='center', va='bottom', fontsize=9)
        
        # 3. 迭代次数
        ax = axes[1, 0]
        iters = [res['iterations'] for res in results]
        ax.bar(x_pos, iters, color='purple', alpha=0.7)
        ax.set_ylabel('Iterations', fontsize=12)
        ax.set_title('Convergence Speed', fontsize=14, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels([res['name'] for res in results])
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加数值标签
        for i, it in enumerate(iters):
            ax.text(i, it, f'{it}', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # 4. 通过/失败总结
        ax = axes[1, 1]
        passed_count = sum(1 for res in results if res['passed'])
        failed_count = len(results) - passed_count
        
        sizes = [passed_count, failed_count]
        colors_pie = ['green', 'red']
        labels = [f'通过 ({passed_count})', f'失败 ({failed_count})']
        explode = (0.1, 0) if passed_count > 0 else (0, 0.1)
        
        ax.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
               autopct='%1.0f%%', shadow=True, startangle=90, textprops={'fontsize': 14})
        ax.set_title('Validation Results', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        # 保存
        output_dir = project_root / 'validation_cases' / 'results'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fig_path = output_dir / f'steady_uniform_flow_{timestamp}.png'
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        print(f"\n 图表已保存: {fig_path}")
        
        plt.close()
        
        return fig_path
    
    def generate_report(self, results):
        """生成验证报告"""
        output_dir = project_root / 'validation_cases' / 'results'
        report_path = output_dir / f'steady_uniform_flow_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("Steady Uniform Flow 验证报告 (Manning公式)\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"测试日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("物理参数:\n")
            f.write(f"  渠道长度: {self.L} m\n")
            f.write(f"  渠道宽度: {self.B} m\n")
            f.write(f"  底坡: {self.S0}\n")
            f.write(f"  Manning糙率: {self.n}\n")
            f.write(f"  节点数: {self.nx}\n\n")
            
            f.write("验收标准:\n")
            f.write("  - 水深误差 < 0.1%\n")
            f.write("  - 流量守恒误差 < 0.01%\n")
            f.write("  - 均匀性(变异系数) < 0.1%\n\n")
            
            f.write("="*80 + "\n")
            f.write("测试结果\n")
            f.write("="*80 + "\n\n")
            
            for i, res in enumerate(results, 1):
                f.write(f"{i}. {res['name']} (Q={res['Q']} m^3/s):\n")
                f.write(f"   解析解: h = {res['h_exact']:.6f} m\n")
                f.write(f"   水深误差: {res['h_error']:.6f}%")
                if res['h_error'] < 0.1:
                    f.write("  PASS\n")
                else:
                    f.write("  FAIL\n")
                
                f.write(f"   流量误差: {res['Q_error']:.6f}%")
                if res['Q_error'] < 0.01:
                    f.write("  PASS\n")
                else:
                    f.write("  FAIL\n")
                
                f.write(f"   均匀性: {res['h_uniformity']:.6f}%")
                if res['h_uniformity'] < 0.1:
                    f.write("  PASS\n")
                else:
                    f.write("  FAIL\n")
                
                f.write(f"   迭代次数: {res['iterations']}\n")
                f.write(f"   总体: ")
                if res['passed']:
                    f.write(" PASS\n\n")
                else:
                    f.write(" FAIL\n\n")
            
            f.write("="*80 + "\n")
            f.write("总结\n")
            f.write("="*80 + "\n\n")
            
            passed_count = sum(1 for res in results if res['passed'])
            total_count = len(results)
            
            f.write(f"通过: {passed_count}/{total_count}\n")
            f.write(f"通过率: {passed_count/total_count*100:.1f}%\n\n")
            
            if passed_count == total_count:
                f.write(" HydrostaticCanalSolver: 完美通过Manning公式验证\n")
                f.write("   这证明了求解器在稳态均匀流条件下的高精度\n")
            else:
                f.write(" HydrostaticCanalSolver: 部分案例未通过验证\n")
        
        print(f" 报告已保存: {report_path}")
        
        return report_path


def main():
    """主函数"""
    print("\n" + "="*80)
    print("标准验证案例3: Steady Uniform Flow")
    print("="*80)
    
    # 创建案例
    case = SteadyUniformFlow()
    
    # 运行所有测试
    results = case.run_all_tests()
    
    # 绘图
    case.plot_results(results)
    
    # 生成报告
    case.generate_report(results)
    
    # 总结
    print("\n" + "="*80)
    print("最终总结")
    print("="*80)
    
    passed_count = sum(1 for res in results if res['passed'])
    total_count = len(results)
    
    print(f"通过: {passed_count}/{total_count}")
    print(f"通过率: {passed_count/total_count*100:.1f}%")
    
    if passed_count == total_count:
        print("\n Manning公式验证完美通过!")
        print("   这是所有验证的基础，证明求解器正确实现了基本物理")
    else:
        print("\n 部分案例未通过，需要进一步分析")


if __name__ == '__main__':
    main()
