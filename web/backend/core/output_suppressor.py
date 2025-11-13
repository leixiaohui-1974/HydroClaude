#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
输出抑制器 - 用于在Windows环境下避免编码错误
"""

import sys
import os
from contextlib import contextmanager
from io import StringIO

@contextmanager
def suppress_output():
    """
    上下文管理器：临时抑制所有stdout和stderr输出
    
    用法:
        with suppress_output():
            # 这里的所有print和输出都会被抑制
            some_function_that_prints()
    """
    # 保存原始的stdout和stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        # 重定向到StringIO（丢弃所有输出）
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        yield
    finally:
        # 恢复原始输出
        sys.stdout = old_stdout
        sys.stderr = old_stderr


@contextmanager
def safe_output():
    """
    上下文管理器：在Windows环境下使用安全的UTF-8输出
    """
    if sys.platform != 'win32':
        # 非Windows环境，不需要特殊处理
        yield
        return
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        # 在Windows下，确保使用UTF-8编码并忽略错误
        import io
        sys.stdout = io.TextIOWrapper(
            old_stdout.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )
        sys.stderr = io.TextIOWrapper(
            old_stderr.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr






