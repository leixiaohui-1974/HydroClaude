#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Matplotlib中文字体配置

解决matplotlib显示中文时的警告和方框问题
"""

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import warnings


def setup_chinese_font():
    """
    配置matplotlib以正确显示中文

    尝试多个中文字体，找到可用的那个
    """
    # 尝试的字体列表（按优先级）
    font_candidates = [
        'SimHei',          # Windows 黑体
        'Microsoft YaHei', # Windows 微软雅黑
        'WenQuanYi Micro Hei',  # Linux 文泉驿微米黑
        'Noto Sans CJK SC',     # Linux Noto
        'AR PL UMing CN',       # Linux 文鼎
        'Droid Sans Fallback',  # Android
        'PingFang SC',          # macOS 苹方
        'Heiti SC',             # macOS 黑体
        'STHeiti',              # macOS 华文黑体
    ]

    # 尝试找到可用的中文字体
    for font_name in font_candidates:
        try:
            # 测试字体是否可用
            test_font = FontProperties(fname=None, family=font_name)

            # 如果没有抛出异常，说明字体可用
            plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams['font.sans-serif']
            plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

            # 抑制中文字符缺失警告
            warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

            return font_name
        except Exception:
            continue

    # 如果没有找到合适的中文字体，使用fallback方案
    # 设置为不显示警告
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    plt.rcParams['axes.unicode_minus'] = False

    return None


def get_chinese_font():
    """
    获取中文字体对象

    Returns:
        FontProperties or None
    """
    font_candidates = [
        'SimHei',
        'Microsoft YaHei',
        'WenQuanYi Micro Hei',
        'Noto Sans CJK SC',
        'PingFang SC',
        'Heiti SC',
    ]

    for font_name in font_candidates:
        try:
            font = FontProperties(fname=None, family=font_name)
            return font
        except Exception:
            continue

    return None


# 自动配置
_configured_font = setup_chinese_font()


if __name__ == "__main__":
    """测试中文字体配置"""
    import numpy as np

    print("测试matplotlib中文字体配置")
    print("="*60)

    if _configured_font:
        print(f" 成功配置中文字体: {_configured_font}")
    else:
        print(" 未找到中文字体，将抑制警告")

    # 创建测试图
    fig, ax = plt.subplots(figsize=(8, 6))

    x = np.linspace(0, 10, 100)
    y = np.sin(x)

    ax.plot(x, y, 'b-', label='正弦曲线')
    ax.set_xlabel('时间 (秒)')
    ax.set_ylabel('幅值 (米)')
    ax.set_title('中文字体测试')
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    plt.savefig('font_test.png', dpi=150)
    print(" 测试图已保存到: font_test.png")
    print()
    print("如果图中中文显示正常，说明配置成功")
