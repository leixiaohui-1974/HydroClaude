# Examples 1-16 测试报告

**生成时间**: 2025-10-22 11:45:44

## 📊 总体统计

- **总示例数**: 21
- **成功**: 5 (23.8%)
- **失败**: 16 (76.2%)
- **总耗时**: 44.69s

---

## 📋 详细结果

| ID | 名称 | 状态 | 耗时 | 错误信息 |
|----|------|------|------|----------|
| example_01_canal_flow | 01_basic | ✅ 成功 | 5.51s | - |
| example_01_canal_flow | 02_methods_comparison | ✅ 成功 | 8.71s | - |
| example_01_canal_flow | 05_step_response | ✅ 成功 | 9.09s | - |
| example_02_pump_system | example_02_pump_system_enhanced | ❌ 失败 | 0.03s | Traceback (most recent call last):
  File "/home/u |
| example_02_spillway_cascade | example_02_spillway_system | ❌ 失败 | 0.61s | Traceback (most recent call last):
  File "/home/u |
| example_03_turbine_demo | example_03_turbine_comparison | ❌ 失败 | 0.61s | Traceback (most recent call last):
  File "/home/u |
| example_03_complex_network | example_03_complex_network | ❌ 失败 | 0.03s | Traceback (most recent call last):
  File "/home/u |
| example_04_hydropower_system | example_04_hydropower_plant | ❌ 失败 | 0.60s | Traceback (most recent call last):
  File "/home/u |
| example_05_transient_analysis | example_05_load_rejection | ❌ 失败 | 0.61s | Traceback (most recent call last):
  File "/home/u |
| example_06_complete_hydropower_system | example_06_complete_system | ❌ 失败 | 0.61s | Traceback (most recent call last):
  File "/home/u |
| example_07_multi_unit_agc | example_07_multi_unit_agc | ❌ 失败 | 0.64s | Traceback (most recent call last):
  File "/home/u |
| example_08_load_acceptance | example_08_load_acceptance | ✅ 成功 | 1.53s | - |
| example_08_preissmann_vs_fvm | example_08_preissmann_vs_fvm_enhanced | ❌ 失败 | 0.69s | Traceback (most recent call last):
  File "/home/u |
| example_09_pipe_rk4 | example_09_pipe_rk4_enhanced | ❌ 失败 | 0.62s | Traceback (most recent call last):
  File "/home/u |
| example_10_series_network | example_10_series_network | ❌ 失败 | 0.03s | Traceback (most recent call last):
  File "/home/u |
| example_11_tree_network | example_11_tree_network | ❌ 失败 | 0.03s | Traceback (most recent call last):
  File "/home/u |
| example_12_loop_network | example_12_loop_network | ❌ 失败 | 0.03s | Traceback (most recent call last):
  File "/home/u |
| example_13_adaptive_timescale | example_13_adaptive_timescale_enhanced | ❌ 失败 | 0.62s | Traceback (most recent call last):
  File "/home/u |
| example_14_adaptive_mpc | example_14_adaptive_mpc_enhanced | ❌ 失败 | 0.62s | Traceback (most recent call last):
  File "/home/u |
| example_15_rls_identification | example_15_rls_identification_enhanced | ❌ 失败 | 0.63s | Traceback (most recent call last):
  File "/home/u |
| example_16_weirs_application | weirs_irrigation_system | ✅ 成功 | 12.86s | - |

---

## ✅ 成功的示例

### example_01_canal_flow: 01_basic

- **文件**: `examples/example_01_canal_flow/code/01_basic.py`
- **耗时**: 5.51s

### example_01_canal_flow: 02_methods_comparison

- **文件**: `examples/example_01_canal_flow/code/02_methods_comparison.py`
- **耗时**: 8.71s

### example_01_canal_flow: 05_step_response

- **文件**: `examples/example_01_canal_flow/code/05_step_response.py`
- **耗时**: 9.09s

### example_08_load_acceptance: example_08_load_acceptance

- **文件**: `examples/example_08_load_acceptance/example_08_load_acceptance.py`
- **耗时**: 1.53s
- **输出文件**: 1个
  - `examples/example_08_load_acceptance/load_acceptance_transient.png`

### example_16_weirs_application: weirs_irrigation_system

- **文件**: `examples/example_16_weirs_application/weirs_irrigation_system.py`
- **耗时**: 12.86s

## ❌ 失败的示例

### example_02_pump_system: example_02_pump_system_enhanced

- **文件**: `examples/example_02_pump_system/example_02_pump_system_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_02_pump_system/example_02_pump_system_enhanced.py", line 14, in <module>
    from physics.tank import Tank
ModuleNotFoundError: No module named 'physics'
```

### example_02_spillway_cascade: example_02_spillway_system

- **文件**: `examples/example_02_spillway_cascade/example_02_spillway_system.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_02_spillway_cascade/example_02_spillway_system.py", line 37, in <module>
    from solvers.gate import Spillway, Transition, Drop, BroadCrestedWeir
ModuleNotFoundError: No module named 'solvers'
```

