#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Runner Router - 测试运行器路由
提供Web界面测试案例运行功能

Endpoints:
- POST /test-runner/run/{case_id} - 运行单个测试案例
- POST /test-runner/batch - 批量运行测试案例
- GET /test-runner/status/{task_id} - 查询测试状态
- GET /test-runner/result/{task_id} - 获取测试结果

Author: HydroClaude Team
Date: 2025-11-13
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import json
import subprocess
import uuid
import time
from pathlib import Path
from datetime import datetime
import sys
import os

# 添加路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

router = APIRouter(prefix="/api/v1/test-runner", tags=["test-runner"])

# 测试案例目录文件
CATALOG_FILE = Path(project_root) / "web" / "backend" / "data" / "test_cases_catalog.json"

# 测试状态和结果缓存
test_tasks: Dict[str, Dict[str, Any]] = {}
test_results: Dict[str, Dict[str, Any]] = {}


class TestRunRequest(BaseModel):
    """测试运行请求"""
    case_id: str
    timeout: Optional[int] = 60  # 超时时间（秒）
    capture_output: Optional[bool] = True


class BatchTestRequest(BaseModel):
    """批量测试请求"""
    case_ids: List[str]
    timeout: Optional[int] = 60
    stop_on_failure: Optional[bool] = False


class TestRunResponse(BaseModel):
    """测试运行响应"""
    task_id: str
    status: str  # queued, running, completed, failed
    message: str


class TestStatusResponse(BaseModel):
    """测试状态响应"""
    task_id: str
    status: str
    progress: Optional[float] = None
    current_case: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TestResultResponse(BaseModel):
    """测试结果响应"""
    task_id: str
    case_id: str
    case_name: str
    status: str  # passed, failed, error
    duration: float
    output: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


