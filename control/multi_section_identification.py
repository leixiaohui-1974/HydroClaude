"""
多断面河渠IDZ参数辨识模块

解决实际工程问题：长距离河渠有多个不规则断面，如何辨识IDZ参数？

提供4种策略：
1. 等效断面法 - 将多个断面等效为单一代表性断面
2. 断面聚类法 - 将相似断面分组，每组一个IDZ模型
3. 分段模型法 - 河道分段，每段用代表性断面
4. 数据驱动法 - 直接从输入输出数据反演等效参数

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import sys
import os

# 简化KMeans实现（避免sklearn依赖）
class SimpleKMeans:
    """简化的KMeans聚类"""
    def __init__(self, n_clusters=3, random_state=42):
        self.n_clusters = n_clusters
        self.random_state = random_state

    def fit_predict(self, X):
        np.random.seed(self.random_state)
        n_samples = X.shape[0]

        # 随机初始化中心
        indices = np.random.choice(n_samples, self.n_clusters, replace=False)
        centers = X[indices]

        # 迭代10次
        for _ in range(10):
            # 分配
            distances = np.array([[np.linalg.norm(x - c) for c in centers] for x in X])
            labels = np.argmin(distances, axis=1)

            # 更新中心
            for i in range(self.n_clusters):
                if np.any(labels == i):
                    centers[i] = X[labels == i].mean(axis=0)

        return labels

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from cross_section import CrossSection, SectionGeometry
    from idz_model import IDZParameters
    from online_identification import RecursiveLeastSquares
except ImportError:
    from physics.cross_section import CrossSection, SectionGeometry
    from control.idz_model import IDZParameters
    from control.online_identification import RecursiveLeastSquares


@dataclass
class SectionLocation:
    """断面位置信息"""
    station: float          # 桩号/里程 (m)
    section: CrossSection   # 断面对象
    weight: float = 1.0     # 权重（用于加权平均）


class EquivalentSectionMethod:
    """
    等效断面法

    将多个不规则断面等效为单一代表性断面，用于IDZ参数计算

    方法：
    1. 计算各断面在正常水深下的几何参数
    2. 根据距离权重计算等效参数
    3. 估算等效 dA/dh
    """

    def __init__(self, section_locations: List[SectionLocation],
                 normal_depth: float):
        """
        Args:
            section_locations: 断面位置列表（按桩号排序）
            normal_depth: 设计正常水深 (m)
        """
        self.section_locations = sorted(section_locations, key=lambda x: x.station)
        self.normal_depth = normal_depth

        # 计算总长度
        self.total_length = (self.section_locations[-1].station -
                            self.section_locations[0].station)

    def compute_equivalent_geometry(self, depth: float) -> Dict[str, float]:
        """
        计算等效断面几何参数

        使用距离加权平均

        Args:
            depth: 水深 (m)

        Returns:
            等效几何参数字典
        """
        total_weight = 0.0
        weighted_area = 0.0
        weighted_perimeter = 0.0
        weighted_width = 0.0
        weighted_hydraulic_radius = 0.0

        for loc in self.section_locations:
            geom = loc.section.compute_geometry(depth)

            # 权重：可以是断面代表的河段长度
            weight = loc.weight
            total_weight += weight

            weighted_area += geom.area * weight
            weighted_perimeter += geom.perimeter * weight
            weighted_width += geom.width * weight
            weighted_hydraulic_radius += geom.hydraulic_radius * weight

        # 加权平均
        equiv_area = weighted_area / total_weight
        equiv_perimeter = weighted_perimeter / total_weight
        equiv_width = weighted_width / total_weight
        equiv_hydraulic_radius = weighted_hydraulic_radius / total_weight

        return {
            'area': equiv_area,
            'perimeter': equiv_perimeter,
            'width': equiv_width,
            'hydraulic_radius': equiv_hydraulic_radius,
            'hydraulic_depth': equiv_area / equiv_width if equiv_width > 0 else 0
        }

    def compute_equivalent_dA_dh(self, depth: float, delta_h: float = 0.01) -> float:
        """
        计算等效 dA/dh（数值微分）

        Args:
            depth: 水深 (m)
            delta_h: 微分步长 (m)

        Returns:
            等效 dA/dh (m²/m)
        """
        geom_plus = self.compute_equivalent_geometry(depth + delta_h)
        geom_minus = self.compute_equivalent_geometry(depth - delta_h)

        dA_dh = (geom_plus['area'] - geom_minus['area']) / (2 * delta_h)

        return dA_dh

    def compute_idz_parameters(self,
                               normal_flow: float,
                               manning_n: float,
                               bed_slope: float) -> IDZParameters:
        """
        基于等效断面计算IDZ参数

        Args:
            normal_flow: 正常流量 (m³/s)
            manning_n: 曼宁系数
            bed_slope: 底坡

        Returns:
            IDZ参数
        """
        # 等效几何
        geom = self.compute_equivalent_geometry(self.normal_depth)

        # 流速
        velocity = normal_flow / geom['area'] if geom['area'] > 0 else 0

        # 弗劳德数
        froude = velocity / np.sqrt(9.81 * geom['hydraulic_depth']) if geom['hydraulic_depth'] > 0 else 0

        # 波速
        wave_celerity = velocity + np.sqrt(9.81 * geom['hydraulic_depth'])

        # 等效 dA/dh
        dA_dh = self.compute_equivalent_dA_dh(self.normal_depth)

        # IDZ参数
        K = self.total_length / (dA_dh * velocity) if (dA_dh > 0 and velocity > 0) else \
            self.total_length / geom['area']

        tau_z = self.total_length / (velocity * (1 + froude**2)) if velocity > 0 else 1000.0
        tau_d = self.total_length / (velocity * np.sqrt(1 + froude**2)) if velocity > 0 else 1000.0
        theta = self.total_length / wave_celerity if wave_celerity > 0 else 100.0

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta)


class SectionClusteringMethod:
    """
    断面聚类法

    将多个断面按几何相似性聚类，每类用一个代表性断面
    减少模型数量
    """

    def __init__(self, section_locations: List[SectionLocation],
                 normal_depth: float,
                 n_clusters: int = 3):
        """
        Args:
            section_locations: 断面位置列表
            normal_depth: 正常水深 (m)
            n_clusters: 聚类数量
        """
        self.section_locations = section_locations
        self.normal_depth = normal_depth
        self.n_clusters = n_clusters

        # 执行聚类
        self.clusters = self._cluster_sections()

    def _cluster_sections(self) -> List[List[SectionLocation]]:
        """
        基于断面几何特征聚类

        特征：面积、湿周、宽度、水力半径 @ 正常水深
        """
        # 提取特征
        features = []
        for loc in self.section_locations:
            geom = loc.section.compute_geometry(self.normal_depth)
            # 归一化特征
            features.append([
                geom.area,
                geom.perimeter,
                geom.width,
                geom.hydraulic_radius
            ])

        features = np.array(features)

        # 标准化
        features_normalized = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-6)

        # KMeans聚类
        kmeans = SimpleKMeans(n_clusters=min(self.n_clusters, len(self.section_locations)),
                             random_state=42)
        labels = kmeans.fit_predict(features_normalized)

        # 分组
        clusters = [[] for _ in range(self.n_clusters)]
        for i, loc in enumerate(self.section_locations):
            clusters[labels[i]].append(loc)

        return [c for c in clusters if c]  # 移除空簇

    def get_representative_sections(self) -> List[Tuple[float, float, SectionLocation]]:
        """
        获取各簇的代表性断面

        Returns:
            [(起始桩号, 结束桩号, 代表性断面)]
        """
        representatives = []

        for cluster in self.clusters:
            if not cluster:
                continue

            # 簇的范围
            start_station = min(loc.station for loc in cluster)
            end_station = max(loc.station for loc in cluster)

            # 选择中间断面作为代表
            mid_idx = len(cluster) // 2
            representative = sorted(cluster, key=lambda x: x.station)[mid_idx]

            representatives.append((start_station, end_station, representative))

        return representatives


class SegmentedModelMethod:
    """
    分段模型法

    将长河道分成多个河段，每段用一个IDZ模型
    适合断面沿程变化较大的情况
    """

    def __init__(self, section_locations: List[SectionLocation],
                 segment_length: float = 5000.0):
        """
        Args:
            section_locations: 断面位置列表
            segment_length: 目标分段长度 (m)
        """
        self.section_locations = sorted(section_locations, key=lambda x: x.station)
        self.segment_length = segment_length

        # 分段
        self.segments = self._create_segments()

    def _create_segments(self) -> List[List[SectionLocation]]:
        """创建分段"""
        if not self.section_locations:
            return []

        segments = []
        current_segment = []
        segment_start = self.section_locations[0].station

        for loc in self.section_locations:
            if loc.station - segment_start <= self.segment_length:
                current_segment.append(loc)
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = [loc]
                segment_start = loc.station

        if current_segment:
            segments.append(current_segment)

        return segments

    def compute_segment_idz_parameters(self,
                                      normal_depth: float,
                                      normal_flow: float,
                                      manning_n: float,
                                      bed_slope: float) -> List[IDZParameters]:
        """
        计算各段IDZ参数

        Args:
            normal_depth: 正常水深 (m)
            normal_flow: 正常流量 (m³/s)
            manning_n: 曼宁系数
            bed_slope: 底坡

        Returns:
            各段IDZ参数列表
        """
        idz_params_list = []

        for segment in self.segments:
            # 使用等效断面法计算该段参数
            equiv_method = EquivalentSectionMethod(segment, normal_depth)
            params = equiv_method.compute_idz_parameters(normal_flow, manning_n, bed_slope)
            idz_params_list.append(params)

        return idz_params_list


class DataDrivenIdentification:
    """
    数据驱动辨识法

    不依赖详细断面几何，直接从输入输出数据辨识等效IDZ参数

    适用于：
    1. 断面数据不完整
    2. 断面形状复杂难以建模
    3. 有充足的实测数据
    """

    def __init__(self, dt: float = 60.0):
        """
        Args:
            dt: 采样时间 (s)
        """
        self.dt = dt

        # 辨识离散模型参数
        # y(k) = a1*y(k-1) + a2*y(k-2) + b1*u(k-1) + b2*u(k-2)
        self.rls = RecursiveLeastSquares(n_params=4)

        # 数据缓冲
        self.y_buffer = []
        self.u_buffer = []

    def update(self, u: float, y: float) -> Optional[Dict[str, float]]:
        """
        更新在线辨识

        Args:
            u: 输入（流量）
            y: 输出（水位）

        Returns:
            等效参数（如果收敛）
        """
        self.u_buffer.append(u)
        self.y_buffer.append(y)

        if len(self.y_buffer) < 5:
            return None

        k = len(self.y_buffer) - 1

        # 构建回归向量
        phi = np.array([
            self.y_buffer[k-1] if k >= 1 else 0,
            self.y_buffer[k-2] if k >= 2 else 0,
            self.u_buffer[k-1] if k >= 1 else 0,
            self.u_buffer[k-2] if k >= 2 else 0,
        ])

        y_k = self.y_buffer[k]

        # RLS更新
        theta, error = self.rls.update(phi, y_k)

        # 保持缓冲大小
        if len(self.y_buffer) > 1000:
            self.y_buffer.pop(0)
            self.u_buffer.pop(0)

        # 转换为等效参数
        equiv_params = self._discrete_to_equivalent(theta)

        return equiv_params

    def _discrete_to_equivalent(self, theta: np.ndarray) -> Dict[str, float]:
        """
        从离散参数转换为等效水力参数

        Args:
            theta: [a1, a2, b1, b2]

        Returns:
            等效参数字典
        """
        a1, a2, b1, b2 = theta

        # 等效增益
        K_equiv = (b1 + b2) / (1 - a1 - a2) if abs(1 - a1 - a2) > 1e-6 else 100.0

        # 等效时间常数
        tau_equiv = -self.dt / np.log(abs(a1)) if 0 < abs(a1) < 1 else 100.0 * self.dt

        # 限制范围
        K_equiv = np.clip(K_equiv, 1.0, 1000.0)
        tau_equiv = np.clip(tau_equiv, self.dt, 10000.0)

        return {
            'K_equivalent': K_equiv,
            'tau_equivalent': tau_equiv,
            'discrete_params': theta
        }


if __name__ == "__main__":
    """测试多断面辨识"""

    from physics.cross_section import RectangularSection, TrapezoidalSection, CompoundSection

    print("=" * 80)
    print("多断面河渠IDZ参数辨识测试")
    print("=" * 80)

    # 模拟一条10km河道，有10个测量断面
    print("\n[场景] 10km河道，10个不规则断面")
    print("-" * 80)

    # 创建10个不同断面（沿程变化）
    sections = []

    # 上游段：梯形断面（0-3km）
    for i in range(3):
        station = i * 1000
        section = TrapezoidalSection(
            f"Trap_{i}",
            bottom_width=8.0 + i * 0.5,
            side_slope=1.5 + i * 0.1
        )
        sections.append(SectionLocation(station, section, weight=1000.0))

    # 中游段：复式断面（3-7km）
    for i in range(3, 7):
        station = i * 1000
        section = CompoundSection(
            f"Compound_{i}",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.0,
            flood_width_left=15.0 + (i-3) * 2,
            flood_width_right=15.0 + (i-3) * 2
        )
        sections.append(SectionLocation(station, section, weight=1000.0))

    # 下游段：梯形断面（7-10km）
    for i in range(7, 10):
        station = i * 1000
        section = TrapezoidalSection(
            f"Trap_{i}",
            bottom_width=12.0 + (i-7) * 0.5,
            side_slope=2.0
        )
        sections.append(SectionLocation(station, section, weight=1000.0))

    print(f"断面数量: {len(sections)}")
    print(f"河道总长: {sections[-1].station - sections[0].station:.0f}m")

    # 设计参数
    normal_depth = 2.5
    normal_flow = 25.0
    manning_n = 0.025
    bed_slope = 0.0001

    print(f"\n设计参数:")
    print(f"  正常水深: {normal_depth}m")
    print(f"  正常流量: {normal_flow}m³/s")
    print(f"  曼宁系数: {manning_n}")
    print(f"  底坡: {bed_slope}")

    # 方法1：等效断面法
    print("\n[方法1] 等效断面法")
    print("-" * 80)

    equiv_method = EquivalentSectionMethod(sections, normal_depth)

    print(f"等效几何参数（h={normal_depth}m）:")
    equiv_geom = equiv_method.compute_equivalent_geometry(normal_depth)
    for key, value in equiv_geom.items():
        print(f"  {key}: {value:.3f}")

    equiv_dA_dh = equiv_method.compute_equivalent_dA_dh(normal_depth)
    print(f"  等效 dA/dh: {equiv_dA_dh:.3f} m²/m")

    idz_equiv = equiv_method.compute_idz_parameters(normal_flow, manning_n, bed_slope)
    print(f"\nIDZ参数（等效断面法）:")
    print(f"  K = {idz_equiv.K:.2f} m/(m³/s)")
    print(f"  τ_z = {idz_equiv.tau_z:.1f} s")
    print(f"  τ_d = {idz_equiv.tau_d:.1f} s")
    print(f"  θ = {idz_equiv.theta:.1f} s")

    # 方法2：断面聚类法
    print("\n[方法2] 断面聚类法（3类）")
    print("-" * 80)

    cluster_method = SectionClusteringMethod(sections, normal_depth, n_clusters=3)

    print(f"聚类结果:")
    representatives = cluster_method.get_representative_sections()
    for i, (start, end, rep) in enumerate(representatives):
        print(f"  簇{i+1}: 桩号{start:.0f}m - {end:.0f}m, "
              f"代表断面: {rep.section.name}")

        # 计算该簇的IDZ参数
        cluster_sections = cluster_method.clusters[i]
        cluster_equiv = EquivalentSectionMethod(cluster_sections, normal_depth)
        cluster_idz = cluster_equiv.compute_idz_parameters(normal_flow, manning_n, bed_slope)

        print(f"    K={cluster_idz.K:.2f}, τ_z={cluster_idz.tau_z:.1f}s, "
              f"τ_d={cluster_idz.tau_d:.1f}s, θ={cluster_idz.theta:.1f}s")

    # 方法3：分段模型法
    print("\n[方法3] 分段模型法（每段~3km）")
    print("-" * 80)

    segment_method = SegmentedModelMethod(sections, segment_length=3000.0)

    print(f"分段数: {len(segment_method.segments)}")

    segment_idz_list = segment_method.compute_segment_idz_parameters(
        normal_depth, normal_flow, manning_n, bed_slope
    )

    for i, (segment, idz) in enumerate(zip(segment_method.segments, segment_idz_list)):
        start_station = segment[0].station
        end_station = segment[-1].station
        print(f"  段{i+1}: {start_station:.0f}m - {end_station:.0f}m")
        print(f"    断面数: {len(segment)}")
        print(f"    K={idz.K:.2f}, τ_z={idz.tau_z:.1f}s, "
              f"τ_d={idz.tau_d:.1f}s, θ={idz.theta:.1f}s")

    # 方法4：数据驱动法（模拟）
    print("\n[方法4] 数据驱动辨识法")
    print("-" * 80)

    data_driven = DataDrivenIdentification(dt=60.0)

    print("模拟数据驱动辨识（100步）...")

    # 模拟数据：使用等效IDZ模型生成
    np.random.seed(42)
    for k in range(100):
        # 模拟输入（随机流量）
        u = normal_flow + np.random.randn() * 2.0

        # 模拟输出（简化：y ≈ K*u 带延迟）
        if k > 5:
            y = idz_equiv.K * data_driven.u_buffer[k-3] / 1000.0 + np.random.randn() * 0.05
        else:
            y = normal_depth + np.random.randn() * 0.05

        # 在线辨识
        result = data_driven.update(u, y)

        if result and k % 25 == 0:
            print(f"  步骤{k}: K_equiv={result['K_equivalent']:.2f}, "
                  f"τ_equiv={result['tau_equivalent']:.1f}s")

    print(f"\n最终辨识结果:")
    final_result = data_driven.update(normal_flow, normal_depth)
    if final_result:
        print(f"  等效增益: {final_result['K_equivalent']:.2f}")
        print(f"  等效时间常数: {final_result['tau_equivalent']:.1f}s")
        print(f"  离散参数: {final_result['discrete_params']}")

    # 对比分析
    print("\n" + "=" * 80)
    print("方法对比总结")
    print("=" * 80)

    print(f"\n{'方法':<20} {'K(m/(m³/s))':<15} {'τ_d(s)':<12} {'复杂度':<15} {'适用场景'}")
    print("-" * 80)
    print(f"{'等效断面法':<20} {idz_equiv.K:<15.2f} {idz_equiv.tau_d:<12.1f} "
          f"{'低':<15} 断面数据完整")

    avg_K_cluster = np.mean([idz.K for idz in
                            [cluster_equiv.compute_idz_parameters(normal_flow, manning_n, bed_slope)
                             for cluster_equiv in [EquivalentSectionMethod(cluster, normal_depth)
                                                  for cluster in cluster_method.clusters]]])
    print(f"{'断面聚类法':<20} {avg_K_cluster:<15.2f} {'变化':<12} "
          f"{'中':<15} 断面沿程有分段特征")

    avg_K_segment = np.mean([idz.K for idz in segment_idz_list])
    print(f"{'分段模型法':<20} {avg_K_segment:<15.2f} {'变化':<12} "
          f"{'中':<15} 长河道断面变化大")

    if final_result:
        print(f"{'数据驱动法':<20} {final_result['K_equivalent']:<15.2f} "
              f"{final_result['tau_equivalent']:<12.1f} "
              f"{'最低':<15} 断面数据不完整")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)

    print("\n建议:")
    print("1. 断面数据完整且变化不大 → 等效断面法（最简单）")
    print("2. 断面有明显分段特征 → 断面聚类法或分段模型法")
    print("3. 断面数据不完整但有实测数据 → 数据驱动法")
    print("4. 高精度要求 → 分段模型法（每段单独IDZ）")
