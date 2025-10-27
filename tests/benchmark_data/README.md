# 基准算例数据

本目录存放国际公认的基准算例数据，用于验证数值方法的正确性。

## 📚 数据来源

### 1. MacDonald基准算例

**来源**: MacDonald, I., Baines, M. J., Nichols, N. K., & Samuels, P. G. (1997). "Analytic benchmark solutions for open-channel flows." *Journal of Hydraulic Engineering*, 123(11), 1041-1045.

**描述**: 经典的明渠流动基准算例，提供解析解或高精度数值解。

**算例**:
- Case 1: 矩形渠道稳态均匀流
- Case 2: 单闸门控制流
- Case 3: 溃坝问题（非恒定流）

**数据格式**: CSV文件，包含位置(x)和水深(h)

### 2. Goutal & Maurel基准算例

**来源**: Goutal, N., & Maurel, F. (1997). "Proceedings of the 2nd workshop on dam-break wave simulation." Technical Report HE-43/97/016/A, EDF-DER.

**描述**: EDF-SOGREAH基准测试集，包含稳态和非恒定流算例。

**算例类型**:
- 稳态水面线（M1, M2, M3, S1, S2, S3曲线）
- 非恒定流（洪水演进、闸门突然开启/关闭）
- 结构物（闸门、堰、泵站）

### 3. SWASHES基准算例

**来源**: Delestre, O., Lucas, C., Ksinant, P. A., Darboux, F., Laguerre, C., Vo, T. N. T., ... & Cordier, S. (2013). "SWASHES: a compilation of shallow water analytic solutions for hydraulic and environmental studies." *International Journal for Numerical Methods in Fluids*, 72(3), 269-300.

**描述**: 浅水方程解析解合集，专门用于验证数值方法。

**网站**: http://www.univ-orleans.fr/mapmo/soft/SWASHES/

**算例特点**:
- 提供精确解析解
- 涵盖各种流动状态
- 包含源代码和数据文件

---

## 📁 目录结构

```
benchmark_data/
├── README.md                    # 本文件
├── macdonald/                   # MacDonald基准算例
│   ├── case1_uniform_flow.csv
│   ├── case2_sluice_gate.csv
│   └── case3_dam_break.csv
├── goutal/                      # Goutal & Maurel基准
│   ├── M1_backwater.csv
│   ├── M2_drawdown.csv
│   ├── gate_sudden_open.csv
│   └── flood_propagation.csv
└── swashes/                     # SWASHES基准
    ├── sw_exact_solution_1.csv
    ├── sw_exact_solution_2.csv
    └── ...
```

---

## 📊 数据格式

### CSV格式（标准）

```csv
x,h,u,z
0.0,2.5,1.0,10.0
100.0,2.48,1.01,9.9
200.0,2.46,1.02,9.8
...
```

**字段说明**:
- `x`: 距离 (m)
- `h`: 水深 (m)
- `u`: 流速 (m/s)
- `z`: 床面高程 (m)

### 元数据文件（JSON）

每个算例配套一个元数据文件：

```json
{
  "name": "MacDonald Case 1",
  "description": "矩形渠道稳态均匀流",
  "reference": "MacDonald et al. (1997) JHE",
  "doi": "10.1061/(ASCE)0733-9429(1997)123:11(1041)",
  "parameters": {
    "length": 10000.0,
    "width": 10.0,
    "slope": 0.001,
    "manning": 0.025,
    "flow_rate": 10.0
  },
  "solution_type": "analytical",
  "expected_error": 0.005,
  "notes": "经典的均匀流验证算例"
}
```

---

## 🔍 如何使用

### Python读取示例

```python
import pandas as pd
import json

# 读取数据
data = pd.read_csv('benchmark_data/macdonald/case1_uniform_flow.csv')

# 读取元数据
with open('benchmark_data/macdonald/case1_uniform_flow.json') as f:
    metadata = json.load(f)

# 使用数据进行对比
x = data['x'].values
h_reference = data['h'].values

# ... 运行数值模拟 ...
# result = solver.solve(...)

# 对比
error = abs(result['h'] - h_reference) / h_reference
print(f"最大误差: {error.max()*100:.2f}%")
```

---

## 📝 贡献数据

如果你有新的基准算例数据：

1. 确保数据来源可靠（文献、实验、高精度数值解）
2. 按照标准格式准备CSV和JSON文件
3. 添加完整的元数据和参考文献
4. 提交Pull Request

---

## ⚠️ 注意事项

1. **版权**: 所有数据必须是公开发表的，或有明确的开源许可
2. **引用**: 使用数据时请引用原始文献
3. **精度**: 标明数据的来源精度（解析解、实验、数值解）
4. **单位**: 统一使用SI单位

---

## 📚 参考文献

1. MacDonald, I., et al. (1997). "Analytic benchmark solutions for open-channel flows." *J. Hydraulic Eng.*, 123(11), 1041-1045.

2. Goutal, N., & Maurel, F. (1997). "Proceedings of the 2nd workshop on dam-break wave simulation." EDF-DER Tech. Report.

3. Delestre, O., et al. (2013). "SWASHES: a compilation of shallow water analytic solutions." *Int. J. Numer. Meth. Fluids*, 72(3), 269-300.

4. Toro, E. F. (2001). *Shock-Capturing Methods for Free-Surface Shallow Flows*. Wiley.

5. Chaudhry, M. H. (2008). *Open-Channel Flow* (2nd ed.). Springer.

---

**维护者**: HydroClaude开发团队  
**最后更新**: 2025-10-27
