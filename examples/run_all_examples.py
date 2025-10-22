#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行所有示例脚本并生成结果
- 自动运行每个example的核心脚本
- 生成图表、GIF动画
- 创建README文档
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import time


class ExampleRunner:
    """示例运行器"""

    def __init__(self, examples_root):
        self.examples_root = Path(examples_root)
        self.results = {}

        # 从organization_report.json读取核心脚本列表
        report_file = self.examples_root / 'organization_report.json'
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report = json.load(f)

    def get_example_info(self, example_name):
        """获取示例信息"""
        info = {
            'example_01_canal_flow': {
                'title': '明渠非恒定流仿真',
                'description': '演示明渠水流的非恒定流动过程，包括水位、流速、流量的时空分布',
                'key_features': ['Saint-Venant方程', 'Preissmann格式', '边界条件处理', '收敛性分析']
            },
            'example_02_pump_system': {
                'title': '泵站系统仿真',
                'description': '模拟泵站启停过程及其对管网的影响',
                'key_features': ['水泵特性曲线', '水锤效应', '调压设施', '动态响应']
            },
            'example_02_spillway_cascade': {
                'title': '溢洪道级联系统',
                'description': '模拟溢洪道级联流动和能量耗散过程',
                'key_features': ['堰流计算', '跌水', '能量耗散', '水面线']
            },
            'example_03_turbine_demo': {
                'title': '水轮机调节系统',
                'description': '演示水轮机及其调速系统的动态响应',
                'key_features': ['Francis水轮机', 'PID调速器', '导叶开度控制', '转速调节']
            },
            'example_04_hydropower_system': {
                'title': '水电站系统仿真',
                'description': '完整的水电站系统，包括引水系统、水轮机、发电机',
                'key_features': ['压力管道', '调压井', '水轮机', '发电机', '负荷响应']
            },
            'example_05_transient_analysis': {
                'title': '甩负荷暂态分析',
                'description': '分析水电站甩负荷时的暂态过程',
                'key_features': ['负荷突变', '转速上升', '导叶关闭', '水位波动']
            },
            'example_06_sil_basic': {
                'title': 'SIL仿真基础',
                'description': '软件在环(SIL)仿真的基本示例',
                'key_features': ['实时仿真', '外部接口', '数据交互', 'Co-simulation']
            },
            'example_07_fault_test': {
                'title': '故障测试',
                'description': '测试系统在各种故障工况下的响应',
                'key_features': ['短路故障', '失磁', '阀门卡死', '保护动作']
            },
            'example_08_load_acceptance': {
                'title': '接受负荷暂态',
                'description': '分析水电站接受负荷时的暂态过程',
                'key_features': ['负荷增加', '转速下降', '导叶开启', '调节响应']
            },
            'example_09_pipe_rk4': {
                'title': '管道系统RK4求解',
                'description': '使用Runge-Kutta方法求解管道水流',
                'key_features': ['RK4积分', 'MOC方法', '时间步长自适应', '精度分析']
            },
            'example_10_series_network': {
                'title': '串联管网系统',
                'description': '多段串联管道的水力分析',
                'key_features': ['串联管道', '节点连续', '压力传递', '流量守恒']
            },
            'example_11_tree_network': {
                'title': '树状管网系统',
                'description': '树状拓扑管网的水力计算',
                'key_features': ['树状网络', '分岔节点', '流量分配', '压力平衡']
            },
            'example_12_loop_network': {
                'title': '环状管网系统',
                'description': '带闭合环路的复杂管网分析',
                'key_features': ['环状网络', 'Hardy-Cross', '流量平差', '压力平衡']
            },
            'example_13_adaptive_timescale': {
                'title': '自适应时间尺度',
                'description': '演示自适应时间步长的求解策略',
                'key_features': ['时间步长自适应', '误差控制', '计算效率', 'CFL条件']
            },
            'example_14_adaptive_mpc': {
                'title': '自适应模型预测控制',
                'description': '基于MPC的自适应控制策略',
                'key_features': ['MPC控制', '在线优化', '约束处理', '滚动优化']
            },
            'example_15_rls_identification': {
                'title': 'RLS参数辨识',
                'description': '使用递推最小二乘法进行系统辨识',
                'key_features': ['RLS算法', '参数辨识', '自适应滤波', '收敛性分析']
            },
            'example_16_weirs_application': {
                'title': '堰闸应用',
                'description': '各种堰闸结构的水力计算',
                'key_features': ['堰流公式', '闸门流量', '淹没度', '流量系数']
            },
            'example_17_reservoir_basic': {
                'title': '水库基础模型',
                'description': '水库的基本水量平衡和调度',
                'key_features': ['库容曲线', '入出流平衡', '水位预报', '调度规则']
            },
            'example_18_cascade_hydropower': {
                'title': '梯级水电站',
                'description': '梯级水电站群的协调调度',
                'key_features': ['梯级调度', '区间流量', '蓄放水', '出力优化']
            },
            'example_19_water_transfer': {
                'title': '跨流域调水',
                'description': '跨流域调水工程的仿真',
                'key_features': ['长距离输水', '多级泵站', '平衡计算', '水位控制']
            },
            'example_20_urban_water_supply': {
                'title': '城市供水系统',
                'description': '城市供水管网的运行优化',
                'key_features': ['供水调度', '压力管理', '水泵优化', '用水预测']
            },
            'example_21_irrigation_optimization': {
                'title': '灌溉优化',
                'description': '灌区灌溉制度的优化',
                'key_features': ['灌溉计划', '渠系配水', '用水效率', '作物需水']
            },
            'example_22_water_hammer': {
                'title': '水锤效应',
                'description': '管道水锤现象的计算和防护',
                'key_features': ['水锤压力', '波速计算', '阀门操作', '保护措施']
            },
            'example_23_control_comparison': {
                'title': '控制策略比较',
                'description': '不同控制策略的性能对比',
                'key_features': ['PID控制', 'MPC控制', '模糊控制', '性能指标']
            },
            'example_24_multi_objective_optimization': {
                'title': '多目标优化',
                'description': '多目标优化算法在水利工程中的应用',
                'key_features': ['Pareto前沿', 'NSGA-II', '权衡分析', '决策支持']
            }
        }

        return info.get(example_name, {
            'title': example_name.replace('example_', '').replace('_', ' ').title(),
            'description': '示例说明',
            'key_features': []
        })

    def run_example(self, example_dir, script_path):
        """运行单个示例脚本"""
        print(f"\n{'='*80}")
        print(f"运行: {example_dir.name} / {script_path.name}")
        print('='*80)

        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.examples_root.parent)
        env['MPLBACKEND'] = 'Agg'  # 使用非交互式后端

        # 构建命令
        cmd = [sys.executable, str(script_path)]

        # 运行脚本
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(example_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            elapsed_time = time.time() - start_time

            success = result.returncode == 0

            return {
                'success': success,
                'elapsed_time': elapsed_time,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            print(f"  ⚠️  超时（>300秒）")
            return {
                'success': False,
                'elapsed_time': 300,
                'stdout': '',
                'stderr': 'Timeout after 300 seconds',
                'returncode': -1
            }
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return {
                'success': False,
                'elapsed_time': time.time() - start_time,
                'stdout': '',
                'stderr': str(e),
                'returncode': -2
            }

    def run_all_examples(self, limit=None):
        """运行所有示例"""
        print(f"\n{'='*80}")
        print("开始运行所有示例")
        print('='*80)

        example_dirs = sorted([d for d in self.examples_root.glob('example_*') if d.is_dir()])

        if limit:
            example_dirs = example_dirs[:limit]

        total = len(example_dirs)
        success_count = 0

        for i, example_dir in enumerate(example_dirs, 1):
            print(f"\n[{i}/{total}] {example_dir.name}")

            # 查找核心脚本
            core_scripts = []

            # 优先查找code目录
            code_dir = example_dir / 'code'
            if code_dir.exists():
                core_scripts = [f for f in code_dir.glob('*.py')
                               if f.name not in ['__init__.py']
                               and not f.name.startswith('test_')]

            # 如果没有，查找根目录
            if not core_scripts:
                core_scripts = [f for f in example_dir.glob('*.py')
                               if f.name not in ['__init__.py']
                               and not f.name.startswith('test_')]

            if not core_scripts:
                print(f"  ⚠️  未找到可运行脚本")
                continue

            # 只运行第一个核心脚本（避免耗时过长）
            script = core_scripts[0]
            result = self.run_example(example_dir, script)

            if result['success']:
                print(f"  ✓ 成功 ({result['elapsed_time']:.2f}秒)")
                success_count += 1
            else:
                print(f"  ✗ 失败 (返回码: {result['returncode']})")
                if result['stderr']:
                    print(f"     错误: {result['stderr'][:200]}")

            self.results[example_dir.name] = result

        print(f"\n{'='*80}")
        print(f"运行完成: {success_count}/{total} 成功")
        print('='*80)

        return self.results

    def save_results(self):
        """保存运行结果"""
        results_file = self.examples_root / 'run_results.json'

        # 简化结果以便保存
        simplified_results = {}
        for name, result in self.results.items():
            simplified_results[name] = {
                'success': result['success'],
                'elapsed_time': result['elapsed_time'],
                'returncode': result['returncode'],
                'stderr_preview': result['stderr'][:500] if result['stderr'] else ''
            }

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(simplified_results, f, indent=2, ensure_ascii=False)

        print(f"\n运行结果已保存到: {results_file}")


def main():
    """主函数"""
    examples_root = Path(__file__).parent

    runner = ExampleRunner(examples_root)

    # 运行所有示例（可以设置limit只运行前几个）
    results = runner.run_all_examples(limit=5)  # 先运行前5个测试

    # 保存结果
    runner.save_results()


if __name__ == '__main__':
    main()
