# 🚀 Phase 5.2: GIS集成 - 项目启动

**启动日期**: 2025-11-15  
**预计完成**: 2026-01-15  
**预计耗时**: 1.5个月  
**Phase 5进度**: 40% → 60%

---

## 📋 项目概述

Phase 5.2将为HydroClaude添加地理信息系统（GIS）功能，使用户能够在地图上绘制渠道、查看结果分布，实现真正的可视化水力模拟。

### 核心目标

1. **地图基础** - 集成Leaflet地图库
2. **渠道绘制** - 在地图上绘制和编辑渠道
3. **结果叠加** - 在地图上显示仿真结果

---

## 🎯 功能规划

### 5.2.1: 地图基础 (2周)

**任务清单**:
- [ ] Leaflet地图集成
- [ ] 底图选择 (OSM/Google/Bing)
- [ ] 地图控件 (缩放/图层/比例尺)
- [ ] 坐标系转换 (WGS84/投影)

**交付物**:
- MapViewer组件
- 底图切换功能
- 基础地图控件
- 坐标转换工具

**预计代码量**: ~600行

---

### 5.2.2: 渠道绘制 (2周)

**任务清单**:
- [ ] 线绘制工具
- [ ] 节点编辑 (添加/删除/移动)
- [ ] 长度/坡度计算
- [ ] GeoJSON导入导出

**交付物**:
- CanalDrawTool组件
- 节点编辑器
- 几何计算工具
- GeoJSON序列化

**预计代码量**: ~800行

---

### 5.2.3: 结果叠加 (2周)

**任务清单**:
- [ ] 水深颜色映射
- [ ] 流速矢量场
- [ ] 淹没范围显示
- [ ] 地图动画播放

**交付物**:
- ResultsOverlay组件
- 颜色映射工具
- 矢量场渲染
- 地图动画控制

**预计代码量**: ~700行

---

## 🏗️ 技术架构

### 核心技术栈

**地图库**:
- **react-leaflet** - React封装的Leaflet
- **leaflet** - 开源地图库
- **leaflet-draw** - 绘图插件

**辅助库**:
- **proj4** - 坐标系转换
- **turf.js** - 地理计算
- **geojson** - GeoJSON类型定义

### 组件架构

```
webapp/src/
├── components/
│   ├── MapViewer/           # 地图查看器
│   │   ├── index.tsx        # 主组件
│   │   ├── MapControls.tsx  # 地图控件
│   │   ├── BaseMapSelector.tsx  # 底图选择
│   │   └── README.md
│   ├── CanalDrawTool/       # 渠道绘制工具
│   │   ├── index.tsx        # 绘制工具主组件
│   │   ├── DrawControls.tsx # 绘制控件
│   │   ├── NodeEditor.tsx   # 节点编辑器
│   │   ├── GeometryInfo.tsx # 几何信息显示
│   │   └── README.md
│   └── ResultsOverlay/      # 结果叠加
│       ├── index.tsx        # 叠加层主组件
│       ├── ColorMap.tsx     # 颜色映射
│       ├── VectorField.tsx  # 矢量场
│       ├── Animation.tsx    # 动画控制
│       └── README.md
├── pages/
│   └── Map/                 # 地图页面
│       └── index.tsx
└── utils/
    ├── geoUtils.ts          # 地理计算工具
    └── coordTransform.ts    # 坐标转换
```

---

## 📦 依赖安装

### NPM包

```json
{
  "dependencies": {
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1",
    "leaflet-draw": "^1.0.4",
    "@types/leaflet": "^1.9.8",
    "@types/leaflet-draw": "^1.0.11",
    "proj4": "^2.9.2",
    "@turf/turf": "^6.5.0",
    "geojson": "^0.5.0",
    "@types/geojson": "^7946.0.14"
  }
}
```

### 安装命令

```bash
cd /workspace/webapp
npm install leaflet react-leaflet leaflet-draw proj4 @turf/turf geojson
npm install -D @types/leaflet @types/leaflet-draw @types/geojson
```

---

## 🎨 功能设计

### 1. 地图查看器

**功能**:
- 基础地图显示
- 多种底图切换
- 缩放/平移控制
- 比例尺显示
- 鼠标坐标显示

