#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
结果自动分析模块（专业版）
对标商业软件：自动生成专业分析报告、可视化、质量检查

功能：
1. 结果质量评估
2. 水力特性分析
3. 关键事件检测
4. 统计指标计算
5. 专业图表生成
6. 完整报告生成

参考商业软件：
- HEC-RAS: 结果汇总表、统计分析、图表模板
- MIKE: 时空分析、关键指标提取、专业报告
- InfoWorks: 性能指标、验证检查、可视化模板

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math
from datetime import datetime
import json


class ResultQuality(Enum):
    """结果质量评级"""
    EXCELLENT = "excellent"   # 优秀
    GOOD = "good"            # 良好
    ACCEPTABLE = "acceptable"  # 可接受
    POOR = "poor"            # 较差
    FAILED = "failed"        # 失败


@dataclass
class HydraulicCharacteristics:
    """水力特性"""
    # 基本统计
    h_mean: float = 0.0
    h_min: float = 0.0
    h_max: float = 0.0
    h_std: float = 0.0
    
    Q_mean: float = 0.0
    Q_min: float = 0.0
    Q_max: float = 0.0
    Q_std: float = 0.0
    
    V_mean: float = 0.0
    V_min: float = 0.0
    V_max: float = 0.0
    V_std: float = 0.0
    
    # Froude数
    Fr_mean: float = 0.0
    Fr_min: float = 0.0
    Fr_max: float = 0.0
    
    # 流态分类
    subcritical_percentage: float = 0.0  # 亚临界流比例
    critical_percentage: float = 0.0     # 临界流比例
    supercritical_percentage: float = 0.0  # 超临界流比例
    
    # 水跃检测
    hydraulic_jumps: List[Dict[str, Any]] = field(default_factory=list)
    
    # 激波检测
    shock_waves: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ConservationMetrics:
    """守恒性指标"""
    mass_conservation: Dict[str, float] = field(default_factory=dict)
    momentum_conservation: Dict[str, float] = field(default_factory=dict)
    energy_dissipation: Dict[str, float] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    computation_time: float = 0.0
    time_steps: int = 0
    iterations: int = 0
    convergence_rate: float = 0.0
    efficiency: float = 0.0  # 时间步/秒


