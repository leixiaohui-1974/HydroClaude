# 结果可视化组件

**Phase 5.1.4 完成**

---

## 📖 概述

结果可视化系统是HydroClaude Web应用的核心展示功能，提供了丰富的数据可视化和分析工具。

### 核心组件

1. **ResultsViewer** - 结果查看器容器
2. **WaterProfileChart** - 水位剖面图（Plotly）
3. **VelocityChart** - 流速分布图（Plotly）
4. **TimeSeriesChart** - 时间序列图（Plotly）
5. **ResultsTable** - 数据表格（Ant Design Table）
6. **AnimationPlayer** - 动画播放器（非恒定流）

---

## 🎯 功能特性

### 1. Plotly交互式图表

#### WaterProfileChart - 水位剖面图

**功能**:
- ✅ 水面线绘制
- ✅ 渠底高程显示
- ✅ 双Y轴（水深+流速）
- ✅ 交互式缩放/平移
- ✅ 悬停显示数据
- ✅ 图表导出（PNG, 高分辨率）

**用法**:
```typescript
<WaterProfileChart
  data={{
    positions: [0, 100, 200, ...],
    depths: [3.1, 3.0, 2.9, ...],
    velocities: [1.5, 1.6, 1.7, ...],
    water_surface: [103.1, 103.0, 102.9, ...],
    bottom_elevation: [100, 100, 100, ...],
  }}
  showVelocity={true}
  height={500}
/>
```

#### VelocityChart - 流速分布图

**功能**:
- ✅ 流速曲线
- ✅ Froude数曲线
- ✅ 临界流线（Fr=1）
- ✅ 双Y轴显示
- ✅ 流态自动判断

**用法**:
```typescript
<VelocityChart
  data={{
    positions: [0, 100, 200, ...],
    velocities: [1.5, 1.6, 1.7, ...],
    froude_numbers: [0.8, 0.85, 0.9, ...],
  }}
  showFroude={true}
  height={400}
/>
```

#### TimeSeriesChart - 时间序列图

**功能**:
- ✅ 多位置监测曲线
- ✅ 时间轴展示
- ✅ 图例可切换
- ✅ 数据悬停显示

**用法**:
```typescript
<TimeSeriesChart
  data={{
    times: [0, 1, 2, 3, ...],
    values: [
      [3.1, 3.2, 3.3, ...], // 位置1
      [3.0, 3.1, 3.2, ...], // 位置2
    ],
    positions: [0, 500],
    variable_name: '水深 (m)',
  }}
  height={400}
/>
```

---

### 2. 数据表格

#### ResultsTable

**功能**:
- ✅ 分页展示
- ✅ 排序功能
- ✅ 搜索筛选
- ✅ 导出CSV
- ✅ 导出JSON
- ✅ 可调整每页数量

**列定义**:
- 位置 (m)
- 水深 (m)
- 流速 (m/s)
- Froude数
- 流量 (m³/s)

**用法**:
```typescript
<ResultsTable
  data={{
    positions: [0, 10, 20, ...],
    depths: [3.1, 3.0, 2.9, ...],
    velocities: [1.5, 1.6, 1.7, ...],
    froude_numbers: [0.8, 0.85, 0.9, ...],
    discharge: [46.5, 48.0, 49.3, ...],
  }}
/>
```

---

### 3. 动画播放器

#### AnimationPlayer

**功能**:
- ✅ 播放/暂停控制
- ✅ 单帧前进/后退
- ✅ 跳转到开始/结束
- ✅ 可调节播放速度（0.25x - 4x）
- ✅ 帧数输入跳转
- ✅ 进度条拖动

**控制器**:
```
[开始] [◀] [▶/⏸] [▶] [结束]
进度条: ━━━━●━━━━━━━
帧数: [50] / 100  速度: [1x ▼]
```

**用法**:
```typescript
<AnimationPlayer
  totalFrames={100}
  currentFrame={currentFrame}
  onFrameChange={setCurrentFrame}
  fps={10}
>
  {/* 在这里放置要动画的内容 */}
  <WaterProfileChart ... />
</AnimationPlayer>
```

