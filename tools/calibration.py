#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude 参数校准工具 (Parameter Calibration Tool)

支持的功能：
- 多种优化算法 (Nelder-Mead, Powell, BFGS, Differential Evolution)
- 多种目标函数 (RMSE, NSE, MAE, PBIAS)
- 多参数同时校准
- 自动不确定性分析
- 校准报告生成

作者: HydroClaude Team
创建日期: 2025-11-02
"""

import numpy as np
from typing import Dict, List, Tuple, Callable, Optional
import json
from datetime import datetime


class ParameterCalibrator:
    """
    参数校准器

    支持使用观测数据自动校准模型参数
    """

    def __init__(self,
                 model_function: Callable,
                 observed_data: Dict[str, np.ndarray],
                 param_ranges: Dict[str, Tuple[float, float]],
                 objective_function: str = 'RMSE'):
        """
        初始化校准器

        Parameters
        ----------
        model_function : callable
            模型运行函数，接受参数字典，返回模拟结果字典
        observed_data : dict
            观测数据 {'variable': array}
        param_ranges : dict
            参数范围 {'param_name': (min, max)}
        objective_function : str
            目标函数类型: 'RMSE', 'NSE', 'MAE', 'PBIAS'
        """
        self.model_function = model_function
        self.observed_data = observed_data
        self.param_ranges = param_ranges
        self.objective_function = objective_function

        # 优化历史
        self.optimization_history = []
        self.best_params = None
        self.best_score = None
        self.n_evaluations = 0

    def _calculate_objective(self,
                            simulated: np.ndarray,
                            observed: np.ndarray) -> float:
        """
        计算目标函数值

        Parameters
        ----------
        simulated : array
            模拟值
        observed : array
            观测值

        Returns
        -------
        float
            目标函数值 (越小越好，除了NSE越大越好)
        """
        # 移除NaN值
        mask = ~(np.isnan(simulated) | np.isnan(observed))
        sim = simulated[mask]
        obs = observed[mask]

        if len(sim) == 0:
            return np.inf

        if self.objective_function == 'RMSE':
            # 均方根误差
            return np.sqrt(np.mean((sim - obs)**2))

        elif self.objective_function == 'NSE':
            # Nash-Sutcliffe效率系数 (转换为最小化问题)
            numerator = np.sum((obs - sim)**2)
            denominator = np.sum((obs - np.mean(obs))**2)
            if denominator == 0:
                return np.inf
            nse = 1 - numerator / denominator
            return -nse  # 转换为最小化

        elif self.objective_function == 'MAE':
            # 平均绝对误差
            return np.mean(np.abs(sim - obs))

        elif self.objective_function == 'PBIAS':
            # 百分比偏差
            pbias = 100 * np.sum(obs - sim) / np.sum(obs)
            return np.abs(pbias)

        else:
            raise ValueError(f"未知的目标函数: {self.objective_function}")

    def _objective_wrapper(self, params_array: np.ndarray) -> float:
        """
        目标函数包装器（用于优化算法）

        Parameters
        ----------
        params_array : array
            参数数组

        Returns
        -------
        float
            总目标函数值
        """
        # 转换为参数字典
        param_names = list(self.param_ranges.keys())
        params_dict = {name: params_array[i] for i, name in enumerate(param_names)}

        # 检查参数范围
        for name, value in params_dict.items():
            min_val, max_val = self.param_ranges[name]
            if value < min_val or value > max_val:
                return 1e10  # 返回大值表示不可行解

        # 运行模型
        try:
            results = self.model_function(params_dict)
        except Exception as e:
            print(f"   模型运行错误: {e}")
            return 1e10

        # 计算所有变量的目标函数
        total_score = 0.0
        n_vars = 0

        for var_name, obs_data in self.observed_data.items():
            if var_name in results:
                sim_data = results[var_name]
                score = self._calculate_objective(sim_data, obs_data)
                if not np.isinf(score):
                    total_score += score
                    n_vars += 1

        if n_vars == 0:
            return 1e10

        # 平均目标函数值
        avg_score = total_score / n_vars

        # 记录历史
        self.n_evaluations += 1
        self.optimization_history.append({
            'params': params_dict.copy(),
            'score': avg_score
        })

        # 更新最优解
        if self.best_score is None or avg_score < self.best_score:
            self.best_score = avg_score
            self.best_params = params_dict.copy()
            print(f"   第 {self.n_evaluations} 次评估: 新最优解 = {avg_score:.6f}")
            print(f"    参数: {params_dict}")

        return avg_score

    def calibrate_nelder_mead(self,
                             initial_params: Optional[Dict] = None,
                             max_iter: int = 200) -> Dict:
        """
        使用Nelder-Mead算法校准参数

        Parameters
        ----------
        initial_params : dict, optional
            初始参数值，默认使用范围中点
        max_iter : int
            最大迭代次数

        Returns
        -------
        dict
            校准结果
        """
        from scipy.optimize import minimize

        print("=" * 70)
        print("开始参数校准 (Nelder-Mead 算法)")
        print("=" * 70)

        # 初始参数
        param_names = list(self.param_ranges.keys())
        if initial_params is None:
            x0 = np.array([(self.param_ranges[name][0] + self.param_ranges[name][1]) / 2
                          for name in param_names])
        else:
            x0 = np.array([initial_params[name] for name in param_names])

        print(f"初始参数: {dict(zip(param_names, x0))}")
        print(f"目标函数: {self.objective_function}")
        print(f"最大迭代: {max_iter}")
        print()

        # 优化
        result = minimize(
            self._objective_wrapper,
            x0,
            method='Nelder-Mead',
            options={'maxiter': max_iter, 'disp': False}
        )

        # 结果
        optimal_params = {name: result.x[i] for i, name in enumerate(param_names)}

        print()
        print("=" * 70)
        print("校准完成!")
        print("=" * 70)
        print(f"目标函数值: {result.fun:.6f}")
        print(f"迭代次数: {result.nit}")
        print(f"函数评估次数: {self.n_evaluations}")
        print(f"收敛状态: {result.message}")
        print()
        print("最优参数:")
        for name, value in optimal_params.items():
            print(f"  {name:20s}: {value:.6f}")

        return {
            'optimal_params': optimal_params,
            'objective_value': result.fun,
            'n_iterations': result.nit,
            'n_evaluations': self.n_evaluations,
            'success': result.success,
            'message': result.message,
            'method': 'Nelder-Mead',
            'history': self.optimization_history
        }

    def calibrate_differential_evolution(self,
                                        max_iter: int = 100,
                                        population_size: int = 15) -> Dict:
        """
        使用差分进化算法校准参数

        差分进化是全局优化算法，不需要初始值，但计算量较大

        Parameters
        ----------
        max_iter : int
            最大迭代次数
        population_size : int
            种群大小

        Returns
        -------
        dict
            校准结果
        """
        from scipy.optimize import differential_evolution

        print("=" * 70)
        print("开始参数校准 (Differential Evolution 算法)")
        print("=" * 70)

        param_names = list(self.param_ranges.keys())
        bounds = [self.param_ranges[name] for name in param_names]

        print(f"参数范围:")
        for name, (min_val, max_val) in zip(param_names, bounds):
            print(f"  {name:20s}: [{min_val:.6f}, {max_val:.6f}]")
        print(f"目标函数: {self.objective_function}")
        print(f"最大迭代: {max_iter}")
        print(f"种群大小: {population_size}")
        print()

        # 优化
        result = differential_evolution(
            self._objective_wrapper,
            bounds,
            maxiter=max_iter,
            popsize=population_size,
            disp=False,
            seed=42
        )

        # 结果
        optimal_params = {name: result.x[i] for i, name in enumerate(param_names)}

        print()
        print("=" * 70)
        print("校准完成!")
        print("=" * 70)
        print(f"目标函数值: {result.fun:.6f}")
        print(f"迭代次数: {result.nit}")
        print(f"函数评估次数: {self.n_evaluations}")
        print(f"收敛状态: {result.message}")
        print()
        print("最优参数:")
        for name, value in optimal_params.items():
            print(f"  {name:20s}: {value:.6f}")

        return {
            'optimal_params': optimal_params,
            'objective_value': result.fun,
            'n_iterations': result.nit,
            'n_evaluations': self.n_evaluations,
            'success': result.success,
            'message': result.message,
            'method': 'Differential Evolution',
            'history': self.optimization_history
        }

    def analyze_uncertainty(self,
                           optimal_params: Dict,
                           n_samples: int = 100,
                           perturbation: float = 0.1) -> Dict:
        """
        分析参数不确定性

        使用蒙特卡洛方法在最优参数附近采样，评估不确定性

        Parameters
        ----------
        optimal_params : dict
            最优参数
        n_samples : int
            采样数量
        perturbation : float
            扰动幅度 (相对于参数范围的比例)

        Returns
        -------
        dict
            不确定性分析结果
        """
        print()
        print("=" * 70)
        print("参数不确定性分析")
        print("=" * 70)
        print(f"采样数量: {n_samples}")
        print(f"扰动幅度: {perturbation * 100:.1f}% of range")
        print()

        param_names = list(optimal_params.keys())
        objective_values = []
        parameter_samples = {name: [] for name in param_names}

        for i in range(n_samples):
            # 生成扰动参数
            perturbed_params = {}
            for name in param_names:
                min_val, max_val = self.param_ranges[name]
                param_range = max_val - min_val
                optimal_val = optimal_params[name]

                # 添加高斯扰动
                perturbation_val = np.random.normal(0, perturbation * param_range)
                new_val = optimal_val + perturbation_val

                # 确保在范围内
                new_val = np.clip(new_val, min_val, max_val)

                perturbed_params[name] = new_val
                parameter_samples[name].append(new_val)

            # 评估目标函数
            params_array = np.array([perturbed_params[name] for name in param_names])
            obj_val = self._objective_wrapper(params_array)
            objective_values.append(obj_val)

            if (i + 1) % 20 == 0:
                print(f"  已完成 {i+1}/{n_samples} 个样本")

        # 统计分析
        obj_array = np.array(objective_values)
        param_stats = {}

        print()
        print("参数不确定性统计:")
        print(f"{'参数名':<20s} {'最优值':<12s} {'均值':<12s} {'标准差':<12s} {'95% CI':<25s}")
        print("-" * 85)

        for name in param_names:
            samples = np.array(parameter_samples[name])
            mean_val = np.mean(samples)
            std_val = np.std(samples)
            ci_lower = np.percentile(samples, 2.5)
            ci_upper = np.percentile(samples, 97.5)

            param_stats[name] = {
                'optimal': optimal_params[name],
                'mean': mean_val,
                'std': std_val,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper
            }

            print(f"{name:<20s} {optimal_params[name]:>11.6f} {mean_val:>11.6f} "
                  f"{std_val:>11.6f} [{ci_lower:.6f}, {ci_upper:.6f}]")

        print()
        print(f"目标函数不确定性:")
        print(f"  最优值: {np.min(obj_array):.6f}")
        print(f"  均值: {np.mean(obj_array):.6f}")
        print(f"  标准差: {np.std(obj_array):.6f}")
        print(f"  95% CI: [{np.percentile(obj_array, 2.5):.6f}, {np.percentile(obj_array, 97.5):.6f}]")

        return {
            'parameter_stats': param_stats,
            'objective_stats': {
                'optimal': np.min(obj_array),
                'mean': np.mean(obj_array),
                'std': np.std(obj_array),
                'ci_lower': np.percentile(obj_array, 2.5),
                'ci_upper': np.percentile(obj_array, 97.5)
            },
            'samples': parameter_samples,
            'objective_values': objective_values
        }

    def save_results(self,
                     results: Dict,
                     uncertainty: Optional[Dict] = None,
                     output_file: str = 'calibration_results.json') -> None:
        """
        保存校准结果

        Parameters
        ----------
        results : dict
            校准结果
        uncertainty : dict, optional
            不确定性分析结果
        output_file : str
            输出文件路径
        """
        output_data = {
            'calibration_info': {
                'timestamp': datetime.now().isoformat(),
                'objective_function': self.objective_function,
                'observed_variables': list(self.observed_data.keys()),
                'n_observations': {var: len(data) for var, data in self.observed_data.items()}
            },
            'calibration_results': {
                'optimal_params': results['optimal_params'],
                'objective_value': float(results['objective_value']),
                'n_iterations': int(results['n_iterations']),
                'n_evaluations': int(results['n_evaluations']),
                'method': results['method'],
                'success': bool(results['success'])
            }
        }

        if uncertainty is not None:
            output_data['uncertainty_analysis'] = {
                'parameter_stats': uncertainty['parameter_stats'],
                'objective_stats': uncertainty['objective_stats']
            }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print()
        print(f" 结果已保存到: {output_file}")

    def plot_convergence(self,
                        save_file: str = 'calibration_convergence.png') -> None:
        """
        绘制收敛曲线

        Parameters
        ----------
        save_file : str
            保存文件路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print(" 需要安装matplotlib才能绘图")
            return

        if len(self.optimization_history) == 0:
            print(" 没有优化历史数据")
            return

        # 提取目标函数值
        iterations = np.arange(len(self.optimization_history))
        scores = np.array([h['score'] for h in self.optimization_history])

        # 计算累积最优值
        cumulative_best = np.minimum.accumulate(scores)

        fig, ax = plt.subplots(figsize=(10, 6))

        # 绘制所有评估点
        ax.scatter(iterations, scores, c='lightblue', alpha=0.5, s=20, label='Evaluations')

        # 绘制累积最优值
        ax.plot(iterations, cumulative_best, 'r-', linewidth=2, label='Best so far')

        ax.set_xlabel('Iteration', fontsize=12)
        ax.set_ylabel('Objective Function Value', fontsize=12)
        ax.set_title('Calibration Convergence', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f" 收敛曲线已保存到: {save_file}")

    def plot_parameter_uncertainty(self,
                                  uncertainty: Dict,
                                  save_file: str = 'parameter_uncertainty.png') -> None:
        """
        绘制参数不确定性图

        Parameters
        ----------
        uncertainty : dict
            不确定性分析结果
        save_file : str
            保存文件路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print(" 需要安装matplotlib才能绘图")
            return

        param_stats = uncertainty['parameter_stats']
        param_names = list(param_stats.keys())
        n_params = len(param_names)

        fig, axes = plt.subplots(1, n_params, figsize=(4*n_params, 4))
        if n_params == 1:
            axes = [axes]

        for i, name in enumerate(param_names):
            ax = axes[i]
            stats = param_stats[name]
            samples = uncertainty['samples'][name]

            # 直方图
            ax.hist(samples, bins=30, alpha=0.7, color='skyblue', edgecolor='black')

            # 最优值线
            ax.axvline(stats['optimal'], color='red', linestyle='--', linewidth=2,
                      label=f"Optimal: {stats['optimal']:.4f}")

            # 均值线
            ax.axvline(stats['mean'], color='green', linestyle='--', linewidth=2,
                      label=f"Mean: {stats['mean']:.4f}")

            # 95% CI
            ax.axvspan(stats['ci_lower'], stats['ci_upper'], alpha=0.2, color='yellow',
                      label=f"95% CI")

            ax.set_xlabel(name, fontsize=11)
            ax.set_ylabel('Frequency', fontsize=11)
            ax.set_title(f'{name}\n(std={stats["std"]:.4f})', fontsize=12, fontweight='bold')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f" 参数不确定性图已保存到: {save_file}")


def create_example_calibration():
    """
    创建一个示例校准案例

    演示如何使用校准工具
    """
    print("=" * 70)
    print("HydroClaude 参数校准示例")
    print("=" * 70)
    print()

    # 生成合成观测数据
    print("生成合成观测数据...")
    np.random.seed(42)

    # 真实参数
    true_kd_20 = 0.20
    true_SOD_20 = 1.5

    # 模拟"真实"观测数据
    n_obs = 50
    time = np.linspace(0, 10, n_obs)  # 10天

    # 简化的DO衰减模型
    DO_true = 8.0 * np.exp(-true_kd_20 * time) - true_SOD_20 * time * 0.1
    DO_true = np.maximum(DO_true, 2.0)  # 最小DO

    # 添加观测噪声
    DO_obs = DO_true + np.random.normal(0, 0.3, n_obs)

    print(f"  生成了 {n_obs} 个DO观测点")
    print(f"  真实参数: kd_20={true_kd_20}, SOD_20={true_SOD_20}")
    print()

    # 定义模型函数
    def simple_do_model(params):
        """简化的DO模型"""
        kd_20 = params['kd_20']
        SOD_20 = params['SOD_20']

        DO_sim = 8.0 * np.exp(-kd_20 * time) - SOD_20 * time * 0.1
        DO_sim = np.maximum(DO_sim, 0.0)

        return {'DO': DO_sim}

    # 创建校准器
    observed_data = {'DO': DO_obs}
    param_ranges = {
        'kd_20': (0.05, 0.50),
        'SOD_20': (0.5, 3.0)
    }

    calibrator = ParameterCalibrator(
        model_function=simple_do_model,
        observed_data=observed_data,
        param_ranges=param_ranges,
        objective_function='RMSE'
    )

    # 运行校准 (Nelder-Mead)
    results = calibrator.calibrate_nelder_mead(max_iter=100)

    # 不确定性分析
    uncertainty = calibrator.analyze_uncertainty(
        results['optimal_params'],
        n_samples=100,
        perturbation=0.1
    )

    # 保存结果
    calibrator.save_results(results, uncertainty, 'example_calibration_results.json')

    # 绘图
    calibrator.plot_convergence('example_calibration_convergence.png')
    calibrator.plot_parameter_uncertainty(uncertainty, 'example_parameter_uncertainty.png')

    print()
    print("=" * 70)
    print("示例完成!")
    print("=" * 70)
    print()
    print("对比真实参数:")
    print(f"  kd_20:  真实={true_kd_20:.4f}, 校准={results['optimal_params']['kd_20']:.4f}, "
          f"误差={abs(results['optimal_params']['kd_20']-true_kd_20)/true_kd_20*100:.2f}%")
    print(f"  SOD_20: 真实={true_SOD_20:.4f}, 校准={results['optimal_params']['SOD_20']:.4f}, "
          f"误差={abs(results['optimal_params']['SOD_20']-true_SOD_20)/true_SOD_20*100:.2f}%")


if __name__ == '__main__':
    # 运行示例
    create_example_calibration()
