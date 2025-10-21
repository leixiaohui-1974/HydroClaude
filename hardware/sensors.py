"""传感器模型"""
import numpy as np

class Sensor:
    def __init__(self, name: str, noise_std: float = 0.0):
        self.name = name
        self.noise_std = noise_std

    def measure(self, true_value: float) -> float:
        noise = np.random.normal(0, self.noise_std)
        return true_value + noise

class LevelSensor(Sensor):
    def __init__(self, name: str, noise_std: float = 0.01):
        super().__init__(name, noise_std)

class FlowSensor(Sensor):
    def __init__(self, name: str, noise_std: float = 0.05):
        super().__init__(name, noise_std)
