# 插件开发最佳实践

**版本**: 1.0.0  
**更新**: 2025-11-15

---

## 📖 概述

本文档总结了插件开发的最佳实践、设计模式和常见陷阱，帮助你开发高质量的插件。

---

## 🎯 设计原则

### 1. 单一职责原则

每个插件应该只做一件事，并把它做好。

**❌ 不好的做法**:
```typescript
// 一个插件做太多事情
class SuperPlugin {
  async onActivate(api: PluginAPI) {
    // 参数优化
    api.commands.register('optimize', ...);
    
    // 数据导入
    api.commands.register('import', ...);
    
    // 可视化
    api.commands.register('visualize', ...);
    
    // 报告生成
    api.commands.register('report', ...);
  }
}
```

**✅ 好的做法**:
```typescript
// 专注于一个功能
class ParameterOptimizationPlugin {
  async onActivate(api: PluginAPI) {
    // 只做参数优化
    api.commands.register('optimize', ...);
    api.commands.register('optimize:stop', ...);
    api.commands.register('optimize:history', ...);
  }
}
```

---

### 2. 最小权限原则

只请求插件真正需要的权限。

**❌ 不好的做法**:
```json
{
  "permissions": [
    "simulation:read",
    "simulation:write",
    "simulation:execute",
    "data:read",
    "data:write",
    "data:delete",
    "filesystem:read",
    "filesystem:write",
    "network:request"
  ]
}
```

**✅ 好的做法**:
```json
{
  "permissions": [
    "simulation:read",
    "ui:modify"
  ]
}
```

---

### 3. 向后兼容

设计时考虑未来的扩展，保持API的向后兼容性。

**✅ 好的做法**:
```typescript
// 使用可选参数
interface CalculateOptions {
  method?: 'fast' | 'accurate';  // 新增选项
  precision?: number;             // 新增选项
}

function calculate(params: Params, options?: CalculateOptions) {
  const { method = 'fast', precision = 0.01 } = options || {};
  // ...
}
```

---

## 💻 代码质量

### 1. TypeScript类型安全

充分利用TypeScript的类型系统。

**✅ 好的做法**:
```typescript
import type { Plugin, PluginAPI } from '@hydroclaude/types';

interface PluginState {
  isRunning: boolean;
  progress: number;
  results: Result[];
}

class MyPlugin implements Plugin {
  private state: PluginState = {
    isRunning: false,
    progress: 0,
    results: [],
  };

  async onActivate(api: PluginAPI): Promise<void> {
    // TypeScript会检查类型
  }
}
```

---

### 2. 错误处理

全面的错误处理和用户友好的错误消息。

**❌ 不好的做法**:
```typescript
async function processData() {
  const data = await api.data.read('file.json');
  return data.values.map(v => v * 2);
}
```

**✅ 好的做法**:
```typescript
async function processData(): Promise<number[]> {
  try {
    const data = await api.data.read('file.json');
    
    if (!data || !Array.isArray(data.values)) {
      throw new Error('数据格式不正确');
    }
    
    return data.values.map(v => {
      if (typeof v !== 'number') {
        throw new Error(`无效的数值: ${v}`);
      }
      return v * 2;
    });
  } catch (error) {
    api.utils.error('处理数据失败:', error);
    
    api.ui.showNotification({
      type: 'error',
      message: `数据处理失败: ${error.message}`,
    });
    
    throw error;  // 重新抛出，让调用者处理
  }
}
```

---

### 3. 异步操作

正确处理异步操作和Promise。

**❌ 不好的做法**:
```typescript
function loadData() {
  api.data.read('file.json').then(data => {
    this.data = data;
  });
  // 返回时数据可能还没加载完
  return this.data;
}
```

**✅ 好的做法**:
```typescript
async function loadData(): Promise<Data> {
  const data = await api.data.read('file.json');
  this.data = data;
  return data;
}

// 或使用Promise.all并行加载
async function loadMultipleFiles(): Promise<Data[]> {
  const promises = files.map(f => api.data.read(f));
  return await Promise.all(promises);
}
```

---

### 4. 资源清理

在插件停用时清理所有资源。

**✅ 好的做法**:
```typescript
class MyPlugin implements Plugin {
  private timers: number[] = [];
  private listeners: Map<string, Function> = new Map();

  async onActivate(api: PluginAPI): Promise<void> {
    // 注册事件
    const handler = () => console.log('event');
    this.listeners.set('simulation:complete', handler);
    api.events.on('simulation:complete', handler);

    // 设置定时器
    const timer = setInterval(() => {
      this.checkStatus();
    }, 1000);
    this.timers.push(timer);
  }

  async onDeactivate(): Promise<void> {
    // 清理事件监听
    this.listeners.forEach((handler, event) => {
      api.events.off(event, handler);
    });
    this.listeners.clear();

    // 清理定时器
    this.timers.forEach(timer => clearInterval(timer));
    this.timers = [];

    // 保存状态
    await api.storage.set('plugin-state', this.state);
  }
}
```

