# Batch Test Report - 批量测试报告

**Generated:** 2025-11-13 11:48:19

---

## Summary / 总结

- **Total Cases / 总案例数:** 541
- **Passed / 通过:** 267 (49.4%)
- **Failed / 失败:** 273 (50.5%)
- **Error / 错误:** 1 (0.2%)
- **Total Duration / 总耗时:** 4155.6s (69.3min)
- **Start Time / 开始时间:** 2025-11-13 10:39:03
- **End Time / 结束时间:** 2025-11-13 11:48:19

---

## Results by Category / 按分类统计

| Category | Total | Passed | Failed | Error | Pass Rate |
|----------|-------|--------|--------|-------|----------|
| examples | 249 | 116 | 132 | 1 | 46.6% |
| tests | 270 | 143 | 127 | 0 | 53.0% |
| validation_cases | 22 | 8 | 14 | 0 | 36.4% |

---

## Failed Cases / 失败案例

### [FAILED] 性能基准测试：牛顿法 vs 迭代法

- **ID:** `tests-benchmark_newton_vs_iterative`
- **Duration:** 1.89s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\benchmark_newton_vs_iterative.py", line 359, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\benchmark_newton_vs_iterative.py", line 228, in main
    all_results['single_gate'] = benchmark_scenario(
                                 ~~~~~~~~~~~~~~~~~~^
        name="单闸门",
        ^^^^^^^^^^^^^^
    ...<6 lines>...
        structures_config=[(500.0, gate1)]
 
```

### [FAILED] Riemann求解器性能基准测试

- **ID:** `tests-benchmark_riemann_solvers`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 核心功能验证测试

- **ID:** `tests-core_functionality_verification`
- **Duration:** 6.01s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_solver.py:555: RuntimeWarning: invalid value encountered in multiply
  h_star = h_n + dt * dh_dt
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_solver.py:556: RuntimeWarning: invalid value encountered in multiply
  Q_star = Q_n + dt * dQ_dt
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_solver.py:490: RuntimeWarning: invalid value encountered in scalar divide
  u = self.Q[i] / A
E:\OneDrive\Do
```

### [FAILED] 诊断精确Riemann求解器通量计算

- **ID:** `tests-debug_exact_flux`
- **Duration:** 5.22s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\debug_exact_flux.py:99: UserWarning: 
================================================================================
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO N
```

### [FAILED] 逐步通量诊断 - 精确求解器

- **ID:** `tests-diagnose_exact_flux_step_by_step`
- **Duration:** 1.86s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnose_exact_flux_step_by_step.py", line 208, in <module>
    single_step_flux_analysis()
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnose_exact_flux_step_by_step.py", line 102, in single_step_flux_analysis
    from solvers.riemann_hll import hll_riemann_flux
ModuleNotFoundError: No module named 'solvers.riemann_hll'

```

### [FAILED] 特征线边界条件单元测试

- **ID:** `tests-test_boundary_conditions`
- **Duration:** 0.14s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_boundary_conditions.py", line 22
    except ImportError as e:
    ^^^^^^
SyntaxError: invalid syntax

```

### [FAILED] 测试边界条件修复：验证Jacobian非奇异性

- **ID:** `tests-test_boundary_condition_fix`
- **Duration:** 2.17s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_boundary_condition_fix.py", line 272, in test_newton_convergence_with_gate
    print(f"  最终残差: {info['final_residual']:.2e}")
                         ~~~~^^^^^^^^^^^^^^^^^^
KeyError: 'final_residual'

```

### [FAILED] Controllers

- **ID:** `tests-test_controllers`
- **Duration:** 2.94s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_controllers.py", line 4, in <module>
    from control.pid_controller import PIDController, PIDConfig
ModuleNotFoundError: No module named 'control.pid_controller'

```

### [FAILED] 测试断面类集成到求解器

- **ID:** `tests-test_cross_section_integration`
- **Duration:** 2.22s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_cross_section_integration.py:36: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WA
```

### [FAILED] 测试断面类集成到求解器（简化版，无需pytest）

- **ID:** `tests-test_cross_section_integration_simple`
- **Duration:** 2.21s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_cross_section_integration_simple.py:38: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balance
```

### [FAILED] 验证CFL=0.1时精确求解器的表现

- **ID:** `tests-test_exact_cfl_01_validation`
- **Duration:** 9.84s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_exact_cfl_01_validation.py:42: UserWarning: 
================================================================================
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
```

### [FAILED] 精确Riemann求解器Lake at Rest测试

- **ID:** `tests-test_exact_lake_at_rest`
- **Duration:** 5.10s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_exact_lake_at_rest.py:87: UserWarning: 
================================================================================
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
   - DO NOT USE  
=
  
```

### [FAILED] 测试HLLC求解器在Lake at Rest问题上的表现

- **ID:** `tests-test_hllc_lake_at_rest`
- **Duration:** 19.99s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_hllc_lake_at_rest.py:115: UserWarning: 
================================================================================
[WARN][WARN][WARN]  HLLC - NOT PRODUCTION READY  [WARN][WARN][WARN]
=
[WARN][WARN][WARN]  HLLC - NOT PRODUCTION READY  [WARN][WARN][WARN]
=
[WARN][WARN][WARN]  HLLC - NOT PRODUCTION READY  [WARN][WARN][WARN]
=
[WARN][WARN][WARN]  HLLC - NOT PRODUCTION READY  [WARN][WARN][WARN]
=
[WARN][WARN][WARN]  HLLC - NOT PRODUCTION 
```

### [FAILED] HLL vs HLLC Riemann求解器对比测试

- **ID:** `tests-test_hll_vs_hllc`
- **Duration:** 1.92s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_hll_vs_hllc.py:54: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Bala
```

### [FAILED] 冰-水质模拟模块测试套件

- **ID:** `tests-test_ice_water_quality`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_ice_water_quality.py", line 29
    except ImportError as e:
    ^^^^^^
SyntaxError: invalid syntax

```

### [FAILED] Lake at Rest Test with Well-Balanced Format

- **ID:** `tests-test_lake_at_rest_wb`
- **Duration:** 11.63s
- **Error:**
```
Exit code: 1
```

### [FAILED] 网络集成测试套件

- **ID:** `tests-test_network_integration`
- **Duration:** 2.88s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_network_integration.py:49: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  W
```

### [FAILED] 简单测试内部水工建筑物（不使用pytest）

- **ID:** `tests-test_network_structures_simple`
- **Duration:** 6.50s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_network_structures_simple.py:37: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WA
```

### [FAILED] 测试牛顿法边界条件修复效果

- **ID:** `tests-test_newton_boundary_fix`
- **Duration:** 2.53s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_newton_boundary_fix.py", line 333, in test_newton_with_gate
    U_solution, info = solver.solve(
                       ~~~~~~~~~~~~^
        U_init,
        ^^^^^^^
        system.compute_residual,
        ^^^^^^^^^^^^^^^^^^^^^^^^
        system.compute_jacobian
        ^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\newton_solver.py", line 167, i
```

### [FAILED] 有压系统单元测试

- **ID:** `tests-test_pressurized_system`
- **Duration:** 0.66s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_pressurized_system.py", line 21, in <module>
    from core.pressurized_solver import PressurizedFlowSolver, PipelineConfig
ModuleNotFoundError: No module named 'core'

```

### [FAILED] 水库组件测试

- **ID:** `tests-test_reservoir`
- **Duration:** 0.36s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_reservoir.py", line 15, in <module>
    from physics.reservoir import Reservoir, ReservoirState, create_reservoir_from_config
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] Riemann求解器单元测试

- **ID:** `tests-test_riemann_solvers`
- **Duration:** 3.02s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_riemann_solvers.py", line 319, in <module>
    success = run_all_tests()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_riemann_solvers.py", line 303, in run_all_tests
    test_mass_conservation()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_riemann_solvers.py", line 158, in test_mass_conservation
    solver.step()
    ~~~~~~~~~~~^
```

### [FAILED] 对比两种初始化方式的差异

- **ID:** `tests-diagnostic-compare_initialization`
- **Duration:** 0.18s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\compare_initialization.py", line 17, in <module>
    from engine.model_builder import ModelBuilder
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] 在33秒时对比两种方法的完整状态

- **ID:** `tests-diagnostic-compare_state_at_33s`
- **Duration:** 0.17s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\compare_state_at_33s.py", line 17, in <module>
    from engine.model_builder import ModelBuilder
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] 单步调试：在35秒前后详细追踪每一步

- **ID:** `tests-diagnostic-debug_step_by_step`
- **Duration:** 0.32s
- **Error:**
```
Exit code: 1
```

### [FAILED] WENO3性能分析工具

- **ID:** `tests-diagnostic-profile_weno3_performance`
- **Duration:** 5.21s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\..\..\solvers\godunov_fvm_weno3.py:78: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Ba
```

### [FAILED] 快速测试 n=0.02 工况

- **ID:** `tests-diagnostic-quick_test_n002`
- **Duration:** 0.39s
- **Error:**
```
Exit code: 1
```

### [FAILED] 自适应时间步性能测试

- **ID:** `tests-diagnostic-test_adaptive_timestep`
- **Duration:** 1.47s
- **Error:**
```
Exit code: 1
```

### [FAILED] 高级功能综合测试

- **ID:** `tests-diagnostic-test_advanced_features`
- **Duration:** 1.39s
- **Error:**
```
Exit code: 1
```

### [FAILED] 自动测试所有示例（Examples 1-16）

- **ID:** `tests-diagnostic-test_all_examples`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 所有水工结构类型的综合测试

- **ID:** `tests-diagnostic-test_all_structures`
- **Duration:** 1.37s
- **Error:**
```
Exit code: 1
```

### [FAILED] Anderson加速性能验证测试

- **ID:** `tests-diagnostic-test_anderson_performance`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_anderson_performance.py", line 543
    report += f"try:
              ^
SyntaxError: unterminated f-string literal (detected at line 543)

```

### [FAILED] 边界条件强制机制诊断测试

- **ID:** `tests-diagnostic-test_boundary_enforcement`
- **Duration:** 0.64s
- **Error:**
```
Exit code: 1
```

### [FAILED] 渠系网络测试案例

- **ID:** `tests-diagnostic-test_canal_network`
- **Duration:** 1.50s
- **Error:**
```
Exit code: 1
```

### [FAILED] CFL敏感性测试 - 找出无摩阻Test 4的稳定CFL数

- **ID:** `tests-diagnostic-test_cfl_sensitivity`
- **Duration:** 0.37s
- **Error:**
```
Exit code: 1
```

### [FAILED] HydroClaude综合系统测试

- **ID:** `tests-diagnostic-test_comprehensive_system`
- **Duration:** 0.34s
- **Error:**
```
Exit code: 1
```

### [FAILED] 测试配置驱动的supercritical边界条件

- **ID:** `tests-diagnostic-test_config_supercritical`
- **Duration:** 0.41s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_config_supercritical.py", line 18, in <module>
    from engine.simulation_engine import SimulationEngine
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] 测试dt_max功能

- **ID:** `tests-diagnostic-test_dt_max_feature`
- **Duration:** 0.38s
- **Error:**
```
Exit code: 1
```

### [FAILED] 测试平坦底床的良平衡性

- **ID:** `tests-diagnostic-test_flat_bed`
- **Duration:** 0.40s
- **Error:**
```
Exit code: 1
```

### [FAILED] 测试洪水过程线模拟 - Phase 1问题修复

- **ID:** `tests-diagnostic-test_flood_hydrograph`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
```

### [FAILED] 简化闸门测试 - FVM求解器

- **ID:** `tests-diagnostic-test_fvm_simple_gate`
- **Duration:** 1.58s
- **Error:**
```
Exit code: 1
```

### [FAILED] FVM求解器验证测试

- **ID:** `tests-diagnostic-test_fvm_validation`
- **Duration:** 1.50s
- **Error:**
```
Exit code: 1
```

### [FAILED] FVM求解器闸门测试

- **ID:** `tests-diagnostic-test_fvm_with_gate`
- **Duration:** 1.48s
- **Error:**
```
Exit code: 1
```

### [FAILED] Godunov-FVM求解器 - Dam Break完整验证

- **ID:** `tests-diagnostic-test_godunov_dam_break`
- **Duration:** 1.35s
- **Error:**
```
Exit code: 1
```

### [FAILED] Godunov-FVM - MacDonald Test Case 1验证

- **ID:** `tests-diagnostic-test_godunov_macdonald`
- **Duration:** 1.31s
- **Error:**
```
Exit code: 1
```

### [FAILED] Godunov-FVM - 稳态均匀流验证

- **ID:** `tests-diagnostic-test_godunov_steady_uniform`
- **Duration:** 1.40s
- **Error:**
```
Exit code: 1
```

### [FAILED] Godunov-FVM + 闸门集成测试

- **ID:** `tests-diagnostic-test_godunov_with_gate`
- **Duration:** 1.35s
- **Error:**
```
Exit code: 1
```

### [FAILED] 高阶格式精度验证测试

- **ID:** `tests-diagnostic-test_high_order_accuracy`
- **Duration:** 1.26s
- **Error:**
```
Exit code: 1
```

### [FAILED] HLL vs HLLC性能对比测试

- **ID:** `tests-diagnostic-test_hllc_comparison`
- **Duration:** 0.35s
- **Error:**
```
Exit code: 1
```

### [FAILED] HLLC vs HLL完整对比测试

- **ID:** `tests-diagnostic-test_hllc_vs_hll_comparison`
- **Duration:** 1.25s
- **Error:**
```
Exit code: 1
```

### [FAILED] 水跃初始条件测试 - 用包含水跃的初场替代线性初场

- **ID:** `tests-diagnostic-test_jump_initial_condition`
- **Duration:** 0.30s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacCormack v2.0 - Dam Break验证

- **ID:** `tests-diagnostic-test_maccormack_dam_break`
- **Duration:** 1.39s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacCormack v3.0 Dam Break测试（带HLL+TVD）

- **ID:** `tests-diagnostic-test_maccormack_v3_dam_break`
- **Duration:** 1.39s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 4 对比测试：标准WENO3 vs 增强WENO3

- **ID:** `tests-diagnostic-test_macdonald4_comparison`
- **Duration:** 2.05s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald4_comparison.py", line 369, in <module>
    results_standard = run_test("标准WENO3", weno3_enhanced=False)
                       ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald4_comparison.py", line 155, in run_test
    engine.initialize()
    ~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHu
```

### [FAILED] MacDonald Test 4 (水跃) 诊断测试

- **ID:** `tests-diagnostic-test_macdonald4_diagnosis`
- **Duration:** 0.33s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 4 - 增强版WENO3测试

- **ID:** `tests-diagnostic-test_macdonald4_enhanced_weno3`
- **Duration:** 2.09s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald4_enhanced_weno3.py", line 338, in <module>
    test_macdonald4_enhanced_weno3()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald4_enhanced_weno3.py", line 179, in test_macdonald4_enhanced_weno3
    engine.initialize()
    ~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\engine\si
```

### [FAILED] MacDonald Test 4简化测试 - 终极诊断

- **ID:** `tests-diagnostic-test_macdonald4_final`
- **Duration:** 0.19s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald4_final.py", line 17, in <module>
    from engine.simulation_engine import SimulationEngine
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] MacDonald Test 4 - 最终验证（WENO3，正确参数）

