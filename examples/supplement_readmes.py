#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
补充缺失的6个示例的README文档
"""

from pathlib import Path


def generate_missing_readmes():
    """为缺失的6个示例生成README"""

    examples_root = Path(__file__).parent

    missing_examples = {
        'example_03_complex_network': {
            'title': '复杂管网系统',
            'description': '演示多源多汇的复杂水力管网系统，包括拓扑分析、流量分配和压力计算。',
            'physics': '复杂管网遵循节点流量守恒和管段能量方程，通过拓扑分析确定系统连接关系',
            'key_features': [
                '多源多汇网络拓扑',
                '节点类型识别（源、汇、分岔、连接）',
                '自动拓扑分析',
                '耦合求解器',
                '流量和压力分配'
            ],
            'applications': ['城市供水', '复杂管网', '多水源系统', '配水优化'],
            'scripts': ['code/example_03_complex_network.py'],
            'key_outputs': [
                '节点水头分布',
                '管段流量分配',
                '拓扑分析结果',
                '网络可视化'
            ]
        },

        'example_04_moc_boundary': {
            'title': 'MOC边界条件处理',
            'description': '演示特征线法（MOC）中各种边界条件的处理方法，包括阀门、泵、水库等。',
            'physics': 'MOC方法通过特征线将偏微分方程转化为常微分方程，边界条件决定特征线的边界值',
            'key_features': [
                'MOC特征线方法',
                '上游边界（水库、恒定水头）',
                '下游边界（阀门、自由出流）',
                '内部边界（泵、阀门、分岔）',
                '边界条件的数值实现'
            ],
            'applications': ['水锤计算', '管道瞬变', '边界处理', '数值方法研究'],
            'scripts': ['code/example_04_moc_boundary.py'],
            'key_outputs': [
                '不同边界条件的压力响应',
                '特征线轨迹',
                '边界反射波',
                '方法对比'
            ]
        },

        'example_05_mode_comparison': {
            'title': '仿真模式对比',
            'description': '对比不同仿真模式（高保真、降阶、简化）的精度和效率，为模型选择提供依据。',
            'physics': '不同模式采用不同的简化假设和数值方法，在精度和计算效率间权衡',
            'key_features': [
                '高保真模式（完整物理模型）',
                '降阶模式（模型简化）',
                '快速模式（实时仿真）',
                '精度对比分析',
                '效率评估'
            ],
            'applications': ['模型选择', '实时仿真', '快速评估', '工程设计'],
            'scripts': ['code/example_05_mode_comparison.py'],
            'key_outputs': [
                '不同模式的结果对比',
                '计算时间统计',
                '精度误差分析',
                '适用场景建议'
            ]
        },

        'example_06_complete_hydropower_system': {
            'title': '完整水电站系统',
            'description': '最完整的水电站仿真，包含引水系统、压力管道、调压井、水轮机、发电机及控制系统的全面耦合。',
            'physics': '水电站是水力-机械-电气多物理场强耦合系统，涉及流体动力学、转动力学和电磁学',
            'key_features': [
                '完整的引水系统',
                '压力管道和调压井',
                'Francis水轮机详细模型',
                '发电机和励磁系统',
                'PID调速器和励磁调节器',
                '负荷变化响应',
                '多物理场耦合'
            ],
            'applications': ['水电站设计', '过渡过程', '控制优化', '稳定性分析'],
            'scripts': ['example_06_complete_system.py'],
            'key_outputs': [
                '水轮机-发电机耦合响应',
                '调压井水位波动',
                '转速和功率曲线',
                '系统稳定性分析'
            ]
        },

        'example_07_multi_unit_agc': {
            'title': '多机组AGC控制',
            'description': '演示多台机组协调的自动发电控制（AGC），包括一次调频、二次调频和经济调度。',
            'physics': 'AGC通过调节多台机组的出力来维持系统频率和联络线功率，实现源荷平衡',
            'key_features': [
                '3台机组协调控制',
                '一次调频（调速器下垂）',
                '二次调频（AGC）',
                '经济调度（负荷分配）',
                'ACE计算和CPS1指标',
                '频率扰动响应'
            ],
            'applications': ['电网调频', 'AGC设计', '多机组协调', '频率稳定'],
            'scripts': ['example_07_multi_unit_agc.py'],
            'key_outputs': [
                '频率响应曲线',
                '多机组出力分配',
                'ACE和CPS1指标',
                'AGC性能评估'
            ]
        },

        'example_08_preissmann_vs_fvm': {
            'title': 'Preissmann格式与有限体积法对比',
            'description': '对比Preissmann四点隐式格式和有限体积法（FVM）求解明渠流的性能差异。',
            'physics': 'Preissmann是隐式格式，无条件稳定；FVM是守恒型方法，处理间断能力强',
            'key_features': [
                'Preissmann四点格式',
                '有限体积法（FVM）',
                'HLL通量计算',
                '精度对比',
                '稳定性分析',
                '计算效率评估'
            ],
            'applications': ['数值方法研究', '算法选择', '精度评估', '明渠仿真'],
            'scripts': ['code/example_08_preissmann_vs_fvm.py', 'example_08_preissmann_vs_fvm_enhanced.py'],
            'key_outputs': [
                '两种方法的水位对比',
                '质量守恒检查',
                '计算时间对比',
                '精度和效率权衡'
            ]
        }
    }

    success_count = 0

    for example_name, info in missing_examples.items():
        example_dir = examples_root / example_name

        if not example_dir.exists():
            print(f"  ✗ {example_name}: 目录不存在")
            continue

        readme_path = example_dir / 'README.md'

        # 生成README内容
        content = generate_readme_content(example_name, info)

        # 写入文件
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"  ✓ {example_name}: README已生成")
        success_count += 1

    print(f"\n补充完成: {success_count}/{len(missing_examples)}")


def generate_readme_content(example_name, info):
    """生成README内容"""

    content = f"""# {info['title']}

## 概述

{info['description']}

## 物理原理

{info['physics']}

## 主要功能

"""

    for feature in info['key_features']:
        content += f"- {feature}\n"

    content += "\n## 应用场景\n\n"

    for app in info['applications']:
        content += f"- {app}\n"

    content += "\n## 脚本文件\n\n"

    for script in info['scripts']:
        content += f"- `{script}`\n"

    content += f"\n## 运行方法\n\n```bash\ncd examples/{example_name}\n"

    # 选择第一个脚本
    if info['scripts']:
        script = info['scripts'][0]
        if script.startswith('code/'):
            content += f"PYTHONPATH=../.. python {script}\n"
        else:
            content += f"PYTHONPATH=../.. python {script}\n"

    content += "```\n\n## 输出结果\n\n"

    for output in info['key_outputs']:
        content += f"- {output}\n"

    content += f"""
## 技术要点

本示例展示了以下技术：

"""

    for i, feature in enumerate(info['key_features'][:3], 1):
        content += f"{i}. **{feature}**\n"

    content += """
## 参考

- 项目文档: [HydroClaude文档](../../docs/)
- 相关示例: 查看 `examples/` 目录下的其他示例

---

*本README由自动化脚本生成*
"""

    return content


if __name__ == '__main__':
    print(f"\n{'='*80}")
    print("补充缺失的README文档")
    print('='*80)
    print()

    generate_missing_readmes()
