#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude - 世界级水力学仿真平台

Setup script for Python package installation.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read version from __init__.py
version = {}
with open(os.path.join(this_directory, '__init__.py'), encoding='utf-8') as f:
    exec(f.read(), version)

setup(
    name='hydroclaude',
    version='2.0.0',
    author='HydroClaude Development Team',
    author_email='dev@hydroclaude.org',
    description='世界级水力学仿真平台',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/your-org/hydroclaude',
    project_urls={
        'Bug Reports': 'https://github.com/your-org/hydroclaude/issues',
        'Source': 'https://github.com/your-org/hydroclaude',
        'Documentation': 'https://hydroclaude.org/docs',
        'Changelog': 'https://github.com/your-org/hydroclaude/blob/main/CHANGELOG.md',
    },
    packages=find_packages(exclude=['tests', 'tests.*', 'examples', 'examples.*', 'web', 'web.*']),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Hydrology',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
        'Natural Language :: Chinese (Simplified)',
        'Natural Language :: English',
    ],
    keywords='hydraulics, simulation, open-channel-flow, pipe-network, water-hammer, engineering',
    python_requires='>=3.12',
    install_requires=[
        'numpy>=1.24.0',
        'scipy>=1.10.0',
        'matplotlib>=3.7.0',
        'fastapi>=0.100.0',
        'uvicorn>=0.23.0',
        'pydantic>=2.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'pytest-html>=3.2.0',
            'black>=23.0.0',
            'pylint>=2.17.0',
            'mypy>=1.4.0',
        ],
        'test': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'pytest-html>=3.2.0',
            'requests>=2.31.0',
        ],
        'docs': [
            'sphinx>=7.0.0',
            'sphinx-rtd-theme>=1.3.0',
            'myst-parser>=2.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'hydroclaude=main:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
