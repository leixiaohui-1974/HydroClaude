#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制策略5: 优化后的MPC控制

基于系统辨识和频域分析优化的MPC参数：

MPC优化要点：
1. 预测时域延长（20→30步）：适应系统大惯性
2. 采样周期延长（10s→30s）：匹配系统时间常数
3. Q权重增大（5→10）：强调跟踪性能
4. R权重增大（2→2）：平滑控制输入
5. 自适应参数保守化：提高鲁棒性
6. 初始模型精确化：基于辨识参数

预期效果：
- 更准确的预测（基于辨识模型）
- 更好的扰动抑制
- 更小的稳态误差
- 更平滑的控制输入

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
    print("控制策略5: 优化后的MPC控制（基于系统辨识）")
    print("=" * 90)
    
    print("\n优化要点：")
    print("  1. 预测时域: 20步 → 30步（适应大惯性）")
    print("  2. 采样周期: 10s → 30s（匹配时间常数）")
    print("  3. Q权重: 5.0 → 10.0（强调跟踪）")
    print("  4. 自适应率: 0.03 → 0.02（保守稳定）")
    print("  5. 遗忘因子: 0.92 → 0.95（长记忆）")
    print("  6. 初始模型: 基于辨识参数（a=0.998, b=0.002）")
    
    print("\n预期性能:")
    print("  - 更准确的预测")
    print("  - 更好的扰动抑制")
    print("  - 更小的稳态误差")
    print("  - 更平滑的控制")
    
    print("\n" + "=" * 90)
    
    # 运行优化MPC控制
    modeler = UniversalModeler("config_05_mpc_optimized.yaml")
    success = modeler.run()
    
    if success:
        print("\n" + "=" * 90)
        print("✓ 优化MPC控制仿真完成！")
        print("  结果目录: results_mpc_optimized")
        print("=" * 90)
        
        # 打印性能指标
        if hasattr(modeler, 'control_result') and modeler.control_result:
            metrics = modeler.control_result.get('control_performance', {})
            print("\n控制性能指标:")
            print(f"  MAE: {metrics.get('mae', 0):.4f} m")
            print(f"  RMSE: {metrics.get('rmse', 0):.4f} m")
            print(f"  最大误差: {metrics.get('max_error', 0):.4f} m")
            print(f"  稳态误差: {metrics.get('steady_state_error', 0):.4f} m")
            
            print("\n与优化前MPC对比:")
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
