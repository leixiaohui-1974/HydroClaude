# Stage 2 Phase 2.2 规划 - 数值方法验证套件扩展

**日期**: 2025-10-29
**前序阶段**: Phase 2.1 (混合流态求解器) - 95%完成
**本阶段目标**: 扩展数值方法测试覆盖率，建立完整验证体系
**预估时间**: 5-7天

---

## 📊 阶段概述

### 当前状态 (Phase 2.1完成)

**已实现功能**:
- ✅ Entropy Fix (Harten-Hyman correction)
- ✅ Critical Flow Treatment (Lax-Friedrichs dissipation)
- ✅ Froude数计算和流态识别
- ✅ 配置文件支持
- ✅ 完整文档体系 (1821行)

**测试覆盖**:
- ✅ P1测试: 10个通过
- ✅ P2测试: 4个通过
- ⏭️ 4个测试跳过（有文档说明）

**文档资产**:
- ✅ 技术文档 (701行)
- ✅ 用户指南 (671行)
- ✅ 会话记录 (629行)

### Phase 2.2目标

**核心目标**: 建立完整的数值方法验证体系

**具体目标**:
1. **扩展测试覆盖率**: 从18个测试 → 30+个测试
2. **提高测试质量**: 增加定量验证和误差分析
3. **覆盖所有数值方法**: WENO3、Well-Balanced、Shock-Capturing、Mixed-Flow
4. **建立性能基准**: CPU时间、内存使用、收敛性
5. **完善V&V文档**: 验证与确认技术报告

**成功标准**:
- [ ] 30+个数值方法测试（P1+P2+P3）
- [ ] 测试覆盖率 >60% (核心数值方法)
- [ ] 所有测试通过或有文档说明
- [ ] 完整的V&V技术报告
- [ ] 性能基准数据库

---

## 🎯 任务分解

### Task 2.2.1: WENO3综合验证 (1-2天)

**目标**: 验证WENO3在各种场景下的性能和准确性

#### 1. 激波捕捉验证

**测试文件**: `tests/numerical_methods/test_shock_capturing.py`

**测试案例**:
1. **一维Sod激波管** (理论解验证)
   - 初始条件: 左侧高水位，右侧低水位，中间diaphragm
   - 验证: 激波位置、激波强度、接触间断
   - 对比: 解析解 (Riemann problem)
   - 指标: L1/L2/L∞误差 < 阈值

2. **MacDonald Test 3 (溃坝)** - 详细分析
   - 验证: 激波传播速度
   - 验证: 质量守恒 (<1%误差)
   - 验证: 能量耗散合理性
   - 对比: 1阶、2阶、3阶WENO精度差异

3. **MacDonald Test 4 Realistic** (有摩阻水跃)
   - 验证: 水跃位置和强度
   - 验证: 前后Froude数变化
   - 验证: 能量损失符合Belanger方程
   - 对比: 启用/禁用critical_flow_treatment

**实现要点**:
```python
@pytest.mark.p2
def test_shock_capturing_accuracy():
    """验证WENO3激波捕捉精度"""
    # 1. Sod激波管
    # 2. 计算数值解
    # 3. 对比解析解
    # 4. 计算误差范数
    assert L1_error < 0.05
    assert L2_error < 0.03
    assert Linf_error < 0.10

@pytest.mark.p2
def test_shock_propagation_speed():
    """验证激波传播速度"""
    # 理论速度 vs 数值速度
    shock_speed_theory = ...
    shock_speed_numerical = ...
    error = abs(shock_speed_numerical - shock_speed_theory) / shock_speed_theory
    assert error < 0.02  # 2%误差

@pytest.mark.p2
def test_weno3_vs_first_order():
    """对比WENO3和1阶格式在激波问题上的表现"""
    # 同一问题，不同空间精度
    results_1st = run_simulation(spatial_order=1)
    results_3rd = run_simulation(spatial_order=3)

    # WENO3应该有更小的数值耗散
    assert results_3rd['shock_width'] < results_1st['shock_width']
    assert results_3rd['mass_error'] < results_1st['mass_error']
```

**预期结果**:
- 3个新增P2测试
- WENO3激波捕捉能力量化
- 精度对比报告

