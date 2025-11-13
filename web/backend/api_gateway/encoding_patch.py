#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows编码补丁 - 商业级解决方案
在应用启动时自动修复所有编码问题
"""

import sys
import os
import io
import warnings

def apply_windows_encoding_patch():
    """
    应用Windows编码补丁
    确保在Windows环境下所有输出都使用UTF-8编码
    """
    
    # 1. 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'
    
    # 2. 禁用所有警告
    warnings.filterwarnings('ignore')
    
    # 3. 禁用Numba警告
    os.environ['NUMBA_DISABLE_PERFORMANCE_WARNINGS'] = '1'
    os.environ['NUMBA_WARNINGS'] = '0'
    
    # 4. 重新配置stdout和stderr
    if sys.platform == 'win32':
        # 使用UTF-8包装器替换标准流
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace',  # 替换无法编码的字符
                line_buffering=True
            )
        
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=True
            )
    
    # 5. Monkey patch print函数，确保安全输出
    import builtins
    _original_print = builtins.print
    
    def safe_print(*args, **kwargs):
        """安全的print函数，自动处理编码问题"""
        try:
            # 尝试正常打印
            _original_print(*args, **kwargs)
        except UnicodeEncodeError:
            # 如果出现编码错误，移除特殊字符后重试
            safe_args = []
            for arg in args:
                try:
                    safe_arg = str(arg).encode('ascii', 'ignore').decode('ascii')
                    safe_args.append(safe_arg)
                except:
                    safe_args.append('[encoding error]')
            try:
                _original_print(*safe_args, **kwargs)
            except:
                pass  # 完全静默失败
    
    builtins.print = safe_print
    
    # 6. 设置默认编码
    if hasattr(sys, 'setdefaultencoding'):
        sys.setdefaultencoding('utf-8')
    
    return True


# 在模块导入时自动应用补丁
_patch_applied = apply_windows_encoding_patch()






