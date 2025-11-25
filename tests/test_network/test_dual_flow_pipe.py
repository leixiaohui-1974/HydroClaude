"""
Unit Tests for Dual Flow Pipe - 明满流管道单元测试
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import pytest
import numpy as np
from network.dual_flow_pipe import DualFlowPipe


class TestDualFlowPipe:
    """测试明满流管道"""

    def test_initialization(self):
        """测试初始化"""
        pipe = DualFlowPipe(diameter=1.0, length=100.0, roughness=0.013)
        
        assert pipe.D == 1.0
        assert pipe.L == 100.0
        assert pipe.n == 0.013
        assert pipe.b_slot > 0
    
    def test_flow_area_open_channel(self):
        """测试明流时的过水面积"""
        pipe = DualFlowPipe(diameter=1.0, length=100.0, roughness=0.013)
        
        # 半满
        A_half = pipe.flow_area(0.5)
        assert 0 < A_half <= pipe.A_full
        
        # 全满
        A_full = pipe.flow_area(1.0)
        assert abs(A_full - pipe.A_full) < 1e-3
    
    def test_flow_area_pressurized(self):
        """测试满流时的面积（含虚拟狭缝）"""
        pipe = DualFlowPipe(diameter=1.0, length=100.0, roughness=0.013)
        
        # 超过管顶
        h = 1.2  # 超出0.2m
        A = pipe.flow_area(h)
        
        # 应该大于管道面积
        assert A > pipe.A_full
    
    def test_is_pressurized(self):
        """测试满管判断"""
        pipe = DualFlowPipe(diameter=1.0, length=100.0, roughness=0.013)
        
        assert not pipe.is_pressurized(0.5)  # 明流
        assert not pipe.is_pressurized(0.98)  # 接近满管但未满
        assert pipe.is_pressurized(1.0)  # 满管
        assert pipe.is_pressurized(1.2)  # 有压流
    
    def test_flow_type(self):
        """测试流态类型"""
        pipe = DualFlowPipe(diameter=1.0, length=100.0, roughness=0.013)
        
        assert pipe.flow_type(0.5) == "open"
        assert pipe.flow_type(0.98) == "transitional"
        assert pipe.flow_type(1.2) == "pressurized"
    
    def test_hydraulic_radius(self):
        """测试水力半径"""
        pipe = DualFlowPipe(diameter=1.0, length=100.0, roughness=0.013)
        
        R = pipe.hydraulic_radius(0.5)
        assert R > 0
        assert R <= pipe.D  # 水力半径合理范围


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