#### 2. WENO3空间收敛性验证

**测试文件**: `tests/numerical_methods/test_convergence.py`

**测试案例**:
1. **光滑解的收敛性**
   - 问题: 小扰动波传播 (无激波)
   - 网格序列: 50, 100, 200, 400单元
   - 验证: 3阶收敛率 (slope ≈ 3.0)
   - 方法: 最小二乘拟合 log(error) vs log(dx)

2. **制造解法 (MMS)**
   - 构造精确解: h(x,t) = h0 + A*sin(kx - ωt)
   - 添加源项使其满足方程
   - 验证: 各阶WENO的收敛阶

**实现要点**:
```python
@pytest.mark.p3
def test_weno3_convergence_rate():
    """验证WENO3在光滑解上的收敛率"""
    dx_list = [10.0, 5.0, 2.5, 1.25]  # 网格尺寸
    errors = []

    for dx in dx_list:
        n_cells = int(L / dx)
        solver = build_solver(n_cells=n_cells, spatial_order=3)
        result = solver.run(t_end=10.0)
        error = compute_l2_error(result, exact_solution)
        errors.append(error)

    # 拟合收敛率
    slope, _ = np.polyfit(np.log(dx_list), np.log(errors), 1)

    print(f"收敛率: {slope:.2f} (理论: 3.0)")
    assert 2.5 < slope < 3.5  # 允许一定偏差
```

**预期结果**:
- 2个新增P3测试
- 收敛率曲线图
- 与理论收敛阶对比报告

#### 3. WENO3稳定性分析

**测试文件**: `tests/numerical_methods/test_weno3_stability.py`

**测试案例**:
1. **CFL数敏感性**
   - CFL = 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8
   - 验证: CFL≤0.5时稳定，CFL>0.5可能失稳
   - 记录: 计算时间 vs CFL

2. **长时间稳定性**
   - 运行1000+个周期
   - 验证: 无数值振荡累积
   - 验证: 质量守恒长期保持

**预期结果**:
- 2个新增P3测试
- CFL稳定性边界图
- 长时间稳定性报告

---

### Task 2.2.2: 混合流态综合测试 (1-2天)

**目标**: 验证entropy fix和critical flow treatment在各种流态转换中的表现

**测试文件**: `tests/numerical_methods/test_mixed_flow_comprehensive.py`

#### 1. 跨临界流综合测试

**测试案例**:
1. **喉道/卡口流动** (亚临界→临界→超临界)
   - 几何: 渐缩-喉道-渐扩
   - 初始: 亚临界流
   - 验证: 喉道处Fr≈1.0
   - 验证: 下游超临界流

2. **陡坡变缓坡** (超临界→临界→亚临界)
   - 上游: S0=0.05 (陡坡)
   - 下游: S0=0.001 (缓坡)
   - 验证: 转换点Fr≈1.0
   - 验证: 无非物理振荡

3. **堰流** (submerged to free-flow transition)
   - 配置: 下游水位变化
   - 验证: 淹没堰流 → 自由堰流转换
   - 验证: Fr变化连续

**实现要点**:
```python
@pytest.mark.p2
def test_throat_critical_flow():
    """测试喉道临界流控制"""
    # 配置渐缩渐扩渠道
    config = {
        'geometry': {
            'type': 'variable_width',
            'width_function': lambda x: width_throat(x)
        },
        'solver': {
            'entropy_fix': True,
            'critical_flow_treatment': True
        }
    }

    engine = SimulationEngine(config)
    engine.run()

    # 找到喉道位置
    throat_idx = np.argmin(engine.solver.B)
    Fr_throat = engine.solver.compute_froude_number()[throat_idx]

    # 验证临界流
    assert 0.95 < Fr_throat < 1.05, f"喉道Fr={Fr_throat:.3f} 偏离1.0"

    # 验证无振荡
    h = engine.solver.h
    oscillation = np.max(np.abs(np.diff(h, n=2)))
    assert oscillation < 0.1 * np.mean(h)

@pytest.mark.p2
def test_steep_to_mild_slope_transition():
    """测试陡坡到缓坡流态转换"""
    # 分段坡度
    L1, L2 = 500.0, 500.0
    S1, S2 = 0.05, 0.001

    # ... 配置和运行

    # 找到Fr=1的位置（临界流点）
    Fr = engine.solver.compute_froude_number()
    critical_idx = np.argmin(np.abs(Fr - 1.0))
    x_critical = engine.solver.x[critical_idx]

    # 验证临界点在坡度转换附近
    assert 400 < x_critical < 600, f"临界点位置={x_critical:.1f}m 异常"

    # 验证上游超临界，下游亚临界
    Fr_upstream = np.mean(Fr[:critical_idx])
    Fr_downstream = np.mean(Fr[critical_idx:])
    assert Fr_upstream > 1.1, "上游应为超临界流"
    assert Fr_downstream < 0.9, "下游应为亚临界流"
```

