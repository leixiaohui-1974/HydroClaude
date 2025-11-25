"""
多断面辨识模块单元测试

测试覆盖：
- SimpleKMeans聚类
- 等效断面法
- 断面聚类法
- 分段模型法
- 数据驱动辨识法

作者：HydroClaude Team
日期：2025-10-24
"""

import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from control.multi_section_identification import (
    SimpleKMeans,
    SectionLocation,
    EquivalentSectionMethod,
    SectionClusteringMethod,
    SegmentedModelMethod,
    DataDrivenIdentification
)
from physics.cross_section import TrapezoidalSection, RectangularSection


class TestSimpleKMeans(unittest.TestCase):
    """简单KMeans聚类测试"""

    def test_single_cluster(self):
        """测试单聚类"""
        X = np.array([[1, 2], [1.5, 1.8], [1.2, 2.1]])
        kmeans = SimpleKMeans(n_clusters=1)
        labels = kmeans.fit_predict(X)

        # 所有点应该属于同一类
        self.assertEqual(len(set(labels)), 1)
        self.assertEqual(len(labels), 3)

    def test_two_clusters(self):
        """测试两聚类"""
        # 两个明显分离的簇
        X = np.array([
            [0, 0], [0.1, 0.1], [0.2, 0],    # 簇1
            [10, 10], [10.1, 10], [10, 10.2]  # 簇2
        ])

        kmeans = SimpleKMeans(n_clusters=2)
        labels = kmeans.fit_predict(X)

        # 应该有两个簇
        self.assertEqual(len(set(labels)), 2)
        self.assertEqual(len(labels), 6)

        # 前3个点应该属于同一簇
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[1], labels[2])

        # 后3个点应该属于同一簇
        self.assertEqual(labels[3], labels[4])
        self.assertEqual(labels[4], labels[5])

        # 两簇标签应该不同
        self.assertNotEqual(labels[0], labels[3])


