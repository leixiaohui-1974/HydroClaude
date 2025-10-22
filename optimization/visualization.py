"""
可视化工具：支持中文字体和增强绘图
"""
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
import platform


def configure_chinese_font():
    """
    配置matplotlib中文字体

    尝试按优先级顺序使用可用的中文字体：
    1. SimHei (Windows)
    2. STHeiti (macOS)
    3. WenQuanYi Micro Hei (Linux)
    4. 降级到DejaVu Sans（无中文支持，但不会报错）
    """
    system = platform.system()

    # 定义候选字体列表
    font_candidates = []

    if system == "Windows":
        font_candidates = ["SimHei", "Microsoft YaHei", "SimSun"]
    elif system == "Darwin":  # macOS
        font_candidates = ["STHeiti", "STSong", "Arial Unicode MS"]
    else:  # Linux
        font_candidates = [
            "WenQuanYi Micro Hei",
            "WenQuanYi Zen Hei",
            "Droid Sans Fallback",
            "Noto Sans CJK SC",
        ]

    # 添加通用备用字体
    font_candidates.extend(["DejaVu Sans", "sans-serif"])

    # 获取可用字体列表
    from matplotlib.font_manager import FontManager

    fm = FontManager()
    available_fonts = {f.name for f in fm.ttflist}

    # 选择第一个可用字体
    selected_font = None
    for font in font_candidates:
        if font in available_fonts:
            selected_font = font
            break

    if selected_font is None:
        selected_font = font_candidates[-1]  # 使用最后的备用字体

    # 设置matplotlib参数
    plt.rcParams["font.sans-serif"] = [selected_font] + font_candidates
    plt.rcParams["axes.unicode_minus"] = False  # 正常显示负号

    return selected_font


def setup_plotting_style(style="default", figsize=(12, 8), dpi=100):
    """
    设置绘图样式

    Args:
        style: 样式名称 ('default', 'seaborn', 'ggplot', 'bmh')
        figsize: 默认图形大小
        dpi: 分辨率
    """
    # 配置中文字体
    font = configure_chinese_font()

    # 设置样式
    if style != "default":
        try:
            plt.style.use(style)
        except:
            pass  # 如果样式不可用，使用默认

    # 设置默认参数
    plt.rcParams["figure.figsize"] = figsize
    plt.rcParams["figure.dpi"] = dpi
    plt.rcParams["savefig.dpi"] = dpi

    # 设置线条和网格样式
    plt.rcParams["lines.linewidth"] = 2
    plt.rcParams["grid.alpha"] = 0.3

    return font


def create_time_series_plot(
    data_dict,
    title="时间序列图",
    xlabel="时间",
    ylabel="数值",
    figsize=(12, 6),
    save_path=None,
):
    """
    创建时间序列图

    Args:
        data_dict: 数据字典 {label: (x_values, y_values)}
        title: 图表标题
        xlabel: X轴标签
        ylabel: Y轴标签
        figsize: 图形大小
        save_path: 保存路径（None则不保存）

    Returns:
        fig, ax: matplotlib图形和坐标轴对象
    """
    setup_plotting_style()

    fig, ax = plt.subplots(figsize=figsize)

    for label, (x_values, y_values) in data_dict.items():
        ax.plot(x_values, y_values, label=label, marker="o", markersize=4)

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig, ax


def create_multi_panel_plot(
    panels_config,
    title=None,
    rows=None,
    cols=None,
    figsize=(14, 10),
    save_path=None,
):
    """
    创建多面板图

    Args:
        panels_config: 面板配置列表，每个元素为字典：
            {
                'data': {label: (x, y), ...},
                'title': '子图标题',
                'xlabel': 'X轴',
                'ylabel': 'Y轴',
                'plot_type': 'line' or 'bar'
            }
        title: 总标题
        rows: 行数（自动计算如果为None）
        cols: 列数（自动计算如果为None）
        figsize: 图形大小
        save_path: 保存路径

    Returns:
        fig, axes: matplotlib图形和坐标轴数组
    """
    setup_plotting_style()

    n_panels = len(panels_config)

    # 自动计算布局
    if rows is None and cols is None:
        if n_panels <= 2:
            rows, cols = 1, n_panels
        elif n_panels <= 4:
            rows, cols = 2, 2
        elif n_panels <= 6:
            rows, cols = 2, 3
        else:
            cols = 3
            rows = (n_panels + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=figsize)

    # 确保axes是数组
    if n_panels == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for idx, (ax, config) in enumerate(zip(axes, panels_config)):
        data = config.get("data", {})
        panel_title = config.get("title", f"面板 {idx+1}")
        xlabel = config.get("xlabel", "X")
        ylabel = config.get("ylabel", "Y")
        plot_type = config.get("plot_type", "line")

        for label, (x_values, y_values) in data.items():
            if plot_type == "line":
                ax.plot(x_values, y_values, label=label, marker="o", markersize=3)
            elif plot_type == "bar":
                ax.bar(x_values, y_values, label=label, alpha=0.7)

        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(panel_title, fontsize=11, fontweight="bold")
        if data:
            ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)

    # 隐藏多余的子图
    for idx in range(n_panels, len(axes)):
        fig.delaxes(axes[idx])

    if title:
        fig.suptitle(title, fontsize=14, fontweight="bold")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig, axes


def create_comparison_plot(
    actual_data,
    target_data,
    title="实际值与目标值对比",
    xlabel="时间",
    ylabel="数值",
    figsize=(12, 6),
    save_path=None,
):
    """
    创建对比图（实际值vs目标值）

    Args:
        actual_data: (x_values, y_values) 元组
        target_data: (x_values, y_values) 元组
        title: 图表标题
        xlabel: X轴标签
        ylabel: Y轴标签
        figsize: 图形大小
        save_path: 保存路径

    Returns:
        fig, ax: matplotlib图形和坐标轴对象
    """
    setup_plotting_style()

    fig, ax = plt.subplots(figsize=figsize)

    x_actual, y_actual = actual_data
    x_target, y_target = target_data

    ax.plot(x_target, y_target, label="目标值", linestyle="--", linewidth=2, alpha=0.7)
    ax.plot(x_actual, y_actual, label="实际值", linewidth=2)

    # 填充差异区域
    if len(x_actual) == len(x_target):
        ax.fill_between(
            x_actual,
            y_actual,
            y_target,
            alpha=0.2,
            label="偏差",
        )

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig, ax


if __name__ == "__main__":
    # 测试中文字体配置
    print("测试中文字体支持...")
    font = setup_plotting_style()
    print(f"选择的字体: {font}")

    # 创建测试图
    import numpy as np

    x = np.arange(0, 24)
    y1 = 50 + 30 * np.sin(x / 4) + np.random.randn(24) * 5
    y2 = 40 + 20 * np.cos(x / 3) + np.random.randn(24) * 3

    fig, ax = create_time_series_plot(
        {
            "流量": (x, y1),
            "需求": (x, y2),
        },
        title="水网流量时间序列",
        xlabel="时间（小时）",
        ylabel="流量（m³/h）",
        save_path="test_chinese_plot.png",
    )

    print("测试图已保存到: test_chinese_plot.png")