---

## ⚡ 性能优化

### 1. 避免阻塞主线程

耗时操作使用Web Worker或分批处理。

**❌ 不好的做法**:
```typescript
function processLargeData(data: number[]): number[] {
  // 阻塞主线程
  return data.map(v => expensiveOperation(v));
}
```

**✅ 好的做法**:
```typescript
async function processLargeData(data: number[]): Promise<number[]> {
  const batchSize = 1000;
  const results: number[] = [];
  
  for (let i = 0; i < data.length; i += batchSize) {
    const batch = data.slice(i, i + batchSize);
    const processed = batch.map(v => expensiveOperation(v));
    results.push(...processed);
    
    // 让出控制权
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  
  return results;
}
```

---

### 2. 缓存计算结果

缓存重复的计算结果。

**✅ 好的做法**:
```typescript
class Calculator {
  private cache: Map<string, number> = new Map();

  calculate(x: number, y: number): number {
    const key = `${x},${y}`;
    
    if (this.cache.has(key)) {
      return this.cache.get(key)!;
    }
    
    const result = expensiveCalculation(x, y);
    this.cache.set(key, result);
    return result;
  }

  clearCache(): void {
    this.cache.clear();
  }
}
```

---

### 3. 防抖和节流

限制频繁触发的操作。

**✅ 防抖** (Debounce):
```typescript
function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: number;
  
  return function(...args: Parameters<T>) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

// 使用
const handleInput = debounce((value: string) => {
  api.simulation.updateConfig({ name: value });
}, 300);
```

**✅ 节流** (Throttle):
```typescript
function throttle<T extends (...args: any[]) => any>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let lastCall = 0;
  
  return function(...args: Parameters<T>) {
    const now = Date.now();
    if (now - lastCall >= limit) {
      lastCall = now;
      fn(...args);
    }
  };
}

// 使用
const handleScroll = throttle(() => {
  updateVisibleItems();
}, 100);
```

---

## 🎨 用户体验

### 1. 提供反馈

所有操作都应该给用户明确的反馈。

**✅ 好的做法**:
```typescript
async function exportData() {
  // 开始时显示loading
  api.ui.showNotification({
    type: 'info',
    message: '正在导出数据...',
  });

  try {
    const data = await prepareData();
    const blob = await api.data.export(data, 'csv');
    api.utils.downloadFile(blob, 'result.csv');
    
    // 成功时显示成功消息
    api.ui.showNotification({
      type: 'success',
      message: '数据导出成功！',
    });
  } catch (error) {
    // 失败时显示错误
    api.ui.showNotification({
      type: 'error',
      message: '导出失败: ' + error.message,
    });
  }
}
```

---

### 2. 进度指示

长时间操作显示进度。

**✅ 好的做法**:
```typescript
async function processLargeDataset(data: any[]) {
  const total = data.length;
  
  for (let i = 0; i < total; i++) {
    await processItem(data[i]);
    
    // 更新进度
    const progress = (i + 1) / total;
    api.events.emit('plugin:progress', {
      current: i + 1,
      total,
      progress,
    });
  }
}
```

---

### 3. 可配置性

提供配置选项而不是硬编码。

**✅ 好的做法**:
```json
{
  "contributes": {
    "settings": [
      {
        "key": "maxIterations",
        "type": "number",
        "default": 100,
        "title": "最大迭代次数",
        "minimum": 10,
        "maximum": 1000
      },
      {
        "key": "algorithm",
        "type": "string",
        "default": "auto",
        "title": "优化算法",
        "enum": ["auto", "genetic", "gradient"]
      }
    ]
  }
}
```

```typescript
async function optimize() {
  const maxIterations = await api.storage.get('maxIterations') || 100;
  const algorithm = await api.storage.get('algorithm') || 'auto';
  
  // 使用配置
  runOptimization({ maxIterations, algorithm });
}
```

---

## 🔒 安全性

### 1. 输入验证

验证所有用户输入。

**✅ 好的做法**:
```typescript
function validateConfig(config: any): SimulationConfig {
  if (!config || typeof config !== 'object') {
    throw new Error('配置必须是对象');
  }

  const { roughness, slope, width } = config;

  if (typeof roughness !== 'number' || roughness <= 0 || roughness > 1) {
    throw new Error('糙率必须在0-1之间');
  }

  if (typeof slope !== 'number' || slope <= 0 || slope > 0.1) {
    throw new Error('坡度必须在0-0.1之间');
  }

  if (typeof width !== 'number' || width <= 0) {
    throw new Error('宽度必须大于0');
  }

  return { roughness, slope, width };
}
```