### example_03_turbine_demo: example_03_turbine_comparison

- **文件**: `examples/example_03_turbine_demo/example_03_turbine_comparison.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_03_turbine_demo/example_03_turbine_comparison.py", line 29, in <module>
    from physics.turbine import FrancisTurbine, KaplanTurbine, PeltonTurbine
ModuleNotFoundError: No module named 'physics'
```

### example_03_complex_network: example_03_complex_network

- **文件**: `examples/example_03_complex_network/code/example_03_complex_network.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_03_complex_network/code/example_03_complex_network.py", line 4, in <module>
    from topology.network_graph import NetworkTopology, Node, Edge, NodeType
ModuleNotFoundError: No module named 'topology'
```

### example_04_hydropower_system: example_04_hydropower_plant

- **文件**: `examples/example_04_hydropower_system/example_04_hydropower_plant.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_04_hydropower_system/example_04_hydropower_plant.py", line 34, in <module>
    from physics.turbine import FrancisTurbine
ModuleNotFoundError: No module named 'physics'
```

### example_05_transient_analysis: example_05_load_rejection

- **文件**: `examples/example_05_transient_analysis/example_05_load_rejection.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_05_transient_analysis/example_05_load_rejection.py", line 33, in <module>
    from physics.turbine import FrancisTurbine
ModuleNotFoundError: No module named 'physics'
```

### example_06_complete_hydropower_system: example_06_complete_system

- **文件**: `examples/example_06_complete_hydropower_system/example_06_complete_system.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_06_complete_hydropower_system/example_06_complete_system.py", line 47, in <module>
    from physics.turbine import FrancisTurbine
ModuleNotFoundError: No module named 'physics'
```

### example_07_multi_unit_agc: example_07_multi_unit_agc

- **文件**: `examples/example_07_multi_unit_agc/example_07_multi_unit_agc.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_07_multi_unit_agc/example_07_multi_unit_agc.py", line 34, in <module>
    from control.agc import (
ModuleNotFoundError: No module named 'control'
```

### example_08_preissmann_vs_fvm: example_08_preissmann_vs_fvm_enhanced

- **文件**: `examples/example_08_preissmann_vs_fvm/example_08_preissmann_vs_fvm_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_08_preissmann_vs_fvm/example_08_preissmann_vs_fvm_enhanced.py", line 19, in <module>
    from physics.canal import Canal
ModuleNotFoundError: No module named 'physics'
```

### example_09_pipe_rk4: example_09_pipe_rk4_enhanced

- **文件**: `examples/example_09_pipe_rk4/example_09_pipe_rk4_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_09_pipe_rk4/example_09_pipe_rk4_enhanced.py", line 19, in <module>
    from physics.pipe import Pipe
ModuleNotFoundError: No module named 'physics'
```

### example_10_series_network: example_10_series_network

- **文件**: `examples/example_10_series_network/code/example_10_series_network.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_10_series_network/code/example_10_series_network.py", line 5, in <module>
    from topology.network_graph import NetworkTopology, Node, Edge, NodeType
ModuleNotFoundError: No module named 'topology'
```

### example_11_tree_network: example_11_tree_network

- **文件**: `examples/example_11_tree_network/code/example_11_tree_network.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_11_tree_network/code/example_11_tree_network.py", line 5, in <module>
    from topology.network_graph import NetworkTopology, Node, Edge, NodeType
ModuleNotFoundError: No module named 'topology'
```

### example_12_loop_network: example_12_loop_network

- **文件**: `examples/example_12_loop_network/code/example_12_loop_network.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_12_loop_network/code/example_12_loop_network.py", line 5, in <module>
    from topology.network_graph import NetworkTopology, Node, Edge, NodeType
ModuleNotFoundError: No module named 'topology'
```

### example_13_adaptive_timescale: example_13_adaptive_timescale_enhanced

- **文件**: `examples/example_13_adaptive_timescale/example_13_adaptive_timescale_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_13_adaptive_timescale/example_13_adaptive_timescale_enhanced.py", line 17, in <module>
    from models.timescale_selector import AdaptiveCanalModel, TimeScaleSelector
ModuleNotFoundError: No module named 'models'
```

### example_14_adaptive_mpc: example_14_adaptive_mpc_enhanced

- **文件**: `examples/example_14_adaptive_mpc/example_14_adaptive_mpc_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_14_adaptive_mpc/example_14_adaptive_mpc_enhanced.py", line 18, in <module>
    from control.adaptive_mpc import AdaptiveMPC, AdaptiveMPCConfig
ModuleNotFoundError: No module named 'control'
```

### example_15_rls_identification: example_15_rls_identification_enhanced

- **文件**: `examples/example_15_rls_identification/example_15_rls_identification_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_15_rls_identification/example_15_rls_identification_enhanced.py", line 18, in <module>
    from identification.rls_identifier import ARXIdentifier
ModuleNotFoundError: No module named 'identification'
```