**UI设计**:
```
┌─────────────────────────────────────────────────────────┐
│  [底图▼] [图层▼] [工具▼]                    [缩放控件] │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                    地图显示区域                          │
│                                                          │
│                                                          │
│                                                          │
│                                                          │
│                                     [比例尺 0___100m]    │
│  [坐标: 116.404, 39.915]                                │
└─────────────────────────────────────────────────────────┘
```

---

### 2. 渠道绘制工具

**功能**:
- 点击绘制渠道线
- 节点拖动编辑
- 节点添加/删除
- 实时长度计算
- 坡度自动计算
- GeoJSON导出

**UI设计**:
```
┌─────────────────────────────────────────────────────────┐
│  [✏️ 绘制] [✋ 编辑] [🗑️ 删除] [💾 保存] [📂 加载]       │
├─────────────────────────────────────────────────────────┤
│                  地图 + 渠道线                           │
│    起点●━━━━━●━━━━━●━━━━━●终点                        │
│         节点1   节点2   节点3                            │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 渠道信息                                         │   │
│  │ 总长度: 1250.5 m                                │   │
│  │ 节点数: 4                                       │   │
│  │ 平均坡度: 0.0012                                │   │
│  │ 起点高程: 100.0 m                               │   │
│  │ 终点高程: 98.5 m                                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

### 3. 结果叠加

**功能**:
- 水深颜色映射
- 流速箭头显示
- 淹没范围渲染
- 时间动画播放
- 图例显示

**UI设计**:
```
┌─────────────────────────────────────────────────────────┐
│  [图层] ☑水深 ☑流速 ☑渠道  [播放▶] ━━━●━━ 时间:10s   │
├─────────────────────────────────────────────────────────┤
│                  地图 + 结果叠加                         │
│         颜色渐变表示水深                                 │
│         箭头表示流速方向和大小                           │
│                                                          │
│  ┌─────────────┐                                        │
│  │ 图例         │                                        │
│  │ 水深 (m)     │                                        │
│  │ █ 3.5        │                                        │
│  │ █ 3.0        │                                        │
│  │ █ 2.5        │                                        │
│  │ █ 2.0        │                                        │
│  │ █ 1.5        │                                        │
│  │              │                                        │
│  │ 流速 (m/s)   │                                        │
│  │ → 0.5        │                                        │
│  │ → 1.0        │                                        │
│  │ → 1.5        │                                        │
│  └─────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 数据结构

### 渠道GeoJSON

```typescript
interface CanalGeoJSON {
  type: 'Feature';
  geometry: {
    type: 'LineString';
    coordinates: [number, number][]; // [经度, 纬度]
  };
  properties: {
    name: string;
    length: number;         // 总长度 (m)
    slope: number;          // 平均坡度
    width: number;          // 宽度 (m)
    roughness: number;      // 粗糙度
    nodes: {
      position: [number, number];
      elevation: number;    // 高程 (m)
      distance: number;     // 距起点距离 (m)
    }[];
  };
}
```

### 结果叠加数据

```typescript
interface ResultsOverlayData {
  type: 'Feature';
  geometry: {
    type: 'LineString';
    coordinates: [number, number][];
  };
  properties: {
    depths: number[];       // 每个点的水深
    velocities: number[];   // 每个点的流速
    positions: number[];    // 距起点距离
    timestamp?: number;     // 时间戳 (非恒定流)
  };
}
```

---

## 🔧 技术实现

### Leaflet集成

```typescript
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const MapViewer: React.FC = () => {
  return (
    <MapContainer
      center={[39.9, 116.4]} // 北京
      zoom={13}
      style={{ height: '100%', width: '100%' }}
    >
      {/* 底图层 */}
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />
      
      {/* 其他图层 */}
    </MapContainer>
  );
};
```

### 渠道绘制

```typescript
import { Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';

const CanalDrawTool: React.FC = () => {
  const [points, setPoints] = useState<L.LatLng[]>([]);
  
  useMapEvents({
    click: (e) => {
      setPoints([...points, e.latlng]);
    },
  });
  
  return (
    <Polyline
      positions={points}
      color="blue"
      weight={3}
    />
  );
};
```

### 颜色映射

