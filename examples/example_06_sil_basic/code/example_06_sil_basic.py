import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.canal import Canal
from physics.gate import Gate
from simulation.plant_simulator import PlantSimulator
from simulation.twin_simulator import TwinSimulator
from control.pid_controller import PIDController

def run_example():
    print("\n" + "="*60)
    print("示例6: SIL基础测试")
    print("="*60)
    
    canal = Canal("明渠1", 5000, 10000, 100, 5000)
    gate = Gate("闸门1", max_opening=1.0)
    
    plant = PlantSimulator([canal, gate], mode='high_fidelity')
    twin = TwinSimulator([canal, gate], mode='reduced')
    
    controller = PIDController("PID1", kp=0.5, ki=0.1, kd=0.05)
    controller.set_target(5.5)
    
    dt = 10.0
    n_steps = 30
    
    print("\n运行SIL仿真...")
    for i in range(n_steps):
        plant_states = plant.step(dt, {})
        twin_states = twin.step(dt, {})
        
        level_plant = plant_states['明渠1'].level
        level_twin = twin_states['明渠1'].level
        
        control = controller.compute(level_plant, dt)
        
        if i % 10 == 0:
            print(f"Step {i}: Plant={level_plant:.2f}m, Twin={level_twin:.2f}m, "
                  f"Error={abs(level_plant-level_twin):.3f}m")
    
    print("\nSIL基础测试完成!")

if __name__ == "__main__":
    run_example()
