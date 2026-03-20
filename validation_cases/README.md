# 国际标准验证案例库

**目的**: 通过国际标准案例验证HydroClaude求解器精度

## 案例分类

### 1. 解析解案例 (`analytical/`)
- Dam Break (Ritter Solution)
- Steady Uniform Flow
- Critical Flow

### 2. 文献案例 (`literature/`)
- MacDonald (1997) - 11个标准案例
- Goutal & Maurel (1997) - CADAM项目
- LeVeque (2002) - 标准测试

### 3. 工程/外部来源案例 (`engineering/`)
- Bridge Assessment
- Flood Routing
- Irrigation Canal
- Urban Drainage
- Water Resources Optimization
- HEC-RAS provenance scaffolds for disputed externally sourced fixtures

## 验收标准

每个案例必须包含：
1. 问题描述（物理场景）
2. 参考解（解析解或HEC-RAS结果）
3. HydroClaude实现
4. 误差分析报告
5. 对比图表

## 精度目标

| 案例类型 | 目标精度 |
|---------|---------|
| 解析解对比 | < 2% |
| HEC-RAS对比 | < 10% |
| 文献对比 | < 15% |

## 当前状态

- [ ] Case 1: Dam Break (Ritter) - 实施中
- [ ] Case 2: MacDonald Case 1
- [ ] Case 3: Steady Flow M1/M2
- [ ] Case 4: Gate Operation
- [x] HEC-RAS steady-flow provenance scaffold created
- [ ] HEC-RAS source artifacts attached and revalidated
- [ ] ...

## Disputed External Benchmarks

- `validation_cases/engineering/hec_ras_steady_flow_example_3_1/README.md`
  - Canonical audit entry point for the disputed `HEC-RAS Steady Flow Benchmark`
  - Current status: `external_review_needed`

**更新日期**: 2026-03-20