@dataclass
class ResultAnalysisReport:
    """结果分析报告"""
    # 基本信息
    task_id: str = ""
    timestamp: str = ""
    quality: ResultQuality = ResultQuality.ACCEPTABLE
    quality_score: float = 0.0  # 0-100
    
    # 水力特性
    hydraulics: HydraulicCharacteristics = field(default_factory=HydraulicCharacteristics)
    
    # 守恒性
    conservation: ConservationMetrics = field(default_factory=ConservationMetrics)
    
    # 性能
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # 关键事件
    key_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # 警告和问题
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # 可视化建议
    visualization_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    
    # 总结
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class ProfessionalResultAnalyzer:
    """
    专业结果分析器
    
    对标商业软件的结果分析功能
    """
    
    def __init__(self):
        """初始化分析器"""
        self.g = 9.81  # 重力加速度
        
        # 质量评分标准
        self.quality_thresholds = {
            'excellent': 95,
            'good': 85,
            'acceptable': 70,
            'poor': 50
        }
        
        # 水跃检测阈值
        self.jump_threshold = 0.3  # 水深变化率
        
        # 激波检测阈值
        self.shock_threshold = 0.5  # 流速梯度
    
    def analyze(self, result: Dict[str, Any], config: Dict[str, Any] = None) -> ResultAnalysisReport:
        """
        全面分析仿真结果
        
        Args:
            result: 仿真结果字典
            config: 仿真配置（可选，用于深度分析）
            
        Returns:
            分析报告
        """
        report = ResultAnalysisReport(
            task_id=result.get('task_id', 'unknown'),
            timestamp=datetime.now().isoformat()
        )
        
        # 提取数据
        x = np.array(result.get('x', []))
        time = np.array(result.get('time', []))
        h = np.array(result.get('h', []))  # [time_idx, x_idx]
        Q = np.array(result.get('Q', []))
        V = np.array(result.get('V', []))
        
        if len(x) == 0 or len(time) == 0 or len(h) == 0:
            report.errors.append("结果数据为空")
            report.quality = ResultQuality.FAILED
            return report
        
        # 1. 水力特性分析
        self._analyze_hydraulics(x, time, h, Q, V, report)
        
        # 2. 守恒性检查
        if config:
            self._check_conservation(x, time, h, Q, V, config, report)
        
        # 3. 性能分析
        metrics = result.get('metrics', {})
        self._analyze_performance(metrics, report)
        
        # 4. 关键事件检测
        self._detect_key_events(x, time, h, Q, V, report)
        
        # 5. 质量评估
        self._assess_quality(h, Q, V, report)
        
        # 6. 生成可视化建议
        self._generate_visualization_recommendations(x, time, h, Q, V, report)
        
        # 7. 生成总结和建议
        self._generate_summary(report)
        
        return report
    
    def _analyze_hydraulics(self, x, time, h, Q, V, report):
        """分析水力特性"""
        hydraulics = report.hydraulics
        
        # 基本统计 - 水深
        hydraulics.h_mean = float(np.mean(h))
        hydraulics.h_min = float(np.min(h))
        hydraulics.h_max = float(np.max(h))
        hydraulics.h_std = float(np.std(h))
        
        # 基本统计 - 流量
        hydraulics.Q_mean = float(np.mean(Q))
        hydraulics.Q_min = float(np.min(Q))
        hydraulics.Q_max = float(np.max(Q))
        hydraulics.Q_std = float(np.std(Q))
        
        # 基本统计 - 流速
        hydraulics.V_mean = float(np.mean(V))
        hydraulics.V_min = float(np.min(V))
        hydraulics.V_max = float(np.max(V))
        hydraulics.V_std = float(np.std(V))
        
        # 计算Froude数
        Fr = np.abs(V) / np.sqrt(self.g * np.maximum(h, 1e-6))
        hydraulics.Fr_mean = float(np.mean(Fr))
        hydraulics.Fr_min = float(np.min(Fr))
        hydraulics.Fr_max = float(np.max(Fr))
        
        # 流态分类
        total_points = Fr.size
        subcritical = np.sum(Fr < 0.9)
        critical = np.sum((Fr >= 0.9) & (Fr <= 1.1))
        supercritical = np.sum(Fr > 1.1)
        
        hydraulics.subcritical_percentage = (subcritical / total_points) * 100
        hydraulics.critical_percentage = (critical / total_points) * 100
        hydraulics.supercritical_percentage = (supercritical / total_points) * 100
        
        # 水跃检测（在最终时刻）
        if len(h) > 0:
            h_final = h[-1, :]
            self._detect_hydraulic_jumps(x, h_final, V[-1, :], hydraulics)
        
        # 激波检测
        self._detect_shock_waves(x, time, h, V, hydraulics)
    
    def _detect_hydraulic_jumps(self, x, h, V, hydraulics):
        """检测水跃"""
        if len(h) < 2:
            return
        
        # 计算水深梯度
        dh_dx = np.gradient(h, x)
        
        # 计算Froude数
        Fr = np.abs(V) / np.sqrt(self.g * np.maximum(h, 1e-6))
        
        # 寻找水跃位置（水深突变且Froude数从>1变到<1）
        for i in range(1, len(x)-1):
            # 相对水深变化
            h_change = (h[i+1] - h[i]) / (h[i] + 1e-6)
            
            # 检测条件：
            # 1. 水深急剧增加
            # 2. 上游超临界，下游亚临界
            if h_change > self.jump_threshold and Fr[i-1] > 1.0 and Fr[i+1] < 1.0:
                jump = {
                    'location': float(x[i]),
                    'upstream_depth': float(h[i]),
                    'downstream_depth': float(h[i+1]),
                    'depth_ratio': float(h[i+1] / (h[i] + 1e-6)),
                    'upstream_froude': float(Fr[i-1]),
                    'downstream_froude': float(Fr[i+1]),
                    'type': 'hydraulic_jump'
                }
                hydraulics.hydraulic_jumps.append(jump)
    
    def _detect_shock_waves(self, x, time, h, V, hydraulics):
        """检测激波"""
        if len(h) < 2 or len(time) < 2:
            return
        
        # 在最终时刻检测激波
        h_final = h[-1, :]
        V_final = V[-1, :]
        
        # 计算流速梯度
        dV_dx = np.gradient(V_final, x)
        
        # 寻找激波位置（流速梯度大）
        shock_indices = np.where(np.abs(dV_dx) > self.shock_threshold)[0]
        
        for i in shock_indices:
            if i > 0 and i < len(x) - 1:
                shock = {
                    'location': float(x[i]),
                    'time': float(time[-1]),
                    'velocity_gradient': float(dV_dx[i]),
                    'depth': float(h_final[i]),
                    'velocity': float(V_final[i]),
                    'type': 'shock_wave'
                }
                hydraulics.shock_waves.append(shock)
    
    def _check_conservation(self, x, time, h, Q, V, config, report):
        """检查守恒性"""
        conservation = report.conservation
        
        # 1. 质量守恒检查
        if len(Q) > 1:
            # 检查流量沿程变化
            Q_inlet = Q[:, 0]  # 入口流量
            Q_outlet = Q[:, -1]  # 出口流量
            
            Q_error = np.abs(Q_inlet - Q_outlet) / (np.abs(Q_inlet) + 1e-6)
            
            conservation.mass_conservation = {
                'inlet_Q_mean': float(np.mean(Q_inlet)),
                'outlet_Q_mean': float(np.mean(Q_outlet)),
                'error_mean': float(np.mean(Q_error) * 100),  # 百分比
                'error_max': float(np.max(Q_error) * 100),
                'status': 'good' if np.mean(Q_error) < 0.01 else 'warning'
            }
            
            if np.mean(Q_error) > 0.05:
                report.warnings.append(f"质量守恒误差较大: {np.mean(Q_error)*100:.2f}%")
        
        # 2. 动量守恒检查（简化）
        width = config.get('width', 10)
        if len(h) > 1 and len(V) > 1:
            # 计算动量通量
            M = h * V**2 * width  # 简化动量
            
            M_inlet = M[:, 0]
            M_outlet = M[:, -1]
            
            conservation.momentum_conservation = {
                'inlet_M_mean': float(np.mean(M_inlet)),
                'outlet_M_mean': float(np.mean(M_outlet)),
                'status': 'computed'
            }
        
        # 3. 能量耗散
        manning_n = config.get('manning_n', 0.025)
        slope = config.get('slope', 0.001)
        
        if manning_n > 0:
            # 计算能量损失
            h_mean = np.mean(h)
            V_mean = np.mean(np.abs(V))
            
            # Manning公式的能量坡度
            R = h_mean  # 假设宽浅渠道
            Sf = (manning_n * V_mean)**2 / (R**(4/3)) if R > 0 else 0
            
            conservation.energy_dissipation = {
                'bed_slope': float(slope),
                'friction_slope': float(Sf),
                'energy_loss_rate': float(Sf - slope),
                'status': 'computed'
            }
    
    def _analyze_performance(self, metrics, report):
        """分析性能"""
        perf = report.performance
        
        perf.computation_time = metrics.get('duration', 0)
        perf.time_steps = metrics.get('time_steps', 0)
        perf.iterations = metrics.get('iterations', 0)
        
        if perf.computation_time > 0 and perf.time_steps > 0:
            perf.efficiency = perf.time_steps / perf.computation_time
            perf.convergence_rate = perf.time_steps / max(perf.iterations, 1)
        
        # 性能评估
        if perf.computation_time > 300:
            report.warnings.append(f"计算时间较长: {perf.computation_time:.1f}秒")
        
        if perf.efficiency < 10:
            report.warnings.append(f"计算效率较低: {perf.efficiency:.1f}步/秒")
    
    def _detect_key_events(self, x, time, h, Q, V, report):
        """检测关键事件"""
        # 1. 检测水深极值事件
        h_max_idx = np.unravel_index(np.argmax(h), h.shape)
        h_min_idx = np.unravel_index(np.argmin(h), h.shape)
        
        if np.max(h) > 1.5 * np.mean(h):
            report.key_events.append({
                'type': 'max_depth',
                'time': float(time[h_max_idx[0]]),
                'location': float(x[h_max_idx[1]]),
                'value': float(np.max(h)),
                'description': f"最大水深 {np.max(h):.2f}m 发生在 t={time[h_max_idx[0]]:.2f}s, x={x[h_max_idx[1]]:.2f}m"
            })
        
        # 2. 检测流速极值事件
        V_max_idx = np.unravel_index(np.argmax(np.abs(V)), V.shape)
        
        if np.max(np.abs(V)) > 10:
            report.key_events.append({
                'type': 'high_velocity',
                'time': float(time[V_max_idx[0]]),
                'location': float(x[V_max_idx[1]]),
                'value': float(np.max(np.abs(V))),
                'description': f"最大流速 {np.max(np.abs(V)):.2f}m/s 发生在 t={time[V_max_idx[0]]:.2f}s, x={x[V_max_idx[1]]:.2f}m"
            })
        
        # 3. 检测波前传播（针对溃坝等问题）
        if len(time) > 1:
            h_diff = h[-1, :] - h[0, :]
            significant_change = np.abs(h_diff) > 0.5 * np.max(np.abs(h_diff))
            
            if np.any(significant_change):
                change_indices = np.where(significant_change)[0]
                wave_front = {
                    'type': 'wave_propagation',
                    'start': float(x[change_indices[0]]),
                    'end': float(x[change_indices[-1]]),
                    'distance': float(x[change_indices[-1]] - x[change_indices[0]]),
                    'duration': float(time[-1] - time[0]),
                    'speed': float((x[change_indices[-1]] - x[change_indices[0]]) / (time[-1] - time[0]))
                }
                report.key_events.append(wave_front)
    
    def _assess_quality(self, h, Q, V, report):
        """评估结果质量"""
        score = 100.0
        
        # 1. 检查非物理值
        if np.any(h < 0):
            score -= 50
            report.errors.append("发现负水深")
        
        if np.any(np.isnan(h)) or np.any(np.isinf(h)):
            score -= 50
            report.errors.append("发现NaN或Inf值")
        
        if np.any(np.isnan(Q)) or np.any(np.isinf(Q)):
            score -= 30
            report.errors.append("流量存在NaN或Inf值")
        
        # 2. 检查数值振荡
        if len(h) > 2:
            h_final = h[-1, :]
            h_diff2 = np.diff(h_final, 2)
            oscillation = np.std(h_diff2) / (np.mean(h_final) + 1e-6)
            
            if oscillation > 0.1:
                score -= 20
                report.warnings.append(f"检测到数值振荡: {oscillation:.3f}")
        
        # 3. 检查结果合理性
        if np.max(h) > 100:
            score -= 10
            report.warnings.append("水深异常大")
        
        if np.max(np.abs(V)) > 50:
            score -= 10
            report.warnings.append("流速异常大")
        
        # 4. 检查守恒性（如果有）
        if report.conservation.mass_conservation:
            error = report.conservation.mass_conservation.get('error_mean', 0)
            if error > 5:
                score -= 20
                report.warnings.append("质量守恒误差大")
            elif error > 1:
                score -= 10
        
        report.quality_score = max(0, score)
        
        # 确定质量等级
        if report.quality_score >= self.quality_thresholds['excellent']:
            report.quality = ResultQuality.EXCELLENT
        elif report.quality_score >= self.quality_thresholds['good']:
            report.quality = ResultQuality.GOOD
        elif report.quality_score >= self.quality_thresholds['acceptable']:
            report.quality = ResultQuality.ACCEPTABLE
        elif report.quality_score >= self.quality_thresholds['poor']:
            report.quality = ResultQuality.POOR
        else:
            report.quality = ResultQuality.FAILED
    
    def _generate_visualization_recommendations(self, x, time, h, Q, V, report):
        """生成可视化建议"""
        recommendations = []
        
        # 1. 基础图表（必选）
        recommendations.append({
            'title': '水深纵剖面图',
            'type': 'longitudinal_profile',
            'priority': 'high',
            'description': '显示最终时刻的水深沿程分布',
            'data': {'x': 'x', 'y': 'h[-1]'}
        })
        
        recommendations.append({
            'title': '流量沿程分布',
            'type': 'discharge_profile',
            'priority': 'high',
            'description': '显示最终时刻的流量沿程分布',
            'data': {'x': 'x', 'y': 'Q[-1]'}
        })
        
        # 2. 时空图（如果时间演化明显）
        if len(time) > 10:
            h_change = np.std(h, axis=0).mean()
            if h_change > 0.1 * np.mean(h):
                recommendations.append({
                    'title': '水深时空演化图',
                    'type': 'spacetime_contour',
                    'priority': 'high',
                    'description': '显示水深随时间和空间的演化过程',
                    'data': {'x': 'x', 't': 'time', 'z': 'h'}
                })
        
        # 3. 特征点时程图
        recommendations.append({
            'title': '关键位置时程图',
            'type': 'time_series',
            'priority': 'medium',
            'description': '显示入口、中点、出口的水深时程',
            'data': {'locations': [0, len(x)//2, -1]}
        })
        
        # 4. Froude数分布（如果有超临界流）
        Fr_mean = report.hydraulics.Fr_mean
        if Fr_mean > 0.5 or report.hydraulics.supercritical_percentage > 10:
            recommendations.append({
                'title': 'Froude数分布',
                'type': 'froude_profile',
                'priority': 'high',
                'description': '显示流态分布（亚临界/临界/超临界）',
                'data': {'x': 'x', 'Fr': 'V/sqrt(g*h)'}
            })
        
        # 5. 水跃可视化
        if len(report.hydraulics.hydraulic_jumps) > 0:
            recommendations.append({
                'title': '水跃位置标注',
                'type': 'hydraulic_jump_markers',
                'priority': 'high',
                'description': '在纵剖面图上标注水跃位置',
                'data': {'jumps': report.hydraulics.hydraulic_jumps}
            })
        
        # 6. 能量线图
        recommendations.append({
            'title': '能量线和水面线',
            'type': 'energy_profile',
            'priority': 'medium',
            'description': '显示总水头线、水面线和底坡',
            'data': {'x': 'x', 'h': 'h', 'V': 'V', 'z': 'bed_elevation'}
        })
        
        report.visualization_recommendations = recommendations
    
    def _generate_summary(self, report):
        """生成总结和建议"""
        # 总结
        summary_parts = []
        
        summary_parts.append(f"仿真质量: {report.quality.value.upper()} (评分: {report.quality_score:.1f}/100)")
        
        hydro = report.hydraulics
        summary_parts.append(
            f"水深范围: {hydro.h_min:.2f}-{hydro.h_max:.2f}m (平均{hydro.h_mean:.2f}m)"
        )
        summary_parts.append(
            f"流速范围: {hydro.V_min:.2f}-{hydro.V_max:.2f}m/s (平均{hydro.V_mean:.2f}m/s)"
        )
        summary_parts.append(
            f"Froude数范围: {hydro.Fr_min:.2f}-{hydro.Fr_max:.2f} (平均{hydro.Fr_mean:.2f})"
        )
        
        # 流态
        if hydro.supercritical_percentage > 50:
            flow_regime = "主要为超临界流"
        elif hydro.subcritical_percentage > 50:
            flow_regime = "主要为亚临界流"
        else:
            flow_regime = "混合流态"
        summary_parts.append(f"流态: {flow_regime}")
        
        # 性能
        perf = report.performance
        if perf.computation_time > 0:
            summary_parts.append(
                f"计算性能: {perf.computation_time:.2f}秒, {perf.time_steps}步, {perf.efficiency:.1f}步/秒"
            )
        
        report.summary = "\n".join(summary_parts)
        
        # 建议
        recommendations = []
        
        if report.quality_score < 80:
            recommendations.append("结果质量有待提高，建议检查配置参数")
        
        if len(report.warnings) > 5:
            recommendations.append("发现多个警告，建议仔细检查结果")
        
        if hydro.supercritical_percentage > 30:
            recommendations.append("存在较多超临界流区域，注意数值稳定性")
        
        if len(hydro.hydraulic_jumps) > 0:
            recommendations.append(f"检测到{len(hydro.hydraulic_jumps)}个水跃，建议加密网格以提高精度")
        
        if report.conservation.mass_conservation:
            error = report.conservation.mass_conservation.get('error_mean', 0)
            if error > 1:
                recommendations.append("质量守恒误差较大，建议减小时间步长或CFL数")
        
        if perf.efficiency < 50 and perf.time_steps > 1000:
            recommendations.append("计算效率较低，考虑优化网格或使用更高阶格式")
        
        if len(recommendations) == 0:
            recommendations.append("结果质量良好，无特别建议")
        
        report.recommendations = recommendations
    
    def generate_markdown_report(self, report: ResultAnalysisReport) -> str:
        """生成Markdown格式的完整报告"""
        lines = []
        
        # 标题
        lines.append("# 📊 仿真结果分析报告")
        lines.append("")
        lines.append(f"**任务ID**: {report.task_id}")
        lines.append(f"**生成时间**: {report.timestamp}")
        lines.append(f"**质量评级**: {self._get_quality_emoji(report.quality)} {report.quality.value.upper()}")
        lines.append(f"**质量评分**: {report.quality_score:.1f}/100")
        lines.append("")
        
        # 执行摘要
        lines.append("## 📋 执行摘要")
        lines.append("")
        lines.append(report.summary)
        lines.append("")
        
        # 水力特性
        lines.append("## 💧 水力特性分析")
        lines.append("")
        
        hydro = report.hydraulics
        lines.append("### 基本统计")
        lines.append("")
        lines.append("| 参数 | 最小值 | 平均值 | 最大值 | 标准差 |")
        lines.append("|------|--------|--------|--------|--------|")
        lines.append(f"| 水深 (m) | {hydro.h_min:.3f} | {hydro.h_mean:.3f} | {hydro.h_max:.3f} | {hydro.h_std:.3f} |")
        lines.append(f"| 流量 (m³/s) | {hydro.Q_min:.3f} | {hydro.Q_mean:.3f} | {hydro.Q_max:.3f} | {hydro.Q_std:.3f} |")
        lines.append(f"| 流速 (m/s) | {hydro.V_min:.3f} | {hydro.V_mean:.3f} | {hydro.V_max:.3f} | {hydro.V_std:.3f} |")
        lines.append(f"| Froude数 | {hydro.Fr_min:.3f} | {hydro.Fr_mean:.3f} | {hydro.Fr_max:.3f} | - |")
        lines.append("")
        
        # 流态分布
        lines.append("### 流态分布")
        lines.append("")
        lines.append(f"- 🔵 亚临界流: {hydro.subcritical_percentage:.1f}%")
        lines.append(f"- 🟡 临界流: {hydro.critical_percentage:.1f}%")
        lines.append(f"- 🔴 超临界流: {hydro.supercritical_percentage:.1f}%")
        lines.append("")
        
        # 水跃检测
        if hydro.hydraulic_jumps:
            lines.append("### 🌊 水跃检测")
            lines.append("")
            for i, jump in enumerate(hydro.hydraulic_jumps, 1):
                lines.append(f"**水跃 #{i}**")
                lines.append(f"- 位置: {jump['location']:.2f} m")
                lines.append(f"- 上游水深: {jump['upstream_depth']:.3f} m (Fr={jump['upstream_froude']:.2f})")
                lines.append(f"- 下游水深: {jump['downstream_depth']:.3f} m (Fr={jump['downstream_froude']:.2f})")
                lines.append(f"- 水深比: {jump['depth_ratio']:.2f}")
                lines.append("")
        
        # 激波检测
        if hydro.shock_waves:
            lines.append("### ⚡ 激波检测")
            lines.append("")
            lines.append(f"检测到 {len(hydro.shock_waves)} 个激波区域")
            lines.append("")
        
        # 守恒性检查
        if report.conservation.mass_conservation:
            lines.append("## ⚖️ 守恒性检查")
            lines.append("")
            
            mass = report.conservation.mass_conservation
            lines.append("### 质量守恒")
            lines.append("")
            lines.append(f"- 入口平均流量: {mass['inlet_Q_mean']:.3f} m³/s")
            lines.append(f"- 出口平均流量: {mass['outlet_Q_mean']:.3f} m³/s")
            lines.append(f"- 平均误差: {mass['error_mean']:.4f}%")
            lines.append(f"- 最大误差: {mass['error_max']:.4f}%")
            lines.append(f"- 状态: {self._get_status_emoji(mass['status'])} {mass['status']}")
            lines.append("")
        
        # 性能指标
        lines.append("## ⚡ 性能指标")
        lines.append("")
        
        perf = report.performance
        lines.append(f"- 计算时间: {perf.computation_time:.2f} 秒")
        lines.append(f"- 时间步数: {perf.time_steps}")
        lines.append(f"- 迭代次数: {perf.iterations}")
        lines.append(f"- 计算效率: {perf.efficiency:.1f} 步/秒")
        lines.append("")
        
        # 关键事件
        if report.key_events:
            lines.append("## 🎯 关键事件")
            lines.append("")
            for event in report.key_events:
                lines.append(f"### {event['type']}")
                lines.append(f"{event.get('description', '无描述')}")
                lines.append("")
        
        # 警告和错误
        if report.errors:
            lines.append("## ❌ 错误")
            lines.append("")
            for error in report.errors:
                lines.append(f"- {error}")
            lines.append("")
        
        if report.warnings:
            lines.append("## ⚠️ 警告")
            lines.append("")
            for warning in report.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        
        # 可视化建议
        lines.append("## 📈 可视化建议")
        lines.append("")
        for i, viz in enumerate(report.visualization_recommendations, 1):
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            emoji = priority_emoji.get(viz['priority'], '⚪')
            lines.append(f"{i}. {emoji} **{viz['title']}** ({viz['priority']} priority)")
            lines.append(f"   - {viz['description']}")
        lines.append("")
        
        # 建议
        lines.append("## 💡 改进建议")
        lines.append("")
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        # 页脚
        lines.append("---")
        lines.append("*报告由 HydroClaude 专业结果分析器自动生成*")
        lines.append("")
        
        return "\n".join(lines)
    
    def _get_quality_emoji(self, quality: ResultQuality) -> str:
        """获取质量等级对应的emoji"""
        emoji_map = {
            ResultQuality.EXCELLENT: "🏆",
            ResultQuality.GOOD: "✅",
            ResultQuality.ACCEPTABLE: "👍",
            ResultQuality.POOR: "⚠️",
            ResultQuality.FAILED: "❌"
        }
        return emoji_map.get(quality, "❓")
    
    def _get_status_emoji(self, status: str) -> str:
        """获取状态对应的emoji"""
        emoji_map = {
            'good': '✅',
            'warning': '⚠️',
            'error': '❌',
            'computed': 'ℹ️'
        }
        return emoji_map.get(status, '❓')
    
    def export_json(self, report: ResultAnalysisReport, filepath: str):
        """导出JSON格式报告"""
        # 将报告转换为字典
        report_dict = {
            'task_id': report.task_id,
            'timestamp': report.timestamp,
            'quality': report.quality.value,
            'quality_score': report.quality_score,
            'hydraulics': {
                'h_mean': report.hydraulics.h_mean,
                'h_min': report.hydraulics.h_min,
                'h_max': report.hydraulics.h_max,
                'h_std': report.hydraulics.h_std,
                'Q_mean': report.hydraulics.Q_mean,
                'Q_min': report.hydraulics.Q_min,
                'Q_max': report.hydraulics.Q_max,
                'Q_std': report.hydraulics.Q_std,
                'V_mean': report.hydraulics.V_mean,
                'V_min': report.hydraulics.V_min,
                'V_max': report.hydraulics.V_max,
                'V_std': report.hydraulics.V_std,
                'Fr_mean': report.hydraulics.Fr_mean,
                'Fr_min': report.hydraulics.Fr_min,
                'Fr_max': report.hydraulics.Fr_max,
                'subcritical_percentage': report.hydraulics.subcritical_percentage,
                'critical_percentage': report.hydraulics.critical_percentage,
                'supercritical_percentage': report.hydraulics.supercritical_percentage,
                'hydraulic_jumps': report.hydraulics.hydraulic_jumps,
                'shock_waves': report.hydraulics.shock_waves
            },
            'conservation': {
                'mass_conservation': report.conservation.mass_conservation,
                'momentum_conservation': report.conservation.momentum_conservation,
                'energy_dissipation': report.conservation.energy_dissipation
            },
            'performance': {
                'computation_time': report.performance.computation_time,
                'time_steps': report.performance.time_steps,
                'iterations': report.performance.iterations,
                'efficiency': report.performance.efficiency
            },
            'key_events': report.key_events,
            'warnings': report.warnings,
            'errors': report.errors,
            'visualization_recommendations': report.visualization_recommendations,
            'summary': report.summary,
            'recommendations': report.recommendations
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)


# 使用示例
if __name__ == "__main__":
    # 模拟测试数据
    test_result = {
        'task_id': 'test_001',
        'x': list(np.linspace(0, 1000, 100)),
        'time': list(np.linspace(0, 100, 50)),
        'h': np.random.uniform(4, 6, (50, 100)).tolist(),
        'Q': np.random.uniform(9, 11, (50, 100)).tolist(),
        'V': np.random.uniform(0.15, 0.25, (50, 100)).tolist(),
        'metrics': {
            'duration': 5.234,
            'time_steps': 500,
            'iterations': 500
        }
    }
    
    test_config = {
        'width': 10.0,
        'manning_n': 0.025,
        'slope': 0.001
    }
    
    # 分析结果
    analyzer = ProfessionalResultAnalyzer()
    report = analyzer.analyze(test_result, test_config)
    
    # 打印Markdown报告
    print(analyzer.generate_markdown_report(report))
    
    # 导出JSON
    analyzer.export_json(report, '/tmp/analysis_report.json')
    
    print("\n" + "="*80)
    print(f"分析完成！")
    print(f"质量评级: {report.quality.value}")
    print(f"质量评分: {report.quality_score:.1f}/100")
    print(f"发现 {len(report.warnings)} 个警告")
    print(f"发现 {len(report.errors)} 个错误")
    print(f"关键事件: {len(report.key_events)} 个")
