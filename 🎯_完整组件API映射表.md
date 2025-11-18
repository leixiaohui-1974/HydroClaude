# 🎯 HydroClaude 完整组件-API-UI映射表

**生成时间**: 2025-11-17  
**用途**: 前后端集成完整参考

---

## 📊 组件状态总览

| 类别 | 组件数 | 后端实现 | API方法 | API路由 | 前端UI | 用户可用 |
|------|--------|----------|---------|---------|--------|----------|
| **泵站系统** | 1 | ✅ | ✅ | ✅ | ⚠️ | 部分 |
| **闸门系统** | 5 | ✅ | 部分 | 部分 | ❌ | 20% |
| **堰系统** | 6 | ✅ | ❌ | ❌ | ❌ | 0% |
| **高级组件** | 4 | ✅ | ❌ | ❌ | ❌ | 0% |
| **扩展结构** | 7 | ✅ | ❌ | ❌ | ❌ | 0% |
| **总计** | **23** | **100%** | **22%** | **22%** | **22%** | **18%** |

---

## 第一部分：泵站系统（1种）

### 1. PumpStation - 泵站

| 维度 | 状态 | 路径/方法 |
|------|------|-----------|
| **后端组件** | ✅ | `backend/core/structures/pump_station.py` |
| **API方法** | ✅ | `HydraulicEngineV2.run_pump_simulation()` |
| **API路由** | ✅ | `POST /api/structures/pump` |
| **前端UI** | ⚠️ | `StructureToolbox.tsx` (基础) |
| **用户可用** | 部分 | 需要完善前端表单 |

**配置参数**:
```json
{
  "pump": {
    "flow_rate": 10.0,
    "head": 15.0,
    "num_pumps": 2,
    "pump_type": "parallel"
  }
}
```

---

## 第二部分：闸门系统（5种）

### 2. SluiceGate - 滑动闸门

| 维度 | 状态 | 路径/方法 |
|------|------|-----------|
| **后端组件** | ✅ | `backend/core/structures/advanced_gates.py` |
| **API方法** | ✅ | `HydraulicEngineV2.run_gate_simulation()` |
| **API路由** | ✅ | `POST /api/structures/gate` |
| **前端UI** | ⚠️ | `StructureToolbox.tsx` (基础) |
| **用户可用** | 部分 | 可用但不完整 |

### 3. RadialGate - 径向闸门

| 维度 | 状态 | 路径/方法 | 需要添加 |
|------|------|-----------|----------|
| **后端组件** | ✅ | `backend/core/structures/advanced_gates.py` | - |
| **API方法** | ❌ | 需要添加 | `run_radial_gate_simulation()` |
| **API路由** | ❌ | 需要添加 | `POST /api/structures/radial-gate` |
| **前端UI** | ❌ | 需要添加 | `componentTemplates.ts` |
| **用户可用** | ❌ | 完全不可用 | 需要全链路实现 |

**需要的配置参数**:
```json
{
  "gate": {
    "type": "radial",
    "width": 10.0,
    "opening": 2.0,
    "radius": 15.0,
    "discharge_coeff": 0.6
  }
}
```

### 4. VerticalLiftGate - 垂直提升闸门

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | - |
| **API方法** | ❌ | `run_vertical_lift_gate_simulation()` |
| **API路由** | ❌ | `POST /api/structures/vertical-lift-gate` |
| **前端UI** | ❌ | 添加到组件库 |
| **用户可用** | ❌ | 需要全链路实现 |

### 5. RollerGate - 滚轮闸门

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | - |
| **API方法** | ❌ | `run_roller_gate_simulation()` |
| **API路由** | ❌ | `POST /api/structures/roller-gate` |
| **前端UI** | ❌ | 添加到组件库 |
| **用户可用** | ❌ | 需要全链路实现 |

### 6. FlapGate - 翻板闸门

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | - |
| **API方法** | ❌ | `run_flap_gate_simulation()` |
| **API路由** | ❌ | `POST /api/structures/flap-gate` |
| **前端UI** | ❌ | 添加到组件库 |
| **用户可用** | ❌ | 需要全链路实现 |

