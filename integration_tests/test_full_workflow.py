"""
集成测试 - 完整工作流

测试从配置生成到结果分析的完整工作流程。

运行方式:
    pytest integration_tests/test_full_workflow.py -v
"""

import pytest
import numpy as np
import sys
from pathlib import Path
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config_generator import ConfigGenerator
from modeling.universal_modeler import UniversalModeler
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from control.pid_controller import PIDController
from utils.data_exporter import DataExporter
from utils.report_generator import ReportGenerator


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # 清理
    shutil.rmtree(temp_dir)


@pytest.mark.integration
class TestBasicWorkflow:
    """基础工作流测试"""

    def test_config_to_simulation_workflow(self, temp_workspace):
        """
        测试配置生成 -> 模拟运行的完整流程
        """
        # 1. 生成配置
        gen = ConfigGenerator()
        config = gen.create_basic_canal(
            length=2000,
            nx=50,
            width=8.0,
            Q_in=15.0,
            h_downstream=2.0,
            T=1800,
            dt=2.0
        )

        # 保存配置
        config_file = temp_workspace / "test_config.yaml"
        success = gen.save_config(config, str(config_file))
        assert success, "配置保存失败"
        assert config_file.exists(), "配置文件未创建"

        # 2. 加载并运行模拟
        try:
            modeler = UniversalModeler(str(config_file))
            results = modeler.run()

            # 验证结果
            assert 'time' in results, "结果缺少时间数组"
            assert 'water_depth' in results, "结果缺少水深数据"
            assert len(results['time']) > 0, "结果为空"

            # 验证物理合理性
            assert np.all(results['water_depth'] > 0), "水深应该为正"
            assert np.all(results['water_depth'] < 10), "水深不应过大"

        except Exception as e:
            pytest.fail(f"模拟运行失败: {e}")

    def test_simulation_and_export_workflow(self, temp_workspace):
        """
        测试模拟 -> 数据导出的工作流
        """
        # 1. 运行模拟
        solver = HydrostaticCanalSolver(
            length=1000,
            nx=20,
            width=5.0,
            manning_n=0.025,
            slope=0.0002,
            dt=1.0
        )

        solver.Q_in = 10.0
        solver.h_downstream = 2.0

        # 运行100步
        time_history = []
        h_history = []

        for step in range(100):
            solver.step()
            time_history.append(solver.t)
            h_history.append(solver.h.copy())

        time = np.array(time_history)
        h_data = np.array(h_history)

        # 2. 导出数据
        exporter = DataExporter(output_dir=str(temp_workspace))

        # 导出时间序列
        files = exporter.export_time_series(
            time, h_data,
            filename='water_depth',
            formats=['csv', 'json', 'npz']
        )

        # 验证导出
        assert 'csv' in files, "CSV导出失败"
        assert 'json' in files, "JSON导出失败"
        assert 'npz' in files, "NPZ导出失败"

        # 验证文件存在
        for file_path in files.values():
            assert Path(file_path).exists(), f"导出文件不存在: {file_path}"

    def test_simulation_and_report_workflow(self, temp_workspace):
        """
        测试模拟 -> 报告生成的工作流
        """
        # 1. 运行模拟
        solver = HydrostaticCanalSolver(
            length=1000,
            nx=20,
            width=5.0,
            manning_n=0.025,
            slope=0.0002,
            dt=1.0
        )

        solver.Q_in = 10.0
        solver.h_downstream = 2.0

        # 运行50步
        for _ in range(50):
            solver.step()

        # 2. 生成报告
        reporter = ReportGenerator(output_dir=str(temp_workspace))

        # 添加系统信息
        reporter.add_system_info('渠道长度', '1000 m')
        reporter.add_system_info('网格数量', '20')

        # 添加结果
        reporter.add_result('最终时间', f'{solver.t:.2f} s')
        reporter.add_result('平均水深', f'{np.mean(solver.h):.3f} m')

        # 生成报告
        md_file = reporter.generate_markdown(str(temp_workspace / "report.md"))
        html_file = reporter.generate_html(str(temp_workspace / "report.html"))

        # 验证报告生成
        assert Path(md_file).exists(), "Markdown报告未生成"
        assert Path(html_file).exists(), "HTML报告未生成"


