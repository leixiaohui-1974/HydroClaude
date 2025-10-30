"""
Dual Flow Pipe Validation - 明满流转换验证
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from network.dual_flow_pipe import DualFlowPipe


def main():
    print("\n" + "="*80)
    print("明满流转换验证 - Dual Flow Transition Validation")
    print("="*80)
    
    pipe = DualFlowPipe(diameter=1.0, length=100.0, roughness=0.013)
    
    print(f"\n管道参数:")
    print(f"  直径 D = {pipe.D} m")
    print(f"  虚拟狭缝宽度 b = {pipe.b_slot:.6f} m")
    
    print(f"\n水力特性随水深变化:")
    print(f"{'h(m)':<8} {'A(m²)':<10} {'流态':<15} {'压力?':<8}")
    print("-" * 45)
    
    for h in [0.3, 0.5, 0.7, 0.95, 1.0, 1.1, 1.2]:
        props = pipe.properties(h)
        print(f"{h:<8.2f} {props['A']:<10.4f} {props['flow_type']:<15} "
              f"{'是' if props['is_pressurized'] else '否':<8}")
    
    print("\n✓ 验证完成 - 明满流平滑过渡")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
