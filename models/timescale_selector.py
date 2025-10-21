"""
时间尺度自适应选择器
根据仿真时间尺度自动选择合适的降阶模型
"""
import numpy as np
from enum import Enum
from typing import Dict, Any, Optional
from models.idz_model import CanalIDZModel
from models.water_balance_model import CanalWaterBalanceModel
from models.transfer_function_model import CanalTransferFunctionModel

class TimeScale(Enum):
    """时间尺度枚举"""
    SECOND = "second"        # 秒级：1-60秒
    MINUTE = "minute"        # 分钟级：1-60分钟
    HOUR = "hour"            # 小时级：1-24小时
    DAY = "day"              # 天级：>24小时

class ModelType(Enum):
    """模型类型枚举"""
    HIGH_FIDELITY = "high_fidelity"  # 高保真（MOC, Preissmann, FVM）
    TRANSFER_FUNCTION = "transfer_function"  # 传递函数模型
    IDZ = "idz"  # IDZ模型
    WATER_BALANCE = "water_balance"  # 水量平衡模型

class TimeScaleSelector:
    """
    时间尺度自适应选择器

    根据时间步长自动选择最合适的仿真模型：
    - dt < 60s: 高保真模型 (MOC, Preissmann, FVM)
    - 60s <= dt < 600s (10min): 传递函数模型
    - 600s <= dt < 3600s (1h): IDZ模型
    - dt >= 3600s: 水量平衡模型
    """

    # 时间尺度阈值（秒）
    THRESHOLDS = {
        TimeScale.SECOND: (0, 60),
        TimeScale.MINUTE: (60, 600),
        TimeScale.HOUR: (600, 3600),
        TimeScale.DAY: (3600, float('inf'))
    }

    # 时间尺度对应的推荐模型
    RECOMMENDED_MODELS = {
        TimeScale.SECOND: ModelType.HIGH_FIDELITY,
        TimeScale.MINUTE: ModelType.TRANSFER_FUNCTION,
        TimeScale.HOUR: ModelType.IDZ,
        TimeScale.DAY: ModelType.WATER_BALANCE
    }

    @staticmethod
    def determine_timescale(dt: float) -> TimeScale:
        """
        确定时间尺度

        Args:
            dt: 时间步长 (s)

        Returns:
            时间尺度
        """
        for scale, (min_dt, max_dt) in TimeScaleSelector.THRESHOLDS.items():
            if min_dt <= dt < max_dt:
                return scale
        return TimeScale.DAY

    @staticmethod
    def recommend_model(dt: float, force_model: Optional[ModelType] = None) -> ModelType:
        """
        推荐模型类型

        Args:
            dt: 时间步长 (s)
            force_model: 强制使用的模型类型（可选）

        Returns:
            推荐的模型类型
        """
        if force_model is not None:
            return force_model

        scale = TimeScaleSelector.determine_timescale(dt)
        return TimeScaleSelector.RECOMMENDED_MODELS[scale]

    @staticmethod
    def validate_model_timestep(model_type: ModelType, dt: float) -> tuple[bool, str]:
        """
        验证模型和时间步长的兼容性

        Args:
            model_type: 模型类型
            dt: 时间步长 (s)

        Returns:
            (is_valid, warning_message)
        """
        scale = TimeScaleSelector.determine_timescale(dt)
        recommended = TimeScaleSelector.RECOMMENDED_MODELS[scale]

        if model_type == recommended:
            return True, ""

        warnings = {
            (ModelType.HIGH_FIDELITY, TimeScale.HOUR): "警告: 高保真模型在大时间步长下可能不稳定",
            (ModelType.HIGH_FIDELITY, TimeScale.DAY): "错误: 高保真模型不适用于天级时间步长",
            (ModelType.WATER_BALANCE, TimeScale.SECOND): "警告: 水量平衡模型在小时间步长下精度不足",
            (ModelType.IDZ, TimeScale.SECOND): "警告: IDZ模型在秒级时间步长下精度可能不足"
        }

        key = (model_type, scale)
        if key in warnings:
            is_critical = "错误" in warnings[key]
            return not is_critical, warnings[key]

        return True, f"注意: {model_type.value}模型用于{scale.value}级时间步长"