- **ID:** `tests-diagnostic-test_macdonald4_final_weno3`
- **Duration:** 0.41s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 4 - 极细网格测试

- **ID:** `tests-diagnostic-test_macdonald4_fine_grid`
- **Duration:** 2.26s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald4_fine_grid.py", line 311, in <module>
    success = test_macdonald4_fine_grid()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald4_fine_grid.py", line 160, in test_macdonald4_fine_grid
    engine.initialize()  # ⭐ 添加初始化步骤
    ~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\engine\simulation_engine.py", line 77, in i
```

### [FAILED] MacDonald Test 4 - HLLC低耗散求解器测试

- **ID:** `tests-diagnostic-test_macdonald4_hllc`
- **Duration:** 0.33s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 4 快速验证 - WENO3

- **ID:** `tests-diagnostic-test_macdonald4_quick_weno3`
- **Duration:** 3.50s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\..\..\solvers\godunov_fvm_weno3.py:377: RuntimeWarning: overflow encountered in square
  alpha1_L = d1 / (eps + beta1_L)**2
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\..\..\solvers\godunov_fvm_weno3.py:378: RuntimeWarning: overflow encountered in square
  alpha2_L = d2 / (eps + beta2_L)**2
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\..\..\solvers\godunov_fvm_weno3.py:381: RuntimeWarning: invalid
```

### [FAILED] MacDonald Test 4 - 超细网格测试（直接使用求解器）

- **ID:** `tests-diagnostic-test_macdonald4_ultra_fine_grid`
- **Duration:** 9.74s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\..\..\solvers\godunov_fvm_weno3.py:377: RuntimeWarning: overflow encountered in square
  alpha1_L = d1 / (eps + beta1_L)**2
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\..\..\solvers\godunov_fvm_weno3.py:378: RuntimeWarning: overflow encountered in square
  alpha2_L = d2 / (eps + beta2_L)**2
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\..\..\solvers\godunov_fvm_weno3.py:381: RuntimeWarning: invalid
```

### [FAILED] MacDonald Test 4 - WENO5高阶格式测试

- **ID:** `tests-diagnostic-test_macdonald4_weno5`
- **Duration:** 0.33s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 5 精度改进诊断

- **ID:** `tests-diagnostic-test_macdonald5_accuracy`
- **Duration:** 0.37s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 5 诊断测试

- **ID:** `tests-diagnostic-test_macdonald5_diagnosis`
- **Duration:** 0.34s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 5 时间步长限制测试

- **ID:** `tests-diagnostic-test_macdonald5_dt_limit`
- **Duration:** 0.34s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 5 时间步长演化追踪

- **ID:** `tests-diagnostic-test_macdonald5_dt_trace`
- **Duration:** 0.36s
- **Error:**
```
Exit code: 1
```

### [FAILED] MacDonald Test 5 完整测试

- **ID:** `tests-diagnostic-test_macdonald5_full`
- **Duration:** 0.44s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_macdonald5_full.py", line 17, in <module>
    from engine.simulation_engine import SimulationEngine
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] MacDonald Test 5 稳定性诊断

- **ID:** `tests-diagnostic-test_macdonald5_stability`
- **Duration:** 0.37s
- **Error:**
```
Exit code: 1
```

### [FAILED] Manning摩阻项诊断测试

- **ID:** `tests-diagnostic-test_manning_friction`
- **Duration:** 0.66s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_manning_friction.py", line 20, in <module>
    from engine.simulation_engine import SimulationEngine
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] 检查Preis

- **ID:** `tests-diagnostic-test_matrix_structure`
- **Duration:** 0.33s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_matrix_structure.py", line 13, in <module>
    from physics.numerical_methods.legacy_preissmann.preissmann_solver_v2 import PreissmannSolverV2
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] MPC智能调度测试

- **ID:** `tests-diagnostic-test_mpc_scheduler`
- **Duration:** 1.29s
- **Error:**
```
Exit code: 1
```

### [FAILED] MUSCL性能测试 - Dam Break

- **ID:** `tests-diagnostic-test_muscl_dambreak`
- **Duration:** 1.26s
- **Error:**
```
Exit code: 1
```

### [FAILED] 简单测试MUSCL重构

- **ID:** `tests-diagnostic-test_muscl_simple`
- **Duration:** 0.32s
- **Error:**
```
Exit code: 1
```

### [FAILED] MUSCL + 正确CFL测试

- **ID:** `tests-diagnostic-test_muscl_with_correct_cfl`
- **Duration:** 1.31s
- **Error:**
```
Exit code: 1
```

### [FAILED] 测试网络求解器V2 - Y-split简单测试

- **ID:** `tests-diagnostic-test_network_v2_simple`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
```

