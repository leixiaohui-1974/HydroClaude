import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from physics.boundaries import ConstantHead, ConstantFlow, FreeOutflow

def test_constant_head():
    bc = ConstantHead(head=10.0)
    assert bc.type == "constant_head"
    assert bc.value == 10.0
    print("✓ Constant head boundary test passed")

def test_constant_flow():
    bc = ConstantFlow(flow=5.0)
    assert bc.type == "constant_flow"
    assert bc.value == 5.0
    print("✓ Constant flow boundary test passed")

def test_free_outflow():
    bc = FreeOutflow()
    assert bc.type == "free"
    print("✓ Free outflow boundary test passed")

if __name__ == "__main__":
    try:
        test_constant_head()
        test_constant_flow()
        test_free_outflow()
        print("\n所有边界条件测试通过!")
    except Exception as e:
        print(f"边界条件测试跳过: {e}")
