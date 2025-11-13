"""
可视化工具模块

提供统一的可视化和报告生成功能：
- 静态图表生成
- 动态GIF动画生成
- 数据表格生成
- Markdown报告生成
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import networkx as nx
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import os

try:
    from topology.network_graph import NetworkTopology, NodeType
except ImportError:
    NetworkTopology = None
    NodeType = None

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class SimulationVisualizer:
    """仿真结果可视化器"""

    def __init__(self, output_dir: str = "reports/figures"):
        """
        初始化可视化器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def plot_time_series(
        self,
        time: np.ndarray,
        data: Dict[str, np.ndarray],
        title: str,
        ylabel: str,
        filename: str,
        figsize: Tuple[int, int] = (12, 6)
    ):
        """绘制时间序列图"""
        fig, ax = plt.subplots(figsize=figsize)

        for label, values in data.items():
            ax.plot(time, values, label=label, linewidth=2)

        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return filepath

    def plot_spatial_profile(
        self,
        x: np.ndarray,
        data: Dict[str, np.ndarray],
        title: str,
        ylabel: str,
        filename: str,
        figsize: Tuple[int, int] = (12, 6)
    ):
        """绘制空间剖面图"""
        fig, ax = plt.subplots(figsize=figsize)

        for label, values in data.items():
            ax.plot(x, values, label=label, linewidth=2, marker='o', markersize=4)

        ax.set_xlabel('Distance (m)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return filepath

    def create_animation_gif(
        self,
        x: np.ndarray,
        time_data: List[np.ndarray],
        time_points: np.ndarray,
        title: str,
        ylabel: str,
        filename: str,
        figsize: Tuple[int, int] = (12, 6),
        fps: int = 10,
        ylim: Optional[Tuple[float, float]] = None
    ):
        """创建动态GIF动画"""
        fig, ax = plt.subplots(figsize=figsize)

        # 确定y轴范围
        if ylim is None:
            all_data = np.concatenate(time_data)
            ylim = (all_data.min() * 0.95, all_data.max() * 1.05)

        line, = ax.plot([], [], 'b-', linewidth=2, marker='o', markersize=4)
        time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes,
                           fontsize=12, verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.set_xlim(x.min(), x.max())
        ax.set_ylim(ylim)
        ax.set_xlabel('Distance (m)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        def init():
            line.set_data([], [])
            time_text.set_text('')
            return line, time_text

        def animate(i):
            line.set_data(x, time_data[i])
            time_text.set_text(f'Time = {time_points[i]:.1f} s')
            return line, time_text

        anim = animation.FuncAnimation(
            fig, animate, init_func=init,
            frames=len(time_data), interval=1000/fps, blit=True
        )

        filepath = os.path.join(self.output_dir, filename)
        anim.save(filepath, writer='pillow', fps=fps, dpi=100)
        plt.close()

        return filepath

    def create_multi_panel_animation(
        self,
        x: np.ndarray,
        data_dict: Dict[str, List[np.ndarray]],
        time_points: np.ndarray,
        filename: str,
        titles: Optional[Dict[str, str]] = None,
        ylabels: Optional[Dict[str, str]] = None,
        figsize: Tuple[int, int] = (14, 10),
        fps: int = 10
    ):
        """创建多子图动画"""
        n_plots = len(data_dict)
        fig, axes = plt.subplots(n_plots, 1, figsize=figsize)
        if n_plots == 1:
            axes = [axes]

        lines = {}
        time_texts = []

        for idx, (key, time_data) in enumerate(data_dict.items()):
            ax = axes[idx]

            # 数据范围
            all_data = np.concatenate(time_data)
            ylim = (all_data.min() * 0.95, all_data.max() * 1.05)

            line, = ax.plot([], [], 'b-', linewidth=2, marker='o', markersize=4)
            lines[key] = line

            if idx == 0:
                time_text = ax.text(0.02, 0.95, '', transform=ax.transAxes,
                                   fontsize=12, verticalalignment='top',
                                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                time_texts.append(time_text)

            ax.set_xlim(x.min(), x.max())
            ax.set_ylim(ylim)
            ax.set_xlabel('Distance (m)', fontsize=12)

            ylabel = ylabels.get(key, key) if ylabels else key
            ax.set_ylabel(ylabel, fontsize=12)

            title = titles.get(key, key) if titles else key
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)

        def init():
            for line in lines.values():
                line.set_data([], [])
            for text in time_texts:
                text.set_text('')
            return list(lines.values()) + time_texts

        def animate(i):
            for key, line in lines.items():
                line.set_data(x, data_dict[key][i])
            for text in time_texts:
                text.set_text(f'Time = {time_points[i]:.1f} s')
            return list(lines.values()) + time_texts

        anim = animation.FuncAnimation(
            fig, animate, init_func=init,
            frames=len(time_points), interval=1000/fps, blit=True
        )

        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        anim.save(filepath, writer='pillow', fps=fps, dpi=100)
        plt.close()

        return filepath


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = "reports"):
        """初始化报告生成器"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_markdown_report(
        self,
        title: str,
        sections: List[Dict[str, Any]],
        filename: str
    ):
        """生成Markdown报告"""
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            # 标题
            f.write(f"# {title}\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            # 各章节
            for section in sections:
                heading = section.get('heading', '')
                content = section.get('content', '')
                images = section.get('images', [])

                if heading:
                    f.write(f"## {heading}\n\n")

                if content:
                    f.write(f"{content}\n\n")

                # 嵌入图片
                for img_path in images:
                    img_name = os.path.basename(img_path)
                    # 使用相对路径
                    rel_path = os.path.relpath(img_path, self.output_dir)
                    f.write(f"![{img_name}]({rel_path})\n\n")

            f.write("---\n\n")
            f.write("**报告结束**\n")

        return filepath

    def create_summary_table(
        self,
        data: Dict[str, Any],
        headers: Optional[List[str]] = None
    ) -> str:
        """创建Markdown表格"""
        if isinstance(data, dict):
            if headers is None:
                headers = ['Parameter', 'Value']

            table = f"| {' | '.join(headers)} |\n"
            table += f"|{'|'.join(['---' for _ in headers])}|\n"

            for k, v in data.items():
                table += f"| {k} | {v} |\n"

        elif isinstance(data, list):
            if headers is None:
                headers = [f"Col{i+1}" for i in range(len(data[0]))]

            table = f"| {' | '.join(headers)} |\n"
            table += f"|{'|'.join(['---' for _ in headers])}|\n"

            for row in data:
                table += f"| {' | '.join(str(x) for x in row)} |\n"

        return table


def visualize_network(topology: 'NetworkTopology', results: Dict = None):
    """可视化网络拓扑"""
    if NetworkTopology is None or NodeType is None:
        print("Warning: NetworkTopology not available")
        return

    G = nx.DiGraph()

    for node_id, node in topology.nodes.items():
        G.add_node(node_id, type=node.node_type.value)

    for edge in topology.edges.values():
        G.add_edge(edge.start_node, edge.end_node,
                  flow=edge.flow, id=edge.id)

    pos = nx.spring_layout(G, k=2, iterations=50)

    plt.figure(figsize=(14, 10))

    node_colors = []
    for node_id in G.nodes():
        node = topology.nodes[node_id]
        if node.node_type == NodeType.SOURCE:
            node_colors.append('lightblue')
        elif node.node_type == NodeType.SINK:
            node_colors.append('lightcoral')
        elif node.node_type == NodeType.BRANCH:
            node_colors.append('lightgreen')
        else:
            node_colors.append('lightgray')

    nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                          node_size=800, alpha=0.9)

    nx.draw_networkx_edges(G, pos, edge_color='gray',
                          arrows=True, arrowsize=20, width=2)

    nx.draw_networkx_labels(G, pos, font_size=8)

    if results:
        edge_labels = {}
        for edge_id, flow in results['edges'].items():
            edge = topology.edges[edge_id]
            edge_labels[(edge.start_node, edge.end_node)] = f"{flow:.1f}"
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=7)

    plt.title("水网拓扑结构", fontsize=14, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('network_topology.png', dpi=150, bbox_inches='tight')
    print("\n 拓扑图已保存: network_topology.png")
