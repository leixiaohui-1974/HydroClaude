# Examples 1-16 测试报告

**生成时间**: 2025-10-22 12:19:05

## 📊 总体统计

- **总示例数**: 21
- **成功**: 21 (100.0%)
- **失败**: 0 (0.0%)
- **总耗时**: 113.59s

---

## 📋 详细结果

| ID | 名称 | 状态 | 耗时 | 错误信息 |
|----|------|------|------|----------|
| example_01_canal_flow | 01_basic | ✅ 成功 | 5.70s | - |
| example_01_canal_flow | 02_methods_comparison | ✅ 成功 | 8.69s | - |
| example_01_canal_flow | 05_step_response | ✅ 成功 | 9.27s | - |
| example_02_pump_system | example_02_pump_system_enhanced | ✅ 成功 | 3.86s | - |
| example_02_spillway_cascade | example_02_spillway_system | ✅ 成功 | 0.94s | - |
| example_03_turbine_demo | example_03_turbine_comparison | ✅ 成功 | 1.45s | - |
| example_03_complex_network | example_03_complex_network | ✅ 成功 | 0.52s | - |
| example_04_hydropower_system | example_04_hydropower_plant | ✅ 成功 | 1.34s | - |
| example_05_transient_analysis | example_05_load_rejection | ✅ 成功 | 1.62s | - |
| example_06_complete_hydropower_system | example_06_complete_system | ✅ 成功 | 1.42s | - |
| example_07_multi_unit_agc | example_07_multi_unit_agc | ✅ 成功 | 2.09s | - |
| example_08_load_acceptance | example_08_load_acceptance | ✅ 成功 | 1.56s | - |
| example_08_preissmann_vs_fvm | example_08_preissmann_vs_fvm_enhanced | ✅ 成功 | 8.05s | - |
| example_09_pipe_rk4 | example_09_pipe_rk4_enhanced | ✅ 成功 | 33.07s | - |
| example_10_series_network | example_10_series_network | ✅ 成功 | 0.51s | - |
| example_11_tree_network | example_11_tree_network | ✅ 成功 | 0.53s | - |
| example_12_loop_network | example_12_loop_network | ✅ 成功 | 1.54s | - |
| example_13_adaptive_timescale | example_13_adaptive_timescale_enhanced | ✅ 成功 | 3.87s | - |
| example_14_adaptive_mpc | example_14_adaptive_mpc_enhanced | ✅ 成功 | 5.75s | - |
| example_15_rls_identification | example_15_rls_identification_enhanced | ✅ 成功 | 8.91s | - |
| example_16_weirs_application | weirs_irrigation_system | ✅ 成功 | 12.90s | - |

---

## ✅ 成功的示例

### example_01_canal_flow: 01_basic

- **文件**: `examples/example_01_canal_flow/code/01_basic.py`
- **耗时**: 5.70s

### example_01_canal_flow: 02_methods_comparison

- **文件**: `examples/example_01_canal_flow/code/02_methods_comparison.py`
- **耗时**: 8.69s

### example_01_canal_flow: 05_step_response

- **文件**: `examples/example_01_canal_flow/code/05_step_response.py`
- **耗时**: 9.27s

### example_02_pump_system: example_02_pump_system_enhanced

- **文件**: `examples/example_02_pump_system/example_02_pump_system_enhanced.py`
- **耗时**: 3.86s

### example_02_spillway_cascade: example_02_spillway_system

- **文件**: `examples/example_02_spillway_cascade/example_02_spillway_system.py`
- **耗时**: 0.94s
- **输出文件**: 1个
  - `examples/example_02_spillway_cascade/rating_curve.png`

### example_03_turbine_demo: example_03_turbine_comparison

- **文件**: `examples/example_03_turbine_demo/example_03_turbine_comparison.py`
- **耗时**: 1.45s
- **输出文件**: 2个
  - `examples/example_03_turbine_demo/hill_chart.png`
  - `examples/example_03_turbine_demo/turbine_comparison.png`

### example_03_complex_network: example_03_complex_network

- **文件**: `examples/example_03_complex_network/code/example_03_complex_network.py`
- **耗时**: 0.52s

### example_04_hydropower_system: example_04_hydropower_plant

- **文件**: `examples/example_04_hydropower_system/example_04_hydropower_plant.py`
- **耗时**: 1.34s
- **输出文件**: 1个
  - `examples/example_04_hydropower_system/plant_performance.png`

### example_05_transient_analysis: example_05_load_rejection

- **文件**: `examples/example_05_transient_analysis/example_05_load_rejection.py`
- **耗时**: 1.62s
- **输出文件**: 1个
  - `examples/example_05_transient_analysis/load_rejection.png`

### example_06_complete_hydropower_system: example_06_complete_system

- **文件**: `examples/example_06_complete_hydropower_system/example_06_complete_system.py`
- **耗时**: 1.42s
- **输出文件**: 1个
  - `examples/example_06_complete_hydropower_system/complete_system_performance.png`

### example_07_multi_unit_agc: example_07_multi_unit_agc

- **文件**: `examples/example_07_multi_unit_agc/example_07_multi_unit_agc.py`
- **耗时**: 2.09s
- **输出文件**: 3个
  - `examples/example_07_multi_unit_agc/scenario3_tie_line_control.png`
  - `examples/example_07_multi_unit_agc/scenario1_frequency_disturbance.png`
  - `examples/example_07_multi_unit_agc/scenario2_load_variation.png`

### example_08_load_acceptance: example_08_load_acceptance

- **文件**: `examples/example_08_load_acceptance/example_08_load_acceptance.py`
- **耗时**: 1.56s
- **输出文件**: 1个
  - `examples/example_08_load_acceptance/load_acceptance_transient.png`

### example_08_preissmann_vs_fvm: example_08_preissmann_vs_fvm_enhanced

- **文件**: `examples/example_08_preissmann_vs_fvm/example_08_preissmann_vs_fvm_enhanced.py`
- **耗时**: 8.05s

### example_09_pipe_rk4: example_09_pipe_rk4_enhanced

- **文件**: `examples/example_09_pipe_rk4/example_09_pipe_rk4_enhanced.py`
- **耗时**: 33.07s

### example_10_series_network: example_10_series_network

- **文件**: `examples/example_10_series_network/code/example_10_series_network.py`
- **耗时**: 0.51s

### example_11_tree_network: example_11_tree_network

- **文件**: `examples/example_11_tree_network/code/example_11_tree_network.py`
- **耗时**: 0.53s

### example_12_loop_network: example_12_loop_network

- **文件**: `examples/example_12_loop_network/code/example_12_loop_network.py`
- **耗时**: 1.54s

### example_13_adaptive_timescale: example_13_adaptive_timescale_enhanced

- **文件**: `examples/example_13_adaptive_timescale/example_13_adaptive_timescale_enhanced.py`
- **耗时**: 3.87s

### example_14_adaptive_mpc: example_14_adaptive_mpc_enhanced

- **文件**: `examples/example_14_adaptive_mpc/example_14_adaptive_mpc_enhanced.py`
- **耗时**: 5.75s

### example_15_rls_identification: example_15_rls_identification_enhanced

- **文件**: `examples/example_15_rls_identification/example_15_rls_identification_enhanced.py`
- **耗时**: 8.91s

### example_16_weirs_application: weirs_irrigation_system

- **文件**: `examples/example_16_weirs_application/weirs_irrigation_system.py`
- **耗时**: 12.90s

