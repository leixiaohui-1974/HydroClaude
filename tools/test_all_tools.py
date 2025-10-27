#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 工具测试脚本

测试所有AI开发工具是否正常工作

Author: HydroClaude Development Team
Date: 2025-10-27
"""

import sys
import os
from pathlib import Path
import subprocess
import tempfile
import shutil

# ========== 测试配置 ==========

TESTS = []
RESULTS = []

def test(name):
    """测试装饰器"""
    def decorator(func):
        TESTS.append((name, func))
        return func
    return decorator

def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def print_result(name, passed, message=""):
    """打印测试结果"""
    status = "✅ 通过" if passed else "❌ 失败"
    print(f"{status}: {name}")
    if message:
        print(f"   {message}")
    RESULTS.append((name, passed, message))

# ========== 测试函数 ==========

@test("检查 .cursorrules 文件存在")
def test_cursorrules_exists():
    """测试.cursorrules文件是否存在"""
    path = Path('.cursorrules')
    if not path.exists():
        return False, ".cursorrules 文件不存在"
    
    content = path.read_text(encoding='utf-8')
    if 'HydrostaticCanalSolver' not in content:
        return False, "文件内容不完整"
    
    return True, f"文件大小: {len(content)} 字节"

@test("检查 EXAMPLES_INDEX.md 文件存在")
def test_examples_index_exists():
    """测试EXAMPLES_INDEX.md文件是否存在"""
    path = Path('EXAMPLES_INDEX.md')
    if not path.exists():
        return False, "EXAMPLES_INDEX.md 文件不存在"
    
    content = path.read_text(encoding='utf-8')
    if '快速查询表' not in content:
        return False, "文件内容不完整"
    
    return True, f"文件大小: {len(content)} 字节"

@test("检查 AI开发工具文档存在")
def test_ai_tools_doc_exists():
    """测试AI_DEVELOPMENT_TOOLS.md文件是否存在"""
    path = Path('AI_DEVELOPMENT_TOOLS.md')
    if not path.exists():
        return False, "AI_DEVELOPMENT_TOOLS.md 文件不存在"
    
    content = path.read_text(encoding='utf-8')
    if '工具概述' not in content:
        return False, "文件内容不完整"
    
    return True, f"文件大小: {len(content)} 字节"

@test("检查 check_library_usage.py 存在并可运行")
def test_check_library_usage():
    """测试检查工具是否可用"""
    script = Path('tools/check_library_usage.py')
    if not script.exists():
        return False, "tools/check_library_usage.py 不存在"
    
    # 测试是否可以运行（显示帮助）
    try:
        # 不提供参数会显示用法信息
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=5
        )
        # 预期返回1（因为没有提供参数）
        if '用法' in result.stdout or '用法' in result.stderr:
            return True, "脚本可以正常运行"
        else:
            return False, "脚本运行异常"
    except Exception as e:
        return False, f"运行失败: {str(e)}"

@test("检查 create_example.py 存在并可运行")
def test_create_example():
    """测试代码生成器是否可用"""
    script = Path('tools/create_example.py')
    if not script.exists():
        return False, "tools/create_example.py 不存在"
    
    # 测试是否可以运行（显示帮助）
    try:
        result = subprocess.run(
            [sys.executable, str(script), '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and 'usage' in result.stdout.lower():
            return True, "脚本可以正常运行"
        else:
            return False, "脚本运行异常"
    except Exception as e:
        return False, f"运行失败: {str(e)}"

@test("检查 .pre-commit-config.yaml 存在")
def test_precommit_config():
    """测试pre-commit配置文件是否存在"""
    path = Path('.pre-commit-config.yaml')
    if not path.exists():
        return False, ".pre-commit-config.yaml 文件不存在"
    
    content = path.read_text(encoding='utf-8')
    if 'check-library-usage' not in content:
        return False, "配置文件不完整"
    
    return True, "配置文件完整"

@test("测试创建示例代码（临时）")
def test_create_example_functional():
    """测试代码生成器功能"""
    script = Path('tools/create_example.py')
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        test_name = "test_example_temp"
        
        try:
            # 运行生成器
            result = subprocess.run(
                [sys.executable, str(script), test_name, "测试示例"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, f"生成失败: {result.stderr}"
            
            # 检查生成的文件
            expected_script = Path(tmpdir) / 'examples' / test_name / f'{test_name}.py'
            expected_readme = Path(tmpdir) / 'examples' / test_name / 'README.md'
            
            if not expected_script.exists():
                return False, "脚本文件未生成"
            
            if not expected_readme.exists():
                return False, "README文件未生成"
            
            # 检查生成的代码是否包含必要的导入
            code = expected_script.read_text(encoding='utf-8')
            if 'HydrostaticCanalSolver' not in code:
                return False, "生成的代码缺少必要的导入"
            
            if 'ResultValidator' not in code:
                return False, "生成的代码缺少验证工具"
            
            return True, "示例代码生成成功"
            
        except Exception as e:
            return False, f"测试失败: {str(e)}"

@test("测试检查工具功能")
def test_check_library_functional():
    """测试检查工具功能"""
    script = Path('tools/check_library_usage.py')
    
    # 创建临时测试文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        # 写入一个使用废弃类的示例
        f.write("""