---

## 第三部分：堰系统（6种）

### 7. SharpCrestedWeir - 尖顶堰

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/advanced_weirs.py` |
| **API方法** | ❌ | `run_sharp_crested_weir_simulation()` |
| **API路由** | ❌ | `POST /api/structures/sharp-crested-weir` |
| **前端UI** | ❌ | 添加到组件库 |
| **用户可用** | ❌ | 需要全链路实现 |

### 8. BroadCrestedWeir - 宽顶堰

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/advanced_weirs.py` |
| **API方法** | ❌ | `run_broad_crested_weir_simulation()` |
| **API路由** | ❌ | `POST /api/structures/broad-crested-weir` |
| **前端UI** | ⚠️ | `ComponentPalette.tsx` (基础) |
| **用户可用** | ❌ | API层缺失 |

### 9-12. 其他堰类型

**VNotchWeir**, **RectangularWeir**, **TrapezoidalWeir**, **OgeeWeir**

都需要：
- ❌ API方法
- ❌ API路由
- ❌ 前端UI

---

## 第四部分：高级水电组件（4种）⭐

### 13. Turbine - 水轮机

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/turbine.py` (600行) |
| **API方法** | ❌ | `run_turbine_simulation()` |
| **API路由** | ❌ | `POST /api/structures/turbine` |
| **前端UI** | ❌ | 完整的水轮机编辑器 |
| **用户可用** | ❌ | 需要全链路实现 |

**重要性**: ⭐⭐⭐⭐⭐ 水电站核心组件

**配置参数**:
```json
{
  "turbine": {
    "type": "francis",  // francis, kaplan, pelton
    "rated_power": 50.0,  // MW
    "rated_head": 100.0,  // m
    "rated_flow": 60.0    // m³/s
  }
}
```

### 14. Valve - 阀门

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/valve.py` (450行，7种类型) |
| **API方法** | ❌ | `run_valve_simulation()` |
| **API路由** | ❌ | `POST /api/structures/valve` |
| **前端UI** | ⚠️ | 仅有CheckValve和ReliefValve |
| **用户可用** | ❌ | 大部分类型不可用 |

**重要性**: ⭐⭐⭐⭐ 流量控制关键组件

### 15. SurgeTank - 调压井

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/surge_tank.py` (280行) |
| **API方法** | ❌ | `run_surge_tank_simulation()` |
| **API路由** | ❌ | `POST /api/structures/surge-tank` |
| **前端UI** | ⚠️ | `ComponentPalette.tsx` (基础) |
| **用户可用** | ❌ | API层缺失 |

**重要性**: ⭐⭐⭐⭐ 水锤防护关键组件

### 16. HydropowerStation - 水电站系统

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/hydropower_station.py` (450行) |
| **API方法** | ❌ | `run_hydropower_station_simulation()` |
| **API路由** | ❌ | `POST /api/structures/hydropower-station` |
| **前端UI** | ❌ | 完整的水电站编辑器 |
| **用户可用** | ❌ | 需要全链路实现 |

**重要性**: ⭐⭐⭐⭐⭐ 集成系统，市场独有

---

## 第五部分：扩展结构（7种）

### 17. Culvert - 涵洞

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/culvert.py` |
| **API方法** | ❌ | `run_culvert_simulation()` |
| **API路由** | ❌ | `POST /api/structures/culvert` |
| **前端UI** | ❌ | 添加到组件库 |
| **用户可用** | ❌ | 需要全链路实现 |

### 18. Bridge - 桥梁

| 维度 | 状态 | 需要添加 |
|------|------|----------|
| **后端组件** | ✅ | `backend/core/structures/bridge.py` |
| **API方法** | ❌ | `run_bridge_simulation()` |
| **API路由** | ❌ | `POST /api/structures/bridge` |
| **前端UI** | ❌ | 添加到组件库 |
| **用户可用** | ❌ | 需要全链路实现 |

### 19-23. 其他扩展结构

**SideWeir**, **Storage**, **Reservoir**, **DropStructure**, **Channel**

都需要完整的API方法、路由和前端UI。

---

## 📋 完整待办清单

### P0: 核心API方法（18个）

需要在 `HydraulicEngineV2` 中添加：

```python
# 闸门（4个）
✅ run_gate_simulation()              # 已有
⏳ run_radial_gate_simulation()
⏳ run_vertical_lift_gate_simulation()
⏳ run_roller_gate_simulation()
⏳ run_flap_gate_simulation()

