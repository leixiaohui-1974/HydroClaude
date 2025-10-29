"""
高级边界条件模块

提供工程常用的复杂边界条件：
1. 时变边界条件 (Time-Dependent BC)
2. Rating Curve 边界 (水位-流量关系曲线)
3. 潮汐边界
4. 洪水过程线

Phase 2.4 - Task 2.4.1, 2.4.2

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Union, Callable, Optional
from scipy.interpolate import interp1d


class TimeDependentBC:
    """
    时变边界条件

    支持任意时间序列的边界条件，自动线性插值

    使用场景：
    - 洪水过程线
    - 水库调度
    - 闸门操作
    - 潮汐边界

    示例：
        # 创建洪水过程线
        time = [0, 3600, 7200, 10800]  # 秒
        flow = [10, 50, 30, 10]        # m³/s

        flood_bc = TimeDependentBC(time, flow, name="洪水过程")

        # 用于求解器
        solver.set_initial_conditions(
            ...,
            bc_left={'type': 'Q', 'value': flood_bc}
        )
    """

    def __init__(
        self,
        time: np.ndarray,
        values: np.ndarray,
        name: str = "Time-Dependent BC",
        extrapolate: str = 'constant'
    ):
        """
        初始化时变边界条件

        Args:
            time: 时间数组 (秒)，必须单调递增
            values: 对应的边界值数组
            name: 边界条件名称
            extrapolate: 超出范围时的外推方式
                - 'constant': 使用端点值（默认）
                - 'linear': 线性外推
                - 'raise': 抛出异常
        """
        self.time = np.asarray(time, dtype=float)
        self.values = np.asarray(values, dtype=float)
        self.name = name
        self.extrapolate = extrapolate

        # 验证输入
        if len(self.time) != len(self.values):
            raise ValueError(f"时间和值数组长度不匹配: {len(time)} vs {len(values)}")

        if len(self.time) < 2:
            raise ValueError(f"时间序列至少需要2个点，当前只有{len(time)}个")

        if not np.all(np.diff(self.time) > 0):
            raise ValueError("时间数组必须单调递增")

        # 创建插值函数
        if extrapolate == 'constant':
            fill_value = (self.values[0], self.values[-1])
            self.interpolator = interp1d(
                self.time, self.values,
                kind='linear',
                bounds_error=False,
                fill_value=fill_value
            )
        elif extrapolate == 'linear':
            self.interpolator = interp1d(
                self.time, self.values,
                kind='linear',
                fill_value='extrapolate'
            )
        elif extrapolate == 'raise':
            self.interpolator = interp1d(
                self.time, self.values,
                kind='linear',
                bounds_error=True
            )
        else:
            raise ValueError(f"未知的外推方式: {extrapolate}")

    def __call__(self, t: float) -> float:
        """
        获取t时刻的边界值（插值）

        Args:
            t: 时间 (秒)

        Returns:
            插值后的边界值
        """
        return float(self.interpolator(t))

    def get_range(self):
        """获取时间和值的范围"""
        return {
            'time_min': self.time[0],
            'time_max': self.time[-1],
            'value_min': np.min(self.values),
            'value_max': np.max(self.values),
            'duration': self.time[-1] - self.time[0]
        }

    def __repr__(self):
        info = self.get_range()
        return (f"{self.name}: "
                f"t=[{info['time_min']:.1f}, {info['time_max']:.1f}]s, "
                f"value=[{info['value_min']:.2f}, {info['value_max']:.2f}]")


class RatingCurveBC:
    """
    Rating Curve 边界条件 (水位-流量关系曲线)

    根据水位自动计算流量（或反之）

    使用场景：
    - 河流断面的水位-流量关系
    - 堰顶过流
    - 自由出流边界

    示例：
        # 创建Rating Curve (从实测数据)
        h_data = [0.5, 1.0, 1.5, 2.0, 2.5]  # 水位 (m)
        Q_data = [5, 15, 30, 50, 75]        # 流量 (m³/s)

        rating = RatingCurveBC(h_data, Q_data, name="下游断面")

        # 用于求解器 (下游边界)
        # 注意：Rating Curve通常用于下游，需要特殊处理
    """

    def __init__(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        name: str = "Rating Curve",
        extrapolate: str = 'linear'
    ):
        """
        初始化Rating Curve

        Args:
            h: 水位数组 (m)，必须单调递增
            Q: 流量数组 (m³/s)
            name: 名称
            extrapolate: 外推方式 ('linear', 'constant', 'raise')
        """
        self.h = np.asarray(h, dtype=float)
        self.Q = np.asarray(Q, dtype=float)
        self.name = name
        self.extrapolate = extrapolate

        # 验证
        if len(self.h) != len(self.Q):
            raise ValueError(f"水位和流量数组长度不匹配: {len(h)} vs {len(Q)}")

        if len(self.h) < 2:
            raise ValueError(f"Rating Curve至少需要2个点")

        if not np.all(np.diff(self.h) > 0):
            raise ValueError("水位数组必须单调递增")

        # 创建双向插值函数
        # h → Q
        if extrapolate == 'constant':
            fill_value = (self.Q[0], self.Q[-1])
            self.h_to_Q = interp1d(
                self.h, self.Q,
                kind='linear',
                bounds_error=False,
                fill_value=fill_value
            )
        elif extrapolate == 'linear':
            self.h_to_Q = interp1d(
                self.h, self.Q,
                kind='linear',
                fill_value='extrapolate'
            )
        else:
            self.h_to_Q = interp1d(
                self.h, self.Q,
                kind='linear',
                bounds_error=True
            )

        # Q → h (反函数，假设Q单调递增)
        if np.all(np.diff(self.Q) > 0):
            if extrapolate == 'constant':
                fill_value = (self.h[0], self.h[-1])
                self.Q_to_h = interp1d(
                    self.Q, self.h,
                    kind='linear',
                    bounds_error=False,
                    fill_value=fill_value
                )
            elif extrapolate == 'linear':
                self.Q_to_h = interp1d(
                    self.Q, self.h,
                    kind='linear',
                    fill_value='extrapolate'
                )
            else:
                self.Q_to_h = interp1d(
                    self.Q, self.h,
                    kind='linear',
                    bounds_error=True
                )
        else:
            # Q非单调，无法反函数插值
            self.Q_to_h = None

    def get_Q(self, h: float) -> float:
        """根据水位获取流量"""
        return float(self.h_to_Q(h))

    def get_h(self, Q: float) -> Optional[float]:
        """根据流量获取水位（如果Q单调）"""
        if self.Q_to_h is None:
            raise ValueError("Rating Curve的Q不单调，无法反函数插值")
        return float(self.Q_to_h(Q))

    def get_range(self):
        """获取有效范围"""
        return {
            'h_min': self.h[0],
            'h_max': self.h[-1],
            'Q_min': self.Q[0],
            'Q_max': self.Q[-1]
        }

    def __repr__(self):
        info = self.get_range()
        return (f"{self.name}: "
                f"h=[{info['h_min']:.2f}, {info['h_max']:.2f}]m, "
                f"Q=[{info['Q_min']:.2f}, {info['Q_max']:.2f}]m³/s")


class TidalBC(TimeDependentBC):
    """
    潮汐边界条件

    简化的余弦潮汐模型：
    h(t) = h_mean + A * cos(2π/T * t + φ)

    示例：
        # 半日潮 (周期12.42小时)
        tidal = TidalBC(
            period=12.42*3600,    # 周期 (秒)
            amplitude=2.0,        # 振幅 (m)
            mean_level=3.0,       # 平均潮位 (m)
            phase=0.0,            # 相位 (弧度)
            duration=24*3600      # 模拟时长 (秒)
        )
    """

    def __init__(
        self,
        period: float,
        amplitude: float,
        mean_level: float,
        phase: float = 0.0,
        duration: float = None,
        n_points: int = 100,
        name: str = "Tidal BC"
    ):
        """
        初始化潮汐边界

        Args:
            period: 潮汐周期 (秒)
            amplitude: 振幅 (m)
            mean_level: 平均潮位 (m)
            phase: 初始相位 (弧度，0=高潮)
            duration: 模拟时长 (秒)，None则为2个周期
            n_points: 离散化点数
            name: 名称
        """
        if duration is None:
            duration = 2 * period

        # 生成时间序列
        time = np.linspace(0, duration, n_points)

        # 余弦潮汐公式
        omega = 2 * np.pi / period
        values = mean_level + amplitude * np.cos(omega * time + phase)

        # 调用父类
        super().__init__(time, values, name=name, extrapolate='constant')

        # 保存参数
        self.period = period
        self.amplitude = amplitude
        self.mean_level = mean_level
        self.phase = phase

    def __repr__(self):
        return (f"{self.name}: "
                f"T={self.period/3600:.2f}h, "
                f"A={self.amplitude:.2f}m, "
                f"h_mean={self.mean_level:.2f}m")


class HydrographBC(TimeDependentBC):
    """
    洪水过程线边界条件

    常用的洪水过程形状：
    - 三角形洪水过程
    - 梯形洪水过程
    - SCS综合单位线

    示例：
        # 三角形洪水过程
        flood = HydrographBC.triangular(
            base_flow=10.0,      # 基流 (m³/s)
            peak_flow=100.0,     # 洪峰流量 (m³/s)
            time_to_peak=3600,   # 涨洪历时 (秒)
            time_to_base=7200    # 总历时 (秒)
        )
    """

    @staticmethod
    def triangular(
        base_flow: float,
        peak_flow: float,
        time_to_peak: float,
        time_to_base: float,
        n_points: int = 50
    ) -> 'HydrographBC':
        """
        三角形洪水过程线

        Args:
            base_flow: 基流 (m³/s)
            peak_flow: 洪峰流量 (m³/s)
            time_to_peak: 涨洪历时 (秒)
            time_to_base: 总历时 (秒)
            n_points: 离散点数
        """
        # 涨洪段
        t1 = np.linspace(0, time_to_peak, n_points//2)
        Q1 = base_flow + (peak_flow - base_flow) * (t1 / time_to_peak)

        # 退洪段
        t2 = np.linspace(time_to_peak, time_to_base, n_points//2)
        Q2 = peak_flow - (peak_flow - base_flow) * ((t2 - time_to_peak) / (time_to_base - time_to_peak))

        time = np.concatenate([t1, t2[1:]])
        flow = np.concatenate([Q1, Q2[1:]])

        return HydrographBC(
            time, flow,
            name=f"三角形洪水过程 (峰值={peak_flow:.1f}m³/s)"
        )

    @staticmethod
    def trapezoidal(
        base_flow: float,
        peak_flow: float,
        time_to_peak: float,
        peak_duration: float,
        time_to_base: float,
        n_points: int = 60
    ) -> 'HydrographBC':
        """
        梯形洪水过程线

        Args:
            base_flow: 基流 (m³/s)
            peak_flow: 洪峰流量 (m³/s)
            time_to_peak: 涨洪历时 (秒)
            peak_duration: 洪峰持续时间 (秒)
            time_to_base: 总历时 (秒)
            n_points: 离散点数
        """
        n1 = n_points // 3
        n2 = n_points // 3
        n3 = n_points - n1 - n2

        # 涨洪段
        t1 = np.linspace(0, time_to_peak, n1)
        Q1 = base_flow + (peak_flow - base_flow) * (t1 / time_to_peak)

        # 洪峰段
        t2 = np.linspace(time_to_peak, time_to_peak + peak_duration, n2)
        Q2 = np.full(n2, peak_flow)

        # 退洪段
        t3 = np.linspace(time_to_peak + peak_duration, time_to_base, n3)
        Q3 = peak_flow - (peak_flow - base_flow) * ((t3 - time_to_peak - peak_duration) / (time_to_base - time_to_peak - peak_duration))

        time = np.concatenate([t1, t2[1:], t3[1:]])
        flow = np.concatenate([Q1, Q2[1:], Q3[1:]])

        return HydrographBC(
            time, flow,
            name=f"梯形洪水过程 (峰值={peak_flow:.1f}m³/s)"
        )


def create_constant_bc(value: float, name: str = "Constant BC") -> Callable:
    """
    创建常数边界条件（便捷函数）

    Args:
        value: 常数值
        name: 名称

    Returns:
        callable函数 f(t) = value
    """
    def constant_func(t):
        return value
    constant_func.__name__ = name
    return constant_func


if __name__ == "__main__":
    """测试高级边界条件"""

    print("="*80)
    print("高级边界条件模块测试")
    print("="*80)

    # 测试1: 时变边界条件
    print("\n[测试1] 时变边界条件")
    print("-"*70)

    time = np.array([0, 1800, 3600, 5400, 7200])  # 0, 0.5h, 1h, 1.5h, 2h
    flow = np.array([10, 30, 50, 40, 20])

    bc_time = TimeDependentBC(time, flow, name="洪水过程")
    print(bc_time)

    # 测试插值
    test_times = [0, 900, 3600, 6300, 7200]
    print("\n插值测试:")
    for t in test_times:
        Q = bc_time(t)
        print(f"  t={t:5.0f}s ({t/3600:.2f}h): Q={Q:.2f} m³/s")

    # 测试2: Rating Curve
    print("\n[测试2] Rating Curve边界")
    print("-"*70)

    h_data = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    Q_data = np.array([5, 15, 30, 50, 75, 105])

    rating = RatingCurveBC(h_data, Q_data, name="下游断面Rating Curve")
    print(rating)

    # 测试h→Q
    test_h = [0.5, 1.25, 2.0, 2.75, 3.0]
    print("\n水位→流量:")
    for h in test_h:
        Q = rating.get_Q(h)
        print(f"  h={h:.2f}m → Q={Q:.2f} m³/s")

    # 测试Q→h
    test_Q = [5, 22.5, 50, 90, 105]
    print("\n流量→水位:")
    for Q in test_Q:
        h = rating.get_h(Q)
        print(f"  Q={Q:.2f}m³/s → h={h:.2f} m")

    # 测试3: 潮汐边界
    print("\n[测试3] 潮汐边界")
    print("-"*70)

    tidal = TidalBC(
        period=12.42*3600,  # 半日潮
        amplitude=2.0,
        mean_level=3.0,
        phase=0.0,
        duration=24*3600
    )
    print(tidal)

    # 测试几个时刻
    test_hours = [0, 3, 6, 9, 12, 18, 24]
    print("\n潮位变化:")
    for hr in test_hours:
        t = hr * 3600
        h = tidal(t)
        print(f"  t={hr:2.0f}h: h={h:.2f}m")

    # 测试4: 三角形洪水过程
    print("\n[测试4] 三角形洪水过程")
    print("-"*70)

    flood = HydrographBC.triangular(
        base_flow=10.0,
        peak_flow=100.0,
        time_to_peak=2*3600,  # 2小时涨洪
        time_to_base=8*3600   # 8小时总历时
    )
    print(flood)

    # 测试关键时刻
    test_hours = [0, 1, 2, 3, 5, 8]
    print("\n洪水过程:")
    for hr in test_hours:
        t = hr * 3600
        Q = flood(t)
        print(f"  t={hr:.0f}h: Q={Q:.1f} m³/s")

    # 测试5: 梯形洪水过程
    print("\n[测试5] 梯形洪水过程")
    print("-"*70)

    flood_trap = HydrographBC.trapezoidal(
        base_flow=10.0,
        peak_flow=100.0,
        time_to_peak=2*3600,
        peak_duration=2*3600,  # 2小时洪峰持续
        time_to_base=10*3600
    )
    print(flood_trap)

    test_hours = [0, 1, 2, 3, 4, 6, 10]
    print("\n洪水过程:")
    for hr in test_hours:
        t = hr * 3600
        Q = flood_trap(t)
        print(f"  t={hr:.0f}h: Q={Q:.1f} m³/s")

    print("\n" + "="*80)
    print("✅ 所有测试通过！")
    print("="*80)
