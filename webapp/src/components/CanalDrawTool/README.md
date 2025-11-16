# CanalDrawTool 组件

**Phase 5.2.2 - 渠道绘制工具**

---

## 📖 概述

CanalDrawTool是HydroClaude GIS功能的渠道绘制组件，允许用户在地图上交互式绘制和编辑渠道线。

### 核心功能

- ✅ 点击绘制渠道线
- ✅ 节点拖动编辑
- ✅ 节点删除（双击）
- ✅ 实时长度计算
- ✅ 坡度自动计算
- ✅ 撤销/重做
- ✅ GeoJSON导出
- ✅ 渠道参数配置

---

## 🎯 功能特性

### 1. 绘制模式

**点击绘制**:
- 点击"开始绘制"按钮进入绘制模式
- 在地图上点击添加节点
- 实时显示渠道线
- 点击"停止绘制"完成绘制

**节点类型**:
- 🟢 **起点** - 绿色节点
- 🔵 **中间节点** - 蓝色节点
- 🔴 **终点** - 红色节点

### 2. 编辑功能

**节点拖动**:
- 非绘制模式下，节点可拖动
- 拖动节点自动更新渠道线
- 实时重新计算长度和坡度

**节点删除**:
- 双击节点删除
- 至少保留2个节点
- 自动更新渠道线

**撤销/重做**:
- ↶ 撤销上一步操作
- ↷ 重做被撤销的操作
- 完整的历史记录

### 3. 实时计算

**几何计算**:
- 📏 **总长度** - 渠道线总长度（米/公里）
- 📐 **平均坡度** - 基于起终点高程
- 📍 **节点数** - 当前节点总数
- 📊 **节点间距** - 各段长度

**高程插值**:
- 根据起点和终点高程
- 线性插值中间节点高程
- 自动计算每个节点的高程值

### 4. 渠道参数

**可配置参数**:
- **渠道宽度** - 1-100米
- **粗糙度** - 0.001-0.1（Manning系数）
- **起点高程** - 任意数值（米）
- **终点高程** - 任意数值（米）

### 5. GeoJSON导出

**导出内容**:
```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [[lng1, lat1], [lng2, lat2], ...]
  },
  "properties": {
    "name": "新建渠道",
    "length": 1250.5,
    "slope": 0.0012,
    "width": 10,
    "roughness": 0.025,
    "nodes": [
      {
        "position": [lng, lat],
        "elevation": 100.0,
        "distance": 0.0
      },
      ...
    ]
  }
}
```

---

## 💻 使用方法

### 基础用法

```typescript
import CanalDrawTool from '@/components/CanalDrawTool';
import MapViewer from '@/components/MapViewer';

const DrawPage = () => {
  const handleSave = (geoJSON) => {
    console.log('保存的GeoJSON:', geoJSON);
    // 处理保存逻辑
  };
  
  return (
    <MapViewer center={[39.9, 116.4]} zoom={13}>
      <CanalDrawTool onSave={handleSave} />
    </MapViewer>
  );
};
```

### 完整配置

```typescript
const AdvancedDraw = () => {
  const handleSave = (geoJSON: CanalGeoJSON) => {
    // 保存到服务器
    fetch('/api/canals', {
      method: 'POST',
      body: JSON.stringify(geoJSON),
    });
    
    // 或保存到本地存储
    localStorage.setItem('canal', JSON.stringify(geoJSON));
  };
  
  const initialData: CanalGeoJSON = {
    // 加载已有数据
  };
  
  return (
    <MapViewer>
      <CanalDrawTool
        onSave={handleSave}
        initialData={initialData}
      />
    </MapViewer>
  );
};
```

---

## 📋 API

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `onSave` | `(data: CanalGeoJSON) => void` | `-` | 保存回调函数 |
| `initialData` | `CanalGeoJSON` | `-` | 初始渠道数据 |

### CanalGeoJSON类型

```typescript
interface CanalGeoJSON {
  type: 'Feature';
  geometry: {
    type: 'LineString';
    coordinates: Position[]; // [lng, lat]
  };
  properties: {
    name: string;           // 渠道名称
    length: number;         // 总长度（米）
    slope: number;          // 平均坡度
    width: number;          // 宽度（米）
    roughness: number;      // 粗糙度
    nodes: {
      position: Position;   // 节点坐标
      elevation: number;    // 高程（米）
      distance: number;     // 距起点距离（米）
    }[];
  };
}
```

---

## 🎨 使用场景

### 场景1: 新建渠道

1. 点击"开始绘制"
2. 在地图上点击绘制路径
3. 设置渠道参数
4. 点击"停止绘制"
5. 调整节点位置（拖动）
6. 点击"保存为GeoJSON"

**体验**: 直观、流畅、精确

### 场景2: 编辑已有渠道

1. 加载GeoJSON数据
2. 拖动节点调整路径
3. 双击删除不需要的节点
4. 修改渠道参数
5. 重新保存

**体验**: 灵活、便捷

### 场景3: 导入配置编辑器

1. 绘制渠道并保存GeoJSON
2. 在配置编辑器中加载
3. 自动填充渠道参数
4. 添加边界条件
5. 运行仿真

