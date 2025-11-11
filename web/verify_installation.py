#!/usr/bin/env python3
"""
HydroClaude Web - 快速安装验证脚本
一键验证整个系统是否正常工作

使用方法:
  python verify_installation.py

可选参数:
  --skip-backend    跳过后端测试
  --skip-frontend   跳过前端测试
  --quick          快速模式（仅基础测试）
"""

import sys
import argparse
import time
import json
import subprocess
from pathlib import Path
from typing import Tuple, Optional

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text: str):
    """打印成功消息"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    """打印错误消息"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text: str):
    """打印警告消息"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text: str):
    """打印信息"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def run_command(cmd: str, check: bool = True) -> Tuple[int, str, str]:
    """运行shell命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except Exception as e:
        return -1, "", str(e)

def check_python_version() -> bool:
    """检查Python版本"""
    print_info("检查Python版本...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print_success(f"Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python版本不符合要求: {version.major}.{version.minor} (需要 >= 3.8)")
        return False

def check_required_packages() -> bool:
    """检查必需的Python包"""
    print_info("检查必需的Python包...")

    required_packages = [
        'numpy',
        'scipy',
        'matplotlib',
        'fastapi',
        'uvicorn',
        'pydantic',
        'requests'
    ]

    optional_packages = [
        'numba'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print_error(f"缺少必需包: {', '.join(missing)}")
        print_info(f"安装命令: pip install {' '.join(missing)}")
        return False

    print_success("所有必需包已安装")

    # 检查可选包
    for package in optional_packages:
        try:
            __import__(package)
            print_success(f"可选包已安装: {package}")
        except ImportError:
            print_warning(f"可选包未安装: {package} (推荐安装以获得8.8x加速)")

    return True

def check_project_structure() -> bool:
    """检查项目结构"""
    print_info("检查项目结构...")

    base_path = Path(__file__).parent.parent
    required_paths = [
        'web/backend/api_gateway',
        'web/backend/simulation_engine',
        'web/frontend/src',
        'web/config_templates',
        'solvers',
        'docs'
    ]

    missing = []
    for path_str in required_paths:
        path = base_path / path_str
        if not path.exists():
            missing.append(path_str)

    if missing:
        print_error(f"缺少目录: {', '.join(missing)}")
        return False

    print_success("项目结构完整")
    return True

def check_backend_health() -> bool:
    """检查后端服务"""
    print_info("检查后端服务...")

    try:
        import requests
        response = requests.get('http://localhost:8000/health', timeout=5)

        if response.status_code == 200:
            data = response.json()
            print_success(f"后端服务正常: {data.get('service')}")
            print_info(f"  版本: {data.get('version')}")
            return True
        else:
            print_error(f"后端响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("后端服务未启动 (http://localhost:8000)")
        print_info("启动命令: cd web/backend && ./start_server.sh")
        return False
    except Exception as e:
        print_error(f"检查后端时出错: {str(e)}")
        return False

def check_frontend_service() -> bool:
    """检查前端服务"""
    print_info("检查前端服务...")

    try:
        import requests
        response = requests.get('http://localhost:5173', timeout=5)

        if response.status_code == 200:
            print_success("前端服务正常 (http://localhost:5173)")
            return True
        else:
            print_error(f"前端响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("前端服务未启动 (http://localhost:5173)")
        print_info("启动命令: cd web/frontend && npm run dev")
        return False
    except Exception as e:
        print_error(f"检查前端时出错: {str(e)}")
        return False

def run_quick_simulation() -> bool:
    """运行快速仿真测试"""
    print_info("运行快速仿真测试...")

    try:
        import requests

        # 加载快速测试模板
        template_path = Path(__file__).parent / 'config_templates' / 'quick_test.json'

        if not template_path.exists():
            print_error(f"测试模板不存在: {template_path}")
            return False

        with open(template_path) as f:
            config = json.load(f)

        # 创建仿真
        response = requests.post(
            'http://localhost:8000/api/v1/simulations',
            json=config,
            timeout=10
        )

        if response.status_code != 201:
            print_error(f"创建仿真失败: {response.status_code}")
            print_error(response.text)
            return False

        task_id = response.json()['task_id']
        print_info(f"仿真已创建: {task_id[:8]}...")

        # 等待完成
        max_wait = 30
        wait_time = 0
        interval = 1

        while wait_time < max_wait:
            status_response = requests.get(
                f'http://localhost:8000/api/v1/simulations/{task_id}/status',
                timeout=5
            )
            status_data = status_response.json()
            status = status_data['status']

            if status == 'completed':
                duration = status_data.get('duration', 0)
                print_success(f"仿真完成，耗时: {duration:.3f}秒")

                # 获取结果验证
                results_response = requests.get(
                    f'http://localhost:8000/api/v1/simulations/{task_id}/results',
                    timeout=10
                )

                if results_response.status_code == 200:
                    results = results_response.json()
                    metrics = results['metrics']

                    # 验证关键指标
                    mass_error = abs(metrics.get('mass_conservation_error', 1.0))
                    if mass_error < 0.05:
                        print_success(f"质量守恒: {mass_error*100:.4f}%")
                    else:
                        print_warning(f"质量守恒误差较大: {mass_error*100:.2f}%")

                    print_info(f"  最大Froude数: {metrics.get('max_froude', 0):.4f}")
                    print_info(f"  最小水深: {metrics.get('min_depth', 0):.4f} m")

                    return True
                else:
                    print_error("获取结果失败")
                    return False

            elif status == 'failed':
                error = status_data.get('error', 'Unknown error')
                print_error(f"仿真失败: {error}")
                return False

            time.sleep(interval)
            wait_time += interval

        print_error("仿真超时")
        return False

    except Exception as e:
        print_error(f"仿真测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_config_templates() -> bool:
    """检查配置模板"""
    print_info("检查配置模板...")

    template_dir = Path(__file__).parent / 'config_templates'
    if not template_dir.exists():
        print_error("配置模板目录不存在")
        return False

    required_templates = [
        'basic_steady_flow.json',
        'quick_test.json',
        'dam_break_stable.json',
        'flood_routing.json'
    ]

    missing = []
    for template in required_templates:
        if not (template_dir / template).exists():
            missing.append(template)

    if missing:
        print_error(f"缺少模板: {', '.join(missing)}")
        return False

    print_success(f"配置模板完整 ({len(required_templates)}个)")
    return True

def check_documentation() -> bool:
    """检查文档"""
    print_info("检查文档...")

    base_path = Path(__file__).parent
    required_docs = [
        'PARAMETER_SELECTION_GUIDE.md',
        'config_templates/README.md',
        'QUICK_START.md',
        'TESTING_GUIDE.md'
    ]

    missing = []
    for doc in required_docs:
        if not (base_path / doc).exists():
            missing.append(doc)

    if missing:
        print_warning(f"部分文档缺失: {', '.join(missing)}")
        return True  # 文档缺失不算致命错误

    print_success(f"文档完整 ({len(required_docs)}个)")
    return True

def print_summary(results: dict):
    """打印总结"""
    print_header("验证结果总结")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"\n{'测试项':<30} {'结果'}")
    print("-" * 50)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:<30} {status}")

    print("-" * 50)
    print(f"{'总计:':<30} {passed}/{total}")
    print(f"{'通过率:':<30} {passed/total*100:.1f}%\n")

    if failed == 0:
        print_success("🎉 所有验证通过！系统运行正常。")
        print_info("\n下一步:")
        print_info("  1. 访问 http://localhost:5173 使用Web界面")
        print_info("  2. 阅读 PARAMETER_SELECTION_GUIDE.md 学习参数选择")
        print_info("  3. 尝试配置模板: config_templates/")
    else:
        print_error(f"⚠️  {failed} 项验证失败，请检查上述错误。")
        print_info("\n常见问题:")
        print_info("  1. 服务未启动 → 运行 start_server.sh")
        print_info("  2. 缺少包 → pip install -r requirements.txt")
        print_info("  3. 端口被占用 → 修改配置或停止冲突进程")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='HydroClaude Web 安装验证')
    parser.add_argument('--skip-backend', action='store_true', help='跳过后端测试')
    parser.add_argument('--skip-frontend', action='store_true', help='跳过前端测试')
    parser.add_argument('--quick', action='store_true', help='快速模式')
    args = parser.parse_args()

    print_header("HydroClaude Web - 安装验证")
    print_info(f"日期: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"位置: {Path(__file__).parent.absolute()}\n")

    results = {}

    # 基础检查
    print_header("1. 基础环境检查")
    results['Python版本'] = check_python_version()
    results['必需包'] = check_required_packages()
    results['项目结构'] = check_project_structure()
    results['配置模板'] = check_config_templates()
    results['文档'] = check_documentation()

    # 服务检查
    if not args.skip_backend:
        print_header("2. 后端服务检查")
        results['后端服务'] = check_backend_health()

        if results['后端服务'] and not args.quick:
            results['快速仿真'] = run_quick_simulation()

    if not args.skip_frontend:
        print_header("3. 前端服务检查")
        results['前端服务'] = check_frontend_service()

    # 打印总结
    print_summary(results)

    # 返回退出码
    return 0 if all(results.values()) else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_warning("\n\n验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\n验证过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
