# HydroClaude Web 测试规范

> **版本**: v1.0
> **日期**: 2025-11-10
> **范围**: Phase 1-2 水力学模拟系统测试

---

## 📋 目录

1. [测试策略](#1-测试策略)
2. [测试环境](#2-测试环境)
3. [算法验证测试](#3-算法验证测试)
4. [功能测试](#4-功能测试)
5. [性能测试](#5-性能测试)
6. [自动化测试](#6-自动化测试)

---

## 1. 测试策略

### 1.1 测试金字塔

```
          /\
         /E2E\         (10%) 端到端测试 - 20个核心流程
        /------\
       / 集成   \       (30%) 集成测试 - 60个标准案例
      /----------\
     /   单元     \     (60%) 单元测试 - 500+单元
    /--------------\
```

### 1.2 测试类型

| 测试类型 | 目的 | 覆盖率目标 | 执行频率 |
|---------|------|----------|---------|
| **单元测试** | 验证单个函数/组件 | >80% | 每次提交 |
| **算法验证测试** | 验证计算正确性 | 100% | 每日构建 |
| **集成测试** | 验证模块间交互 | 60个标准案例 | 每日构建 |
| **端到端测试** | 验证完整流程 | 20个核心流程 | 发布前 |
| **性能测试** | 验证性能指标 | 基准回归 | 每周 |
| **用户验收测试** | 验证用户需求 | 用户满意度>4.0 | 发布前 |

---

## 2. 测试环境

### 2.1 环境配置

#### 开发环境（Dev）
- **用途**: 开发人员本地测试
- **数据**: 模拟数据
- **自动化**: 单元测试、基础集成测试

#### 测试环境（Test）
- **用途**: 自动化测试、算法验证
- **数据**: 标准测试案例数据
- **自动化**: 完整测试套件

#### 预生产环境（Staging）
- **用途**: 最终验收测试
- **数据**: 生产级数据
- **自动化**: E2E测试、性能测试

### 2.2 测试数据

```
test_data/
├── standard_cases/          # 标准验证案例
│   ├── macdonald/          # MacDonald案例(10个)
│   ├── toro/               # Toro案例(5个)
│   ├── water_hammer/       # 水击案例(5个)
│   └── engineering/        # 工程案例(15个)
├── reference_results/       # 参考结果
│   ├── engine_direct/      # 核心引擎直接运行结果
│   ├── analytical/         # 解析解
│   └── measured/           # 实测数据
└── extreme_cases/          # 极端场景
    ├── numerical/          # 数值极端场景
    └── system/             # 系统极端场景
```

---

## 3. 算法验证测试

**最高优先级**：确保Web系统计算结果与HydroClaude核心引擎完全一致

### 3.1 明渠算法验证（35个案例）

#### 3.1.1 MacDonald标准案例（10个）

**测试目标**：验证明渠求解器在标准工况下的准确性

| 编号 | 案例名称 | 流态 | 验收标准 |
|-----|---------|-----|---------|
| M01 | Subcritical Flow | 缓流 | 误差 <1e-6 |
| M02 | Transcritical Flow with Shock | 跨临界+激波 | 激波位置误差 <0.1% |
| M03 | Transcritical Flow over Bump | 跨临界+凸起 | 临界点位置准确 |
| M04 | Dam Break (Dry Bed) | 溃坝干床 | 波阵面位置误差 <0.5% |
| M05 | Dam Break (Wet Bed) | 溃坝湿床 | 水深误差 <1% |
| M06 | Steady Flow over Bump | 稳态流+凸起 | 静水平衡保持 |
| M07 | Wetting and Drying | 干湿交替 | 不出现负水深 |
| M08 | Wide Range of Flow | 宽范围流动 | 全域收敛 |
| M09 | Channel Constriction | 渠道收缩 | 质量守恒误差 <1e-6 |
| M10 | Complex Topography | 复杂地形 | 稳定性良好 |

**测试步骤**：
```python
# 自动化测试脚本
def test_macdonald_case_01():
    # 1. 通过API提交仿真
    response = api.post('/simulations', json={
        'model_id': 'macdonald_01',
        'solver_type': 'godunov_fvm',
        'solver_config': {...}
    })
    task_id = response.json()['task_id']

    # 2. 等待完成
    wait_for_completion(task_id, timeout=300)

    # 3. 获取结果
    result_web = api.get(f'/simulations/{task_id}/results/timeseries')

    # 4. 加载参考结果（核心引擎直接运行）
    result_engine = load_reference('macdonald_01')

    # 5. 对比验证
    assert_results_equal(
        result_web,
        result_engine,
        tolerance=1e-6,
        variables=['h', 'Q', 'V']
    )

    # 6. 验证关键指标
    assert result_web['mass_conservation_error'] < 1e-6
    assert result_web['converged'] == True
```

#### 3.1.2 Toro标准案例（5个）

| 编号 | 案例名称 | 特点 | 验收标准 |
|-----|---------|-----|---------|
| T01 | Dam Break Problem | 经典溃坝 | 与解析解误差 <1% |
| T02 | Rare Rarefaction | 稀疏波 | 波速误差 <0.5% |
| T03 | Shock Tube | 激波管 | 激波捕捉准确 |
| T04 | Stationary Contact | 静止接触 | 保持不动 |
| T05 | Strong Shock | 强激波 | 数值振荡 <5% |

#### 3.1.3 工程验证案例（20个）

**a) 洪水演进（5个案例）**
- [ ] 山区河道洪水演进
- [ ] 平原河道洪水演进
- [ ] 水库溃坝洪水演进
- [ ] 城市内涝演进
- [ ] 潮汐河段洪水

**验收标准**：
- 与实测数据误差 <10%（峰值流量）
- 洪峰到达时间误差 <10%
- 水位过程相关系数 >0.9

**b) 灌溉渠道（5个案例）**
- [ ] 梯形渠道恒定流
- [ ] 渠道水位调节
- [ ] 渠道闸门控制
- [ ] 分水口流量分配
- [ ] 渠道干湿交替

**验收标准**：
- 流量分配误差 <5%
- 水位调节精度 <0.05m
- 质量守恒误差 <1e-5

**c) 城市排水（5个案例）**
- [ ] 雨水管网演算
- [ ] 暴雨径流模拟
- [ ] 排水泵站调度
- [ ] 内涝积水演进
- [ ] 溢流堰溢流

**验收标准**：
- 积水深度误差 <0.1m
- 管网流量误差 <10%
- 泵站启停准确

**d) 水工建筑物（5个案例）**
- [ ] 溢洪道泄流
- [ ] 闸门调度
- [ ] 跌水消能
- [ ] 渡槽流动
- [ ] 倒虹吸

**验收标准**：
- 泄流能力误差 <5%
- 局部水头损失误差 <10%
- 数值稳定

---

### 3.2 管道算法验证（20个案例）

#### 3.2.1 水击标准案例（5个）

| 编号 | 案例名称 | 特点 | 验收标准 |
|-----|---------|-----|---------|
| P01 | Sudden Valve Closure | 快速关阀 | 压力峰值误差 <2% |
| P02 | Gradual Valve Closure | 缓慢关阀 | 压力波形一致 |
| P03 | Pump Shutdown | 泵站停机 | 负压识别准确 |
| P04 | Surge Tank | 调压室作用 | 调压效果准确 |
| P05 | Air Chamber | 空气室作用 | 压力衰减正确 |

**测试重点**：
- 压力波速计算准确性
- 波的传播、反射、叠加
- 摩擦损失计算
- 边界条件处理

#### 3.2.2 管网案例（10个）

**串联管网**（3个）
- [ ] 双管串联
- [ ] 三管串联+调压室
- [ ] 长管串联+摩阻

**树形管网**（3个）
- [ ] 简单分支
- [ ] 多级分支
- [ ] 不等径分支

**环形管网**（4个）
- [ ] 单环网
- [ ] 双环网
- [ ] 复杂环网
- [ ] 混合管网

**验收标准**：
- 节点压力误差 <1%
- 管段流量误差 <2%
- 迭代收敛
- 质量守恒误差 <1e-6

#### 3.2.3 阀门操作案例（5个）

- [ ] 止回阀作用
- [ ] 泄压阀启闭
- [ ] 调节阀调节
- [ ] 多阀协同
- [ ] 阀门故障

---

### 3.3 混合系统验证（10个案例）

#### 3.3.1 级联水库（3个）
- [ ] Example 17 - 水库基础
- [ ] Example 18 - 级联水电
- [ ] 梯级水库调度

#### 3.3.2 水电站系统（3个）
- [ ] Example 03 - 水轮机演示
- [ ] Example 04 - 水电站系统
- [ ] Example 06 - 完整水电系统

#### 3.3.3 供水系统（2个）
- [ ] Example 19 - 引水工程
- [ ] Example 20 - 城市供水

#### 3.3.4 灌溉系统（2个）
- [ ] Example 21 - 灌溉优化
- [ ] 灌区渠系

---

### 3.4 极端场景测试（15个案例）

#### 3.4.1 数值稳定性（8个）

**干湿交替**
- [ ] 干床溃坝
- [ ] 潮滩淹没
- [ ] 渠道断流
- [ ] 负水深处理

**激波捕捉**
- [ ] 强激波
- [ ] 激波反射
- [ ] 激波碰撞
- [ ] 激波衰减

#### 3.4.2 边界极端（4个）
- [ ] 极端流量（0.01x - 100x）
- [ ] 阶跃变化
- [ ] 高频振荡
- [ ] 周期性边界

#### 3.4.3 系统极端（3个）
- [ ] 超大规模（5000+网格）
- [ ] 复杂拓扑（100+组件）
- [ ] 长时间仿真（10000s）

---

## 4. 功能测试

### 4.1 建模功能测试

#### 4.1.1 组件添加测试
```javascript
describe('组件添加', () => {
  test('拖拽添加明渠组件', async () => {
    // 模拟拖拽操作
    await page.dragAndDrop('#component-canal', '#canvas');

    // 验证组件已添加
    const components = await page.$$('[data-testid^="component-"]');
    expect(components).toHaveLength(1);

    // 验证默认参数
    const params = await getComponentParams('canal_1');
    expect(params.length).toBeGreaterThan(0);
    expect(params.width).toBeGreaterThan(0);
  });
});
```

#### 4.1.2 参数配置测试
- [ ] 参数输入验证（范围、类型）
- [ ] 参数联动（如：流速 = 流量 / 面积）
- [ ] 单位转换
- [ ] 默认值推荐

#### 4.1.3 拓扑验证测试
- [ ] 检测断开组件
- [ ] 检测循环依赖
- [ ] 检测入口/出口缺失
- [ ] 检测参数冲突

### 4.2 仿真功能测试

#### 4.2.1 任务提交
- [ ] 正常提交
- [ ] 并发提交
- [ ] 参数验证失败
- [ ] 模型验证失败

#### 4.2.2 任务执行
- [ ] 排队机制
- [ ] 优先级处理
- [ ] 超时处理
- [ ] 取消操作

#### 4.2.3 进度监控
- [ ] WebSocket实时更新
- [ ] 进度条显示
- [ ] 关键指标显示
- [ ] 异常检测

### 4.3 可视化功能测试

#### 4.3.1 2D图表
- [ ] 折线图正确显示
- [ ] 交互操作（缩放、平移）
- [ ] 数据探针
- [ ] 导出图片

#### 4.3.2 3D可视化
- [ ] 场景渲染
- [ ] 视角控制
- [ ] 动画播放
- [ ] 性能测试（帧率）

#### 4.3.3 数据导出
- [ ] CSV格式
- [ ] JSON格式
- [ ] Excel格式
- [ ] 报表生成

---

## 5. 性能测试

### 5.1 计算性能基准

#### 5.1.1 基准案例性能

| 案例 | 网格数 | 时间步 | 目标时间 | 基准 |
|-----|-------|-------|---------|------|
| 小规模 | 100 | 1000 | <30s | 核心引擎 |
| 中等规模 | 500 | 2000 | <2min | 核心引擎 |
| 大规模 | 1000 | 5000 | <5min | 核心引擎 |
| 超大规模 | 5000 | 10000 | <30min | 商业软件 |

**测试脚本**：
```python
import time
import pytest

@pytest.mark.performance
def test_performance_small_scale():
    # 提交小规模仿真
    start_time = time.time()
    task_id = submit_simulation('small_scale_100_cells')

    # 等待完成
    wait_for_completion(task_id)
    duration = time.time() - start_time

    # 验证时间
    assert duration < 30, f"Small scale simulation took {duration}s, expected <30s"

    # 对比核心引擎性能
    engine_duration = run_engine_directly('small_scale_100_cells')
    overhead = duration - engine_duration
    assert overhead < 5, f"API overhead {overhead}s too large"
```

#### 5.1.2 加速比测试

**Numba加速验证**：
```python
def test_numba_acceleration():
    # 不启用Numba
    config_no_numba = {'use_numba': False}
    duration_no_numba = run_simulation(config_no_numba)

    # 启用Numba
    config_numba = {'use_numba': True}
    duration_numba = run_simulation(config_numba)

    # 验证加速比
    speedup = duration_no_numba / duration_numba
    assert speedup > 5, f"Numba speedup {speedup}x, expected >5x"
```

### 5.2 并发性能测试

#### 5.2.1 并发任务处理

| 并发数 | 预期行为 | 验收标准 |
|-------|---------|---------|
| 10 | 全部同时执行 | 成功率 100% |
| 100 | 排队等待 | 成功率 >99% |
| 1000 | 限流保护 | 无系统崩溃 |

**压力测试脚本**（Locust）：
```python
from locust import HttpUser, task, between

class SimulationUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def submit_simulation(self):
        response = self.client.post("/v1/simulations", json={
            "model_id": "test_model",
            "solver_type": "godunov_fvm",
            ...
        })
        if response.status_code == 201:
            task_id = response.json()['task_id']
            self.client.get(f"/v1/simulations/{task_id}")
```

### 5.3 API性能测试

#### 5.3.1 响应时间基准

| 端点 | p50 | p95 | p99 | QPS |
|-----|-----|-----|-----|-----|
| GET /projects | <50ms | <100ms | <200ms | >500 |
| GET /models | <50ms | <100ms | <200ms | >500 |
| POST /simulations | <100ms | <200ms | <500ms | >100 |
| GET /results | <50ms | <150ms | <300ms | >200 |

### 5.4 前端性能测试

#### 5.4.1 Lighthouse指标

| 指标 | 目标 |
|-----|------|
| Performance | >90 |
| Accessibility | >90 |
| Best Practices | >90 |
| SEO | >80 |

#### 5.4.2 Web Vitals

| 指标 | 目标 |
|-----|------|
| LCP (Largest Contentful Paint) | <2.5s |
| FID (First Input Delay) | <100ms |
| CLS (Cumulative Layout Shift) | <0.1 |

---

## 6. 自动化测试

### 6.1 持续集成流程

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest tests/unit/ --cov

  algorithm-validation:
    runs-on: ubuntu-latest
    needs: unit-test
    steps:
      - name: Run MacDonald cases
        run: python tests/validation/run_macdonald_cases.py
      - name: Run Toro cases
        run: python tests/validation/run_toro_cases.py
      - name: Compare results
        run: python tests/validation/compare_results.py
      - name: Generate report
        run: python tests/validation/generate_report.py
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: validation-report
          path: reports/validation_report.html

  performance-test:
    runs-on: ubuntu-latest
    needs: algorithm-validation
    steps:
      - name: Run performance benchmarks
        run: pytest tests/performance/ --benchmark
      - name: Compare with baseline
        run: python tests/performance/compare_baseline.py
```

### 6.2 测试报告

#### 6.2.1 验证报告模板

```
HydroClaude Web 算法验证报告
日期: 2025-11-10
版本: v1.0.0

总体统计
========
测试案例总数: 65
通过: 65
失败: 0
通过率: 100%

明渠测试 (35个案例)
===================
MacDonald案例: 10/10 ✅
Toro案例: 5/5 ✅
工程案例: 20/20 ✅

管道测试 (20个案例)
===================
水击案例: 5/5 ✅
管网案例: 10/10 ✅
阀门案例: 5/5 ✅

混合系统 (10个案例)
===================
级联水库: 3/3 ✅
水电站: 3/3 ✅
供水系统: 2/2 ✅
灌溉系统: 2/2 ✅

详细结果
========
案例: MacDonald_Case_01
状态: ✅ 通过
误差: 1.23e-7 (目标: <1e-6)
执行时间: 15.3s
质量守恒: 0.000000%

...
```

---

## 7. 验收标准总结

### 7.1 Phase 1 完成标准

**算法验证**
- ✅ 65个标准测试案例100%通过
- ✅ 与核心引擎误差 <1e-6
- ✅ 与理论解误差 <1%
- ✅ 与实测数据误差 <5%

**功能完整性**
- ✅ 核心功能100%可用
- ✅ 用户流程完整
- ✅ 无阻塞性Bug

**性能达标**
- ✅ 计算速度达到基准
- ✅ API响应时间 <200ms (p95)
- ✅ 前端性能 Lighthouse >90

### 7.2 Phase 2 完成标准

**全面测试**
- ✅ 极端场景测试通过
- ✅ 压力测试通过
- ✅ 7x24小时稳定性测试

**用户验收**
- ✅ Beta测试用户满意度 >4.0/5.0
- ✅ NPS >30
- ✅ 零严重Bug

---

**文档版本**: v1.0
**最后更新**: 2025-11-10
**适用范围**: Phase 1-2 水力学模拟系统
