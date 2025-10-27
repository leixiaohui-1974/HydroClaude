#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件驱动系统测试

验证：
1. 配置文件解析
2. 自动建模
3. 一键运行
4. 多种场景

Author: Claude (AI Assistant)
Date: 2025-10-27
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import HydraulicModelConfig


class ConfigSystemTest:
    """配置文件系统测试"""
    
    def __init__(self):
        self.tests = []
    
    def test_1_simple_canal(self):
        """测试1: 简单明渠配置"""
        print("\n" + "="*80)
        print("测试1: 简单明渠配置解析")
        print("="*80)
        
        config_file = "config/examples/simple_canal.yaml"
        
        if not os.path.exists(config_file):
            print(f"⚠️  配置文件不存在: {config_file}")
            self.tests.append(('简单明渠', False, "文件不存在"))
            return
        
        try:
            # 加载配置
            config = HydraulicModelConfig(config_file)
            print("✓ 配置加载成功")
            
            # 打印摘要
            config.print_summary()
            
            # 创建模型
            solver = config.build_model()
            print(f"\n✓ 模型创建成功: {type(solver).__name__}")
            
            self.tests.append(('简单明渠配置', True, 0))
            
        except Exception as e:
            print(f"✗ 失败: {e}")
            self.tests.append(('简单明渠配置', False, str(e)))
    
    def test_2_gate_config(self):
        """测试2: 单闸门配置"""
        print("\n" + "="*80)
        print("测试2: 单闸门配置解析")
        print("="*80)
        
        config_file = "config/examples/single_gate.yaml"
        
        if not os.path.exists(config_file):
            print(f"⚠️  配置文件不存在: {config_file}")
            self.tests.append(('单闸门配置', False, "文件不存在"))
            return
        
        try:
            config = HydraulicModelConfig(config_file)
            solver = config.build_model()
            
            # 验证结构物
            assert len(solver.structures) == 1, "应有1个结构物"
            assert solver.structures[0].__class__.__name__ == 'SluiceGate', "应为闸门"
            
            print(f"✓ 配置解析成功")
            print(f"✓ 结构物: {len(solver.structures)}个")
            
            self.tests.append(('单闸门配置', True, 0))
            
        except Exception as e:
            print(f"✗ 失败: {e}")
            self.tests.append(('单闸门配置', False, str(e)))
    
    def test_3_cascade_config(self):
        """测试3: 串联闸泵群配置"""
        print("\n" + "="*80)
        print("测试3: 串联闸泵群配置解析")
        print("="*80)
        
        config_file = "config/examples/gate_pump_cascade.yaml"
        
        if not os.path.exists(config_file):
            print(f"⚠️  配置文件不存在: {config_file}")
            self.tests.append(('串联闸泵群配置', False, "文件不存在"))
            return
        
        try:
            config = HydraulicModelConfig(config_file)
            solver = config.build_model()
            
            # 验证结构物
            assert len(solver.structures) == 3, "应有3个结构物"
            
            structure_types = [s.__class__.__name__ for s in solver.structures]
            print(f"✓ 配置解析成功")
            print(f"✓ 结构物: {structure_types}")
            
            self.tests.append(('串联闸泵群配置', True, 0))
            
        except Exception as e:
            print(f"✗ 失败: {e}")
            self.tests.append(('串联闸泵群配置', False, str(e)))
    
    def test_4_one_line_simulation(self):
        """测试4: 一行代码运行模拟"""
        print("\n" + "="*80)
        print("测试4: 一行代码运行模拟")
        print("="*80)
        
        config_file = "config/examples/simple_canal.yaml"
        
        if not os.path.exists(config_file):
            print(f"⚠️  配置文件不存在: {config_file}")
            self.tests.append(('一行代码模拟', False, "文件不存在"))
            return
        
        try:
            # 一行代码完成！
            config = HydraulicModelConfig(config_file)
            result = config.run_simulation(verbose=False)
            
            # 验证结果
            assert 'converged' in result or 'h' in result, "应有求解结果"
            
            print(f"✓ 一行代码模拟成功")
            if 'error' in result:
                print(f"✓ 流量误差: {result['error']:.4f}%")
            
            self.tests.append(('一行代码模拟', True, 0))
            
        except Exception as e:
            print(f"✗ 失败: {e}")
            import traceback
            traceback.print_exc()
            self.tests.append(('一行代码模拟', False, str(e)))
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*80)
        print("配置文件系统测试总结")
        print("="*80)
        
        total = len(self.tests)
        passed = sum(1 for _, p, _ in self.tests if p)
        
        print(f"总测试: {total}")
        print(f"通过: {passed}/{total}")
        print("")
        
        for name, passed_flag, error in self.tests:
            status = "✓ PASS" if passed_flag else "✗ FAIL"
            error_str = f"(误差={error:.2f}%)" if isinstance(error, (int, float)) else f"({error})" if error else ""
            print(f"{status} | {name} {error_str}")
        
        print("")
        print("="*80)
        if passed == total:
            print("🎉 配置文件系统全部测试通过！")
        else:
            print(f"⚠️  {total-passed}个测试未通过")
        print("="*80)
    
    def run_all(self):
        """运行所有测试"""
        print("="*80)
        print("配置文件驱动系统测试套件")
        print("="*80)
        
        self.test_1_simple_canal()
        self.test_2_gate_config()
        self.test_3_cascade_config()
        self.test_4_one_line_simulation()
        
        self.print_summary()


def main():
    """主函数"""
    test = ConfigSystemTest()
    test.run_all()


if __name__ == '__main__':
    main()
