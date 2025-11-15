#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析API路由

提供配置分析和结果分析的API接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from ...analysis.config_analyzer import ConfigAnalyzer, ConfigAnalysisReport
from ...analysis.result_analyzer_professional import ProfessionalResultAnalyzer, ResultAnalysisReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])

# 创建分析器实例
config_analyzer = ConfigAnalyzer()
result_analyzer = ProfessionalResultAnalyzer()


@router.post("/config", summary="分析仿真配置")
async def analyze_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析仿真配置的合理性、稳定性和性能预测
    
    Args:
        config: 仿真配置字典
        
    Returns:
        配置分析报告
    """
    try:
        logger.info(f"开始分析配置...")
        
        # 执行分析
        report = config_analyzer.analyze(config)
        
        # 转换为JSON格式
        result = {
            'is_valid': report.is_valid,
            'quality_score': report.quality_score,
            'estimated_time': report.estimated_time,
            'estimated_memory': report.estimated_memory,
            'estimated_iterations': report.estimated_iterations,
            'spatial_resolution': report.spatial_resolution,
            'temporal_resolution': report.temporal_resolution,
            'numerical_stability': report.numerical_stability,
            'physical_validity': report.physical_validity,
            'issues': [
                {
                    'severity': issue.severity.value,
                    'category': issue.category,
                    'message': issue.message,
                    'suggestion': issue.suggestion,
                    'parameter': issue.parameter,
                    'value': issue.value,
                    'recommended': issue.recommended
                }
                for issue in report.issues
            ],
            'warnings': report.warnings,
            'errors': report.errors,
            'recommendations': report.recommendations,
            'diagnostics': report.diagnostics
        }
        
        # 生成Markdown报告
        result['markdown_report'] = config_analyzer.generate_report_markdown(report)
        
        logger.info(f"配置分析完成，质量分数: {report.quality_score:.1f}")
        
        return result
        
    except Exception as e:
        logger.error(f"配置分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"配置分析失败: {str(e)}")


@router.post("/result", summary="分析仿真结果")
async def analyze_result(
    result: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    分析仿真结果的质量、水力特性和关键事件
    
    Args:
        result: 仿真结果字典
        config: 仿真配置（可选，用于深度分析）
        
    Returns:
        结果分析报告
    """
    try:
        logger.info(f"开始分析结果 (task_id: {result.get('task_id', 'unknown')})...")
        
        # 执行分析
        report = result_analyzer.analyze(result, config)
        
        # 转换为JSON格式
        analysis_result = {
            'task_id': report.task_id,
            'timestamp': report.timestamp,
            'quality': report.quality.value,
            'quality_score': report.quality_score,
            'summary': report.summary,
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
            'recommendations': report.recommendations
        }
        
        # 生成Markdown报告
        analysis_result['markdown_report'] = result_analyzer.generate_markdown_report(report)
        
        logger.info(f"结果分析完成，质量评级: {report.quality.value}")
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"结果分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"结果分析失败: {str(e)}")


@router.get("/health", summary="健康检查")
async def health_check():
    """分析服务健康检查"""
    return {
        "status": "healthy",
        "config_analyzer": "ready",
        "result_analyzer": "ready"
    }
