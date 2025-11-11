# 性能测试指南
# Performance Testing Guide

**版本**: v1.4.1
**日期**: 2025-11-11

---

## 📋 概述

本指南介绍如何测试 HydroClaude Web 前端的性能，包括：
- 自动化基准测试
- 手动性能分析
- 性能指标解读
- 优化建议

---

## 🚀 快速开始

### 运行自动化基准测试

```bash
# 进入前端目录
cd web/frontend

# 运行基准测试（如果已配置）
npm run benchmark

# 或使用 Vitest bench mode
npx vitest bench src/benchmarks/
```

### 浏览器手动测试

1. 启动开发服务器:
   ```bash
   npm run dev
   ```

2. 打开 Chrome 浏览器访问 http://localhost:5173

3. 打开 Chrome DevTools (F12)

4. 切换到 **Performance** 标签页

5. 点击 **Record** 按钮

6. 在应用中执行操作:
   - 切换标签页
   - 运行仿真
   - 播放动画
   - 交互3D图表

7. 停止录制

8. 分析结果

---

## 📊 性能测试场景

### 场景1: 小数据集 (Small Dataset)

**配置**:
- 网格点数: 50
- 时间步数: 20

**预期性能**:
- 首次渲染: < 500ms
- 动画帧率: 30 FPS
- 内存占用: < 100MB

**测试步骤**:
1. 创建小规模模型 (50点)
2. 运行仿真
3. 打开仿真结果
4. 播放动画
5. 检查性能指标

---

### 场景2: 中等数据集 (Medium Dataset)

**配置**:
- 网格点数: 200
- 时间步数: 100

**预期性能**:
- 首次渲染: < 2s
- 动画帧率: 20-30 FPS
- 内存占用: < 300MB

**测试步骤**:
1. 创建中等规模模型 (200点)
2. 运行仿真
3. 打开3D可视化
4. 旋转、缩放3D图表
5. 检查性能指标

---

### 场景3: 大数据集 (Large Dataset)

**配置**:
- 网格点数: 500
- 时间步数: 200

**预期性能**:
- 首次渲染: < 5s
- 动画帧率: 10-20 FPS
- 内存占用: < 500MB

**测试步骤**:
1. 创建大规模模型 (500点)
2. 运行仿真
3. 打开增强图表
4. 切换不同图表类型
5. 检查性能指标

---

## 📈 关键性能指标 (KPIs)

### 1. 加载性能

| 指标 | 目标 | 说明 |
|------|------|------|
| **FCP** (First Contentful Paint) | < 1.5s | 首次内容绘制 |
| **LCP** (Largest Contentful Paint) | < 2.5s | 最大内容绘制 |
| **TTI** (Time to Interactive) | < 3.5s | 可交互时间 |
| **TBT** (Total Blocking Time) | < 300ms | 总阻塞时间 |

### 2. 运行时性能

| 指标 | 目标 | 说明 |
|------|------|------|
| **FPS** (Frames Per Second) | > 30 | 动画流畅度 |
| **Input Latency** | < 100ms | 输入响应时间 |
| **Re-render Time** | < 16ms | 重渲染时间（60 FPS） |

### 3. 资源使用

| 指标 | 目标 | 说明 |
|------|------|------|
| **JS Heap Size** | < 50MB | JavaScript内存 |
| **Total Memory** | < 500MB | 总内存占用 |
| **Network Transferred** | < 2MB | 网络传输（gzipped） |

---

## 🔍 Chrome DevTools 性能分析

### 1. Performance Timeline

**查看内容**:
- Scripting (脚本执行时间) - 应该<50%
- Rendering (渲染时间) - 应该<30%
- Painting (绘制时间) - 应该<20%
- System (系统开销) - 通常占小部分

**优化目标**:
- 减少 Scripting 时间 → 优化 JavaScript
- 减少 Rendering 时间 → 优化 DOM 操作
- 减少 Layout Shift → 固定元素尺寸

### 2. Memory Profiler

**查看内容**:
- Heap Snapshot (堆快照)
- Timeline (内存时间线)
- Allocation Timeline (分配时间线)

**关注点**:
- 内存泄漏检测
- 大对象识别
- 垃圾回收频率

### 3. Network Panel

**查看内容**:
- Chunk加载顺序
- 缓存命中率
- 传输大小

**优化检查**:
- ✓ vendor-plotly 仅在需要时加载
- ✓ 图表组件懒加载
- ✓ 浏览器缓存有效

---

## 🛠️ 性能优化清单

### ✅ 已实现

- [x] **代码分割** - React.lazy() for workspaces
- [x] **Manual Chunks** - 7个独立vendor chunks
- [x] **React.memo()** - Plot3D, EnhancedCharts, AnimationController
- [x] **useMemo()** - 昂贵的计算结果缓存
- [x] **Lazy Loading** - 工作区组件按需加载
- [x] **Terser Minification** - 生产环境代码压缩
- [x] **Tree Shaking** - 移除未使用代码

