from physics.canal import Canal
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from simulation.plant_simulator import PlantSimulator
import numpy as np

def run_example():
    """Runs a simple canal simulation example."""
    # 1. Create components
    canal1 = Canal(
        name="canal1",
        volume_min=5000,
        volume_max=10000,
        area=100,
        length=5000,
        slope=0.0001,
        n_sections=11
    )

    components = [canal1]

    # 2. Initialize simulator
    simulator = PlantSimulator(components, mode='high_fidelity')

    # 3. Run simulation
    dt = 10.0  # Time step in seconds
    n_steps = 10

    print("\nStarting simple canal simulation...")
    for i in range(n_steps):
        # No control inputs for this simple example
        control_inputs = {}

        # Simulator step
        states = simulator.step(dt, control_inputs)

        # Print state
        level = states['canal1'].level
        flow = states['canal1'].flow
        print(f"Step {i+1}/{n_steps}: Level={level:.2f}m, Flow={flow:.2f}m³/s")

    print("\nSimple canal simulation finished.")

if __name__ == "__main__":
    run_example()