**预期结果**:
- 4个新增P2测试
- 混合流态转换验证报告
- Fr分布可视化

#### 2. Entropy Fix效果对比

**测试案例**:
1. **有无entropy fix的对比**
   - 同一问题（如MacDonald Test 2）
   - 对比: 解的光滑性、质量守恒、计算时间
   - 验证: entropy fix改善效果

**实现要点**:
```python
@pytest.mark.p2
def test_entropy_fix_effectiveness():
    """测试entropy fix的有效性"""
    # 运行两次：with/without entropy fix
    result_no_fix = run_simulation(entropy_fix=False)
    result_with_fix = run_simulation(entropy_fix=True)

    # 对比质量守恒
    mass_error_no_fix = result_no_fix['mass_error']
    mass_error_with_fix = result_with_fix['mass_error']

    print(f"质量误差对比:")
    print(f"  无Entropy Fix: {mass_error_no_fix:.4f}%")
    print(f"  有Entropy Fix: {mass_error_with_fix:.4f}%")

    # 验证改善
    assert mass_error_with_fix < mass_error_no_fix * 1.2  # 允许相当或略差，但不能差太多

    # 对比解的振荡
    oscillation_no_fix = compute_oscillation(result_no_fix['h'])
    oscillation_with_fix = compute_oscillation(result_with_fix['h'])

    print(f"振荡指标对比:")
    print(f"  无Entropy Fix: {oscillation_no_fix:.6f}")
    print(f"  有Entropy Fix: {oscillation_with_fix:.6f}")
```

**预期结果**:
- 2个新增P2测试
- Entropy fix效果量化报告

---

### Task 2.2.3: CFL稳定性系统测试 (1天)

**目标**: 系统测试不同CFL数下的稳定性和性能

**测试文件**: `tests/numerical_methods/test_cfl_stability.py`

#### 测试矩阵

| 测试场景 | CFL范围 | 预期结果 |
|---------|---------|----------|
| 平稳流 (MacDonald 1) | 0.1-0.9 | 全部稳定 |
| 激波 (MacDonald 3) | 0.1-0.6 | CFL≤0.5稳定 |
| 临界流 (MacDonald 2) | 0.1-0.5 | CFL≤0.4推荐 |
| 混合流态 | 0.1-0.4 | CFL≤0.3最佳 |

**实现要点**:
```python
@pytest.mark.p3
@pytest.mark.parametrize("cfl", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
def test_cfl_stability_smooth_flow(cfl):
    """测试平稳流下的CFL稳定性"""
    config = create_macdonald1_config(cfl=cfl)
    engine = SimulationEngine(config)

    try:
        engine.run()
        mass_error = engine.solver.get_mass_conservation_error()

        # 验证稳定性
        assert not np.any(np.isnan(engine.solver.h)), "出现NaN，失稳"
        assert mass_error < 5.0, f"质量误差{mass_error:.2f}% >5%"

        print(f"CFL={cfl:.1f}: ✅ 稳定 (质量误差={mass_error:.4f}%)")
    except Exception as e:
        print(f"CFL={cfl:.1f}: ❌ 失稳 ({str(e)})")
        pytest.fail(f"CFL={cfl:.1f}时失稳")

@pytest.mark.p3
def test_cfl_performance_tradeoff():
    """测试CFL数与计算性能的权衡"""
    cfl_list = [0.1, 0.2, 0.3, 0.4, 0.5]
    times = []
    steps = []

    for cfl in cfl_list:
        start = time.time()
        config = create_test_config(cfl=cfl)
        engine = SimulationEngine(config)
        engine.run()
        elapsed = time.time() - start

        times.append(elapsed)
        steps.append(engine.solver.step_count)

    # 生成性能报告
    print("\nCFL性能权衡:")
    for cfl, t, n in zip(cfl_list, times, steps):
        print(f"  CFL={cfl:.1f}: {t:.2f}s, {n}步")

    # 绘制性能曲线（可选）
    # plt.plot(cfl_list, times)
    # plt.xlabel('CFL')
    # plt.ylabel('计算时间 (s)')
```

