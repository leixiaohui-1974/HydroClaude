#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一日志系统

为HydroClaude项目提供统一的日志记录功能

特性:
- 多级日志 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 控制台和文件双输出
- 彩色控制台输出（可选）
- 自动日志文件轮转
- 模块化日志器

使用示例:
```python
from core.logging_config import get_logger

logger = get_logger('HydroClaude.Newton')
logger.info("开始Newton求解")
logger.debug(f"初值: {U_init}")
logger.warning("接近最大迭代次数")
logger.error("求解失败")
```

作者: Claude
日期: 2025-10-22
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys


# 彩色输出支持（可选）
try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


# 全局配置
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 彩色日志格式（如果可用）
if HAS_COLORLOG:
    COLOR_FORMAT = (
        '%(log_color)s%(levelname)-8s%(reset)s '
        '%(cyan)s%(name)s%(reset)s - '
        '%(message)s'
    )
    LOG_COLORS = {
        'DEBUG': 'white',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    console: bool = True,
    file_logging: bool = True,
    file_level: int = logging.DEBUG,
    console_level: Optional[int] = None,
    use_color: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    配置并返回一个日志记录器

    Args:
        name: 日志器名称（建议格式: 'HydroClaude.Module'）
        level: 总体日志级别
        log_dir: 日志文件目录（默认: logs/）
        console: 是否输出到控制台
        file_logging: 是否输出到文件
        file_level: 文件日志级别（通常更详细）
        console_level: 控制台日志级别（None则使用level）
        use_color: 控制台是否使用彩色输出
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的日志文件数量

    Returns:
        logging.Logger: 配置好的日志器
    """
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除已有的处理器（避免重复）
    logger.handlers.clear()

    # 控制台日志级别
    if console_level is None:
        console_level = level

    # ===== 控制台处理器 =====
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)

        if use_color and HAS_COLORLOG:
            # 彩色格式化器
            console_formatter = colorlog.ColoredFormatter(
                COLOR_FORMAT,
                datefmt=DEFAULT_DATE_FORMAT,
                log_colors=LOG_COLORS
            )
        else:
            # 普通格式化器
            console_formatter = logging.Formatter(
                DEFAULT_FORMAT,
                datefmt=DEFAULT_DATE_FORMAT
            )

        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # ===== 文件处理器 =====
    if file_logging:
        # 创建日志目录
        if log_dir is None:
            log_dir = DEFAULT_LOG_DIR
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件名（模块化）
        # HydroClaude.Newton → newton.log
        # HydroClaude.Reservoir → reservoir.log
        module_name = name.split('.')[-1].lower()
        log_file = log_dir / f"{module_name}.log"

        # 使用RotatingFileHandler实现日志轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)

        # 文件格式化器（更详细）
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt=DEFAULT_DATE_FORMAT
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    获取日志器的便捷函数

    Args:
        name: 日志器名称
        level: 日志级别

    Returns:
        logging.Logger: 日志器
    """
    return setup_logger(name, level=level)


def set_global_level(level: int):
    """
    设置全局日志级别

    Args:
        level: 日志级别（logging.DEBUG/INFO/WARNING/ERROR/CRITICAL）
    """
    logging.getLogger('HydroClaude').setLevel(level)


def disable_all_logging():
    """禁用所有日志输出（用于性能测试等）"""
    logging.disable(logging.CRITICAL)


def enable_all_logging():
    """重新启用日志输出"""
    logging.disable(logging.NOTSET)


# 创建默认的根日志器
root_logger = setup_logger('HydroClaude', level=DEFAULT_LOG_LEVEL)


def demo():
    """日志系统演示"""
    print("="*80)
    print("HydroClaude 日志系统演示")
    print("="*80)
    print()

    # 创建不同模块的日志器
    logger_newton = get_logger('HydroClaude.Newton')
    logger_reservoir = get_logger('HydroClaude.Reservoir', level=logging.DEBUG)
    logger_controller = get_logger('HydroClaude.Controller')

    # 演示不同级别的日志
    print("1. Newton求解器日志:")
    logger_newton.debug("调试信息：计算Jacobian矩阵")
    logger_newton.info("开始Newton迭代求解")
    logger_newton.warning("接近最大迭代次数（18/20）")
    logger_newton.error("求解失败: 残差未收敛")
    print()

    print("2. 水库模拟日志:")
    logger_reservoir.debug(f"当前库容: 50000000 m³")
    logger_reservoir.info("水位上涨: 260.5m → 261.2m")
    logger_reservoir.warning("接近防洪限制水位")
    logger_reservoir.error("水量平衡检查失败")
    print()

    print("3. 控制器日志:")
    logger_controller.info("PID控制器已初始化")
    logger_controller.debug(f"PID参数: Kp=0.5, Ki=0.1, Kd=0.05")
    logger_controller.info("闸门开度调整: 3.0m → 3.5m")
    print()

    print("="*80)
    print(f"日志文件已保存到: {DEFAULT_LOG_DIR}/")
    print("  - newton.log")
    print("  - reservoir.log")
    print("  - controller.log")
    print("="*80)


if __name__ == "__main__":
    demo()
