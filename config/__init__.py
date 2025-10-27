"""
配置文件驱动系统

实现通过YAML配置文件自动化建模和模拟。

核心功能：
- YAML配置文件解析
- 自动参数验证
- 一键创建模型
- 一键运行模拟

使用示例：
    >>> from config import HydraulicModelConfig
    >>> 
    >>> config = HydraulicModelConfig("my_canal.yaml")
    >>> result = config.run_simulation()  # 一行完成！

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

from .config_parser import HydraulicModelConfig, ConfigValidator

__all__ = [
    'HydraulicModelConfig',
    'ConfigValidator',
]

__version__ = '2.2.0-alpha'
