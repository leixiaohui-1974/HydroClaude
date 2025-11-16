# 🚀 Phase 5.3 插件系统 - 快速体验指南

**更新**: 2025-11-15  
**版本**: HydroClaude v2.0.0  
**状态**: ✅ 已完成

---

## 📖 概述

本指南将帮助你在5分钟内快速体验HydroClaude的插件系统功能。

---

## 🎯 快速开始

### 步骤1: 查看插件文档

**所有文档位于**: `docs/plugins/`

```bash
cd docs/plugins/
ls -l
```

**文档列表**:
```
README.md              # 文档导航和索引 ⭐ 从这里开始
getting-started.md     # 快速入门指南
api-reference.md       # API完整参考
best-practices.md      # 最佳实践
faq.md                 # 常见问题
plugin-manifest.md     # 插件清单规范
```

---

### 步骤2: 查看示例插件

**所有示例位于**: `plugins/examples/`

```bash
cd plugins/examples/
ls -l
```

**示例列表**:
```
parameter-optimization/    # 参数优化插件
data-import/              # 数据导入插件
custom-visualization/     # 自定义可视化插件
```

---

### 步骤3: 理解插件架构

#### 插件文件结构

```
my-plugin/
├── plugin.json           # 插件清单（必需）
├── src/
│   └── index.ts          # 插件入口（必需）
├── package.json
├── tsconfig.json
└── README.md
```

#### 最小插件示例

**plugin.json**:
```json
{
  "id": "my-plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "description": "插件描述",
  "author": "你的名字",
  "main": "dist/index.js",
  "permissions": ["ui:modify"],
  "license": "MIT"
}
```

**src/index.ts**:
```typescript
import type { Plugin, PluginAPI } from '@hydroclaude/types';

class MyPlugin implements Plugin {
  manifest = {
    id: 'my-plugin',
    name: '我的插件',
    version: '1.0.0',
    description: '插件描述',
    author: '你的名字',
    main: 'dist/index.js',
    permissions: ['ui:modify' as const],
    license: 'MIT',
  };

  async onActivate(api: PluginAPI): Promise<void> {
    api.ui.showNotification({
      type: 'success',
      message: 'Hello from my plugin!',
    });
  }

  async onDeactivate(): Promise<void> {
    console.log('插件已停用');
  }
}

export default new MyPlugin();
```

---

### 步骤4: 学习插件API

#### 8个标准API

| API | 用途 | 常用方法 |
|-----|------|----------|
| **SimulationAPI** | 仿真控制 | `run()`, `getResult()`, `onProgress()` |
| **VisualizationAPI** | 可视化 | `registerChart()`, `createChart()` |
| **DataAPI** | 数据处理 | `import()`, `export()`, `registerImporter()` |
| **UIAPI** | 用户界面 | `addButton()`, `showNotification()`, `showDialog()` |
| **UtilsAPI** | 工具函数 | `log()`, `fetch()`, `downloadFile()` |
| **StorageAPI** | 数据存储 | `get()`, `set()`, `keys()` |
| **EventsAPI** | 事件系统 | `on()`, `emit()`, `once()` |
| **CommandsAPI** | 命令系统 | `register()`, `execute()` |

**详细文档**: 查看 `docs/plugins/api-reference.md`

---

### 步骤5: 查看实际示例

#### 示例1: 参数优化插件

**位置**: `plugins/examples/parameter-optimization/`

**功能**:
- ✅ 遗传算法优化
- ✅ 实时进度显示
- ✅ 历史记录管理
- ✅ 结果可视化

**使用的API**:
- Simulation API - 运行仿真
- UI API - 显示进度
- Storage API - 保存历史
- Events API - 发布事件
- Commands API - 注册命令

**查看代码**:
```bash
cd plugins/examples/parameter-optimization/
cat README.md              # 查看文档
cat src/index.ts           # 查看源代码
```

---

#### 示例2: 数据导入插件

**位置**: `plugins/examples/data-import/`