---

### 4. 结果查看器

#### ResultsViewer

**功能**:
- ✅ 多标签页组织
- ✅ 工具栏（下载、导出、动画）
- ✅ 显示选项切换
- ✅ 自适应布局

**标签页**:
1. 水位剖面 - 空间分布
2. 流速分布 - 流速和Froude数
3. 时间序列 - 监测点时间变化（非恒定流）
4. 动画播放 - 动态演示（非恒定流）
5. 数据表格 - 原始数据

**用法**:
```typescript
<ResultsViewer
  results={{
    metadata: {
      simulation_type: 'steady',
      case_name: '渠道流动',
      timestamp: '2025-11-15T10:00:00',
    },
    spatial: {
      positions: [...],
      depths: [...],
      velocities: [...],
    },
    temporal: { // 非恒定流
      times: [...],
      depth_series: [...],
      velocity_series: [...],
    },
  }}
/>
```

---

## 🎨 可视化效果

### 水位剖面图示例

```
水位剖面图
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
高  │    ┌─────────────────────┐
程  │   ╱                       ╲  水面线
(m) │  ╱                         ╲
    │ ╱                           ╲
    │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 渠底
    └─────────────────────────────→
              距离 (m)
```

### 流速分布图示例

```
流速 / Froude数
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    │     ┌──┐     
流  │    ╱    ╲    流速曲线
速  │   ╱      ╲   
    │  ╱        ╲  
    │ ╱    ┄┄┄┄┄╲┄ Fr=1 (临界)
    │╱   ┆      ╲
    │  ┆  Froude数
    └─────────────────────────────→
              距离 (m)
```

---

## 🔧 技术实现

### Plotly配置

```typescript
// 图表配置
config={{
  responsive: true,          // 响应式
  displayModeBar: true,      // 显示工具栏
  displaylogo: false,        // 隐藏logo
  modeBarButtonsToRemove: [  // 移除不需要的按钮
    'pan2d', 
    'lasso2d', 
    'select2d'
  ],
  toImageButtonOptions: {    // 导出选项
    format: 'png',
    filename: 'chart',
    height: 800,
    width: 1200,
    scale: 2,                // 2x分辨率
  },
}}
```

### 双Y轴实现

```typescript
// 左Y轴（水深）
yaxis: {
  title: '水深 (m)',
},

// 右Y轴（流速）
yaxis2: {
  title: '流速 (m/s)',
  overlaying: 'y',
  side: 'right',
},

// 数据绑定到不同y轴
{
  y: depths,
  yaxis: 'y',   // 左轴
},
{
  y: velocities,
  yaxis: 'y2',  // 右轴
}
```

### CSV导出实现

```typescript
const exportToCSV = () => {
  const headers = ['位置(m)', '水深(m)', '流速(m/s)'];
  const csvContent = [
    headers.join(','),
    ...data.map(row => [
      row.position,
      row.depth,
      row.velocity,
    ].join(','))
  ].join('\n');

  const blob = new Blob(['\ufeff' + csvContent], { 
    type: 'text/csv;charset=utf-8;' 
  });
  // ... 下载逻辑
};
```

---

## 📊 数据格式

### 空间数据（Spatial）

```typescript
interface SpatialData {
  positions: number[];        // 位置数组 (m)
  depths: number[];          // 水深数组 (m)
  velocities: number[];      // 流速数组 (m/s)
  froude_numbers?: number[]; // Froude数（可选）
  discharge?: number[];      // 流量（可选）
  water_surface?: number[];  // 水面高程（可选）
  bottom_elevation?: number[]; // 底部高程（可选）
}
```

### 时间序列数据（Temporal）

```typescript
interface TemporalData {
  times: number[];              // 时间数组 (s)
  depth_series: number[][];     // 水深时间序列 [位置][时间]
  velocity_series: number[][]; // 流速时间序列 [位置][时间]
}
```

