#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
报告生成器

自动生成专业的仿真报告，支持多种格式：
- Markdown: 文本报告，易于编辑
- HTML: 网页报告，带交互式图表
- PDF: 打印报告（需要额外依赖）

作者: Claude
日期: 2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import json


class ReportGenerator:
    """
    仿真报告生成器

    使用示例:
    ```python
    reporter = ReportGenerator(
        project_name="灌溉渠道设计",
        output_dir="reports"
    )

    # 添加系统配置
    reporter.add_system_info({
        'length': 10000.0,
        'width': 10.0,
        'slope': 0.001
    })

    # 添加结果
    reporter.add_results({
        'max_depth': 3.5,
        'min_depth': 1.2,
        'avg_flow': 15.3
    })

    # 添加图表
    reporter.add_figure('profile.png', '水面线剖面图')

    # 生成报告
    reporter.generate_markdown()
    reporter.generate_html()
    ```
    """

    def __init__(
        self,
        project_name: str = "HydroClaude仿真",
        author: str = "HydroClaude",
        output_dir: str = "reports"
    ):
        """
        初始化报告生成器

        Args:
            project_name: 项目名称
            author: 作者
            output_dir: 输出目录
        """
        self.project_name = project_name
        self.author = author
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 报告内容
        self.sections = []
        self.system_info = {}
        self.results = {}
        self.figures = []
        self.tables = []
        self.timestamp = datetime.now()

    def add_section(self, title: str, content: str, level: int = 2):
        """
        添加章节

        Args:
            title: 章节标题
            content: 章节内容
            level: 标题级别 (1-6)
        """
        self.sections.append({
            'type': 'section',
            'title': title,
            'content': content,
            'level': level
        })

    def add_system_info(self, info: Dict[str, Any]):
        """
        添加系统信息

        Args:
            info: 系统参数字典
        """
        self.system_info.update(info)

    def add_results(self, results: Dict[str, Any]):
        """
        添加仿真结果

        Args:
            results: 结果字典
        """
        self.results.update(results)

    def add_figure(
        self,
        figure_path: str,
        caption: str = "",
        description: str = ""
    ):
        """
        添加图表

        Args:
            figure_path: 图表文件路径
            caption: 图表标题
            description: 图表说明
        """
        self.figures.append({
            'path': figure_path,
            'caption': caption,
            'description': description
        })

    def add_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[Any]],
        description: str = ""
    ):
        """
        添加表格

        Args:
            title: 表格标题
            headers: 列标题
            rows: 数据行
            description: 表格说明
        """
        self.tables.append({
            'title': title,
            'headers': headers,
            'rows': rows,
            'description': description
        })

    def generate_markdown(self, filename: str = "report.md") -> str:
        """
        生成Markdown报告

        Args:
            filename: 输出文件名

        Returns:
            报告文件路径
        """
        output_file = self.output_dir / filename

        with open(output_file, 'w', encoding='utf-8') as f:
            # 标题和元信息
            f.write(f"# {self.project_name}\n\n")
            f.write(f"**生成时间**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**作者**: {self.author}\n\n")
            f.write("---\n\n")

            # 目录
            f.write("## 目录\n\n")
            toc_items = []
            if self.system_info:
                toc_items.append("1. [系统配置](#系统配置)")
            if self.results:
                toc_items.append("2. [仿真结果](#仿真结果)")
            if self.figures:
                toc_items.append("3. [图表](#图表)")
            if self.tables:
                toc_items.append("4. [数据表](#数据表)")
            if self.sections:
                for i, section in enumerate(self.sections, start=len(toc_items)+1):
                    anchor = section['title'].replace(' ', '-').lower()
                    toc_items.append(f"{i}. [{section['title']}](#{anchor})")

            for item in toc_items:
                f.write(f"{item}\n")
            f.write("\n---\n\n")

            # 系统配置
            if self.system_info:
                f.write("## 系统配置\n\n")
                f.write("| 参数 | 值 |\n")
                f.write("|------|----|\n")
                for key, value in self.system_info.items():
                    f.write(f"| {key} | {value} |\n")
                f.write("\n")

            # 仿真结果
            if self.results:
                f.write("## 仿真结果\n\n")
                f.write("| 指标 | 值 |\n")
                f.write("|------|----|\n")
                for key, value in self.results.items():
                    if isinstance(value, float):
                        f.write(f"| {key} | {value:.4f} |\n")
                    else:
                        f.write(f"| {key} | {value} |\n")
                f.write("\n")

            # 图表
            if self.figures:
                f.write("## 图表\n\n")
                for i, fig in enumerate(self.figures, 1):
                    f.write(f"### 图 {i}: {fig['caption']}\n\n")
                    if fig['description']:
                        f.write(f"{fig['description']}\n\n")
                    f.write(f"![{fig['caption']}]({fig['path']})\n\n")

            # 数据表
            if self.tables:
                f.write("## 数据表\n\n")
                for i, table in enumerate(self.tables, 1):
                    f.write(f"### 表 {i}: {table['title']}\n\n")
                    if table['description']:
                        f.write(f"{table['description']}\n\n")

                    # 表格header
                    f.write("| " + " | ".join(table['headers']) + " |\n")
                    f.write("|" + "|".join(["---" for _ in table['headers']]) + "|\n")

                    # 表格数据
                    for row in table['rows']:
                        f.write("| " + " | ".join([str(cell) for cell in row]) + " |\n")
                    f.write("\n")

            # 自定义章节
            for section in self.sections:
                level = section['level']
                f.write(f"{'#' * level} {section['title']}\n\n")
                f.write(f"{section['content']}\n\n")

            # 页脚
            f.write("---\n\n")
            f.write("*本报告由HydroClaude自动生成*\n")

        return str(output_file)

    def generate_html(self, filename: str = "report.html") -> str:
        """
        生成HTML报告

        Args:
            filename: 输出文件名

        Returns:
            报告文件路径
        """
        output_file = self.output_dir / filename

        # HTML模板
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.project_name}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .meta {{
            margin-top: 10px;
            opacity: 0.9;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #667eea;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .figure {{
            text-align: center;
            margin: 20px 0;
        }}
        .figure img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .figure-caption {{
            margin-top: 10px;
            font-style: italic;
            color: #666;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.project_name}</h1>
        <div class="meta">
            <p>生成时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>作者: {self.author}</p>
        </div>
    </div>
"""

        # 系统配置
        if self.system_info:
            html_content += """
    <div class="section">
        <h2>系统配置</h2>
        <table>
            <thead>
                <tr><th>参数</th><th>值</th></tr>
            </thead>
            <tbody>
"""
            for key, value in self.system_info.items():
                html_content += f"                <tr><td>{key}</td><td>{value}</td></tr>\n"
            html_content += """
            </tbody>
        </table>
    </div>
"""

        # 仿真结果
        if self.results:
            html_content += """
    <div class="section">
        <h2>仿真结果</h2>
        <table>
            <thead>
                <tr><th>指标</th><th>值</th></tr>
            </thead>
            <tbody>
"""
            for key, value in self.results.items():
                if isinstance(value, float):
                    value_str = f"{value:.4f}"
                else:
                    value_str = str(value)
                html_content += f"                <tr><td>{key}</td><td>{value_str}</td></tr>\n"
            html_content += """
            </tbody>
        </table>
    </div>
"""

        # 图表
        if self.figures:
            html_content += """
    <div class="section">
        <h2>图表</h2>
"""
            for i, fig in enumerate(self.figures, 1):
                html_content += f"""
        <div class="figure">
            <h3>图 {i}: {fig['caption']}</h3>
            {f'<p>{fig["description"]}</p>' if fig['description'] else ''}
            <img src="{fig['path']}" alt="{fig['caption']}">
        </div>
"""
            html_content += "    </div>\n"

        # 数据表
        if self.tables:
            for i, table in enumerate(self.tables, 1):
                html_content += f"""
    <div class="section">
        <h2>表 {i}: {table['title']}</h2>
        {f'<p>{table["description"]}</p>' if table['description'] else ''}
        <table>
            <thead>
                <tr>
"""
                for header in table['headers']:
                    html_content += f"                    <th>{header}</th>\n"
                html_content += """                </tr>
            </thead>
            <tbody>
"""
                for row in table['rows']:
                    html_content += "                <tr>\n"
                    for cell in row:
                        html_content += f"                    <td>{cell}</td>\n"
                    html_content += "                </tr>\n"
                html_content += """            </tbody>
        </table>
    </div>
"""

        # 自定义章节
        for section in self.sections:
            html_content += f"""
    <div class="section">
        <h2>{section['title']}</h2>
        <p>{section['content']}</p>
    </div>
"""

        # 页脚
        html_content += """
    <div class="footer">
        <p>本报告由 HydroClaude 自动生成</p>
    </div>
</body>
</html>
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_file)

    def generate_summary_json(self, filename: str = "summary.json") -> str:
        """
        生成JSON格式的摘要

        Args:
            filename: 输出文件名

        Returns:
            文件路径
        """
        output_file = self.output_dir / filename

        summary = {
            'project_name': self.project_name,
            'author': self.author,
            'timestamp': self.timestamp.isoformat(),
            'system_info': self.system_info,
            'results': self.results,
            'figures': [{'caption': fig['caption'], 'path': fig['path']} for fig in self.figures],
            'tables': [{'title': t['title'], 'rows': len(t['rows'])} for t in self.tables]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return str(output_file)


# 便捷函数
def quick_report(
    project_name: str,
    system_info: Dict,
    results: Dict,
    figures: List[str] = None,
    output_dir: str = "reports"
) -> Dict[str, str]:
    """
    快速生成报告

    Args:
        project_name: 项目名称
        system_info: 系统信息
        results: 仿真结果
        figures: 图表文件列表
        output_dir: 输出目录

    Returns:
        生成的文件路径字典
    """
    reporter = ReportGenerator(project_name=project_name, output_dir=output_dir)
    reporter.add_system_info(system_info)
    reporter.add_results(results)

    if figures:
        for fig in figures:
            caption = Path(fig).stem.replace('_', ' ').title()
            reporter.add_figure(fig, caption=caption)

    files = {
        'markdown': reporter.generate_markdown(),
        'html': reporter.generate_html(),
        'json': reporter.generate_summary_json()
    }

    return files


if __name__ == "__main__":
    # 测试示例
    print("报告生成器测试")
    print()

    # 创建报告生成器
    reporter = ReportGenerator(
        project_name="测试仿真项目",
        author="Claude",
        output_dir="test_reports"
    )

    # 添加系统信息
    reporter.add_system_info({
        '渠道长度': '10 km',
        '渠道宽度': '10 m',
        '底坡': '0.001',
        '曼宁系数': '0.025'
    })

    # 添加结果
    reporter.add_results({
        '最大水深': 3.5,
        '最小水深': 1.2,
        '平均流量': 15.3,
        '收敛迭代': 5
    })

    # 添加表格
    reporter.add_table(
        title="关键点水位",
        headers=['位置 (km)', '水深 (m)', '流速 (m/s)'],
        rows=[
            [0, 3.5, 1.2],
            [2.5, 3.2, 1.3],
            [5.0, 2.9, 1.4],
            [7.5, 2.6, 1.5],
            [10.0, 2.3, 1.6]
        ]
    )

    # 添加章节
    reporter.add_section(
        title="结论",
        content="仿真结果表明，设计方案满足所有技术要求。流量守恒精度达到0.000001%，计算效率为40×实时。"
    )

    # 生成报告
    print("生成Markdown报告...")
    md_file = reporter.generate_markdown()
    print(f"   {md_file}")

    print("\n生成HTML报告...")
    html_file = reporter.generate_html()
    print(f"   {html_file}")

    print("\n生成JSON摘要...")
    json_file = reporter.generate_summary_json()
    print(f"   {json_file}")

    print("\n 测试完成！")
