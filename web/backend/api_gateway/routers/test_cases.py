#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Cases Router - 测试案例API路由
提供测试案例的浏览、搜索、运行和报告生成功能

Endpoints:
- GET /test-cases - 获取所有测试案例列表
- GET /test-cases/{category} - 按分类获取案例
- GET /test-cases/search?q=query - 搜索测试案例
- GET /test-cases/detail/{case_id} - 获取案例详情
- POST /test-cases/run/{case_id} - 运行指定测试案例
- GET /test-cases/report/{case_id} - 获取案例分析报告

Author: HydroClaude Team
Date: 2025-11-13
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
from pathlib import Path
import sys
import os

# 添加路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from auto_report_generator import ReportGenerator, SimulationResult

router = APIRouter(prefix="/api/v1/test-cases", tags=["test-cases"])

# 加载测试案例目录
TEST_CASES_FILE = Path(__file__).parent.parent.parent / "data" / "test_cases_catalog.json"

# 全局变量
test_cases_catalog = None
report_generator = ReportGenerator()


def load_test_cases():
    """加载测试案例目录"""
    global test_cases_catalog
    if test_cases_catalog is None:
        if TEST_CASES_FILE.exists():
            with open(TEST_CASES_FILE, 'r', encoding='utf-8') as f:
                test_cases_catalog = json.load(f)
        else:
            test_cases_catalog = {'totalCases': 0, 'categories': {}, 'testCases': []}
    return test_cases_catalog


# Pydantic Models
class TestCaseListResponse(BaseModel):
    """测试案例列表响应"""
    total: int
    categories: Dict[str, int]
    cases: List[Dict[str, Any]]


class TestCaseDetailResponse(BaseModel):
    """测试案例详情响应"""
    metadata: Dict[str, Any]
    config: Dict[str, Any]
    expectedResults: Dict[str, Any]
    validationCriteria: Dict[str, Any]
    sourcePath: str


class TestCaseRunRequest(BaseModel):
    """测试案例运行请求"""
    caseId: str
    overrideConfig: Optional[Dict[str, Any]] = None


class TestCaseRunResponse(BaseModel):
    """测试案例运行响应"""
    status: str
    message: str
    resultId: Optional[str] = None


class ReportResponse(BaseModel):
    """报告响应"""
    metadata: Dict[str, Any]
    summary: Dict[str, str]
    analysis: Dict[str, Any]
    metrics: Dict[str, float]
    validation: Dict[str, Any]
    visualizations: List[Dict[str, Any]]
    conclusions: Dict[str, List[str]]
    markdown: str