### [FAILED] 测试网络求解器V2 - 最简单串联测试

- **ID:** `tests-diagnostic-test_network_v2_串联`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
```

### [FAILED] Preissmann v4.0 扩展测试

- **ID:** `tests-diagnostic-test_preissmann_v4_extended`
- **Duration:** 0.38s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_preissmann_v4_extended.py", line 14, in <module>
    from physics.numerical_methods.legacy_preissmann.preissmann_solver_v4_linear import PreissmannSolverV4Linear
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] 测试泵站源项是否正确工作

- **ID:** `tests-diagnostic-test_pump_source_term`
- **Duration:** 0.33s
- **Error:**
```
Exit code: 1
```

### [FAILED] 实际工况综合测试

- **ID:** `tests-diagnostic-test_realistic_cases`
- **Duration:** 1.40s
- **Error:**
```
Exit code: 1
```

### [FAILED] RK时间积分性能测试 - Dam Break

- **ID:** `tests-diagnostic-test_rk_dambreak`
- **Duration:** 1.22s
- **Error:**
```
Exit code: 1
```

### [FAILED] 最小化SimulationEngine测试 - 去除所有输出逻辑

- **ID:** `tests-diagnostic-test_simulation_engine_minimal`
- **Duration:** 0.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_simulation_engine_minimal.py", line 17, in <module>
    from engine.model_builder import ModelBuilder
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] 测试单个渠道 + 闸门的稳态求解

- **ID:** `tests-diagnostic-test_single_canal_with_gate`
- **Duration:** 15.68s
- **Error:**
```
Exit code: 1
```

### [FAILED] 小摩阻系数测试 - 用极小摩阻替代完全无摩阻

- **ID:** `tests-diagnostic-test_small_friction`
- **Duration:** 0.32s
- **Error:**
```
Exit code: 1
```

### [FAILED] 测试静水重构法：凸起上的稳态流

- **ID:** `tests-diagnostic-test_steady_flow_over_bump`
- **Duration:** 5.53s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_steady_flow_over_bump.py:204: UserWarning: Glyph 39640 (\N{CJK UNIFIED IDEOGRAPH-9AD8}) missing from font(s) DejaVu Sans.
  plt.tight_layout()
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_steady_flow_over_bump.py:204: UserWarning: Glyph 31243 (\N{CJK UNIFIED IDEOGRAPH-7A0B}) missing from font(s) DejaVu Sans.
  plt.tight_layout()
E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_steady_flo
```

### [FAILED] 对比两种step()调用方式

- **ID:** `tests-diagnostic-test_step_with_and_without_dt`
- **Duration:** 0.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\diagnostic\test_step_with_and_without_dt.py", line 19, in <module>
    from engine.model_builder import ModelBuilder
ModuleNotFoundError: No module named 'engine'

```

### [FAILED] 测试supercritical边界条件是否正确工作

- **ID:** `tests-diagnostic-test_supercritical_bc`
- **Duration:** 0.30s
- **Error:**
```
Exit code: 1
```

### [FAILED] 测试超临界流稳定性 - Phase 1问题修复

- **ID:** `tests-diagnostic-test_supercritical_flow`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
```

### [FAILED] 瞬态流测试 - 验证HydrostaticCanalSolver的瞬态演化功能

- **ID:** `tests-diagnostic-test_transient_flow`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 测试静水重构的良平衡性质

- **ID:** `tests-diagnostic-test_well_balanced`
- **Duration:** 0.33s
- **Error:**
```
Exit code: 1
```

### [FAILED] Well-Balanced Godunov-FVM完整验证

- **ID:** `tests-diagnostic-test_well_balanced_complete`
- **Duration:** 1.25s
- **Error:**
```
Exit code: 1
```

### [FAILED] WENO epsilon敏感性测试 - 增加数值耗散

- **ID:** `tests-diagnostic-test_weno_epsilon_sensitivity`
- **Duration:** 0.30s
- **Error:**
```
Exit code: 1
```

### [FAILED] 精细调优的自适应smooth_weight测试

- **ID:** `tests-legacy_diagnostic-test_adaptive_fine_tuned`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_adaptive_fine_tuned.py", line 21
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 16

```

### [FAILED] 测试优化的自适应网格参数

- **ID:** `tests-legacy_diagnostic-test_adaptive_grid_optimized`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_adaptive_grid_optimized.py", line 23
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 18

```

### [FAILED] 测试自适应网格求解器

- **ID:** `tests-legacy_diagnostic-test_adaptive_grid_solver`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_adaptive_grid_solver.py", line 23
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 18

```

### [FAILED] 自适应平滑权重测试脚本

- **ID:** `tests-legacy_diagnostic-test_adaptive_smooth_weight`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_adaptive_smooth_weight.py", line 25
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 20

```

### [FAILED] Anderson vs Aitken 加速方法性能对比测试

- **ID:** `tests-legacy_diagnostic-test_anderson_vs_aitken`
- **Duration:** 1.00s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_anderson_vs_aitken.py", line 41, in <module>
    from solvers.fixed_point_iteration import (
    ...<3 lines>...
    )
ModuleNotFoundError: No module named 'solvers.fixed_point_iteration'

```

### [FAILED] 数字孪生测试

- **ID:** `tests-legacy_diagnostic-test_digital_twin`
- **Duration:** 1.27s
- **Error:**
```
Exit code: 1
```

### [FAILED] 闸门精度最终优化测试

- **ID:** `tests-legacy_diagnostic-test_final_optimization`
- **Duration:** 0.11s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_final_optimization.py", line 21
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 16

```

### [FAILED] 快速测试修复后的求解器

- **ID:** `tests-legacy_diagnostic-test_fixes_quick`
- **Duration:** 0.15s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_fixes_quick.py", line 20
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 15

```

### [FAILED] FVM-FDM对比测试

- **ID:** `tests-legacy_diagnostic-test_fvm_fdm_comparison`
- **Duration:** 0.16s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_fvm_fdm_comparison.py", line 32
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 27

```

### [FAILED] 完整FVM隐式求解器 - 最终测试

- **ID:** `tests-legacy_diagnostic-test_fvm_full_final`
- **Duration:** 0.14s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_fvm_full_final.py", line 28
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 23

```

### [FAILED] FVM稳态求解器对比测试

- **ID:** `tests-legacy_diagnostic-test_fvm_steady_comparison`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_fvm_steady_comparison.py", line 25
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 20

```

### [FAILED] 网格加密全面测试

- **ID:** `tests-legacy_diagnostic-test_grid_comprehensive`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_grid_comprehensive.py", line 24
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 19

```

### [FAILED] 局部网格加密测试

- **ID:** `tests-legacy_diagnostic-test_grid_refinement`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_grid_refinement.py", line 21
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 16

```

### [FAILED] 高精度求解器测试

- **ID:** `tests-legacy_diagnostic-test_high_precision_solver`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_high_precision_solver.py", line 17
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 12

```

### [FAILED] 性能对比测试

- **ID:** `tests-legacy_diagnostic-test_performance_comparison`
- **Duration:** 1.27s
- **Error:**
```
Exit code: 1
```

### [FAILED] Phase 2高精度求解器验证脚本

- **ID:** `tests-legacy_diagnostic-test_phase2_solver`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_phase2_solver.py", line 22
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 17

```

### [FAILED] 测试SWMM风格omega=0.5的效果

- **ID:** `tests-legacy_diagnostic-test_swmm_omega`
- **Duration:** 0.11s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\legacy_diagnostic\test_swmm_omega.py", line 19
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 14

```

### [FAILED] WENO3空间收敛性验证测试

- **ID:** `tests-numerical_methods-test_convergence`
- **Duration:** 2.05s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\numerical_methods\test_convergence.py", line 434, in <module>
    test.test_weno3_convergence_rate_smooth_wave()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\numerical_methods\test_convergence.py", line 130, in test_weno3_convergence_rate_smooth_wave
    engine.initialize()
    ~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Tes
```

### [FAILED] 临界流测试（Critical Flow Test）

- **ID:** `tests-numerical_methods-test_critical_flow`
- **Duration:** 2.06s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\numerical_methods\test_critical_flow.py", line 235, in <module>
    test.test_critical_flow_detection()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\numerical_methods\test_critical_flow.py", line 55, in test_critical_flow_detection
    pytest.skip("测试设置需重新设计：当前配置不产生稳定临界流（见test_critical_flow_treatment.py的实际临界流测试）")
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
```

### [FAILED] 质量守恒深入验证测试

- **ID:** `tests-numerical_methods-test_mass_conservation_comprehensive`
- **Duration:** 2.04s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_weno3.py:78: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-B
```

### [FAILED] 混合流态综合测试

- **ID:** `tests-numerical_methods-test_mixed_flow_comprehensive`
- **Duration:** 40.54s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_weno3.py:78: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-B
```

### [FAILED] WENO3重构精度测试（WENO3 Reconstruction Accuracy Test）

- **ID:** `tests-numerical_methods-test_weno3_accuracy`
- **Duration:** 6.09s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_solver.py:490: RuntimeWarning: invalid value encountered in scalar divide
  u = self.Q[i] / A
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\numerical_methods\test_weno3_accuracy.py", line 310, in <module>
    test.test_weno3_convergence_rate()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\numerical_methods\test_weno3_accuracy.py",
```

### [FAILED] WENO3稳定性分析测试

- **ID:** `tests-numerical_methods-test_weno3_stability`
- **Duration:** 6.12s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_weno3.py:78: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-B
```

### [FAILED] 案例示例验证测试

- **ID:** `tests-test_examples-test_case_examples`
- **Duration:** 0.11s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_examples\test_case_examples.py", line 93
    from solvers.hardy_cross_solver import HardyCrossSolver
IndentationError: expected an indented block after 'try' statement on line 92

```

### [FAILED] Unit Tests for Dual Flow Pipe - 明满流管道单元测试

- **ID:** `tests-test_network-test_dual_flow_pipe`
- **Duration:** 0.56s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_network\test_dual_flow_pipe.py", line 15, in <module>
    from network.dual_flow_pipe import DualFlowPipe
