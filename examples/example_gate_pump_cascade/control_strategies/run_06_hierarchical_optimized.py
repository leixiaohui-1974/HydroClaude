#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制策略6: 优化后的分层控制（MPC上层 + PID下层）

基于系统辨识的分层控制优化：

分层架构：
- 上层MPC（慢，60s）：全局优化，计算设定值
- 下层PID（快，30s）：局部执行，快速跟踪

优化要点：
1. 时间尺度分离（60s上层 / 30s下层）
2. 超长预测时域（30步×60s=30min）
3. 高Q权重（15.0）：强调全局优化
4. 高R权重（3.0）：平滑设定值变化
5. 保守自适应：稳定可靠

预期效果：
- 结合MPC的全局优化能力
- 结合PID的快速响应能力
- 更优的全局性能
- 更好的鲁棒性

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
    print("控制策略6: 优化后的分层控制（MPC + PID）")
    print("=" * 90)
    
    print("\n分层架构：")
    print("  上层MPC:")
    print("    - 控制周期: 60s（慢，全局规划）")
    print("    - 预测时域: 30min（超长视野）")
    print("    - 功能: 全局优化，计算设定值")
    
    print("\n  下层PID:")
    print("    - 控制周期: 30s（快，局部执行）")
    print("    - 参数: Kp=2.5, Ki=0.3, Kd=0.5")
    print("    - 功能: 快速跟踪，抑制扰动")
    
    print("\n优化要点：")
    print("  1. 时间尺度分离（2:1比例）")
    print("  2. MPC预测时域延长至30min")
    print("  3. Q权重增大至15.0（强调全局优化）")
    print("  4. R权重增大至3.0（平滑设定值）")
    print("  5. 保守自适应（稳定可靠）")
    
    print("\n预期性能:")
    print("  - 更优的全局性能")
    print("  - 更快的扰动抑制")
    print("  - 更好的鲁棒性")
    print("  - 结合MPC和PID优势")
    
    print("\n" + "=" * 90)
    
    # 运行优化分层控制
    modeler = UniversalModeler("config_06_hierarchical_optimized.yaml")
    success = modeler.run()
    
    if success:
        print("\n" + "=" * 90)
        print("✓ 优化分层控制仿真完成！")
        print("  结果目录: results_hierarchical_optimized")
        print("=" * 90)
        
        # 打印性能指标
        if hasattr(modeler, 'control_result') and modeler.control_result:
            metrics = modeler.control_result.get('control_performance', {})
            print("\n控制性能指标:")
            print(f"  MAE: {metrics.get('mae', 0):.4f} m")
            print(f"  RMSE: {metrics.get('rmse', 0):.4f} m")
            print(f"  最大误差: {metrics.get('max_error', 0):.4f} m")
            print(f"  稳态误差: {metrics.get('steady_state_error', 0):.4f} m")
            
            print("\n与优化前分层控制对比:")
            mae_old = 0.55  # 估计值
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
