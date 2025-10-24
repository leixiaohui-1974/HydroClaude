# 文件边界条件示例

## 概述

本示例展示如何从CSV文件读取时间序列数据，并作为边界条件应用到水力学模拟中。

## 功能特点

- **CSV文件读取**: 自动读取CSV格式的时间序列数据
- **线性插值**: 在时间点之间进行线性插值，实现平滑变化
- **多列支持**: 支持多列数据（flow、depth、temperature等）
- **相对路径**: 支持相对于配置文件的路径

## 文件结构

```
example_file_boundary_condition/
├── config.yaml           # 配置文件
├── flow_data.csv         # 时间序列数据文件
├── run.py                # 运行脚本
└── README.md             # 本文件
```

## CSV文件格式

```csv
time,flow,depth
0,10.0,2.0
60,10.5,2.05
120,11.0,2.1
...
```

**要求**:
- 第一列必须是 `time`（单位：秒）
- 其他列可以是任意数据（flow、depth等）
- 使用逗号分隔
- 支持UTF-8编码

## 配置文件格式

```yaml
time_varying_bc:
  enabled: true
  type: file              # 使用文件类型
  file: flow_data.csv     # CSV文件路径
  boundary: upstream      # 应用到哪个边界（upstream/downstream）
  column: flow            # 使用哪一列数据
```

## 运行示例

### 方法1: 使用运行脚本

```bash
cd examples/example_file_boundary_condition
python run.py
```

### 方法2: 使用通用建模器CLI

```bash
python -m modeling.universal_modeler examples/example_file_boundary_condition/config.yaml
```

## 预期结果

**边界条件变化**:
- 0-300秒: 流量从10 m³/s 逐渐增加到15 m³/s
- 300-600秒: 流量继续增加到17 m³/s
- 600-960秒: 流量逐渐降低回10 m³/s

**系统响应**:
- 水深随流量变化而变化
- 流速随流量和水深联合调整
- 整个过程保持流量守恒

## 典型应用场景

### 1. 实测数据回放
将现场测量的流量或水位数据导入仿真，验证模型准确性。

### 2. 洪水过程模拟
使用历史洪水过程线作为边界条件，模拟防洪响应。

### 3. 复杂调度策略
将优化或人工决策的调度过程导出为CSV，在仿真中验证。

### 4. 多场景对比
创建多个CSV文件代表不同场景，快速对比分析。

## 数据准备建议

### Excel到CSV转换

1. 在Excel中准备数据:
   - A列: time（秒）
   - B列: flow（m³/s）
   - C列: depth（m）等

2. 另存为CSV格式:
   - 文件 → 另存为 → CSV (逗号分隔)(*.csv)

3. 确保编码为UTF-8:
   - 用记事本打开 → 另存为 → 编码选择UTF-8

### Python生成数据

```python
import numpy as np
import pandas as pd

# 生成时间序列
time = np.linspace(0, 1200, 100)
flow = 10 + 5 * np.sin(2 * np.pi * time / 600)

# 保存为CSV
df = pd.DataFrame({'time': time, 'flow': flow})
df.to_csv('flow_data.csv', index=False)
```

## 高级用法

### 多列数据

CSV文件可以包含多列数据:

```csv
time,flow,temperature,turbidity
0,10.0,15.5,20.0
60,10.5,15.6,21.0
```

配置文件中指定使用哪一列:

```yaml
time_varying_bc:
  type: file
  file: flow_data.csv
  column: flow        # 使用flow列
```

### 多个边界条件

可以在配置中定义多个时变边界条件:

```yaml
time_varying_bc:
  - type: file
    file: upstream_flow.csv
    boundary: upstream
    column: flow

  - type: file
    file: downstream_level.csv
    boundary: downstream
    column: depth
```

## 技术细节

**插值方法**: 线性插值（`np.interp`）
- 在指定时间点之间线性插值
- 超出范围时使用边界值
- 保证连续性和平滑性

**性能优化**:
- 文件只读取一次，缓存在内存中
- 插值计算时间 < 0.001秒
- 支持大型数据文件（>10000个时间点）

## 故障排除

### 问题1: 文件未找到

**错误**: `FileNotFoundError`

**解决**:
- 检查文件路径是否正确
- 使用相对于配置文件的路径
- 或使用绝对路径

### 问题2: 列不存在

**警告**: `列 'xxx' 不存在，使用第一列`

**解决**:
- 检查CSV文件的列名
- 确保配置文件中的`column`与CSV列名匹配
- 列名区分大小写

### 问题3: 数据格式错误

**错误**: `ValueError: could not convert string to float`

**解决**:
- 检查CSV文件是否有非数字数据
- 确保使用逗号分隔，不是分号或制表符
- 检查是否有空行或注释行

## 参考资料

- [通用建模系统文档](../README.md)
- [时变边界条件完整示例](../example_time_varying_bc/)
- [配置文件格式说明](../../QUICKSTART_GUIDE.md)
