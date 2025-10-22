#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为所有示例生成README.md文档
"""

import os
from pathlib import Path
import json


class READMEGenerator:
    """README生成器"""

    def __init__(self, examples_root):
        self.examples_root = Path(examples_root)

        # 示例信息数据库
        self.examples_info = {
            'example_01_canal_flow': {
                'title': '明渠非恒定流仿真',
                'description': '演示明渠水流的非恒定流动过程，使用Saint-Venant方程描述水位、流速、流量的时空分布。',
                'key_features': [
                    'Saint-Venant方程求解',
                    '三种数值方法：显式、Preissmann、HLL',
                    '边界条件处理（上游流量、下游水深）',
                    '收敛性和稳定性分析',
                    '动态可视化（GIF动画）'
                ],
                'physics': '明渠流动遵循连续性方程和动量方程（Saint-Venant方程组）',
                'applications': ['灌溉渠道', '排水系统', '河流防洪', '水位预报'],
                'key_outputs': [
                    '水位-距离分布图',
                    '流速-距离分布图',
                    '时间演化GIF动画',
                    '收敛性分析报告'
                ]
            },
            'example_02_pump_system': {
                'title': '泵站系统仿真',
                'description': '模拟泵站启停过程及其对管网系统的水力影响，包括水锤效应和调压设施的作用。',
                'key_features': [
                    '泵特性曲线建模',
                    '启停过程动态响应',
                    '水锤波传播',
                    '调压井/罐作用'
                ],
                'physics': '泵站系统涉及泵的能量转换、管道水击、压力波动',
                'applications': ['城市供水', '灌溉泵站', '排涝泵站', '输水工程'],
                'key_outputs': []
            },
            'example_02_spillway_cascade': {
                'title': '溢洪道级联系统',
                'description': '模拟溢洪道级联流动过程，包括堰流计算、跌水、能量耗散。',
                'key_features': [
                    '堰流公式应用',
                    '级联跌水计算',
                    '能量耗散分析',
                    '水面线计算'
                ],
                'physics': '溢洪道流动涉及堰流、急流、跌水的能量转换',
                'applications': ['水库泄洪', '防洪工程', '梯级电站', '河道整治'],
                'key_outputs': []
            },
            'example_03_turbine_demo': {
                'title': '水轮机调节系统',
                'description': '演示水轮机及其调速系统的动态响应，包括PID调速器对转速的控制。',
                'key_features': [
                    'Francis水轮机模型',
                    'PID调速器',
                    '导叶开度控制',
                    '转速调节响应'
                ],
                'physics': '水轮机通过导叶调节流量，调速器维持转速稳定',
                'applications': ['水电站控制', '频率调节', '负荷响应', '孤网运行'],
                'key_outputs': []
            },
            'example_04_hydropower_system': {
                'title': '水电站系统仿真',
                'description': '完整的水电站系统仿真，包括引水系统、压力管道、调压井、水轮机和发电机。',
                'key_features': [
                    '压力管道水击',
                    '调压井水位波动',
                    '水轮机-发电机耦合',
                    '负荷响应特性'
                ],
                'physics': '水电站是水力-机械-电气的多物理场耦合系统',
                'applications': ['水电站设计', '过渡过程分析', '控制策略优化', '稳定性分析'],
                'key_outputs': []
            },
            'example_05_transient_analysis': {
                'title': '甩负荷暂态分析',
                'description': '分析水电站甩负荷（负荷突然减小或消失）时的暂态过程。',
                'key_features': [
                    '负荷突变响应',
                    '转速上升分析',
                    '导叶关闭策略',
                    '调压井水位波动'
                ],
                'physics': '甩负荷时动能转化为势能，导致转速上升和水位波动',
                'applications': ['电站安全分析', '调速器整定', '保护配置', '事故预案'],
                'key_outputs': []
            },
            'example_06_sil_basic': {
                'title': 'SIL仿真基础',
                'description': '软件在环（Software-in-the-Loop）仿真的基本示例，演示外部接口和数据交互。',
                'key_features': [
                    '实时仿真框架',
                    '外部接口协议',
                    '数据交互机制',
                    'Co-simulation'
                ],
                'physics': 'SIL允许将实际控制软件与仿真模型联合运行',
                'applications': ['控制器测试', '硬件在环', '虚拟调试', '系统集成'],
                'key_outputs': []
            },
            'example_07_fault_test': {
                'title': '故障测试',
                'description': '测试水电站系统在各种故障工况下的响应和保护动作。',
                'key_features': [
                    '短路故障',
                    '失磁保护',
                    '阀门卡死',
                    '保护动作逻辑'
                ],
                'physics': '故障工况下系统的非正常运行特性',
                'applications': ['保护配置', '故障诊断', '安全评估', '应急预案'],
                'key_outputs': []
            },
            'example_08_load_acceptance': {
                'title': '接受负荷暂态',
                'description': '分析水电站接受负荷（负荷突然增加）时的暂态过程。',
                'key_features': [
                    '负荷增加响应',
                    '转速下降分析',
                    '导叶开启策略',
                    '频率恢复过程'
                ],
                'physics': '接受负荷时电能消耗增加，转速下降，需快速增加水流',
                'applications': ['一次调频', '备用容量', '电网支撑', '频率调节'],
                'key_outputs': []
            },
            'example_09_pipe_rk4': {
                'title': '管道系统RK4求解',
                'description': '使用Runge-Kutta方法求解管道水流，对比不同时间积分方法的精度。',
                'key_features': [
                    'RK4时间积分',
                    'MOC特征线方法',
                    '时间步长自适应',
                    '精度对比分析'
                ],
                'physics': '管道水击波的传播和反射',
                'applications': ['长距离输水', '水锤分析', '数值方法研究', '精度评估'],
                'key_outputs': []
            },
            'example_10_series_network': {
                'title': '串联管网系统',
                'description': '多段串联管道的水力计算，包括节点连续性和压力传递。',
                'key_features': [
                    '串联管段',
                    '节点连续方程',
                    '压力传递',
                    '流量守恒'
                ],
                'physics': '串联系统中流量处处相等，总水头损失为各段之和',
                'applications': ['输水管线', '长距离管道', '多级泵站', '压力分析'],
                'key_outputs': []
            },
            'example_11_tree_network': {
                'title': '树状管网系统',
                'description': '树状拓扑管网的水力计算，处理分岔节点的流量分配。',
                'key_features': [
                    '树状网络拓扑',
                    '分岔节点处理',
                    '流量分配计算',
                    '节点压力平衡'
                ],
                'physics': '分岔点满足流量守恒和能量守恒',
                'applications': ['供水管网', '配水系统', '灌溉网络', '分支管道'],
                'key_outputs': []
            },
            'example_12_loop_network': {
                'title': '环状管网系统',
                'description': '带闭合环路的复杂管网分析，使用Hardy-Cross方法平差。',
                'key_features': [
                    '环状网络拓扑',
                    'Hardy-Cross平差',
                    '流量分配优化',
                    '压力平衡计算'
                ],
                'physics': '环路系统流量分配满足能量方程的闭合条件',
                'applications': ['城市管网', '复杂管网', '流量优化', '供水可靠性'],
                'key_outputs': []
            },
            'example_13_adaptive_timescale': {
                'title': '自适应时间尺度',
                'description': '演示自适应时间步长的求解策略，根据误差自动调整步长。',
                'key_features': [
                    '时间步长自适应',
                    '局部误差估计',
                    'CFL条件检查',
                    '计算效率优化'
                ],
                'physics': '不同物理过程有不同的时间尺度',
                'applications': ['刚性系统', '多时间尺度', '高效求解', '误差控制'],
                'key_outputs': []
            },
            'example_14_adaptive_mpc': {
                'title': '自适应模型预测控制',
                'description': '基于MPC的自适应控制策略，在线优化和约束处理。',
                'key_features': [
                    'MPC控制器',
                    '滚动时域优化',
                    '约束处理',
                    '自适应调整'
                ],
                'physics': 'MPC通过预测模型和优化算法实现最优控制',
                'applications': ['先进控制', '多变量控制', '约束系统', '预测控制'],
                'key_outputs': []
            },
            'example_15_rls_identification': {
                'title': 'RLS参数辨识',
                'description': '使用递推最小二乘法（RLS）进行系统参数在线辨识。',
                'key_features': [
                    'RLS算法',
                    '在线参数辨识',
                    '自适应滤波',
                    '收敛性分析'
                ],
                'physics': '通过最小化预测误差平方和辨识模型参数',
                'applications': ['系统辨识', '自适应控制', '参数估计', '模型更新'],
                'key_outputs': []
            },
            'example_16_weirs_application': {
                'title': '堰闸应用',
                'description': '各种堰闸结构的水力计算，包括不同堰型和淹没条件。',
                'key_features': [
                    '堰流公式',
                    '闸门流量计算',
                    '淹没度影响',
                    '流量系数确定'
                ],
                'physics': '堰闸流量与上下游水位差和堰型有关',
                'applications': ['水位控制', '流量测量', '灌溉配水', '河道调节'],
                'key_outputs': []
            },
            'example_17_reservoir_basic': {
                'title': '水库基础模型',
                'description': '水库的基本水量平衡和调度计算。',
                'key_features': [
                    '库容曲线',
                    '水量平衡方程',
                    '水位预报',
                    '调度规则'
                ],
                'physics': '水库蓄水量变化等于入流减出流',
                'applications': ['水库调度', '防洪计算', '兴利调节', '水位预报'],
                'key_outputs': []
            },
            'example_18_cascade_hydropower': {
                'title': '梯级水电站',
                'description': '梯级水电站群的协调调度和优化运行。',
                'key_features': [
                    '梯级水力联系',
                    '区间流量计算',
                    '蓄放水协调',
                    '出力优化'
                ],
                'physics': '梯级电站通过河道相连，上级出流影响下级入流',
                'applications': ['流域调度', '梯级优化', '水资源配置', '发电调度'],
                'key_outputs': []
            },
            'example_19_water_transfer': {
                'title': '跨流域调水',
                'description': '跨流域调水工程的仿真，包括长距离输水和多级泵站。',
                'key_features': [
                    '长距离输水',
                    '多级泵站联合调度',
                    '水量平衡',
                    '水位控制'
                ],
                'physics': '调水系统是长距离、大流量的复杂输水系统',
                'applications': ['南水北调', '引水工程', '区域供水', '水资源配置'],
                'key_outputs': []
            },
            'example_20_urban_water_supply': {
                'title': '城市供水系统',
                'description': '城市供水管网的运行调度和压力管理优化。',
                'key_features': [
                    '供水调度',
                    '压力分区管理',
                    '水泵优化运行',
                    '用水需求预测'
                ],
                'physics': '供水系统需满足用户压力需求和水量需求',
                'applications': ['城市供水', '管网优化', '压力控制', '节能运行'],
                'key_outputs': []
            },
            'example_21_irrigation_optimization': {
                'title': '灌溉优化',
                'description': '灌区灌溉制度的优化和渠系配水计算。',
                'key_features': [
                    '灌溉计划优化',
                    '渠系配水',
                    '用水效率提升',
                    '作物需水分析'
                ],
                'physics': '灌溉系统需平衡作物需水和水资源供给',
                'applications': ['灌区管理', '节水灌溉', '配水优化', '农业水管理'],
                'key_outputs': []
            },
            'example_22_water_hammer': {
                'title': '水锤效应',
                'description': '管道水锤现象的计算和防护措施分析。',
                'key_features': [
                    '水锤压力计算',
                    '波速确定',
                    '阀门操作影响',
                    '保护措施评估'
                ],
                'physics': '水锤是液流速度急变引起的压力冲击波',
                'applications': ['管道设计', '水锤防护', '阀门操作', '安全评估'],
                'key_outputs': []
            },
            'example_23_control_comparison': {
                'title': '控制策略比较',
                'description': '不同控制策略（PID、MPC、模糊控制）的性能对比。',
                'key_features': [
                    'PID控制',
                    'MPC控制',
                    '模糊控制',
                    '性能指标对比'
                ],
                'physics': '不同控制策略有不同的响应特性和适用范围',
                'applications': ['控制选型', '性能评估', '参数整定', '控制优化'],
                'key_outputs': []
            },
            'example_24_multi_objective_optimization': {
                'title': '多目标优化',
                'description': '多目标优化算法在水利工程中的应用，如发电与防洪的权衡。',
                'key_features': [
                    'Pareto前沿',
                    'NSGA-II算法',
                    '多目标权衡',
                    '决策支持'
                ],
                'physics': '水利系统往往有多个相互冲突的目标',
                'applications': ['水库调度', '方案比选', '综合效益', '决策分析'],
                'key_outputs': []
            }
        }

    def generate_readme(self, example_dir):
        """为单个示例生成README.md"""
        example_name = example_dir.name
        info = self.examples_info.get(example_name, {})

        if not info:
            print(f"  ⚠️  未找到 {example_name} 的信息")
            return False

        # 查找脚本文件
        scripts = []
        code_dir = example_dir / 'code'
        if code_dir.exists():
            scripts = sorted([f.name for f in code_dir.glob('*.py')
                            if f.name != '__init__.py' and not f.name.startswith('test_')])
        if not scripts:
            scripts = sorted([f.name for f in example_dir.glob('*.py')
                            if f.name != '__init__.py' and not f.name.startswith('test_')])

        # 查找输出文件
        outputs_dir = example_dir / 'outputs'
        figures = []
        animations = []
        if outputs_dir.exists():
            figures_dir = outputs_dir / 'figures'
            if figures_dir.exists():
                figures = sorted([f.name for f in figures_dir.glob('*.png')])

            animations_dir = outputs_dir / 'animations'
            if animations_dir.exists():
                animations = sorted([f.name for f in animations_dir.glob('*.gif')])

        # 生成README内容
        readme_content = self._generate_readme_content(
            example_name, info, scripts, figures, animations
        )

        # 写入文件
        readme_path = example_dir / 'README.md'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"  ✓ README已生成: {readme_path}")
        return True

    def _generate_readme_content(self, example_name, info, scripts, figures, animations):
        """生成README内容"""
        content = f"""# {info.get('title', example_name)}

