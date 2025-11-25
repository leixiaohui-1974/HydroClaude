# -*- coding: utf-8 -*-
"""
Simulation Service
负责处理仿真请求，协调HydraulicEngineV2进行计算
"""
import sys
import os
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(os.path.dirname(backend_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web.backend.core.hydraulic_engine_v2 import HydraulicEngineV2
from web.backend.services.result_store import result_store

class SimulationService:
    def __init__(self):
        self.engine = HydraulicEngineV2()
        # self._results_store = {}  # Replaced by persistent store

    def get_simulation_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取仿真结果"""
        return result_store.get(task_id)

    def run_simulation_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据配置运行仿真
        
        Args:
            config: 完整的仿真配置字典
            
        Returns:
            Dict: 仿真结果字典
        """
        try:
            # 1. 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 2. 解析配置并转换为引擎需要的格式
            engine_config = self._convert_to_engine_config(config)
            
            # 3. 根据结构类型选择合适的仿真方法
            structures = config.get("structures", [])
            result = None
            
            if not structures:
                # 纯明渠仿真
                result = self.engine.run_canal_simulation(task_id, engine_config)
            else:
                # 包含结构的仿真
                structure_type = structures[0].get("type")
                
                if structure_type == "pump":
                    if "canal" in config:
                        result = self.engine.run_canal_with_pump(task_id, engine_config)
                    else:
                        result = self.engine.run_pump_simulation(task_id, engine_config)
                        
                elif structure_type in ["gate", "sluice_gate", "radial_gate"]:
                    if "canal" in config:
                        result = self.engine.run_canal_with_gate(task_id, engine_config)
                    else:
                        result = self.engine.run_gate_simulation(task_id, engine_config)
                        
                elif structure_type in ["weir", "broad_crested_weir", "sharp_crested_weir"]:
                     if "canal" in config:
                        # 尝试调用可能存在的weir方法，如果不存在则回退
                        if hasattr(self.engine, "run_canal_with_weir"):
                            result = self.engine.run_canal_with_weir(task_id, engine_config)
                        else:
                            result = self.engine.run_canal_simulation(task_id, engine_config)
                     else:
                        if hasattr(self.engine, "run_weir_simulation"):
                            result = self.engine.run_weir_simulation(task_id, engine_config)
                        else:
                             raise ValueError(f"Unsupported structure type for standalone simulation: {structure_type}")
                else:
                    # 默认尝试明渠仿真
                    result = self.engine.run_canal_simulation(task_id, engine_config)

            # 4. 转换结果为字典并存储
            if result:
                result_dict = self._convert_result_to_dict(result)
                result_store.save(task_id, result_dict)
                return result_dict
            else:
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": "No result generated"
                }

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return {
                "task_id": task_id if 'task_id' in locals() else str(uuid.uuid4()),
                "status": "failed",
                "error": str(e),
                "message": str(e)
            }

    def _convert_to_engine_config(self, api_config: Dict[str, Any]) -> Dict[str, Any]:
        """将API配置转换为引擎配置"""
        engine_config = {}
        
        # 1. 提取明渠参数
        if "canal" in api_config:
            canal = api_config["canal"]
            engine_config.update({
                "width": canal.get("width", 10.0),
                "length": canal.get("length", 1000.0),
                "slope": canal.get("slope", 0.001),
                "manning_n": canal.get("manning_n", 0.015),
                "n_cells": canal.get("grid", {}).get("nx", 101),
                "t_end": api_config.get("simulation", {}).get("time", {}).get("end", 3600),
                "dt_max": api_config.get("simulation", {}).get("time", {}).get("dt", 1.0),
                "output_interval": api_config.get("simulation", {}).get("time", {}).get("output_interval", 60)
            })

        # 2. 提取结构参数
        if "structures" in api_config and api_config["structures"]:
            structure = api_config["structures"][0]
            st_type = structure.get("type")
            st_params = structure.get("parameters", {})
            st_pos = structure.get("position", 500.0)
            
            if st_type == "pump":
                engine_config["pump"] = {
                    "position": st_pos,
                    "flow_rate": st_params.get("flow_rate", 10.0),
                    "head": st_params.get("head", 10.0),
                    "name": st_params.get("name", "Pump-01"),
                    "num_pumps": st_params.get("num_pumps", 1),
                    "pump_type": st_params.get("pump_type", "single")
                }
            elif st_type in ["gate", "sluice_gate", "radial_gate"]:
                engine_config["gate"] = {
                    "position": st_pos,
                    "type": "radial" if "radial" in st_type else "sluice",
                    "width": st_params.get("width", 5.0),
                    "opening": st_params.get("opening", 1.0),
                    "discharge_coeff": st_params.get("discharge_coeff", 0.6),
                    "name": st_params.get("name", "Gate-01")
                }
            elif st_type in ["weir", "broad_crested_weir", "sharp_crested_weir"]:
                engine_config["weir"] = {
                    "position": st_pos,
                    "type": st_type,
                    "crest_height": st_params.get("crest_height", 1.0),
                    "discharge_coeff": st_params.get("discharge_coeff", 0.6),
                    "width": st_params.get("width", 10.0)
                }

        # 3. 提取初始条件
        if "initial_conditions" in api_config:
            ic = api_config["initial_conditions"]
            engine_config["initial_conditions"] = {
                "type": "uniform" if ic.get("depth") == "uniform_flow" else "custom",
                "h": ic.get("h_initial", 5.0),
                "Q": ic.get("Q_initial", 0.0)
            }

        # 4. 提取边界条件
        if "boundary_conditions" in api_config:
            bc = api_config["boundary_conditions"]
            engine_config["boundary_conditions"] = bc

        return engine_config

    def _convert_result_to_dict(self, result) -> Dict[str, Any]:
        """将SimulationResult对象转换为字典"""
        return {
            "task_id": result.task_id,
            "status": result.status,
            "time": result.time,
            "x": result.x,
            "h": result.h,
            "Q": result.Q,
            "V": result.V,
            "metrics": result.metrics,
            "duration": result.duration,
            "timestamp": result.timestamp,
            "error": result.error
        }

# 单例实例
simulation_service = SimulationService()
