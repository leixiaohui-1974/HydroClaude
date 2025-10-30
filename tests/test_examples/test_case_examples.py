#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例示例验证测试
Case Examples Validation Tests

验证案例库中的示例能够正确运行并产生合理结果

Author: HydroClaude Team
Date: 2025-10-30
"""

import sys
import os
import pytest
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from network.pressure_pipe import create_pressure_pipe
from network.network_node import Junction, Reservoir, Tank
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver


class TestUrbanWaterSupplyCase:
    """测试城市供水管网案例"""

    def test_case1_network_creation(self):
        """测试管网创建"""
        # 导入案例模块
        from examples.case1_urban_water_supply import create_urban_water_network

        topology = create_urban_water_network()

        # 验证节点数量
        assert len(topology.nodes) == 8  # 1水库 + 1水塔 + 6节点
        assert 'R1' in topology.nodes
        assert 'T1' in topology.nodes
        for i in range(1, 7):
            assert f'J{i}' in topology.nodes

        # 验证管道数量
        assert len(topology.pipes) == 8
        for i in range(1, 9):
            assert f'P{i}' in topology.pipes

        # 验证环路检测
        loops = topology.find_loops()
        assert len(loops) > 0  # 至少有一个环路

    def test_case1_steady_state_analysis(self):
        """测试稳态水力分析"""
        from examples.case1_urban_water_supply import (
            create_urban_water_network,
            analyze_operating_conditions
        )

        topology = create_urban_water_network()
        results = analyze_operating_conditions(topology)

        # 验证三种工况都收敛
        assert '高峰工况' in results
        assert '平均工况' in results
        assert '低峰工况' in results

        for scenario, result in results.items():
            assert result['converged'], f"{scenario} 未收敛"
            assert result['iterations'] > 0
            assert result['iterations'] <= 100

            # 验证节点水头都是正数
            for nid, head in result['heads'].items():
                assert head > 0, f"{scenario}: 节点{nid}水头为负"

            # 验证水库和水塔水头合理
            H_reservoir = result['heads']['R1']
            H_tank = result['heads']['T1']
            assert 120 < H_reservoir < 140, "水库水头异常"
            assert 100 < H_tank < 130, "水塔水头异常"

    def test_case1_pressure_requirements(self):
        """测试压力要求"""
        from examples.case1_urban_water_supply import create_urban_water_network
        from solvers.hardy_cross_solver import HardyCrossSolver

        topology = create_urban_water_network()
        solver = HardyCrossSolver(topology, max_iter=100, tol=1e-6, verbose=False)
        flows, heads = solver.solve()

        # 检查所有节点压力
        junction_ids = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6']
        pressures = []

        for jid in junction_ids:
            node = topology.nodes[jid]
            head = heads[jid]
            pressure = head - node.elevation
            pressures.append(pressure)
            assert pressure > 0, f"节点{jid}压力为负"

        # 至少大部分节点满足15m最小压力
        min_pressure = min(pressures)
        assert min_pressure > 5, "最小压力过低"

    def test_case1_flow_conservation(self):
        """测试流量守恒"""
        from examples.case1_urban_water_supply import create_urban_water_network
        from solvers.hardy_cross_solver import HardyCrossSolver

        topology = create_urban_water_network()
        solver = HardyCrossSolver(topology, max_iter=100, tol=1e-6, verbose=False)
        flows, heads = solver.solve()

        # 计算总需水量
        total_demand = sum(
            node.demand for node in topology.nodes.values()
            if isinstance(node, Junction)
        )

        # 计算从水库流出的总流量（P1）
        Q_reservoir = abs(flows['P1'])

        # 流量守恒误差应小于1%
        error = abs(Q_reservoir - total_demand) / total_demand
        assert error < 0.01, f"流量守恒误差过大: {error*100:.2f}%"


class TestPumpWaterHammerCase:
    """测试泵站水锤案例"""

    def test_case2_joukowsky_formula(self):
        """测试Joukowsky公式计算"""
        from examples.case2_pump_water_hammer import joukowsky_analysis

        # 运行Joukowsky分析（返回元组）
        Q0, D, L, a, f, V0, delta_H_jouk, T_critical = joukowsky_analysis()

        # 验证参数合理性
        assert Q0 > 0, "流量应为正"
        assert D > 0, "管径应为正"
        assert L > 0, "长度应为正"
        assert a > 0, "波速应为正"
        assert V0 > 0, "流速应为正"

        # 验证波速在合理范围内（800-1200 m/s）
        assert 800 < a < 1200, "波速超出合理范围"

        # 验证Joukowsky压力升高
        assert delta_H_jouk > 0, "压力升高应为正"

        # 验证ΔH = a*V/g公式
        g = 9.81
        expected_delta_H = a * V0 / g
        assert abs(delta_H_jouk - expected_delta_H) < 0.1, "Joukowsky公式计算错误"

        # 验证临界时间
        expected_T_c = 2 * L / a
        assert abs(T_critical - expected_T_c) < 0.01, "临界时间计算错误"

    def test_case2_moc_simulation_setup(self):
        """测试MOC模拟设置"""
        from examples.case2_pump_water_hammer import simulate_power_failure

        Q0 = 1.0  # m³/s
        D = 0.8   # m
        L = 5000  # m
        a = 1000  # m/s
        f = 0.02

        # 运行模拟（短时间）
        solver, result, H0_up = simulate_power_failure(Q0, D, L, a, f, duration=1.0, verbose=False)

        # 验证求解器设置
        assert solver.nx > 10, "空间节点数太少"
        assert solver.dt > 0, "时间步长应为正"

        # 验证CFL条件
        CFL = solver.a * solver.dt / solver.dx
        assert 0.5 < CFL <= 1.0, f"CFL数不合理: {CFL}"

        # 验证结果数组形状（result是字典）
        assert result['H'].shape[1] == solver.nx, "水头数组形状错误"
        assert result['Q'].shape[1] == solver.nx, "流量数组形状错误"
        assert len(result['t']) > 0, "时间历程为空"

    def test_case2_water_hammer_physics(self):
        """测试水锤物理现象"""
        from examples.case2_pump_water_hammer import simulate_power_failure

        Q0 = 1.0
        D = 0.8
        L = 5000
        a = 1000
        f = 0.02

        # 运行完整模拟
        solver, result, H0 = simulate_power_failure(Q0, D, L, a, f, duration=20.0, verbose=False)

        # 提取下游（阀门处）压力历程
        H_downstream = result['H'][:, -1]  # 最后一个节点的所有时间步
        t_history = result['t']

        # 找到最大和最小水头
        H_max = np.max(H_downstream)
        H_min = np.min(H_downstream)

        # 验证压力升高
        delta_H_max = H_max - H0
        assert delta_H_max > 0, "应该出现压力升高"

        # 验证压力下降
        delta_H_min = H_min - H0
        assert delta_H_min < 0, "应该出现压力下降"

        # 验证压力升高和下降大致相等（能量守恒）
        assert abs(abs(delta_H_max) - abs(delta_H_min)) / abs(delta_H_max) < 0.3, \
            "压力升高和下降应大致相等"

        # 验证压力升高接近Joukowsky理论
        g = 9.81
        A = np.pi * (D/2)**2
        V0 = Q0 / A
        delta_H_jouk = a * V0 / g

        error = abs(delta_H_max - delta_H_jouk) / delta_H_jouk
        assert error < 0.5, f"数值结果与Joukowsky理论偏差过大: {error*100:.1f}%"

    def test_case2_pressure_wave_propagation(self):
        """测试压力波传播"""
        from examples.case2_pump_water_hammer import simulate_power_failure

        Q0 = 1.0
        D = 0.8
        L = 5000
        a = 1000
        f = 0.02

        solver, result, H0 = simulate_power_failure(Q0, D, L, a, f, duration=20.0, verbose=False)

        # 理论临界时间
        T_c = 2 * L / a

        # 在临界时间附近应该看到压力峰值
        t_history = np.array(result['t'])
        H_downstream = result['H'][:, -1]  # 最后一个节点

        # 找到第一个压力峰值的时间
        # 跳过前几个时间步避免初始扰动
        start_idx = 5
        peaks = []
        for i in range(start_idx, len(H_downstream)-1):
            if H_downstream[i] > H_downstream[i-1] and H_downstream[i] > H_downstream[i+1]:
                if H_downstream[i] > 150:  # 显著的峰值
                    peaks.append((t_history[i], H_downstream[i]))

        assert len(peaks) > 0, "应该检测到压力峰值"

        # 第一个峰值应该在临界时间附近
        t_first_peak = peaks[0][0]
        assert abs(t_first_peak - T_c) < 2.0, \
            f"第一个压力峰值时间({t_first_peak:.1f}s)偏离临界时间({T_c:.1f}s)过多"

    def test_case2_valve_closure(self):
        """测试阀门关闭边界条件"""
        from examples.case2_pump_water_hammer import simulate_power_failure

        Q0 = 1.0
        D = 0.8
        L = 5000
        a = 1000
        f = 0.02

        solver, result, H0 = simulate_power_failure(Q0, D, L, a, f, duration=5.0, verbose=False)

        # 提取下游流量历程
        Q_downstream = result['Q'][:, -1]  # 最后一个节点
        t_history = result['t']

        # 阀门在t=0.1s关闭后，流量应该接近0
        t_close = 0.1
        idx_after_close = np.where(np.array(t_history) > t_close + 0.5)[0]

        if len(idx_after_close) > 0:
            Q_after = Q_downstream[idx_after_close]
            # 关闭后流量应该很小
            assert np.mean(np.abs(Q_after)) < 0.1 * Q0, "阀门关闭后流量应接近0"


class TestCaseExamplesIntegration:
    """集成测试：验证案例可以独立运行"""

    def test_case1_standalone_execution(self, capsys):
        """测试案例1可以独立执行"""
        # 清除之前的输出
        capsys.readouterr()

        # 导入并运行主函数
        from examples.case1_urban_water_supply import main
        main()

        # 捕获输出
        captured = capsys.readouterr()

        # 验证关键输出
        assert '城市供水管网系统' in captured.out
        assert '✅ 案例分析完成' in captured.out
        assert '高峰工况' in captured.out
        assert '平均工况' in captured.out
        assert '低峰工况' in captured.out

    def test_case2_standalone_execution(self, capsys):
        """测试案例2可以独立执行"""
        # 清除之前的输出
        capsys.readouterr()

        # 导入并运行主函数
        from examples.case2_pump_water_hammer import main
        main()

        # 捕获输出
        captured = capsys.readouterr()

        # 验证关键输出
        assert '泵站水锤分析案例' in captured.out
        assert 'Joukowsky' in captured.out
        assert '✅ 案例分析完成' in captured.out
        assert '水锤防护措施建议' in captured.out


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
