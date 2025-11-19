# 前端适配指南 (Backend API v2.2.0)

本文档旨在帮助前端开发者将现有应用与重构后的后端API（版本 `2.2.0-service-layer`）进行适配。

---

## 🌟 核心变化总结

后端进行了重大重构，旨在提高代码质量、计算准确性和未来可扩展性。对前端而言，核心变化如下：

1.  **API端点统一化**: 多个针对特定水工结构（如各种闸门、各种堰）的API端点已被合并为更通用的端点。
2.  **计算逻辑分离**:
    *   **独立计算**: 对于单个水工结构（如一个闸门或一个泵），现在有专门的、快速的计算API。
    *   **组合仿真**: 对于需要完整水力模型的复杂场景（如渠道+水工结构），现在有一个统一的、功能强大的仿真API。
3.  **请求与响应模型变更**: JSON请求和响应的结构已更新，以适应新的API设计。

---

## 🚀 API 变更详情

### 1. 独立水工结构计算 (新)

这些是新的、用于快速计算的API端点。它们取代了旧的、返回硬编码或简化结果的API。

| 结构 | HTTP方法 | 新API端点 | 关键请求参数 | 关键响应内容 (`metrics`) |
| :--- | :--- | :--- | :--- | :--- |
| **泵** | `POST` | `/api/structures/pump` | `pump` (配置), `system_head` | `flow_rate`, `power_kw` |
| **闸门** | `POST` | `/api/structures/gate` | `gate` (配置), `upstream_depth`, `downstream_depth` | `discharge`, `flow_regime` |
| **堰** | `POST` | `/api/structures/weir` | `weir` (配置), `upstream_depth`, `downstream_depth` | `discharge`, `head` |
| **水轮机** | `POST` | `/api/structures/turbine`| `turbine` (配置), `current_head`, `current_flow`| `power_mw`, `efficiency` |
| **阀门** | `POST` | `/api/structures/valve` | `valve` (配置), `upstream_pressure`, `downstream_pressure` | `flow_rate`, `velocity` |

**✅ 统一化**:
请注意，您不再需要为 `sluice_gate` 和 `radial_gate` 调用不同的端点。现在只需调用 **`/api/structures/gate`**，并在请求体中指定 `type`:

```json
// 调用平板闸
{
  "gate": { "type": "sluice", ... },
  ...
}

// 调用径向闸
{
  "gate": { "type": "radial", ... },
  ...
}
```
堰（weir）的调用方式与此类似。

### 2. 组合仿真 (新)

所有涉及渠道和水工结构的完整仿真，现在都通过一个统一的API端点来完成。

| 场景 | HTTP方法 | 新API端点 |
| :--- | :--- | :--- |
| **渠道 + 任何结构** | `POST` | `/api/structures/simulate-canal-with-structure` |

**❌ 废弃的端点**:
以下旧的API端点已被 **移除**，请使用上述新端点替代：
- `/api/structures/canal-with-gate`
- `/api/structures/canal-with-pump`
- `/api/structures/canal-with-weir`
- `/api/structures/canal`

---

## 🛠️ 如何构建新的API请求

### 示例 1: 计算单个闸门的流量 (独立计算)

这是一个典型的独立计算请求。

**请求**: `POST /api/structures/gate`
**Body**:
```json
{
  "gate": {
    "type": "sluice",
    "width": 5.0,
    "opening": 1.5,
    "discharge_coeff": 0.62
  },
  "upstream_depth": 4.0,
  "downstream_depth": 2.0
}
```

**响应**: `CalculationResponse`
```json
{
  "task_id": "...",
  "status": "completed",
  "metrics": {
    "discharge": 20.30,
    "flow_regime": "submerged",
    "velocity": 2.70,
    "error": null
  },
  ...
}
```

### 示例 2: 运行一个渠道+闸门的稳态流仿真 (组合仿真)

这是一个典型的组合仿真请求。您需要提供渠道、结构、边界条件等所有信息。

**请求**: `POST /api/structures/simulate-canal-with-structure`
**Body**:
```json
{
    "simulation_type": "steady",
    "canal": {
        "length": 1000.0,
        "width": 10.0,
        "slope": 0.001,
        "manning_n": 0.015,
        "grid_nx": 101
    },
    "structure_type": "sluice_gate",
    "structure": {
        "position": 500.0,
        "parameters": {
            "width": 8.0,
            "opening": 1.2,
            "discharge_coefficient": 0.6
        }
    },
    "boundaries": {
        "upstream": { "type": "Q", "value": 30.0 },
        "downstream": { "type": "h", "value": 2.5 }
    },
    "metadata": {
        "title": "Frontend API Call Example"
    }
}
```
**响应**: `ComplexSimulationResponse`
```json
{
    "task_id": "...",
    "status": "completed",
    "results": {
        "hydro_result": { ... },
        "simulation": { ... },
        "geometry": {
            "dimensions": {
                "spatial": {
                    "values": [0.0, 10.0, ...]
                }
            }
        },
        "variables": {
            "depth": {
                "data": [ [3.1, 3.09, ...] ]
            },
            "flow": {
                "data": [ [30.0, 30.0, ...] ]
            }
        },
        "structures": [ ... ],
        ...
    },
    "error": null
}
```
**注意**: 响应中的 `results` 字段包含了由核心仿真引擎生成的、非常详细的“通用数据模型”。前端可以利用这些数据来绘制详细的水位剖面图等。

---

## 💻 JavaScript Fetch API 示例

这是一个完整的前端调用新组合仿真API的示例代码。

```javascript
async function runComplexSimulation() {
    const apiUrl = 'http://localhost:8000/api/structures/simulate-canal-with-structure';

    const simulationConfig = {
        "simulation_type": "steady",
        "canal": { "length": 1000, "width": 10, "slope": 0.001, "manning_n": 0.015, "grid_nx": 101 },
        "structure_type": "sluice_gate",
        "structure": {
            "position": 500.0,
            "parameters": { "width": 8.0, "opening": 1.2, "discharge_coefficient": 0.6 }
        },
        "boundaries": {
            "upstream": { "type": "Q", "value": 30.0 },
            "downstream": { "type": "h", "value": 2.5 }
        },
        "metadata": { "title": "Frontend API Call Example" }
    };

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(simulationConfig),
        });

        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`, await response.json());
            return;
        }

        const data = await response.json();

        if (data.status === 'completed') {
            console.log('Simulation successful!', data);
            // 在这里处理和可视化 `data.results`
            // 例如，提取水位数据进行绘图:
            const waterDepthProfile = data.results.variables.depth.data[0];
            const spatialPoints = data.results.geometry.dimensions.spatial.values;
            console.log('Water depth at each point:', waterDepthProfile);
        } else {
            console.error('Simulation failed:', data.error);
        }

    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
    }
}

// 调用示例
runComplexSimulation();
```

如有任何疑问，请随时与后端团队联系。
