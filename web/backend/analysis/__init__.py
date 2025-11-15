#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动分析模块

提供配置和结果的专业分析功能
"""

from .config_analyzer import ConfigAnalyzer, ConfigAnalysisReport, AnalysisIssue, SeverityLevel
from .result_analyzer_professional import (
    ProfessionalResultAnalyzer, 
    ResultAnalysisReport, 
    HydraulicCharacteristics,
    ResultQuality
)

__all__ = [
    'ConfigAnalyzer',
    'ConfigAnalysisReport',
    'AnalysisIssue',
    'SeverityLevel',
    'ProfessionalResultAnalyzer',
    'ResultAnalysisReport',
    'HydraulicCharacteristics',
    'ResultQuality'
]
