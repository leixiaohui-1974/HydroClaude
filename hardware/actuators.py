"""执行器模型"""
import numpy as np

class Actuator:
    def __init__(self, name: str, rate_limit: float = None):
        self.name = name
        self.rate_limit = rate_limit
        self.current_value = 0.0

    def actuate(self, command: float, dt: float) -> float:
        if self.rate_limit:
            max_change = self.rate_limit * dt
            delta = np.clip(command - self.current_value, -max_change, max_change)
            self.current_value += delta
        else:
            self.current_value = command
        return self.current_value
