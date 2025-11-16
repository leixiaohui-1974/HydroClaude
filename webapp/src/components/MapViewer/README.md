# MapViewer 组件

**Phase 5.2.1 - 地图基础**

---

## 📖 概述

MapViewer是HydroClaude GIS功能的核心组件，提供了基于Leaflet的交互式地图查看功能。

### 核心功能

- ✅ 基础地图显示
- ✅ 多种底图切换
- ✅ 缩放控件
- ✅ 比例尺显示
- ✅ 鼠标坐标显示
- ✅ 响应式设计

---

## 🎯 功能特性

### 1. 底图选择

支持6种内置底图：

| 底图 | 说明 | 适用场景 |
|------|------|----------|
| OpenStreetMap | 标准街道地图 | 城市规划、导航 |
| OSM HOT | 人道主义地图 | 灾害响应 |
| CartoDB Light | 浅色底图 | 数据叠加 |
| CartoDB Dark | 深色底图 | 夜间模式 |
| Esri World Imagery | 卫星影像 | 地形分析 |
| Esri World Street | Esri街道地图 | 详细地图 |

### 2. 地图控件

**缩放控件**:
- 放大 (+)
- 缩小 (-)
- 鼠标滚轮缩放
- 双击缩放

**比例尺**:
- 公制单位
- 自动调整
- 实时更新

**坐标显示**:
- 鼠标实时坐标
- 精度：6位小数
- WGS84坐标系

---

## 💻 使用方法

### 基础用法

```typescript
import MapViewer from '@/components/MapViewer';

const MyMapPage = () => {
  return (
    <MapViewer
      center={[39.9042, 116.4074]} // 北京
      zoom={13}
      height="600px"
    />
  );
};
```

### 完整配置

```typescript
import MapViewer from '@/components/MapViewer';
import type { LatLngExpression } from 'leaflet';

const AdvancedMap = () => {
  const [mapCenter] = useState<LatLngExpression>([39.9042, 116.4074]);
  
  const handleMapReady = (map: L.Map) => {
    console.log('地图已加载', map);
    // 可以在这里做更多初始化
  };
  
  return (
    <MapViewer
      center={mapCenter}
      zoom={13}
      height="calc(100vh - 200px)"
      defaultBaseMap="cartoLight"
      showControls={true}
      showBaseMapSelector={true}
      onMapReady={handleMapReady}
    >
      {/* 在这里添加子组件，如标记、线、多边形等 */}
    </MapViewer>
  );
};
```

### 添加子组件

```typescript
import MapViewer from '@/components/MapViewer';
import { Marker, Popup } from 'react-leaflet';

const MapWithMarker = () => {
  return (
    <MapViewer center={[39.9042, 116.4074]} zoom={13}>
      <Marker position={[39.9042, 116.4074]}>
        <Popup>
          北京天安门
        </Popup>
      </Marker>
    </MapViewer>
  );
};
```

---

## 📋 API

### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `center` | `LatLngExpression` | `[39.9042, 116.4074]` | 地图中心点坐标 |
| `zoom` | `number` | `13` | 初始缩放级别(1-20) |
| `height` | `string \| number` | `'600px'` | 地图高度 |
| `defaultBaseMap` | `BaseMapType` | `'osm'` | 默认底图 |
| `showControls` | `boolean` | `true` | 显示地图控件 |
| `showBaseMapSelector` | `boolean` | `true` | 显示底图选择器 |
| `onMapReady` | `(map: L.Map) => void` | `-` | 地图加载完成回调 |
| `children` | `React.ReactNode` | `-` | 子组件（标记、线等） |

### BaseMapType

```typescript
type BaseMapType = 
  | 'osm'
  | 'osmHOT'
  | 'cartoLight'
  | 'cartoDark'
  | 'esriWorldImagery'
  | 'esriWorldStreet';
```

---

## 🎨 样式自定义

### 修改地图高度

```typescript
<MapViewer
  height="800px"          // 固定高度
  height="80vh"           // 视口百分比
  height="calc(100% - 100px)"  // 计算高度
/>
```

