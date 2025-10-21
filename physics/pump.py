from core.base import HydraulicComponent
from core.states import ComponentState

class Pump(HydraulicComponent):
    """泵站"""
    def __init__(self, name: str, max_flow: float = 100.0, rated_head: float = 50.0):
        super().__init__(name, "pump")
        self.max_flow = max_flow
        self.rated_head = rated_head
        
        self.state = ComponentState()
        self.state.flow = 0.0
        self.state.head = 0.0
    
    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        return self.update_reduced_order(dt, inputs)
    
    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        speed = inputs.get('speed', 0.0)  # 0-100%
        
        self.state.flow = self.max_flow * speed / 100.0
        self.state.head = self.rated_head * (speed / 100.0) ** 2
        self.state.pressure = self.state.head
        
        return self.state
    
    def get_constraints(self):
        return {
            'max_flow': self.max_flow,
            'rated_head': self.rated_head,
            'min_speed': 0.0,
            'max_speed': 100.0
        }
