# Examples 1-16 测试报告

**生成时间**: 2025-11-13 09:12:44

##  总体统计

- **总示例数**: 21
- **成功**: 4 (19.0%)
- **失败**: 17 (81.0%)
- **总耗时**: 59.64s

---

##  详细结果

| ID | 名称 | 状态 | 耗时 | 错误信息 |
|----|------|------|------|----------|
| example_01_canal_flow | 01_basic |  失败 | 0.00s | File not found |
| example_01_canal_flow | 02_methods_comparison |  失败 | 0.00s | File not found |
| example_01_canal_flow | 05_step_response |  失败 | 0.00s | File not found |
| example_02_pump_system | example_02_pump_system_enhanced |  失败 | 1.85s | Traceback (most recent call last):
  File "E:\OneD |
| example_02_spillway_cascade | example_02_spillway_system |  失败 | 1.31s |     main()
    ~~~~^^
  File "E:\OneDrive\Document |
| example_03_turbine_demo | example_03_turbine_comparison |  失败 | 1.28s |   File "E:\OneDrive\Documents\GitHub\Test\HydroCla |
| example_03_complex_network | example_03_complex_network |  失败 | 0.98s | Traceback (most recent call last):
  File "E:\OneD |
| example_04_hydropower_system | example_04_hydropower_plant |  失败 | 1.26s |   File "E:\OneDrive\Documents\GitHub\Test\HydroCla |
| example_05_transient_analysis | example_05_load_rejection |  失败 | 1.21s |   File "E:\OneDrive\Documents\GitHub\Test\HydroCla |
| example_06_complete_hydropower_system | example_06_complete_system |  失败 | 1.14s |   File "E:\OneDrive\Documents\GitHub\Test\HydroCla |
| example_07_multi_unit_agc | example_07_multi_unit_agc |  成功 | 4.02s | - |
| example_08_load_acceptance | example_08_load_acceptance |  失败 | 1.13s | Traceback (most recent call last):
  File "E:\OneD |
| example_08_preissmann_vs_fvm | example_08_preissmann_vs_fvm_enhanced |  失败 | 2.19s |   File "E:\OneDrive\Documents\GitHub\Test\HydroCla |
| example_09_pipe_rk4 | example_09_pipe_rk4_enhanced |  失败 | 1.73s |   File "E:\OneDrive\Documents\GitHub\Test\HydroCla |
| example_10_series_network | example_10_series_network |  失败 | 0.94s | Traceback (most recent call last):
  File "E:\OneD |
| example_11_tree_network | example_11_tree_network |  失败 | 0.97s | Traceback (most recent call last):
  File "E:\OneD |
| example_12_loop_network | example_12_loop_network |  失败 | 2.37s |   File "E:\OneDrive\Documents\GitHub\Test\HydroCla |
| example_13_adaptive_timescale | example_13_adaptive_timescale_enhanced |  成功 | 7.15s | - |
| example_14_adaptive_mpc | example_14_adaptive_mpc_enhanced |  成功 | 10.58s | - |
| example_15_rls_identification | example_15_rls_identification_enhanced |  成功 | 18.12s | - |
| example_16_weirs_application | weirs_irrigation_system |  失败 | 1.41s | Traceback (most recent call last):
  File "E:\OneD |

---

##  成功的示例

### example_07_multi_unit_agc: example_07_multi_unit_agc

- **文件**: `examples/example_07_multi_unit_agc/example_07_multi_unit_agc.py`
- **耗时**: 4.02s
- **输出文件**: 3个
  - `examples\example_07_multi_unit_agc\scenario1_frequency_disturbance.png`
  - `examples\example_07_multi_unit_agc\scenario2_load_variation.png`
  - `examples\example_07_multi_unit_agc\scenario3_tie_line_control.png`

### example_13_adaptive_timescale: example_13_adaptive_timescale_enhanced

- **文件**: `examples/example_13_adaptive_timescale/example_13_adaptive_timescale_enhanced.py`
- **耗时**: 7.15s

### example_14_adaptive_mpc: example_14_adaptive_mpc_enhanced

- **文件**: `examples/example_14_adaptive_mpc/example_14_adaptive_mpc_enhanced.py`
- **耗时**: 10.58s

