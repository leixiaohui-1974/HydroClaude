#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证案例批量运行工具

一键运行所有标准验证案例，生成完整报告
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import subprocess
from datetime import datetime
import json


class ValidationRunner:
    """验证案例批量运行器"""
    
    def __init__(self):
        self.validation_dir = Path(__file__).parent
        self.results_dir = self.validation_dir / 'results'
        self.results_dir.mkdir(exist_ok=True)
        
        # 定义所有验证案例
        self.cases = [
            {
                'id': 1,
                'name': 'Dam Break (Ritter Solution)',
                'script': self.validation_dir / 'analytical' / 'dam_break_ritter.py',
                'type': 'analytical',
                'priority': 'P0',
                'description': '溃坝标准案例，Ritter解析解',
            },
            {
                'id': 2,
                'name': 'MacDonald Case 1',
                'script': self.validation_dir / 'literature' / 'macdonald_case1.py',
                'type': 'literature',
                'priority': 'P0',
                'description': '稳态激波流动，MacDonald (1997)',
            },
            {
                'id': 3,
                'name': 'Steady Uniform Flow',
                'script': self.validation_dir / 'analytical' / 'steady_uniform_flow.py',
                'type': 'analytical',
                'priority': 'P0',
                'description': 'Manning公式验证，最基础测试',
            },
        ]
    
    def run_single_case(self, case):
        """运行单个验证案例"""
        print(f"\n{'='*80}")
        print(f"[{case['id']}] {case['name']}")
        print(f"{'='*80}")
        print(f"优先级: {case['priority']}")
        print(f"描述: {case['description']}")
        print(f"脚本: {case['script'].name}")
        print(f"")
        
        if not case['script'].exists():
            print(f"❌ 脚本文件不存在: {case['script']}")
            return {
                'success': False,
                'error': 'Script not found',
                'output': ''
            }
        
        try:
            # 运行脚本
            result = subprocess.run(
                [sys.executable, str(case['script'])],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            success = (result.returncode == 0)
            
            if success:
                print(f"✅ 案例 {case['id']} 运行成功")
            else:
                print(f"❌ 案例 {case['id']} 运行失败")
                print(f"错误信息:\n{result.stderr}")
            
            return {
                'success': success,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            print(f"⏱️ 案例 {case['id']} 超时")
            return {
                'success': False,
                'error': 'Timeout',
                'output': ''
            }
        except Exception as e:
            print(f"❌ 案例 {case['id']} 异常: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': ''
            }
    
    def run_all(self):
        """运行所有验证案例"""
        print("\n" + "="*80)
        print("HydroClaude 标准验证案例批量运行")
        print("="*80)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总案例数: {len(self.cases)}")
        print("")
        
        results = []
        
        for case in self.cases:
            result = self.run_single_case(case)
            results.append({
                'case': case,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        
        # 生成总结报告
        self.generate_summary_report(results)
        
        return results
    
    def generate_summary_report(self, results):
        """生成总结报告"""
        print("\n" + "="*80)
        print("验证总结")
        print("="*80)
        
        success_count = sum(1 for r in results if r['result']['success'])
        total_count = len(results)
        
        print(f"\n总计: {total_count} 个案例")
        print(f"成功: {success_count} ({success_count/total_count*100:.1f}%)")
        print(f"失败: {total_count - success_count}")
        
        print(f"\n详细结果:")
        for r in results:
            case = r['case']
            success = r['result']['success']
            status = "✅" if success else "❌"
            print(f"  {status} [{case['id']}] {case['name']}")
        
        # 保存JSON报告
        json_path = self.results_dir / f'validation_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        summary_data = {
            'timestamp': datetime.now().isoformat(),
            'total_cases': total_count,
            'success_count': success_count,
            'fail_count': total_count - success_count,
            'success_rate': success_count / total_count * 100,
            'cases': [
                {
                    'id': r['case']['id'],
                    'name': r['case']['name'],
                    'type': r['case']['type'],
                    'priority': r['case']['priority'],
                    'success': r['result']['success'],
                    'timestamp': r['timestamp']
                }
                for r in results
            ]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ JSON报告已保存: {json_path}")
        
        # 保存文本报告
        txt_path = self.results_dir / f'validation_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("HydroClaude 标准验证案例总结报告\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"总体统计:\n")
            f.write(f"  总案例数: {total_count}\n")
            f.write(f"  成功: {success_count} ({success_count/total_count*100:.1f}%)\n")
            f.write(f"  失败: {total_count - success_count}\n\n")
            
            f.write("="*80 + "\n")
            f.write("详细结果\n")
            f.write("="*80 + "\n\n")
            
            for r in results:
                case = r['case']
                result = r['result']
                
                f.write(f"[{case['id']}] {case['name']}\n")
                f.write(f"  类型: {case['type']}\n")
                f.write(f"  优先级: {case['priority']}\n")
                f.write(f"  描述: {case['description']}\n")
                f.write(f"  状态: ")
                if result['success']:
                    f.write("✅ 成功\n")
                else:
                    f.write("❌ 失败\n")
                    if 'error' in result:
                        f.write(f"  错误: {result['error']}\n")
                f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("结论\n")
            f.write("="*80 + "\n\n")
            
            if success_count == total_count:
                f.write("✅ 所有验证案例通过！\n")
                f.write("   HydroClaude求解器达到预期精度标准。\n")
            elif success_count > 0:
                f.write(f"⚠️ 部分验证案例通过 ({success_count}/{total_count})\n")
                f.write("   建议检查失败案例，分析原因并改进。\n")
            else:
                f.write("❌ 所有验证案例失败\n")
                f.write("   需要全面检查求解器实现。\n")
        
        print(f"✅ 文本报告已保存: {txt_path}")
        
        print(f"\n所有结果文件位于: {self.results_dir}/")


def main():
    """主函数"""
    runner = ValidationRunner()
    results = runner.run_all()
    
    print("\n" + "="*80)
    print("批量验证完成")
    print("="*80)
    print("\n请查看 validation_cases/results/ 目录获取详细结果")


if __name__ == '__main__':
    main()