**预期结果**:
- 4个新增P3测试
- CFL稳定性矩阵
- CFL性能权衡报告

---

### Task 2.2.4: 质量守恒深入验证 (0.5天)

**目标**: 系统验证质量守恒在各种场景下的表现

**测试文件**: `tests/numerical_methods/test_mass_conservation_comprehensive.py`

#### 测试案例

1. **长时间质量守恒**
   - 运行1000+时间步
   - 验证: 累积误差<0.5%

2. **干湿界面质量守恒**
   - 溃坝到干床
   - 验证: 水舌前进时无质量损失

3. **边界条件质量守恒**
   - 流量边界 vs 水位边界
   - 验证: 流入量 = 流出量 + 存储变化

**实现要点**:
```python
@pytest.mark.p2
def test_long_term_mass_conservation():
    """测试长时间质量守恒"""
    config = create_config(t_end=1000.0)  # 长时间
    engine = SimulationEngine(config)

    mass_initial = engine.solver._compute_total_mass()
    mass_history = [mass_initial]

    # 每100s记录一次
    for t in range(100, 1001, 100):
        engine.run_to(t)
        mass_history.append(engine.solver._compute_total_mass())

    # 计算最大偏差
    mass_errors = [(m - mass_initial)/mass_initial * 100 for m in mass_history]
    max_error = max(abs(e) for e in mass_errors)

    print(f"\n长时间质量守恒:")
    print(f"  初始质量: {mass_initial:.2f} m³")
    print(f"  最终质量: {mass_history[-1]:.2f} m³")
    print(f"  最大误差: {max_error:.4f}%")

    assert max_error < 0.5, f"长时间质量误差{max_error:.4f}% >0.5%"
```

**预期结果**:
- 3个新增P2测试
- 质量守恒验证报告

---

### Task 2.2.5: 性能基准数据库 (1天)

**目标**: 建立系统的性能基准，用于回归测试和性能监控

**文件**: `tests/performance/benchmark_suite.py`

#### 基准测试集

**标准测试场景**:
1. MacDonald Test 1 (平稳流) - 基线
2. MacDonald Test 3 (激波) - 计算密集
3. 大规模网格 (10000单元) - 内存测试
4. 长时间模拟 (10000步) - 稳定性测试

**性能指标**:
- CPU时间 (总时间、每步平均时间)
- 内存使用 (峰值内存、平均内存)
- 收敛步数
- 数值精度 (L1/L2误差)

**实现要点**:
```python
@pytest.mark.benchmark
def test_benchmark_macdonald1():
    """MacDonald Test 1 性能基准"""
    import time
    import psutil

    config = create_macdonald1_config()

    # 记录初始状态
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024**2  # MB

    # 运行模拟
    start = time.time()
    engine = SimulationEngine(config)
    engine.run()
    elapsed = time.time() - start

    # 记录性能指标
    mem_after = process.memory_info().rss / 1024**2  # MB
    mem_used = mem_after - mem_before

    benchmark_result = {
        'test': 'macdonald1',
        'cpu_time': elapsed,
        'memory_mb': mem_used,
        'steps': engine.solver.step_count,
        'time_per_step': elapsed / engine.solver.step_count,
        'mass_error': engine.solver.get_mass_conservation_error()
    }

    # 保存到数据库
    save_benchmark(benchmark_result)

    print(f"\n性能基准 - MacDonald Test 1:")
    print(f"  CPU时间: {elapsed:.2f}s")
    print(f"  内存使用: {mem_used:.1f} MB")
    print(f"  计算步数: {engine.solver.step_count}")
    print(f"  平均每步: {elapsed/engine.solver.step_count*1000:.2f} ms")

    # 性能回归检查（与历史数据对比）
    baseline = load_baseline('macdonald1')
    if baseline:
        speedup = baseline['cpu_time'] / elapsed
        print(f"  vs 基线: {speedup:.2f}x")

def save_benchmark(result):
    """保存基准结果到JSON数据库"""
    import json
    from pathlib import Path
    from datetime import datetime

    db_file = Path('tests/performance/benchmark_db.json')

    # 加载现有数据
    if db_file.exists():
        with open(db_file) as f:
            db = json.load(f)
    else:
        db = {'benchmarks': []}

    # 添加时间戳
    result['timestamp'] = datetime.now().isoformat()
    result['git_commit'] = get_git_commit()

    # 保存
    db['benchmarks'].append(result)
    with open(db_file, 'w') as f:
        json.dump(db, f, indent=2)
```

