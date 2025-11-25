#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Examples测试套件
使用pytest进行自动化测试
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import sys
import os
from pathlib import Path
import subprocess
import time

# 添加项目根目录
examples_root = Path(__file__).parent.parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestExampleExecution:
    """测试示例执行"""

    # 定义要测试的示例列表
    EXAMPLES_TO_TEST = [
        ('example_01_canal_flow', 'code/01_basic.py', 30),
        ('example_02_pump_system', 'code/example_02_pump_system.py', 10),
        ('example_03_turbine_demo', 'example_03_turbine_comparison.py', 10),
        ('example_05_transient_analysis', 'example_05_load_rejection.py', 10),
        ('example_08_load_acceptance', 'example_08_load_acceptance.py', 10),
        ('example_17_reservoir_basic', 'demo_reservoir.py', 10),
    ]

    @pytest.mark.parametrize("example_name,script_path,timeout", EXAMPLES_TO_TEST)
    def test_example_runs_successfully(self, example_name, script_path, timeout):
        """测试示例能够成功运行"""
        example_dir = examples_root / example_name
        script_file = example_dir / script_path

        assert example_dir.exists(), f"示例目录不存在: {example_dir}"
        assert script_file.exists(), f"脚本文件不存在: {script_file}"

        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(examples_root.parent)
        env['MPLBACKEND'] = 'Agg'

        # 运行脚本
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=str(example_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        assert result.returncode == 0, f"脚本运行失败:\n{result.stderr}"

    @pytest.mark.parametrize("example_name,script_path,timeout", EXAMPLES_TO_TEST)
    def test_example_generates_output(self, example_name, script_path, timeout):
        """测试示例生成输出文件"""
        example_dir = examples_root / example_name

        # 先运行示例
        script_file = example_dir / script_path

        env = os.environ.copy()
        env['PYTHONPATH'] = str(examples_root.parent)
        env['MPLBACKEND'] = 'Agg'

        subprocess.run(
            [sys.executable, str(script_file)],
            cwd=str(example_dir),
            env=env,
            capture_output=True,
            timeout=timeout
        )

        # 检查是否生成了输出文件（PNG或GIF）
        outputs_dir = example_dir / 'outputs'
        has_output = False

        if outputs_dir.exists():
            png_files = list(outputs_dir.rglob('*.png'))
            gif_files = list(outputs_dir.rglob('*.gif'))
            has_output = len(png_files) > 0 or len(gif_files) > 0

        # 如果outputs目录不存在，检查根目录
        if not has_output:
            png_files = list(example_dir.glob('*.png'))
            gif_files = list(example_dir.glob('*.gif'))
            has_output = len(png_files) > 0 or len(gif_files) > 0

        assert has_output, f"示例未生成任何输出文件（PNG或GIF）"


class TestExampleStructure:
    """测试示例目录结构"""

    def get_all_examples(self):
        """获取所有示例目录"""
        return sorted([d for d in examples_root.glob('example_*') if d.is_dir()])

    @pytest.mark.parametrize("example_dir", get_all_examples(None))
    def test_example_has_readme(self, example_dir):
        """测试每个示例都有README"""
        readme = example_dir / 'README.md'
        assert readme.exists(), f"缺少README.md: {example_dir.name}"

    @pytest.mark.parametrize("example_dir", get_all_examples(None))
    def test_example_has_script(self, example_dir):
        """测试每个示例都有可执行脚本"""
        # 检查code目录或根目录是否有Python脚本
        code_dir = example_dir / 'code'
        has_script = False

        if code_dir.exists():
            scripts = [f for f in code_dir.glob('*.py')
                      if f.name != '__init__.py' and not f.name.startswith('test_')]
            has_script = len(scripts) > 0

        if not has_script:
            scripts = [f for f in example_dir.glob('*.py')
                      if f.name != '__init__.py' and not f.name.startswith('test_')]
            has_script = len(scripts) > 0

        assert has_script, f"示例没有可执行脚本: {example_dir.name}"

    @pytest.mark.parametrize("example_dir", get_all_examples(None))
    def test_example_has_outputs_dir(self, example_dir):
        """测试每个示例都有outputs目录"""
        outputs_dir = example_dir / 'outputs'
        # outputs目录应该存在（由整理脚本创建）
        assert outputs_dir.exists(), f"缺少outputs目录: {example_dir.name}"


class TestAnimationQuality:
    """测试动画质量"""

    def get_examples_with_animations(self):
        """获取有动画的示例"""
        examples_with_gifs = []
        for example_dir in examples_root.glob('example_*'):
            animations_dir = example_dir / 'outputs' / 'animations'
            if animations_dir.exists():
                gifs = list(animations_dir.glob('*.gif'))
                if gifs:
                    examples_with_gifs.append((example_dir, gifs))
        return examples_with_gifs

    @pytest.mark.parametrize("example_dir,gif_files", get_examples_with_animations(None))
    def test_gif_file_size_reasonable(self, example_dir, gif_files):
        """测试GIF文件大小合理（<5MB）"""
        for gif in gif_files:
            size_mb = gif.stat().st_size / (1024 * 1024)
            assert size_mb < 5.0, f"GIF文件过大: {gif.name} ({size_mb:.2f}MB)"

    @pytest.mark.parametrize("example_dir,gif_files", get_examples_with_animations(None))
    def test_gif_file_exists(self, example_dir, gif_files):
        """测试GIF文件存在且非空"""
        for gif in gif_files:
            assert gif.exists(), f"GIF文件不存在: {gif}"
            assert gif.stat().st_size > 0, f"GIF文件为空: {gif}"


class TestPerformance:
    """性能测试"""

    @pytest.mark.slow
    def test_example01_basic_performance(self):
        """测试example_01基础版本的性能"""
        example_dir = examples_root / 'example_01_canal_flow'
        script_file = example_dir / 'code' / '01_basic.py'

        env = os.environ.copy()
        env['PYTHONPATH'] = str(examples_root.parent)
        env['MPLBACKEND'] = 'Agg'

        start_time = time.time()

        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=str(example_dir),
            env=env,
            capture_output=True,
            timeout=30
        )

        elapsed_time = time.time() - start_time

        assert result.returncode == 0, "脚本运行失败"
        assert elapsed_time < 15.0, f"运行时间过长: {elapsed_time:.2f}秒 (期望<15秒)"

    @pytest.mark.slow
    def test_example03_turbine_performance(self):
        """测试example_03水轮机示例的性能"""
        example_dir = examples_root / 'example_03_turbine_demo'
        script_file = example_dir / 'example_03_turbine_comparison.py'

        env = os.environ.copy()
        env['PYTHONPATH'] = str(examples_root.parent)
        env['MPLBACKEND'] = 'Agg'

        start_time = time.time()

        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=str(example_dir),
            env=env,
            capture_output=True,
            timeout=10
        )

        elapsed_time = time.time() - start_time

        assert result.returncode == 0, "脚本运行失败"
        assert elapsed_time < 5.0, f"运行时间过长: {elapsed_time:.2f}秒 (期望<5秒)"


@pytest.fixture(scope="session")
def examples_root_fixture():
    """提供examples根目录的fixture"""
    return examples_root


# 可以运行的命令：
# pytest examples/tests/test_examples.py -v
# pytest examples/tests/test_examples.py -v -k "structure"  # 只运行结构测试
# pytest examples/tests/test_examples.py -v -m "not slow"  # 跳过慢速测试
# pytest examples/tests/test_examples.py -v --maxfail=1   # 第一个失败后停止
