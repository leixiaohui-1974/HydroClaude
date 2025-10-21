class PIDController:
    """PID控制器"""
    def __init__(self, name: str, kp: float = 1.0, ki: float = 0.0, kd: float = 0.0):
        self.name = name
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.target = 0.0
        self.integral = 0.0
        self.last_error = 0.0
    
    def set_target(self, target: float):
        self.target = target
    
    def compute(self, measurement: float, dt: float) -> float:
        error = self.target - measurement
        
        self.integral += error * dt
        derivative = (error - self.last_error) / dt if dt > 0 else 0.0
        
        control = self.kp * error + self.ki * self.integral + self.kd * derivative
        
        self.last_error = error
        
        return control
    
    def reset(self):
        self.integral = 0.0
        self.last_error = 0.0
