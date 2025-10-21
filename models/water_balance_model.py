"""
水量平衡模型
适用于长时间步长（小时/天级）的粗粒度仿真
基于质量守恒原则
"""
import numpy as np
from typing import Dict, Optional

class WaterBalanceModel:
    """
    水量平衡模型：dV/dt = Q_in - Q_out

    适用场景：
    - 水库/水池长期运行模拟
    - 大时间尺度优化
    - 水资源调度
    """

    def __init__(self, area: float, volume_min: float = 0.0,
                 volume_max: float = float('inf'),
                 initial_volume: Optional[float] = None):
        """
        Args:
            area: 水面面积 (m²)，用于计算水位
            volume_min: 最小库容 (m³)
            volume_max: 最大库容 (m³)
            initial_volume: 初始库容 (m³)
        """
        self.area = area
        self.volume_min = volume_min
        self.volume_max = volume_max

        if initial_volume is None:
            self.volume = (volume_min + volume_max) / 2
        else:
            self.volume = initial_volume

        # 统计量
        self.total_inflow = 0.0
        self.total_outflow = 0.0
        self.overflow_count = 0
        self.shortage_count = 0

    def update(self, dt: float, inflow: float, outflow: float,
               precipitation: float = 0.0, evaporation: float = 0.0) -> Dict[str, float]:
        """
        更新水量平衡

        Args:
            dt: 时间步长 (s)
            inflow: 入流流量 (m³/s)
            outflow: 出流流量 (m³/s)
            precipitation: 降雨强度 (mm/h)
            evaporation: 蒸发强度 (mm/h)

        Returns:
            状态字典
        """
        # 降雨和蒸发体积（转换单位）
        precip_volume = precipitation * self.area / 1000 / 3600 * dt  # mm/h -> m³
        evap_volume = evaporation * self.area / 1000 / 3600 * dt

        # 体积变化
        dV = (inflow - outflow) * dt + precip_volume - evap_volume

        # 更新库容
        new_volume = self.volume + dV

        # 处理溢出和短缺
        overflow = 0.0
        shortage = 0.0

        if new_volume > self.volume_max:
            overflow = new_volume - self.volume_max
            new_volume = self.volume_max
            self.overflow_count += 1

        elif new_volume < self.volume_min:
            shortage = self.volume_min - new_volume
            new_volume = self.volume_min
            self.shortage_count += 1

        self.volume = new_volume

        # 计算水位
        level = self.volume / self.area

        # 更新统计量
        self.total_inflow += inflow * dt
        self.total_outflow += outflow * dt

        return {
            'volume': self.volume,
            'level': level,
            'inflow': inflow,
            'outflow': outflow,
            'overflow': overflow,
            'shortage': shortage,
            'storage_ratio': (self.volume - self.volume_min) / (self.volume_max - self.volume_min)
        }

    def get_level(self) -> float:
        """获取当前水位"""
        return self.volume / self.area

    def get_storage_ratio(self) -> float:
        """获取库容比（0-1）"""
        if self.volume_max == self.volume_min:
            return 0.0
        return (self.volume - self.volume_min) / (self.volume_max - self.volume_min)

    def reset(self, initial_volume: Optional[float] = None):
        """重置模型"""
        if initial_volume is None:
            self.volume = (self.volume_min + self.volume_max) / 2
        else:
            self.volume = initial_volume

        self.total_inflow = 0.0
        self.total_outflow = 0.0
        self.overflow_count = 0
        self.shortage_count = 0


class CanalWaterBalanceModel:
    """明渠水量平衡模型"""

    def __init__(self, length: float, width: float,
                 min_depth: float = 0.1, max_depth: float = 10.0,
                 initial_depth: Optional[float] = None):
        """
        Args:
            length: 渠道长度 (m)
            width: 渠道宽度 (m)
            min_depth: 最小水深 (m)
            max_depth: 最大水深 (m)
            initial_depth: 初始水深 (m)
        """
        self.length = length
        self.width = width
        self.min_depth = min_depth
        self.max_depth = max_depth

        # 体积范围
        area = length * width
        volume_min = area * min_depth
        volume_max = area * max_depth
        initial_volume = area * (initial_depth if initial_depth else (min_depth + max_depth) / 2)

        # 创建水量平衡模型
        self.wb_model = WaterBalanceModel(
            area=area,
            volume_min=volume_min,
            volume_max=volume_max,
            initial_volume=initial_volume
        )

        # 当前流量（用于输出）
        self.current_flow = 0.0

    def update(self, dt: float, upstream_flow: float, downstream_flow: float) -> Dict[str, float]:
        """
        更新明渠状态

        Args:
            dt: 时间步长 (s)
            upstream_flow: 上游流量 (m³/s)
            downstream_flow: 下游流量 (m³/s)

        Returns:
            状态字典
        """
        result = self.wb_model.update(dt, upstream_flow, downstream_flow)

        # 更新流量（简化：取上下游平均）
        self.current_flow = (upstream_flow + downstream_flow) / 2

        result['flow'] = self.current_flow
        result['depth'] = result['level']  # 对于矩形渠道，depth = level

        return result

    def get_depth(self) -> float:
        """获取当前水深"""
        return self.wb_model.get_level()

    def reset(self):
        """重置模型"""
        self.wb_model.reset()
        self.current_flow = 0.0
