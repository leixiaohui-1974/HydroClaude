"""HydroClaude 集成层 — 对外暴露 HydroMind 标准协议适配器

本包将 HydroClaude 的高保真求解器包装为 hydromind-contracts 定义的标准接口，
使 HydroMind/HydroMind/HydroGuard 生态中的任何上层模块都能无缝调用。

可用适配器：
  HydroClaude1DSolverAdapter          水动力求解器（Preissmann）
  HydroClaude1DWaterQualityAdapter    水质仿真（River1DSystem）
  HydroClaude1DLeakDetectorAdapter    漏水/偷水检测（EKF，依赖 pipedream）
  HydroClaude1DPollutionSourceAdapter 污染溯源（BLP-EnKF，依赖 pipedream）
"""
from .hydromind_adapter import (
    HydroClaude1DSolverAdapter,
    HydroClaude1DWaterQualityAdapter,
    HydroClaude1DLeakDetectorAdapter,
    HydroClaude1DPollutionSourceAdapter,
)

__all__ = [
    "HydroClaude1DSolverAdapter",
    "HydroClaude1DWaterQualityAdapter",
    "HydroClaude1DLeakDetectorAdapter",
    "HydroClaude1DPollutionSourceAdapter",
]
