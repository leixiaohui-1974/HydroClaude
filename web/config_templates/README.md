# HydroClaude 仿真配置模板库

本目录包含经过验证的、数值稳定的仿真配置模板。

## 📁 模板分类

### 1. 基础模板
- `basic_steady_flow.json` - 基础稳态流
- `basic_unsteady_flow.json` - 基础非稳态流

### 2. 专项模板
- `dam_break_stable.json` - 稳定的溃坝模拟
- `flood_routing.json` - 洪水演进
- `gate_control.json` - 闸门控制

### 3. 测试模板
- `quick_test.json` - 快速测试（<10秒）
- `validation_test.json` - 验证测试

## 🎯 模板选择指南

### 按问题类型选择

| 问题类型 | 推荐模板 | 说明 |
|---------|---------|------|
| 稳态流 | `basic_steady_flow.json` | 固定流量，长时间模拟 |
| 溃坝 | `dam_break_stable.json` | 激波，需要低CFL |
| 洪水 | `flood_routing.json` | 大流量，长河道 |
| 闸门 | `gate_control.json` | 边界控制 |
| 快速验证 | `quick_test.json` | 开发测试用 |

### 按网格规模选择

| 网格数 | 模拟时间 | 预计耗时 | 建议 |
|-------|---------|---------|------|
| 50-100 | < 60s | < 0.5s | 快速测试 ✅ |
| 100-500 | < 300s | < 5s | 标准模拟 ✅ |
| 500-1000 | < 600s | < 30s | 详细模拟 ⚠️ |
| > 1000 | > 600s | > 60s | 高精度研究 ⚠️ |

## 📊 参数说明

### 必需参数

```json
{
  "width": 10.0,        // 渠道宽度 (m), 范围: 0.1-1000
  "length": 1000.0,     // 渠道长度 (m), 范围: 10-100000
  "n_cells": 100,       // 网格数, 范围: 10-10000
  "t_end": 60.0,        // 模拟时间 (s), 范围: 1-86400
  "slope": 0.001,       // 底坡, 范围: 0-0.1
  "manning_n": 0.025,   // 曼宁系数, 范围: 0.01-0.1
  "initial_conditions": {...},
  "boundary_conditions": {...}
}
```

### 可选参数（数值稳定性）

```json
{
  "cfl": 0.3,           // CFL数, 默认: 0.5, 稳定范围: 0.1-0.5
  "order": 1,           // 空间精度, 默认: 2, 稳定选择: 1
  "use_numba": true,    // Numba加速, 默认: true
  "well_balanced": false // Well-Balanced格式, 默认: false
}
```

## ⚠️ 数值稳定性指南

### 稳定配置建议

**保守配置（推荐新手）**:
```json
{
  "cfl": 0.3,
  "order": 1,
  "Q_initial": < 50 m³/s,
  "n_cells": 100-200
}
```

**标准配置（经验用户）**:
```json
{
  "cfl": 0.5,
  "order": 2,
  "Q_initial": < 100 m³/s,
  "n_cells": 200-500
}
```

**高精度配置（研究用）**:
```json
{
  "cfl": 0.3,
  "order": 2,
  "Q_initial": 自定义,
  "n_cells": > 500
}
```

### 常见问题和解决方案

#### 问题1: "Numerical instability detected"
**原因**: 数值不稳定
**解决方案**:
1. 降低CFL数: 0.5 → 0.3
2. 降低精度: order=2 → order=1
3. 减小初始流量
4. 检查边界条件是否与初始条件匹配

#### 问题2: "RuntimeWarning: overflow"
**原因**: 数值溢出，通常由大流量引起
**解决方案**:
1. 减小流量（< 50 m³/s）
2. 降低CFL数
3. 使用1阶格式

#### 问题3: 模拟速度太慢
**原因**: 网格过多或CFL过小
**解决方案**:
1. 减少网格数
2. 增大CFL数（但不超过0.5）
3. 缩短模拟时间
4. 确保 `use_numba=true`

#### 问题4: 质量不守恒
**原因**: 边界条件设置错误
**解决方案**:
1. 检查上下游边界类型
2. 确保初始条件合理
3. 使用质量守恒测试模板验证

## 🚀 使用方法

### 方法1: 直接使用模板
```python
import json

# 加载模板
with open('config_templates/basic_steady_flow.json') as f:
    config = json.load(f)

# 根据需要修改参数
config['config']['width'] = 15.0
config['config']['t_end'] = 120.0

# 提交仿真
response = requests.post(
    'http://localhost:8000/api/v1/simulations',
    json=config
)
```

### 方法2: 基于模板自定义
```python
from copy import deepcopy

# 加载基础模板
base_config = load_template('basic_steady_flow.json')

# 创建自定义配置
my_config = deepcopy(base_config)
my_config['name'] = '我的自定义仿真'
my_config['config']['length'] = 2000.0
my_config['config']['n_cells'] = 200

# 提交
response = requests.post(API_URL, json=my_config)
```

## 📚 参考资料

- [API参考文档](../docs/API_REFERENCE.md)
- [用户快速入门](../docs/USER_QUICK_START.md)
- [参数选择指南](../web/PARAMETER_SELECTION_GUIDE.md)
- [数值方法说明](../docs/NUMERICAL_METHODS.md)

## 🔄 模板更新记录

- **2025-11-11**: 初始版本，包含7个基础模板
- 后续更新将在此记录

## 💡 贡献

如果您有新的稳定配置，欢迎提交PR！

**提交要求**:
1. 配置必须通过稳定性测试
2. 质量守恒误差 < 1%
3. 包含详细说明和使用场景
4. 附带验证测试结果
