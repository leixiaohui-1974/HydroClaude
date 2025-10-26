#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制策略5: 真正优化的MPC控制（修正版）

问题诊断：
之前的MPC配置过于保守，导致性能与PID完全相同

6大问题及修正：
1. ❌ 预测时域过长（900s） → ✅ 缩短至100s
2. ❌ 采样周期太长（30s） → ✅ 缩短至10s  
3. ❌ Q/R比太小（5） → ✅ 增大至83
4. ❌ 初始模型保守（B=0.002） → ✅ 增大至0.07
5. ❌ 自适应太慢（0.02） → ✅ 加快至0.15
6. ❌ 控制周期同PID（30s） → ✅ 加快至10s

真正的优化（方案C）：
- 预测时域：10步×10s=100s（短期精准）
- 控制周期：10s（高频率，比PID快3倍）
- Q/R比：83（强跟踪，允许激进控制）
- 快速自适应：0.15
- 准确模型：B增大35倍

预期效果：
- MAE: 0.42-0.44m（比PID↓15-20%）
- 稳态误差: 0.38-0.41m（比PID↓20-25%）
- 应该成为最佳策略！🏆

作者: Claude AI
日期: 2025-10-26
版本: v2.0 - 真正优化
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from modeling.universal_modeler import UniversalModeler


def main():
    """主函数"""
    print("=" * 90)
    print("控制策略5: 真正优化的MPC控制（修正版v2.0）")
    print("=" * 90)
    
    print("\n问题诊断：")
    print("  之前的MPC过于保守，性能与PID完全相同（MAE=0.52m）")
    
    print("\n6大问题：")
    print("  ❌ 1. 预测时域过长（900s）→ 过于保守")
    print("  ❌ 2. 采样周期太长（30s）→ 失去快速响应优势")
    print("  ❌ 3. Q/R比太小（5）→ 过度惩罚控制动作")
    print("  ❌ 4. 初始模型保守（B=0.002）→ 低估控制能力")
    print("  ❌ 5. 自适应太慢（0.02）→ 无法快速学习")
    print("  ❌ 6. 控制周期同PID（30s）→ 没发挥MPC优势")
    
    print("\n真正的优化（方案C - 短时域高频率）：")
    print("  ✅ 1. 预测时域: 900s → 100s（短期精准）")
    print("  ✅ 2. 控制周期: 30s → 10s（高频率，比PID快3倍）")
    print("  ✅ 3. Q/R比: 5 → 83（强调跟踪）")
    print("  ✅ 4. 初始模型: B=0.002 → 0.07（增大35倍）")
    print("  ✅ 5. 自适应率: 0.02 → 0.15（快速学习）")
    print("  ✅ 6. 采样周期: 30s → 10s（匹配控制周期）")
    
    print("\n核心改进：")
    print("  • 预测时域：10步×10s = 100秒（vs 原30步×30s=900秒）")
    print("  • 控制时域：8步（充分利用80%预测时域）")
    print("  • Q权重：25.0（强调跟踪，原5.0）")
    print("  • R权重：0.3（允许激进，原2.0）")
    print("  • Q/R比：83（比原来大17倍！）")
    
    print("\n预期性能:")
    print("  • MAE: 0.42-0.44m（比优化PID↓15-20%）")
    print("  • 稳态误差: 0.38-0.41m（比优化PID↓20-25%）")
    print("  • ISE: 7-8（比优化PID↓30-40%）")
    print("  • 应该显著优于所有其他策略 🏆")
    
    print("\n" + "=" * 90)
    print("开始运行真正优化的MPC控制...")
    print("=" * 90 + "\n")
    
    # 运行真正优化的MPC控制
    modeler = UniversalModeler("config_05_mpc_truly_optimized.yaml")
    success = modeler.run()
    
    if success:
        print("\n" + "=" * 90)
        print("✓ 真正优化的MPC控制仿真完成！")
        print("  结果目录: results_mpc_truly_optimized")
        print("=" * 90)
        
        # 打印性能指标
        if hasattr(modeler, 'control_result') and modeler.control_result:
            metrics = modeler.control_result.get('control_performance', {})
            mae = metrics.get('mae', 0)
            rmse = metrics.get('rmse', 0)
            max_err = metrics.get('max_error', 0)
            steady_err = metrics.get('steady_state_error', 0)
            ise = metrics.get('ise', 0)
            iae = metrics.get('iae', 0)
            
            print("\n控制性能指标:")
            print(f"  MAE: {mae:.4f} m")
            print(f"  RMSE: {rmse:.4f} m")
            print(f"  最大误差: {max_err:.4f} m")
            print(f"  稳态误差: {steady_err:.4f} m")
            print(f"  ISE: {ise:.4f}")
            print(f"  IAE: {iae:.4f}")
            
            print("\n与优化PID对比:")
            mae_pid = 0.5166
            steady_pid = 0.5094
            ise_pid = 10.6938
            iae_pid = 20.6632
            
            mae_improve = (mae_pid - mae) / mae_pid * 100 if mae < mae_pid else 0
            steady_improve = (steady_pid - steady_err) / steady_pid * 100 if steady_err < steady_pid else 0
            ise_improve = (ise_pid - ise) / ise_pid * 100 if ise < ise_pid else 0
            iae_improve = (iae_pid - iae) / iae_pid * 100 if iae < iae_pid else 0
            
            print(f"  MAE改进: {mae_improve:.1f}% ({mae_pid:.4f} → {mae:.4f})")
            print(f"  稳态误差改进: {steady_improve:.1f}% ({steady_pid:.4f} → {steady_err:.4f})")
            print(f"  ISE改进: {ise_improve:.1f}% ({ise_pid:.4f} → {ise:.4f})")
            print(f"  IAE改进: {iae_improve:.1f}% ({iae_pid:.4f} → {iae:.4f})")
            
            print("\n评价:")
            if mae_improve > 15 and steady_improve > 20:
                print("  ✅ 优化效果显著！MPC显著优于PID！")
                print("  🏆 MPC重夺第一！")
            elif mae_improve > 10:
                print("  ✅ 优化效果良好！MPC优于PID！")
            elif mae_improve > 5:
                print("  ⚠️ 有一定改进，但不够显著")
            else:
                print("  ⚠️ 改进有限，需进一步分析")
                
            print("\n与优化分层控制对比:")
            mae_hier = 0.5159
            steady_hier = 0.5040
            ise_hier = 5.3326
            
            if mae < mae_hier and steady_err < steady_hier:
                print(f"  🏆 MPC全面超越分层控制！")
                print(f"     MAE: {mae:.4f} < {mae_hier:.4f} ✅")
                print(f"     稳态误差: {steady_err:.4f} < {steady_hier:.4f} ✅")
                print(f"     ISE: {ise:.4f} vs {ise_hier:.4f}")
            elif mae < mae_hier or steady_err < steady_hier:
                print(f"  ⚠️ MPC部分指标优于分层控制")
            else:
                print(f"  ℹ️ 分层控制仍然更优")
    
    return success


if __name__ == "__main__":
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    success = main()
    sys.exit(0 if success else 1)