## 概述

{info.get('description', '示例说明')}

## 物理原理

{info.get('physics', '物理原理说明')}

## 主要功能

"""

        # 添加功能列表
        for feature in info.get('key_features', []):
            content += f"- {feature}\n"

        content += "\n## 应用场景\n\n"

        # 添加应用场景
        for app in info.get('applications', []):
            content += f"- {app}\n"

        content += "\n## 脚本文件\n\n"

        # 添加脚本列表
        if scripts:
            for script in scripts:
                content += f"- `{script}`\n"
        else:
            content += "- 待添加\n"

        content += "\n## 运行方法\n\n```bash\n"
        content += f"cd examples/{example_name}\n"

        if scripts:
            # 选择第一个脚本作为示例
            script = scripts[0]
            if (Path(f"examples/{example_name}/code").exists()
                and Path(f"examples/{example_name}/code/{script}").exists()):
                content += f"PYTHONPATH=../.. python code/{script}\n"
            else:
                content += f"PYTHONPATH=../.. python {script}\n"
        else:
            content += "# 运行脚本\n"

        content += "```\n\n## 输出结果\n\n"

        # 添加输出说明
        if info.get('key_outputs'):
            for output in info['key_outputs']:
                content += f"- {output}\n"
        else:
            content += "### 图表\n\n"
            if figures:
                for fig in figures[:5]:  # 只列出前5个
                    content += f"- `outputs/figures/{fig}`\n"
            else:
                content += "- 待生成\n"

            content += "\n### 动画\n\n"
            if animations:
                for anim in animations:
                    content += f"- `outputs/animations/{anim}`\n"
                    # 嵌入第一个GIF
                    if anim == animations[0]:
                        content += f"\n![动画]({Path('outputs/animations') / anim})\n"
            else:
                content += "- 待生成\n"

        content += "\n## 技术要点\n\n"
        content += "本示例展示了以下技术：\n\n"
        for i, feature in enumerate(info.get('key_features', [])[:3], 1):
            content += f"{i}. **{feature}**\n"

        content += "\n## 参考\n\n"
        content += "- 项目文档: [HydroClaude文档](../../docs/)\n"
        content += f"- 相关示例: 查看 `examples/` 目录下的其他示例\n"

        content += "\n---\n\n"
        content += "*本README由自动化脚本生成*\n"

        return content

    def generate_all_readmes(self):
        """为所有示例生成README"""
        print(f"\n{'='*80}")
        print("生成所有示例的README.md")
        print('='*80)

        example_dirs = sorted([d for d in self.examples_root.glob('example_*') if d.is_dir()])

        success_count = 0
        for i, example_dir in enumerate(example_dirs, 1):
            print(f"\n[{i}/{len(example_dirs)}] {example_dir.name}")

            if self.generate_readme(example_dir):
                success_count += 1

        print(f"\n{'='*80}")
        print(f"README生成完成: {success_count}/{len(example_dirs)}")
        print('='*80)


def main():
    """主函数"""
    examples_root = Path(__file__).parent

    generator = READMEGenerator(examples_root)
    generator.generate_all_readmes()


if __name__ == '__main__':
    main()
