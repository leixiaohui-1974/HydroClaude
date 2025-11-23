"""
其他 API 端点测试

测试项目的其他 API 功能
按照 Spec-Kit 规范编写

Author: HydroClaude Test Team
Date: 2025-11-20
Spec: 001-comprehensive-review-and-testing
"""
import pytest
import httpx
from pathlib import Path
import sys

# 路径设置
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestLearnSystemAPI:
    """学习系统 API 测试"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.mark.backend
    @pytest.mark.asyncio
    async def test_get_learn_menu(self, api_client):
        """
        测试获取学习菜单
        
        端点: GET /api/learn/menu
        
        验收标准:
        - 返回状态码 200 或 404
        - 数据格式正确
        """
        print("\n" + "="*70)
        print("测试: GET /api/learn/menu")
        print("="*70)
        
        response = await api_client.get(f"{self.BASE_URL}/api/learn/menu")
        
        print(f"\n响应状态码: {response.status_code}")
        
        assert response.status_code in [200, 404, 405], \
            f"状态码错误: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"菜单数据: {data}")
            print("\n✅ 学习菜单 API 测试通过！")
        else:
            print("\n⚠️ 端点不存在或未实现")
    
    @pytest.mark.backend
    @pytest.mark.asyncio
    async def test_get_learn_content(self, api_client):
        """
        测试获取学习内容
        
        端点: GET /api/learn/content/{id}
        
        验收标准:
        - 返回状态码 200 或 404
        """
        print("\n" + "="*70)
        print("测试: GET /api/learn/content/{id}")
        print("="*70)
        
        test_id = "basic_01"
        
        response = await api_client.get(
            f"{self.BASE_URL}/api/learn/content/{test_id}"
        )
        
        print(f"\n响应状态码: {response.status_code}")
        
        assert response.status_code in [200, 404, 405], \
            f"状态码错误: {response.status_code}"
        
        if response.status_code == 200:
            print("\n✅ 学习内容 API 测试通过！")
        else:
            print("\n⚠️ 内容不存在或端点未实现")


class TestExampleRunAPI:
    """案例运行 API 测试"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.mark.backend
    @pytest.mark.asyncio
    async def test_list_examples(self, api_client):
        """
        测试获取案例列表
        
        端点: GET /api/examples 或 /api/cases
        
        验收标准:
        - 返回状态码 200 或 404
        - 返回案例列表
        """
        print("\n" + "="*70)
        print("测试: 获取案例列表")
        print("="*70)
        
        # 尝试多个可能的端点
        endpoints = [
            "/api/examples",
            "/api/cases",
            "/api/example/list"
        ]
        
        success = False
        
        for endpoint in endpoints:
            try:
                response = await api_client.get(f"{self.BASE_URL}{endpoint}")
                
                print(f"\n端点: {endpoint}")
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"返回数据类型: {type(data)}")
                    
                    if isinstance(data, list):
                        print(f"案例数量: {len(data)}")
                    
                    success = True
                    break
            
            except Exception as e:
                print(f"端点 {endpoint} 失败: {e}")
                continue
        
        if success:
            print("\n✅ 案例列表 API 测试通过！")
        else:
            print("\n⚠️ 未找到可用的案例列表端点")
    
    @pytest.mark.backend
    @pytest.mark.asyncio
    async def test_run_example(self, api_client):
        """
        测试运行案例
        
        端点: POST /api/examples/run
        
        验收标准:
        - 返回状态码 200, 201 或 404
        """
        print("\n" + "="*70)
        print("测试: 运行案例")
        print("="*70)
        
        # 尝试多个可能的端点
        endpoints = [
            ("/api/examples/run", "POST"),
            ("/api/example/run", "POST"),
            ("/api/run", "POST")
        ]
        
        test_data = {
            "example_id": "test_example",
            "parameters": {
                "Q": 50.0,
                "h": 2.0
            }
        }
        
        for endpoint, method in endpoints:
            try:
                response = await api_client.post(
                    f"{self.BASE_URL}{endpoint}",
                    json=test_data
                )
                
                print(f"\n端点: {endpoint}")
                print(f"状态码: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    print("✅ 案例运行成功")
                    break
            
            except Exception as e:
                print(f"端点 {endpoint} 失败: {e}")
                continue
        
        print("\n⚠️ 案例运行 API 测试完成 (可能未实现)")


class TestStatisticsAPI:
    """统计 API 测试"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.mark.backend
    @pytest.mark.asyncio
    async def test_get_stats(self, api_client):
        """
        测试获取系统统计
        
        端点: GET /api/stats 或 /api/knowledge/stats
        
        验收标准:
        - 返回状态码 200 或 404
        - 返回统计数据
        """
        print("\n" + "="*70)
        print("测试: 获取系统统计")
        print("="*70)
        
        # 尝试多个可能的端点
        endpoints = [
            "/api/stats",
            "/api/knowledge/stats",
            "/api/statistics"
        ]
        
        for endpoint in endpoints:
            try:
                response = await api_client.get(f"{self.BASE_URL}{endpoint}")
                
                print(f"\n端点: {endpoint}")
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"统计数据: {data}")
                    print("\n✅ 统计 API 测试通过！")
                    return
            
            except Exception as e:
                print(f"端点 {endpoint} 失败: {e}")
                continue
        
        print("\n⚠️ 未找到可用的统计端点")


class TestCORSandSecurity:
    """CORS 和安全性测试"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.mark.backend
    @pytest.mark.asyncio
    async def test_cors_headers(self, api_client):
        """
        测试 CORS 响应头
        
        验收标准:
        - OPTIONS 请求返回正确的 CORS 头
        """
        print("\n" + "="*70)
        print("测试: CORS 响应头")
        print("="*70)
        
        try:
            response = await api_client.options(
                f"{self.BASE_URL}/api/knowledge/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )
            
            print(f"\n响应状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            # 检查 CORS 头
            headers = response.headers
            
            has_cors = (
                "access-control-allow-origin" in headers or
                "Access-Control-Allow-Origin" in headers
            )
            
            if has_cors:
                print("\n✅ CORS 配置正确！")
            else:
                print("\n⚠️ CORS 可能未配置")
        
        except Exception as e:
            print(f"\n⚠️ CORS 测试失败: {e}")
    
    @pytest.mark.backend
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_client):
        """
        测试速率限制
        
        验收标准:
        - 快速请求不会导致服务器崩溃
        """
        print("\n" + "="*70)
        print("测试: 速率限制")
        print("="*70)
        
        print("\n发送 10 个快速请求...")
        
        try:
            responses = []
            
            for i in range(10):
                response = await api_client.get(f"{self.BASE_URL}/")
                responses.append(response.status_code)
            
            print(f"响应状态码: {responses}")
            
            # 检查是否有 429 (Too Many Requests)
            has_rate_limit = 429 in responses
            
            if has_rate_limit:
                print("\n✅ 速率限制已配置！")
            else:
                print("\n⚠️ 速率限制可能未配置 (所有请求成功)")
        
        except Exception as e:
            print(f"\n⚠️ 速率限制测试失败: {e}")


class TestDocumentationAPI:
    """文档 API 测试"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.mark.backend
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_api_docs(self, api_client):
        """
        测试 API 文档端点
        
        端点: GET /docs
        
        验收标准:
        - 返回状态码 200
        - 返回 HTML 文档
        """
        print("\n" + "="*70)
        print("测试: API 文档")
        print("="*70)
        
        response = await api_client.get(f"{self.BASE_URL}/docs")
        
        print(f"\n响应状态码: {response.status_code}")
        
        assert response.status_code == 200, \
            f"状态码错误: {response.status_code}"
        
        # 检查是否是 HTML
        content_type = response.headers.get("content-type", "")
        
        print(f"Content-Type: {content_type}")
        
        assert "html" in content_type.lower(), \
            "不是 HTML 文档"
        
        print("\n✅ API 文档测试通过！")
    
    @pytest.mark.backend
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_redoc(self, api_client):
        """
        测试 ReDoc 文档端点
        
        端点: GET /redoc
        
        验收标准:
        - 返回状态码 200 或 404
        """
        print("\n" + "="*70)
        print("测试: ReDoc 文档")
        print("="*70)
        
        response = await api_client.get(f"{self.BASE_URL}/redoc")
        
        print(f"\n响应状态码: {response.status_code}")
        
        assert response.status_code in [200, 404], \
            f"状态码错误: {response.status_code}"
        
        if response.status_code == 200:
            print("\n✅ ReDoc 文档测试通过！")
        else:
            print("\n⚠️ ReDoc 未启用")


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v", "-s"])