### example_15_rls_identification: example_15_rls_identification_enhanced

- **文件**: `examples/example_15_rls_identification/example_15_rls_identification_enhanced.py`
- **耗时**: 18.12s

##  失败的示例

### example_01_canal_flow: 01_basic

- **文件**: `examples/example_01_canal_flow/code/01_basic.py`
- **错误**:
```
File not found
```

### example_01_canal_flow: 02_methods_comparison

- **文件**: `examples/example_01_canal_flow/code/02_methods_comparison.py`
- **错误**:
```
File not found
```

### example_01_canal_flow: 05_step_response

- **文件**: `examples/example_01_canal_flow/code/05_step_response.py`
- **错误**:
```
File not found
```

### example_02_pump_system: example_02_pump_system_enhanced

- **文件**: `examples/example_02_pump_system/example_02_pump_system_enhanced.py`
- **错误**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_pump_system\example_02_pump_system_enhanced.py", line 312, in <module>
    run_example()
    ~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_pump_system\example_02_pump_system_enhanced.py", line 54, in run_example
    print(f"  水池1: 面积={tank1.area} m\xb2, 容量范围=[{tank1.volume_min}, {tank1.volume_max}] m\xb3")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb2' in position 15: illegal multibyte sequence
```

### example_02_spillway_cascade: example_02_spillway_system

- **文件**: `examples/example_02_spillway_cascade/example_02_spillway_system.py`
- **错误**:
```
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_spillway_cascade\example_02_spillway_system.py", line 283, in main
    system.print_results(results)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_spillway_cascade\example_02_spillway_system.py", line 182, in print_results
    print(f"Average Flow:     {results['average_flow']:.2f} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 28: illegal multibyte sequence
```

### example_03_turbine_demo: example_03_turbine_comparison

- **文件**: `examples/example_03_turbine_demo/example_03_turbine_comparison.py`
- **错误**:
```
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_turbine_demo\example_03_turbine_comparison.py", line 374, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_turbine_demo\example_03_turbine_comparison.py", line 328, in main
    francis_data = demo_francis_turbine()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_turbine_demo\example_03_turbine_comparison.py", line 51, in demo_francis_turbine
    print(f"\n{francis}")
    ~~~~~^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 73: illegal multibyte sequence
```

### example_03_complex_network: example_03_complex_network

- **文件**: `examples/example_03_complex_network/code/example_03_complex_network.py`
- **错误**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_complex_network\code\example_03_complex_network.py", line 47, in <module>
    run_example()
    ~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_complex_network\code\example_03_complex_network.py", line 44, in run_example
    print(f"  {edge_id}: {flow:.2f} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 13: illegal multibyte sequence
```

### example_04_hydropower_system: example_04_hydropower_plant

- **文件**: `examples/example_04_hydropower_system/example_04_hydropower_plant.py`
- **错误**:
```
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_04_hydropower_system\example_04_hydropower_plant.py", line 384, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_04_hydropower_system\example_04_hydropower_plant.py", line 313, in main
    plant = HydropowerPlant()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_04_hydropower_system\example_04_hydropower_plant.py", line 111, in __init__
    print(f"Surge tank:         {self.surge_tank}")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb2' in position 66: illegal multibyte sequence
```

### example_05_transient_analysis: example_05_load_rejection

- **文件**: `examples/example_05_transient_analysis/example_05_load_rejection.py`
- **错误**:
```
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_05_transient_analysis\example_05_load_rejection.py", line 441, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_05_transient_analysis\example_05_load_rejection.py", line 380, in main
    simulator = HydropowerTransientSimulator()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_05_transient_analysis\example_05_load_rejection.py", line 114, in __init__
    print(f"Turbine:        {self.turbine}")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 87: illegal multibyte sequence
```

### example_06_complete_hydropower_system: example_06_complete_system

- **文件**: `examples/example_06_complete_hydropower_system/example_06_complete_system.py`
- **错误**:
```
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_06_complete_hydropower_system\example_06_complete_system.py", line 452, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_06_complete_hydropower_system\example_06_complete_system.py", line 404, in main
    system = CompleteHydropowerSystem()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_06_complete_hydropower_system\example_06_complete_system.py", line 165, in __init__
    print(f"{'Headrace Tunnel':<25} L={self.tunnel['length']/1000:.1f} km, \xd8{self.tunnel['diameter']:.1f} m, ε={self.tunnel['roughness']*1000:.1f} mm")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xd8' in position 36: illegal multibyte sequence
```

### example_08_load_acceptance: example_08_load_acceptance

- **文件**: `examples/example_08_load_acceptance/example_08_load_acceptance.py`
- **错误**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_load_acceptance\example_08_load_acceptance.py", line 445, in <module>
    results = run_load_acceptance_simulation()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_load_acceptance\example_08_load_acceptance.py", line 264, in run_load_acceptance_simulation
    sim = LoadAcceptanceSimulator()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_load_acceptance\example_08_load_acceptance.py", line 83, in __init__
    print(f"   Rated flow: {self.turbine.rated_flow:.1f} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 21: illegal multibyte sequence
```

### example_08_preissmann_vs_fvm: example_08_preissmann_vs_fvm_enhanced

- **文件**: `examples/example_08_preissmann_vs_fvm/example_08_preissmann_vs_fvm_enhanced.py`
- **错误**:
```
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_preissmann_vs_fvm\example_08_preissmann_vs_fvm_enhanced.py", line 546, in <module>
    example_preissmann_vs_fvm()
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_preissmann_vs_fvm\example_08_preissmann_vs_fvm_enhanced.py", line 64, in example_preissmann_vs_fvm
    print(f"  步 {step+1}/{n_steps}: 水位={canal_p.state.level:.3f}m, "
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          f"流量={canal_p.state.flow:.3f}m\xb3/s")
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 31: illegal multibyte sequence
```

### example_09_pipe_rk4: example_09_pipe_rk4_enhanced

- **文件**: `examples/example_09_pipe_rk4/example_09_pipe_rk4_enhanced.py`
- **错误**:
```
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_09_pipe_rk4\example_09_pipe_rk4_enhanced.py", line 540, in <module>
    example_pipe_rk4()
    ~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_09_pipe_rk4\example_09_pipe_rk4_enhanced.py", line 78, in example_pipe_rk4
    print(f"  步 {step+1}/{n_steps}: 时间={step*dt:.1f}s, "
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          f"压力={state.pressure:.2f}m, 流量={state.flow:.3f}m\xb3/s")
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 40: illegal multibyte sequence
```

### example_10_series_network: example_10_series_network

- **文件**: `examples/example_10_series_network/code/example_10_series_network.py`
- **错误**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_10_series_network\code\example_10_series_network.py", line 48, in <module>
    example_series_network()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_10_series_network\code\example_10_series_network.py", line 45, in example_series_network
    print(f"  {edge_id}: {flow:.2f} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 13: illegal multibyte sequence
```

### example_11_tree_network: example_11_tree_network

- **文件**: `examples/example_11_tree_network/code/example_11_tree_network.py`
- **错误**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_11_tree_network\code\example_11_tree_network.py", line 55, in <module>
    example_tree_network()
    ~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_11_tree_network\code\example_11_tree_network.py", line 52, in example_tree_network
    print(f"  {edge_id}: {edge.flow:.2f} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 13: illegal multibyte sequence
```

### example_12_loop_network: example_12_loop_network

- **文件**: `examples/example_12_loop_network/code/example_12_loop_network.py`
- **错误**:
```
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\coupled_solver.py", line 22, in solve_timestep
    return self._solve_loop_network_hardy_cross(dt)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\coupled_solver.py", line 125, in _solve_loop_network_hardy_cross
    flows = hardy_cross.solve(self.topology, head_loss)
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\hardy_cross.py", line 36, in solve
    print(f"  : {max_correction:.6f} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 14: illegal multibyte sequence
```

### example_16_weirs_application: weirs_irrigation_system

- **文件**: `examples/example_16_weirs_application/weirs_irrigation_system.py`
- **错误**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_16_weirs_application\weirs_irrigation_system.py", line 436, in <module>
    run_irrigation_system_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_16_weirs_application\weirs_irrigation_system.py", line 115, in run_irrigation_system_simulation
    solver = SingleCanalSolver(
             ^^^^^^^^^^^^^^^^^
NameError: name 'SingleCanalSolver' is not defined
```

