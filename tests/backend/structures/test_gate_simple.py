#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水工结构简单测试

测试闸门、堰、孔口等水工结构的流量计算
验证公式准确性和参数影响

Author: HydroClaude Test Team
Date: 2025-11-20
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice
import numpy as np
import pytest


class Test闸门:
    """测试闸门流量计算"""
    
    def test_01_创建闸门(self):
        """测试创建闸门"""
        print(f"\n{'='*70}")
        print(f"测试: 创建闸门")
        print(f"{'='*70}")
        
        position = 500.0
        width = 10.0
        opening = 2.0
        
        gate = SluiceGate(position=position, width=width, opening=opening)
        
        print(f"   位置: {gate.position} m")
        print(f"   宽度: {gate.width} m")
        print(f"   开度: {opening} m")
        
        assert gate.position == position
        assert gate.width == width
        
        print(f"   ✅ 闸门创建成功！")
    
    def test_02_自由流计算(self):
        """测试闸门自由流流量计算"""
        print(f"\n{'='*70}")
        print(f"测试: 闸门自由流计算")
        print(f"{'='*70}")
        
        gate = SluiceGate(position=500.0, width=10.0, opening=2.0, Cd=0.6)
        
        # 自由流条件：上游水深远大于下游水深
        h_up = 5.0
        h_down = 0.5
        
        Q, flow_type = gate.calculate_discharge(h_up, h_down)
        
        print(f"   上游水深: {h_up} m")
        print(f"   下游水深: {h_down} m")
        print(f"   流量: {Q:.4f} m³/s")
        print(f"   流型: {flow_type}")
        
        # 验证流量为正
        assert Q > 0, "流量应该为正"
        
        # 自由流理论公式: Q = Cd * B * e * sqrt(2 * g * h_up)
        Cd = 0.6
        B = 10.0
        e = 2.0
        g = 9.81
        Q_theory = Cd * B * e * np.sqrt(2 * g * h_up)
        
        print(f"   理论流量: {Q_theory:.4f} m³/s")
        
        error = abs(Q - Q_theory) / Q_theory * 100
        print(f"   误差: {error:.2f}%")
        
        # 允许一定误差（可能有淹没修正）
        assert error < 20.0, f"流量误差过大: {error:.2f}%"
        
        print(f"   ✅ 自由流计算通过！")
    
    def test_03_淹没流计算(self):
        """测试闸门淹没流流量计算"""
        print(f"\n{'='*70}")
        print(f"测试: 闸门淹没流计算")
        print(f"{'='*70}")
        
        gate = SluiceGate(position=500.0, width=10.0, opening=2.0, Cd=0.6)
        
        # 淹没流条件：上下游水深相近
        h_up = 5.0
        h_down = 4.0
        
        Q, flow_type = gate.calculate_discharge(h_up, h_down)
        
        print(f"   上游水深: {h_up} m")
        print(f"   下游水深: {h_down} m")
        print(f"   流量: {Q:.4f} m³/s")
        print(f"   流型: {flow_type}")
        
        # 验证流量为正
        assert Q > 0, "流量应该为正"
        
        # 淹没流理论公式: Q = Cd * B * e * sqrt(2 * g * (h_up - h_down))
        Cd = 0.6
        B = 10.0
        e = 2.0
        g = 9.81
        Q_theory = Cd * B * e * np.sqrt(2 * g * (h_up - h_down))
        
        print(f"   理论流量: {Q_theory:.4f} m³/s")
        
        error = abs(Q - Q_theory) / Q_theory * 100
        print(f"   误差: {error:.2f}%")
        
        assert error < 20.0, f"流量误差过大: {error:.2f}%"
        
        print(f"   ✅ 淹没流计算通过！")
    
    @pytest.mark.parametrize("opening", [1.0, 2.0, 3.0, 4.0])
    def test_不同开度(self, opening):
        """测试不同闸门开度"""
        print(f"\n测试开度: {opening} m")
        
        gate = SluiceGate(position=500.0, width=10.0, opening=opening)
        
        h_up = 5.0
        h_down = 0.5
        
        Q, flow_type = gate.calculate_discharge(h_up, h_down)
        
        print(f"   流量: {Q:.4f} m³/s")
        
        assert Q > 0
        
        print(f"   ✅ 通过")


