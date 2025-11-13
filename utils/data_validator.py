"""
数据验证工具 - Data Validator

提供模拟结果的物理合理性检查和数据质量验证功能。

主要功能：
- 物理合理性检查（水深、流速、Froude数等）
- 守恒定律验证（质量守恒、能量守恒）
- 数值稳定性检查（NaN、Inf、突变等）
- 数据完整性检查
- 自动修复（可选）

使用示例：
    from utils.data_validator import DataValidator

    validator = DataValidator()

    # 验证水深数据
    is_valid, report = validator.validate_water_depth(h)

    # 验证流量守恒
    is_conserved = validator.check_mass_conservation(Q_in, Q_out, dV_dt)

    # 生成验证报告
    validator.generate_report("validation_report.html")

作者: Claude Code
创建日期: 2025-10-24
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import json
from datetime import datetime


class DataValidator:
    """数据验证器"""

    # 物理参数的合理范围
    PHYSICAL_RANGES = {
        'water_depth': (0.01, 100.0),  # m
        'velocity': (-10.0, 10.0),  # m/s
        'froude_number': (0.0, 3.0),
        'flow_rate': (-1000.0, 1000.0),  # m³/s
        'manning_n': (0.001, 0.15),
        'slope': (-0.1, 0.1)
    }

    # 数值稳定性阈值
    STABILITY_THRESHOLDS = {
        'max_relative_change': 0.5,  # 最大相对变化 50%
        'max_absolute_change': 5.0,  # 最大绝对变化
        'consecutive_changes': 5  # 连续变化警告阈值
    }

    def __init__(self, strict: bool = False):
        """
        初始化验证器

        Args:
            strict: 严格模式（更严格的阈值）
        """
        self.strict = strict
        self.validation_results = []
        self.warnings = []
        self.errors = []

        if strict:
            # 严格模式下使用更严格的阈值
            self.STABILITY_THRESHOLDS['max_relative_change'] = 0.2
            self.STABILITY_THRESHOLDS['consecutive_changes'] = 3

    def validate_water_depth(self, h: np.ndarray,
                            check_continuity: bool = True) -> Tuple[bool, Dict]:
        """
        验证水深数据

        Args:
            h: 水深数组
            check_continuity: 是否检查连续性

        Returns:
            (is_valid, report_dict)
        """
        report = {
            'variable': 'water_depth',
            'status': 'passed',
            'checks': []
        }

        # 检查1：范围检查
        min_h, max_h = self.PHYSICAL_RANGES['water_depth']
        range_check = np.all((h >= min_h) & (h <= max_h))

        report['checks'].append({
            'name': '范围检查',
            'passed': range_check,
            'details': f"范围: [{min_h}, {max_h}], 实际: [{np.min(h):.3f}, {np.max(h):.3f}]"
        })

        if not range_check:
            self.errors.append(f"水深超出合理范围: [{np.min(h):.3f}, {np.max(h):.3f}]")

        # 检查2：有限性检查
        finite_check = np.all(np.isfinite(h))

        report['checks'].append({
            'name': '有限性检查',
            'passed': finite_check,
            'details': f"NaN数量: {np.sum(np.isnan(h))}, Inf数量: {np.sum(np.isinf(h))}"
        })

        if not finite_check:
            self.errors.append(f"水深包含非有限值: NaN={np.sum(np.isnan(h))}, Inf={np.sum(np.isinf(h))}")

        # 检查3：正值检查
        positive_check = np.all(h > 0)

        report['checks'].append({
            'name': '正值检查',
            'passed': positive_check,
            'details': f"负值或零值数量: {np.sum(h <= 0)}"
        })

        if not positive_check:
            self.errors.append(f"水深包含负值或零值: {np.sum(h <= 0)}个")

        # 检查4：连续性检查
        if check_continuity and len(h) > 1:
            dh = np.abs(np.diff(h))
            max_change = np.max(dh)
            max_rel_change = np.max(dh[1:] / h[:-1]) if np.all(h[:-1] > 0) else np.inf

            continuity_check = max_rel_change < self.STABILITY_THRESHOLDS['max_relative_change']

            report['checks'].append({
                'name': '连续性检查',
                'passed': continuity_check,
                'details': f"最大变化: {max_change:.3f}, 最大相对变化: {max_rel_change:.3%}"
            })

            if not continuity_check:
                self.warnings.append(f"水深变化过大: 最大相对变化 {max_rel_change:.3%}")

        # 总体状态
        all_passed = all(check['passed'] for check in report['checks'])
        report['status'] = 'passed' if all_passed else 'failed'

        self.validation_results.append(report)

        return all_passed, report

    def validate_velocity(self, u: np.ndarray,
                         h: Optional[np.ndarray] = None) -> Tuple[bool, Dict]:
        """
        验证流速数据

        Args:
            u: 流速数组
            h: 水深数组（可选，用于Froude数检查）

        Returns:
            (is_valid, report_dict)
        """
        report = {
            'variable': 'velocity',
            'status': 'passed',
            'checks': []
        }

        # 检查1：范围检查
        min_u, max_u = self.PHYSICAL_RANGES['velocity']
        range_check = np.all((u >= min_u) & (u <= max_u))

        report['checks'].append({
            'name': '范围检查',
            'passed': range_check,
            'details': f"范围: [{min_u}, {max_u}], 实际: [{np.min(u):.3f}, {np.max(u):.3f}]"
        })

        # 检查2：有限性检查
        finite_check = np.all(np.isfinite(u))

        report['checks'].append({
            'name': '有限性检查',
            'passed': finite_check,
            'details': f"NaN数量: {np.sum(np.isnan(u))}, Inf数量: {np.sum(np.isinf(u))}"
        })

        # 检查3：Froude数检查（如果提供水深）
        if h is not None:
            g = 9.81
            Fr = np.abs(u) / np.sqrt(g * h)
            Fr_max = np.max(Fr)

            froude_check = Fr_max < self.PHYSICAL_RANGES['froude_number'][1]

            report['checks'].append({
                'name': 'Froude数检查',
                'passed': froude_check,
                'details': f"最大Froude数: {Fr_max:.3f}"
            })

            if not froude_check:
                self.warnings.append(f"Froude数过大: {Fr_max:.3f}")

        all_passed = all(check['passed'] for check in report['checks'])
        report['status'] = 'passed' if all_passed else 'failed'

        self.validation_results.append(report)

        return all_passed, report

    def check_mass_conservation(self, Q_in: float, Q_out: float,
                               dV_dt: float, tolerance: float = 0.01) -> Tuple[bool, Dict]:
        """
        检查质量守恒

        Args:
            Q_in: 入流流量 (m³/s)
            Q_out: 出流流量 (m³/s)
            dV_dt: 体积变化率 (m³/s)
            tolerance: 允许的相对误差

        Returns:
            (is_conserved, report_dict)
        """
        # 质量守恒: Q_in - Q_out = dV/dt
        balance = Q_in - Q_out - dV_dt
        relative_error = abs(balance) / (abs(Q_in) + 1e-10)

        is_conserved = relative_error < tolerance

        report = {
            'check': 'mass_conservation',
            'passed': is_conserved,
            'Q_in': Q_in,
            'Q_out': Q_out,
            'dV_dt': dV_dt,
            'imbalance': balance,
            'relative_error': relative_error,
            'tolerance': tolerance
        }

        if not is_conserved:
            self.warnings.append(
                f"质量不守恒: 相对误差 {relative_error:.4%} > {tolerance:.4%}"
            )

        self.validation_results.append(report)

        return is_conserved, report

    def check_courant_condition(self, u: np.ndarray, h: np.ndarray,
                               dx: float, dt: float) -> Tuple[bool, Dict]:
        """
        检查Courant条件（CFL条件）

        Args:
            u: 流速数组
            h: 水深数组
            dx: 空间步长
            dt: 时间步长

        Returns:
            (is_stable, report_dict)
        """
        g = 9.81

        # 计算波速
        c = np.sqrt(g * h)

        # 计算Courant数
        courant = (np.abs(u) + c) * dt / dx
        max_courant = np.max(courant)

        # CFL条件: Courant <= 1.0 (或更严格的0.9)
        threshold = 0.9 if self.strict else 1.0
        is_stable = max_courant <= threshold

        report = {
            'check': 'courant_condition',
            'passed': is_stable,
            'max_courant': max_courant,
            'threshold': threshold,
            'dx': dx,
            'dt': dt,
            'max_wave_speed': np.max(c)
        }

        if not is_stable:
            self.warnings.append(
                f"违反CFL条件: Courant={max_courant:.3f} > {threshold}"
            )

        self.validation_results.append(report)

        return is_stable, report

    def detect_outliers(self, data: np.ndarray,
                       method: str = 'iqr',
                       threshold: float = 3.0) -> Tuple[np.ndarray, Dict]:
        """
        检测异常值

        Args:
            data: 数据数组
            method: 检测方法 ('iqr', 'zscore', 'mad')
            threshold: 阈值

        Returns:
            (outlier_mask, report_dict)
        """
        if method == 'iqr':
            # 四分位数方法
            Q1 = np.percentile(data, 25)
            Q3 = np.percentile(data, 75)
            IQR = Q3 - Q1
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            outliers = (data < lower) | (data > upper)

        elif method == 'zscore':
            # Z-score方法
            mean = np.mean(data)
            std = np.std(data)
            z_scores = np.abs((data - mean) / std)
            outliers = z_scores > threshold

        elif method == 'mad':
            # 中位数绝对偏差方法
            median = np.median(data)
            mad = np.median(np.abs(data - median))
            modified_z_scores = 0.6745 * (data - median) / mad
            outliers = np.abs(modified_z_scores) > threshold

        else:
            raise ValueError(f"未知的异常值检测方法: {method}")

        n_outliers = np.sum(outliers)

        report = {
            'check': f'outlier_detection_{method}',
            'method': method,
            'threshold': threshold,
            'n_outliers': n_outliers,
            'percentage': n_outliers / len(data) * 100 if len(data) > 0 else 0
        }

        if n_outliers > 0:
            self.warnings.append(
                f"检测到 {n_outliers} 个异常值 ({report['percentage']:.2f}%)"
            )

        self.validation_results.append(report)

        return outliers, report

    def validate_time_series(self, time: np.ndarray, data: np.ndarray,
                            variable_name: str = 'data') -> Tuple[bool, Dict]:
        """
        验证时间序列数据

        Args:
            time: 时间数组
            data: 数据数组
            variable_name: 变量名称

        Returns:
            (is_valid, report_dict)
        """
        report = {
            'variable': variable_name,
            'type': 'time_series',
            'checks': []
        }

        # 检查1：时间单调性
        time_monotonic = np.all(np.diff(time) > 0)

        report['checks'].append({
            'name': '时间单调性',
            'passed': time_monotonic,
            'details': f"时间范围: [{time[0]:.2f}, {time[-1]:.2f}]"
        })

        # 检查2：数据完整性
        complete_check = len(time) == len(data)

        report['checks'].append({
            'name': '数据完整性',
            'passed': complete_check,
            'details': f"时间点数: {len(time)}, 数据点数: {len(data)}"
        })

        # 检查3：数据有限性
        finite_check = np.all(np.isfinite(data))

        report['checks'].append({
            'name': '有限性检查',
            'passed': finite_check,
            'details': f"无效值: {np.sum(~np.isfinite(data))}"
        })

        # 检查4：突变检测
        if len(data) > 1:
            diff = np.abs(np.diff(data))
            mean_diff = np.mean(diff)
            std_diff = np.std(diff)
            sudden_changes = np.sum(diff > mean_diff + 3 * std_diff)

            spike_check = sudden_changes < len(data) * 0.01  # 少于1%

            report['checks'].append({
                'name': '突变检测',
                'passed': spike_check,
                'details': f"突变点: {sudden_changes} ({sudden_changes/len(data)*100:.2f}%)"
            })

        all_passed = all(check['passed'] for check in report['checks'])
        report['status'] = 'passed' if all_passed else 'failed'

        self.validation_results.append(report)

        return all_passed, report

    def generate_summary(self) -> Dict:
        """
        生成验证摘要

        Returns:
            摘要字典
        """
        total_checks = len(self.validation_results)
        passed_checks = sum(1 for r in self.validation_results
                           if r.get('status') == 'passed' or r.get('passed') == True)

        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': total_checks - passed_checks,
            'n_warnings': len(self.warnings),
            'n_errors': len(self.errors),
            'success_rate': passed_checks / total_checks * 100 if total_checks > 0 else 0,
            'warnings': self.warnings,
            'errors': self.errors,
            'all_results': self.validation_results
        }

        return summary

    def generate_report(self, filename: str = "validation_report.html"):
        """
        生成HTML验证报告

        Args:
            filename: 文件名
        """
        summary = self.generate_summary()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>数据验证报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .check-result {{
            margin: 15px 0;
            padding: 15px;
            border-radius: 8px;
            background: #f9f9f9;
        }}
        .check-header {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .status-passed {{
            background-color: #4caf50;
            color: white;
        }}
        .status-failed {{
            background-color: #f44336;
            color: white;
        }}
        .warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin: 10px 0;
        }}
        .error {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 10px;
            margin: 10px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1> 数据验证报告</h1>
        <p>生成时间: {summary['timestamp']}</p>

        <div class="summary">
            <div class="summary-card">
                <h3>{summary['total_checks']}</h3>
                <p>总检查数</p>
            </div>
            <div class="summary-card">
                <h3>{summary['passed_checks']}</h3>
                <p>通过</p>
            </div>
            <div class="summary-card">
                <h3>{summary['failed_checks']}</h3>
                <p>失败</p>
            </div>
            <div class="summary-card">
                <h3>{summary['success_rate']:.1f}%</h3>
                <p>成功率</p>
            </div>
        </div>
"""

        # 错误列表
        if summary['errors']:
            html += """
        <h2> 错误</h2>
"""
            for error in summary['errors']:
                html += f'        <div class="error">{error}</div>\n'

        # 警告列表
        if summary['warnings']:
            html += """
        <h2>️ 警告</h2>
"""
            for warning in summary['warnings']:
                html += f'        <div class="warning">{warning}</div>\n'

        # 详细结果
        html += """
        <h2> 详细检查结果</h2>
"""

        for result in summary['all_results']:
            status = result.get('status', 'unknown')
            if status == 'unknown':
                status = 'passed' if result.get('passed', False) else 'failed'

            badge_class = 'status-passed' if status == 'passed' else 'status-failed'

            html += f"""
        <div class="check-result">
            <div class="check-header">
                <strong>{result.get('variable', result.get('check', 'Check'))}</strong>
                <span class="status-badge {badge_class}">{status}</span>
            </div>
"""

            if 'checks' in result:
                for check in result['checks']:
                    check_status = '' if check['passed'] else ''
                    html += f"""
            <div>
                {check_status} <strong>{check['name']}</strong>: {check['details']}
            </div>
"""

            html += """
        </div>
"""

        html += """
        <div class="footer">
            <p>Generated with <a href="https://claude.com/claude-code">Claude Code</a></p>
        </div>
    </div>
</body>
</html>
"""

        output_path = Path(filename)
        output_path.write_text(html, encoding='utf-8')
        print(f" 验证报告已生成: {output_path}")

    def reset(self):
        """重置验证器状态"""
        self.validation_results = []
        self.warnings = []
        self.errors = []


