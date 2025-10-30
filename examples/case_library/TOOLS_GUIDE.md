# HydroClaude Case Library Tools Guide
# HydroClaude 案例库工具指南

**Version**: 1.0
**Date**: 2025-10-30

---

## 📋 Overview / 概述

This guide describes the convenient tools available for running and testing HydroClaude engineering cases.

本指南描述了用于运行和测试HydroClaude工程案例的便捷工具。

**Available Tools / 可用工具**:
1. **Case Runner** (`run_all_cases.py`) - Run cases individually or in batch
2. **Performance Benchmark** (`benchmark_performance.py`) - Measure performance metrics
3. **Test Suite** (`test_cases.py`) - Comprehensive testing
4. **Makefile** - Quick command shortcuts

---

## 🚀 Quick Start / 快速开始

### Using Makefile (Recommended / 推荐)

The easiest way to use the tools is through the Makefile:

```bash
cd examples/case_library

# Show all available commands / 显示所有可用命令
make help

# Run all cases in quick mode / 快速模式运行所有案例
make run-quick

# Run a specific case / 运行特定案例
make run-case-1     # Hydropower Plant
make run-case-4     # Urban Drainage

# Run tests / 运行测试
make test

# Performance benchmark / 性能基准测试
make benchmark
```

### Direct Python Execution / 直接Python执行

You can also run the tools directly:

```bash
# Case runner / 案例运行器
python run_all_cases.py --help
python run_all_cases.py
python run_all_cases.py --case 1 2 3
python run_all_cases.py --quick

# Performance benchmark / 性能基准测试
python benchmark_performance.py
python benchmark_performance.py --case 1 2

# Test suite / 测试套件
python test_cases.py
```

---

## 🛠️ Tool 1: Case Runner / 案例运行器

**File**: `run_all_cases.py`

### Description / 说明

Convenient tool to run engineering cases individually or in batch, with options for quick mode and benchmarking.

方便的工具来单独或批量运行工程案例，支持快速模式和性能测试。

### Usage / 用法

```bash
# Show help / 显示帮助
python run_all_cases.py --help

# List all cases / 列出所有案例
python run_all_cases.py --list

# Run all cases / 运行所有案例
python run_all_cases.py

# Run specific cases / 运行特定案例
python run_all_cases.py --case 1        # Case 01 only
python run_all_cases.py --case 1 2 3    # Cases 01, 02, 03

# Quick mode (shorter simulations) / 快速模式（较短模拟）
python run_all_cases.py --quick
python run_all_cases.py --case 4 --quick

# Benchmark mode / 性能测试模式
python run_all_cases.py --benchmark
```

### Options / 选项

| Option | Short | Description / 说明 |
|--------|-------|-------------------|
| `--case N` | `-c N` | Run specific case(s) / 运行特定案例 |
| `--quick` | `-q` | Quick mode (shorter) / 快速模式 |
| `--benchmark` | `-b` | Measure performance / 测量性能 |
| `--list` | `-l` | List all cases / 列出所有案例 |
| `--help` | `-h` | Show help / 显示帮助 |

### Output / 输出

The runner provides:
- Real-time progress updates / 实时进度更新
- Success/failure status for each case / 每个案例的成功/失败状态
- Execution times / 执行时间
- Summary statistics / 统计总结

Example output:
```
================================================================================
Running Case 1: Hydropower Plant / 水电站系统
================================================================================

Description: 100MW Francis turbine with surge tank
描述: 100MW法兰西斯水轮机含调压井
Estimated Time: 2-3 min

✓ Case 1 completed successfully in 145.32s

================================================================================
EXECUTION SUMMARY / 执行总结
================================================================================

Total Cases Run / 运行案例总数:    5
Passed / 通过:                     5
Failed / 失败:                     0
Total Time / 总时间:               420.15s (7.0 min)

Success Rate / 成功率: 100.0% 🎉
```

---

## 📊 Tool 2: Performance Benchmark / 性能基准测试

**File**: `benchmark_performance.py`

### Description / 说明

Comprehensive performance benchmarking tool that measures:
- Execution time / 执行时间
- Memory usage / 内存使用
- CPU utilization / CPU利用率
- Output file sizes / 输出文件大小

全面的性能基准测试工具，测量执行时间、内存使用、CPU利用率和输出文件大小。

### Usage / 用法