@router.get("/", response_model=TestCaseListResponse)
async def get_all_test_cases(
    limit: int = 100,
    offset: int = 0,
    category: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """
    获取所有测试案例列表
    
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    - **category**: 按分类过滤（可选）
    - **difficulty**: 按难度过滤（可选）
    """
    catalog = load_test_cases()
    
    cases = catalog['testCases']
    
    # 应用过滤器
    if category:
        cases = [c for c in cases if c.get('metadata', {}).get('category') == category]
    
    if difficulty:
        cases = [c for c in cases if c.get('metadata', {}).get('difficulty') == difficulty]
    
    # 分页
    total = len(cases)
    cases_page = cases[offset:offset + limit]
    
    return TestCaseListResponse(
        total=total,
        categories=catalog['categories'],
        cases=cases_page
    )


@router.get("/categories", response_model=Dict[str, int])
async def get_categories():
    """获取所有分类及其案例数量"""
    catalog = load_test_cases()
    return catalog['categories']


@router.get("/search", response_model=TestCaseListResponse)
async def search_test_cases(
    q: str,
    limit: int = 50
):
    """
    搜索测试案例
    
    - **q**: 搜索关键词
    - **limit**: 返回数量限制
    """
    catalog = load_test_cases()
    
    query_lower = q.lower()
    results = []
    
    for case in catalog['testCases']:
        metadata = case.get('metadata', {})
        # 在名称、标签、分类中搜索
        if (query_lower in metadata.get('name', '').lower() or
            query_lower in metadata.get('nameCN', '') or
            query_lower in metadata.get('category', '').lower() or
            any(query_lower in tag.lower() for tag in metadata.get('tags', []))):
            results.append(case)
    
    results = results[:limit]
    
    return TestCaseListResponse(
        total=len(results),
        categories=catalog['categories'],
        cases=results
    )


@router.get("/detail/{case_id}", response_model=TestCaseDetailResponse)
async def get_test_case_detail(case_id: str):
    """
    获取测试案例详情
    
    - **case_id**: 案例ID
    """
    catalog = load_test_cases()
    
    # 查找案例
    for case in catalog['testCases']:
        if case.get('metadata', {}).get('id') == case_id:
            return TestCaseDetailResponse(**case)
    
    raise HTTPException(status_code=404, detail=f"Test case {case_id} not found")


@router.post("/run/{case_id}", response_model=TestCaseRunResponse)
async def run_test_case(
    case_id: str,
    background_tasks: BackgroundTasks,
    request: Optional[TestCaseRunRequest] = None
):
    """
    运行指定测试案例
    
    - **case_id**: 案例ID
    - **request**: 可选的配置覆盖
    """
    catalog = load_test_cases()
    
    # 查找案例
    test_case = None
    for case in catalog['testCases']:
        if case.get('metadata', {}).get('id') == case_id:
            test_case = case
            break
    
    if not test_case:
        raise HTTPException(status_code=404, detail=f"Test case {case_id} not found")
    
    # TODO: 实际运行测试案例
    # 这里需要调用HydraulicEngine
    # 暂时返回模拟响应
    
    return TestCaseRunResponse(
        status="queued",
        message=f"Test case {case_id} queued for execution",
        resultId=f"result-{case_id}-{int(time.time())}"
    )


@router.get("/report/{result_id}", response_model=ReportResponse)
async def get_test_report(result_id: str):
    """
    获取测试案例分析报告
    
    - **result_id**: 结果ID
    """
    # TODO: 从数据库或缓存中加载结果
    # 暂时返回模拟报告
    
    # 模拟结果
    import numpy as np
    import time
    
    result = SimulationResult(
        case_id=result_id,
        case_name="Dam Break Test",
        category="dam_break",
        status="completed",
        duration=2.5,
        time=[0, 10, 20, 30, 40, 50],
        x=list(np.linspace(0, 1000, 100)),
        h=[list(np.random.uniform(2, 5, 100)) for _ in range(6)],
        Q=[list(np.random.uniform(50, 150, 100)) for _ in range(6)],
        metrics={},
        validation={}
    )
    
    test_case = {
        'name': 'Dam Break Test',
        'nameCN': '溃坝测试',
        'difficulty': 'intermediate',
        'tags': ['dam-break', 'riemann'],
        'config': {},
        'validationCriteria': {
            'checkMassConservation': True,
            'checkNumericalStability': True
        }
    }
    
    # 生成报告
    report = report_generator.generate_report(result, test_case)
    
    # 添加Markdown格式
    markdown = report_generator.export_to_markdown(report)
    report['markdown'] = markdown
    
    return ReportResponse(**report)


@router.get("/statistics", response_model=Dict[str, Any])
async def get_test_statistics():
    """获取测试案例统计信息"""
    catalog = load_test_cases()
    
    # 统计难度分布
    difficulty_dist = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
    for case in catalog['testCases']:
        diff = case.get('metadata', {}).get('difficulty', 'intermediate')
        difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1
    
    # 统计标签
    tag_count = {}
    for case in catalog['testCases']:
        for tag in case.get('metadata', {}).get('tags', []):
            tag_count[tag] = tag_count.get(tag, 0) + 1
    
    # 前10个热门标签
    top_tags = dict(sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return {
        'total': catalog['totalCases'],
        'categories': catalog['categories'],
        'difficulty': difficulty_dist,
        'topTags': top_tags
    }


import time  # 添加time import