### 自定义CSS

```css
/* 修改控制栏背景 */
.map-controls-bar {
  background: #fff;
  padding: 12px 16px;
}

/* 修改坐标显示样式 */
.map-coordinates {
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
}
```

---

## 🔧 技术实现

### Leaflet集成

```typescript
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

<MapContainer center={center} zoom={zoom}>
  <TileLayer url={baseMapUrl} attribution={attribution} />
</MapContainer>
```

### 坐标监听

```typescript
const handleMapCreated = (map: L.Map) => {
  map.on('mousemove', (e: L.LeafletMouseEvent) => {
    setMousePosition({
      lat: e.latlng.lat,
      lng: e.latlng.lng,
    });
  });
};
```

### 缩放监听

```typescript
map.on('zoomend', () => {
  setMapZoom(map.getZoom());
});
```

---

## 📊 坐标系统

### WGS84 (默认)

- **EPSG**: 4326
- **格式**: [纬度, 经度]
- **范围**: 纬度 [-90, 90]，经度 [-180, 180]
- **用途**: GPS、Web地图

### 示例坐标

```typescript
// 中国主要城市
const cities = {
  beijing: [39.9042, 116.4074],   // 北京
  shanghai: [31.2304, 121.4737],  // 上海
  guangzhou: [23.1291, 113.2644], // 广州
  shenzhen: [22.5431, 114.0579],  // 深圳
};
```

---

## 🎯 常见用例

### 用例1: 项目位置展示

```typescript
const ProjectMap = ({ project }: { project: Project }) => {
  return (
    <MapViewer
      center={[project.latitude, project.longitude]}
      zoom={15}
      height="400px"
    >
      <Marker position={[project.latitude, project.longitude]}>
        <Popup>{project.name}</Popup>
      </Marker>
    </MapViewer>
  );
};
```

### 用例2: 多点展示

```typescript
const MultiPointMap = ({ points }: { points: Point[] }) => {
  return (
    <MapViewer center={points[0]} zoom={12}>
      {points.map((point, i) => (
        <Marker key={i} position={point}>
          <Popup>点 {i + 1}</Popup>
        </Marker>
      ))}
    </MapViewer>
  );
};
```

### 用例3: 路径展示

```typescript
import { Polyline } from 'react-leaflet';

const RouteMap = ({ route }: { route: LatLng[] }) => {
  return (
    <MapViewer center={route[0]} zoom={13}>
      <Polyline positions={route} color="blue" weight={3} />
    </MapViewer>
  );
};
```

---

## 🐛 常见问题

### Q1: 地图不显示

**问题**: 地图区域空白

**解决**:
1. 确保导入了CSS: `import 'leaflet/dist/leaflet.css'`
2. 设置明确的高度: `height="600px"`
3. 检查网络连接（底图需要网络加载）

### Q2: 标记图标不显示

**问题**: Marker显示为空白方块

**解决**:
```typescript
// 在组件文件中添加
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;
```

### Q3: 坐标顺序混乱

**问题**: 地图显示位置不对

**解决**:
- Leaflet使用 `[纬度, 经度]` 顺序
- 与某些GeoJSON标准 `[经度, 纬度]` 相反
- 始终检查坐标顺序

---

## 🔜 未来改进

### 短期 (Phase 5.2)

- [ ] 添加绘制工具
- [ ] 添加测量工具
- [ ] 支持坐标系转换

### 中期

- [ ] 离线地图支持
- [ ] 自定义底图
- [ ] 3D地形

### 长期

- [ ] 卫星影像时序
- [ ] 实时气象叠加
- [ ] AR增强现实

---

## 📚 相关资源

- [Leaflet官方文档](https://leafletjs.com/)
- [React-Leaflet文档](https://react-leaflet.js.org/)
- [OpenStreetMap](https://www.openstreetmap.org/)

---

<p align="center">
  <b>MapViewer - Phase 5.2.1 Complete</b>
</p>