**体验**: 无缝衔接

---

## 🔧 技术实现

### 地图事件监听

```typescript
useMapEvents({
  click: (e) => {
    if (isDrawing) {
      const newNode = {
        position: e.latlng,
        elevation: 0,
      };
      setNodes([...nodes, newNode]);
    }
  },
});
```

### 节点拖动

```typescript
<Marker
  position={node.position}
  draggable={!isDrawing}
  eventHandlers={{
    dragend: (e) => {
      const newPosition = e.target.getLatLng();
      updateNodePosition(index, newPosition);
    },
  }}
/>
```

### 长度计算 (Turf.js)

```typescript
import { calculateTotalLength } from '@/utils/geoUtils';

const coordinates = nodes.map(n => [n.position.lng, n.position.lat]);
const totalLength = calculateTotalLength(coordinates);
```

### 高程插值

```typescript
const elevations = nodes.map((_, index) => {
  const ratio = nodes.length > 1 ? index / (nodes.length - 1) : 0;
  return startElevation + (endElevation - startElevation) * ratio;
});
```

### 历史记录（撤销/重做）

```typescript
const [history, setHistory] = useState<CanalNode[][]>([[]]);
const [historyIndex, setHistoryIndex] = useState(0);

const addToHistory = (newNodes: CanalNode[]) => {
  const newHistory = history.slice(0, historyIndex + 1);
  newHistory.push([...newNodes]);
  setHistory(newHistory);
  setHistoryIndex(newHistory.length - 1);
};
```

---

## 🎯 geoUtils工具函数

### 距离计算

```typescript
import { calculateDistance, calculateTotalLength } from '@/utils/geoUtils';

// 两点间距离
const dist = calculateDistance([lng1, lat1], [lng2, lat2]); // 米

// 线段总长度
const total = calculateTotalLength(coordinates); // 米
```

### 坡度计算

```typescript
import { calculateAverageSlope } from '@/utils/geoUtils';

const slope = calculateAverageSlope(coordinates, elevations);
// 返回小数，如 0.0012 表示 0.12%
```

### 距离累积

```typescript
import { calculateDistancesFromStart } from '@/utils/geoUtils';

const distances = calculateDistancesFromStart(coordinates);
// [0, 125.5, 267.3, 450.0, ...] 每个节点距起点的距离
```

### 格式化显示

```typescript
import { formatDistance, formatSlope } from '@/utils/geoUtils';

formatDistance(1250.5); // "1.25 km"
formatDistance(125.5);  // "125.5 m"

formatSlope(0.0012);    // "0.1200%"
```

---

## 🎨 UI设计

### 控制面板

```
┌─────────────────────────────────────┐
│  [开始绘制] [↶] [↷] [清空]          │
├─────────────────────────────────────┤
│  节点数: 5                          │
│  总长度: 1.25 km                    │
│  平均坡度: 0.1200%                  │
├─────────────────────────────────────┤
│  渠道宽度 (m):  [10     ]           │
│  粗糙度:        [0.025  ]           │
│  起点高程 (m):  [100    ]           │
│  终点高程 (m):  [98     ]           │
├─────────────────────────────────────┤
│  [保存为GeoJSON]                    │
└─────────────────────────────────────┘
```

### 节点颜色

- 🟢 **起点** - 绿色 (#52c41a)
- 🔵 **中间节点** - 蓝色 (#1890ff)
- 🔴 **终点** - 红色 (#f5222d)

---

## 🐛 常见问题

### Q1: 节点无法拖动

**问题**: 点击节点没反应

**解决**:
- 确保不在"绘制模式"中
- 点击"停止绘制"按钮
- 节点在非绘制模式下才可拖动

### Q2: 双击地图放大而不是删除节点

**问题**: 想删除节点但地图放大了

**解决**:
- 精确双击节点（不是节点旁边）
- 节点有12px的点击区域
- 或使用清空按钮重新绘制

### Q3: 保存后坐标顺序混乱

**问题**: GeoJSON中坐标顺序不对

**解决**:
- GeoJSON标准使用 `[经度, 纬度]` 顺序
- Leaflet使用 `[纬度, 经度]` 顺序
- 组件已自动转换，无需手动处理

---

## 🔜 未来改进

### 短期

- [ ] 支持添加中间节点（不仅在末尾）
- [ ] 节点编号显示
- [ ] 渠道宽度可视化
- [ ] 坡度分段计算

### 中期

- [ ] GeoJSON导入功能
- [ ] 多条渠道同时编辑
- [ ] 渠道分支支持
- [ ] 导出为配置文件

### 长期

- [ ] 自动地形高程获取（DEM）
- [ ] 智能路径优化
- [ ] 成本估算
- [ ] 3D可视化

---

## 📚 相关资源

- [Turf.js文档](https://turfjs.org/)
- [GeoJSON规范](https://geojson.org/)
- [Leaflet Markers](https://leafletjs.com/reference.html#marker)

---

<p align="center">
  <b>CanalDrawTool - Phase 5.2.2 Complete</b>
</p>
