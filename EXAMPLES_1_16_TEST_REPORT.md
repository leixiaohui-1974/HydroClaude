# Examples 1-16 测试报告

**生成时间**: 2025-10-22 12:09:44

## 📊 总体统计

- **总示例数**: 21
- **成功**: 20 (95.2%)
- **失败**: 1 (4.8%)
- **总耗时**: 111.58s

---

## 📋 详细结果

| ID | 名称 | 状态 | 耗时 | 错误信息 |
|----|------|------|------|----------|
| example_01_canal_flow | 01_basic | ✅ 成功 | 5.48s | - |
| example_01_canal_flow | 02_methods_comparison | ✅ 成功 | 8.57s | - |
| example_01_canal_flow | 05_step_response | ✅ 成功 | 9.38s | - |
| example_02_pump_system | example_02_pump_system_enhanced | ❌ 失败 | 0.93s | Traceback (most recent call last):
  File "/home/u |
| example_02_spillway_cascade | example_02_spillway_system | ✅ 成功 | 0.93s | - |
| example_03_turbine_demo | example_03_turbine_comparison | ✅ 成功 | 1.51s | - |
| example_03_complex_network | example_03_complex_network | ✅ 成功 | 0.60s | - |
| example_04_hydropower_system | example_04_hydropower_plant | ✅ 成功 | 1.44s | - |
| example_05_transient_analysis | example_05_load_rejection | ✅ 成功 | 1.61s | - |
| example_06_complete_hydropower_system | example_06_complete_system | ✅ 成功 | 1.48s | - |
| example_07_multi_unit_agc | example_07_multi_unit_agc | ✅ 成功 | 2.13s | - |
| example_08_load_acceptance | example_08_load_acceptance | ✅ 成功 | 1.62s | - |
| example_08_preissmann_vs_fvm | example_08_preissmann_vs_fvm_enhanced | ✅ 成功 | 8.18s | - |
| example_09_pipe_rk4 | example_09_pipe_rk4_enhanced | ✅ 成功 | 33.44s | - |
| example_10_series_network | example_10_series_network | ✅ 成功 | 0.53s | - |
| example_11_tree_network | example_11_tree_network | ✅ 成功 | 0.53s | - |
| example_12_loop_network | example_12_loop_network | ✅ 成功 | 1.53s | - |
| example_13_adaptive_timescale | example_13_adaptive_timescale_enhanced | ✅ 成功 | 3.81s | - |
| example_14_adaptive_mpc | example_14_adaptive_mpc_enhanced | ✅ 成功 | 5.78s | - |
| example_15_rls_identification | example_15_rls_identification_enhanced | ✅ 成功 | 8.93s | - |
| example_16_weirs_application | weirs_irrigation_system | ✅ 成功 | 13.18s | - |

---

## ✅ 成功的示例

### example_01_canal_flow: 01_basic

- **文件**: `examples/example_01_canal_flow/code/01_basic.py`
- **耗时**: 5.48s

### example_01_canal_flow: 02_methods_comparison

- **文件**: `examples/example_01_canal_flow/code/02_methods_comparison.py`
- **耗时**: 8.57s

### example_01_canal_flow: 05_step_response

- **文件**: `examples/example_01_canal_flow/code/05_step_response.py`
- **耗时**: 9.38s

### example_02_spillway_cascade: example_02_spillway_system

- **文件**: `examples/example_02_spillway_cascade/example_02_spillway_system.py`
- **耗时**: 0.93s
- **输出文件**: 1个
  - `examples/example_02_spillway_cascade/rating_curve.png`

### example_03_turbine_demo: example_03_turbine_comparison

- **文件**: `examples/example_03_turbine_demo/example_03_turbine_comparison.py`
- **耗时**: 1.51s
- **输出文件**: 2个
  - `examples/example_03_turbine_demo/hill_chart.png`
  - `examples/example_03_turbine_demo/turbine_comparison.png`

### example_03_complex_network: example_03_complex_network

- **文件**: `examples/example_03_complex_network/code/example_03_complex_network.py`
- **耗时**: 0.60s

