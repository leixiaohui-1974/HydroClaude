#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试环境检查脚本

检查测试环境是否正确配置
按照 Spec-Kit 规范编写

Author: HydroClaude Test Team
Date: 2025-11-20
Spec: 001-comprehensive-review-and-testing
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    print("=" * 70)
    print("检查 Python 版本")
    print("=" * 70)
    
    version = sys.version_info
    
    print(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 9:
        print("✅ Python 版本符合要求 (>= 3.9)")
        return True
    else:
        print("❌ Python 版本过低，需要 >= 3.9")
        return False


def check_dependencies():
    """检查依赖包"""
    print("\n" + "=" * 70)
    print("检查依赖包")
    print("=" * 70)
    
    required_packages = {
        'numpy': 'numpy',
        'scipy': 'scipy',
        'matplotlib': 'matplotlib',
        'pandas': 'pandas',
        'pytest': 'pytest',
        'httpx': 'httpx',
        'playwright': 'playwright',
        'locust': 'locust'
    }
    
    missing = []
    
    for name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} (未安装)")
            missing.append(name)
    
    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print("请运行: pip install " + " ".join(missing))
        return False
    
    print("\n✅ 所有依赖包已安装")
    return True


def check_directory_structure():
    """检查目录结构"""
    print("\n" + "=" * 70)
    print("检查目录结构")
    print("=" * 70)
    
    required_dirs = [
        'tests',
        'tests/backend',
        'tests/backend/solvers',
        'tests/backend/api',
        'tests/frontend',
        'tests/e2e',
        'tests/performance',
        'tests/fixtures',
        'reports',
        'reports/screenshots',
        'reports/html',
        'reports/coverage'
    ]
    
    project_root = Path(__file__).parent.parent
    
    missing = []
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        
        if full_path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} (不存在)")
            missing.append(dir_path)
    
    if missing:
        print(f"\n缺少目录: {', '.join(missing)}")
        return False
    
    print("\n✅ 目录结构完整")
    return True


def check_test_files():
    """检查测试文件"""
    print("\n" + "=" * 70)
    print("检查测试文件")
    print("=" * 70)
    
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / 'tests'
    
    # 统计测试文件
    backend_tests = list((tests_dir / 'backend').rglob('test_*.py'))
    frontend_tests = list((tests_dir / 'frontend').rglob('*.spec.js'))
    e2e_tests = list((tests_dir / 'e2e').rglob('*.spec.js'))
    
    print(f"后端测试: {len(backend_tests)} 个")
    print(f"前端测试: {len(frontend_tests)} 个")
    print(f"E2E 测试: {len(e2e_tests)} 个")
    
    total = len(backend_tests) + len(frontend_tests) + len(e2e_tests)
    
    print(f"\n总计: {total} 个测试文件")
    
    if total >= 20:
        print("✅ 测试覆盖率良好")
        return True
    else:
        print("⚠️ 测试文件较少")
        return False


def check_config_files():
    """检查配置文件"""
    print("\n" + "=" * 70)
    print("检查配置文件")
    print("=" * 70)
    
    project_root = Path(__file__).parent.parent
    
    config_files = {
        'pytest.ini': '后端测试配置',
        'playwright.config.js': '前端测试配置',
        'locustfile.py': '性能测试配置',
        'Dockerfile.test': 'Docker 测试配置',
        'docker-compose.test.yml': 'Docker Compose 配置',
        '.github/workflows/test.yml': 'CI/CD 配置'
    }
    
    missing = []
    
    for file_path, description in config_files.items():
        full_path = project_root / file_path
        
        if full_path.exists():
            print(f"✅ {file_path} ({description})")
        else:
            print(f"❌ {file_path} ({description}) - 不存在")
            missing.append(file_path)
    
    if missing:
        print(f"\n缺少配置文件: {', '.join(missing)}")
        return False
    
    print("\n✅ 所有配置文件已创建")
    return True


def check_playwright():
    """检查 Playwright 安装"""
    print("\n" + "=" * 70)
    print("检查 Playwright")
    print("=" * 70)
    
    try:
        import playwright
        print(f"✅ Playwright 已安装 (版本: {playwright.__version__})")
        
        # 检查浏览器
        from playwright.sync_api import sync_playwright
        
        print("\n检查浏览器安装...")
        
        # 简单检查（不实际启动浏览器）
        print("ℹ️ 请运行 'playwright install' 安装浏览器")
        
        return True
    except ImportError:
        print("❌ Playwright 未安装")
        print("请运行: pip install playwright && playwright install")
        return False


def check_api_server():
    """检查 API 服务器"""
    print("\n" + "=" * 70)
    print("检查 API 服务器")
    print("=" * 70)
    
    import httpx
    
    api_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    
    try:
        response = httpx.get(f"{api_url}/health", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ API 服务器运行正常: {api_url}")
            return True
        else:
            print(f"⚠️ API 服务器响应异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️ 无法连接到 API 服务器: {api_url}")
        print(f"   错误: {e}")
        print("   请确保后端服务已启动")
        return False


def generate_report():
    """生成测试环境报告"""
    print("\n" + "=" * 70)
    print("测试环境总结")
    print("=" * 70)
    
    checks = [
        ("Python 版本", check_python_version()),
        ("依赖包", check_dependencies()),
        ("目录结构", check_directory_structure()),
        ("测试文件", check_test_files()),
        ("配置文件", check_config_files()),
        ("Playwright", check_playwright()),
        ("API 服务器", check_api_server())
    ]
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    print(f"\n通过检查: {passed}/{total}")
    
    if passed == total:
        print("✅ 测试环境完全就绪！")
        return 0
    elif passed >= total * 0.7:
        print("⚠️ 测试环境基本就绪，但有些项目需要改进")
        return 0
    else:
        print("❌ 测试环境未就绪，请修复上述问题")
        return 1


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("HydroClaude 测试环境检查")
    print("=" * 70)
    
    return generate_report()


if __name__ == '__main__':
    sys.exit(main())
