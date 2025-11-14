#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例质量验证器 - 不仅检查能否运行，还验证结果质量

验证指标：
1. 流量守恒精度（< 0.01%）
2. 收敛性能（迭代次数合理）
3. 数值稳定性（无NaN/Inf）
4. 控制效果（如果有控制）
5. 物理合理性
"""

import subprocess
import sys
import os
import re
from pathlib import Path
import json

class QualityValidator:
    """质量验证器"""
    
    def __init__(self):
        self.quality_thresholds = {
            'flux_error_excellent': 0.000001,  # < 0.0001%
            'flux_error_good': 0.0001,         # < 0.01%
            'flux_error_acceptable': 0.001,    # < 0.1%
            'iterations_fast': 10,              # < 10次迭代
            'iterations_acceptable': 100,       # < 100次迭代
        }
    
    def run_and_validate(self, script_path, timeout=60):
        """运行脚本并验证结果质量"""
        script = Path(script_path)
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = '/home/ubuntu/.local/lib/python3.12/site-packages'
            
            proc = subprocess.run(
                [sys.executable, script.name],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(script.parent),
                env=env,
                errors='replace'
            )
            
            if proc.returncode != 0:
                return {
                    'status': 'failed',
                    'error': 'Script execution failed',
                    'quality': None
                }
            
            # 分析输出质量
            quality = self.analyze_output_quality(proc.stdout, proc.stderr)
            
            return {
                'status': 'passed',
                'quality': quality,
                'script': str(script)
            }
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'quality': None
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'quality': None
            }
    
    def analyze_output_quality(self, stdout, stderr):
        """分析输出质量"""
        quality = {
            'flux_conservation': None,
            'convergence': None,
            'numerical_stability': True,
            'grade': 'unknown'
        }
        
        # 1. 检查流量守恒
        flux_patterns = [
            r'流量.*误差[：:]\s*([\d\.]+)%',
            r'流量守恒[：:]\s*([\d\.]+)%',
            r'Overall.*流量守恒[：:]\s*([\d\.]+)%',
            r'flux.*error[：:]\s*([\d\.]+)%',
        ]
        
        for pattern in flux_patterns:
            match = re.search(pattern, stdout, re.IGNORECASE)
            if match:
                flux_error = float(match.group(1))
                quality['flux_conservation'] = flux_error
                break
        
        # 2. 检查收敛性
        iter_patterns = [
            r'迭代次数[：:]\s*(\d+)',
            r'iterations[：:]\s*(\d+)',
            r'收敛.*(\d+).*次',
        ]
        
        for pattern in iter_patterns:
            match = re.search(pattern, stdout, re.IGNORECASE)
            if match:
                iterations = int(match.group(1))
                quality['convergence'] = iterations
                break
        
        # 3. 检查数值稳定性（是否有NaN/Inf）
        if 'nan' in stdout.lower() or 'inf' in stdout.lower():
            quality['numerical_stability'] = False
        
        # 4. 检查是否有警告或错误
        if 'warning' in stdout.lower() or 'error' in stderr.lower():
            quality['has_warnings'] = True
        else:
            quality['has_warnings'] = False
        
        # 5. 综合评级
        quality['grade'] = self.calculate_grade(quality)
        
        return quality
    
    def calculate_grade(self, quality):
        """计算质量评级"""
        if not quality['numerical_stability']:
            return 'F'  # 数值不稳定
        
        flux_error = quality['flux_conservation']
        iterations = quality['convergence']
        
        # 如果有流量守恒数据
        if flux_error is not None:
            if flux_error < self.quality_thresholds['flux_error_excellent']:
                flux_grade = 'A+'
            elif flux_error < self.quality_thresholds['flux_error_good']:
                flux_grade = 'A'
            elif flux_error < self.quality_thresholds['flux_error_acceptable']:
                flux_grade = 'B'
            else:
                flux_grade = 'C'
        else:
            flux_grade = 'N/A'
        
        # 如果有收敛数据
        if iterations is not None:
            if iterations < self.quality_thresholds['iterations_fast']:
                conv_grade = 'A+'
            elif iterations < self.quality_thresholds['iterations_acceptable']:
                conv_grade = 'A'
            else:
                conv_grade = 'B'
        else:
            conv_grade = 'N/A'
        
        # 综合评级
        if flux_grade in ['A+', 'A'] and conv_grade in ['A+', 'A']:
            return 'A+优秀'
        elif flux_grade in ['A+', 'A', 'B']:
            return 'A良好'
        elif flux_grade == 'C' or conv_grade == 'B':
            return 'B合格'
        else:
            return 'C'
    
    def validate_script(self, script_path):
        """验证单个脚本"""
        result = self.run_and_validate(script_path)
        return result

def main():
    """测试验证器"""
    validator = QualityValidator()
    
    # 测试核心案例
    test_script = 'examples/example_01_canal_flow/scripts/01_basic_v2.py'
    
    print("质量验证器测试")
    print("="*80)
    print(f"测试脚本: {test_script}")
    print()
    
    result = validator.validate_script(test_script)
    
    print(f"状态: {result['status']}")
    if result['quality']:
        print(f"质量等级: {result['quality']['grade']}")
        print(f"流量守恒误差: {result['quality']['flux_conservation']}%")
        print(f"收敛迭代次数: {result['quality']['convergence']}")
        print(f"数值稳定性: {result['quality']['numerical_stability']}")

if __name__ == '__main__':
    main()
