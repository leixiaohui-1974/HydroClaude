# 串联明渠闸泵群系统 - 完整运行计划

## 📋 运行脚本清单

### 一、核心泵站模型仿真（3个脚本）

#### 1. 原始模型（PumpStation）
```bash
python3 gate_pump_cascade_system.py
```
- 固定流量模型
- 基准对比

#### 2. 简化模型（PumpStationSimplified）
```bash
python3 gate_pump_cascade_simplified.py
```
- 流量跟随模型
- 质量守恒

#### 3. 高精度模型（PumpStationAdvanced）
```bash
python3 gate_pump_cascade_advanced.py
```
- 真实泵特性曲线
- 工作点求解

### 二、控制策略对比（7个脚本）

#### 1. PID扰动响应
```bash
python3 control_strategies/run_01_pid_disturbance.py
```

#### 2. MPC预测控制
```bash
python3 control_strategies/run_02_mpc_predictive.py
```

#### 3. 分层控制
```bash
python3 control_strategies/run_03_hierarchical.py
```

#### 4. 优化PID
```bash
python3 control_strategies/run_04_optimized_pid.py
```

#### 5. 优化MPC
```bash
python3 control_strategies/run_05_mpc_optimized.py
```

#### 6. 真正优化MPC
```bash
python3 control_strategies/run_05_mpc_truly_optimized.py
```

#### 7. 优化分层控制
```bash
python3 control_strategies/run_06_hierarchical_optimized.py
```

### 三、工况测试脚本（5个）

#### 1. 泵站模型对比
```bash
python3 test_pump_models.py
```

#### 2. 简单扰动测试
```bash
python3 test_disturbances_simple.py
```

#### 3. 简单非恒定流测试
```bash
python3 test_unsteady_simple.py
```

#### 4. 完整非恒定流测试
```bash
python3 test_unsteady_complete.py
```

#### 5. 综合扰动测试
```bash
python3 test_comprehensive_disturbances.py
```

### 四、综合分析脚本（3个）

#### 1. 三模型对比
```bash
python3 compare_all_models.py
```

#### 2. 完整对比生成
```bash
python3 generate_complete_comparison.py
```

#### 3. 优化控制测试
```bash
python3 test_optimized_control.py
```

### 五、其他配置运行（2个）

#### 1. 闸泵自动控制
```bash
python3 run_gate_pump_auto.py
```

#### 2. 最终优化系统
```bash
python3 run_final_optimized_system.py
```

---

## 📊 预期输出

### 每个脚本的输出：
- 稳态纵断面图
- 时空演化图（水位、流量）
- 关键位置时间序列
- 动画GIF
- 数据NPZ文件
- 控制性能指标

### 总计预期文件数：
- PNG图表：~150个
- GIF动画：~20个
- NPZ数据：~20个
- 对比报告：~10个

---

## ⏱️ 预计运行时间

- 核心模型：3×5分钟 = 15分钟
- 控制策略：7×3分钟 = 21分钟
- 工况测试：5×3分钟 = 15分钟
- 综合分析：3×2分钟 = 6分钟
- 其他配置：2×3分钟 = 6分钟

**总计：约63分钟**

---

## 运行顺序

### 第一批：核心模型（15分钟）
1. gate_pump_cascade_system.py
2. gate_pump_cascade_simplified.py
3. gate_pump_cascade_advanced.py

### 第二批：模型对比（5分钟）
4. test_pump_models.py
5. compare_all_models.py

### 第三批：控制策略（21分钟）
6-12. control_strategies/run_*.py

### 第四批：工况测试（15分钟）
13-17. test_*.py

### 第五批：综合分析（7分钟）
18-20. 其他脚本