**预期结果**:
- 4个基准测试
- JSON性能数据库
- 性能趋势可视化脚本

---

## 📚 文档任务

### Task 2.2.6: V&V技术报告 (1-2天)

**文件**: `docs/VERIFICATION_AND_VALIDATION_REPORT.md`

**内容结构**:

#### 1. Executive Summary (2-3页)
- 验证与确认目标
- 关键发现
- 测试通过率
- 推荐使用场景

#### 2. 数值方法验证 (10-15页)
- **WENO3验证**
  - 激波捕捉精度
  - 空间收敛性
  - CFL稳定性
  - 与1阶/2阶对比

- **Entropy Fix验证**
  - 效果量化
  - 适用场景
  - 性能开销

- **Critical Flow Treatment验证**
  - 临界流稳定性
  - 混合流态表现
  - 参数敏感性

#### 3. 标准测试验证 (15-20页)
- **MacDonald Test Suite**
  - Test 1: Backwater Curve ✅
  - Test 2: Drawdown Curve ✅
  - Test 3: Dam Break ✅
  - Test 4: Hydraulic Jump (Realistic) ✅
  - Test 5: Wide Channel ✅

- **Dam Break (Ritter Solution)** ✅

#### 4. 质量保证 (5-10页)
- 质量守恒验证
- 能量耗散分析
- 数值稳定性
- 长时间稳定性

#### 5. 性能基准 (5页)
- CPU时间基准
- 内存使用基准
- 可扩展性分析
- 与其他求解器对比

#### 6. 已知限制 (3-5页)
- WENO3无摩阻强激波限制
- CFL数限制
- 网格分辨率要求
- 未来改进方向

#### 7. 结论与建议 (2-3页)
- 验证完成度评估
- 推荐使用场景
- 不推荐场景
- 未来工作

**预期**: 50-70页完整技术报告

---

## 🎯 成功标准

### 定量指标

| 指标 | 当前 | 目标 | 评估 |
|------|------|------|------|
| P1+P2+P3测试数量 | 18 | 30+ | 增加12+个测试 |
| 测试通过率 | 14/18 (78%) | 25/30+ (80%+) | 保持或提高 |
| 测试覆盖率 | ~40% | >60% | 核心数值方法 |
| 文档页数 | 50 (会话+技术) | 120+ | 增加V&V报告 |
| 性能基准 | 0 | 4+ | 建立基线 |

### 定性目标

- [ ] 完整的WENO3验证体系
- [ ] 混合流态全场景测试
- [ ] CFL稳定性边界明确
- [ ] 质量守恒全面验证
- [ ] 性能基准数据库建立
- [ ] V&V技术报告完成
- [ ] 所有数值方法有文档和测试

---

## 📅 时间规划

### Week 1 (3-4天)

**Day 1-2: WENO3综合验证**
- [ ] Task 2.2.1: 激波捕捉测试
- [ ] Task 2.2.1: 收敛性测试
- [ ] Task 2.2.1: 稳定性测试
- **产出**: 7个新增测试，WENO3验证报告

**Day 3-4: 混合流态综合测试**
- [ ] Task 2.2.2: 跨临界流测试
- [ ] Task 2.2.2: Entropy fix效果对比
- **产出**: 6个新增测试，混合流态报告

### Week 2 (3天)

