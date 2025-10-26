#!/bin/bash
# 快速运行多个工况

cd /workspace/examples/example_gate_pump_cascade

echo "=========================================="
echo "工况2: 上游流量中等阶跃 (30→42 m³/s)"
echo "=========================================="

# 临时修改Q_step
sed -i 's/Q_step = 55.0/Q_step = 42.0/' gate_pump_cascade_advanced.py
# 修改输出目录
sed -i 's|"results"|"results_advanced/scenario_02_upstream_flow_medium"|' gate_pump_cascade_advanced.py

# 运行
python3 gate_pump_cascade_advanced.py 2>&1 | tail -30

# 恢复
sed -i 's/Q_step = 42.0/Q_step = 55.0/' gate_pump_cascade_advanced.py
sed -i 's|"results_advanced/scenario_02_upstream_flow_medium"|"results"|' gate_pump_cascade_advanced.py

echo ""
echo "✓ 工况2完成"
echo ""
