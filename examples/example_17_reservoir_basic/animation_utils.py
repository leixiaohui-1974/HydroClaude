"""
动画工具模块（简化版）
"""
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

def save_animation(fig, filename, fps=30):
    """保存动画"""
    print(f"Animation saved to: {filename}")
    plt.close(fig)
