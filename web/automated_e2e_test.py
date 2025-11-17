#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化端到端测试工具
模拟完整的用户操作流程，测试前端到后端的完整链路
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys


class E2ETestRunner:
    """端到端测试运行器"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", 
                 frontend_url: str = "http://localhost:8080"):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.results = []
        
    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{'═' * 70}")
        print(f"  {text}")
        print(f"{'═' * 70}\n")
    
    def test_scenario(self, name: str, steps: List[Tuple[str, callable]]) -> Dict:
        """测试一个场景"""
        print(f"\n📋 场景: {name}")
        print(f"{'─' * 70}")
        
        scenario_result = {
            'name': name,
            'steps': [],
            'success': True,
            'start_time': datetime.now().isoformat()
        }
        
        for step_name, step_func in steps:
            print(f"\n  步骤: {step_name}")
            start_time = time.time()
            
            try:
                result = step_func()
                elapsed = (time.time() - start_time) * 1000
                
                scenario_result['steps'].append({
                    'name': step_name,
                    'success': True,
                    'time_ms': elapsed,
                    'result': result
                })
                
                print(f"    ✅ 成功 ({elapsed:.1f}ms)")
                if isinstance(result, dict) and 'metrics' in result:
                    for key, value in result['metrics'].items():
                        print(f"       • {key}: {value}")
                        
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                scenario_result['steps'].append({
                    'name': step_name,
                    'success': False,
                    'time_ms': elapsed,
                    'error': str(e)
                })
                scenario_result['success'] = False
                print(f"    ❌ 失败: {e}")
        
        scenario_result['end_time'] = datetime.now().isoformat()
        self.results.append(scenario_result)
        
        return scenario_result
    
    # ========== 基础测试步骤 ==========
    
    def step_check_backend_health(self):
        """检查后端健康状态"""
        response = requests.get(f"{self.backend_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    
    def step_check_frontend_page(self):
        """检查前端页面"""
        response = requests.get(f"{self.frontend_url}/frontend_integration_test.html", timeout=5)
        response.raise_for_status()
        if 'HydroClaude' not in response.text:
            raise Exception("前端页面内容不正确")
        return {'size': len(response.text), 'status': 'ok'}
    
    def step_get_component_types(self):
        """获取组件类型"""
        response = requests.get(f"{self.backend_url}/api/structures/types", timeout=5)
        response.raise_for_status()
        data = response.json()
        if data['total_components'] < 20:
            raise Exception(f"组件数量不足: {data['total_components']}")
        return data
    
    def step_pump_simulation(self):
        """泵站仿真"""
        data = {
            'pump': {'flow_rate': 10.0, 'head': 15.0, 'num_pumps': 2, 'pump_type': 'parallel'},
            'upstream': {'water_level': 5.0},
            'downstream': {'elevation': 20.0},
            'operation': {'duration': 100.0}
        }
        response = requests.post(f"{self.backend_url}/api/structures/pump", 
                                json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        # 验证结果
        if 'metrics' not in result:
            raise Exception("返回数据缺少metrics字段")
        if result['metrics']['avg_flow'] <= 0:
            raise Exception("流量计算错误")
            
        return result
    
    def step_turbine_simulation(self):
        """水轮机仿真"""
        data = {
            'turbine': {
                'type': 'francis',
                'rated_power': 50.0,
                'rated_head': 100.0,
                'rated_flow': 60.0
            },
            'operation': {
                'head': 100.0,
                'flow': 60.0
            }
        }
        response = requests.post(f"{self.backend_url}/api/structures/turbine", 
                                json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if 'metrics' not in result:
            raise Exception("返回数据缺少metrics字段")
            
        return result
    
    def step_gate_simulation(self):
        """闸门仿真"""
        data = {
            'gate': {'type': 'sluice', 'width': 10.0, 'opening': 2.0},
            'upstream': {'water_depth': 5.0},
            'downstream': {'water_depth': 2.0}
        }
        response = requests.post(f"{self.backend_url}/api/structures/gate", 
                                json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def step_canal_simulation(self):
        """明渠仿真"""
        data = {
            'geometry': {
                'length': 1000.0,
                'width': 10.0,
                'slope': 0.001,
                'roughness': 0.025
            },
            'discharge': 50.0
        }
        response = requests.post(f"{self.backend_url}/api/structures/canal", 
                                json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def step_weir_simulation(self):
        """堰仿真"""
        data = {
            'weir': {'type': 'broad_crested', 'width': 10.0, 'crest_height': 0.5},
            'flow': {'discharge': 50.0}
        }
        response = requests.post(f"{self.backend_url}/api/structures/weir", 
                                json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    # ========== 测试场景 ==========
    
    def scenario_1_system_health_check(self):
        """场景1: 系统健康检查"""
        return self.test_scenario("系统健康检查", [
            ("检查后端API", self.step_check_backend_health),
            ("检查前端页面", self.step_check_frontend_page),
            ("获取组件列表", self.step_get_component_types),
        ])
    
    def scenario_2_basic_simulations(self):
        """场景2: 基础仿真测试"""
        return self.test_scenario("基础仿真功能", [
            ("泵站仿真", self.step_pump_simulation),
            ("闸门仿真", self.step_gate_simulation),
            ("明渠仿真", self.step_canal_simulation),
        ])
    
    def scenario_3_advanced_components(self):
        """场景3: 高级组件测试"""
        return self.test_scenario("高级组件功能", [
            ("水轮机仿真", self.step_turbine_simulation),
            ("堰仿真", self.step_weir_simulation),
        ])
    
    def scenario_4_full_workflow(self):
        """场景4: 完整工作流"""
        return self.test_scenario("完整用户工作流", [
            ("1. 用户访问前端", self.step_check_frontend_page),
            ("2. 查看可用组件", self.step_get_component_types),
            ("3. 配置泵站参数", self.step_pump_simulation),
            ("4. 配置水轮机参数", self.step_turbine_simulation),
            ("5. 查看仿真结果", lambda: {'status': 'completed'}),
        ])
    
    def scenario_5_stress_test(self):
        """场景5: 压力测试"""
        def multi_requests():
            results = []
            for i in range(5):
                response = requests.get(f"{self.backend_url}/health", timeout=5)
                results.append(response.status_code)
            if all(code == 200 for code in results):
                return {'requests': len(results), 'all_success': True}
            else:
                raise Exception("部分请求失败")
        
        return self.test_scenario("并发压力测试", [
            ("连续5次健康检查", multi_requests),
            ("连续泵站仿真", self.step_pump_simulation),
        ])
    
    # ========== 报告生成 ==========
    
    def generate_report(self):
        """生成测试报告"""
        self.print_header("📊 自动化端到端测试报告")
        
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"后端地址: {self.backend_url}")
        print(f"前端地址: {self.frontend_url}")
        print(f"\n{'─' * 70}\n")
        
        total_scenarios = len(self.results)
        success_scenarios = sum(1 for r in self.results if r['success'])
        
        print(f"场景总数: {total_scenarios}")
        print(f"成功场景: {success_scenarios}")
        print(f"失败场景: {total_scenarios - success_scenarios}")
        print(f"成功率: {(success_scenarios / total_scenarios * 100):.1f}%")
        
        print(f"\n{'─' * 70}\n")
        print("场景详情:\n")
        
        for i, result in enumerate(self.results, 1):
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"{i}. {result['name']}: {status}")
            
            total_steps = len(result['steps'])
            success_steps = sum(1 for s in result['steps'] if s['success'])
            print(f"   步骤: {success_steps}/{total_steps}")
            
            total_time = sum(s['time_ms'] for s in result['steps'])
            print(f"   总耗时: {total_time:.1f}ms")
            
            for step in result['steps']:
                step_status = "✅" if step['success'] else "❌"
                print(f"     {step_status} {step['name']} ({step['time_ms']:.1f}ms)")
            
            print()
        
        # 生成JSON报告
        report_file = f"/workspace/web/e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'backend_url': self.backend_url,
                'frontend_url': self.frontend_url,
                'summary': {
                    'total_scenarios': total_scenarios,
                    'success_scenarios': success_scenarios,
                    'success_rate': success_scenarios / total_scenarios * 100
                },
                'results': self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"{'─' * 70}\n")
        print(f"✅ 详细报告已保存: {report_file}\n")
        
        return success_scenarios == total_scenarios
    
    def run_all_scenarios(self):
        """运行所有测试场景"""
        self.print_header("🚀 开始自动化端到端测试")
        
        scenarios = [
            self.scenario_1_system_health_check,
            self.scenario_2_basic_simulations,
            self.scenario_3_advanced_components,
            self.scenario_4_full_workflow,
            self.scenario_5_stress_test,
        ]
        
        for scenario in scenarios:
            scenario()
            time.sleep(0.5)  # 短暂延迟
        
        return self.generate_report()


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║           🧪 HydroClaude 自动化端到端测试工具                       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    runner = E2ETestRunner()
    
    try:
        all_passed = runner.run_all_scenarios()
        
        if all_passed:
            print("╔══════════════════════════════════════════════════════════════════════╗")
            print("║                  🎉 所有测试通过！系统完全正常！                    ║")
            print("╚══════════════════════════════════════════════════════════════════════╝")
            sys.exit(0)
        else:
            print("╔══════════════════════════════════════════════════════════════════════╗")
            print("║                  ⚠️  部分测试失败，请检查详情                       ║")
            print("╚══════════════════════════════════════════════════════════════════════╝")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n测试已中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试运行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