class Test堰:
    """测试宽顶堰流量计算"""
    
    def test_01_创建堰(self):
        """测试创建宽顶堰"""
        print(f"\n{'='*70}")
        print(f"测试: 创建宽顶堰")
        print(f"{'='*70}")
        
        position = 500.0
        width = 10.0
        crest_height = 1.0
        
        weir = BroadCrestedWeir(position=position, width=width, crest_height=crest_height)
        
        print(f"   位置: {weir.position} m")
        print(f"   宽度: {weir.width} m")
        print(f"   堰顶高程: {crest_height} m")
        
        assert weir.position == position
        assert weir.width == width
        
        print(f"   ✅ 宽顶堰创建成功！")
    
    def test_02_自由溢流(self):
        """测试宽顶堰自由溢流"""
        print(f"\n{'='*70}")
        print(f"测试: 宽顶堰自由溢流")
        print(f"{'='*70}")
        
        weir = BroadCrestedWeir(position=500.0, width=10.0, crest_height=1.0, Cd=0.4)
        
        h_up = 2.5  # 上游水深2.5m，超过堰顶1.5m
        h_down = 0.5
        
        Q, flow_type = weir.calculate_discharge(h_up, h_down)
        
        print(f"   上游水深: {h_up} m")
        print(f"   下游水深: {h_down} m")
        print(f"   超高: {h_up - 1.0:.2f} m")
        print(f"   流量: {Q:.4f} m³/s")
        print(f"   流型: {flow_type}")
        
        assert Q > 0, "流量应该为正"
        
        print(f"   ✅ 自由溢流计算通过！")
    
    @pytest.mark.parametrize("h_up", [1.5, 2.0, 2.5, 3.0])
    def test_不同上游水深(self, h_up):
        """测试不同上游水深的溢流"""
        print(f"\n测试上游水深: {h_up} m")
        
        weir = BroadCrestedWeir(position=500.0, width=10.0, crest_height=1.0)
        
        h_down = 0.5
        
        Q, flow_type = weir.calculate_discharge(h_up, h_down)
        
        print(f"   流量: {Q:.4f} m³/s")
        
        if h_up > 1.0:  # 超过堰顶
            assert Q > 0
        
        print(f"   ✅ 通过")


class Test孔口:
    """测试孔口流量计算"""
    
    def test_01_创建孔口(self):
        """测试创建孔口"""
        print(f"\n{'='*70}")
        print(f"测试: 创建孔口")
        print(f"{'='*70}")
        
        position = 500.0
        width = 5.0
        height = 2.0
        bottom_elevation = 0.5
        
        orifice = Orifice(position=position, width=width, 
                         height=height, bottom_elevation=bottom_elevation)
        
        print(f"   位置: {orifice.position} m")
        print(f"   宽度: {width} m")
        print(f"   高度: {height} m")
        print(f"   底高程: {bottom_elevation} m")
        
        assert orifice.position == position
        
        print(f"   ✅ 孔口创建成功！")
    
    def test_02_孔口出流(self):
        """测试孔口出流计算"""
        print(f"\n{'='*70}")
        print(f"测试: 孔口出流")
        print(f"{'='*70}")
        
        orifice = Orifice(position=500.0, width=5.0, 
                         height=2.0, bottom_elevation=0.5, Cd=0.6)
        
        h_up = 4.0
        h_down = 0.5
        
        Q, flow_type = orifice.calculate_discharge(h_up, h_down)
        
        print(f"   上游水深: {h_up} m")
        print(f"   下游水深: {h_down} m")
        print(f"   流量: {Q:.4f} m³/s")
        print(f"   流型: {flow_type}")
        
        assert Q > 0, "流量应该为正"
        
        print(f"   ✅ 孔口出流计算通过！")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
