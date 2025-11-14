# HydroClaude求解器性能基准测试报告

**生成时间**: 2025-11-14 04:41:35

---

## 测试概览

- **场景数量**: 1
- **求解器数量**: 2
- **总测试数**: 2

### 测试场景

| 编号 | 场景名称 | 网格点数 | 渠道长度 (m) | 结构数量 | 说明 |
|------|---------|---------|-------------|---------|------|
| 1 | Single Gate | 51 | 1000.0 | 1 | Single gate benchmark |

### 测试求解器

1. **Continuation**
2. **Newton**

## 性能汇总

### 完整结果表

| 场景 | 求解器 | 收敛 | 迭代次数 | 时间 (s) | 流量误差 (%) | 最终残差 |
|------|-------|------|---------|---------|------------|----------|
| Single Gate | Newton |  | 5 | 0.0085 | 0.0000 | 4.08e-02 |
| Single Gate | Continuation |  | 7 | 0.0136 | 0.0000 | 1.82e-03 |

## 统计分析

### 收敛成功率

| 求解器 | 成功数 | 总数 | 成功率 |
|-------|-------|------|-------|
| Continuation | 1 | 1 | 100.0% |
| Newton | 1 | 1 | 100.0% |

### 平均性能指标

| 求解器 | 平均迭代次数 | 平均时间 (s) | 平均流量误差 (%) |
|-------|------------|------------|----------------|
| Continuation | 7.0 | 0.0136 | 0.0000 |
| Newton | 5.0 | 0.0085 | 0.0000 |

### 加速比分析

**基线**: Continuation

| 场景 | 目标求解器 | 加速比 (x) |
|------|-----------|----------|
| Single Gate | Newton | 1.61x |

## 可视化图表

### Iterations

![iterations](iterations_comparison.png)

### Time

![time](time_comparison.png)

### Speedup

![speedup](speedup_comparison.png)

### Success Rate

![success_rate](success_rate.png)

### Scalability

![scalability](scalability.png)

## 结论

### 关键发现

1. **Newton** 是平均速度最快的求解器 (平均时间: 0.0085s)
2. **Newton** 迭代次数最少 (平均: 5.0次)
3. **Continuation** 成功率最高 (100.0%)

### 使用建议

基于测试结果，我们建议：

- 对于**速度优先**的场景，使用 **Newton**
- 对于**迭代效率优先**的场景，使用 **Newton**
- 对于**鲁棒性优先**的场景，使用 **Continuation**

## 附录

### 测试环境

- **Python版本**: 3.11
- **NumPy版本**: Latest
- **SciPy版本**: Latest
- **操作系统**: Linux

### 参数设置

所有求解器使用以下共同参数：

- 收敛容差: 1e-4
- 最大迭代次数: 30
- 初值: 均匀流

---

*报告由 HydroClaude BenchmarkReporter 自动生成于 2025-11-14 04:41:35*
