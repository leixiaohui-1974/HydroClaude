# 插件开发FAQ

**版本**: 1.0.0  
**更新**: 2025-11-15

---

## 📖 概述

本文档收集了插件开发过程中的常见问题和解决方案。

---

## 🚀 入门问题

### Q1: 如何开始开发插件？

**A**: 遵循以下步骤：

1. 阅读[快速入门指南](./getting-started.md)
2. 克隆插件模板
3. 查看[示例插件](../../plugins/examples/)
4. 参考[API文档](./api-reference.md)

---

### Q2: 需要什么开发技能？

**A**: 基础要求：
- ✅ JavaScript/TypeScript
- ✅ Node.js和npm
- ✅ 异步编程

可选技能：
- React（如果需要UI组件）
- Git版本控制
- 测试（Jest）

---

### Q3: 插件开发需要多长时间？

**A**: 取决于复杂度：
- **简单插件** (Hello World): 30分钟
- **实用插件** (数据导入): 2-4小时
- **复杂插件** (参数优化): 1-3天
- **高级插件** (GIS集成): 1-2周

---

## 🔧 技术问题

### Q4: 如何调试插件？

**A**: 多种调试方法：

**方法1: Console输出**
```typescript
api.utils.log('调试信息:', value);
api.utils.warn('警告:', warning);
api.utils.error('错误:', error);
```

**方法2: 浏览器开发者工具**
- 按F12打开
- 查看Console标签
- 使用断点

**方法3: VS Code调试**
```json
// .vscode/launch.json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Plugin",
  "program": "${workspaceFolder}/dist/index.js"
}
```

---

### Q5: 为什么插件加载失败？

**A**: 常见原因：

1. **清单文件错误**
```bash
# 检查plugin.json格式
npx jsonlint plugin.json
```

2. **权限不足**
```json
// 添加缺失的权限
{
  "permissions": ["simulation:read"]
}
```

3. **入口文件路径错误**
```json
{
  "main": "dist/index.js"  // 确保路径正确
}
```

4. **未编译TypeScript**
```bash
npm run build
```

---

### Q6: 如何处理异步操作？

**A**: 使用async/await：

**❌ 错误**:
```typescript
function loadData() {
  api.data.read('file.json').then(data => {
    this.data = data;
  });
  return this.data;  // undefined!
}
```

**✅ 正确**:
```typescript
async function loadData() {
  this.data = await api.data.read('file.json');
  return this.data;
}
```

---

### Q7: 插件间如何通信？

**A**: 使用Events API：

**插件A（发送方）**:
```typescript
api.events.emit('data-updated', { data: newData });
```

**插件B（接收方）**:
```typescript
api.events.on('data-updated', (payload) => {
  console.log('收到数据:', payload.data);
});
```

---

### Q8: 如何保存插件状态？

**A**: 使用Storage API：

```typescript
class MyPlugin {
  async onActivate(api: PluginAPI) {
    // 加载状态
    const state = await api.storage.get('plugin-state') || {
      count: 0,
      history: [],
    };
    
    this.state = state;
  }

  async onDeactivate() {
    // 保存状态
    await api.storage.set('plugin-state', this.state);
  }
}
```

---

## 🎨 UI问题

### Q9: 如何添加工具栏按钮？

**A**: 使用UI API：

```typescript
api.ui.addButton({
  id: 'my-button',
  label: '我的按钮',
  icon: 'star',
  position: 'toolbar',
  onClick: () => {
    console.log('按钮被点击');
  },
});
```

---

### Q10: 如何显示通知？

**A**: 使用showNotification：

```typescript
// 成功通知
api.ui.showNotification({
  type: 'success',
  message: '操作成功！',
  duration: 3000,
});

// 错误通知
api.ui.showNotification({
  type: 'error',
  message: '操作失败',
});
```

---

### Q11: 如何创建对话框？

**A**: 使用showDialog：

```typescript
api.ui.showDialog({
  title: '确认操作',
  content: '确定要继续吗？',
  onOk: () => {
    // 用户点击确定
    performAction();
  },
  onCancel: () => {
    // 用户点击取消
  },
});
```

---

## 📊 数据处理

### Q12: 如何导入Excel文件？

**A**: 注册导入器：

```typescript
api.data.registerImporter({
  formats: ['xlsx', 'xls'],
  handler: async (file) => {
    // 使用xlsx库解析
    const workbook = XLSX.read(await file.arrayBuffer());
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    return XLSX.utils.sheet_to_json(sheet);
  },
});
```

---

### Q13: 如何导出CSV？

**A**: 使用Data API：

```typescript
const data = [
  { x: 0, y: 1 },
  { x: 1, y: 2 },
];

const blob = await api.data.export(data, 'csv');
api.utils.downloadFile(blob, 'result.csv');
```

---

## 🔍 仿真相关

### Q14: 如何运行仿真？

**A**: 使用Simulation API：

```typescript
try {
  const result = await api.simulation.run({
    roughness: 0.025,
    slope: 0.001,
    duration: 3600,
  });
  
  console.log('仿真结果:', result);
} catch (error) {
  api.utils.error('仿真失败:', error);
}
```

---

### Q15: 如何监听仿真进度？

**A**: 使用事件监听：

```typescript
api.simulation.onProgress((progress) => {
  console.log('进度:', (progress * 100).toFixed(1) + '%');
  
  api.ui.showNotification({
    type: 'info',
    message: `进度: ${(progress * 100).toFixed(0)}%`,
  });
});
```

---

### Q16: 如何获取仿真结果？

**A**: 两种方式：

**方式1: 直接从run()返回**
```typescript
const result = await api.simulation.run(config);
console.log(result.depth, result.velocity);
```

**方式2: 通过jobId获取**
```typescript
const result = await api.simulation.getResult('job-123');
```

