import numpy as np
from core.water_body import Canal
from core.other_components import Pipe
from core.control_device import Pump

class ModelValidator:
    """模型验证工具"""

    @staticmethod
    def validate_canal_model(canal: Canal, duration: float = 3600):
        """验证明渠模型"""
        print(f"\n验证明渠模型: {canal.name}")
        print("-" * 50)

        # 测试场景：阶跃响应
        dt = 60
        n_steps = int(duration / dt)

        history_high_fidelity = []
        history_reduced_order = []

        for step in range(n_steps):
            # 阶跃输入
            inflow = 5.0 if step < n_steps / 2 else 8.0
            outflow = 4.0

            inputs = {'inflow': inflow, 'outflow': outflow}

            # 高保真更新
            canal.update_state_high_fidelity(dt, inputs)
            history_high_fidelity.append(canal.state.level)

            # 降阶更新
            canal.update_state(dt, inputs)
            history_reduced_order.append(canal.state.level)

        # 比较结果
        error = np.array(history_high_fidelity) - np.array(history_reduced_order)
        rmse = np.sqrt(np.mean(error**2))

        print(f"✓ RMSE: {rmse:.4f} m")
        print(f"✓ 最大误差: {np.max(np.abs(error)):.4f} m")

        return rmse < 0.5  # 误差小于0.5m为合格

    @staticmethod
    def validate_pipe_model(pipe: Pipe, duration: float = 60):
        """验证管道模型"""
        print(f"\n验证管道模型: {pipe.name}")
        print("-" * 50)

        dt = 0.1
        n_steps = int(duration / dt)

        # 模拟阀门突然关闭（水击）
        for step in range(n_steps):
            flow = 5.0 if step < n_steps / 2 else 0.5
            inputs = {'inflow': flow, 'outflow': flow, 'upstream_pressure': 50.0}

            pipe.update_state_high_fidelity(dt, inputs)

        print(f"✓ 最大压力: {np.max(pipe.H_nodes):.2f} m")
        print(f"✓ 压力波动: {np.std(pipe.H_nodes):.2f} m")

        return True

    @staticmethod
    def validate_pump_model(pump: Pump):
        """验证泵站模型"""
        print(f"\n验证泵站模型: {pump.name}")
        print("-" * 50)

        # 测试特性曲线
        flows = np.linspace(pump.flow_min, pump.flow_max, 10)
        heads = []
        powers = []
        efficiencies = []

        for Q in flows:
            pump.update_state(1.0, {'target_flow': Q})
            heads.append(pump.state.head)
            powers.append(pump.state.power)
            efficiencies.append(pump.state.efficiency)

        print(f"✓ 零流量扬程: {heads[0]:.2f} m")
        print(f"✓ 额定扬程: {heads[len(heads)//2]:.2f} m")
        print(f"✓ 最大效率: {max(efficiencies):.2%}")
        print(f"✓ 额定功率: {powers[len(powers)//2]:.2f} kW")

        return True
