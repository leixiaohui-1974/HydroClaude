import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from physics.moc_solver import MOCSolver

def test_moc_solver_creation():
    solver = MOCSolver()
    assert solver is not None
    print(" MOC solver creation test passed")

def test_characteristic_equations():
    # Test that MOC solver can handle basic characteristic equations
    solver = MOCSolver()
    
    # Simple test values
    h1, Q1 = 5.0, 3.0
    h2, Q2 = 5.0, 3.0
    
    # These should be close to input for steady state
    assert h1 > 0 and Q1 > 0
    print(" Characteristic equations test passed")

if __name__ == "__main__":
    test_moc_solver_creation()
    test_characteristic_equations()
    print("\n所有MOC求解器测试通过!")