### example_04_hydropower_system: example_04_hydropower_plant

- **文件**: `examples/example_04_hydropower_system/example_04_hydropower_plant.py`
- **耗时**: 1.44s
- **输出文件**: 1个
  - `examples/example_04_hydropower_system/plant_performance.png`

### example_05_transient_analysis: example_05_load_rejection

- **文件**: `examples/example_05_transient_analysis/example_05_load_rejection.py`
- **耗时**: 1.61s
- **输出文件**: 1个
  - `examples/example_05_transient_analysis/load_rejection.png`

### example_06_complete_hydropower_system: example_06_complete_system

- **文件**: `examples/example_06_complete_hydropower_system/example_06_complete_system.py`
- **耗时**: 1.48s
- **输出文件**: 1个
  - `examples/example_06_complete_hydropower_system/complete_system_performance.png`

### example_07_multi_unit_agc: example_07_multi_unit_agc

- **文件**: `examples/example_07_multi_unit_agc/example_07_multi_unit_agc.py`
- **耗时**: 2.13s
- **输出文件**: 3个
  - `examples/example_07_multi_unit_agc/scenario3_tie_line_control.png`
  - `examples/example_07_multi_unit_agc/scenario1_frequency_disturbance.png`
  - `examples/example_07_multi_unit_agc/scenario2_load_variation.png`

### example_08_load_acceptance: example_08_load_acceptance

- **文件**: `examples/example_08_load_acceptance/example_08_load_acceptance.py`
- **耗时**: 1.62s
- **输出文件**: 1个
  - `examples/example_08_load_acceptance/load_acceptance_transient.png`

### example_08_preissmann_vs_fvm: example_08_preissmann_vs_fvm_enhanced

- **文件**: `examples/example_08_preissmann_vs_fvm/example_08_preissmann_vs_fvm_enhanced.py`
- **耗时**: 8.18s

### example_09_pipe_rk4: example_09_pipe_rk4_enhanced

- **文件**: `examples/example_09_pipe_rk4/example_09_pipe_rk4_enhanced.py`
- **耗时**: 33.44s

### example_10_series_network: example_10_series_network

- **文件**: `examples/example_10_series_network/code/example_10_series_network.py`
- **耗时**: 0.53s

### example_11_tree_network: example_11_tree_network

- **文件**: `examples/example_11_tree_network/code/example_11_tree_network.py`
- **耗时**: 0.53s

### example_12_loop_network: example_12_loop_network

- **文件**: `examples/example_12_loop_network/code/example_12_loop_network.py`
- **耗时**: 1.53s

### example_13_adaptive_timescale: example_13_adaptive_timescale_enhanced

- **文件**: `examples/example_13_adaptive_timescale/example_13_adaptive_timescale_enhanced.py`
- **耗时**: 3.81s

### example_14_adaptive_mpc: example_14_adaptive_mpc_enhanced

- **文件**: `examples/example_14_adaptive_mpc/example_14_adaptive_mpc_enhanced.py`
- **耗时**: 5.78s

### example_15_rls_identification: example_15_rls_identification_enhanced

- **文件**: `examples/example_15_rls_identification/example_15_rls_identification_enhanced.py`
- **耗时**: 8.93s

### example_16_weirs_application: weirs_irrigation_system

- **文件**: `examples/example_16_weirs_application/weirs_irrigation_system.py`
- **耗时**: 13.18s

## ❌ 失败的示例

### example_02_pump_system: example_02_pump_system_enhanced

- **文件**: `examples/example_02_pump_system/example_02_pump_system_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "/home/user/HydroClaude/examples/example_02_pump_system/example_02_pump_system_enhanced.py", line 312, in <module>
    run_example()
  File "/home/user/HydroClaude/examples/example_02_pump_system/example_02_pump_system_enhanced.py", line 56, in run_example
    print(f"  泵站: 最大流量={pump.max_flow} m³/s, 额定扬程={pump.rated_head} m")
                              ^^^^^^^^^^^^^
AttributeError: 'Pump' object has no attribute 'max_flow'
```