```bash
# Benchmark all cases / 基准测试所有案例
python benchmark_performance.py

# Benchmark specific cases / 基准测试特定案例
python benchmark_performance.py --case 1 2 3

# Custom output directory / 自定义输出目录
python benchmark_performance.py --output /path/to/results
```

### Requirements / 要求

The benchmark tool requires the `psutil` package:

```bash
pip install psutil
```

### Options / 选项

| Option | Short | Description / 说明 |
|--------|-------|-------------------|
| `--case N` | `-c N` | Benchmark specific case(s) / 基准测试特定案例 |
| `--output DIR` | `-o DIR` | Output directory / 输出目录 |
| `--help` | `-h` | Show help / 显示帮助 |

### Output / 输出

The benchmark tool provides:

1. **Console Output** / **控制台输出**:
   - Individual case results / 单个案例结果
   - Performance metrics table / 性能指标表
   - Statistical summary / 统计总结

2. **JSON Results File** / **JSON结果文件**:
   - Saved to `benchmark_results/benchmark_YYYYMMDD_HHMMSS.json`
   - Contains detailed metrics for all cases
   - Machine-readable format for analysis

Example output:
```
================================================================================
BENCHMARK SUMMARY / 基准测试总结
================================================================================

Total Cases / 总案例数:        5
Successful / 成功:             5
Failed / 失败:                 0
Total Time / 总时间:           425.50s (7.1 min)

Performance Metrics / 性能指标:

Case   Name                      Time(s)    Memory(MB)   CPU(%)
--------------------------------------------------------------------------------
1      Hydropower Plant         145.32     152.45       45.2
2      Water Supply Network      85.67      82.30       38.5
3      Irrigation Canal          95.12      98.75       42.1
4      Urban Drainage            45.23      115.60       35.8
5      River Network            105.89      165.20       48.3

Statistics / 统计:
  Execution Time / 执行时间:
    Average / 平均:    95.45s
    Minimum / 最小:    45.23s
    Maximum / 最大:    145.32s

  Peak Memory / 峰值内存:
    Average / 平均:    122.86 MB
    Minimum / 最小:    82.30 MB
    Maximum / 最大:    165.20 MB

  CPU Utilization / CPU利用率:
    Average / 平均:    41.98%
```

---

## 🧪 Tool 3: Test Suite / 测试套件

**File**: `test_cases.py`

### Description / 说明

Comprehensive test suite with 15 test cases covering all engineering cases and physics components.

包含15个测试用例的全面测试套件，覆盖所有工程案例和物理组件。

### Usage / 用法

```bash
# Run all tests / 运行所有测试
python test_cases.py

# Or use make / 或使用make
make test
```

### Test Coverage / 测试覆盖

**Case Tests** (11 tests):
- Case 01: Hydropower (3 tests)
  - Basic functionality
  - Normal operation simulation
  - Load rejection scenario

- Case 02: Water Supply (2 tests)
  - Basic functionality
  - Demand pattern

- Case 04: Urban Drainage (3 tests)
  - Basic functionality
  - Rainfall event
  - Preissmann Slot method

- Case 05: River Network (3 tests)
  - Basic functionality
  - Compound channel
  - Flood diversion gate

**Physics Component Tests** (4 tests):
- Turbine models
- Pump models
- Valve models
- Surge tank dynamics

### Output / 输出

```
######################################################################
#             HydroClaude - Engineering Cases Test Suite             #
#                              工程案例测试套件                              #
######################################################################

======================================================================
Running: Case 01 - Hydropower Basic
======================================================================

✓ Case 01 - Hydropower Basic PASSED (0.85s)

[... 14 more tests ...]

######################################################################
#                            TEST SUMMARY                            #
######################################################################

Total Tests: 15
✓ Passed:  15
✗ Failed:  0
⊘ Skipped: 0

🎉 All tests passed!
```

---

## 📦 Tool 4: Makefile Shortcuts / Makefile快捷命令

**File**: `Makefile`

### Description / 说明

Convenient shortcuts for common operations.
常用操作的便捷快捷方式。

### Available Targets / 可用目标