### 🔜 待实现

- [ ] **Virtual Scrolling** - react-window for large lists
- [ ] **Web Workers** - 后台计算密集任务
- [ ] **Service Worker** - 离线缓存和预加载
- [ ] **Image Optimization** - 图片懒加载和压缩
- [ ] **CDN Deployment** - 静态资源CDN加速

---

## 📝 性能测试报告模板

```markdown
## 性能测试报告

**测试日期**: YYYY-MM-DD
**测试人员**: __________
**浏览器**: Chrome ___ / Firefox ___ / Safari ___
**设备**: _____________

### 测试结果

#### 场景1: 小数据集 (50点 × 20步)
- 首次渲染: _____ ms
- 动画帧率: _____ FPS
- 内存占用: _____ MB
- 评价: □优秀 □良好 □一般 □需改进

#### 场景2: 中等数据集 (200点 × 100步)
- 首次渲染: _____ ms
- 动画帧率: _____ FPS
- 内存占用: _____ MB
- 评价: □优秀 □良好 □一般 □需改进

#### 场景3: 大数据集 (500点 × 200步)
- 首次渲染: _____ ms
- 动画帧率: _____ FPS
- 内存占用: _____ MB
- 评价: □优秀 □良好 □一般 □需改进

### 发现的问题
1. _________________________________
2. _________________________________
3. _________________________________

### 优化建议
1. _________________________________
2. _________________________________
3. _________________________________

### 总体评价
□优秀 □良好 □一般 □需改进

备注:
_____________________________________
_____________________________________
```

---

## 🔬 高级性能测试

### Lighthouse CI

```bash
# 安装 Lighthouse
npm install -g @lhci/cli

# 运行 Lighthouse
lhci autorun --collect.url=http://localhost:5173
```

**性能预算**:
```json
{
  "performance": 90,
  "accessibility": 95,
  "best-practices": 90,
  "seo": 80,
  "first-contentful-paint": 1500,
  "largest-contentful-paint": 2500,
  "total-blocking-time": 300
}
```

### React DevTools Profiler

1. 安装 React DevTools 浏览器扩展
2. 打开 Profiler 标签页
3. 点击 Record 按钮
4. 执行操作
5. 停止录制
6. 分析组件渲染时间:
   - 查找最慢的组件
   - 检查不必要的重渲染
   - 验证memo()效果

### Bundle Analyzer

```bash
# 安装分析工具
npm install -D vite-bundle-visualizer

# 构建并分析
npm run build
npx vite-bundle-visualizer
```

**分析重点**:
- 最大的chunks
- 重复的依赖
- 未使用的代码

---

## 💡 性能优化建议

### 1. React组件优化

```typescript
// ✅ 好的做法
const MyComponent = memo(({ data }) => {
  const result = useMemo(() => expensiveComputation(data), [data]);
  const handleClick = useCallback(() => { /* ... */ }, []);
  return <div>{result}</div>;
});

// ❌ 避免的做法
const MyComponent = ({ data }) => {
  const result = expensiveComputation(data); // 每次都重新计算
  const handleClick = () => { /* ... */ }; // 每次都创建新函数
  return <div>{result}</div>;
};
```

### 2. Plotly图表优化

```typescript
// ✅ 使用useMemo缓存plot配置
const plotData = useMemo(() => ({
  data: [{ x, y, type: 'scatter' }],
  layout: { title: 'My Plot' }
}), [x, y]);

<Plot {...plotData} />

// ❌ 每次都创建新对象
<Plot
  data={[{ x, y, type: 'scatter' }]}
  layout={{ title: 'My Plot' }}
/>
```

### 3. 大数据集处理

```typescript
// ✅ 使用虚拟化
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={1000}
  itemSize={35}
>
  {Row}
</FixedSizeList>

// ❌ 直接渲染大列表
{items.map(item => <Row key={item.id} {...item} />)}
```

---

## 📚 参考资源

### 工具
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)
- [React DevTools Profiler](https://react.dev/reference/react/Profiler)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [Web Vitals](https://web.dev/vitals/)
- [Vite Bundle Analyzer](https://github.com/btd/rollup-plugin-visualizer)

### 最佳实践
- [React Performance Optimization](https://react.dev/reference/react/memo)
- [Web Performance Best Practices](https://web.dev/fast/)
- [JavaScript Performance](https://developer.mozilla.org/en-US/docs/Web/Performance)

### 项目文档
- `NEXT_STEPS.md` - 后续优化计划
- `OPTIMIZATION_COMPLETE.md` - 已完成的优化
- `SESSION_2025_11_11_PERFORMANCE_OPTIMIZATION.md` - 详细技术文档

---

**最后更新**: 2025-11-11
**维护者**: HydroClaude Development Team
