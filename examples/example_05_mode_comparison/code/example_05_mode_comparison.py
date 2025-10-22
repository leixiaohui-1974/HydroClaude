import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from physics.canal import Canal
from simulation.plant_simulator import PlantSimulator
import time

def run_example():
    print("\n" + "="*60)
    print("示例5: 仿真模式对比")
    print("="*60)
    
    canal = Canal("明渠1", 5000, 10000, 100, 5000, n_sections=51)
    
    # 高保真模式
    print("\n高保真模式...")
    simulator_hf = PlantSimulator([canal], mode='high_fidelity')
    t0 = time.time()
    for i in range(50):
        simulator_hf.step(10.0, {})
    t_hf = time.time() - t0
    
    # 降阶模式  
    print("降阶模式...")
    simulator_ro = PlantSimulator([canal], mode='reduced')
    t0 = time.time()
    for i in range(50):
        simulator_ro.step(10.0, {})
    t_ro = time.time() - t0
    
    print(f"\n高保真模式耗时: {t_hf:.3f}s")
    print(f"降阶模式耗时: {t_ro:.3f}s")
    print(f"加速比: {t_hf/t_ro:.2f}x")

if __name__ == "__main__":
    run_example()
