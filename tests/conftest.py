"""
pytest 全局配置和 Fixtures

按照 Spec-Kit 规范和 HydroClaude 项目宪法编写
"""
import pytest
import asyncio
from httpx import AsyncClient
from pathlib import Path
import sys
import os
import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web" / "backend"))
sys.path.insert(0, str(project_root / "solvers"))
sys.path.insert(0, str(project_root / "utils"))


# ==================== 事件循环 Fixture ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（用于异步测试）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== API 测试 Fixtures ====================

# 使用 pytest_asyncio fixture
import pytest_asyncio
import socket

def is_server_running(host="localhost", port=8000):
    """检查服务器是否运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

@pytest_asyncio.fixture
async def api_client():
    """API 测试客户端"""
    # 如果服务器未运行，跳过测试
    if not is_server_running():
        pytest.skip("API server not running at localhost:8000")

    client = AsyncClient(
        base_url="http://localhost:8000",
        timeout=30.0,
        follow_redirects=True
    )
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def api_base_url():
    """API 基础 URL"""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


# ==================== 路径 Fixtures ====================

@pytest.fixture(scope="session")
def project_root_path():
    """项目根目录路径"""
    return project_root


@pytest.fixture(scope="session")
def tests_root_path():
    """测试根目录路径"""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def screenshot_path():
    """截图保存路径"""
    path = project_root / "reports" / "screenshots"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@pytest.fixture(scope="session")
def baseline_path():
    """基准图像路径"""
    path = project_root / "reports" / "baseline"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@pytest.fixture(scope="session")
def reports_path():
    """测试报告路径"""
    path = project_root / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@pytest.fixture(scope="session")
def fixtures_path():
    """测试数据 Fixtures 路径"""
    path = Path(__file__).parent / "fixtures"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


# ==================== 数据生成 Fixtures ====================

@pytest.fixture
def sample_canal_params():
    """标准明渠参数"""
    return {
        "length": 1000.0,
        "width": 10.0,
        "slope": 0.001,
        "manning_n": 0.025,
        "Q": 50.0,
        "h_downstream": 2.0,
    }


@pytest.fixture
def sample_network_params():
    """标准管网参数"""
    return {
        "nodes": [
            {"id": "N1", "elevation": 100.0, "demand": 0.0},
            {"id": "N2", "elevation": 90.0, "demand": 10.0},
            {"id": "N3", "elevation": 85.0, "demand": 15.0},
        ],
        "pipes": [
            {"id": "P1", "from": "N1", "to": "N2", "length": 1000, "diameter": 0.3},
            {"id": "P2", "from": "N2", "to": "N3", "length": 800, "diameter": 0.25},
        ],
    }


@pytest.fixture
def tolerance_dict():
    """标准容差字典"""
    return {
        "h": 0.01,  # 水深容差 (m)
        "Q": 0.5,   # 流量容差 (m³/s)
        "v": 0.05,  # 速度容差 (m/s)
        "percentage": 0.01,  # 百分比容差 (1%)
    }


# ==================== 工具函数 Fixtures ====================

@pytest.fixture
def compare_with_tolerance():
    """比较函数（带容差）"""
    def _compare(actual, expected, tolerance):
        """
        比较数值是否在容差范围内
        
        Args:
            actual: 实际值
            expected: 期望值
            tolerance: 容差
            
        Returns:
            bool: 是否在容差范围内
        """
        if isinstance(actual, (list, np.ndarray)):
            actual = np.array(actual)
            expected = np.array(expected)
            return np.all(np.abs(actual - expected) <= tolerance)
        else:
            return abs(actual - expected) <= tolerance
    
    return _compare


@pytest.fixture
def calculate_error_percentage():
    """计算误差百分比"""
    def _calculate(actual, expected):
        """
        计算相对误差百分比
        
        Args:
            actual: 实际值
            expected: 期望值
            
        Returns:
            float: 误差百分比
        """
        if expected == 0:
            return 0.0 if actual == 0 else float('inf')
        return abs(actual - expected) / abs(expected) * 100
    
    return _calculate


# ==================== 清理 Fixtures ====================

@pytest.fixture(autouse=True)
def cleanup_temp_files(request):
    """自动清理临时文件"""
    yield
    
    # 测试完成后清理
    temp_dir = project_root / "temp"
    if temp_dir.exists():
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: 无法清理临时目录: {e}")


# ==================== Pytest 钩子函数 ====================

def pytest_configure(config):
    """Pytest 配置钩子"""
    # 确保报告目录存在
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    (reports_dir / "html").mkdir(exist_ok=True)
    (reports_dir / "screenshots").mkdir(exist_ok=True)
    (reports_dir / "baseline").mkdir(exist_ok=True)
    
    print("\n" + "="*70)
    print("HydroClaude 测试套件")
    print("Powered by Spec-Kit Specification-Driven Development")
    print("="*70 + "\n")


def pytest_collection_modifyitems(config, items):
    """修改测试项目收集"""
    for item in items:
        # 为慢速测试添加标记
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.slow)
        
        # 为商业对标测试添加标记
        if "commercial" in item.keywords:
            item.add_marker(pytest.mark.commercial)


def pytest_report_header(config):
    """测试报告头部"""
    return [
        "项目: HydroClaude v2.0.0",
        "规格: 001-comprehensive-review-and-testing",
        "方法论: GitHub Spec-Kit",
    ]