### 完整结果数据

```typescript
interface SimulationResults {
  metadata: {
    simulation_type: 'steady' | 'unsteady';
    case_name: string;
    timestamp: string;
    solver?: string;
    convergence?: {
      iterations: number;
      error: number;
    };
  };
  spatial: SpatialData;
  temporal?: TemporalData;
}
```

---

## 💡 使用示例

### 完整示例 - 稳态流

```typescript
import ResultsViewer from '@/components/ResultsViewer';

const SteadyFlowResults = () => {
  const results = {
    metadata: {
      simulation_type: 'steady',
      case_name: '渠道稳态流',
      timestamp: new Date().toISOString(),
      solver: 'hydrostatic',
      convergence: {
        iterations: 5,
        error: 0.000001,
      },
    },
    spatial: {
      positions: [0, 100, 200, 300, 400, 500],
      depths: [3.1, 3.0, 2.9, 2.85, 2.8, 2.75],
      velocities: [1.5, 1.6, 1.7, 1.75, 1.8, 1.85],
      froude_numbers: [0.85, 0.92, 0.99, 1.02, 1.08, 1.12],
    },
  };

  return <ResultsViewer results={results} />;
};
```

### 完整示例 - 非恒定流

```typescript
const UnsteadyFlowResults = () => {
  const results = {
    metadata: {
      simulation_type: 'unsteady',
      case_name: '溃坝波演进',
      timestamp: new Date().toISOString(),
    },
    spatial: {
      positions: [0, 100, 200, 300, 400, 500],
      depths: [3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
      velocities: [0, 0, 0, 0, 0, 0],
    },
    temporal: {
      times: [0, 1, 2, 3, 4, 5],
      depth_series: [
        [3.0, 3.1, 3.2, 3.15, 3.05, 3.0], // 位置0
        [3.0, 3.0, 3.1, 3.2, 3.15, 3.05], // 位置100
        // ...
      ],
      velocity_series: [
        [0, 0.5, 1.0, 0.8, 0.4, 0.1],
        [0, 0, 0.5, 1.0, 0.8, 0.4],
        // ...
      ],
    },
  };

  return <ResultsViewer results={results} />;
};
```

---

## 🎯 最佳实践

### 1. 性能优化

```typescript
// 使用useMemo缓存图表数据
const plotData = useMemo(() => {
  return generatePlotData(data);
}, [data]);

// 使用useMemo缓存布局配置
const layout = useMemo(() => ({
  title: 'Chart Title',
  // ...
}), [dependencies]);
```

### 2. 响应式设计

```typescript
// 图表自适应容器大小
<Plot
  data={plotData}
  layout={layout}
  config={{ responsive: true }}
  style={{ width: '100%', height }}
/>
```

### 3. 错误处理

```typescript
if (!data || !data.positions || data.positions.length === 0) {
  return (
    <Card>
      <Empty description="暂无数据" />
    </Card>
  );
}
```

### 4. 数据导出

```typescript
// CSV导出需要添加BOM以支持中文
const blob = new Blob(['\ufeff' + csvContent], { 
  type: 'text/csv;charset=utf-8;' 
});
```

---

## 🔧 扩展指南

### 添加新的图表类型

1. 创建新组件 `components/Charts/NewChart.tsx`
2. 实现Plotly图表逻辑
3. 在ResultsViewer中添加新标签页
4. 更新数据接口类型

### 添加新的导出格式

```typescript
const exportToExcel = () => {
  // 使用xlsx库
  import('xlsx').then(XLSX => {
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Results');
    XLSX.writeFile(wb, 'results.xlsx');
  });
};
```

---

## 📚 相关文档

- [Plotly.js文档](https://plotly.com/javascript/)
- [React Plotly文档](https://plotly.com/javascript/react/)
- [Ant Design Table](https://ant.design/components/table)

---

<p align="center">
  <b>结果可视化组件 - Phase 5.1.4 Complete</b>
</p>
