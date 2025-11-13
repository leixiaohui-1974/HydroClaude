"""
稳定性评价模块

用于定量评估明渠数值求解算法的稳定性

作者: Claude
日期: 2025-10-21
"""

import numpy as np
from typing import Dict, List, Tuple


class StabilityEvaluator:
    """
    数值稳定性评价器

    评价指标：
    1. 数值振荡指数（Oscillation Index）
    2. 质量守恒误差（Mass Conservation Error）
    3. 物理合理性指数（Physical Validity Index）
    4. 收敛性指数（Convergence Index）
    5. 综合稳定性评分（Overall Stability Score）
    """

    def __init__(self):
        self.results = {}

    def evaluate(self, time: np.ndarray, h_history: List[np.ndarray],
                 Q_history: List[np.ndarray], canal_params: dict,
                 method_name: str = "Unknown") -> Dict:
        """
        综合评估数值稳定性

        Args:
            time: 时间数组
            h_history: 水深历史记录列表
            Q_history: 流量历史记录列表
            canal_params: 渠道参数字典 {'length', 'width', 'slope', 'manning_n', 'nx'}
            method_name: 求解器名称

        Returns:
            评估结果字典
        """

        result = {
            'method': method_name,
            'success': True,
            'message': ''
        }

        # 检查NaN和Inf
        has_nan, has_inf = self._check_validity(h_history, Q_history)
        if has_nan or has_inf:
            result['success'] = False
            result['message'] = f'数值错误: NaN={has_nan}, Inf={has_inf}'
            result['score'] = 0.0
            return result

        # 计算各项指标
        result['oscillation_index'] = self._compute_oscillation_index(time, h_history, Q_history)
        result['mass_error'] = self._compute_mass_conservation_error(h_history, Q_history, canal_params)
        result['physical_validity'] = self._compute_physical_validity(h_history, Q_history, canal_params)
        result['convergence_index'] = self._compute_convergence_index(time, h_history, Q_history)

        # 综合评分（0-100分）
        result['score'] = self._compute_overall_score(result)

        # 判断是否稳定（不影响success标志）
        if result['score'] >= 70:
            result['stability'] = '稳定'
            result['pass_test'] = True
        elif result['score'] >= 50:
            result['stability'] = '基本稳定'
            result['pass_test'] = False
        else:
            result['stability'] = '不稳定'
            result['pass_test'] = False

        self.results[method_name] = result
        return result

    def _check_validity(self, h_history, Q_history) -> Tuple[bool, bool]:
        """检查是否有NaN或Inf"""
        h_array = np.array([h for h in h_history])
        Q_array = np.array([Q for Q in Q_history])

        has_nan = np.isnan(h_array).any() or np.isnan(Q_array).any()
        has_inf = np.isinf(h_array).any() or np.isinf(Q_array).any()

        return has_nan, has_inf

    def _compute_oscillation_index(self, time, h_history, Q_history) -> float:
        """
        计算数值振荡指数（0-1，越小越好）

        方法：计算时间序列的二阶差分归一化标准差
        """

        # 提取上游和下游水位时间序列
        hu_series = np.array([h[0] for h in h_history])
        hd_series = np.array([h[-1] for h in h_history])

        # 计算二阶差分（检测高频振荡）
        if len(hu_series) < 3:
            return 0.0

        d2_hu = np.diff(hu_series, n=2)
        d2_hd = np.diff(hd_series, n=2)

        # 归一化标准差
        hu_mean = np.abs(hu_series).mean() + 1e-6
        hd_mean = np.abs(hd_series).mean() + 1e-6

        osc_hu = np.std(d2_hu) / hu_mean
        osc_hd = np.std(d2_hd) / hd_mean

        # 平均振荡指数
        oscillation_index = (osc_hu + osc_hd) / 2

        return min(oscillation_index, 1.0)

    def _compute_mass_conservation_error(self, h_history, Q_history, canal_params) -> float:
        """
        计算质量守恒误差（相对误差，%）

        理论：总水量应该只因边界条件净流入/流出而变化
        """

        B = canal_params['width']
        dx = canal_params['length'] / (canal_params['nx'] - 1)

        # 计算每个时刻的总水量（体积）
        volumes = []
        for h in h_history:
            volume = np.sum(h * B * dx)  # V = Σ(h * B * dx)
            volumes.append(volume)

        volumes = np.array(volumes)

        # 计算水量变化率
        if len(volumes) > 1:
            dV = volumes[-1] - volumes[0]
            V_mean = np.mean(volumes)

            # 相对变化率（%）
            if V_mean > 1e-6:
                mass_error = abs(dV) / V_mean * 100
            else:
                mass_error = 0.0
        else:
            mass_error = 0.0

        return mass_error

    def _compute_physical_validity(self, h_history, Q_history, canal_params) -> float:
        """
        计算物理合理性指数（0-1，越大越好）

        检查：
        1. 水深非负
        2. 流量非负
        3. Froude数合理（< 2.0）
        4. 流速合理（< 10 m/s）
        """

        B = canal_params['width']
        g = 9.81

        validity_score = 1.0
        penalty_count = 0

        for h, Q in zip(h_history, Q_history):
            # 1. 检查水深
            if (h < 0).any():
                validity_score -= 0.2
                penalty_count += 1

            if (h < 0.01).any():  # 水深过小
                validity_score -= 0.1
                penalty_count += 1

            # 2. 检查流量
            if (Q < 0).any():
                validity_score -= 0.2
                penalty_count += 1

            # 3. 检查Froude数
            for i in range(len(h)):
                if h[i] > 1e-3:
                    A = h[i] * B
                    V = Q[i] / A if A > 0 else 0
                    Fr = V / np.sqrt(g * h[i]) if h[i] > 0 else 0

                    if Fr > 2.0:  # Froude数过大（超临界流）
                        validity_score -= 0.05
                        penalty_count += 1
                        break

            # 4. 检查流速
            for i in range(len(h)):
                if h[i] > 1e-3:
                    A = h[i] * B
                    V = Q[i] / A if A > 0 else 0

                    if V > 10.0:  # 流速过大
                        validity_score -= 0.05
                        penalty_count += 1
                        break

        return max(validity_score, 0.0)

    def _compute_convergence_index(self, time, h_history, Q_history) -> float:
        """
        计算收敛性指数（0-1，越大越好）

        方法：检查后半段时间序列的变化趋势
        """

        if len(time) < 50:
            return 0.5  # 数据不足，给中等评分

        # 提取后半段数据
        mid_idx = len(time) // 2

        hu_series = np.array([h[0] for h in h_history])
        hd_series = np.array([h[-1] for h in h_history])

        hu_late = hu_series[mid_idx:]
        hd_late = hd_series[mid_idx:]

        # 计算后半段的标准差（归一化）
        hu_std = np.std(hu_late) / (np.abs(np.mean(hu_late)) + 1e-6)
        hd_std = np.std(hd_late) / (np.abs(np.mean(hd_late)) + 1e-6)

        # 标准差越小，收敛性越好
        convergence_hu = 1.0 / (1.0 + 10 * hu_std)
        convergence_hd = 1.0 / (1.0 + 10 * hd_std)

        convergence_index = (convergence_hu + convergence_hd) / 2

        return convergence_index

    def _compute_overall_score(self, result: dict) -> float:
        """
        计算综合稳定性评分（0-100）

        权重分配：
        - 振荡指数: 30%（越小越好）
        - 质量守恒: 20%（越小越好）
        - 物理合理性: 30%（越大越好）
        - 收敛性: 20%（越大越好）
        """

        # 振荡指数得分（反向，越小越好）
        osc_score = max(0, 100 * (1.0 - result['oscillation_index']))

        # 质量守恒得分（误差<5%为满分）
        if result['mass_error'] < 5.0:
            mass_score = 100
        elif result['mass_error'] < 20.0:
            mass_score = 100 - (result['mass_error'] - 5.0) * 5
        else:
            mass_score = 0

        # 物理合理性得分
        phys_score = result['physical_validity'] * 100

        # 收敛性得分
        conv_score = result['convergence_index'] * 100

        # 加权平均
        overall_score = (
            0.30 * osc_score +
            0.20 * mass_score +
            0.30 * phys_score +
            0.20 * conv_score
        )

        return overall_score

    def print_report(self, method_name: str = None):
        """打印评估报告"""

        if method_name:
            methods = [method_name]
        else:
            methods = list(self.results.keys())

        print("=" * 80)
        print("数值稳定性评估报告")
        print("=" * 80)

        for method in methods:
            if method not in self.results:
                print(f"\n方法 '{method}' 未找到评估结果")
                continue

            result = self.results[method]

            print(f"\n### {method} ###")
            print(f"{'='*60}")

            if not result['success']:
                print(f" 数值计算失败: {result['message']}")
                if 'score' in result:
                    print(f"综合评分: {result['score']:.1f}/100")
                continue

            print(f"稳定性等级: {result['stability']}")
            print(f"综合评分: {result['score']:.1f}/100")
            print(f"\n详细指标:")
            print(f"  1. 振荡指数: {result['oscillation_index']:.6f} (越小越好，<0.01为优秀)")
            print(f"  2. 质量守恒误差: {result['mass_error']:.2f}% (越小越好，<5%为优秀)")
            print(f"  3. 物理合理性: {result['physical_validity']:.3f} (越大越好，>0.9为优秀)")
            print(f"  4. 收敛性指数: {result['convergence_index']:.3f} (越大越好，>0.8为优秀)")

            # 评价建议
            print(f"\n评价:")
            if result['score'] >= 90:
                print(f"   优秀 - 该方法数值稳定性极佳，推荐使用")
            elif result['score'] >= 70:
                print(f"   良好 - 该方法数值稳定，可以使用")
            elif result['score'] >= 50:
                print(f"  ️  一般 - 该方法基本稳定，建议优化参数")
            else:
                print(f"   较差 - 该方法存在稳定性问题，不推荐使用")

        print("\n" + "=" * 80)

    def compare_methods(self):
        """对比多个方法"""

        if len(self.results) < 2:
            print("至少需要两个方法才能对比")
            return

        print("\n" + "=" * 80)
        print("方法对比")
        print("=" * 80)

        # 创建对比表格
        methods = list(self.results.keys())

        print(f"\n{'方法':<20} {'综合评分':<12} {'振荡指数':<12} {'质量误差':<12} {'物理性':<10} {'收敛性':<10} {'稳定性':<10}")
        print("-" * 90)

        for method in methods:
            result = self.results[method]
            if result['success']:
                print(f"{method:<20} {result['score']:>8.1f}/100  "
                      f"{result['oscillation_index']:>10.6f}  "
                      f"{result['mass_error']:>9.2f}%  "
                      f"{result['physical_validity']:>8.3f}  "
                      f"{result['convergence_index']:>8.3f}  "
                      f"{result['stability']:<10}")
            else:
                print(f"{method:<20} {'失败':>11}  {'N/A':<12} {'N/A':<12} {'N/A':<10} {'N/A':<10} {'不稳定':<10}")

        # 推荐最佳方法
        valid_methods = [(m, r['score']) for m, r in self.results.items() if r['success']]
        if valid_methods:
            best_method = max(valid_methods, key=lambda x: x[1])
            print(f"\n推荐方法: {best_method[0]} (评分: {best_method[1]:.1f}/100)")

        print("=" * 80)

    def is_stable(self, method_name: str, min_score: float = 70.0) -> bool:
        """
        判断某个方法是否稳定

        Args:
            method_name: 方法名称
            min_score: 最低评分要求（默认70分）

        Returns:
            是否稳定
        """
        if method_name not in self.results:
            return False

        result = self.results[method_name]
        if not result['success']:
            return False

        return result.get('pass_test', False) or result['score'] >= min_score

    def get_stable_methods(self, min_score: float = 70.0) -> List[str]:
        """
        获取所有稳定的方法

        Args:
            min_score: 最低评分要求

        Returns:
            稳定方法列表
        """
        stable = []
        for method, result in self.results.items():
            if not result['success']:
                continue
            if result.get('pass_test', False) or result['score'] >= min_score:
                stable.append(method)
        return stable