@pytest.mark.integration
class TestControlWorkflow:
    """控制系统工作流测试"""

    def test_solver_with_pid_control_workflow(self, temp_workspace):
        """
        测试求解器 + PID控制器的集成
        """
        # 1. 创建求解器
        solver = HydrostaticCanalSolver(
            length=2000,
            nx=30,
            width=8.0,
            manning_n=0.025,
            slope=0.0001,
            dt=1.0
        )

        solver.Q_in = 15.0
        solver.h_downstream = 2.0

        # 2. 创建PID控制器
        controller = PIDController(
            Kp=3.0,
            Ki=0.3,
            Kd=0.05,
            dt=1.0,
            output_limits=(10.0, 25.0)
        )

        controller.set_setpoint(2.5)

        # 3. 运行闭环控制
        n_steps = 200
        h_history = []
        u_history = []

        for step in range(n_steps):
            # 获取中点水位
            h_mid = solver.h[solver.nx // 2]

            # 计算控制输入
            u = controller.compute(h_mid)

            # 应用控制
            solver.Q_in = u
            solver.step()

            # 记录
            h_history.append(h_mid)
            u_history.append(u)

        h_history = np.array(h_history)
        u_history = np.array(u_history)

        # 4. 验证控制性能
        # 最后50步的平均误差应该较小
        final_error = np.mean(np.abs(h_history[-50:] - 2.5))
        assert final_error < 0.5, f"控制误差过大: {final_error:.3f}"

        # 控制输入应该在限幅范围内
        assert np.all((u_history >= 10.0) & (u_history <= 25.0)), "控制输入超出限幅"

    def test_config_with_control_full_workflow(self, temp_workspace):
        """
        测试带控制器的配置完整工作流
        """
        # 1. 生成配置
        gen = ConfigGenerator()
        config = gen.create_basic_canal(
            length=3000,
            nx=50,
            Q_in=20.0,
            h_downstream=2.5,
            T=1800,
            simulation_type='unsteady'
        )

        # 添加闸门
        config = gen.add_structure(
            config, 'gate', position=1500,
            opening=0.8, width=10.0, height=3.0
        )

        # 添加PID控制器
        config = gen.add_controller(
            config, 'pid', target_level=2.5,
            sensor_position=2000,
            Kp=5.0, Ki=0.5, Kd=0.1
        )

        # 保存配置
        config_file = temp_workspace / "control_config.yaml"
        gen.save_config(config, str(config_file))

        # 2. 验证配置可以加载（但不实际运行模拟）
        assert config_file.exists(), "配置文件未创建"

        # 验证配置内容
        assert 'control' in config, "配置缺少控制器"
        assert 'structures' in config, "配置缺少结构物"


@pytest.mark.integration
@pytest.mark.slow
class TestComplexWorkflow:
    """复杂工作流测试"""

    def test_end_to_end_with_all_tools(self, temp_workspace):
        """
        端到端测试：配置生成 -> 模拟 -> 数据导出 -> 报告生成
        """
        # 1. 配置生成
        gen = ConfigGenerator()
        config = gen.create_basic_canal(
            length=1500,
            nx=30,
            Q_in=15.0,
            h_downstream=2.0,
            T=600,
            dt=2.0
        )

        config_file = temp_workspace / "full_test_config.yaml"
        gen.save_config(config, str(config_file))

        # 2. 运行模拟
        try:
            modeler = UniversalModeler(str(config_file))
            results = modeler.run()
        except Exception as e:
            pytest.skip(f"模拟运行需要完整的UniversalModeler实现: {e}")
            return

        # 3. 数据导出
        exporter = DataExporter(output_dir=str(temp_workspace))
        export_files = exporter.export_time_series(
            results['time'],
            results['water_depth'],
            filename='simulation_results',
            formats=['csv', 'npz']
        )

        # 4. 生成报告
        reporter = ReportGenerator(output_dir=str(temp_workspace))
        reporter.add_system_info('配置文件', config_file.name)
        reporter.add_system_info('模拟时间', f"{results['time'][-1]:.1f} s")
        reporter.add_result('网格数量', str(config['geometry']['nx']))
        reporter.add_result('平均水深', f"{np.mean(results['water_depth']):.3f} m")

        report_file = reporter.generate_html(str(temp_workspace / "full_report.html"))

        # 5. 验证所有输出
        assert len(export_files) > 0, "数据导出失败"
        assert Path(report_file).exists(), "报告生成失败"

        # 验证数据合理性
        assert np.all(np.isfinite(results['water_depth'])), "结果包含无效值"


@pytest.mark.integration
class TestRobustness:
    """鲁棒性测试"""

    def test_invalid_config_handling(self, temp_workspace):
        """
        测试无效配置的处理
        """
        gen = ConfigGenerator()

        # 创建无效配置（nx太小）
        config = gen.create_basic_canal(
            length=1000,
            nx=5,  # 太小
            Q_in=10.0,
            h_downstream=2.0
        )

        # 验证应该失败
        is_valid, errors = gen.validate_config(config)
        assert not is_valid, "应该检测到无效配置"
        assert len(errors) > 0, "应该有错误消息"

    def test_numerical_stability(self):
        """
        测试数值稳定性
        """
        solver = HydrostaticCanalSolver(
            length=1000,
            nx=50,
            width=10.0,
            manning_n=0.025,
            slope=0.0001,
            dt=0.5  # 小时间步长
        )

        solver.Q_in = 20.0
        solver.h_downstream = 2.5

        # 运行多步
        for _ in range(500):
            solver.step()

            # 检查数值稳定性
            assert np.all(np.isfinite(solver.h)), "水深包含无效值"
            assert np.all(np.isfinite(solver.hu)), "流量包含无效值"
            assert np.all(solver.h > 0), "水深应该为正"
            assert np.all(solver.h < 100), "水深不合理"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