```typescript
import { Polyline } from 'react-leaflet';

const ResultsOverlay: React.FC<{ data: ResultsOverlayData }> = ({ data }) => {
  const getColor = (depth: number) => {
    // 颜色映射: 深蓝 → 浅蓝
    const ratio = (depth - minDepth) / (maxDepth - minDepth);
    const hue = 240 - ratio * 60; // 240(蓝) → 180(青)
    return `hsl(${hue}, 100%, 50%)`;
  };
  
  return (
    <>
      {data.properties.depths.map((depth, i) => (
        <Polyline
          key={i}
          positions={[
            data.geometry.coordinates[i],
            data.geometry.coordinates[i + 1],
          ]}
          color={getColor(depth)}
          weight={5}
        />
      ))}
    </>
  );
};
```

---

## 🎓 用户场景

### 场景1: 绘制新渠道

1. 打开地图页面
2. 点击"绘制"按钮
3. 在地图上点击绘制渠道线
4. 编辑节点调整路径
5. 输入高程数据
6. 保存为GeoJSON
7. 导入到配置编辑器

### 场景2: 查看仿真结果

1. 运行仿真
2. 切换到地图页面
3. 加载渠道GeoJSON
4. 叠加结果数据
5. 查看水深颜色分布
6. 查看流速矢量场
7. 播放动画（非恒定流）

### 场景3: 真实地形对接

1. 加载底图（卫星图）
2. 在真实地形上绘制渠道
3. 使用DEM数据获取高程
4. 自动计算坡度
5. 生成配置文件
6. 运行仿真
7. 结果叠加到地图

---

## 📈 开发计划

### Week 1-2: 地图基础

**Day 1-2**: Leaflet集成
- 安装依赖
- 创建MapViewer组件
- 基础地图显示

**Day 3-4**: 底图选择
- OSM底图
- Google卫星图
- Bing地图
- 底图切换UI

**Day 5-7**: 地图控件
- 缩放控件
- 图层控制
- 比例尺
- 坐标显示

**Day 8-10**: 坐标转换
- proj4集成
- WGS84支持
- 投影坐标系
- 坐标转换工具

---

### Week 3-4: 渠道绘制

**Day 11-13**: 线绘制工具
- 点击绘制
- 线段显示
- 绘制控制

**Day 14-16**: 节点编辑
- 节点拖动
- 节点添加
- 节点删除
- 节点信息

**Day 17-19**: 几何计算
- 长度计算（turf.js）
- 坡度计算
- 高程插值

**Day 20-21**: GeoJSON支持
- 导入GeoJSON
- 导出GeoJSON
- 数据验证

---

### Week 5-6: 结果叠加

**Day 22-24**: 颜色映射
- 颜色方案设计
- 分段渲染
- 图例显示

**Day 25-27**: 矢量场
- 箭头绘制
- 方向计算
- 大小比例

**Day 28-30**: 动画
- 时间控制
- 帧渲染
- 播放控制

**Day 31-33**: 优化和测试
- 性能优化
- 用户测试
- 文档编写

---

## ✅ 验收标准

### 功能完整性

- [ ] 地图正常显示
- [ ] 底图可切换
- [ ] 渠道可绘制
- [ ] 节点可编辑
- [ ] 几何信息正确
- [ ] GeoJSON导入导出
- [ ] 结果正确叠加
- [ ] 颜色映射合理
- [ ] 动画播放流畅

### 性能指标

- [ ] 地图加载 < 2秒
- [ ] 绘制响应 < 100ms
- [ ] 叠加渲染 < 1秒
- [ ] 动画帧率 > 30fps

### 用户体验

- [ ] 操作直观
- [ ] 反馈及时
- [ ] 错误提示清晰
- [ ] 帮助文档完善

---

## 🔜 后续工作

### Phase 5.3: 插件系统

**预计**: 2026-01-15 → 2026-02-15

### Phase 5.4: 桌面应用 (可选)

**预计**: 2026-02-15 → 2026-03-15

### Phase 5.5: 社区平台

**预计**: 2026-03-15 → 2026-05-01

---

<p align="center">
  <b>🚀 Phase 5.2: GIS集成 - 项目启动！ 🚀</b>
</p>

<p align="center">
  <i>From Data to Maps - Visualize Everywhere</i>
</p>

<p align="center">
  <b>Let's Build the Future of Hydraulic GIS!</b>
</p>

---

**HydroClaude Development Team**  
**Phase 5.2 Start: November 15, 2025**  
**Expected Complete: January 15, 2026**  
**Phase 5 Progress: 40% → 60%**
