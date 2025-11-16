# 插件API完整参考

**版本**: 2.0.0  
**更新**: 2025-11-15

---

## 📖 概述

HydroClaude插件系统提供8个标准API，涵盖仿真、可视化、数据处理、UI交互等各个方面。

### API列表

1. [Simulation API](#simulation-api) - 仿真控制
2. [Visualization API](#visualization-api) - 可视化扩展
3. [Data API](#data-api) - 数据处理
4. [UI API](#ui-api) - 用户界面
5. [Utils API](#utils-api) - 工具函数
6. [Storage API](#storage-api) - 数据存储
7. [Events API](#events-api) - 事件通信
8. [Commands API](#commands-api) - 命令系统

---

## Simulation API

控制和监控仿真过程。

### getConfig()

获取当前仿真配置。

**签名**:
```typescript
getConfig(): Promise<SimulationConfig>
```

**返回**: 仿真配置对象

**示例**:
```typescript
const config = await api.simulation.getConfig();
console.log('当前糙率:', config.roughness);
console.log('坡度:', config.slope);
```

---

### updateConfig(config)

更新仿真配置。

**签名**:
```typescript
updateConfig(config: Partial<SimulationConfig>): Promise<void>
```

**参数**:
- `config`: 要更新的配置（部分）

**示例**:
```typescript
await api.simulation.updateConfig({
  roughness: 0.030,
  slope: 0.002,
});

api.ui.showNotification({
  type: 'success',
  message: '配置已更新',
});
```

---

### run(config?)

运行仿真。

**签名**:
```typescript
run(config?: SimulationConfig): Promise<SimulationResult>
```

**参数**:
- `config`: 可选的仿真配置

**返回**: 仿真结果

**示例**:
```typescript
try {
  const result = await api.simulation.run({
    roughness: 0.025,
    slope: 0.001,
    duration: 3600,
  });
  
  console.log('仿真完成:', result);
} catch (error) {
  api.utils.error('仿真失败:', error);
}
```

---

### stop()

停止正在运行的仿真。

**签名**:
```typescript
stop(): Promise<void>
```

**示例**:
```typescript
await api.simulation.stop();
api.ui.showNotification({
  type: 'info',
  message: '仿真已停止',
});
```

---

### getResult(jobId)

获取仿真结果。

**签名**:
```typescript
getResult(jobId: string): Promise<SimulationResult>
```

**参数**:
- `jobId`: 任务ID

**返回**: 仿真结果

**示例**:
```typescript
const result = await api.simulation.getResult('job-123');
console.log('水深:', result.depth);
console.log('流速:', result.velocity);
```

---

### 事件监听

#### onStart(callback)

监听仿真开始事件。

```typescript
api.simulation.onStart((jobId) => {
  console.log('仿真开始:', jobId);
});
```

#### onProgress(callback)

监听仿真进度。

```typescript
api.simulation.onProgress((progress) => {
  console.log('进度:', progress * 100 + '%');
});
```

#### onComplete(callback)

监听仿真完成。

```typescript
api.simulation.onComplete((result) => {
  console.log('仿真完成:', result);
});
```

#### onError(callback)

监听仿真错误。

```typescript
api.simulation.onError((error) => {
  api.utils.error('仿真错误:', error);
});
```

---

## Visualization API

扩展和自定义可视化功能。

### registerChart(config)

注册自定义图表类型。

**签名**:
```typescript
registerChart(config: {
  type: string;
  component: React.ComponentType<any>;
  icon?: string;
  title?: string;
}): void
```

**参数**:
- `type`: 图表类型标识
- `component`: React组件
- `icon`: 图标（可选）
- `title`: 标题（可选）

**示例**:
```typescript
api.visualization.registerChart({
  type: 'my-chart',
  component: MyChartComponent,
  icon: 'chart-line',
  title: '我的图表',
});
```

---

### createChart(type, data, options?)

创建图表实例。

**签名**:
```typescript
createChart(type: string, data: any, options?: any): void
```

**参数**:
- `type`: 图表类型
- `data`: 图表数据
- `options`: 可选配置

**示例**:
```typescript
api.visualization.createChart('heatmap', {
  x: [0, 100, 200],
  y: [0, 10, 20],
  z: [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
  colorscale: 'Viridis',
});
```

---

### updateChart(id, data)

更新已有图表。

**签名**:
```typescript
updateChart(id: string, data: any): void
```

**示例**:
```typescript
api.visualization.updateChart('chart-1', {
  z: [[2, 3, 4], [5, 6, 7], [8, 9, 10]],
});
```

---

### removeChart(id)

删除图表。

**签名**:
```typescript
removeChart(id: string): void
```

**示例**:
```typescript
api.visualization.removeChart('chart-1');
```

---

## Data API

数据导入、导出和处理。

### read(path)

读取数据文件。

**签名**:
```typescript
read(path: string): Promise<any>
```

**参数**:
- `path`: 文件路径

**返回**: 文件内容

**示例**:
```typescript
const data = await api.data.read('/path/to/data.json');
console.log(data);
```

---

### write(path, data)

写入数据文件。

**签名**:
```typescript
write(path: string, data: any): Promise<void>
```

**参数**:
- `path`: 文件路径
- `data`: 要写入的数据

**示例**:
```typescript
await api.data.write('/path/to/output.json', {
  result: 'success',
  value: 123,
});
```

---

### import(file, format)

导入数据文件。

**签名**:
```typescript
import(file: File, format: string): Promise<any>
```

**参数**:
- `file`: 文件对象
- `format`: 文件格式（xlsx, csv, json等）

**返回**: 解析后的数据

**示例**:
```typescript
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];

const data = await api.data.import(file, 'xlsx');
console.log('导入数据:', data);
```

---

### export(data, format)

导出数据。

**签名**:
```typescript
export(data: any, format: string): Promise<Blob>
```

**参数**:
- `data`: 要导出的数据
- `format`: 导出格式

**返回**: Blob对象

**示例**:
```typescript
const blob = await api.data.export(result, 'csv');
api.utils.downloadFile(blob, 'result.csv');
```

---

### registerImporter(config)

注册自定义数据导入器。

**签名**:
```typescript
registerImporter(config: {
  formats: string[];
  handler: (file: File) => Promise<any>;
}): void
```

**示例**:
```typescript
api.data.registerImporter({
  formats: ['txt', 'dat'],
  handler: async (file) => {
    const text = await file.text();
    return parseCustomFormat(text);
  },
});
```

---

### registerExporter(config)

注册自定义数据导出器。

**签名**:
```typescript
registerExporter(config: {
  format: string;
  handler: (data: any) => Promise<Blob>;
}): void
```

**示例**:
```typescript
api.data.registerExporter({
  format: 'custom',
  handler: async (data) => {
    const text = formatCustom(data);
    return new Blob([text], { type: 'text/plain' });
  },
});
```

---

## UI API

用户界面集成和交互。

### addButton(config)

添加工具栏按钮。

**签名**:
```typescript
addButton(config: {
  id: string;
  label: string;
  icon?: string;
  position: 'toolbar' | 'sidebar';
  onClick: () => void;
}): void
```

**示例**:
```typescript
api.ui.addButton({
  id: 'my-button',
  label: '点击我',
  icon: 'star',
  position: 'toolbar',
  onClick: () => {
    console.log('按钮被点击');
  },
});
```

---

### addPanel(config)

添加侧边面板。

**签名**:
```typescript
addPanel(config: {
  id: string;
  title: string;
  component: React.ComponentType;
  position: 'left' | 'right' | 'bottom';
}): void
```

**示例**:
```typescript
api.ui.addPanel({
  id: 'my-panel',
  title: '我的面板',
  component: MyPanelComponent,
  position: 'right',
});
```

---

### showNotification(config)

显示通知消息。

**签名**:
```typescript
showNotification(config: {
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  duration?: number;
}): void
```

**示例**:
```typescript
api.ui.showNotification({
  type: 'success',
  message: '操作成功！',
  duration: 3000,
});
```

---

### showDialog(config)

显示对话框。

**签名**:
```typescript
showDialog(config: {
  title: string;
  content: React.ReactNode;
  onOk?: () => void;
  onCancel?: () => void;
}): void
```

**示例**:
```typescript
api.ui.showDialog({
  title: '确认操作',
  content: '确定要继续吗？',
  onOk: () => {
    console.log('用户点击确定');
  },
  onCancel: () => {
    console.log('用户点击取消');
  },
});
```

---

## Utils API

实用工具函数。

### log(...args)

输出日志信息。

**签名**:
```typescript
log(...args: any[]): void
```

**示例**:
```typescript
api.utils.log('这是日志信息');
api.utils.log('多个参数:', value1, value2);
```

---

### warn(...args)

输出警告信息。

**签名**:
```typescript
warn(...args: any[]): void
```

**示例**:
```typescript
api.utils.warn('警告: 参数可能不正确');
```

---

### error(...args)

输出错误信息。

**签名**:
```typescript
error(...args: any[]): void
```

**示例**:
```typescript
api.utils.error('错误:', error.message);
```

---

### fetch

标准fetch API。

**签名**:
```typescript
fetch: typeof window.fetch
```

**示例**:
```typescript
const response = await api.utils.fetch('https://api.example.com/data');
const data = await response.json();
```

---

### readFile(file)

读取文件内容。

**签名**:
```typescript
readFile(file: File): Promise<string | ArrayBuffer>
```

**示例**:
```typescript
const content = await api.utils.readFile(file);
console.log(content);
```

---

### downloadFile(blob, filename)

下载文件。

**签名**:
```typescript
downloadFile(blob: Blob, filename: string): void
```

**示例**:
```typescript
const blob = new Blob(['Hello World'], { type: 'text/plain' });
api.utils.downloadFile(blob, 'hello.txt');
```

---

## Storage API

持久化数据存储。

### get(key)

获取存储的数据。

**签名**:
```typescript
get(key: string): Promise<any>
```

**示例**:
```typescript
const value = await api.storage.get('my-key');
console.log(value);
```

---

### set(key, value)

存储数据。

**签名**:
```typescript
set(key: string, value: any): Promise<void>
```

**示例**:
```typescript
await api.storage.set('my-key', { count: 42 });
```

---

### remove(key)

删除数据。

**签名**:
```typescript
remove(key: string): Promise<void>
```

**示例**:
```typescript
await api.storage.remove('my-key');
```

---

### clear()

清空所有数据。

**签名**:
```typescript
clear(): Promise<void>
```

**示例**:
```typescript
await api.storage.clear();
```

---

### keys()

获取所有键。

**签名**:
```typescript
keys(): Promise<string[]>
```

**示例**:
```typescript
const keys = await api.storage.keys();
console.log('所有键:', keys);
```

---

## Events API

事件发布订阅系统。

### on(event, callback)

订阅事件。

**签名**:
```typescript
on(event: string, callback: (...args: any[]) => void): void
```

**示例**:
```typescript
api.events.on('simulation:complete', (result) => {
  console.log('仿真完成:', result);
});
```

---

### off(event, callback)

取消订阅。

**签名**:
```typescript
off(event: string, callback: (...args: any[]) => void): void
```

**示例**:
```typescript
const handler = (result) => console.log(result);
api.events.on('simulation:complete', handler);
// 稍后取消
api.events.off('simulation:complete', handler);
```

---

### emit(event, ...args)

发布事件。

**签名**:
```typescript
emit(event: string, ...args: any[]): void
```

**示例**:
```typescript
api.events.emit('my-event', { data: 'hello' });
```

---

### once(event, callback)

一次性订阅。

**签名**:
```typescript
once(event: string, callback: (...args: any[]) => void): void
```

**示例**:
```typescript
api.events.once('simulation:complete', (result) => {
  console.log('只触发一次');
});
```

---

## Commands API

命令注册和执行。

### register(id, handler)

注册命令。

**签名**:
```typescript
register(id: string, handler: (...args: any[]) => any): void
```

**示例**:
```typescript
api.commands.register('my-command', (arg1, arg2) => {
  console.log('执行命令:', arg1, arg2);
  return 'result';
});
```

---

### execute(id, ...args)

执行命令。

**签名**:
```typescript
execute(id: string, ...args: any[]): Promise<any>
```

**示例**:
```typescript
const result = await api.commands.execute('my-command', 'hello', 'world');
console.log('命令结果:', result);
```

---

### unregister(id)

取消注册。

**签名**:
```typescript
unregister(id: string): void
```

**示例**:
```typescript
api.commands.unregister('my-command');
```

---

### getAll()

获取所有命令。

**签名**:
```typescript
getAll(): PluginCommand[]
```

**示例**:
```typescript
const commands = api.commands.getAll();
console.log('可用命令:', commands);
```

---

## 📚 最佳实践

### 错误处理

```typescript
try {
  const result = await api.simulation.run(config);
} catch (error) {
  api.utils.error('仿真失败:', error);
  api.ui.showNotification({
    type: 'error',
    message: '仿真失败: ' + error.message,
  });
}
```

### 资源清理

```typescript
async onDeactivate(): Promise<void> {
  // 取消事件订阅
  api.events.off('simulation:complete', this.handler);
  
  // 取消命令注册
  api.commands.unregister('my-command');
  
  // 保存数据
  await api.storage.set('state', this.state);
}
```

### 类型安全

```typescript
import type { PluginAPI, SimulationResult } from '@hydroclaude/types';

async function processResult(api: PluginAPI): Promise<void> {
  const result: SimulationResult = await api.simulation.getResult('job-1');
  console.log(result.depth);
}
```

---

<p align="center">
  <b>API参考完成</b>
</p>

<p align="center">
  下一步: [最佳实践](./best-practices.md)
</p>
