import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from physics.pipe import Pipe
from hardware.sensors import LevelSensor, FlowSensor
from disturbance.disturbance_generator import DisturbanceGenerator
import numpy as np

def run_example():
    print("\n" + "="*60)
    print("示例7: 故障测试")
    print("="*60)
    
    pipe = Pipe("管道1", length=1000, diameter=0.6, n_sections=21)
    
    level_sensor = LevelSensor("LS1", noise_std=0.05)
    flow_sensor = FlowSensor("FS1", noise_std=0.1)
    
    dt = 0.1
    n_steps = 100
    
    print("\n模拟传感器故障...")
    for i in range(n_steps):
        inputs = {'downstream_flow': 3.0 + 0.5*np.sin(i*0.1)}
        state = pipe.update_high_fidelity(dt, inputs)
        
        true_pressure = np.mean(pipe.hydraulic_state.P)
        measured_pressure = level_sensor.measure(true_pressure)
        
        true_flow = state.flow
        measured_flow = flow_sensor.measure(true_flow)
        
        if i % 25 == 0:
            print(f"Step {i}: 真实压力={true_pressure:.2f}m, "
                  f"测量压力={measured_pressure:.2f}m, "
                  f"误差={abs(true_pressure-measured_pressure):.3f}m")
    
    print("\n故障测试完成!")

if __name__ == "__main__":
    run_example()
