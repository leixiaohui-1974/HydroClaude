# 测试错误修复计划
# Test Error Fixing Plan

**创建时间**: 2025-11-13 11:05
**当前通过率**: 18.9% (102/541)
**目标通过率**: 25-30%
**预期提升**: +6-11%

---

## 🎯 **修复优先级**

### 基于第一轮测试分析的失败原因：

```
优先级1: Exit code 1 (数值稳定性) - 284个 (65.3%) 
→ 预期提升: +5-8%

优先级2: 超时问题 - 11个 (2.5%)
→ 预期提升: +1-2%

优先级3: ModuleNotFoundError剩余 - 少量
→ 预期提升: +0.5-1%

优先级4: 配置错误 - 若干
→ 预期提升: +1-2%
```

---

## 🔧 **Phase 1: 数值稳定性优化**（最重要）

### 问题描述
```
失败类型: Exit code 1
数量: 284个案例
原因: 数值不稳定、计算发散
```

### 修复策略

#### 1. 降低CFL数
```python
# 当前配置
cfl = 0.5

# 优化后
cfl = 0.3  # 更保守，更稳定

# 预期效果: 减少50-100个失败
```

#### 2. 减小最大时间步
```python
# 当前配置
dt_max = 0.5-1.0

# 优化后
dt_max = 0.2  # 更小的时间步

# 预期效果: 减少30-50个失败
```

#### 3. 使用一阶精度
```python
# 当前配置
order = 2  # 二阶精度

# 优化后
order = 1  # 一阶精度，更稳定

# 预期效果: 减少20-30个失败
```

#### 4. 增加网格分辨率
```python
# 当前配置
n_cells = 100-200

# 优化后
n_cells = int(n_cells * 1.2)  # 增加20%

# 预期效果: 减少10-20个失败
```

#### 5. 优化初始条件
```python
# 使用更接近理论值的初始条件
from utils.canal_utils import compute_steady_uniform_flow

h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
initial_h = h_uniform * 1.02  # 略高于理论值
```

---

## 🚀 **执行步骤**

### Step 1: 识别需要优化的案例（5分钟）
```bash
python analyze_failure_patterns.py

# 输出: 
# - test_results/failure_analysis.json
# - 按失败类型分类的案例列表
```

### Step 2: 批量优化配置（10分钟）
```bash
# 使用优化脚本
python optimize_failing_scenarios.py

# 功能:
# - 自动识别Exit code 1案例
# - 应用优化策略
# - 生成优化后的配置
```

### Step 3: 小批量验证（10分钟）
```bash
# 测试50个案例验证效果
python quick_test_sample.py -n 50

# 检查通过率是否提升
```

### Step 4: 完整第三轮测试（40分钟）
```bash
# 如果小批量测试效果好，运行完整测试
python batch_test_all_cases.py

# 预期结果: 25-30%通过率
```

---

## 📋 **具体修复脚本**

让我创建一个专门的修复脚本...