class TestEquivalentSectionMethod(unittest.TestCase):
    """等效断面法测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建3个不同的梯形断面
        self.sections = [
            TrapezoidalSection("S1", bottom_width=8.0, side_slope=1.5),
            TrapezoidalSection("S2", bottom_width=10.0, side_slope=1.5),
            TrapezoidalSection("S3", bottom_width=12.0, side_slope=1.5)
        ]

        self.locations = [
            SectionLocation(section=self.sections[0], station=0.0),
            SectionLocation(section=self.sections[1], station=1000.0),
            SectionLocation(section=self.sections[2], station=2000.0)
        ]

        self.normal_depth = 2.5
        self.method = EquivalentSectionMethod(self.locations, self.normal_depth)

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(len(self.method.section_locations), 3)
        self.assertEqual(self.method.normal_depth, self.normal_depth)

    def test_equivalent_geometry(self):
        """测试等效几何参数"""
        depth = 2.0
        equiv_geom = self.method.compute_equivalent_geometry(depth)

        # 应该返回字典
        self.assertIsInstance(equiv_geom, dict)
        self.assertIn('area', equiv_geom)
        self.assertIn('width', equiv_geom)

        # 等效面积应该在最小和最大断面之间
        area1 = self.sections[0].compute_geometry(depth).area
        area3 = self.sections[2].compute_geometry(depth).area

        self.assertGreater(equiv_geom['area'], area1)
        self.assertLess(equiv_geom['area'], area3)

    def test_equivalent_dA_dh(self):
        """测试等效面积微分"""
        depth = 2.0
        dA_dh = self.method.compute_equivalent_dA_dh(depth)

        # dA/dh应该为正
        self.assertGreater(dA_dh, 0)

        # 应该在合理范围（对于底宽8-12m的梯形断面）
        self.assertGreater(dA_dh, 8.0)
        self.assertLess(dA_dh, 20.0)

    def test_idz_parameters_calculation(self):
        """测试IDZ参数计算"""
        normal_flow = 25.0
        manning = 0.025
        bed_slope = 0.0001

        params = self.method.compute_idz_parameters(
            normal_flow=normal_flow,
            manning_n=manning,
            bed_slope=bed_slope
        )

        # 应该返回IDZParameters对象
        from control.idz_model import IDZParameters
        self.assertIsInstance(params, IDZParameters)

        # 参数应该在合理范围
        self.assertGreater(params.K, 0)
        self.assertLess(params.K, 10000)
        self.assertGreater(params.tau_d, 0)
        self.assertLess(params.tau_d, 50000)
        self.assertGreater(params.tau_z, 0)
        self.assertGreater(params.theta, 0)


class TestSectionClusteringMethod(unittest.TestCase):
    """断面聚类法测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建10个断面，分为3组
        self.sections = []

        # 组1：小断面（底宽6-8m）
        for i in range(3):
            s = TrapezoidalSection(f"Small{i}", bottom_width=6.0 + i*0.5, side_slope=1.5)
            self.sections.append(s)

        # 组2：中断面（底宽10-12m）
        for i in range(4):
            s = TrapezoidalSection(f"Medium{i}", bottom_width=10.0 + i*0.5, side_slope=1.5)
            self.sections.append(s)

        # 组3：大断面（底宽14-16m）
        for i in range(3):
            s = TrapezoidalSection(f"Large{i}", bottom_width=14.0 + i*0.5, side_slope=1.5)
            self.sections.append(s)

        # 创建位置信息（等间距）
        self.locations = [
            SectionLocation(section=s, station=i*1000.0)
            for i, s in enumerate(self.sections)
        ]

        self.normal_depth = 2.5
        self.method = SectionClusteringMethod(
            section_locations=self.locations,
            normal_depth=self.normal_depth,
            n_clusters=3
        )

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.method.n_clusters, 3)
        self.assertEqual(len(self.method.section_locations), 10)
        self.assertEqual(self.method.normal_depth, self.normal_depth)

    def test_get_representative_sections(self):
        """测试获取代表断面"""
        representatives = self.method.get_representative_sections()

        # 应该返回列表
        self.assertIsInstance(representatives, list)

        # 应该有3个代表断面（3个簇）
        self.assertEqual(len(representatives), 3)

        # 每个代表应该是元组(start, end, section_location)
        for rep in representatives:
            self.assertIsInstance(rep, tuple)
            self.assertEqual(len(rep), 3)
            self.assertIsInstance(rep[0], (int, float))  # start
            self.assertIsInstance(rep[1], (int, float))  # end
            self.assertIsInstance(rep[2], SectionLocation)  # section