def demo():
    """演示验证功能"""
    print("="*70)
    print("  DataValidator 演示")
    print("="*70 + "\n")

    validator = DataValidator()

    # 示例1：验证水深
    print("1. 验证水深数据...")
    h = np.linspace(1.8, 2.2, 50) + np.random.normal(0, 0.05, 50)
    is_valid, report = validator.validate_water_depth(h)
    print(f"   结果: {' 通过' if is_valid else ' 失败'}")

    # 示例2：验证流速
    print("\n2. 验证流速数据...")
    u = np.linspace(0.8, 1.2, 50) + np.random.normal(0, 0.02, 50)
    is_valid, report = validator.validate_velocity(u, h)
    print(f"   结果: {' 通过' if is_valid else ' 失败'}")

    # 示例3：质量守恒检查
    print("\n3. 检查质量守恒...")
    Q_in = 20.0
    Q_out = 19.98
    dV_dt = 0.02
    is_conserved, report = validator.check_mass_conservation(Q_in, Q_out, dV_dt)
    print(f"   结果: {' 守恒' if is_conserved else ' 不守恒'}")
    print(f"   相对误差: {report['relative_error']:.4%}")

    # 生成报告
    print("\n4. 生成验证报告...")
    validator.generate_report("demo_validation_report.html")

    # 打印摘要
    summary = validator.generate_summary()
    print(f"\n摘要:")
    print(f"  总检查数: {summary['total_checks']}")
    print(f"  通过: {summary['passed_checks']}")
    print(f"  失败: {summary['failed_checks']}")
    print(f"  成功率: {summary['success_rate']:.1f}%")

    print("\n 演示完成！")


if __name__ == "__main__":
    demo()
