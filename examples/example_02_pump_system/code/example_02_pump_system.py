import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from physics.tank import Tank
from physics.pump import Pump
from physics.pipe import Pipe
from simulation.plant_simulator import PlantSimulator

def run_example():
    print("\n" + "="*60)
    print("示例2: 泵站系统 (Pump System)")
    print("="*60)
    
    tank1 = Tank("水池1", 0, 1000, 100)
    pump = Pump("泵站1", max_flow=10, rated_head=50)
    pipe = Pipe("管道1", length=1000, diameter=0.5)
    tank2 = Tank("水池2", 0, 1000, 100)
    
    components = [tank1, pump, pipe, tank2]
    simulator = PlantSimulator(components, mode='reduced')
    
    dt = 10.0
    n_steps = 20
    
    print("\n运行泵站系统仿真...")
    for i in range(n_steps):
        control_inputs = {'泵站1': {'speed': 60.0}}
        states = simulator.step(dt, control_inputs)
        
        if i % 5 == 0:
            print(f"Step {i+1}/{n_steps}: Tank1 Level={states['水池1'].level:.2f}m, "
                  f"Tank2 Level={states['水池2'].level:.2f}m")
    
    print("\n泵站系统仿真完成!")

if __name__ == "__main__":
    run_example()