**功能**:
- ✅ Excel导入 (.xlsx, .xls)
- ✅ CSV导入 (.csv)
- ✅ JSON导入 (.json)
- ✅ 自动格式检测
- ✅ 数据验证

**使用的API**:
- Data API - 注册导入器
- Utils API - 文件操作
- UI API - 显示对话框
- Commands API - 注册命令
- Storage API - 保存配置

**查看代码**:
```bash
cd plugins/examples/data-import/
cat README.md
cat src/index.ts
```

---

#### 示例3: 自定义可视化插件

**位置**: `plugins/examples/custom-visualization/`

**功能**:
- ✅ 热力图 (Heatmap)
- ✅ 等值线图 (Contour)
- ✅ 3D表面图 (3D Surface)
- ✅ 交互式图表

**使用的API**:
- Visualization API - 注册图表
- Data API - 获取数据
- UI API - 显示按钮
- Events API - 监听事件
- Commands API - 注册命令

**查看代码**:
```bash
cd plugins/examples/custom-visualization/
cat README.md
cat src/index.ts
```

---

## 📚 学习路径

### 新手路径 (推荐)

**第1步**: 阅读文档首页
```bash
# 打开文档首页
cat docs/plugins/README.md
```

**第2步**: 完成快速入门
```bash
# 阅读快速入门指南
cat docs/plugins/getting-started.md
```

**第3步**: 查看API参考
```bash
# 查看API完整参考
cat docs/plugins/api-reference.md
```

**第4步**: 学习示例插件
```bash
# 阅读示例插件代码
cat plugins/examples/parameter-optimization/src/index.ts
cat plugins/examples/data-import/src/index.ts
cat plugins/examples/custom-visualization/src/index.ts
```

**第5步**: 阅读最佳实践
```bash
# 学习最佳实践
cat docs/plugins/best-practices.md
```

**第6步**: 查阅FAQ
```bash
# 查找常见问题解答
cat docs/plugins/faq.md
```

---

### 进阶路径

**第1步**: 理解插件清单
```bash
# 学习plugin.json规范
cat docs/plugins/plugin-manifest.md
```

**第2步**: 深入API文档
```bash
# 详细阅读API参考
cat docs/plugins/api-reference.md
```

**第3步**: 分析示例代码
```bash
# 深入分析示例插件实现
cd plugins/examples/parameter-optimization/
# 阅读完整源代码
```

**第4步**: 实践开发
```bash
# 创建自己的插件
# 参考示例和文档
```

---

## 🎓 关键概念

### 插件生命周期

```typescript
class MyPlugin implements Plugin {
  // 1. 插件激活时调用
  async onActivate(api: PluginAPI): Promise<void> {
    // 注册功能
    // 初始化状态
    // 加载配置
  }

  // 2. 插件停用时调用
  async onDeactivate(): Promise<void> {
    // 清理资源
    // 保存状态
    // 取消注册
  }

  // 3. 插件更新时调用（可选）
  async onUpdate?(oldVersion: string): Promise<void> {
    // 迁移数据
    // 更新配置
  }

  // 4. 插件卸载时调用（可选）
  async onUninstall?(): Promise<void> {
    // 清理数据
    // 删除配置
  }
}
```

---

### 权限系统

**16个细粒度权限**:

```json
{
  "permissions": [
    // 仿真权限
    "simulation:read",
    "simulation:write",
    "simulation:execute",
    
    // 数据权限
    "data:read",
    "data:write",
    "data:import",
    "data:export",
    
    // UI权限
    "ui:modify",
    
    // 文件系统权限
    "filesystem:read",
    "filesystem:write",
    
    // 网络权限
    "network:request"
  ]
}
```

**最佳实践**: 只请求必需的权限

---

### 事件通信

**发布事件**:
```typescript
api.events.emit('my-event', { data: 'hello' });
```

**订阅事件**:
```typescript
api.events.on('simulation:complete', (result) => {
  console.log('仿真完成:', result);
});
```

**一次性订阅**:
```typescript
api.events.once('plugin:loaded', () => {
  console.log('插件已加载');
});
```

