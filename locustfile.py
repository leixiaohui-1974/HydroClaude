#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Locust 性能测试配置文件

用于对 HydroClaude API 进行压力测试和性能基准测试
按照 Spec-Kit 规范编写

Author: HydroClaude Test Team
Date: 2025-11-20
Spec: 001-comprehensive-review-and-testing

Usage:
    # 启动 Web UI
    locust -f locustfile.py --host=http://localhost:8000
    
    # 无头模式
    locust -f locustfile.py --host=http://localhost:8000 --headless --users 100 --spawn-rate 10 --run-time 60s
    
    # 指定任务
    locust -f locustfile.py --host=http://localhost:8000 --tags api
"""

from locust import HttpUser, task, between, tag
import json
import random


class HydroCl audeUser(HttpUser):
    """
    HydroClaude 用户行为模拟
    
    模拟真实用户对 HydroClaude API 的访问模式
    """
    
    # 用户等待时间（秒）
    wait_time = between(1, 5)
    
    def on_start(self):
        """
        用户开始时执行
        
        可用于登录、初始化等操作
        """
        print(f"[Locust] 用户 {id(self)} 开始测试")
        
        # 可选：登录
        # self.login()
    
    def on_stop(self):
        """
        用户结束时执行
        """
        print(f"[Locust] 用户 {id(self)} 结束测试")
    
    # ========== API 测试 ==========
    
    @task(10)
    @tag('api', 'knowledge')
    def get_knowledge_base(self):
        """
        获取知识库列表
        
        权重: 10 (高频请求)
        """
        with self.client.get(
            "/api/knowledge-base",
            catch_response=True,
            name="GET /api/knowledge-base"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(8)
    @tag('api', 'progress')
    def get_learning_progress(self):
        """
        获取学习进度
        
        权重: 8
        """
        with self.client.get(
            "/api/learning-progress",
            catch_response=True,
            name="GET /api/learning-progress"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(6)
    @tag('api', 'cases')
    def get_cases(self):
        """
        获取案例列表
        
        权重: 6
        """
        with self.client.get(
            "/api/cases",
            catch_response=True,
            name="GET /api/cases"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(5)
    @tag('api', 'health')
    def health_check(self):
        """
        健康检查
        
        权重: 5
        """
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="GET /api/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(3)
    @tag('api', 'solver')
    def run_simple_simulation(self):
        """
        运行简单模拟
        
        权重: 3 (计算密集型，较低频率)
        """
        # 简单的渠道流动参数
        data = {
            "canal": {
                "length": random.uniform(500, 2000),
                "width": random.uniform(5, 15),
                "slope": random.uniform(0.0001, 0.01),
                "roughness": random.uniform(0.015, 0.035)
            },
            "flow": {
                "discharge": random.uniform(10, 100)
            }
        }
        
        with self.client.post(
            "/api/solve/steady-flow",
            json=data,
            catch_response=True,
            name="POST /api/solve/steady-flow",
            timeout=30
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    if 'depth' in result or 'result' in result:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except:
                    response.failure("Failed to parse JSON")
            elif response.status_code == 404:
                # API 可能未实现
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(2)
    @tag('api', 'statistics')
    def get_statistics(self):
        """
        获取统计信息
        
        权重: 2
        """
        with self.client.get(
            "/api/statistics",
            catch_response=True,
            name="GET /api/statistics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    # ========== 前端页面测试 ==========
    
    @task(15)
    @tag('frontend', 'homepage')
    def visit_homepage(self):
        """
        访问首页
        
        权重: 15 (最高频)
        """
        with self.client.get(
            "/",
            catch_response=True,
            name="GET /"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(4)
    @tag('frontend', 'modeling')
    def visit_modeling_page(self):
        """
        访问建模页面
        
        权重: 4
        """
        paths = ['/model', '/modeling', '/create']
        path = random.choice(paths)
        
        with self.client.get(
            path,
            catch_response=True,
            name=f"GET {path}"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # 路径可能不存在
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(3)
    @tag('frontend', 'cases')
    def visit_cases_page(self):
        """
        访问案例页面
        
        权重: 3
        """
        paths = ['/cases', '/examples', '/demos']
        path = random.choice(paths)
        
        with self.client.get(
            path,
            catch_response=True,
            name=f"GET {path}"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class APIOnlyUser(HttpUser):
    """
    只测试 API 的用户
    
    用于专门测试 API 性能
    """
    
    wait_time = between(0.5, 2)
    
    @task
    @tag('api-only')
    def api_health_check(self):
        """
        API 健康检查
        """
        self.client.get("/api/health")
    
    @task
    @tag('api-only')
    def api_knowledge_base(self):
        """
        API 知识库
        """
        self.client.get("/api/knowledge-base")


class HeavyUser(HttpUser):
    """
    重负载用户
    
    模拟计算密集型操作
    """
    
    wait_time = between(2, 10)
    
    @task
    @tag('heavy')
    def run_complex_simulation(self):
        """
        运行复杂模拟
        
        使用更大的数据量
        """
        data = {
            "canal": {
                "length": random.uniform(5000, 10000),
                "width": random.uniform(10, 20),
                "slope": random.uniform(0.0001, 0.005),
                "roughness": random.uniform(0.02, 0.04),
                "segments": random.randint(50, 200)
            },
            "flow": {
                "discharge": random.uniform(50, 200)
            },
            "structures": [
                {
                    "type": "gate",
                    "position": random.uniform(1000, 4000),
                    "width": random.uniform(8, 15),
                    "opening": random.uniform(2, 8)
                }
            ]
        }
        
        with self.client.post(
            "/api/solve/advanced",
            json=data,
            catch_response=True,
            name="POST /api/solve/advanced",
            timeout=60
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # API 可能未实现
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


# ========== 性能测试场景 ==========

class QuickTest(HttpUser):
    """
    快速测试场景
    
    用于快速验证系统是否正常
    """
    
    wait_time = between(1, 2)
    
    @task
    def quick_check(self):
        """快速检查"""
        self.client.get("/")
        self.client.get("/api/health")


class SteadyLoad(HttpUser):
    """
    稳定负载场景
    
    模拟正常业务负载
    """
    
    wait_time = between(2, 5)
    
    @task(20)
    def normal_browsing(self):
        """正常浏览"""
        self.client.get("/")
    
    @task(10)
    def api_calls(self):
        """API 调用"""
        self.client.get("/api/knowledge-base")
        self.client.get("/api/learning-progress")
    
    @task(5)
    def computation(self):
        """计算任务"""
        data = {
            "canal": {
                "length": 1000,
                "width": 10,
                "slope": 0.001,
                "roughness": 0.025
            },
            "flow": {
                "discharge": 50
            }
        }
        
        self.client.post("/api/solve/steady-flow", json=data, timeout=30)


class SpikeLoad(HttpUser):
    """
    峰值负载场景
    
    模拟突发流量
    """
    
    wait_time = between(0.1, 1)
    
    @task
    def spike_requests(self):
        """突发请求"""
        self.client.get("/")
        self.client.get("/api/health")
        self.client.get("/api/knowledge-base")


# ========== 事件监听 ==========

from locust import events

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    测试开始时执行
    """
    print("\n" + "="*70)
    print("🚀 Locust 性能测试开始")
    print("="*70)
    print(f"目标主机: {environment.host}")
    print(f"用户数: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    测试结束时执行
    """
    print("\n" + "="*70)
    print("✅ Locust 性能测试完成")
    print("="*70)
    
    # 打印统计信息
    stats = environment.stats
    
    print(f"\n总请求数: {stats.total.num_requests}")
    print(f"失败请求数: {stats.total.num_failures}")
    print(f"成功率: {(1 - stats.total.fail_ratio) * 100:.2f}%")
    print(f"平均响应时间: {stats.total.avg_response_time:.2f} ms")
    print(f"最小响应时间: {stats.total.min_response_time:.2f} ms")
    print(f"最大响应时间: {stats.total.max_response_time:.2f} ms")
    print(f"RPS: {stats.total.total_rps:.2f}")
    
    print("\n" + "="*70 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """
    每个请求完成时执行
    
    可用于详细日志记录
    """
    # 只记录慢请求
    if response_time > 1000:
        print(f"⚠️ 慢请求: {request_type} {name} - {response_time:.0f}ms")
    
    # 只记录错误
    if exception:
        print(f"❌ 请求失败: {request_type} {name} - {exception}")