ModuleNotFoundError: No module named 'network'

```

### [FAILED] Unit Tests for Network Node Module - 管网节点模块单元测试

- **ID:** `tests-test_network-test_network_node`
- **Duration:** 0.57s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_network\test_network_node.py", line 24, in <module>
    from network.network_node import (
    ...<3 lines>...
    )
ModuleNotFoundError: No module named 'network'

```

### [FAILED] Network Node Boundary Tests - 网络节点边界测试

- **ID:** `tests-test_network-test_network_node_boundaries`
- **Duration:** 0.40s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_network\test_network_node_boundaries.py", line 21, in <module>
    from network.network_node import NetworkNode, Junction, Reservoir, Tank
ModuleNotFoundError: No module named 'network'

```

### [FAILED] Unit Tests for Network Topology Module - 管网拓扑模块单元测试

- **ID:** `tests-test_network-test_network_topology`
- **Duration:** 0.54s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_network\test_network_topology.py", line 25, in <module>
    from network.network_topology import NetworkTopology
ModuleNotFoundError: No module named 'network'

```

### [FAILED] Unit Tests for Hardy Cross Solver - Hardy Cross求解器单元测试

- **ID:** `tests-test_solvers-test_hardy_cross_solver`
- **Duration:** 0.58s
- **Error:**
```
Exit code: 1
```

### [FAILED] Newton-Raphson求解器优化测试

- **ID:** `tests-test_solvers-test_newton_raphson_improvement`
- **Duration:** 0.53s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_solvers\test_newton_raphson_improvement.py", line 24, in <module>
    from network.pressure_pipe import create_pressure_pipe
ModuleNotFoundError: No module named 'network'

```

### [FAILED] Unit Tests for Newton-Raphson Network Solver

- **ID:** `tests-test_solvers-test_newton_raphson_solver`
- **Duration:** 0.72s
- **Error:**
```
Exit code: 1
```

### [FAILED] 离心泵边界条件测试

- **ID:** `tests-test_solvers-test_pump_boundary`
- **Duration:** 0.14s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_solvers\test_pump_boundary.py", line 24
    except ImportError as e:
    ^^^^^^
SyntaxError: invalid syntax

```

### [FAILED] 性能优化模块测试

- **ID:** `tests-test_utils-test_performance`
- **Duration:** 0.68s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\tests\test_utils\test_performance.py", line 24, in <module>
    from network.pressure_pipe import PressurePipe
ModuleNotFoundError: No module named 'network'

```

### [FAILED] RP5-RP7干床问题测试套件（Phase 8.2）

- **ID:** `tests-verification-test_rp567_wet_dry`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] Toro标准Riemann问题测试套件

- **ID:** `tests-verification-test_toro_riemann_problems`
- **Duration:** 3.74s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_weno3.py:377: RuntimeWarning: overflow encountered in square
  alpha1_L = d1 / (eps + beta1_L)**2
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_weno3.py:378: RuntimeWarning: overflow encountered in square
  alpha2_L = d2 / (eps + beta2_L)**2
E:\OneDrive\Documents\GitHub\Test\HydroClaude\solvers\godunov_fvm_weno3.py:381: RuntimeWarning: invalid value encountered in divide
  omega1_L = alpha1_L / sum_alpha_L
E:\O
```

### [FAILED] 高级动画生成器 - 从实际运行结果生成GIF

- **ID:** `examples-advanced_animation_generator`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_animation_generator.py", line 62
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver
IndentationError: expected an indented block after 'try' statement on line 57

```

### [FAILED] 工程案例4: 闸门调度优化

- **ID:** `examples-case_gate_operation`
- **Duration:** 1.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\case_gate_operation.py", line 133, in <module>
    solver.initialize(h_init, Q_init)
    ^^^^^^^^^^^^^^^^^
AttributeError: 'HydrostaticCanalSolver' object has no attribute 'initialize'

```

### [FAILED] 实际工程案例 - 灌区渠系调度优化

- **ID:** `examples-case_irrigation_scheduling`
- **Duration:** 7.46s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\case_irrigation_scheduling.py:104: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WA
```

### [FAILED] 气候变化对河流冰-水质的影响评估

- **ID:** `examples-climate_change_assessment`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 综合动画生成器 - 为所有剩余示例生成GIF动画

- **ID:** `examples-comprehensive_animation_generator`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 高级边界条件使用示例

- **ID:** `examples-example_advanced_bc`
- **Duration:** 1.68s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_advanced_bc.py:58: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Wel
```

### [FAILED] 梯级水库完整示例

- **ID:** `examples-example_cascade_reservoirs`
- **Duration:** 2.45s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_cascade_reservoirs.py", line 429, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_cascade_reservoirs.py", line 400, in main
    network = build_cascade_system()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_cascade_reservoirs.py", line 87, in build_cascade_system
    reservoir1 = ReservoirNode(
        "水库1",
 
```

### [FAILED] 完整工作流程示例

- **ID:** `examples-example_complete_workflow`
- **Duration:** 1.68s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_complete_workflow.py", line 306, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_complete_workflow.py", line 277, in main
    input("按Enter开始...")
    ~~~~~^^^^^^^^^^^^^^^^^^
EOFError: EOF when reading a line

```

### [FAILED] 复合断面渠道示例

- **ID:** `examples-example_compound_channel`
- **Duration:** 0.31s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_compound_channel.py", line 495, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_compound_channel.py", line 482, in main
    example_1_basic_compound_channel()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_compound_channel.py", line 45, in example_1_basic_compound_channel
 
```

### [FAILED] 内部水工建筑物使用示例

- **ID:** `examples-example_internal_structures`
- **Duration:** 2.54s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_internal_structures.py:36: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WA
```

### [FAILED] 天然不规则断面渠道示例

- **ID:** `examples-example_irregular_channel`
- **Duration:** 0.31s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_irregular_channel.py", line 386, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_irregular_channel.py", line 372, in main
    example_6_channel_comparison()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_irregular_channel.py", line 328, in example_6_channel_comparison
    trap_
```

### [FAILED] 灌溉渠系网络完整示例

- **ID:** `examples-example_irrigation_network`
- **Duration:** 2.45s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_irrigation_network.py:53: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WAR
```

### [FAILED] 网络求解器使用示例

- **ID:** `examples-example_network_solver`
- **Duration:** 2.46s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_network_solver.py:33: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  
```

### [FAILED] 网络拓扑使用示例

- **ID:** `examples-example_network_topology`
- **Duration:** 2.48s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_network_topology.py:57: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]
```

### [FAILED] 网络验证工具使用示例

- **ID:** `examples-example_network_validation`
- **Duration:** 2.74s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_network_validation.py:32: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WAR
```

### [FAILED] 泵站提水灌溉示例

- **ID:** `examples-example_pump_station`
- **Duration:** 2.48s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_pump_station.py", line 310, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_pump_station.py", line 254, in main
    network, pump_station = build_pumping_system()
                            ~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_pump_station.py", line 83, in build_pumping_system
 
```

### [FAILED] 时间序列边界条件示例

- **ID:** `examples-example_timeseries_bc`
- **Duration:** 1.17s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_timeseries_bc.py", line 465, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_timeseries_bc.py", line 454, in main
    example_4_reservoir_operation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_timeseries_bc.py", line 217, in example_4_reservoir_operation
    bc_reservoir =
```

### [FAILED] 为所有示例生成动态GIF动画

- **ID:** `examples-generate_animations`
- **Duration:** 0.11s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\generate_animations.py", line 36
    from utils.canal_utils import compute_steady_uniform_flow
IndentationError: unexpected indent

```

### [FAILED] Phase 1应用示例 - 洪水演进模拟

- **ID:** `examples-phase1_flood_routing`
- **Duration:** 7.35s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\phase1_flood_routing.py:87: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  We
```

### [FAILED] Phase 1应用示例 - 闸门调度控制（简化版）

- **ID:** `examples-phase1_simple_gate_control`
- **Duration:** 6.97s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\phase1_simple_gate_control.py:59: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WAR
```

### [FAILED] Phase 1应用示例集 - 稳态场景库

- **ID:** `examples-phase1_steady_scenarios`
- **Duration:** 9.88s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\phase1_steady_scenarios.py:53: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN] 
```

### [FAILED] 快速验证脚本 - 测试所有新增案例

- **ID:** `examples-validate_new_examples`
- **Duration:** 0.14s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\validate_new_examples.py", line 334, in <module>
    sys.exit(main())
             ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\validate_new_examples.py", line 132, in main
    input("按Enter开始测试...")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^
EOFError: EOF when reading a line

```

### [FAILED] 自适应一阶MPC测试

- **ID:** `examples-advanced_examples-adaptive_first_order_mpc_test`
- **Duration:** 1.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\adaptive_first_order_mpc_test.py", line 23, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 控制器性能基准测试示例

- **ID:** `examples-advanced_examples-benchmark_controllers`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 对比不同Saint-Venant求解器的精度

