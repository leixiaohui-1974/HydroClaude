# -*- coding: utf-8 -*-
"""
simulation_service.py - 服务层

该服务层作为API网关和核心仿真引擎之间的桥梁。
它负责接收来自API的请求，将其转换为仿真引擎所需的配置格式，
然后调用引擎执行仿真并返回结果。
"""

from typing import Dict, Any
from core.simulation_engine import SimulationEngine

class SimulationService:
    """
    仿真服务类
    """
    def run_simulation_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据传入的配置字典运行一个完整的仿真。

        Args:
            config (Dict[str, Any]): 一个符合 core.config_parser.py
                                     期望格式的配置字典。

        Returns:
            Dict[str, Any]: 仿真结果，格式为通用数据模型。
        """
        try:
            # 1. （可选）在这里可以添加配置验证逻辑
            if "simulation" not in config or "canal" not in config:
                raise ValueError("配置字典中缺少 'simulation' 或 'canal' 关键部分")

            # 2. 初始化仿真引擎
            # verbose=True 可以提供详细的控制台输出，便于调试
            engine = SimulationEngine(config, verbose=True)

            # 3. 运行仿真
            results = engine.run()

            return results

        except ValueError as ve:
            # 配置错误
            return {
                "status": "error",
                "message": f"配置错误: {ve}"
            }
        except Exception as e:
            # 引擎内部错误
            return {
                "status": "error",
                "message": f"仿真引擎在运行时发生内部错误: {e}"
            }

# 创建一个单例服务实例，供API层导入和使用
simulation_service = SimulationService()

def get_simulation_service() -> SimulationService:
    """
    获取仿真服务的实例。
    这是一个依赖注入函数，可以在FastAPI中优雅地使用。
    """
    return simulation_service