def load_test_cases() -> Dict:
    """加载测试案例目录"""
    if not CATALOG_FILE.exists():
        raise HTTPException(status_code=404, detail="Test cases catalog not found")
    
    with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_test_case_sync(case_id: str, timeout: int = 60) -> Dict[str, Any]:
    """同步运行测试案例"""
    catalog = load_test_cases()
    test_cases = catalog.get('testCases', [])
    
    # 查找案例
    test_case = None
    for tc in test_cases:
        if tc.get('metadata', {}).get('id') == case_id:
            test_case = tc
            break
    
    if not test_case:
        return {
            'status': 'error',
            'error': f'Test case {case_id} not found'
        }
    
    file_path = test_case.get('sourcePath', '')
    case_name = test_case.get('metadata', {}).get('name', 'Unknown')
    
    if not file_path:
        return {
            'status': 'error',
            'case_name': case_name,
            'error': 'No source file path'
        }
    
    full_path = Path(project_root) / file_path
    
    if not full_path.exists():
        return {
            'status': 'error',
            'case_name': case_name,
            'error': f'File not found: {file_path}'
        }
    
    # 运行测试
    try:
        start_time = time.time()
        
        process = subprocess.Popen(
            [sys.executable, str(full_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            returncode = process.returncode
            duration = time.time() - start_time
            
            if returncode == 0:
                return {
                    'status': 'passed',
                    'case_name': case_name,
                    'duration': duration,
                    'output': stdout[:1000] if stdout else None  # 限制输出大小
                }
            else:
                return {
                    'status': 'failed',
                    'case_name': case_name,
                    'duration': duration,
                    'error': f'Exit code: {returncode}\n{stderr[:500]}'
                }
        
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                'status': 'failed',
                'case_name': case_name,
                'duration': timeout,
                'error': f'Timeout after {timeout}s'
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'case_name': case_name,
            'error': str(e)
        }


async def run_test_task(task_id: str, case_id: str, timeout: int):
    """后台运行测试任务"""
    test_tasks[task_id] = {
        'status': 'running',
        'case_id': case_id,
        'started_at': datetime.now().isoformat()
    }
    
    try:
        result = run_test_case_sync(case_id, timeout)
        result['task_id'] = task_id
        result['case_id'] = case_id
        result['timestamp'] = datetime.now().isoformat()
        
        test_results[task_id] = result
        test_tasks[task_id]['status'] = 'completed'
        test_tasks[task_id]['completed_at'] = datetime.now().isoformat()
    
    except Exception as e:
        test_results[task_id] = {
            'task_id': task_id,
            'case_id': case_id,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        test_tasks[task_id]['status'] = 'failed'
        test_tasks[task_id]['completed_at'] = datetime.now().isoformat()


async def run_batch_test_task(task_id: str, case_ids: List[str], timeout: int, stop_on_failure: bool):
    """后台运行批量测试任务"""
    test_tasks[task_id] = {
        'status': 'running',
        'total_cases': len(case_ids),
        'completed_cases': 0,
        'passed': 0,
        'failed': 0,
        'started_at': datetime.now().isoformat()
    }
    
    results = []
    
    for idx, case_id in enumerate(case_ids):
        test_tasks[task_id]['current_case'] = case_id
        test_tasks[task_id]['progress'] = (idx / len(case_ids)) * 100
        
        result = run_test_case_sync(case_id, timeout)
        result['task_id'] = task_id
        result['case_id'] = case_id
        result['timestamp'] = datetime.now().isoformat()
        
        results.append(result)
        
        test_tasks[task_id]['completed_cases'] = idx + 1
        
        if result['status'] == 'passed':
            test_tasks[task_id]['passed'] += 1
        else:
            test_tasks[task_id]['failed'] += 1
            
            if stop_on_failure:
                break
    
    test_results[task_id] = {
        'task_id': task_id,
        'status': 'completed',
        'total': len(case_ids),
        'passed': test_tasks[task_id]['passed'],
        'failed': test_tasks[task_id]['failed'],
        'results': results,
        'timestamp': datetime.now().isoformat()
    }
    
    test_tasks[task_id]['status'] = 'completed'
    test_tasks[task_id]['completed_at'] = datetime.now().isoformat()
    test_tasks[task_id]['progress'] = 100


@router.post("/run/{case_id}", response_model=TestRunResponse)
async def run_single_test(
    case_id: str,
    background_tasks: BackgroundTasks,
    timeout: int = 60
):
    """
    运行单个测试案例
    
    - **case_id**: 测试案例ID
    - **timeout**: 超时时间（秒），默认60秒
    """
    task_id = str(uuid.uuid4())
    
    # 添加后台任务
    background_tasks.add_task(run_test_task, task_id, case_id, timeout)
    
    return TestRunResponse(
        task_id=task_id,
        status="queued",
        message=f"Test case {case_id} queued for execution"
    )


@router.post("/batch", response_model=TestRunResponse)
async def run_batch_tests(
    request: BatchTestRequest,
    background_tasks: BackgroundTasks
):
    """
    批量运行测试案例
    
    - **case_ids**: 测试案例ID列表
    - **timeout**: 每个案例的超时时间（秒）
    - **stop_on_failure**: 遇到失败是否停止
    """
    task_id = str(uuid.uuid4())
    
    # 添加后台任务
    background_tasks.add_task(
        run_batch_test_task,
        task_id,
        request.case_ids,
        request.timeout,
        request.stop_on_failure
    )
    
    return TestRunResponse(
        task_id=task_id,
        status="queued",
        message=f"Batch test with {len(request.case_ids)} cases queued"
    )


@router.get("/status/{task_id}", response_model=TestStatusResponse)
async def get_test_status(task_id: str):
    """
    查询测试状态
    
    - **task_id**: 任务ID
    """
    if task_id not in test_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = test_tasks[task_id]
    
    return TestStatusResponse(
        task_id=task_id,
        status=task['status'],
        progress=task.get('progress'),
        current_case=task.get('current_case'),
        started_at=task.get('started_at'),
        completed_at=task.get('completed_at')
    )


@router.get("/result/{task_id}")
async def get_test_result(task_id: str):
    """
    获取测试结果
    
    - **task_id**: 任务ID
    """
    if task_id not in test_results:
        # 检查任务是否还在运行
        if task_id in test_tasks and test_tasks[task_id]['status'] == 'running':
            raise HTTPException(status_code=202, detail="Test still running")
        
        raise HTTPException(status_code=404, detail=f"Result for task {task_id} not found")
    
    return test_results[task_id]


@router.get("/statistics")
async def get_test_statistics():
    """获取测试统计信息"""
    total_tasks = len(test_tasks)
    completed_tasks = sum(1 for t in test_tasks.values() if t['status'] == 'completed')
    running_tasks = sum(1 for t in test_tasks.values() if t['status'] == 'running')
    
    total_results = len(test_results)
    passed_results = sum(1 for r in test_results.values() if r.get('status') == 'passed')
    failed_results = sum(1 for r in test_results.values() if r.get('status') in ['failed', 'error'])
    
    return {
        'tasks': {
            'total': total_tasks,
            'completed': completed_tasks,
            'running': running_tasks
        },
        'results': {
            'total': total_results,
            'passed': passed_results,
            'failed': failed_results,
            'pass_rate': f"{passed_results/total_results*100:.1f}%" if total_results > 0 else "0%"
        }
    }


@router.delete("/clear")
async def clear_test_cache():
    """清除测试缓存"""
    test_tasks.clear()
    test_results.clear()
    return {"message": "Test cache cleared"}


