#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch modify scripts to use unified output structure

This script adds output_helper imports and updates output paths
for scripts 03, 05, and 06.
"""

import os
import re


def modify_script_03():
    """Modify script 03_idz_identification.py"""
    script_path = 'code/03_idz_identification.py'

    with open(script_path, 'r') as f:
        content = f.read()

    # Add imports if not present
    if 'from output_helper import' not in content:
        import_section = """import pandas as pd

# Import output helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from output_helper import get_output_path, save_table, save_figure
"""
        content = content.replace(
            "import os\n",
            f"import os\n{import_section}"
        )

    # Replace output paths
    content = re.sub(
        r"os\.makedirs\(['\"]\.\.\/reports\/figures['\"],\s*exist_ok=True\)",
        "",
        content
    )

    content = content.replace(
        "fig_path = f'../reports/figures/example_01_idz_{scenario}.png'",
        "fig_path = get_output_path('figures', f'03_idz_{scenario}.png')"
    )

    content = content.replace(
        "fig_path = '../reports/figures/example_01_idz_parameters_comparison.png'",
        "fig_path = get_output_path('figures', '03_idz_parameters_comparison.png')"
    )

    # Add save confirmations
    content = content.replace(
        'print(f"  保存图表: {fig_path}")',
        'print(f"   Saved figure: {os.path.basename(fig_path)}")'
    )

    content = content.replace(
        'print(f"  保存参数对比图: {fig_path}")',
        'print(f"   Saved figure: {os.path.basename(fig_path)}")'
    )

    with open(script_path, 'w') as f:
        f.write(content)

    print(f" Modified {script_path}")


def modify_script_05():
    """Modify script 05_step_response.py"""
    script_path = 'code/05_step_response.py'

    with open(script_path, 'r') as f:
        content = f.read()

    # Add imports if not present
    if 'from output_helper import' not in content:
        import_section = """import pandas as pd

# Import output helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from output_helper import get_output_path, save_table, save_figure
"""
        content = content.replace(
            "import os\n",
            f"import os\n{import_section}"
        )

    # Replace output paths
    content = re.sub(
        r"os\.makedirs\(['\"]\.\.\/reports\/figures['\"],\s*exist_ok=True\)",
        "",
        content
    )

    content = content.replace(
        "fig_path = '../reports/figures/example_01_step_response",
        "fig_path = get_output_path('figures', '05_step_response"
    )

    # Add save confirmations
    content = content.replace(
        'print(f"  Saved: {fig_path}")',
        'print(f"   Saved figure: {os.path.basename(fig_path)}")'
    )

    with open(script_path, 'w') as f:
        f.write(content)

    print(f" Modified {script_path}")


def modify_script_06():
    """Modify script 06_animation.py"""
    script_path = 'code/06_animation.py'

    with open(script_path, 'r') as f:
        content = f.read()

    # Add imports if not present
    if 'from output_helper import' not in content:
        import_section = """
# Import output helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from output_helper import get_output_path, save_animation
"""
        # Find the right place to insert (after other imports)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('def compute_steady_uniform_flow'):
                lines.insert(i, import_section)
                break
        content = '\n'.join(lines)

    # Replace output directory creation
    content = re.sub(
        r"output_dir = os\.path\.join\(os\.path\.dirname\(__file__\),\s*['\"]\.\.['\"](,\s*['\"]reports['\"])?,\s*['\"]figures['\"]\)",
        "",
        content
    )

    content = re.sub(
        r"os\.makedirs\(output_dir,\s*exist_ok=True\)",
        "",
        content
    )

    # Replace gif_path
    content = content.replace(
        "gif_path = os.path.join(output_dir, 'canal_flow_comparison_improved.gif')",
        "gif_path = get_output_path('animations', '06_canal_flow_animation.gif')"
    )

    # Replace fig_path
    content = content.replace(
        "fig_path = os.path.join(output_dir, 'canal_flow_final_state_improved.png')",
        "fig_path = get_output_path('figures', '06_canal_flow_final_state.png')"
    )

    with open(script_path, 'w') as f:
        f.write(content)

    print(f" Modified {script_path}")


if __name__ == '__main__':
    print("=" * 80)
    print("Batch Modifying Scripts...")
    print("=" * 80)

    modify_script_03()
    modify_script_05()
    modify_script_06()

    print("=" * 80)
    print(" All scripts modified successfully!")
    print("=" * 80)