class AdaptiveCanalModel:
    """自适应明渠模型 - 根据时间步长自动选择合适的模型"""

    def __init__(self, length: float, width: float, slope: float,
                 manning_n: float, nominal_depth: float):
        """
        Args:
            length: 渠道长度 (m)
            width: 渠道宽度 (m)
            slope: 坡度
            manning_n: Manning系数
            nominal_depth: 标称水深 (m)
        """
        self.length = length
        self.width = width
        self.slope = slope
        self.manning_n = manning_n
        self.nominal_depth = nominal_depth

        # 当前使用的模型
        self.current_model = None
        self.current_model_type = None
        self.current_dt = None

        # 高保真模型实例（延迟创建）
        self.high_fidelity_model = None

    def _create_model(self, model_type: ModelType, dt: float) -> Any:
        """创建指定类型的模型"""
        if model_type == ModelType.WATER_BALANCE:
            return CanalWaterBalanceModel(
                length=self.length,
                width=self.width,
                initial_depth=self.nominal_depth
            )

        elif model_type == ModelType.IDZ:
            return CanalIDZModel(
                length=self.length,
                width=self.width,
                slope=self.slope,
                manning_n=self.manning_n,
                nominal_depth=self.nominal_depth,
                dt=dt
            )

        elif model_type == ModelType.TRANSFER_FUNCTION:
            return CanalTransferFunctionModel(
                length=self.length,
                width=self.width,
                slope=self.slope,
                manning_n=self.manning_n,
                nominal_depth=self.nominal_depth,
                dt=dt,
                model_type='second_order'  # 默认使用二阶模型
            )

        elif model_type == ModelType.HIGH_FIDELITY:
            # 这里返回None，实际使用时需要从physics模块创建
            # 由于循环依赖，这里只是占位
            from physics.canal import Canal
            return Canal(
                name="adaptive_canal",
                volume_min=self.length * self.width * 0.1,
                volume_max=self.length * self.width * 10.0,
                area=self.length * self.width,
                length=self.length,
                slope=self.slope,
                n_sections=51
            )

        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def update(self, dt: float, upstream_flow: float, downstream_flow: float,
               force_model: Optional[ModelType] = None) -> Dict[str, float]:
        """
        更新模型 - 自动选择合适的模型

        Args:
            dt: 时间步长 (s)
            upstream_flow: 上游流量 (m³/s)
            downstream_flow: 下游流量 (m³/s)
            force_model: 强制使用的模型类型（可选）

        Returns:
            状态字典
        """
        # 确定应使用的模型类型
        recommended_model = TimeScaleSelector.recommend_model(dt, force_model)

        # 检查是否需要切换模型
        if (self.current_model is None or
            self.current_model_type != recommended_model or
            abs(dt - (self.current_dt or 0)) > 1e-6):

            # 验证模型和时间步长
            is_valid, warning = TimeScaleSelector.validate_model_timestep(recommended_model, dt)
            if warning:
                print(f"[TimeScaleSelector] {warning}")

            # 创建新模型
            self.current_model = self._create_model(recommended_model, dt)
            self.current_model_type = recommended_model
            self.current_dt = dt

        # 更新模型
        if self.current_model_type == ModelType.HIGH_FIDELITY:
            # 高保真模型使用不同的接口
            inputs = {
                'upstream_flow': upstream_flow,
                'downstream_flow': downstream_flow
            }
            state = self.current_model.update_high_fidelity(dt, inputs)
            return {
                'depth': state.level,
                'level': state.level,
                'flow': state.flow,
                'volume': state.volume,
                'model_type': self.current_model_type.value
            }
        else:
            # 降阶模型使用统一接口
            result = self.current_model.update(dt, upstream_flow, downstream_flow)
            result['model_type'] = self.current_model_type.value
            return result

    def get_current_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        return {
            'model_type': self.current_model_type.value if self.current_model_type else None,
            'time_step': self.current_dt,
            'time_scale': TimeScaleSelector.determine_timescale(self.current_dt).value if self.current_dt else None
        }
