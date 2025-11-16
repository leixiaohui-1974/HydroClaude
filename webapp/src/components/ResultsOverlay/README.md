# ResultsOverlay 组件

**Phase 5.2.3 - 结果叠加**

---

## 📖 概述

ResultsOverlay是HydroClaude GIS功能的结果可视化组件，在地图上叠加显示仿真结果，包括水深颜色映射和流速矢量场。

### 核心功能

- ✅ 水深颜色映射
- ✅ 流速颜色映射
- ✅ 流速矢量场
- ✅ 多种配色方案
- ✅ 交互式图例
- ✅ 透明度控制
- ✅ 矢量密度调节

---

## 🎯 功能特性

### 1. 颜色映射

**5种配色方案**:
1. **depth** - 深蓝→浅蓝→青→黄（水深专用）
2. **velocity** - 蓝→绿→黄→红（流速专用）
3. **viridis** - 科学可视化标准配色
4. **plasma** - 等离子配色
5. **coolwarm** - 冷暖色配色

**颜色插值**:
- 线性插值RGB值
- 平滑渐变过渡
- 自动归一化

### 2. 水深叠加

**显示方式**:
- 彩色线段叠加在渠道上
- 颜色表示水深大小
- 鼠标悬停显示详细信息

**控制选项**:
- 开关显示
- 配色方案选择
- 透明度调节（10%-100%）

### 3. 流速叠加

**显示方式**:
- 彩色线段表示流速
- 颜色从蓝（慢）到红（快）
- 支持与水深同时显示

**控制选项**:
- 开关显示
- 配色方案选择
- 透明度调节

### 4. 矢量场

**显示方式**:
- 箭头表示流速方向和大小
- 箭头颜色表示流速
- 箭头长度与流速成正比

**控制选项**:
- 开关显示
- 密度调节（1-50）
- 自动方向计算

### 5. 交互式图例

**图例内容**:
- 颜色条
- 数值标签
- 单位说明

**位置**:
- 右下角
- 自动显示/隐藏

---

## 💻 使用方法

### 基础用法

```typescript
import ResultsOverlay from '@/components/ResultsOverlay';
import MapViewer from '@/components/MapViewer';

const ResultsMap = () => {
  const resultsData = {
    coordinates: [
      [116.404, 39.915],
      [116.405, 39.916],
      [116.406, 39.917],
    ],
    depths: [3.0, 2.9, 2.8],
    velocities: [1.5, 1.6, 1.7],
    positions: [0, 150, 300],
  };
  
  return (
    <MapViewer center={[39.915, 116.404]} zoom={15}>
      <ResultsOverlay data={resultsData} />
    </MapViewer>
  );
};
```

### 完整配置