---

## 💻 实用代码片段

### 添加工具栏按钮

```typescript
api.ui.addButton({
  id: 'my-button',
  label: '点我',
  icon: 'star',
  position: 'toolbar',
  onClick: () => {
    api.ui.showNotification({
      type: 'success',
      message: '按钮被点击！',
    });
  },
});
```

---

### 运行仿真

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

### 导入数据

```typescript
api.data.registerImporter({
  formats: ['csv'],
  handler: async (file) => {
    const text = await file.text();
    const rows = text.split('\n').map(row => row.split(','));
    return rows;
  },
});
```

---

### 保存和读取数据

```typescript
// 保存
await api.storage.set('my-key', { value: 123 });

// 读取
const data = await api.storage.get('my-key');
console.log(data.value); // 123
```

---

## 🔍 常见问题速查

### Q: 如何调试插件？

**A**: 使用`api.utils.log()`或浏览器开发者工具

```typescript
api.utils.log('调试信息:', value);
api.utils.warn('警告:', warning);
api.utils.error('错误:', error);
```

---

### Q: 插件加载失败？

**A**: 检查以下几点：
1. `plugin.json`格式是否正确
2. 权限是否完整
3. 入口文件路径是否正确
4. TypeScript是否已编译

---

### Q: 如何处理错误？

**A**: 使用try-catch

```typescript
async onActivate(api: PluginAPI) {
  try {
    await initialize();
  } catch (error) {
    api.utils.error('初始化失败:', error);
    api.ui.showNotification({
      type: 'error',
      message: '插件加载失败',
    });
  }
}
```

---

## 📊 插件系统能力

```
✅ 8个标准API
✅ 完整的生命周期管理
✅ 细粒度权限系统
✅ 事件通信机制
✅ 数据持久化
✅ UI扩展能力
✅ 命令系统
✅ TypeScript类型安全
```

---

## 🎯 下一步

### 初学者

1. **阅读快速入门**
   ```bash
   cat docs/plugins/getting-started.md
   ```

2. **查看示例插件**
   ```bash
   cd plugins/examples/
   ls -l
   ```

3. **尝试创建插件**
   - 从Hello World开始
   - 参考示例代码

---

### 有经验的开发者

1. **深入API文档**
   ```bash
   cat docs/plugins/api-reference.md
   ```

2. **学习最佳实践**
   ```bash
   cat docs/plugins/best-practices.md
   ```

3. **分析示例插件**
   - 参数优化算法
   - 数据导入机制
   - 可视化扩展

---

## 📁 文件导航

### 文档文件

```
docs/plugins/
├── README.md                # 🏠 文档首页
├── getting-started.md       # 🚀 快速入门
├── api-reference.md         # 📖 API参考
├── best-practices.md        # 💡 最佳实践
├── faq.md                   # ❓ 常见问题
└── plugin-manifest.md       # 📋 清单规范
```

### 示例插件

```
plugins/examples/
├── parameter-optimization/  # 🎯 参数优化
├── data-import/            # 📥 数据导入
└── custom-visualization/   # 📊 自定义可视化
```

### 核心代码

```
webapp/src/
├── types/plugin.ts          # 类型定义
├── services/
│   ├── pluginManager.ts     # 插件管理器
│   └── pluginAPI.ts         # 插件API实现
└── components/
    └── PluginCard/          # 插件卡片组件
```

---

## 🎉 快速体验完成！

现在你已经了解了HydroClaude插件系统的基础知识。

**接下来可以**:

1. ✅ 深入阅读完整文档
2. ✅ 分析示例插件代码
3. ✅ 创建你的第一个插件
4. ✅ 加入社区讨论

**需要帮助？**

- 📖 查看文档: `docs/plugins/`
- 💬 论坛: https://forum.hydroclaude.com
- 💻 GitHub: https://github.com/hydroclaude/hydroclaude

---

<p align="center">
  <b>🚀 开始你的插件开发之旅！🚀</b>
</p>
