# HydrostaticCanalSolver v2脚本验证报告

**验证时间**: 2025-11-13 09:32:15

**验证脚本数**: 6

---

##  总体统计

| 指标 | 数值 |
|-----|------|
| 总脚本数 | 6 |
|  成功 | 0 (0.0%) |
|  失败 | 6 (100.0%) |
| 总耗时 | 12.13秒 |
| 平均耗时 | 2.02秒 |

---

##  详细结果

| 脚本 | 状态 | 耗时(s) | 流量误差 | 迭代次数 |
|------|------|---------|---------|----------|
| 01_basic_v2.py |  | 1.93 | N/A | N/A |
| 04_boundary_conditions_v2.py |  | 2.02 | N/A | N/A |
| 07_sluice_gate_flow_v2.py |  | 2.07 | N/A | N/A |
| 08_optimized_steady_solving_v2.py |  | 2.02 | N/A | N/A |
| 11_advanced_structures.py |  | 2.06 | N/A | N/A |
| 12_advanced_optimized_v2.py |  | 2.04 | N/A | N/A |

---

## ️ 失败详情

### 01_basic_v2.py

- **返回码**: 1
- **错误信息**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic_v2.py", line 376, in <module>
    validator = main()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\01_basic_v2.py", line 66, in main
    print(f"目标流量: {Q_target} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in position 11: illegal multibyte sequence
```

### 04_boundary_conditions_v2.py

- **返回码**: 1
- **错误信息**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\04_boundary_conditions_v2.py", line 447, in <module>
    validator = main()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\04_boundary_conditions_v2.py", line 71, in main
    print(f"  初始流量: {Q_initial} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't encode character '\xb3' in posit
```

### 07_sluice_gate_flow_v2.py

- **返回码**: 1
- **错误信息**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\07_sluice_gate_flow_v2.py", line 303, in <module>
    validator = run_sluice_gate_dynamics()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\07_sluice_gate_flow_v2.py", line 103, in run_sluice_gate_dynamics
    print(f"  初始流量: {Q_initial} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can
```

### 08_optimized_steady_solving_v2.py

- **返回码**: 1
- **错误信息**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\08_optimized_steady_solving_v2.py", line 414, in <module>
    validator = run_optimized_example()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\08_optimized_steady_solving_v2.py", line 67, in run_optimized_example
    print(f"  目标流量: {Q_target} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' co
```

### 11_advanced_structures.py

- **返回码**: 1
- **错误信息**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\11_advanced_structures.py", line 560, in <module>
    run_advanced_structures_demo()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\11_advanced_structures.py", line 97, in run_advanced_structures_demo
    result1 = solver1.solve_steady_state(
        Q_target=Q_initial,
    ...<4 lines>...

```

### 12_advanced_optimized_v2.py

- **返回码**: 1
- **错误信息**:
```
Traceback (most recent call last):
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\12_advanced_optimized_v2.py", line 398, in <module>
    validator = run_optimized_example()
  File "E:\OneDrive\Documents\GitHub\Test\HydroClaude\examples\example_01_canal_flow\scripts\12_advanced_optimized_v2.py", line 152, in run_optimized_example
    print(f"  目标流量: {Q_target} m\xb3/s")
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'gbk' codec can't e
```


---

**Generated with Claude Code**
**Co-Authored-By: Claude <noreply@anthropic.com>**
