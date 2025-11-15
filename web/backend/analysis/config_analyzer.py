#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
输入配置自动分析模块
对标商业软件：自动检查配置合理性、预测计算、优化建议

功能：
1. 参数合理性检查
2. 数值稳定性分析
3. 计算时间预测
4. 参数优化建议
5. 问题诊断和警告

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math


class SeverityLevel(Enum):
    """问题严重程度"""
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重错误


@dataclass
class AnalysisIssue:
    """分析发现的问题"""
    severity: SeverityLevel
    category: str           # 问题类别
    message: str           # 问题描述
    suggestion: str        # 建议
    parameter: Optional[str] = None  # 相关参数
    value: Optional[Any] = None      # 当前值
    recommended: Optional[Any] = None  # 推荐值


@dataclass
class ConfigAnalysisReport:
    """配置分析报告"""
    # 基本信息
    is_valid: bool
    quality_score: float  # 0-100分
    
    # 检查结果
    issues: List[AnalysisIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # 性能预测
    estimated_time: float = 0.0  # 预计计算时间（秒）
    estimated_memory: float = 0.0  # 预计内存使用（MB）
    estimated_iterations: int = 0  # 预计时间步数
    
    # 参数评估
    spatial_resolution: Dict[str, Any] = field(default_factory=dict)
    temporal_resolution: Dict[str, Any] = field(default_factory=dict)
    numerical_stability: Dict[str, Any] = field(default_factory=dict)
    physical_validity: Dict[str, Any] = field(default_factory=dict)
    
    # 优化建议
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    
    # 诊断信息
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class ConfigAnalyzer:
    """
    配置自动分析器
    
    参考商业软件功能：
    - HEC-RAS: 预处理检查、稳定性分析
    - MIKE: 模型质量检查、优化建议
    - InfoWorks: 网络验证、性能预测
    """
    
    def __init__(self):
        """初始化分析器"""
        self.min_quality_score = 60.0  # 最低质量分数
        
        # 性能系数（基于经验值，可根据实际测试调整）
        self.time_per_cell_per_step = 0.0001  # 秒/网格/步
        self.memory_per_cell = 0.01  # MB/网格
    
    def analyze(self, config: Dict[str, Any]) -> ConfigAnalysisReport:
        """
        全面分析配置
        
        Args:
            config: 仿真配置字典
            
        Returns:
            分析报告
        """
        report = ConfigAnalysisReport(is_valid=True, quality_score=100.0)
        
        # 1. 几何参数检查
        self._check_geometry(config, report)
        
        # 2. 物理参数检查
        self._check_physical_parameters(config, report)
        
        # 3. 数值参数检查
        self._check_numerical_parameters(config, report)
        
        # 4. 时间参数检查
        self._check_temporal_parameters(config, report)
        
        # 5. 边界条件检查
        self._check_boundary_conditions(config, report)
        
        # 6. 初始条件检查
        self._check_initial_conditions(config, report)
        
        # 7. 稳定性分析
        self._analyze_stability(config, report)
        
        # 8. 性能预测
        self._predict_performance(config, report)
        
        # 9. 生成建议
        self._generate_recommendations(config, report)
        
        # 10. 计算质量分数
        self._calculate_quality_score(report)
        
        # 11. 判断有效性
        report.is_valid = len(report.errors) == 0 and report.quality_score >= self.min_quality_score
        
        return report
    
    def _check_geometry(self, config: Dict, report: ConfigAnalysisReport):
        """检查几何参数"""
        width = config.get('width', 0)
        length = config.get('length', 0)
        n_cells = config.get('n_cells', 0)
        
        # 计算空间分辨率
        dx = length / n_cells if n_cells > 0 else 0
        aspect_ratio = length / width if width > 0 else 0
        
        report.spatial_resolution = {
            'dx': dx,
            'cells_per_width': width / dx if dx > 0 else 0,
            'aspect_ratio': aspect_ratio,
            'total_cells': n_cells
        }
        
        # 检查宽度
        if width <= 0:
            report.errors.append("渠道宽度必须大于0")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="geometry",
                message="渠道宽度无效",
                suggestion="设置合理的渠道宽度（通常1-100m）",
                parameter="width",
                value=width
            ))
        elif width < 1.0:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="geometry",
                message="渠道宽度较小",
                suggestion="确认是否为小型渠道，建议宽度>1m",
                parameter="width",
                value=width
            ))
        elif width > 100.0:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="geometry",
                message="渠道宽度较大",
                suggestion="大型渠道可能需要更复杂的模型",
                parameter="width",
                value=width
            ))
        
        # 检查长度
        if length <= 0:
            report.errors.append("渠道长度必须大于0")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="geometry",
                message="渠道长度无效",
                suggestion="设置合理的渠道长度",
                parameter="length",
                value=length
            ))
        
        # 检查空间分辨率
        if dx > 0:
            if dx < 0.1:
                report.issues.append(AnalysisIssue(
                    severity=SeverityLevel.WARNING,
                    category="spatial_resolution",
                    message=f"空间分辨率过细 (dx={dx:.3f}m)",
                    suggestion=f"可能导致计算时间过长，建议dx>0.1m",
                    parameter="n_cells",
                    value=n_cells,
                    recommended=int(length / 0.5)
                ))
            elif dx > 50.0:
                report.issues.append(AnalysisIssue(
                    severity=SeverityLevel.WARNING,
                    category="spatial_resolution",
                    message=f"空间分辨率过粗 (dx={dx:.1f}m)",
                    suggestion=f"可能影响精度，建议dx<50m",
                    parameter="n_cells",
                    value=n_cells,
                    recommended=int(length / 10.0)
                ))
            
            # 最佳实践：dx应该是水深的5-10倍
            report.diagnostics['optimal_dx_range'] = "建议dx为典型水深的5-10倍"
    
    def _check_physical_parameters(self, config: Dict, report: ConfigAnalysisReport):
        """检查物理参数"""
        manning_n = config.get('manning_n', 0)
        slope = config.get('slope', 0)
        
        report.physical_validity = {
            'manning_n': manning_n,
            'slope': slope
        }
        
        # 检查Manning系数
        if manning_n <= 0:
            report.errors.append("Manning系数必须大于0")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="physical",
                message="Manning系数无效",
                suggestion="设置合理的糙率系数（通常0.010-0.050）",
                parameter="manning_n",
                value=manning_n
            ))
        elif manning_n < 0.010:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="physical",
                message=f"Manning系数偏小 (n={manning_n:.3f})",
                suggestion="极光滑表面，请确认是否正确（混凝土约0.012-0.015）",
                parameter="manning_n",
                value=manning_n
            ))
        elif manning_n > 0.100:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="physical",
                message=f"Manning系数偏大 (n={manning_n:.3f})",
                suggestion="极粗糙表面，请确认是否正确（天然河道约0.025-0.050）",
                parameter="manning_n",
                value=manning_n
            ))
        
        # 检查底坡
        if slope < 0:
            report.errors.append("底坡不能为负")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="physical",
                message="底坡为负值",
                suggestion="底坡应为非负值",
                parameter="slope",
                value=slope
            ))
        elif slope == 0:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.INFO,
                category="physical",
                message="水平底坡",
                suggestion="水平渠道，确保边界条件和初始条件合理",
                parameter="slope",
                value=slope
            ))
        elif slope > 0.1:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="physical",
                message=f"底坡很陡 (S={slope:.3f})",
                suggestion="陡坡渠道可能出现超临界流，注意数值稳定性",
                parameter="slope",
                value=slope
            ))
        
        # 估算Froude数
        if manning_n > 0 and slope > 0:
            # 估算正常水深和流速
            report.diagnostics['expected_flow_regime'] = self._estimate_flow_regime(
                slope, manning_n, config.get('width', 10)
            )
    
    def _check_numerical_parameters(self, config: Dict, report: ConfigAnalysisReport):
        """检查数值参数"""
        cfl = config.get('cfl', 0)
        order = config.get('order', 1)
        
        report.numerical_stability = {
            'cfl': cfl,
            'order': order,
            'scheme': f"{order}阶精度"
        }
        
        # 检查CFL数
        if cfl <= 0:
            report.errors.append("CFL数必须大于0")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="numerical",
                message="CFL数无效",
                suggestion="设置合理的CFL数（通常0.3-0.9）",
                parameter="cfl",
                value=cfl
            ))
        elif cfl > 1.0:
            report.errors.append("CFL数超过稳定性限制")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.CRITICAL,
                category="numerical",
                message=f"CFL数过大 (CFL={cfl:.2f})",
                suggestion="显式格式要求CFL≤1.0，建议CFL=0.3-0.9",
                parameter="cfl",
                value=cfl,
                recommended=0.5
            ))
        elif cfl > 0.9:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="numerical",
                message=f"CFL数接近稳定性极限 (CFL={cfl:.2f})",
                suggestion="建议降低CFL至0.3-0.8以提高稳定性",
                parameter="cfl",
                value=cfl,
                recommended=0.5
            ))
        
        # 检查空间精度
        if order == 2 and cfl > 0.5:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="numerical",
                message="二阶格式的CFL数较高",
                suggestion="二阶格式建议CFL≤0.5以保证稳定性",
                parameter="cfl",
                value=cfl,
                recommended=0.5
            ))
    
    def _check_temporal_parameters(self, config: Dict, report: ConfigAnalysisReport):
        """检查时间参数"""
        t_end = config.get('t_end', 0)
        dt_max = config.get('dt_max', 0)
        output_interval = config.get('output_interval', 0)
        
        if t_end <= 0:
            report.errors.append("结束时间必须大于0")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="temporal",
                message="结束时间无效",
                suggestion="设置合理的模拟时长",
                parameter="t_end",
                value=t_end
            ))
        
        if dt_max <= 0:
            report.errors.append("最大时间步必须大于0")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="temporal",
                message="最大时间步无效",
                suggestion="设置合理的时间步长",
                parameter="dt_max",
                value=dt_max
            ))
        
        if output_interval <= 0:
            report.errors.append("输出间隔必须大于0")
        elif output_interval < dt_max:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="temporal",
                message="输出间隔小于时间步长",
                suggestion="输出间隔应≥dt_max，建议设为dt_max的整数倍",
                parameter="output_interval",
                value=output_interval,
                recommended=dt_max
            ))
        
        # 估算时间步数
        if dt_max > 0:
            estimated_steps = int(t_end / dt_max)
            report.temporal_resolution = {
                'dt_max': dt_max,
                't_end': t_end,
                'estimated_steps': estimated_steps,
                'output_interval': output_interval,
                'estimated_outputs': int(t_end / output_interval) if output_interval > 0 else 0
            }
            
            if estimated_steps > 100000:
                report.issues.append(AnalysisIssue(
                    severity=SeverityLevel.WARNING,
                    category="temporal",
                    message=f"预计时间步数很多 ({estimated_steps}步)",
                    suggestion="计算可能耗时较长，考虑增大dt_max或减小t_end",
                    parameter="dt_max",
                    value=dt_max
                ))
    
    def _check_boundary_conditions(self, config: Dict, report: ConfigAnalysisReport):
        """检查边界条件"""
        bc = config.get('boundary_conditions', {})
        upstream = bc.get('upstream', {})
        downstream = bc.get('downstream', {})
        
        # 检查上游边界
        upstream_type = upstream.get('type')
        upstream_value = upstream.get('value')
        
        if upstream_type in ['h', 'Q'] and upstream_value is None:
            report.errors.append(f"上游边界类型'{upstream_type}'需要指定value")
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.ERROR,
                category="boundary",
                message="上游边界条件缺少值",
                suggestion=f"边界类型'{upstream_type}'必须提供value参数",
                parameter="boundary_conditions.upstream.value"
            ))
        elif upstream_type in ['h', 'Q'] and upstream_value is not None:
            if upstream_value < 0:
                report.errors.append("上游边界值不能为负")
                report.issues.append(AnalysisIssue(
                    severity=SeverityLevel.ERROR,
                    category="boundary",
                    message="上游边界值为负",
                    suggestion="水深和流量应为非负值",
                    parameter="boundary_conditions.upstream.value",
                    value=upstream_value
                ))
        
        # 检查下游边界
        downstream_type = downstream.get('type')
        downstream_value = downstream.get('value')
        
        if downstream_type in ['h', 'Q'] and downstream_value is None:
            report.errors.append(f"下游边界类型'{downstream_type}'需要指定value")
        elif downstream_type in ['h', 'Q'] and downstream_value is not None:
            if downstream_value < 0:
                report.errors.append("下游边界值不能为负")
        
        # 检查边界条件兼容性
        if upstream_type == 'Q' and downstream_type == 'Q':
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="boundary",
                message="上下游都是流量边界",
                suggestion="可能导致数值不稳定，建议一端用水深边界",
                parameter="boundary_conditions"
            ))
    
    def _check_initial_conditions(self, config: Dict, report: ConfigAnalysisReport):
        """检查初始条件"""
        ic = config.get('initial_conditions', {})
        ic_type = ic.get('type', 'uniform')
        
        if ic_type == 'uniform':
            h = ic.get('h', 0)
            Q = ic.get('Q', 0)
            
            if h <= 0:
                report.errors.append("初始水深必须大于0")
                report.issues.append(AnalysisIssue(
                    severity=SeverityLevel.ERROR,
                    category="initial",
                    message="初始水深无效",
                    suggestion="设置合理的初始水深",
                    parameter="initial_conditions.h",
                    value=h
                ))
            
            if Q < 0:
                report.errors.append("初始流量不能为负")
        
        elif ic_type == 'dam_break':
            dam_pos = ic.get('dam_position')
            h_left = ic.get('h_left')
            h_right = ic.get('h_right')
            
            if dam_pos is None or h_left is None or h_right is None:
                report.errors.append("溃坝初始条件缺少必要参数")
                report.issues.append(AnalysisIssue(
                    severity=SeverityLevel.ERROR,
                    category="initial",
                    message="溃坝参数不完整",
                    suggestion="必须提供dam_position, h_left, h_right",
                    parameter="initial_conditions"
                ))
            else:
                length = config.get('length', 0)
                if dam_pos <= 0 or dam_pos >= length:
                    report.errors.append("溃坝位置超出渠道范围")
                    report.issues.append(AnalysisIssue(
                        severity=SeverityLevel.ERROR,
                        category="initial",
                        message=f"溃坝位置无效 ({dam_pos}m)",
                        suggestion=f"必须在0到{length}m之间",
                        parameter="initial_conditions.dam_position",
                        value=dam_pos,
                        recommended=length / 2
                    ))
                
                if h_left <= 0 or h_right <= 0:
                    report.errors.append("溃坝水深必须大于0")
    
    def _analyze_stability(self, config: Dict, report: ConfigAnalysisReport):
        """稳定性分析"""
        # 计算关键无量纲数
        width = config.get('width', 10)
        length = config.get('length', 1000)
        n_cells = config.get('n_cells', 100)
        manning_n = config.get('manning_n', 0.025)
        slope = config.get('slope', 0.001)
        cfl = config.get('cfl', 0.5)
        
        dx = length / n_cells if n_cells > 0 else 0
        
        # 估算特征流速和Froude数
        if manning_n > 0 and slope > 0:
            # 使用Manning公式估算
            h_est = 5.0  # 假设水深
            V_est = (1/manning_n) * (h_est**(2/3)) * (slope**0.5)
            Fr_est = V_est / math.sqrt(9.81 * h_est)
            
            report.numerical_stability['estimated_velocity'] = V_est
            report.numerical_stability['estimated_froude'] = Fr_est
            report.numerical_stability['flow_regime'] = "超临界" if Fr_est > 1 else "亚临界"
            
            # 估算数值扩散
            if dx > 0:
                Pe = V_est * dx / (0.1 * V_est * dx)  # 简化的Peclet数
                report.numerical_stability['peclet_number'] = Pe
                
                if Pe > 2:
                    report.issues.append(AnalysisIssue(
                        severity=SeverityLevel.INFO,
                        category="stability",
                        message="可能出现数值扩散",
                        suggestion="考虑使用二阶格式或更细网格",
                        parameter="order"
                    ))
    
    def _predict_performance(self, config: Dict, report: ConfigAnalysisReport):
        """性能预测"""
        n_cells = config.get('n_cells', 100)
        t_end = config.get('t_end', 10)
        dt_max = config.get('dt_max', 0.1)
        
        # 估算时间步数
        estimated_steps = int(t_end / dt_max) if dt_max > 0 else 0
        
        # 估算计算时间
        use_numba = config.get('use_numba', True)
        speedup_factor = 10 if use_numba else 1
        
        time_per_step = n_cells * self.time_per_cell_per_step / speedup_factor
        estimated_time = estimated_steps * time_per_step
        
        # 估算内存使用
        estimated_memory = n_cells * self.memory_per_cell * estimated_steps / 100
        
        report.estimated_time = estimated_time
        report.estimated_memory = estimated_memory
        report.estimated_iterations = estimated_steps
        
        # 性能警告
        if estimated_time > 60:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="performance",
                message=f"预计计算时间较长 ({estimated_time:.1f}秒)",
                suggestion="考虑减少网格数或增大时间步",
                parameter="n_cells"
            ))
        
        if estimated_memory > 1000:
            report.issues.append(AnalysisIssue(
                severity=SeverityLevel.WARNING,
                category="performance",
                message=f"预计内存使用较大 ({estimated_memory:.0f}MB)",
                suggestion="考虑减少输出频率或网格数",
                parameter="output_interval"
            ))
    
    def _generate_recommendations(self, config: Dict, report: ConfigAnalysisReport):
        """生成优化建议"""
        # 基于分析结果生成建议
        cfl = config.get('cfl', 0.5)
        order = config.get('order', 1)
        n_cells = config.get('n_cells', 100)
        
        # 建议1：精度与效率平衡
        if order == 1 and n_cells > 200:
            report.recommendations.append({
                'title': '提高计算精度',
                'description': '网格较密但使用一阶格式',
                'action': '建议使用二阶格式以提高精度和效率',
                'parameters': {'order': 2, 'cfl': 0.5}
            })
        
        # 建议2：CFL优化
        if cfl < 0.3:
            report.recommendations.append({
                'title': 'CFL数优化',
                'description': 'CFL数偏小可能影响效率',
                'action': '可以适当增大CFL至0.5-0.8',
                'parameters': {'cfl': 0.5}
            })
        
        # 建议3：网格优化
        dx = config.get('length', 1000) / n_cells if n_cells > 0 else 0
        if dx > 20:
            report.recommendations.append({
                'title': '空间分辨率优化',
                'description': f'当前网格分辨率较粗 (dx={dx:.1f}m)',
                'action': '建议增加网格数以提高精度',
                'parameters': {'n_cells': int(config.get('length', 1000) / 10)}
            })
    
    def _calculate_quality_score(self, report: ConfigAnalysisReport):
        """计算配置质量分数"""
        score = 100.0
        
        # 根据问题严重程度扣分
        for issue in report.issues:
            if issue.severity == SeverityLevel.CRITICAL:
                score -= 30
            elif issue.severity == SeverityLevel.ERROR:
                score -= 20
            elif issue.severity == SeverityLevel.WARNING:
                score -= 5
            elif issue.severity == SeverityLevel.INFO:
                score -= 1
        
        report.quality_score = max(0, score)
    
    def _estimate_flow_regime(self, slope: float, manning_n: float, width: float) -> str:
        """估算流态"""
        # 简化估算
        if slope > 0.01:
            return "可能为超临界流（陡坡）"
        elif slope < 0.0001:
            return "可能为缓流（平坡）"
        else:
            return "可能为亚临界流"
    
    def generate_report_markdown(self, report: ConfigAnalysisReport) -> str:
        """生成Markdown格式报告"""
        lines = []
        
        lines.append("# 🔍 配置分析报告")
        lines.append("")
        lines.append(f"**质量分数**: {report.quality_score:.1f}/100")
        lines.append(f"**配置状态**: {'✅ 有效' if report.is_valid else '❌ 无效'}")
        lines.append("")
        
        # 性能预测
        lines.append("## ⏱️ 性能预测")
        lines.append("")
        lines.append(f"- 预计计算时间: {report.estimated_time:.2f} 秒")
        lines.append(f"- 预计内存使用: {report.estimated_memory:.1f} MB")
        lines.append(f"- 预计时间步数: {report.estimated_iterations}")
        lines.append("")
        
        # 问题列表
        if report.issues:
            lines.append("## ⚠️ 发现的问题")
            lines.append("")
            
            for issue in sorted(report.issues, key=lambda x: x.severity.value):
                emoji = {'critical': '🔴', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}
                lines.append(f"### {emoji[issue.severity.value]} {issue.category}")
                lines.append(f"**问题**: {issue.message}")
                lines.append(f"**建议**: {issue.suggestion}")
                if issue.parameter:
                    lines.append(f"**参数**: `{issue.parameter}`")
                if issue.value is not None:
                    lines.append(f"**当前值**: {issue.value}")
                if issue.recommended is not None:
                    lines.append(f"**推荐值**: {issue.recommended}")
                lines.append("")
        
        # 优化建议
        if report.recommendations:
            lines.append("## 💡 优化建议")
            lines.append("")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"### {i}. {rec['title']}")
                lines.append(f"**说明**: {rec['description']}")
                lines.append(f"**操作**: {rec['action']}")
                lines.append("")
        
        return "\n".join(lines)


# 使用示例
if __name__ == "__main__":
    # 测试配置
    test_config = {
        "width": 10.0,
        "length": 1000.0,
        "n_cells": 100,
        "manning_n": 0.025,
        "slope": 0.001,
        "cfl": 0.9,
        "order": 2,
        "use_numba": True,
        "t_end": 100.0,
        "dt_max": 0.1,
        "output_interval": 1.0,
        "initial_conditions": {
            "type": "uniform",
            "h": 5.0,
            "Q": 10.0
        },
        "boundary_conditions": {
            "upstream": {"type": "Q", "value": 10.0},
            "downstream": {"type": "h", "value": 5.0}
        }
    }
    
    # 分析配置
    analyzer = ConfigAnalyzer()
    report = analyzer.analyze(test_config)
    
    # 打印报告
    print(analyzer.generate_report_markdown(report))
    
    print(f"\n{'='*80}")
    print(f"分析完成！")
    print(f"质量分数: {report.quality_score:.1f}/100")
    print(f"配置{'有效' if report.is_valid else '无效'}")
    print(f"发现 {len(report.issues)} 个问题")
    print(f"提供 {len(report.recommendations)} 条建议")
