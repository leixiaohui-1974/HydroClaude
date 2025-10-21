import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control.pid_controller import PIDController

def test_pid_creation():
    pid = PIDController("test_pid", kp=1.0, ki=0.1, kd=0.01)
    assert pid.name == "test_pid"
    assert pid.kp == 1.0
    print("✓ PID creation test passed")

def test_pid_compute():
    pid = PIDController("test", kp=1.0, ki=0.0, kd=0.0)
    pid.set_target(10.0)
    
    control = pid.compute(8.0, 1.0)
    assert control > 0  # Should be positive to increase
    print("✓ PID compute test passed")

def test_pid_integral():
    pid = PIDController("test", kp=0.0, ki=1.0, kd=0.0)
    pid.set_target(10.0)
    
    # Run multiple steps
    for _ in range(5):
        pid.compute(8.0, 1.0)
    
    assert abs(pid.integral) > 0
    print("✓ PID integral test passed")

if __name__ == "__main__":
    test_pid_creation()
    test_pid_compute()
    test_pid_integral()
    print("\n所有控制器测试通过!")
