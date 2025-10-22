#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 安装脚本

使用方法:
    pip install -e .           # 开发模式安装（推荐）
    pip install .              # 正式安装
    python setup.py install    # 传统安装
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README
readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    with open(readme_file, 'r', encoding='utf-8') as f:
        long_description = f.read()
else:
    long_description = 'HydroClaude - 水力学仿真与优化框架'

setup(
    name="HydroClaude",
    version="0.2.0",
    author="leixiaohui-1974",
    author_email="",
    description="专业的水力学仿真与优化框架 - 明渠流动、管网系统、梯级水库调度",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/leixiaohui-1974/HydroClaude',
    project_urls={
        'Bug Tracker': 'https://github.com/leixiaohui-1974/HydroClaude/issues',
        'Documentation': 'https://github.com/leixiaohui-1974/HydroClaude/blob/main/README.md',
        'Source Code': 'https://github.com/leixiaohui-1974/HydroClaude',
    },
    packages=find_packages(exclude=['tests*', 'docs*', 'examples*', 'benchmark_results*']),
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "matplotlib>=3.4.0",
        "networkx>=2.6.0",
        "pyyaml>=5.4.0",
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=3.0.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
        ],
        'docs': [
            'sphinx>=4.0.0',
            'sphinx-rtd-theme>=1.0.0',
        ],
        'logging': [
            'colorlog>=6.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'hydroclaude-benchmark=benchmark_suite:main',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Hydrology",
        "Topic :: Scientific/Engineering :: Mathematics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords=[
        'hydraulics', 'hydrology', 'saint-venant',
        'open-channel-flow', 'reservoir', 'optimization',
        'control', 'simulation', 'water-resources',
    ],
    include_package_data=True,
    zip_safe=False,
)
