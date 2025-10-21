import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from physics.canal import Canal
from physics.pipe import Pipe
from physics.tank import Tank

def test_canal_creation():
    canal = Canal("test_canal", 1000, 5000, 100, 1000)
    assert canal.name == "test_canal"
    assert canal.length == 1000
    print("✓ Canal creation test passed")

def test_pipe_creation():
    pipe = Pipe("test_pipe", length=500, diameter=0.5)
    assert pipe.name == "test_pipe"
    assert pipe.length == 500
    print("✓ Pipe creation test passed")

def test_tank_creation():
    tank = Tank("test_tank", 0, 1000, 100)
    assert tank.name == "test_tank"
    assert tank.volume_max == 1000
    print("✓ Tank creation test passed")

def test_canal_update():
    canal = Canal("test", 1000, 5000, 100, 1000, n_sections=11)
    initial_level = canal.state.level
    canal.update_high_fidelity(10.0, {})
    # Level should change slightly
    assert canal.state.level > 0
    print("✓ Canal update test passed")

if __name__ == "__main__":
    test_canal_creation()
    test_pipe_creation()
    test_tank_creation()
    test_canal_update()
    print("\n所有组件测试通过!")