- **ID:** `examples-advanced_examples-compare_canal_solvers`
- **Duration:** 2.50s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\compare_canal_solvers.py", line 271, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\compare_canal_solvers.py", line 153, in main
    result = test_solver(method)
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\compare_canal_solvers.py", line 38, in test_solver
    canal = Canal(
   
```

### [FAILED] 完整的控制器基准测试套件

- **ID:** `examples-advanced_examples-complete_benchmark_suite`
- **Duration:** 1.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\complete_benchmark_suite.py", line 32, in <module>
    from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\first_order_mpc.py", line 12, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 调试MPC观测器和优化问题

- **ID:** `examples-advanced_examples-debug_mpc_observer`
- **Duration:** 1.74s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\debug_mpc_observer.py", line 16, in <module>
    from control.mpc_controller import MPCController, MPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\mpc_controller.py", line 18, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] Saint-Venant模型简化诊断脚本

- **ID:** `examples-advanced_examples-debug_saint_venant`
- **Duration:** 0.93s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\debug_saint_venant.py", line 16, in <module>
    canal = Canal(
        name="test_canal",
    ...<10 lines>...
        initial_flow=20.0
    )
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\physics\canal.py", line 116, in __init__
    raise ValueError(f"不支持的求解方法'{self.method}'。仅支持'preissmann'。")
ValueError: 不支持的求解方法'moc'。仅支持'preissmann'。

```

### [FAILED] 详细诊断Canal MOC边界条件实现

- **ID:** `examples-advanced_examples-diagnose_canal_boundary`
- **Duration:** 1.87s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\diagnose_canal_boundary.py", line 17, in <module>
    canal = Canal(
        name="test_canal",
    ...<11 lines>...
        h_max=5.0  # 限制最大水位，避免过度上升
    )
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\physics\canal.py", line 116, in __init__
    raise ValueError(f"不支持的求解方法'{self.method}'。仅支持'preissmann'。")
ValueError: 不支持的求解方法'moc'。仅支持'preissmann'。

```

### [FAILED] MPC性能诊断分析

- **ID:** `examples-advanced_examples-diagnose_mpc_performance`
- **Duration:** 1.18s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\diagnose_mpc_performance.py", line 23, in <module>
    from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\first_order_mpc.py", line 12, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 多工作点分段线性化MPC（增益调度MPC）

- **ID:** `examples-advanced_examples-gain_scheduled_mpc`
- **Duration:** 1.21s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\gain_scheduled_mpc.py", line 30, in <module>
    from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\first_order_mpc.py", line 12, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 一阶MPC在非线性模型上的性能测试

- **ID:** `examples-advanced_examples-mpc_nonlinear_test`
- **Duration:** 1.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\mpc_nonlinear_test.py", line 25, in <module>
    from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\first_order_mpc.py", line 12, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] MPC鲁棒性分析

- **ID:** `examples-advanced_examples-mpc_robustness_analysis`
- **Duration:** 1.15s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\mpc_robustness_analysis.py", line 25, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 一阶MPC在Saint-Venant高保真模型上的性能测试

- **ID:** `examples-advanced_examples-mpc_saint_venant_test`
- **Duration:** 1.66s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\mpc_saint_venant_test.py", line 50, in <module>
    from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\first_order_mpc.py", line 12, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] MPC水位控制示例

- **ID:** `examples-advanced_examples-mpc_water_level_control`
- **Duration:** 2.55s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\mpc_water_level_control.py", line 31, in <module>
    from control.mpc_controller import MPCController, MPCConfig, AdaptiveMPCController
ModuleNotFoundError: No module named 'control.mpc_controller'

```

### [FAILED] 多目标水库调度优化案例

- **ID:** `examples-advanced_examples-multi_objective_reservoir_scheduling`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] Preissmann求解器参数优化

- **ID:** `examples-advanced_examples-optimize_preissmann`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 一阶MPC基准测试（配合LinearizedCanalSimulator）

- **ID:** `examples-advanced_examples-run_first_order_mpc_benchmark`
- **Duration:** 1.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\run_first_order_mpc_benchmark.py", line 19, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] MPC控制器基准测试

- **ID:** `examples-advanced_examples-run_mpc_benchmark`
- **Duration:** 2.93s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\run_mpc_benchmark.py", line 38, in <module>
    from control.mpc_controller import MPCController, MPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\mpc_controller.py", line 18, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 测试一阶MPC控制方向

- **ID:** `examples-advanced_examples-test_first_order_mpc`
- **Duration:** 0.34s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\test_first_order_mpc.py", line 8, in <module>
    from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\first_order_mpc.py", line 12, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] IDZ MPC性能测试

- **ID:** `examples-advanced_examples-test_idz_mpc_performance`
- **Duration:** 1.39s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\test_idz_mpc_performance.py", line 25, in <module>
    from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\first_order_mpc.py", line 12, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 测试MPC控制方向

- **ID:** `examples-advanced_examples-test_mpc_direction`
- **Duration:** 2.13s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\test_mpc_direction.py", line 9, in <module>
    from control.mpc_controller import MPCController, MPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\mpc_controller.py", line 18, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] 测试MPC不使用观测器

- **ID:** `examples-advanced_examples-test_mpc_no_observer`
- **Duration:** 1.94s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\advanced_examples\test_mpc_no_observer.py", line 9, in <module>
    from control.mpc_controller import MPCController, MPCConfig
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\control\mpc_controller.py", line 18, in <module>
    import cvxpy as cp
ModuleNotFoundError: No module named 'cvxpy'

```

### [FAILED] HydroClaude Performance Benchmark Tool - 性能基准测试工具

- **ID:** `examples-case_library-benchmark_performance`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] HydroClaude Case Library Runner - 案例库运行器

- **ID:** `examples-case_library-run_all_cases`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] Test Suite for Engineering Cases - 工程案例测试套件

- **ID:** `examples-case_library-test_cases`
- **Duration:** 2.12s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\case_library\test_cases.py", line 47, in run_test
    test_func()
    ~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\case_library\test_cases.py", line 219, in test_case_02_water_supply_demand_pattern
    total_demand = sum(node['current_demand'] for node_id, node in network.nodes.items()
                      if node_id not in ['SOURCE', 'TOWER'])
  File "E:\OneDrive\Docu
```

### [FAILED] 单配置文件仿真运行器

- **ID:** `examples-config_driven-simulate`
- **Duration:** 1.71s
- **Error:**
```
Exit code: 1
用法: python simulate.py config.json

```

### [FAILED] Batch modify scripts to use unified output structure

- **ID:** `examples-example_01_canal_flow-batch_modify_scripts`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\batch_modify_scripts.py", line 170, in <module>
    modify_script_03()
    ~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\batch_modify_scripts.py", line 18, in modify_script_03
    with open(script_path, 'r') as f:
         ~~~~^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: 'code/03_idz_identif
```

### [ERROR] Quick test for script 10 numerical stability

- **ID:** `examples-example_01_canal_flow-test_script10_stability`
- **Duration:** 0.00s
- **Error:**
```
File not found: E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\test_script10_stability.py
```

### [FAILED] 验证所有v2升级脚本

- **ID:** `examples-example_01_canal_flow-validate_all_v2_scripts`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 示例2: 泵站系统 - 增强版（嵌入式动画）

- **ID:** `examples-example_02_pump_system-example_02_pump_system_with_anim`
- **Duration:** 1.15s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_pump_system\example_02_pump_system_with_anim.py", line 25, in <module>
    from physics.tank import Tank
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] Example 02: Hydraulic Structures Demonstration

- **ID:** `examples-example_02_spillway_cascade-example_02_spillway_simple`
- **Duration:** 2.18s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_spillway_cascade\example_02_spillway_simple.py", line 302, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_spillway_cascade\example_02_spillway_simple.py", line 281, in main
    demo_spillway()
    ~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_spillway_cascade\example_02_spillway_simple
```

### [FAILED] Example 02: Spillway Cascade System

- **ID:** `examples-example_02_spillway_cascade-example_02_spillway_system`
- **Duration:** 2.02s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_spillway_cascade\example_02_spillway_system.py", line 328, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_02_spillway_cascade\example_02_spillway_system.py", line 306, in main
    reservoir_levels, discharges = system.run_rating_curve_analysis()
                                   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDri
```

### [FAILED] Example 03: Hydraulic Turbine Comparison

- **ID:** `examples-example_03_turbine_demo-example_03_turbine_comparison`
- **Duration:** 2.46s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_turbine_demo\example_03_turbine_comparison.py", line 374, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_turbine_demo\example_03_turbine_comparison.py", line 333, in main
    plot_efficiency_curves(francis_data, kaplan_data, pelton_data)
    ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "E:\OneDrive\Docum
```

### [FAILED] 示例3: 水轮机暂态响应 - 增强版（嵌入式动画）

- **ID:** `examples-example_03_turbine_demo-example_03_turbine_with_anim`
- **Duration:** 1.23s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_03_turbine_demo\example_03_turbine_with_anim.py", line 25, in <module>
    from physics.turbine import FrancisTurbine
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] Example 04: Complete Hydropower Plant System

- **ID:** `examples-example_04_hydropower_system-example_04_hydropower_plant`
- **Duration:** 2.83s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_04_hydropower_system\example_04_hydropower_plant.py", line 384, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_04_hydropower_system\example_04_hydropower_plant.py", line 343, in main
    Q_range, powers, efficiencies = plant.generate_performance_curves()
                                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E
```

### [FAILED] Example 05: Hydropower Plant Transient Analysis - Load Rejection

- **ID:** `examples-example_05_transient_analysis-example_05_load_rejection`
- **Duration:** 3.05s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_05_transient_analysis\example_05_load_rejection.py", line 441, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_05_transient_analysis\example_05_load_rejection.py", line 421, in main
    plot_results(results)
    ~~~~~~~~~~~~^^^^^^^^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_05_transient_analysis\example_05
```

### [FAILED] Example 06: Complete Hydropower Plant System Integration

- **ID:** `examples-example_06_complete_hydropower_system-example_06_complete_system`
- **Duration:** 2.69s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_06_complete_hydropower_system\example_06_complete_system.py", line 452, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_06_complete_hydropower_system\example_06_complete_system.py", line 407, in main
    results = system.run_performance_analysis()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_06_complete_hydrop
```

### [FAILED] 示例8: 水轮机接受负荷 - 增强版（嵌入式动画）

- **ID:** `examples-example_08_load_acceptance-example_08_load_acceptance_with_anim`
- **Duration:** 1.10s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_load_acceptance\example_08_load_acceptance_with_anim.py", line 28, in <module>
    from animation_utils import AnimationGenerator
ModuleNotFoundError: No module named 'animation_utils'

```

### [FAILED] 示例8: Preissmann格式 vs 有限体积法对比（增强版）