from solvers.single_canal_solver import SingleCanalSolver

def main():
    solver = SingleCanalSolver()
    pass
""")
        temp_file = f.name
    
    try:
        # 运行检查
        result = subprocess.run(
            [sys.executable, str(script), temp_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # 应该检测到废弃类的使用
        if '废弃' in result.stdout or '废弃' in result.stderr:
            return True, "检查工具正确检测到问题"
        else:
            return False, "检查工具未检测到问题"
            
    except Exception as e:
        return False, f"测试失败: {str(e)}"
    finally:
        # 清理临时文件
        os.unlink(temp_file)

@test("检查 README.md 更新")
def test_readme_updated():
    """测试README是否添加了AI开发者警示区"""
    path = Path('README.md')
    if not path.exists():
        return False, "README.md 不存在"
    
    content = path.read_text(encoding='utf-8')
    if '🤖 AI开发者请注意' not in content:
        return False, "README未添加AI开发者警示区"
    
    if 'EXAMPLES_INDEX.md' not in content:
        return False, "README未引用EXAMPLES_INDEX.md"
    
    return True, "README已正确更新"

# ========== 主测试函数 ==========

def run_all_tests():
    """运行所有测试"""
    print_section("HydroClaude AI开发工具测试")
    
    print(f"\n开始测试 {len(TESTS)} 个项目...")
    
    # 运行所有测试
    for name, test_func in TESTS:
        try:
            passed, message = test_func()
            print_result(name, passed, message)
        except Exception as e:
            print_result(name, False, f"测试异常: {str(e)}")
    
    # 打印总结
    print_section("测试总结")
    
    total = len(RESULTS)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = total - passed
    
    print(f"\n总计: {total} 个测试")
    print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
    print(f"❌ 失败: {failed}")
    
    if failed > 0:
        print("\n失败的测试:")
        for name, passed, message in RESULTS:
            if not passed:
                print(f"  ❌ {name}")
                if message:
                    print(f"     {message}")
    
    print("\n" + "=" * 80)
    
    if failed == 0:
        print("🎉 所有测试通过！工具安装成功！")
        print("\n下一步:")
        print("  1. 查阅 AI_DEVELOPMENT_TOOLS.md 了解使用方法")
        print("  2. 查阅 EXAMPLES_INDEX.md 找到参考代码")
        print("  3. 使用 create_example.py 生成新示例")
        print("  4. 使用 check_library_usage.py 检查代码")
        return 0
    else:
        print("⚠️  部分测试失败，请检查安装")
        return 1

def main():
    """主函数"""
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    return run_all_tests()

if __name__ == '__main__':
    sys.exit(main())
