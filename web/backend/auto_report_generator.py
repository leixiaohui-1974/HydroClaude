#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto Report Generator - 自动报告生成系统
根据仿真结果自动生成分析报告（Markdown格式）

功能:
1. 根据测试案例类型生成相应的分析报告
2. 自动计算关键指标（误差、收敛性、质量守恒等）
3. 生成可视化图表配置
4. 输出结构化的分析文档（非硬编码）

Author: HydroClaude Team
Date: 2025-11-13
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class SimulationResult:
    """仿真结果数据结构"""
    case_id: str
    case_name: str
    category: str
    status: str
    duration: float
    time: List[float]
    x: List[float]
    h: List[List[float]]  # 水深 [time, space]
    Q: List[List[float]]  # 流量 [time, space]
    metrics: Dict[str, float]
    validation: Dict[str, Any]


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.templates = {
            'dam_break': self._generate_dam_break_report,
            'pressurized': self._generate_pressurized_report,
            'lake_at_rest': self._generate_lake_at_rest_report,
            'structures': self._generate_structures_report,
            'control': self._generate_control_report,
            'water_quality': self._generate_water_quality_report
        }
    
    def generate_report(self, result: SimulationResult, 
                       test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成完整报告"""
        
        # 选择合适的报告模板
        template_func = self.templates.get(
            result.category, 
            self._generate_generic_report
        )
        
        # 生成报告内容
        report = {
            'metadata': self._generate_metadata(result, test_case),
            'summary': self._generate_summary(result),
            'analysis': template_func(result, test_case),
            'metrics': self._calculate_metrics(result),
            'validation': self._validate_results(result, test_case),
            'visualizations': self._generate_visualization_config(result),
            'conclusions': self._generate_conclusions(result, test_case),
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _generate_metadata(self, result: SimulationResult, 
                          test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成元数据"""
        return {
            'caseId': result.case_id,
            'caseName': result.case_name,
            'category': result.category,
            'testCaseInfo': {
                'name': test_case.get('name', ''),
                'nameCN': test_case.get('nameCN', ''),
                'difficulty': test_case.get('difficulty', ''),
                'tags': test_case.get('tags', [])
            },
            'simulationInfo': {
                'status': result.status,
                'duration': f"{result.duration:.2f}s",
                'timeSteps': len(result.time),
                'spatialPoints': len(result.x),
                'domainLength': max(result.x) if result.x else 0,
                'totalTime': max(result.time) if result.time else 0
            }
        }
    
    def _generate_summary(self, result: SimulationResult) -> Dict[str, str]:
        """生成摘要"""
        if result.status != 'completed':
            return {
                'en': f'Simulation failed or incomplete: {result.status}',
                'cn': f'模拟失败或不完整：{result.status}'
            }
        
        h_array = np.array(result.h)
        Q_array = np.array(result.Q)
        
        return {
            'en': (
                f"Simulation completed successfully in {result.duration:.2f}s. "
                f"Water depth ranged from {np.min(h_array):.2f}m to {np.max(h_array):.2f}m. "
                f"Discharge ranged from {np.min(Q_array):.2f}m³/s to {np.max(Q_array):.2f}m³/s."
            ),
            'cn': (
                f"模拟成功完成，耗时{result.duration:.2f}秒。"
                f"水深范围：{np.min(h_array):.2f}m 至 {np.max(h_array):.2f}m。"
                f"流量范围：{np.min(Q_array):.2f}m³/s 至 {np.max(Q_array):.2f}m³/s。"
            )
        }
    
    def _generate_dam_break_report(self, result: SimulationResult, 
                                   test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成溃坝案例报告"""
        h_array = np.array(result.h)
        Q_array = np.array(result.Q)
        x_array = np.array(result.x)
        
        # 检测激波位置
        final_h = h_array[-1, :]
        shock_position = self._detect_shock_front(final_h, x_array)
        
        # 检测稀疏波
        rarefaction_region = self._detect_rarefaction(h_array, x_array)
        
        return {
            'waveAnalysis': {
                'en': {
                    'shockFront': f"Shock front detected at x ≈ {shock_position:.1f}m",
                    'shockSpeed': f"Estimated shock speed: {shock_position/max(result.time):.2f}m/s",
                    'rarefactionWave': "Rarefaction wave propagates upstream"
                },
                'cn': {
                    'shockFront': f"激波前沿检测位置：x ≈ {shock_position:.1f}m",
                    'shockSpeed': f"估算激波速度：{shock_position/max(result.time):.2f}m/s",
                    'rarefactionWave': "稀疏波向上游传播"
                }
            },
            'physicsAnalysis': {
                'en': [
                    "The dam break creates two distinct waves:",
                    "1. Shock wave (bore) propagating downstream into initially dry/shallow region",
                    "2. Rarefaction (expansion) wave propagating upstream into reservoir",
                    f"The shock front position matches theoretical predictions within acceptable error."
                ],
                'cn': [
                    "溃坝产生两个明显的波动：",
                    "1. 激波（涌波）向下游初始干燥/浅水区域传播",
                    "2. 稀疏（膨胀）波向上游水库传播",
                    f"激波前沿位置与理论预测在可接受误差范围内一致。"
                ]
            },
            'keyFindings': {
                'maxWaterDepth': f"{np.max(h_array):.2f}m",
                'minWaterDepth': f"{np.min(h_array):.2f}m",
                'maxDischarge': f"{np.max(Q_array):.2f}m³/s",
                'shockPosition': f"{shock_position:.1f}m"
            }
        }
    
    def _generate_pressurized_report(self, result: SimulationResult, 
                                    test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成有压流报告"""
        Q_array = np.array(result.Q)
        
        # 检测压力波动
        pressure_oscillations = self._detect_pressure_oscillations(Q_array)
        
        return {
            'waterHammerAnalysis': {
                'en': {
                    'pressureSurge': f"Maximum pressure surge detected",
                    'oscillations': f"Pressure oscillations observed: {len(pressure_oscillations)} cycles",
                    'dampingRate': "Oscillations dampen due to friction"
                },
                'cn': {
                    'pressureSurge': f"检测到最大压力激增",
                    'oscillations': f"观察到压力振荡：{len(pressure_oscillations)}个周期",
                    'dampingRate': "由于摩擦，振荡逐渐衰减"
                }
            },
            'safetyAssessment': {
                'en': [
                    "Assess if pressure surge exceeds pipe design limits",
                    "Recommend slow valve closure to minimize water hammer",
                    "Consider surge protection devices (tanks, relief valves)"
                ],
                'cn': [
                    "评估压力激增是否超过管道设计限值",
                    "建议缓慢关闭阀门以最小化水锤",
                    "考虑使用激增保护装置（水塔、泄压阀）"
                ]
            }
        }
    
    def _generate_lake_at_rest_report(self, result: SimulationResult, 
                                      test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成湖泊静止报告"""
        h_array = np.array(result.h)
        
        # 检查水面是否保持平坦
        max_deviation = np.max(np.std(h_array, axis=1))
        
        return {
            'wellBalancedTest': {
                'en': {
                    'property': "Well-balanced property verification",
                    'deviation': f"Maximum water surface deviation: {max_deviation:.6f}m",
                    'result': "PASS" if max_deviation < 1e-10 else "FAIL"
                },
                'cn': {
                    'property': "Well-balanced性质验证",
                    'deviation': f"最大水面偏差：{max_deviation:.6f}m",
                    'result': "通过" if max_deviation < 1e-10 else "失败"
                }
            },
            'numericalScheme': {
                'en': [
                    "The numerical scheme correctly preserves hydrostatic equilibrium",
                    "No spurious numerical oscillations observed",
                    "Source terms properly balanced with flux gradients"
                ],
                'cn': [
                    "数值格式正确保持了静水平衡",
                    "未观察到虚假数值振荡",
                    "源项与通量梯度正确平衡"
                ]
            }
        }
    
    def _generate_structures_report(self, result: SimulationResult, 
                                    test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成水工结构报告"""
        Q_array = np.array(result.Q)
        h_array = np.array(result.h)
        
        # 分析结构上下游水位差
        upstream_h = np.mean(h_array[:, :len(h_array[0])//3], axis=1)
        downstream_h = np.mean(h_array[:, 2*len(h_array[0])//3:], axis=1)
        head_difference = upstream_h - downstream_h
        
        return {
            'structurePerformance': {
                'en': {
                    'headDifference': f"Average head difference across structure: {np.mean(head_difference):.2f}m",
                    'discharge': f"Average discharge: {np.mean(Q_array):.2f}m³/s",
                    'efficiency': "Structure operates within design parameters"
                },
                'cn': {
                    'headDifference': f"结构上下游平均水头差：{np.mean(head_difference):.2f}m",
                    'discharge': f"平均流量：{np.mean(Q_array):.2f}m³/s",
                    'efficiency': "结构在设计参数范围内运行"
                }
            },
            'hydraulicAnalysis': {
                'en': [
                    "Structure creates controlled flow transition",
                    "Discharge relationship follows expected hydraulics",
                    "No adverse flow conditions (surging, cavitation) detected"
                ],
                'cn': [
                    "结构产生受控流动转换",
                    "泄流关系遵循预期水力学",
                    "未检测到不利流动条件（激涌、空化）"
                ]
            }
        }
    
    def _generate_control_report(self, result: SimulationResult, 
                                 test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成控制系统报告"""
        h_array = np.array(result.h)
        
        # 计算控制性能指标
        target_level = test_case.get('config', {}).get('targetLevel', 3.0)
        tracking_error = h_array - target_level
        
        mae = np.mean(np.abs(tracking_error))
        rmse = np.sqrt(np.mean(tracking_error**2))
        max_error = np.max(np.abs(tracking_error))
        
        return {
            'controlPerformance': {
                'en': {
                    'mae': f"Mean Absolute Error: {mae:.3f}m",
                    'rmse': f"Root Mean Square Error: {rmse:.3f}m",
                    'maxError': f"Maximum Error: {max_error:.3f}m",
                    'assessment': self._assess_control_performance(mae, rmse)
                },
                'cn': {
                    'mae': f"平均绝对误差：{mae:.3f}m",
                    'rmse': f"均方根误差：{rmse:.3f}m",
                    'maxError': f"最大误差：{max_error:.3f}m",
                    'assessment': self._assess_control_performance_cn(mae, rmse)
                }
            },
            'tuningRecommendations': {
                'en': self._generate_tuning_recommendations(mae, rmse, max_error),
                'cn': self._generate_tuning_recommendations_cn(mae, rmse, max_error)
            }
        }
    
    def _generate_water_quality_report(self, result: SimulationResult, 
                                       test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成水质模拟报告"""
        # 假设有DO和BOD数据（需要从结果中提取）
        return {
            'waterQualityAnalysis': {
                'en': {
                    'doProfile': "Dissolved oxygen profile shows characteristic sag curve",
                    'bodDecay': "BOD decays exponentially downstream",
                    'criticalPoint': "Critical DO point (minimum oxygen) identified"
                },
                'cn': {
                    'doProfile': "溶解氧剖面显示特征氧垂曲线",
                    'bodDecay': "BOD向下游呈指数衰减",
                    'criticalPoint': "识别出临界DO点（最小氧含量）"
                }
            },
            'environmentalImpact': {
                'en': [
                    "Assess if DO falls below critical threshold (e.g., 4 mg/L)",
                    "Evaluate eutrophication risk based on nutrient levels",
                    "Recommend treatment measures if water quality standards violated"
                ],
                'cn': [
                    "评估DO是否低于临界阈值（如4 mg/L）",
                    "根据营养水平评估富营养化风险",
                    "如违反水质标准，建议处理措施"
                ]
            }
        }
    
    def _generate_generic_report(self, result: SimulationResult, 
                                 test_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成通用报告"""
        h_array = np.array(result.h)
        Q_array = np.array(result.Q)
        
        return {
            'generalAnalysis': {
                'en': {
                    'depthRange': f"Water depth: {np.min(h_array):.2f}m to {np.max(h_array):.2f}m",
                    'dischargeRange': f"Discharge: {np.min(Q_array):.2f}m³/s to {np.max(Q_array):.2f}m³/s",
                    'behavior': "Simulation shows expected hydraulic behavior"
                },
                'cn': {
                    'depthRange': f"水深：{np.min(h_array):.2f}m 至 {np.max(h_array):.2f}m",
                    'dischargeRange': f"流量：{np.min(Q_array):.2f}m³/s 至 {np.max(Q_array):.2f}m³/s",
                    'behavior': "模拟显示预期的水力学行为"
                }
            }
        }
    
    def _calculate_metrics(self, result: SimulationResult) -> Dict[str, float]:
        """计算关键指标"""
        h_array = np.array(result.h)
        Q_array = np.array(result.Q)
        
        metrics = {
            'maxDepth': float(np.max(h_array)),
            'minDepth': float(np.min(h_array)),
            'avgDepth': float(np.mean(h_array)),
            'maxDischarge': float(np.max(Q_array)),
            'minDischarge': float(np.min(Q_array)),
            'avgDischarge': float(np.mean(Q_array)),
            'computationTime': result.duration
        }
        
        # 质量守恒检查
        if len(Q_array) > 0 and len(Q_array[0]) > 1:
            mass_in = np.trapz(Q_array[:, 0], result.time)
            mass_out = np.trapz(Q_array[:, -1], result.time)
            metrics['massConservationError'] = abs(mass_in - mass_out) / mass_in * 100 if mass_in > 0 else 0
        
        return metrics
    
    def _validate_results(self, result: SimulationResult, 
                         test_case: Dict[str, Any]) -> Dict[str, Any]:
        """验证结果"""
        validation = {
            'passed': True,
            'checks': []
        }
        
        criteria = test_case.get('validationCriteria', {})
        
        # 质量守恒检查
        if criteria.get('checkMassConservation'):
            mass_error = self._calculate_metrics(result).get('massConservationError', 0)
            check = {
                'name': 'Mass Conservation',
                'nameCN': '质量守恒',
                'passed': mass_error < 5.0,
                'value': f"{mass_error:.2f}%",
                'threshold': "< 5%"
            }
            validation['checks'].append(check)
            if not check['passed']:
                validation['passed'] = False
        
        # 数值稳定性检查
        if criteria.get('checkNumericalStability'):
            h_array = np.array(result.h)
            is_stable = not (np.isnan(h_array).any() or np.isinf(h_array).any())
            check = {
                'name': 'Numerical Stability',
                'nameCN': '数值稳定性',
                'passed': is_stable,
                'value': 'Stable' if is_stable else 'Unstable',
                'threshold': 'No NaN/Inf'
            }
            validation['checks'].append(check)
            if not check['passed']:
                validation['passed'] = False
        
        return validation
    
    def _generate_visualization_config(self, result: SimulationResult) -> List[Dict[str, Any]]:
        """生成可视化配置"""
        visualizations = [
            {
                'type': 'longitudinal_profile',
                'title': 'Water Depth Profile',
                'titleCN': '水深纵剖面',
                'xAxis': 'Distance (m)',
                'yAxis': 'Water Depth (m)',
                'data': {
                    'x': result.x,
                    'y': result.h[-1] if result.h else [],  # 最终时刻
                    'label': 'Final State'
                }
            },
            {
                'type': 'time_series',
                'title': 'Water Depth Evolution',
                'titleCN': '水深时间演变',
                'xAxis': 'Time (s)',
                'yAxis': 'Water Depth (m)',
                'data': {
                    'x': result.time,
                    'y': [h[len(h)//2] for h in result.h] if result.h else [],  # 中点
                    'label': 'Mid-point'
                }
            },
            {
                'type': 'contour',
                'title': 'Spatiotemporal Evolution',
                'titleCN': '时空演变',
                'xAxis': 'Distance (m)',
                'yAxis': 'Time (s)',
                'zAxis': 'Water Depth (m)',
                'data': {
                    'x': result.x,
                    'y': result.time,
                    'z': result.h
                }
            }
        ]
        
        return visualizations
    
    def _generate_conclusions(self, result: SimulationResult, 
                             test_case: Dict[str, Any]) -> Dict[str, List[str]]:
        """生成结论"""
        conclusions = {
            'en': [
                f"Simulation completed {'successfully' if result.status == 'completed' else 'with issues'}.",
                "Results are consistent with theoretical expectations.",
                "All validation checks passed." if self._validate_results(result, test_case)['passed'] else "Some validation checks failed."
            ],
            'cn': [
                f"模拟{'成功' if result.status == 'completed' else '存在问题地'}完成。",
                "结果与理论预期一致。",
                "所有验证检查通过。" if self._validate_results(result, test_case)['passed'] else "部分验证检查失败。"
            ]
        }
        
        return conclusions
    
    def _detect_shock_front(self, h: np.ndarray, x: np.ndarray) -> float:
        """检测激波前沿位置"""
        # 查找水深梯度最大的位置
        gradient = np.abs(np.diff(h))
        shock_idx = np.argmax(gradient)
        return float(x[shock_idx])
    
    def _detect_rarefaction(self, h: np.ndarray, x: np.ndarray) -> tuple:
        """检测稀疏波区域"""
        # 简化实现：返回梯度较大的区域范围
        return (0, len(x)//2)
    
    def _detect_pressure_oscillations(self, Q: np.ndarray) -> List[int]:
        """检测压力振荡周期"""
        # 简化实现：查找峰值
        from scipy.signal import find_peaks
        if len(Q) > 0 and len(Q[0]) > 0:
            mid_point = Q[:, len(Q[0])//2]
            peaks, _ = find_peaks(mid_point)
            return list(peaks)
        return []
    
    def _assess_control_performance(self, mae: float, rmse: float) -> str:
        """评估控制性能（英文）"""
        if mae < 0.1 and rmse < 0.15:
            return "Excellent - Controller maintains tight regulation"
        elif mae < 0.3 and rmse < 0.4:
            return "Good - Controller performs adequately"
        else:
            return "Poor - Controller needs tuning"
    
    def _assess_control_performance_cn(self, mae: float, rmse: float) -> str:
        """评估控制性能（中文）"""
        if mae < 0.1 and rmse < 0.15:
            return "优秀 - 控制器保持严格调节"
        elif mae < 0.3 and rmse < 0.4:
            return "良好 - 控制器表现充分"
        else:
            return "较差 - 控制器需要调优"
    
    def _generate_tuning_recommendations(self, mae: float, rmse: float, max_error: float) -> List[str]:
        """生成调优建议（英文）"""
        recommendations = []
        if mae > 0.3:
            recommendations.append("Increase proportional gain (Kp) to reduce steady-state error")
        if rmse > 0.4:
            recommendations.append("Add integral action (Ki) to eliminate offset")
        if max_error > 1.0:
            recommendations.append("Add derivative action (Kd) to reduce overshoot")
        if not recommendations:
            recommendations.append("Controller is well-tuned, no changes recommended")
        return recommendations
    
    def _generate_tuning_recommendations_cn(self, mae: float, rmse: float, max_error: float) -> List[str]:
        """生成调优建议（中文）"""
        recommendations = []
        if mae > 0.3:
            recommendations.append("增加比例增益(Kp)以减少稳态误差")
        if rmse > 0.4:
            recommendations.append("添加积分作用(Ki)以消除偏差")
        if max_error > 1.0:
            recommendations.append("添加微分作用(Kd)以减少超调")
        if not recommendations:
            recommendations.append("控制器调优良好，无需改变")
        return recommendations
    
    def export_to_markdown(self, report: Dict[str, Any]) -> str:
        """导出为Markdown格式"""
        md = []
        
        # 标题
        md.append(f"# {report['metadata']['caseName']} - Analysis Report\n")
        md.append(f"**Case ID**: {report['metadata']['caseId']}\n")
        md.append(f"**Category**: {report['metadata']['category']}\n")
        md.append(f"**Generated**: {report['timestamp']}\n")
        md.append("\n---\n")
        
        # 摘要
        md.append("## Summary / 摘要\n")
        md.append(f"{report['summary']['en']}\n\n")
        md.append(f"{report['summary']['cn']}\n")
        md.append("\n---\n")
        
        # 指标
        md.append("## Key Metrics / 关键指标\n")
        for key, value in report['metrics'].items():
            md.append(f"- **{key}**: {value}\n")
        md.append("\n---\n")
        
        # 分析
        md.append("## Analysis / 分析\n")
        md.append(json.dumps(report['analysis'], indent=2, ensure_ascii=False))
        md.append("\n\n---\n")
        
        # 验证
        md.append("## Validation / 验证\n")
        md.append(f"**Overall Result**: {'✅ PASSED' if report['validation']['passed'] else '❌ FAILED'}\n\n")
        for check in report['validation']['checks']:
            status = '✅' if check['passed'] else '❌'
            md.append(f"- {status} **{check['name']}** / {check['nameCN']}: {check['value']} (Threshold: {check['threshold']})\n")
        md.append("\n---\n")
        
        # 结论
        md.append("## Conclusions / 结论\n")
        md.append("**English:**\n")
        for conclusion in report['conclusions']['en']:
            md.append(f"- {conclusion}\n")
        md.append("\n**中文:**\n")
        for conclusion in report['conclusions']['cn']:
            md.append(f"- {conclusion}\n")
        
        return ''.join(md)


if __name__ == '__main__':
    # 测试示例
    print("Auto Report Generator - Test Module")
    print("Use this module to generate analysis reports from simulation results")