**Day 5: CFL稳定性和质量守恒**
- [ ] Task 2.2.3: CFL稳定性矩阵
- [ ] Task 2.2.4: 质量守恒深入验证
- **产出**: 7个新增测试，稳定性报告

**Day 6: 性能基准**
- [ ] Task 2.2.5: 性能基准数据库
- **产出**: 4个基准测试，性能数据库

**Day 7: V&V报告**
- [ ] Task 2.2.6: 编写V&V技术报告
- **产出**: 50-70页技术报告

### 灵活调整

如果某些任务提前完成，可以增加：
- 更多边缘场景测试
- 参数敏感性分析
- 与商业软件对比
- 性能优化

---

## 🚀 Phase 2.2完成标志

### 必须完成 (Must Have)

- [x] Phase 2.1完成 (95%)
- [ ] 30+个数值方法测试通过
- [ ] V&V技术报告完成
- [ ] 性能基准数据库建立
- [ ] 所有代码已提交并推送

### 应该完成 (Should Have)

- [ ] 测试覆盖率 >60%
- [ ] WENO3完整验证
- [ ] 混合流态全场景测试
- [ ] CFL稳定性边界明确

### 可选完成 (Nice to Have)

- [ ] 性能优化建议
- [ ] 与HEC-RAS对比测试
- [ ] 参数自动调优工具
- [ ] 测试可视化仪表板

---

## 📊 Phase 2.2完成后的状态

### 代码库

```
HydroClaude/
├── solvers/
│   ├── godunov_fvm_solver.py        ✅ 含entropy fix + critical flow
│   ├── godunov_fvm_weno3.py         ✅ WENO3实现
│   └── ...
├── tests/
│   ├── standard_tests/              ✅ 6个标准测试
│   ├── numerical_methods/           ✅ 20+个数值方法测试
│   │   ├── test_weno3.py           🆕 WENO3综合验证
│   │   ├── test_shock_capturing.py 🆕 激波捕捉
│   │   ├── test_convergence.py     🆕 收敛性
│   │   ├── test_mixed_flow_comprehensive.py 🆕 混合流态
│   │   ├── test_cfl_stability.py   🆕 CFL稳定性
│   │   └── test_mass_conservation_comprehensive.py 🆕 质量守恒
│   └── performance/                 🆕 性能基准
│       ├── benchmark_suite.py      🆕 基准测试集
│       └── benchmark_db.json       🆕 性能数据库
├── docs/
│   ├── CRITICAL_FLOW_TREATMENT_TECHNICAL_DOC.md  ✅ 技术文档
│   ├── CRITICAL_FLOW_USER_GUIDE.md               ✅ 用户指南
│   ├── SESSION_2025_10_29_STAGE2_CRITICAL_FLOW_INTEGRATION.md ✅ 会话记录
│   ├── STAGE2_PHASE2_2_PLANNING.md               ✅ Phase 2.2规划
│   └── VERIFICATION_AND_VALIDATION_REPORT.md     🆕 V&V技术报告
```

### 测试覆盖

- **P1测试**: 10个 (核心功能)
- **P2测试**: 15个 (重要功能)
- **P3测试**: 10个 (性能/边界)
- **性能基准**: 4个
- **总计**: 35+个测试

### 文档资产

- 技术文档: 701行
- 用户指南: 671行
- 会话记录: 629行
- V&V报告: 预计1500+行
- **总计**: 3500+行专业文档

---

## 🔄 与Phase 2.3的衔接

Phase 2.2完成后，将进入**Phase 2.3: 几何模型扩展**

**Phase 2.3预览**:
- 梯形断面支持
- 天然不规则断面
- 变宽渠道
- 断面数据库管理

**Phase 2.2为2.3奠定的基础**:
- ✅ 完整的数值方法验证体系
- ✅ 稳健的测试框架
- ✅ 明确的性能基线
- ✅ V&V文档体系

---

**规划创建时间**: 2025-10-29
**预计Phase 2.2开始时间**: 2025-10-29 (当前会话后续)
**预计Phase 2.2完成时间**: 2025-11-05 (7个工作日后)
**Stage 2 总体进度**: Phase 2.1 (95%) → Phase 2.2 (0%) → 目标总体60%