class TestSegmentedModelMethod(unittest.TestCase):
    """分段模型法测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建10个断面，沿程变化
        self.sections = [
            TrapezoidalSection(f"S{i}", bottom_width=8.0 + i*0.4, side_slope=1.5)
            for i in range(10)
        ]

        self.locations = [
            SectionLocation(section=s, station=i*1000.0)
            for i, s in enumerate(self.sections)
        ]

        # 分为3段（每3km一段）
        self.method = SegmentedModelMethod(
            section_locations=self.locations,
            segment_length=3000.0
        )

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.method.segment_length, 3000.0)
        self.assertEqual(len(self.method.section_locations), 10)

    def test_compute_segment_idz_parameters(self):
        """测试分段IDZ参数计算"""
        normal_depth = 2.5
        normal_flow = 25.0
        manning = 0.025
        bed_slope = 0.0001

        params_list = self.method.compute_segment_idz_parameters(
            normal_depth=normal_depth,
            normal_flow=normal_flow,
            manning_n=manning,
            bed_slope=bed_slope
        )

        # 应该返回列表
        self.assertIsInstance(params_list, list)

        # 10km渠道，每3km一段，应该有3-4段
        self.assertGreaterEqual(len(params_list), 3)
        self.assertLessEqual(len(params_list), 4)

        # 每个参数都应该是IDZParameters对象
        from control.idz_model import IDZParameters
        for params in params_list:
            self.assertIsInstance(params, IDZParameters)

            # K应该为正且在合理范围
            self.assertGreater(params.K, 0)
            self.assertLess(params.K, 10000)
            self.assertGreater(params.tau_z, 0)
            self.assertGreater(params.tau_d, 0)


class TestDataDrivenIdentification(unittest.TestCase):
    """数据驱动辨识法测试"""

    def setUp(self):
        """设置测试环境"""
        self.dt = 10.0
        self.method = DataDrivenIdentification(dt=self.dt)

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.method.dt, self.dt)

    def test_update_returns_dict(self):
        """测试update方法返回字典"""
        # 模拟简单数据
        np.random.seed(42)

        for i in range(50):
            u = 0.5 + 0.1 * np.sin(i * 0.1)
            y = 10.0 + 5.0 * u + 0.1 * np.random.randn()

            result = self.method.update(u, y)

        # update应该返回字典或None
        self.assertTrue(result is None or isinstance(result, dict))

    def test_convergence_with_data(self):
        """测试数据驱动辨识收敛"""
        # 模拟类渠道系统
        np.random.seed(42)

        y_prev = 0.0
        results = []

        for i in range(200):
            u = 0.5 + 0.1 * np.sin(i * 0.05)

            # 简化的渠道响应：y(k) = 0.9*y(k-1) + 0.2*u(k) + noise
            y = 0.9 * y_prev + 0.2 * u + 0.01 * np.random.randn()

            result = self.method.update(u, y)
            if result is not None:
                results.append(result)

            y_prev = y

        # 经过足够迭代后应该有结果
        self.assertGreater(len(results), 0)

        # 最终结果应该包含等效IDZ参数
        if results:
            final_result = results[-1]
            # DataDrivenIdentification返回'K_equivalent'和'tau_equivalent'
            self.assertIn('K_equivalent', final_result)
            self.assertIn('tau_equivalent', final_result)

            # 参数应该在合理范围
            self.assertGreater(final_result['K_equivalent'], 0)
            self.assertLess(final_result['K_equivalent'], 1000)
            self.assertGreater(final_result['tau_equivalent'], 0)
            self.assertLess(final_result['tau_equivalent'], 10000)


class TestMethodComparison(unittest.TestCase):
    """不同方法对比测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建10个梯形断面
        self.sections = [
            TrapezoidalSection(f"S{i}", bottom_width=8.0 + i*0.5, side_slope=1.5)
            for i in range(10)
        ]

        self.locations = [
            SectionLocation(section=s, station=i*1000.0)
            for i, s in enumerate(self.sections)
        ]

        # 水力参数
        self.normal_depth = 2.5
        self.normal_flow = 25.0
        self.manning = 0.025
        self.bed_slope = 0.0001

    def test_equivalent_method_single_K(self):
        """测试等效法返回单个K"""
        equiv_method = EquivalentSectionMethod(self.locations, self.normal_depth)
        equiv_params = equiv_method.compute_idz_parameters(
            normal_flow=self.normal_flow,
            manning_n=self.manning,
            bed_slope=self.bed_slope
        )

        # 应该返回IDZParameters对象
        from control.idz_model import IDZParameters
        self.assertIsInstance(equiv_params, IDZParameters)
        self.assertGreater(equiv_params.K, 0)
        self.assertLess(equiv_params.K, 5000)

    def test_clustering_method_multiple_segments(self):
        """测试聚类法返回多个段"""
        cluster_method = SectionClusteringMethod(
            self.locations,
            self.normal_depth,
            n_clusters=3
        )
        representatives = cluster_method.get_representative_sections()

        # 应该有3个代表断面
        self.assertEqual(len(representatives), 3)

        # 每个代表应该覆盖一定长度
        for start, end, section_loc in representatives:
            self.assertGreaterEqual(end, start)

    def test_segmented_method_multiple_K(self):
        """测试分段法返回多个K"""
        segment_method = SegmentedModelMethod(self.locations, segment_length=3000.0)
        segment_params_list = segment_method.compute_segment_idz_parameters(
            normal_depth=self.normal_depth,
            normal_flow=self.normal_flow,
            manning_n=self.manning,
            bed_slope=self.bed_slope
        )

        # 应该有多个段
        self.assertGreaterEqual(len(segment_params_list), 3)

        # 各段K应该有差异
        K_values = [p.K for p in segment_params_list]  # IDZParameters对象用.K访问
        K_std = np.std(K_values)

        # 由于底宽逐渐变化，K应该有差异
        self.assertGreater(K_std, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