- **ID:** `examples-example_08_preissmann_vs_fvm-example_08_preissmann_vs_fvm_enhanced`
- **Duration:** 2.85s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_preissmann_vs_fvm\example_08_preissmann_vs_fvm_enhanced.py", line 546, in <module>
    example_preissmann_vs_fvm()
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_preissmann_vs_fvm\example_08_preissmann_vs_fvm_enhanced.py", line 72, in example_preissmann_vs_fvm
    canal_f = Canal(
        "Canal_FVM", 5000, 10000, 100, length,
   
```

### [FAILED] 示例9: 管道水击RK4高精度求解（增强版）

- **ID:** `examples-example_09_pipe_rk4-example_09_pipe_rk4_enhanced`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 示例16：堰类组件在灌区引水渠系统中的应用

- **ID:** `examples-example_16_weirs_application-weirs_irrigation_system`
- **Duration:** 1.19s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_16_weirs_application\weirs_irrigation_system.py", line 438, in <module>
    run_irrigation_system_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_16_weirs_application\weirs_irrigation_system.py", line 117, in run_irrigation_system_simulation
    solver = SingleCanalSolver(
        total_length=canal_length,
    ...<5 
```

### [FAILED] 示例17: 水库基础示例

- **ID:** `examples-example_17_reservoir_basic-demo_reservoir`
- **Duration:** 3.34s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_17_reservoir_basic\demo_reservoir.py", line 260, in <module>
    reservoir, results = demo_basic_reservoir()
                         ~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_17_reservoir_basic\demo_reservoir.py", line 195, in demo_basic_reservoir
    plt.savefig('/home/user/HydroClaude/examples/example_17_reservoir_basic/reservoir_simulat
```

### [FAILED] 示例18: 梯级水电站调度

- **ID:** `examples-example_18_cascade_hydropower-demo_cascade`
- **Duration:** 0.14s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_18_cascade_hydropower\demo_cascade.py", line 16, in <module>
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                       ^^
NameError: name 'os' is not defined. Did you forget to import 'os'?

```

### [FAILED] 示例19: 长距离调水工程

- **ID:** `examples-example_19_water_transfer-demo_water_transfer`
- **Duration:** 4.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_19_water_transfer\demo_water_transfer.py", line 519, in <module>
    visualize_results(results)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_19_water_transfer\demo_water_transfer.py", line 465, in visualize_results
    plt.savefig('/home/user/HydroClaude/examples/example_19_water_transfer/water_transfer_simulation.png',
    ~~~~~~~~~~~
```

### [FAILED] 示例20: 城市供水管网优化调度

- **ID:** `examples-example_20_urban_water_supply-demo_urban_supply`
- **Duration:** 4.74s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_20_urban_water_supply\demo_urban_supply.py", line 563, in <module>
    visualize_results(results, system)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_20_urban_water_supply\demo_urban_supply.py", line 550, in visualize_results
    plt.savefig('/home/user/HydroClaude/examples/example_20_urban_water_supply/urban_supply_simulation
```

### [FAILED] 示例21: 灌区配水优化调度

- **ID:** `examples-example_21_irrigation_optimization-demo_irrigation`
- **Duration:** 2.78s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_21_irrigation_optimization\demo_irrigation.py", line 504, in <module>
    visualize_results(results, system)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_21_irrigation_optimization\demo_irrigation.py", line 491, in visualize_results
    plt.savefig('/home/user/HydroClaude/examples/example_21_irrigation_optimization/irrigation_o
```

### [FAILED] 示例22: 水锤效应分析

- **ID:** `examples-example_22_water_hammer-demo_water_hammer`
- **Duration:** 2.87s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_22_water_hammer\demo_water_hammer.py:266: UserWarning: Glyph 26497 (\N{CJK UNIFIED IDEOGRAPH-6781}) missing from font(s) DejaVu Sans.
  plt.tight_layout()
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_22_water_hammer\demo_water_hammer.py:266: UserWarning: Glyph 24555 (\N{CJK UNIFIED IDEOGRAPH-5FEB}) missing from font(s) DejaVu Sans.
  plt.tight_layout()
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_2
```

### [FAILED] 示例23: 控制策略性能对比 (PID vs MPC)

- **ID:** `examples-example_23_control_comparison-demo_control_comparison`
- **Duration:** 4.95s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_23_control_comparison\demo_control_comparison.py", line 524, in <module>
    results = run_control_comparison()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_23_control_comparison\demo_control_comparison.py", line 468, in run_control_comparison
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File
```

### [FAILED] 示例24: 水库多目标优化调度

- **ID:** `examples-example_24_multi_objective_optimization-demo_multi_objective`
- **Duration:** 3.46s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_24_multi_objective_optimization\demo_multi_objective.py:456: UserWarning: Glyph 21457 (\N{CJK UNIFIED IDEOGRAPH-53D1}) missing from font(s) DejaVu Sans.
  plt.savefig(output_path, dpi=150, bbox_inches='tight')
E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_24_multi_objective_optimization\demo_multi_objective.py:456: UserWarning: Glyph 30005 (\N{CJK UNIFIED IDEOGRAPH-7535}) missing from font(s) DejaVu Sans.
  plt.savef
```

### [FAILED] MPC水位控制示例

- **ID:** `examples-example_control-run_mpc_control`
- **Duration:** 1.22s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 1082, in run
    self.run_control_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 689, in run_control_simulation
    h_init, hu_init, steady_result = self.steady_estimator.estimate_from_steady_solution(
                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

### [FAILED] PID水位控制示例

- **ID:** `examples-example_control-run_pid_control`
- **Duration:** 1.19s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 1082, in run
    self.run_control_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 689, in run_control_simulation
    h_init, hu_init, steady_result = self.steady_estimator.estimate_from_steady_solution(
                                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

### [FAILED] 深度分析所有工况结果

- **ID:** `examples-example_gate_pump_cascade-analyze_all_scenarios`
- **Duration:** 1.15s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\analyze_all_scenarios.py", line 278, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\analyze_all_scenarios.py", line 99, in main
    scenarios = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
                                   ~~~~~~~~~~^^^^^^^^^^
FileNotFoundEr
```

### [FAILED] 批量运行所有工况 - 验证高精度非恒定流模拟引擎

- **ID:** `examples-example_gate_pump_cascade-batch_run_all_scenarios`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 串联明渠闸泵群系统 - 综合工况测试

- **ID:** `examples-example_gate_pump_cascade-comprehensive_scenario_test`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 串联明渠闸泵群系统 - 增强版工况测试

- **ID:** `examples-example_gate_pump_cascade-enhanced_scenario_test`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 明渠串联闸泵群系统 - 使用高精度泵站模型（完整特性曲线）

- **ID:** `examples-example_gate_pump_cascade-gate_pump_cascade_advanced`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 串联明渠闸泵群系统 - 快速工况测试（精简版）

- **ID:** `examples-example_gate_pump_cascade-quick_scenario_test`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 快速运行工况的辅助脚本

- **ID:** `examples-example_gate_pump_cascade-run_scenario`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 工况1: 上游大流量阶跃

- **ID:** `examples-example_gate_pump_cascade-run_scenario_01`
- **Duration:** 0.14s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\run_scenario_01.py", line 16, in <module>
    exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0xab in position 55: illegal multibyte sequence

```

### [FAILED] 工况2: 上游中等流量阶跃

- **ID:** `examples-example_gate_pump_cascade-run_scenario_02`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\run_scenario_02.py", line 16, in <module>
    exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0xab in position 55: illegal multibyte sequence

```

### [FAILED] 工况3: 下游水位阶跃

- **ID:** `examples-example_gate_pump_cascade-run_scenario_03`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\run_scenario_03.py", line 15, in <module>
    exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0xab in position 55: illegal multibyte sequence

```

### [FAILED] 工况4: 闸门开度调控

- **ID:** `examples-example_gate_pump_cascade-run_scenario_04`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\run_scenario_04.py", line 15, in <module>
    exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0xab in position 55: illegal multibyte sequence

```

### [FAILED] 工况5: 极端流量测试

- **ID:** `examples-example_gate_pump_cascade-run_scenario_05`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\run_scenario_05.py", line 15, in <module>
    exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0xab in position 55: illegal multibyte sequence

```

### [FAILED] 串联明渠闸泵群系统 - 标准多工况测试（遵守开发规范）

- **ID:** `examples-example_gate_pump_cascade-standard_multi_scenario_test`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 快速测试所有工况的初始恒定流状态

- **ID:** `examples-example_gate_pump_cascade-test_all_scenarios_quick`
- **Duration:** 1.13s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\test_all_scenarios_quick.py", line 25, in <module>
    exec(open('examples/example_gate_pump_cascade/enhanced_scenario_test.py').read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0x9f in position 80: illegal multibyte sequence

```

### [FAILED] 测试修复效果

- **ID:** `examples-example_gate_pump_cascade-test_fix`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\test_fix.py", line 15, in <module>
    exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0xab in position 55: illegal multibyte sequence

```

### [FAILED] 测试修复后的求解器

- **ID:** `examples-example_gate_pump_cascade-test_fixed_solver`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_gate_pump_cascade\test_fixed_solver.py", line 13, in <module>
    exec(open(os.path.join(os.path.dirname(__file__), 'run_scenario.py')).read())
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
UnicodeDecodeError: 'gbk' codec can't decode byte 0xab in position 55: illegal multibyte sequence

```

### [FAILED] 简单明渠稳态流模拟 - 使用通用建模系统

- **ID:** `examples-example_simple_canal-run_simple_canal`
- **Duration:** 1.20s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 1080, in run
    self.run_steady_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 315, in run_steady_simulation
    h, hu, result = self.steady_estimator.estimate_from_steady_solution(
                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        solver=self.solver,

```

### [FAILED] 溢洪道结构物示例

- **ID:** `examples-example_structures-run_spillway`
- **Duration:** 1.19s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 1080, in run
    self.run_steady_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 315, in run_steady_simulation
    h, hu, result = self.steady_estimator.estimate_from_steady_solution(
                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        solver=self.solver,

```

### [FAILED] 时变边界条件示例 - 正弦波动流量

- **ID:** `examples-example_unsteady-run_time_varying_bc`
- **Duration:** 1.19s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 1084, in run
    self.run_unsteady_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 383, in run_unsteady_simulation
    h, hu, steady_result = self.steady_estimator.estimate_from_steady_solution(
                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        
```

### [FAILED] 非稳态流动模拟示例

- **ID:** `examples-example_unsteady-run_unsteady_flow`
- **Duration:** 1.19s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 1084, in run
    self.run_unsteady_simulation()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\modeling\universal_modeler.py", line 383, in run_unsteady_simulation
    h, hu, steady_result = self.steady_estimator.estimate_from_steady_solution(
                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        
```

### [FAILED] 实际工程案例：城市供水管网系统

- **ID:** `examples-pressurized_examples-water_supply_network`
- **Duration:** 1.14s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\pressurized_examples\water_supply_network.py", line 33, in <module>
    from core.pressurized_solver import PressurizedFlowSolver, PipelineConfig
ModuleNotFoundError: No module named 'core'

```

### [FAILED] 实际工程案例：灌溉渠道自动化控制系统

- **ID:** `examples-real_world_cases-irrigation_canal_automation`
- **Duration:** 2.64s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\real_world_cases\irrigation_canal_automation.py", line 33, in <module>
    from control.mpc_controller import MPCController, MPCConfig
ModuleNotFoundError: No module named 'control.mpc_controller'

```

### [FAILED] 实际工程案例：城市排水泵站智能调度系统

- **ID:** `examples-real_world_cases-urban_drainage_pump_station`
- **Duration:** 3.34s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\real_world_cases\urban_drainage_pump_station.py", line 36, in <module>
    from control.mpc_controller import MPCController, MPCConfig
ModuleNotFoundError: No module named 'control.mpc_controller'

```

### [FAILED] 示例：Preissmann vs FVM对比

- **ID:** `examples-example_08_preissmann_vs_fvm-code-example_08_preissmann_vs_fvm`
- **Duration:** 2.38s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_preissmann_vs_fvm\code\example_08_preissmann_vs_fvm.py", line 96, in <module>
    example_preissmann_vs_fvm()
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_08_preissmann_vs_fvm\code\example_08_preissmann_vs_fvm.py", line 35, in example_preissmann_vs_fvm
    canal_f = Canal(
        "明渠_FVM", 5000, 10000, 100, length,
        method=
```

### [FAILED] Example 07 Fault Test

- **ID:** `examples-example_07_fault_test-code-example_07_fault_test`
- **Duration:** 0.35s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_07_fault_test\code\example_07_fault_test.py", line 6, in <module>
    from disturbance.disturbance_generator import DisturbanceGenerator
ImportError: cannot import name 'DisturbanceGenerator' from 'disturbance.disturbance_generator' (E:\OneDrive\Documents\GitHub\Test\HydroClaude\disturbance\disturbance_generator.py). Did you mean: 'disturbance_generator'?

```

### [FAILED] Example 06 Sil Basic

- **ID:** `examples-example_06_sil_basic-code-example_06_sil_basic`
- **Duration:** 0.92s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_06_sil_basic\code\example_06_sil_basic.py", line 5, in <module>
    from physics.gate import Gate
ImportError: cannot import name 'Gate' from 'physics.gate' (E:\OneDrive\Documents\GitHub\Test\HydroClaude\physics\gate.py). Did you mean: 'gate'?

```

### [FAILED] 例子1：明渠非恒定流 - 重构版（简化）

- **ID:** `examples-example_01_canal_flow-scripts-01_basic`
- **Duration:** 1.78s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic.py", line 284, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic.py", line 89, in main
    solver = CanalSolver(
        length=length,
    ...<4 lines>...
        method=method
    )
TypeError: HydrostaticCanalSolver.__init__() got an unexpected keyword argument 'method'

```

### [FAILED] 例子1：明渠非恒定流 - 重构版（简化）

- **ID:** `examples-example_01_canal_flow-scripts-01_basic_refactored`
- **Duration:** 1.04s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic_refactored.py", line 27, in <module>
    from solvers_canal_solver import CanalSolver
ModuleNotFoundError: No module named 'solvers_canal_solver'

```

### [FAILED] 例子1：明渠非恒定流 - 嵌入动画版本

- **ID:** `examples-example_01_canal_flow-scripts-01_basic_with_animation`
- **Duration:** 1.29s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic_with_animation.py", line 377, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic_with_animation.py", line 126, in main
    solver = CanalSolver(
        length=length,
    ...<4 lines>...
        method=method
    )
TypeError: HydrostaticCanalSolver.__init__() got an unexpected
```

### [FAILED] 例子1：明渠非恒定流 - 嵌入动画版本

- **ID:** `examples-example_01_canal_flow-scripts-01_basic_with_animation_refactored`
- **Duration:** 0.32s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic_with_animation_refactored.py", line 28, in <module>
    sys.path.insert(0, EXAMPLES_DIR)
                       ^^^^^^^^^^^^
NameError: name 'EXAMPLES_DIR' is not defined

```

### [FAILED] 例子1扩展：不同下游边界条件的影响研究（完全收敛版）

- **ID:** `examples-example_01_canal_flow-scripts-04_boundary_conditions`
- **Duration:** 1.16s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\04_boundary_conditions.py", line 396, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\04_boundary_conditions.py", line 173, in main
    h_init, Q_init, converged, iterations = compute_steady_state_with_convergence(
                                            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

### [FAILED] 例子1扩展：不同下游边界条件的影响研究（完全收敛版）

- **ID:** `examples-example_01_canal_flow-scripts-04_boundary_conditions_refactored`
- **Duration:** 0.30s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\04_boundary_conditions_refactored.py", line 28, in <module>
    from solvers_canal_solver import CanalSolver
ModuleNotFoundError: No module named 'solvers_canal_solver'

```

### [FAILED] 例子1扩展：不同下游边界条件的影响研究 (HydrostaticCanalSolver高精度版本)

- **ID:** `examples-example_01_canal_flow-scripts-04_boundary_conditions_v2`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 例子1扩展：不同下游边界条件的影响研究 (HydrostaticCanalSolver高精度版本 - Refactored)

- **ID:** `examples-example_01_canal_flow-scripts-04_boundary_conditions_v2_refactored`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 例子1：明渠非恒定流 - 阶跃响应三种方法对比 (ScriptHelper重构版)

- **ID:** `examples-example_01_canal_flow-scripts-05_step_response_refactored`
- **Duration:** 21.48s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\05_step_response_refactored.py", line 546, in <module>
    results = run_step_response_comparison()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\05_step_response_refactored.py", line 540, in run_step_response_comparison
    print(f"\nAll outputs saved to: {helper.output_dir}/")
                                     ^^^^^^^^
```

### [FAILED] 示例1: 明渠非恒定流 - 生成GIF动画（改进版，消除边界振荡）

- **ID:** `examples-example_01_canal_flow-scripts-06_animation`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 示例1: 明渠非恒定流 - 生成GIF动画 (ScriptHelper重构版)

- **ID:** `examples-example_01_canal_flow-scripts-06_animation_refactored`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 示例1扩展：明渠闸门过流动力学分析（单一求解器版本）

- **ID:** `examples-example_01_canal_flow-scripts-07_sluice_gate_flow`
- **Duration:** 1.87s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\07_sluice_gate_flow.py", line 25, in <module>
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
ModuleNotFoundError: No module named 'solvers'

```

### [FAILED] 示例1扩展：明渠闸门过流动力学分析（单一求解器版本）

- **ID:** `examples-example_01_canal_flow-scripts-07_sluice_gate_flow_refactored`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\07_sluice_gate_flow_refactored.py", line 398
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                                                       ^
IndentationError: unindent does not match any outer indentation level

```

### [FAILED] 示例1扩展：明渠闸门过流动力学分析（单一求解器版本）

- **ID:** `examples-example_01_canal_flow-scripts-07_sluice_gate_flow_refactored_v2`
- **Duration:** 0.12s
- **Error:**
```
Exit code: 1
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\07_sluice_gate_flow_refactored_v2.py", line 173
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                                                       ^
IndentationError: unindent does not match any outer indentation level

```

### [FAILED] 优化版例子1：闸门流动模拟

- **ID:** `examples-example_01_canal_flow-scripts-08_optimized_steady_solving`
- **Duration:** 1.82s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\08_optimized_steady_solving.py", line 24, in <module>
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
ModuleNotFoundError: No module named 'solvers'

```

### [FAILED] 示例1: 简单明渠仿真（增强版）

- **ID:** `examples-example_01_canal_flow-scripts-09_simple_canal_enhanced`
- **Duration:** 0.13s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\09_simple_canal_enhanced.py", line 11, in <module>
    from physics.canal import Canal
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] 示例1: 明渠深入分析 v2（边界条件、阶跃响应、IDZ模型辨识）

- **ID:** `examples-example_01_canal_flow-scripts-10_canal_deep_analysis`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 示例1: 明渠深入分析 (ScriptHelper重构版) v2（边界条件、阶跃响应、IDZ模型辨识）

- **ID:** `examples-example_01_canal_flow-scripts-10_canal_deep_analysis_refactored`
- **Duration:** 3.82s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\10_canal_deep_analysis_refactored.py", line 28, in <module>
    helper = ScriptHelper(__file__)
             ^^^^^^^^^^^^
NameError: name 'ScriptHelper' is not defined

```

### [FAILED] 示例2：高级水工建筑物组合（重构版）

- **ID:** `examples-example_01_canal_flow-scripts-11_advanced_structures`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 示例2：高级水工建筑物组合 (ScriptHelper重构版)（重构版）

- **ID:** `examples-example_01_canal_flow-scripts-11_advanced_structures_refactored`
- **Duration:** 1.22s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\11_advanced_structures_refactored.py", line 34, in <module>
    helper = ScriptHelper(__file__)
             ^^^^^^^^^^^^
NameError: name 'ScriptHelper' is not defined

```

### [FAILED] 优化版例子2：三闸门串联和混合结构

- **ID:** `examples-example_01_canal_flow-scripts-12_advanced_optimized`
- **Duration:** 0.30s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\12_advanced_optimized.py", line 22, in <module>
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
ModuleNotFoundError: No module named 'solvers'

```

### [FAILED] 明渠非恒定流求解器

- **ID:** `examples-example_01_canal_flow-scripts-_local_canal_solver`
- **Duration:** 1.73s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\_local_canal_solver.py", line 22, in <module>
    from utils.canal_utils import compute_steady_uniform_flow, compute_manning_friction_slope
ModuleNotFoundError: No module named 'utils'

```

### [FAILED] 单一求解器版本的渠道-闸门耦合求解器（重构版）

- **ID:** `examples-example_01_canal_flow-scripts-_local_single_canal_solver`
- **Duration:** 1.74s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\_local_single_canal_solver.py", line 21, in <module>
    from _local_canal_solver import CanalSolver
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\_local_canal_solver.py", line 22, in <module>
    from utils.canal_utils import compute_steady_uniform_flow, compute_manning_friction_slope
ModuleNotFoundError: No module named '
```

### [FAILED] 详细分析Jacobian矩阵结构

- **ID:** `examples-example_01_canal_flow-tests-analyze_jacobian`
- **Duration:** 0.32s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\analyze_jacobian.py", line 16, in <module>
    from physics.steady_saint_venant import SteadySaintVenantSystem
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] 性能对比测试：自适应松弛因子 vs 固定松弛因子

- **ID:** `examples-example_01_canal_flow-tests-test_adaptive_relax`
- **Duration:** 0.31s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_adaptive_relax.py", line 22, in <module>
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
ModuleNotFoundError: No module named 'solvers'

```

### [FAILED] Anderson加速简单测试

- **ID:** `examples-example_01_canal_flow-tests-test_anderson_simple`
- **Duration:** 0.32s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_anderson_simple.py", line 16, in <module>
    from solvers.anderson_acceleration import AndersonAcceleration
ModuleNotFoundError: No module named 'solvers'

```

### [FAILED] Anderson加速参数调优

- **ID:** `examples-example_01_canal_flow-tests-test_anderson_tuning`
- **Duration:** 0.30s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_anderson_tuning.py", line 21, in <module>
    from structures.sluice_gate import SluiceGate
ModuleNotFoundError: No module named 'structures'

```

### [FAILED] Anderson加速 vs Aitken加速性能对比

- **ID:** `examples-example_01_canal_flow-tests-test_anderson_vs_aitken`
- **Duration:** 0.30s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_anderson_vs_aitken.py", line 24, in <module>
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver
ModuleNotFoundError: No module named 'solvers'

```

### [FAILED] 检查数值方法的实际收敛性 - 可视化时间序列

- **ID:** `examples-example_01_canal_flow-tests-test_convergence_visual`
- **Duration:** 1.22s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_convergence_visual.py", line 9, in <module>
    from example_01_canal_stability_test import ImprovedCanalSolver
ModuleNotFoundError: No module named 'example_01_canal_stability_test'

```

### [FAILED] 测试Jacobian矩阵的秩和条件数

- **ID:** `examples-example_01_canal_flow-tests-test_jacobian_rank`
- **Duration:** 0.29s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_jacobian_rank.py", line 16, in <module>
    from physics.steady_saint_venant import SteadySaintVenantSystem
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] 测试修复后的牛顿法求解器

- **ID:** `examples-example_01_canal_flow-tests-test_newton_fixed`
- **Duration:** 0.32s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_newton_fixed.py", line 17, in <module>
    from physics.steady_saint_venant import SteadySaintVenantSystem
ModuleNotFoundError: No module named 'physics'

```

### [FAILED] 性能对比测试：全面评估不同求解策略

- **ID:** `examples-example_01_canal_flow-tests-test_performance_comparison`
- **Duration:** 1.15s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\tests\test_performance_comparison.py", line 29, in <module>
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
ModuleNotFoundError: No module named 'solvers'

```

### [FAILED] 工程案例4: 参数在线校准

- **ID:** `examples-engineering_cases-case_04_parameter_calibration-run`
- **Duration:** 6.23s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\engineering_cases\case_04_parameter_calibration\run.py", line 270, in <module>
    run_parameter_calibration()
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\engineering_cases\case_04_parameter_calibration\run.py", line 131, in run_parameter_calibration
    measurements = create_synthetic_data(
        true_solver,
    ...<2 lines>...
        dt=10.0
 
```

### [FAILED] 工程案例5: 水资源优化调度

- **ID:** `examples-engineering_cases-case_05_water_resource_optimization-run`
- **Duration:** 1.19s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\engineering_cases\case_05_water_resource_optimization\run.py", line 362, in <module>
    run_optimization()
    ~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\engineering_cases\case_05_water_resource_optimization\run.py", line 176, in run_optimization
    pump = PumpStation(
        position=pump_position,
    ...<4 lines>...
        g=9.81
    )
TypeError: PumpSta
```

### [FAILED] 案例1: 溃坝模拟 - 方法对比

- **ID:** `examples-case_library-case_01_dam_break-dam_break_comparison`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 验证案例批量运行工具

- **ID:** `validation_cases-run_all_validation`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 综合验证测试套件

- **ID:** `validation_cases-run_comprehensive_validation`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 标准验证案例1: Dam Break with Dry Bed (Ritter Solution)

- **ID:** `validation_cases-analytical-dam_break_ritter`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] 渐变流水面线解析解验证 (Gradually Varied Flow)

- **ID:** `validation_cases-analytical-gradually_varied_flow`
- **Duration:** 53.84s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\analytical\gradually_varied_flow.py:217: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-
```

### [FAILED] 水跃验证 (Hydraulic Jump)

- **ID:** `validation_cases-analytical-hydraulic_jump`
- **Duration:** 13.20s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\analytical\hydraulic_jump.py:202: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balance
```

### [FAILED] 恒定均匀流验证 (Steady Uniform Flow)

- **ID:** `validation_cases-analytical-steady_uniform_flow_comprehensive`
- **Duration:** 9.95s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\analytical\steady_uniform_flow_comprehensive.py:93: UserWarning: 
================================================================================
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[WARN]  Well-Balanced
=
[W
```

### [FAILED] 单管道验证案例集 - Single Pipe Validation Cases

- **ID:** `validation_cases-pressure_network-single_pipe_validation`
- **Duration:** 60.00s
- **Error:**
```
Timeout (>60s)
```

### [FAILED] Stage 5 综合验证案例 / Stage 5 Integration Validation Case

- **ID:** `validation_cases-pressure_network-stage5_integration_validation`
- **Duration:** 3.07s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\pressure_network\stage5_integration_validation.py", line 447, in <module>
    results = demo_stage5_integration()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\pressure_network\stage5_integration_validation.py", line 99, in demo_stage5_integration
    topology.add_node(node_id, node)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
TypeError: NetworkTopology.add_node() takes 2 p
```

### [FAILED] 水锤分析验证案例 / Water Hammer Validation Case

- **ID:** `validation_cases-pressure_network-water_hammer_validation`
- **Duration:** 5.54s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\pressure_network\water_hammer_validation.py", line 336, in <module>
    results = valve_closure_case()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\pressure_network\water_hammer_validation.py", line 298, in valve_closure_case
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Users\lxh\min
```

### [FAILED] HydroClaude Engineering Case Study 3: Bridge Hydraulic Capacity Assessment

- **ID:** `validation_cases-engineering-bridge_assessment-bridge_assessment_case`
- **Duration:** 6.80s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\bridge_assessment\bridge_assessment_case.py", line 643, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\bridge_assessment\bridge_assessment_case.py", line 620, in main
    bridge_assess.visualize_results(flood_results, comparison, Q_design)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

### [FAILED] HydroClaude Engineering Case Study 2: Natural River Flood Routing

- **ID:** `validation_cases-engineering-flood_routing-flood_routing_case`
- **Duration:** 12.70s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\flood_routing\flood_routing_case.py:239: DeprecationWarning: `trapz` is deprecated. Use `trapezoid` instead, or one of the numerical integration functions in `scipy.integrate`.
  print(f"  Total Volume: {np.trapz(Q_flood, time_array) * 3600 / 1e6:.2f} million m³")
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\flood_routing\flood_routing_case.py:476: RuntimeWarning: overflow encountered in scal
```

### [FAILED] HydroClaude Engineering Case Study 1: Trapezoidal Irrigation Canal System

- **ID:** `validation_cases-engineering-irrigation_canal-irrigation_canal_case`
- **Duration:** 6.31s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\irrigation_canal\irrigation_canal_case.py:498: DeprecationWarning: `trapz` is deprecated. Use `trapezoid` instead, or one of the numerical integration functions in `scipy.integrate`.
  total_delivered = np.trapz(results['total_demand'], results['time']) * 3600  # m³
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\irrigation_canal\irrigation_canal_case.py:499: DeprecationWarning: `trapz` is depre
```

### [FAILED] HydroClaude Engineering Case Study 4: Urban Drainage System

- **ID:** `validation_cases-engineering-urban_drainage-urban_drainage_case`
- **Duration:** 5.80s
- **Error:**
```
Exit code: 1
E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\urban_drainage\urban_drainage_case.py:322: DeprecationWarning: `trapz` is deprecated. Use `trapezoid` instead, or one of the numerical integration functions in `scipy.integrate`.
  total_rainfall = np.trapz(intensity, time_array)  # mm
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\urban_drainage\urban_drainage_case.py", line 661, in <module>
    main(
```

### [FAILED] HydroClaude Engineering Case Study 5: Water Resources Optimization

- **ID:** `validation_cases-engineering-water_resources_optimization-water_optimization_case`
- **Duration:** 6.85s
- **Error:**
```
Exit code: 1
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\water_resources_optimization\water_optimization_case.py", line 651, in <module>
    main()
    ~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\validation_cases\engineering\water_resources_optimization\water_optimization_case.py", line 624, in main
    system.visualize_results(results)
    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "E:\OneDrive\Documents\GitHub\Test\Hyd
```

---

*Generated by HydroClaude Batch Tester*