---

## 🎯 高级问题

### Q17: 如何实现参数优化？

**A**: 参考示例插件：

```typescript
// 1. 定义目标函数
function objectiveFunction(params: number[]): number {
  // 运行仿真
  const result = runSimulation(params);
  // 计算误差
  return calculateError(result, target);
}

// 2. 实现优化算法（如遗传算法）
async function optimize() {
  let population = initializePopulation();
  
  for (let gen = 0; gen < maxGenerations; gen++) {
    population = await evaluateFitness(population);
    population = evolve(population);
  }
  
  return getBest(population);
}
```

完整示例: [参数优化插件](../../plugins/examples/parameter-optimization/)

---

### Q18: 如何创建自定义图表？

**A**: 注册图表类型：

```typescript
api.visualization.registerChart({
  type: 'my-chart',
  component: MyChartComponent,
  icon: 'chart',
  title: '我的图表',
});

// 使用
api.visualization.createChart('my-chart', {
  data: chartData,
});
```

完整示例: [自定义可视化插件](../../plugins/examples/custom-visualization/)

---

### Q19: 如何处理大数据？

**A**: 使用分批处理：

```typescript
async function processLargeData(data: number[]) {
  const batchSize = 1000;
  const results = [];
  
  for (let i = 0; i < data.length; i += batchSize) {
    const batch = data.slice(i, i + batchSize);
    const processed = await processBatch(batch);
    results.push(...processed);
    
    // 让出控制权，避免阻塞
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  
  return results;
}
```

---

### Q20: 如何优化插件性能？

**A**: 多种优化策略：

1. **缓存计算结果**
```typescript
const cache = new Map();
function calculate(x: number): number {
  if (cache.has(x)) return cache.get(x);
  const result = expensiveCalculation(x);
  cache.set(x, result);
  return result;
}
```

2. **使用Web Worker**
```typescript
const worker = new Worker('worker.js');
worker.postMessage({ data: largeData });
worker.onmessage = (e) => {
  console.log('结果:', e.data);
};
```

3. **防抖和节流**
```typescript
const handleInput = debounce((value) => {
  processInput(value);
}, 300);
```

---

## 🐛 错误处理

### Q21: 常见错误及解决方法

#### 错误1: "Permission denied"

**原因**: 权限不足

**解决**: 在plugin.json中添加权限
```json
{
  "permissions": ["simulation:read"]
}
```

---

#### 错误2: "Module not found"

**原因**: 依赖未安装

**解决**:
```bash
npm install
```

---

#### 错误3: "Cannot read property of undefined"

**原因**: 访问了不存在的属性

**解决**: 使用可选链和空值合并
```typescript
// ❌ 错误
const value = data.result.value;

// ✅ 正确
const value = data?.result?.value ?? defaultValue;
```

---

#### 错误4: "Failed to activate plugin"

**原因**: onActivate()抛出异常

**解决**: 添加错误处理
```typescript
async onActivate(api: PluginAPI) {
  try {
    // 插件初始化代码
    await initialize();
  } catch (error) {
    api.utils.error('激活失败:', error);
    throw error;
  }
}
```

---

## 📦 发布问题

### Q22: 如何发布插件？

**A**: 发布步骤：

1. **完成开发和测试**
```bash
npm test
npm run build
```

2. **更新版本**
```bash
npm version patch  # 或 minor, major
```

3. **编写文档**
- README.md
- CHANGELOG.md
- LICENSE

4. **发布到市场**
```bash
hydroclaude-cli publish
```

---

### Q23: 如何更新已发布的插件？

**A**: 更新流程：

1. 修改代码
2. 更新版本号
3. 更新CHANGELOG
4. 重新发布

```bash
npm version patch
npm run build
hydroclaude-cli publish
```

---

## 💡 最佳实践

### Q24: 插件开发有哪些注意事项？

**A**: 关键要点：

1. **✅ 单一职责** - 一个插件做一件事
2. **✅ 最小权限** - 只请求必需的权限
3. **✅ 错误处理** - 全面的try-catch
4. **✅ 资源清理** - onDeactivate()清理资源
5. **✅ 类型安全** - 使用TypeScript
6. **✅ 文档完善** - 编写清晰的文档
7. **✅ 版本管理** - 遵循语义化版本

---

### Q25: 如何学习插件开发？

**A**: 学习路径：

1. **阅读文档**
   - [快速入门](./getting-started.md)
   - [API参考](./api-reference.md)
   - [最佳实践](./best-practices.md)

2. **学习示例**
   - [参数优化](../../plugins/examples/parameter-optimization/)
   - [数据导入](../../plugins/examples/data-import/)
   - [自定义可视化](../../plugins/examples/custom-visualization/)

3. **实践练习**
   - 创建Hello World插件
   - 实现简单功能
   - 逐步增加复杂度

4. **社区交流**
   - 论坛: https://forum.hydroclaude.com
   - Discord: https://discord.gg/hydroclaude
   - GitHub: https://github.com/hydroclaude/hydroclaude

---

## 🔗 相关资源

- **文档首页**: https://docs.hydroclaude.com
- **插件模板**: https://github.com/hydroclaude/plugin-template
- **示例插件**: [examples/](../../plugins/examples/)
- **API参考**: [api-reference.md](./api-reference.md)
- **最佳实践**: [best-practices.md](./best-practices.md)

---

## 📮 获取帮助

如果你的问题在这里找不到答案：

1. **搜索文档**: https://docs.hydroclaude.com
2. **查看Issue**: https://github.com/hydroclaude/hydroclaude/issues
3. **提问论坛**: https://forum.hydroclaude.com
4. **Discord**: https://discord.gg/hydroclaude

---

<p align="center">
  <b>还有问题？欢迎在论坛提问！</b>
</p>
