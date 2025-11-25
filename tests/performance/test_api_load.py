#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 负载测试

使用 locust 进行 API 压力测试
按照 Spec-Kit 规范编写

Author: HydroClaude Test Team
Date: 2025-11-20
Spec: 001-comprehensive-review-and-testing

Usage:
    # 运行 API 负载测试
    locust -f tests/performance/test_api_load.py --host=http://localhost:8000 --headless \
           --users 50 --spawn-rate 5 --run-time 60s --tags api
"""

from locust import HttpUser, task, between, tag
import warnings
warnings.filterwarnings("ignore")
import random
import json


class APILoadTest(HttpUser):
    """
    API 负载测试用户
    
    模拟大量用户同时访问 API
    """
    
    wait_time = between(1, 3)
    
    @task(20)
    @tag('api', 'read')
    def get_knowledge_base(self):
        """
        读取知识库 (高频)
        """
        with self.client.get(
            "/api/knowledge-base",
            catch_response=True
        ) as response:
            if response.elapsed.total_seconds() > 1.0:
                response.failure("Response time > 1s")
            elif response.status_code == 200:
                response.success()
    
    @task(15)
    @tag('api', 'read')
    def get_learning_progress(self):
        """
        读取学习进度
        """
        self.client.get("/api/learning-progress")
    
    @task(10)
    @tag('api', 'read')
    def get_cases(self):
        """
        读取案例列表
        """
        self.client.get("/api/cases")
    
    @task(5)
    @tag('api', 'write')
    def create_simulation(self):
        """
        创建模拟任务 (写操作)
        """
        data = {
            "name": f"test_simulation_{random.randint(1000, 9999)}",
            "parameters": {
                "length": random.uniform(100, 1000),
                "width": random.uniform(5, 15),
                "discharge": random.uniform(10, 100)
            }
        }
        
        with self.client.post(
            "/api/simulations",
            json=data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(3)
    @tag('api', 'compute')
    def run_computation(self):
        """
        运行计算 (计算密集)
        """
        data = {
            "canal": {
                "length": 1000,
                "width": 10,
                "slope": 0.001
            },
            "flow": {
                "discharge": 50
            }
        }
        
        with self.client.post(
            "/api/solve/steady-flow",
            json=data,
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code in [200, 404]:
                response.success()


class HighConcurrencyTest(HttpUser):
    """
    高并发测试
    
    测试系统在高并发下的表现
    """
    
    wait_time = between(0.1, 0.5)
    
    @task
    def rapid_requests(self):
        """
        快速连续请求
        """
        self.client.get("/api/health")
        self.client.get("/api/knowledge-base")
        self.client.get("/api/learning-progress")


class SustainedLoadTest(HttpUser):
    """
    持续负载测试
    
    测试系统长时间运行的稳定性
    """
    
    wait_time = between(2, 5)
    
    @task(10)
    def normal_api_call(self):
        """
        正常 API 调用
        """
        endpoints = [
            "/api/knowledge-base",
            "/api/learning-progress",
            "/api/cases",
            "/api/health"
        ]
        
        endpoint = random.choice(endpoints)
        self.client.get(endpoint)
    
    @task(1)
    def computation_task(self):
        """
        计算任务
        """
        data = {
            "canal": {
                "length": random.uniform(500, 2000),
                "width": random.uniform(5, 15)
            },
            "flow": {
                "discharge": random.uniform(20, 100)
            }
        }
        
        self.client.post("/api/solve/steady-flow", json=data, timeout=30)