# 堰（6个）
⏳ run_sharp_crested_weir_simulation()
⏳ run_broad_crested_weir_simulation()
⏳ run_v_notch_weir_simulation()
⏳ run_rectangular_weir_simulation()
⏳ run_trapezoidal_weir_simulation()
⏳ run_ogee_weir_simulation()

# 高级组件（4个）
⏳ run_turbine_simulation()
⏳ run_valve_simulation()
⏳ run_surge_tank_simulation()
⏳ run_hydropower_station_simulation()

# 扩展结构（7个）
⏳ run_culvert_simulation()
⏳ run_bridge_simulation()
⏳ run_side_weir_simulation()
⏳ run_storage_simulation()
⏳ run_reservoir_simulation()
⏳ run_drop_structure_simulation()
⏳ run_channel_simulation()
```

### P0: API路由（18个）

需要在 `structures.py` 中添加：

```python
POST /api/structures/radial-gate
POST /api/structures/vertical-lift-gate
POST /api/structures/roller-gate
POST /api/structures/flap-gate
POST /api/structures/sharp-crested-weir
POST /api/structures/broad-crested-weir
POST /api/structures/v-notch-weir
POST /api/structures/rectangular-weir
POST /api/structures/trapezoidal-weir
POST /api/structures/ogee-weir
POST /api/structures/turbine
POST /api/structures/valve
POST /api/structures/surge-tank
POST /api/structures/hydropower-station
POST /api/structures/culvert
POST /api/structures/bridge
POST /api/structures/side-weir
POST /api/structures/storage
POST /api/structures/reservoir
POST /api/structures/drop-structure
POST /api/structures/channel
```

### P0: 前端UI（18个组件）

需要统一添加到 `componentTemplates.ts`。

---

## 🎯 优先级排序

### 高优先级（用户最需要）

1. ⭐⭐⭐⭐⭐ **Turbine** - 水轮机（独有功能）
2. ⭐⭐⭐⭐⭐ **HydropowerStation** - 水电站（独有功能）
3. ⭐⭐⭐⭐ **Valve** - 阀门（通用需求）
4. ⭐⭐⭐⭐ **SurgeTank** - 调压井（水锤防护）
5. ⭐⭐⭐⭐ **RadialGate** - 径向闸门（最常用）

### 中优先级（完善功能）

6-11. 其他闸门和堰类型

### 低优先级（扩展功能）

12-18. 涵洞、桥梁等扩展结构

---

## 📊 工作量评估

| 任务 | 数量 | 单个耗时 | 总耗时 |
|------|------|----------|--------|
| **API方法** | 18个 | 15分钟 | 4.5小时 |
| **API路由** | 18个 | 5分钟 | 1.5小时 |
| **前端UI** | 18个 | 20分钟 | 6小时 |
| **测试验证** | 18个 | 5分钟 | 1.5小时 |
| **总计** | - | - | **13.5小时** |

---

## ✅ 验收标准

完成后应达到：

1. ✅ 所有23种组件都有对应的API方法
2. ✅ 所有23种组件都有对应的API路由
3. ✅ 所有23种组件都有前端UI定义
4. ✅ 端到端测试100%通过
5. ✅ 用户可以通过浏览器使用所有功能

---

**生成时间**: 2025-11-17  
**下一步**: 开始执行P0任务，逐个添加方法和路由