```bash
make help          # Show all commands / 显示所有命令
make list          # List all cases / 列出所有案例
make test          # Run test suite / 运行测试套件
make run-all       # Run all cases (full) / 运行所有案例（完整）
make run-quick     # Run all cases (quick) / 运行所有案例（快速）
make run-case-1    # Run Case 01 / 运行案例01
make run-case-2    # Run Case 02 / 运行案例02
make run-case-3    # Run Case 03 / 运行案例03
make run-case-4    # Run Case 04 / 运行案例04
make run-case-5    # Run Case 05 / 运行案例05
make benchmark     # Performance benchmark / 性能基准测试
make clean         # Clean output files / 清理输出文件
```

### Examples / 示例

```bash
# Show help
make help

# Quick test of all cases
make run-quick

# Run specific case
make run-case-4

# Performance benchmark (takes time!)
make benchmark

# Clean up
make clean
```

---

## 💡 Tips & Best Practices / 提示与最佳实践

### 1. Quick Mode for Testing / 快速模式用于测试

Use quick mode (`--quick` or `make run-quick`) when:
- Testing code changes / 测试代码更改
- Verifying cases still work / 验证案例仍然工作
- Quick demos / 快速演示

Quick mode runs shorter simulations (10-30 seconds per case vs 1-3 minutes).

### 2. Benchmark Before and After / 前后基准测试

When making changes:
1. Run benchmark before changes / 更改前运行基准测试
2. Make your changes / 进行更改
3. Run benchmark after changes / 更改后运行基准测试
4. Compare results / 比较结果

```bash
# Before
make benchmark
mv benchmark_results/benchmark_*.json benchmark_before.json

# ... make changes ...

# After
make benchmark
mv benchmark_results/benchmark_*.json benchmark_after.json

# Compare
python compare_benchmarks.py benchmark_before.json benchmark_after.json
```

### 3. Test Early, Test Often / 尽早测试，经常测试

Run the test suite frequently:
```bash
make test
```

This ensures all cases are working correctly.

### 4. Clean Output Files / 清理输出文件

Before running cases, clean old output:
```bash
make clean
```

This prevents confusion with old results.

### 5. Check Individual Cases / 检查单个案例

If a case fails in batch mode, run it individually:
```bash
make run-case-4
# or
python case_04_urban_drainage.py
```

This provides more detailed output.

---

## 🐛 Troubleshooting / 故障排除

### Problem: Import errors / 问题：导入错误

**Symptom / 症状**:
```
ModuleNotFoundError: No module named 'numpy'
```

**Solution / 解决方案**:
```bash
pip install -r ../../requirements.txt
```

### Problem: Permission denied / 问题：权限被拒

**Symptom / 症状**:
```
Permission denied: 'run_all_cases.py'
```

**Solution / 解决方案**:
```bash
chmod +x run_all_cases.py
chmod +x benchmark_performance.py
```

### Problem: Benchmark requires psutil / 问题：基准测试需要psutil

**Symptom / 症状**:
```
Error: psutil package is required for benchmarking
```

**Solution / 解决方案**:
```bash
pip install psutil
```

### Problem: Case timeout / 问题：案例超时

**Symptom / 症状**:
```
✗ Case N TIMEOUT (exceeded 10 minutes)
```

**Solution / 解决方案**:
- Check if case is stuck in infinite loop / 检查案例是否陷入无限循环
- Reduce simulation time in case file / 减少案例文件中的模拟时间
- Use quick mode: `make run-quick` / 使用快速模式

---

## 📚 Additional Resources / 其他资源

- **Case Library README**: `README.md` - Detailed documentation for all cases
- **Project Documentation**: `../../docs/` - Technical documentation
- **Development Roadmap**: `../../docs/COMPREHENSIVE_DEVELOPMENT_ROADMAP_2025_10_30.md`
- **Test Guide**: `../../tests/README.md` - Testing procedures

---

## 🤝 Contributing / 贡献

If you develop new tools or improvements:

1. Add documentation to this guide / 在本指南中添加文档
2. Update the Makefile if applicable / 如果适用，更新Makefile
3. Add tests for your tool / 为您的工具添加测试
4. Submit a pull request / 提交拉取请求

---

## 📝 Changelog / 更新日志

**Version 1.0** (2025-10-30):
- Initial release / 初始版本
- Case runner tool / 案例运行器工具
- Performance benchmark tool / 性能基准测试工具
- Makefile shortcuts / Makefile快捷命令
- Comprehensive documentation / 全面文档

---

**Last Updated**: 2025-10-30
**Maintainer**: HydroClaude Development Team

**🤖 Generated with [Claude Code](https://claude.com/claude-code)**
