#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成HTML示例索引页面
创建一个美观的Web界面浏览所有示例
"""

import sys
from pathlib import Path
import json


class HTMLIndexGenerator:
    """HTML索引生成器"""

    def __init__(self, examples_root):
        self.examples_root = Path(examples_root)

        # 示例分类
        self.categories = {
            '明渠与开放水流': [
                'example_01_canal_flow',
                'example_02_spillway_cascade',
                'example_16_weirs_application'
            ],
            '管道与压力系统': [
                'example_02_pump_system',
                'example_09_pipe_rk4',
                'example_10_series_network',
                'example_11_tree_network',
                'example_12_loop_network',
                'example_22_water_hammer'
            ],
            '水电站系统': [
                'example_03_turbine_demo',
                'example_04_hydropower_system',
                'example_05_transient_analysis',
                'example_06_complete_hydropower_system',
                'example_08_load_acceptance',
                'example_18_cascade_hydropower'
            ],
            '控制与优化': [
                'example_06_sil_basic',
                'example_07_fault_test',
                'example_07_multi_unit_agc',
                'example_13_adaptive_timescale',
                'example_14_adaptive_mpc',
                'example_15_rls_identification',
                'example_23_control_comparison',
                'example_24_multi_objective_optimization'
            ],
            '水资源系统': [
                'example_17_reservoir_basic',
                'example_19_water_transfer',
                'example_20_urban_water_supply',
                'example_21_irrigation_optimization'
            ],
            '数值方法': [
                'example_03_complex_network',
                'example_04_moc_boundary',
                'example_05_mode_comparison',
                'example_08_preissmann_vs_fvm'
            ]
        }

    def get_example_info(self, example_name):
        """获取示例信息"""
        example_dir = self.examples_root / example_name
        readme = example_dir / 'README.md'

        if not readme.exists():
            return {
                'title': example_name.replace('example_', '').replace('_', ' ').title(),
                'description': '暂无描述',
                'has_readme': False,
                'has_gif': False,
                'has_png': False,
                'gif_count': 0,
                'png_count': 0
            }

        # 读取README第一行作为标题
        with open(readme, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            title = lines[0].strip('# \n') if lines else example_name

            # 查找概述部分
            description = ''
            for i, line in enumerate(lines):
                if '## 概述' in line and i+2 < len(lines):
                    description = lines[i+2].strip()
                    break

        # 检查输出文件
        outputs_dir = example_dir / 'outputs'
        gif_count = 0
        png_count = 0

        if outputs_dir.exists():
            gifs = list(outputs_dir.rglob('*.gif'))
            pngs = list(outputs_dir.rglob('*.png'))
            gif_count = len(gifs)
            png_count = len(pngs)

        return {
            'title': title,
            'description': description or '暂无描述',
            'has_readme': True,
            'has_gif': gif_count > 0,
            'has_png': png_count > 0,
            'gif_count': gif_count,
            'png_count': png_count
        }

    def generate_html(self):
        """生成HTML索引"""
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HydroClaude 示例库</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            text-align: center;
            padding: 60px 20px;
            color: white;
        }

        h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 30px;
            flex-wrap: wrap;
        }

        .stat-item {
            background: rgba(255,255,255,0.2);
            padding: 15px 30px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        .stat-number {
            font-size: 2em;
            font-weight: bold;
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }

        .category {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        .category-title {
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }

        .examples-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }

        .example-card {
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .example-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
            border-color: #667eea;
        }

        .example-title {
            font-size: 1.3em;
            color: #333;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .example-description {
            color: #666;
            font-size: 0.95em;
            margin-bottom: 15px;
            line-height: 1.5;
        }

        .example-badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }

        .badge-readme {
            background: #4CAF50;
            color: white;
        }

        .badge-gif {
            background: #FF9800;
            color: white;
        }

        .badge-png {
            background: #2196F3;
            color: white;
        }

        .example-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            margin-top: 10px;
            display: inline-block;
        }

        .example-link:hover {
            text-decoration: underline;
        }

        footer {
            text-align: center;
            padding: 40px 20px;
            color: white;
            margin-top: 40px;
        }

        .search-box {
            margin: 30px auto;
            max-width: 600px;
        }

        .search-input {
            width: 100%;
            padding: 15px 20px;
            font-size: 1.1em;
            border: none;
            border-radius: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }

        @media (max-width: 768px) {
            h1 {
                font-size: 2em;
            }

            .examples-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>🌊 HydroClaude 示例库</h1>
        <p class="subtitle">水利仿真框架 - 31个精选示例</p>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{total_examples}</div>
                <div class="stat-label">示例总数</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_gifs}</div>
                <div class="stat-label">动画演示</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{total_pngs}</div>
                <div class="stat-label">分析图表</div>
            </div>
        </div>

        <div class="search-box">
            <input type="text" class="search-input" id="searchInput" placeholder="搜索示例...">
        </div>
    </header>

    <div class="container">
        {categories_html}
    </div>

    <footer>
        <p>HydroClaude - 水利仿真框架</p>
        <p>项目地址: <a href="https://github.com/leixiaohui-1974/HydroClaude" style="color: white;">GitHub</a></p>
    </footer>

    <script>
        // 搜索功能
        document.getElementById('searchInput').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const cards = document.querySelectorAll('.example-card');

            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });

        // 点击卡片跳转
        document.querySelectorAll('.example-card').forEach(card => {
            card.addEventListener('click', function() {
                const link = this.querySelector('.example-link');
                if (link) {
                    window.location.href = link.href;
                }
            });
        });
    </script>
</body>
</html>
"""

        # 统计信息
        total_examples = 0
        total_gifs = 0
        total_pngs = 0

        # 生成分类HTML
        categories_html = ""

        for category_name, examples in self.categories.items():
            examples_html = ""

            for example_name in examples:
                example_dir = self.examples_root / example_name
                if not example_dir.exists():
                    continue

                total_examples += 1

                info = self.get_example_info(example_name)
                total_gifs += info['gif_count']
                total_pngs += info['png_count']

                badges = ""
                if info['has_readme']:
                    badges += '<span class="badge badge-readme">📖 README</span>'
                if info['has_gif']:
                    badges += f'<span class="badge badge-gif">🎬 {info["gif_count"]} GIF</span>'
                if info['has_png']:
                    badges += f'<span class="badge badge-png">📊 {info["png_count"]} PNG</span>'

                examples_html += f"""
                <div class="example-card">
                    <div class="example-title">{info['title']}</div>
                    <div class="example-description">{info['description']}</div>
                    <div class="example-badges">{badges}</div>
                    <a href="{example_name}/README.md" class="example-link">查看详情 →</a>
                </div>
                """

            if examples_html:
                categories_html += f"""
                <div class="category">
                    <h2 class="category-title">{category_name}</h2>
                    <div class="examples-grid">
                        {examples_html}
                    </div>
                </div>
                """

        # 替换模板变量
        html = html.replace('{total_examples}', str(total_examples))
        html = html.replace('{total_gifs}', str(total_gifs))
        html = html.replace('{total_pngs}', str(total_pngs))
        html = html.replace('{categories_html}', categories_html)

        # 保存HTML文件
        output_file = self.examples_root / 'index.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML索引已生成: {output_file}")
        print(f"统计: {total_examples}个示例, {total_gifs}个GIF, {total_pngs}个PNG")

        return output_file


def main():
    """主函数"""
    examples_root = Path(__file__).parent

    generator = HTMLIndexGenerator(examples_root)
    generator.generate_html()


if __name__ == '__main__':
    main()
