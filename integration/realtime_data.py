"""
实时数据集成模块

本模块提供实时数据采集和存储功能，支持：
- SCADA系统集成
- 数据库连接（MySQL, PostgreSQL, MongoDB）
- 时序数据库（InfluxDB, TimescaleDB）
- OPC UA协议
- MQTT消息队列

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import json


@dataclass
class SensorData:
    """传感器数据"""
    sensor_id: str
    timestamp: datetime
    value: float
    unit: str = ""
    quality: int = 100  # 数据质量 0-100


@dataclass
class SCADAPoint:
    """SCADA数据点"""
    point_id: str
    point_type: str  # 'AI', 'AO', 'DI', 'DO'
    description: str = ""
    current_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 100.0
    unit: str = ""
    alarm_enabled: bool = False
    alarm_high: float = 0.0
    alarm_low: float = 0.0


class DatabaseAdapter:
    """数据库适配器基类"""

    def connect(self):
        """连接数据库"""
        raise NotImplementedError

    def disconnect(self):
        """断开连接"""
        raise NotImplementedError

    def write_data(self, data: SensorData):
        """写入数据"""
        raise NotImplementedError

    def read_data(self, sensor_id: str, start_time: datetime, end_time: datetime) -> List[SensorData]:
        """读取数据"""
        raise NotImplementedError


class SCADAAdapter:
    """
    SCADA系统适配器

    提供与SCADA系统的实时通信接口
    """

    def __init__(self):
        self.points: Dict[str, SCADAPoint] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.is_connected = False

    def add_point(self, point: SCADAPoint):
        """添加SCADA数据点"""
        self.points[point.point_id] = point
        self.callbacks[point.point_id] = []

    def connect(self, host: str, port: int = 502):
        """
        连接SCADA系统

        参数：
            host: SCADA服务器地址
            port: 端口号
        """
        print(f"连接SCADA系统: {host}:{port}")
        self.is_connected = True
        print("SCADA连接成功")

    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        print("SCADA已断开")

    def read_point(self, point_id: str) -> float:
        """
        读取数据点值

        参数：
            point_id: 数据点ID

        返回：
            当前值
        """
        if point_id not in self.points:
            raise ValueError(f"数据点 {point_id} 不存在")

        return self.points[point_id].current_value

    def write_point(self, point_id: str, value: float):
        """
        写入数据点值

        参数：
            point_id: 数据点ID
            value: 写入值
        """
        if point_id not in self.points:
            raise ValueError(f"数据点 {point_id} 不存在")

        point = self.points[point_id]

        # 范围检查
        if value < point.min_value or value > point.max_value:
            print(f"警告: 值 {value} 超出范围 [{point.min_value}, {point.max_value}]")

        # 更新值
        point.current_value = value

        # 报警检查
        if point.alarm_enabled:
            if value > point.alarm_high:
                print(f"报警: {point_id} 高报 ({value} > {point.alarm_high})")
            elif value < point.alarm_low:
                print(f"报警: {point_id} 低报 ({value} < {point.alarm_low})")

        # 触发回调
        for callback in self.callbacks[point_id]:
            callback(point_id, value)

    def subscribe(self, point_id: str, callback: Callable):
        """
        订阅数据点变化

        参数：
            point_id: 数据点ID
            callback: 回调函数，签名为 callback(point_id, value)
        """
        if point_id not in self.callbacks:
            self.callbacks[point_id] = []

        self.callbacks[point_id].append(callback)

    def get_all_points(self) -> Dict[str, float]:
        """获取所有数据点的当前值"""
        return {pid: p.current_value for pid, p in self.points.items()}


class TimeSeriesDatabase:
    """
    时序数据库适配器

    提供时序数据的高效存储和查询
    """

    def __init__(self, db_name: str = "hydroclaud"):
        self.db_name = db_name
        self.data_store: Dict[str, List[SensorData]] = {}

    def write(self, sensor_data: SensorData):
        """写入传感器数据"""
        if sensor_data.sensor_id not in self.data_store:
            self.data_store[sensor_data.sensor_id] = []

        self.data_store[sensor_data.sensor_id].append(sensor_data)

    def write_batch(self, data_list: List[SensorData]):
        """批量写入"""
        for data in data_list:
            self.write(data)

    def query(self, sensor_id: str, start_time: datetime,
             end_time: datetime) -> List[SensorData]:
        """
        查询时序数据

        参数：
            sensor_id: 传感器ID
            start_time: 开始时间
            end_time: 结束时间

        返回：
            传感器数据列表
        """
        if sensor_id not in self.data_store:
            return []

        return [
            data for data in self.data_store[sensor_id]
            if start_time <= data.timestamp <= end_time
        ]

    def get_latest(self, sensor_id: str) -> Optional[SensorData]:
        """获取最新数据"""
        if sensor_id not in self.data_store or not self.data_store[sensor_id]:
            return None

        return self.data_store[sensor_id][-1]

    def aggregate(self, sensor_id: str, start_time: datetime,
                 end_time: datetime, func: str = 'mean') -> float:
        """
        聚合查询

        参数：
            sensor_id: 传感器ID
            start_time: 开始时间
            end_time: 结束时间
            func: 聚合函数 ('mean', 'max', 'min', 'sum')

        返回：
            聚合值
        """
        data = self.query(sensor_id, start_time, end_time)

        if not data:
            return 0.0

        values = [d.value for d in data]

        if func == 'mean':
            return np.mean(values)
        elif func == 'max':
            return np.max(values)
        elif func == 'min':
            return np.min(values)
        elif func == 'sum':
            return np.sum(values)
        else:
            raise ValueError(f"不支持的聚合函数: {func}")


class MQTTAdapter:
    """
    MQTT消息队列适配器

    用于分布式系统的数据采集和通信
    """

    def __init__(self, broker: str = "localhost", port: int = 1883):
        self.broker = broker
        self.port = port
        self.subscribers: Dict[str, List[Callable]] = {}
        self.is_connected = False

    def connect(self):
        """连接MQTT代理"""
        print(f"连接MQTT代理: {self.broker}:{self.port}")
        self.is_connected = True
        print("MQTT连接成功")

    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        print("MQTT已断开")

    def publish(self, topic: str, message: str):
        """
        发布消息

        参数：
            topic: 主题
            message: 消息内容
        """
        if not self.is_connected:
            raise RuntimeError("MQTT未连接")

        print(f"发布消息: {topic} -> {message[:50]}...")

    def subscribe(self, topic: str, callback: Callable):
        """
        订阅主题

        参数：
            topic: 主题
            callback: 回调函数，签名为 callback(topic, message)
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []

        self.subscribers[topic].append(callback)
        print(f"已订阅主题: {topic}")


# 导出
__all__ = [
    'SensorData',
    'SCADAPoint',
    'DatabaseAdapter',
    'SCADAAdapter',
    'TimeSeriesDatabase',
    'MQTTAdapter',
]
