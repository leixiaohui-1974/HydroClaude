#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制策略4: 优化后的PID控制

基于系统辨识和频域分析优化的PID参数：
- Kp: 0.8 → 2.5 (提高响应速度)
- Ki: 0.08 → 0.3 (消除稳态误差)
- Kd: 0.15 → 0.5 (减少超调)
- 控制周期: 10s → 30s (匹配系统时间常数)
- 监测点: 优化位置（远离闸门）

预期效果：
- MAE: 0.55m → <0.15m
- 稳态误差: 0.71m → <0.10m
- 扰动抑制能力显著提升

作者: Claude AI
日期: 2025-10-26
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from modeling.universal_modeler import UniversalModeler


def main():
    """主函数"""
    print("=" * 90)
    print("控制策略4: 优化后的PID控制（基于系统辨识）")
    print("=" * 90)
    
    print("\n优化要点：")
    print("  1. PID参数基于系统辨识和频域分析优化")
    print("  2. Kp增大3倍以提高响应速度")
    print("  3. Ki增大4倍以消除稳态误差")
    print("  4. Kd增大3倍以减少超调")
    print("  5. 控制周期从10s优化到30s")
    print("  6. 监测点位置优化")
    
    print("\n预期性能:")
    print("  - MAE: 0.55m → <0.15m (↓73%)")
    print("  - 稳态误差: 0.71m → <0.10m (↓86%)")
    print("  - 扰动抑制: 误差增36% → <15% (↓58%)")
    
    print("\n" + "=" * 90)
    
    # 运行优化控制
    modeler = UniversalModeler("../config_pid_optimized.yaml")
    success = modeler.run()
    
    if success:
        print("\n" + "=" * 90)
        print("✓ 优化控制仿真完成！")
        print("  结果目录: results_pid_optimized")
        print("=" * 90)
        
        # 打印性能指标
        if hasattr(modeler, 'control_result') and modeler.control_result:
            metrics = modeler.control_result.get('control_performance', {})
            print("\n控制性能指标:")
            print(f"  MAE: {metrics.get('mae', 0):.4f} m")
            print(f"  RMSE: {metrics.get('rmse', 0):.4f} m")
            print(f"  最大误差: {metrics.get('max_error', 0):.4f} m")
            print(f"  稳态误差: {metrics.get('steady_state_error', 0):.4f} m")
            
            print("\n与优化前对比:")
            mae_old = 0.5496
            mae_new = metrics.get('mae', mae_old)
            improvement = (mae_old - mae_new) / mae_old * 100 if mae_new < mae_old else 0
            print(f"  MAE改进: {improvement:.1f}%")
            
            if improvement > 50:
                print("  评价: ✅ 优化效果显著！")
            elif improvement > 20:
                print("  评价: ⚠️ 有一定改进")
            else:
                print("  评价: ⚠️ 改进有限，需进一步调整")
    
    return success


if __name__ == "__main__":
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    success = main()
    sys.exit(0 if success else 1)
