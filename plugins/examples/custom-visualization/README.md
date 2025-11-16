# 自定义可视化插件

**版本**: 1.0.0  
**作者**: VizTeam  
**类别**: visualization

---

## 📖 概述

自定义可视化插件为HydroClaude添加新的图表类型，包括热力图、等值线图、3D表面图等，提供更丰富的数据可视化方式。

### 新增图表

- ✅ 热力图 (Heatmap)
- ✅ 等值线图 (Contour)
- ✅ 3D表面图 (3D Surface)
- ✅ 矢量场图 (Vector Field)

---

## 🚀 快速开始

### 安装插件

1. 打开HydroClaude
2. 进入"插件市场"
3. 搜索"自定义可视化"
4. 点击"安装"

### 创建图表

1. 运行仿真获得结果
2. 点击工具栏"自定义图表"
3. 选择图表类型
4. 配置参数
5. 生成图表

---

## 🎯 图表类型

### 1. 热力图 (Heatmap)

**用途**: 显示二维数据分布，颜色表示数值大小

**适用场景**:
- 水深时空分布
- 流速时空变化
- 温度场分布

**示例代码**:
```typescript
api.commands.execute('custom-viz.createHeatmap');
```

**效果**:
```
高 ┃ █████████████
   ┃ ███▓▓▓▓▓▓███
   ┃ ██▓▓▒▒▒▓▓██
   ┃ █▓▓▒░░░▒▓▓█
低 ┃ ▓▒░░   ░▒▓
   ┗━━━━━━━━━━━━
    距离 →
```

### 2. 等值线图 (Contour)

**用途**: 用等值线表示数值相等的点

**适用场景**:
- 水面等高线
- 流速等值线
- Froude数分布

**示例代码**:
```typescript
api.commands.execute('custom-viz.createContour');
```

**效果**:
```
  ╱───╲
 ╱  3  ╲  ╱───╲
╱───────╲╱  2  ╲
╲  2.5  ╱╲─────╱
 ╲─────╱  ╲  1.5
```

### 3. 3D表面图 (3D Surface)

**用途**: 三维立体显示数据

**适用场景**:
- 水面形态
- 河床地形
- 3D流场

**示例代码**:
```typescript
api.commands.execute('custom-viz.create3DSurface');
```

**效果**:
```
      ╱╲
     ╱  ╲
    ╱    ╲╱╲
   ╱    ╱╲  ╲
  ╱____╱  ╲__╲
```

### 4. 矢量场图 (Vector Field)

**用途**: 显示矢量的方向和大小

**适用场景**:
- 流速矢量场
- 力场分布
- 梯度场

**效果**:
```
→ → → → →
↗ → → → ↘
↑ → ○ ← ↓
↖ ← ← ← ↙
← ← ← ← ←
```

---

## 📋 API使用

### 创建热力图

```typescript
const data = {
  x: [0, 100, 200, 300],      // X轴坐标
  y: [0, 10, 20, 30],         // Y轴坐标
  z: [                         // Z值（二维数组）
    [3.0, 2.9, 2.8, 2.7],
    [3.1, 3.0, 2.9, 2.8],
    [3.2, 3.1, 3.0, 2.9],
    [3.3, 3.2, 3.1, 3.0],
  ],
  colorscale: 'Viridis',       // 配色方案
  title: '水深热力图'
};

api.visualization.createChart('heatmap', data);
```

### 创建等值线图

```typescript
const data = {
  x: [0, 100, 200, 300],
  y: [0, 10, 20, 30],
  z: [[...], [...], [...], [...]],
  contours: {
    start: 0,
    end: 3,
    size: 0.2
  },
  title: '流速等值线'
};

api.visualization.createChart('contour', data);
```

### 创建3D表面图

```typescript
const data = {
  x: [0, 100, 200, 300],
  y: [0, 10, 20, 30],
  z: [[...], [...], [...], [...]],
  colorscale: 'Jet',
  title: '水面3D图'
};

api.visualization.createChart('surface3d', data);
```

---

## ⚙️ 配置选项

### 配色方案

可用的配色方案：
- `Viridis` - 科学可视化标准
- `Jet` - 经典彩虹配色
- `Hot` - 热力图配色
- `Cool` - 冷色调
- `Plasma` - 等离子配色
- `RdBu` - 红蓝双色

### 等值线配置

```typescript
{
  contours: {
    start: 0,        // 起始值
    end: 10,         // 结束值
    size: 0.5,       // 间隔
    coloring: 'lines' // 'fill' | 'lines' | 'none'
  }
}
```

### 3D视角

```typescript
{
  camera: {
    eye: { x: 1.5, y: 1.5, z: 1.5 },
    center: { x: 0, y: 0, z: 0 }
  }
}
```

---

## 📊 数据格式

### 输入格式

