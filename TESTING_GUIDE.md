# HydroClaude Testing Guide
# 测试指南

**Version**: 1.0  
**Date**: 2025-11-13  
**Status**: 完整测试体系已建立

---

## 📋 目录 / Table of Contents

1. [测试体系概述](#测试体系概述)
2. [快速开始](#快速开始)
3. [批量测试](#批量测试)
4. [测试结果分析](#测试结果分析)
5. [问题修复](#问题修复)
6. [Web界面测试](#web界面测试)
7. [最佳实践](#最佳实践)

---

## 测试体系概述 / Testing System Overview

HydroClaude项目包含**541个测试案例**，覆盖以下类别：

### 测试案例分类

| 类别 | 数量 | 描述 |
|------|------|------|
| **基础流动** (Basic Flow) | ~80 | 均匀流、非均匀流、稳态/非稳态 |
| **溃坝** (Dam Break) | ~120 | 干河床/湿河床、不同地形 |
| **有压流** (Pressurized) | ~60 | 管道流动、水锤分析 |
| **静水** (Lake at Rest) | ~40 | 静止水体、数值稳定性 |
| **水工结构** (Structures) | ~100 | 闸门、堰、泵站、阀门 |
| **控制系统** (Control) | ~70 | PID、MPC控制 |
| **水质模拟** (Water Quality) | ~50 | DO/BOD、营养物质 |
| **其他** (Others) | ~21 | 耦合模拟、复杂场景 |

### 测试工具

```
├── batch_test_all_cases.py       # 批量测试所有案例
├── quick_test_sample.py          # 快速测试样本
├── analyze_test_results.py       # 结果分析工具
├── fix_test_import_issues.py     # 导入问题修复工具
└── web/backend/api_gateway/routers/test_runner.py  # Web测试API
```

---

## 快速开始 / Quick Start

### 1. 快速测试 (5个随机案例)

```bash
python quick_test_sample.py
```

**输出示例**:
```
Quick Test - 5 Random Cases
============================
[1/5] Running: Dam Break - Wet Bed
    Status: PASS (2.34s)

Summary:
  Passed: 4/5 (80%)
  Failed: 1/5 (20%)
```

### 2. 批量测试 (所有541个案例)

```bash
# 在后台运行，输出保存到文件
python batch_test_all_cases.py > test_results/batch_test_output.txt 2>&1

# 或者直接运行（控制台输出）
python batch_test_all_cases.py
```

**预计耗时**: 15-30分钟

---

## 批量测试 / Batch Testing

### 运行批量测试

```bash
# 方法1: 后台运行（推荐）
python batch_test_all_cases.py > test_results/batch_test_output.txt 2>&1 &

# 方法2: 前台运行
python batch_test_all_cases.py

# 方法3: Windows后台运行
Start-Process python -ArgumentList "batch_test_all_cases.py" -NoNewWindow -RedirectStandardOutput "test_results\batch_test_output.txt" -RedirectStandardError "test_results\batch_test_error.txt"
```

### 监控进度

```bash
# Linux/Mac
tail -f test_results/batch_test_output.txt

# Windows PowerShell
Get-Content test_results\batch_test_output.txt -Tail 50 -Wait

# 检查当前进度
python -c "import re; content=open('test_results/batch_test_output.txt').read(); match=re.findall(r'\[(\d+)/541\]', content); print(f'Progress: {match[-1]}/541' if match else 'Not started')"
```

### 输出文件

测试完成后会生成以下文件：

```
test_results/
├── batch_test_output.txt         # 完整测试日志
├── batch_test_summary.md         # 汇总报告（Markdown）
└── batch_test_results.json       # 详细结果（JSON）
```

---

## 测试结果分析 / Test Results Analysis

### 运行分析工具

测试完成后，使用分析工具生成详细报告：

```bash
python analyze_test_results.py
```

### 生成的报告

**batch_test_analysis.md** 包含：

1. **总体统计**
   - 通过率、失败率
   - 总耗时、平均耗时
   - 状态分布图

2. **分类统计**
   - 每个类别的通过率
   - 性能对比

3. **失败模式分析**
   - Top 10 失败原因
   - 错误模式统计

4. **失败案例列表**
   - 详细的错误信息
   - 建议的修复方案

5. **改进建议**
   - 优先修复项
   - 性能优化建议

### 示例报告片段

```markdown
## 📊 总体统计 / Overall Statistics

总计测试案例 / Total Cases:     541
通过 / Passed:                  412 (76.2%)
失败 / Failed:                  89 (16.4%)
错误 / Error:                   35 (6.5%)
超时 / Timeout:                 5 (0.9%)

通过率 / Pass Rate:             76.2%
总耗时 / Total Duration:        1234.5s (20.6 min)
平均耗时 / Avg Duration:        2.28s
```

---

## 问题修复 / Issue Fixing

### 常见问题类型

#### 1. **ModuleNotFoundError** (最常见)

**原因**: Python导入路径配置问题

**修复方法**:

##### 自动修复（推荐）

```bash
# 干运行（查看会修复什么）
python fix_test_import_issues.py --directory tests

# 应用修复
python fix_test_import_issues.py --apply --directory tests

# 修复所有目录
python fix_test_import_issues.py --apply --directory .
```

##### 手动修复

在测试文件开头添加：

```python
import sys
import os

# Add project root to Python path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
```

#### 2. **UnicodeEncodeError (GBK)**

**原因**: Windows默认编码问题

**修复方法**:

- 已通过`encoding_patch.py`全局修复
- 确保后端服务启动时加载了patch

#### 3. **Timeout (超时)**

**原因**: 案例运行时间过长

**修复方法**:

```python
# 在 batch_test_all_cases.py 中调整超时时间
process.communicate(timeout=600)  # 从600秒增加到更大值
```

#### 4. **Non-zero Exit Code**

**原因**: 测试脚本本身有错误

**修复方法**:

1. 单独运行失败的案例查看详细错误
2. 检查数值参数设置
3. 验证依赖库版本

### 修复工作流

```bash
# 1. 运行批量测试
python batch_test_all_cases.py

# 2. 分析结果
python analyze_test_results.py

# 3. 根据报告修复问题
#    - 如果是导入问题：
python fix_test_import_issues.py --apply --directory tests

#    - 如果是其他问题：手动修复

# 4. 重新测试失败的案例
python quick_test_sample.py

# 5. 再次运行批量测试验证
python batch_test_all_cases.py
```

---

## Web界面测试 / Web Interface Testing

### 启动后端服务

```bash
cd E:\OneDrive\Documents\GitHub\Test\HydroClaude
python -m uvicorn web.backend.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### 通过Web API测试

#### 1. 获取测试案例列表

```bash
curl http://localhost:8000/api/v1/test-cases/catalog
```

#### 2. 运行单个测试案例

```bash
curl -X POST http://localhost:8000/api/v1/test-runner/run \
  -H "Content-Type: application/json" \
  -d '{"case_id": "examples-example_01_canal_flow-01_basic_v2"}'
```

#### 3. 查询测试状态

```bash
curl http://localhost:8000/api/v1/test-runner/status/{task_id}
```

#### 4. 生成测试报告

```bash
curl http://localhost:8000/api/v1/test-runner/results/{task_id}/report
```

### 前端界面测试

1. 打开浏览器：`http://localhost:3000`
2. 导航到"测试案例库" (Test Case Library)
3. 选择一个案例
4. 点击"运行测试" (Run Test)
5. 查看实时进度和结果
6. 下载分析报告

---

## 最佳实践 / Best Practices

### 测试前准备

✅ **检查环境**
```bash
python --version  # 确保 Python 3.10+
pip list | grep numpy  # 确保依赖库已安装
```

✅ **清理旧结果**
```bash
rm -rf test_results/*  # Linux/Mac
Remove-Item test_results\* -Recurse -Force  # Windows
```

✅ **备份重要数据**
```bash
cp -r test_results test_results_backup_$(date +%Y%m%d)
```

### 测试中监控

✅ **监控系统资源**
```bash
# Linux/Mac
top
htop

# Windows
taskmgr  # 任务管理器
```

✅ **定期检查进度**
```bash
# 每5分钟检查一次
watch -n 300 'tail test_results/batch_test_output.txt'
```

### 测试后分析

✅ **立即生成报告**
```bash
python analyze_test_results.py
```

✅ **归档结果**
```bash
tar -czf test_results_$(date +%Y%m%d_%H%M%S).tar.gz test_results/
```

✅ **分享结果**
```bash
# 复制报告到项目文档
cp test_results/batch_test_analysis.md docs/
```

---

## 故障排除 / Troubleshooting

### 问题1: 测试运行缓慢

**症状**: 每个案例耗时超过10秒

**解决方案**:
- 检查CPU使用率
- 减小网格数量
- 降低模拟时间
- 使用并行测试（未来功能）

### 问题2: 大量失败

**症状**: 通过率低于50%

**解决方案**:
1. 检查Python环境
2. 重新安装依赖：`pip install -r requirements.txt`
3. 运行快速测试验证环境
4. 使用导入修复工具

### 问题3: 内存不足

**症状**: 测试中途崩溃

**解决方案**:
- 增加系统内存
- 减小批量大小（修改batch_test_all_cases.py）
- 分批测试不同类别

### 问题4: Web API无响应

**症状**: Web测试API返回超时

**解决方案**:
- 检查后端服务状态
- 重启uvicorn服务
- 检查防火墙设置
- 查看后端日志

---

## 性能基准 / Performance Benchmarks

### 预期性能指标

| 指标 | 目标值 | 备注 |
|------|--------|------|
| 通过率 | ≥ 90% | 高质量目标 |
| 平均耗时 | < 3s | 单个案例 |
| 总测试时间 | < 30 min | 541个案例 |
| 内存占用 | < 4 GB | 峰值 |
| CPU使用率 | < 80% | 平均 |

### 实际性能（参考）

基于初步测试结果：

```
通过率: ~70-80% (需要修复导入问题)
平均耗时: ~2.3s
总测试时间: ~20-25 min
内存占用: ~2-3 GB
```

---

## 测试报告示例 / Sample Test Report

查看完整示例: `test_results/batch_test_analysis.md`

**关键指标**:
- ✅ 412 passed (76.2%)
- ❌ 89 failed (16.4%)
- ⚠️ 35 errors (6.5%)
- ⏱️ 5 timeout (0.9%)

**Top 3 失败原因**:
1. ModuleNotFoundError (45 cases)
2. Non-zero exit code (28 cases)
3. ImportError (12 cases)

**改进建议**:
1. 运行导入修复工具
2. 检查特定类别的失败模式
3. 优化数值参数

---

## 相关文档 / Related Documentation

- [开发规则](./AI_RULES.md) - AI开发必读
- [库参考](./LIBRARY_REFERENCE.md) - 基础库API
- [开发指南](./DEVELOPMENT_GUIDE.md) - 开发规范
- [8周实施报告](./WEB_8WEEK_IMPLEMENTATION_REPORT.md) - Web系统进展

---

## 联系支持 / Support

遇到问题？

1. 查看 `test_results/batch_test_analysis.md` 获取详细分析
2. 运行 `python fix_test_import_issues.py` 自动修复常见问题
3. 查看项目文档获取更多帮助

---

**最后更新 / Last Updated**: 2025-11-13  
**文档版本 / Version**: 1.0  
**测试案例总数 / Total Cases**: 541

**🎯 目标: 实现90%+通过率，打造商业级水力学模拟软件！**