```typescript
const AdvancedResults = () => {
  return (
    <MapViewer>
      <ResultsOverlay
        data={resultsData}
        showDepth={true}          // 显示水深
        showVelocity={false}      // 不显示流速
        showVelocityVectors={true} // 显示矢量场
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
| `data` | `ResultsOverlayData` | **必填** | 结果数据 |
| `showDepth` | `boolean` | `true` | 显示水深 |
| `showVelocity` | `boolean` | `false` | 显示流速 |
| `showVelocityVectors` | `boolean` | `false` | 显示矢量场 |

### ResultsOverlayData类型

```typescript
interface ResultsOverlayData {
  coordinates: Position[];     // 渠道坐标 [[lng,lat], ...]
  depths: number[];            // 水深数组 (m)
  velocities: number[];        // 流速数组 (m/s)
  positions: number[];         // 距起点距离 (m)
  froudeNumbers?: number[];    // Froude数（可选）
}
```

---

## 🎨 配色方案

### 水深配色（depth）

```
深蓝 (#00008B) ──→ 蓝色 (#0064FF) ──→ 浅蓝 (#00BFFF) ──→ 天蓝 (#87CEEB) ──→ 黄色 (#FFFF00)
  0.0              0.25              0.5              0.75              1.0
```

**适用**: 水深、高程

### 流速配色（velocity）

```
蓝色 (#0000FF) ──→ 绿色 (#00FF00) ──→ 黄色 (#FFFF00) ──→ 红色 (#FF0000)
  0.0              0.33              0.67              1.0
```

**适用**: 流速、Froude数

### Viridis配色

```
深紫 ──→ 深蓝 ──→ 青绿 ──→ 黄绿 ──→ 黄色
```

**适用**: 科学可视化、论文发表

### Plasma配色

```
深蓝紫 ──→ 紫色 ──→ 红色 ──→ 橙色 ──→ 黄色
```

**适用**: 高对比度场景

### CoolWarm配色

```
冷蓝 ──→ 浅蓝 ──→ 白色 ──→ 浅红 ──→ 暖红
```

**适用**: 偏差分析、对比

---

## 🔧 技术实现

### 颜色映射算法

```typescript
// 归一化到[0,1]
const normalized = (value - min) / (max - min);

// 查找相邻颜色点
for (let i = 0; i < colorMap.length - 1; i++) {
  if (normalized >= colorMap[i].value && 
      normalized <= colorMap[i+1].value) {
    // 线性插值
    const ratio = (normalized - colorMap[i].value) / 
                  (colorMap[i+1].value - colorMap[i].value);
    return interpolateColor(colorMap[i].color, colorMap[i+1].color, ratio);
  }
}
```

### RGB插值

```typescript
const interpolateColor = (c1: RGB, c2: RGB, ratio: number): RGB => ({
  r: Math.round(c1.r + (c2.r - c1.r) * ratio),
  g: Math.round(c1.g + (c2.g - c1.g) * ratio),
  b: Math.round(c1.b + (c2.b - c1.b) * ratio),
});
```

### 矢量计算

```typescript
// 计算方向向量
const dx = end[0] - start[0];
const dy = end[1] - start[1];
const length = Math.sqrt(dx * dx + dy * dy);

// 归一化并缩放
const scale = velocity * 0.0001;
const arrowEnd = [
  start[0] + (dx / length) * scale,
  start[1] + (dy / length) * scale,
];
```

---

## 🎯 使用场景

### 场景1: 查看水深分布

1. 运行仿真获得结果
2. 切换到"结果叠加"标签
3. 开启"显示水深"
4. 选择合适的配色方案
5. 调整透明度查看细节

**体验**: 直观看到水深变化

### 场景2: 分析流速

1. 关闭水深显示
2. 开启"显示流速"
3. 选择velocity配色
4. 开启矢量场
5. 调整矢量密度

**体验**: 清晰看到流速分布和方向

### 场景3: 综合分析

1. 同时开启水深和流速
2. 调整透明度区分层次
3. 开启矢量场
4. 鼠标悬停查看详细数值

**体验**: 全面了解流动状态

---

## 🎨 UI设计

### 控制面板

```
┌─────────────────────────────┐
│  ☑ 显示水深                 │
│  ☐ 显示流速                 │
│  ☐ 显示矢量场               │
├─────────────────────────────┤
│  透明度: 80%                │
│  ━━━━━●━━━━                │
├─────────────────────────────┤
│  水深配色:                  │
│  [深蓝-浅蓝-黄 ▼]          │
├─────────────────────────────┤
│  矢量密度: 10               │
│  ━━━━━●━━━━                │
└─────────────────────────────┘
```

### 图例

```
┌─────────────────┐
│  水深 (m)       │
├─────────────────┤
│ █ 3.00          │
│ █ 2.75          │
│ █ 2.50          │
│ █ 2.25          │
│ █ 2.00          │
└─────────────────┘
```

---

## 🔧 colorMaps工具

### 获取颜色

```typescript
import { getColorString } from '@/utils/colorMaps';

const color = getColorString(2.5, 2.0, 3.0, 'depth');
// 返回: "#00BFFF" (16进制颜色)
```

### 生成图例

```typescript
import { generateLegendData } from '@/utils/colorMaps';

const legend = generateLegendData(2.0, 3.0, 10, 'depth');
// 返回: [
//   { value: 3.00, color: "#FFFF00", label: "3.00" },
//   { value: 2.90, color: "#87CEEB", label: "2.90" },
//   ...
// ]
```

### 计算颜色范围

```typescript
import { calculateColorRange } from '@/utils/colorMaps';

const range = calculateColorRange([2.0, 2.5, 3.0, 2.8, 2.3]);
// 返回: { min: 2.0, max: 3.0 }
```

---

## 🐛 常见问题

### Q1: 颜色显示不正确

**问题**: 颜色全部相同

**解决**:
- 检查数据范围（min !== max）
- 确保数据不全是NaN
- 查看控制台错误信息

### Q2: 矢量不显示

**问题**: 开启矢量场但没有箭头

**解决**:
- 检查coordinates长度 >= 2
- 确保velocities有有效值
- 调整矢量密度（减小值）

### Q3: 图例数值不合理

**问题**: 图例显示的范围不对

**解决**:
- 数据会自动排除极值（95%百分位）
- 可以手动设置min/max
- 检查数据单位是否正确

---

## 🔜 未来改进

### 短期

- [ ] 自定义配色方案
- [ ] 等高线显示
- [ ] 数据点标注
- [ ] 截面选择

### 中期

- [ ] 3D高程显示
- [ ] 动画播放（时间序列）
- [ ] 多结果对比
- [ ] 导出为图片

### 长期

- [ ] 实时更新
- [ ] WebGL加速渲染
- [ ] 大数据优化
- [ ] VR/AR支持

---

## 📚 相关资源

- [颜色理论](https://en.wikipedia.org/wiki/Color_theory)
- [科学配色](https://matplotlib.org/stable/tutorials/colors/colormaps.html)
- [Leaflet文档](https://leafletjs.com/)

---

<p align="center">
  <b>ResultsOverlay - Phase 5.2.3 Complete</b>
</p>