---

### 2. 避免注入攻击

不要直接执行用户输入的代码。

**❌ 危险的做法**:
```typescript
// 永远不要这样做！
const formula = userInput;
const result = eval(formula);
```

**✅ 安全的做法**:
```typescript
// 使用白名单
const allowedFunctions = {
  sin: Math.sin,
  cos: Math.cos,
  sqrt: Math.sqrt,
};

function evaluateFormula(formula: string, x: number): number {
  // 只允许特定的函数
  const match = formula.match(/^(\w+)\(x\)$/);
  if (!match) {
    throw new Error('无效的公式');
  }
  
  const funcName = match[1];
  const func = allowedFunctions[funcName];
  
  if (!func) {
    throw new Error(`不支持的函数: ${funcName}`);
  }
  
  return func(x);
}
```

---

## 📚 文档

### 1. 代码注释

关键逻辑添加清晰的注释。

**✅ 好的做法**:
```typescript
/**
 * 使用遗传算法优化参数
 * 
 * @param params - 优化参数
 * @param config - 算法配置
 * @returns 最优解
 * 
 * @example
 * ```typescript
 * const result = await optimize({
 *   parameters: [{ name: 'roughness', min: 0.01, max: 0.05 }],
 *   targetValue: 10.0
 * });
 * ```
 */
async function optimize(
  params: OptimizationParams,
  config?: AlgorithmConfig
): Promise<OptimizationResult> {
  // 初始化种群
  let population = initializePopulation(params);

  // 迭代优化
  for (let gen = 0; gen < config.maxGenerations; gen++) {
    // 评估适应度
    population = await evaluateFitness(population);
    
    // 选择
    const selected = selection(population);
    
    // 交叉和变异
    population = crossoverAndMutate(selected);
  }

  return getBest(population);
}
```

---

### 2. README文档

提供完整的README。

**必须包含**:
- 功能概述
- 安装方法
- 使用示例
- API文档
- 配置选项
- 常见问题
- 更新日志
- 许可证

---

## 🧪 测试

### 1. 单元测试

为关键函数编写单元测试。

**✅ 好的做法**:
```typescript
// calculate.test.ts
import { describe, test, expect } from '@jest/globals';
import { calculate } from './calculate';

describe('calculate', () => {
  test('should calculate correctly', () => {
    expect(calculate(2, 3)).toBe(5);
  });

  test('should handle negative numbers', () => {
    expect(calculate(-2, 3)).toBe(1);
  });

  test('should throw for invalid input', () => {
    expect(() => calculate(NaN, 3)).toThrow();
  });
});
```

---

### 2. 集成测试

测试插件与HydroClaude的集成。

**✅ 好的做法**:
```typescript
describe('MyPlugin Integration', () => {
  let api: PluginAPI;
  let plugin: MyPlugin;

  beforeEach(() => {
    api = createMockAPI();
    plugin = new MyPlugin();
  });

  test('should register commands on activate', async () => {
    await plugin.onActivate(api);
    
    expect(api.commands.register).toHaveBeenCalledWith(
      'my-command',
      expect.any(Function)
    );
  });

  test('should clean up on deactivate', async () => {
    await plugin.onActivate(api);
    await plugin.onDeactivate();
    
    expect(api.commands.unregister).toHaveBeenCalled();
  });
});
```

---

## 🚀 发布

### 1. 版本管理

遵循语义化版本控制。

```
版本格式: MAJOR.MINOR.PATCH

- MAJOR: 不兼容的API修改
- MINOR: 向下兼容的功能性新增
- PATCH: 向下兼容的bug修复

例子:
1.0.0 -> 1.0.1 (bug修复)
1.0.1 -> 1.1.0 (新功能)
1.1.0 -> 2.0.0 (破坏性变更)
```

---

### 2. 更新日志

维护详细的CHANGELOG.md。

```markdown
# 更新日志

## [1.1.0] - 2025-11-15

### 新增
- 添加批量处理功能
- 支持新的文件格式

### 修改
- 优化性能，提速30%
- 改进用户界面

### 修复
- 修复导出bug (#123)
- 修复内存泄漏

## [1.0.0] - 2025-11-01

### 新增
- 初始版本发布
```

---

## 📊 性能基准

### 推荐指标

```
插件大小:     < 1MB
加载时间:     < 500ms
激活时间:     < 100ms
命令响应:     < 50ms
内存占用:     < 50MB
```

---

<p align="center">
  <b>遵循最佳实践，开发高质量插件</b>
</p>