**网格数据**:
```typescript
{
  x: number[];      // 长度为m
  y: number[];      // 长度为n
  z: number[][];    // 大小为n×m
}
```

**散点数据**:
```typescript
{
  x: number[];      // 长度为k
  y: number[];      // 长度为k
  z: number[];      // 长度为k
}
```

### 数据转换

```typescript
// 从1D转2D
function reshape(data: number[], nx: number, ny: number): number[][] {
  const result = [];
  for (let i = 0; i < ny; i++) {
    result.push(data.slice(i * nx, (i + 1) * nx));
  }
  return result;
}

// 插值到网格
function interpolateToGrid(
  points: { x: number; y: number; z: number }[],
  nx: number,
  ny: number
): { x: number[]; y: number[]; z: number[][] } {
  // 实现插值算法
  // ...
}
```

---

## 🎨 样式定制

### 自定义配色

```typescript
const customColorscale = [
  [0, 'rgb(0, 0, 255)'],      // 蓝
  [0.5, 'rgb(0, 255, 0)'],    // 绿
  [1, 'rgb(255, 0, 0)']       // 红
];

api.visualization.createChart('heatmap', {
  ...data,
  colorscale: customColorscale
});
```

### 自定义标记

```typescript
{
  marker: {
    size: 5,
    color: 'red',
    symbol: 'circle'
  }
}
```

---

## 🔧 高级功能

### 动画

```typescript
// 创建时间序列动画
const frames = timeSteps.map(t => ({
  data: [{
    z: getDataAtTime(t)
  }],
  name: `t=${t}s`
}));

api.visualization.createChart('heatmap', {
  ...data,
  frames
});
```

### 交互

```typescript
// 添加点击事件
chart.on('plotly_click', (data) => {
  const point = data.points[0];
  console.log(`Clicked: x=${point.x}, y=${point.y}, z=${point.z}`);
});

// 添加选择事件
chart.on('plotly_selected', (data) => {
  const selected = data.points.map(p => ({
    x: p.x,
    y: p.y,
    z: p.z
  }));
  console.log('Selected:', selected);
});
```

### 导出

```typescript
// 导出为图片
api.visualization.exportChart('heatmap-1', 'png', {
  width: 1920,
  height: 1080
});

// 导出为SVG
api.visualization.exportChart('contour-1', 'svg');

// 导出数据
const data = api.visualization.getChartData('surface-1');
api.data.export(data, 'json');
```

---

## 📈 性能优化

### 数据量建议

| 图表类型 | 推荐数据点 | 最大数据点 |
|----------|------------|------------|
| 热力图   | 50×50      | 200×200    |
| 等值线图 | 100×100    | 500×500    |
| 3D表面图 | 50×50      | 100×100    |

### 优化技巧

1. **数据采样**:
```typescript
function downsample(data: number[], factor: number): number[] {
  return data.filter((_, i) => i % factor === 0);
}
```

2. **渐进式渲染**:
```typescript
// 先显示低分辨率
api.visualization.createChart('heatmap', lowResData);

// 后台加载高分辨率
setTimeout(() => {
  api.visualization.updateChart('heatmap-1', highResData);
}, 100);
```

3. **缓存计算**:
```typescript
const cache = new Map();
function getInterpolated(x: number, y: number): number {
  const key = `${x},${y}`;
  if (!cache.has(key)) {
    cache.set(key, interpolate(x, y));
  }
  return cache.get(key);
}
```

---

## 🐛 常见问题

### Q1: 热力图显示不正常？

**A**:
- 检查Z值是否为二维数组
- 确认X和Y的长度与Z的维度匹配
- 查看是否有NaN或Infinity

### Q2: 3D图旋转卡顿？

**A**:
- 减少数据点数量
- 使用数据采样
- 关闭实时渲染

### Q3: 等值线不平滑？

**A**:
- 增加数据点密度
- 使用插值
- 调整contour size

---

## 📚 示例

### 示例1: 水深时空分布

```typescript
// 获取仿真结果
const result = await api.simulation.getResult('job-123');

// 准备数据
const data = {
  x: result.positions,
  y: result.times,
  z: result.depth2d,
  colorscale: 'Viridis',
  title: '水深时空分布'
};

// 创建热力图
api.visualization.createChart('heatmap', data);
```

### 示例2: 流速矢量场

```typescript
const vectors = result.velocities.map((v, i) => ({
  x: result.positions[i],
  y: 0,
  u: v,
  v: 0
}));

api.visualization.createChart('vectorfield', {
  vectors,
  title: '流速矢量场'
});
```

---

## 🔜 未来改进

- [ ] 更多图表类型（散点图、箱线图）
- [ ] WebGL加速渲染
- [ ] VR/AR支持
- [ ] 实时数据流
- [ ] 协同标注

---

## 📄 许可证

MIT License

---

<p align="center">
  <b>自定义可视化插件 - 让数据更直观</b>
</p>
