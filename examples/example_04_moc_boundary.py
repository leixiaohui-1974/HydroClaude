import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from physics.pipe import Pipe

def run_example():
    print("\n" + "="*60)
    print("示例4: MOC边界条件测试")
    print("="*60)
    
    pipe = Pipe("管道1", length=2000, diameter=0.8, wave_speed=1000, n_sections=41)
    
    print("\n测试阀门快速关闭...")
    dt = 0.05
    n_steps = 100
    
    for i in range(n_steps):
        if i < 20:
            inputs = {'downstream_flow': 5.0}
        else:
            inputs = {'downstream_flow': 0.0}  # 快速关闭
        
        state = pipe.update_high_fidelity(dt, inputs)
        
        if i % 20 == 0:
            print(f"  t={i*dt:.2f}s: 最大压力={np.max(pipe.hydraulic_state.P):.2f}m")
    
    print(f"\n最终最大压力: {np.max(pipe.hydraulic_state.P):.2f}m")
    print("MOC边界条件测试完成!")

if __name__ == "__main__":
    run_example()
