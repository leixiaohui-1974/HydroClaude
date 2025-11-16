# HydroClaude插件开发文档

**版本**: 2.0.0  
**更新**: 2025-11-15

---

## 📖 文档导航

欢迎来到HydroClaude插件开发文档！本文档将帮助你快速上手插件开发。

---

## 🚀 快速开始

### 5分钟入门

1. **[快速入门指南](./getting-started.md)** 📘
   - 创建第一个插件
   - 项目结构
   - 开发环境
   - 调试技巧

2. **[示例插件](../../plugins/examples/)** 💡
   - 参数优化插件
   - 数据导入插件
   - 自定义可视化插件

---

## 📚 核心文档

### 基础知识

- **[快速入门](./getting-started.md)** - 30分钟快速上手
- **[插件清单规范](./plugin-manifest.md)** - plugin.json详解
- **[API完整参考](./api-reference.md)** - 8个标准API文档

### 进阶学习

- **[最佳实践](./best-practices.md)** - 设计模式和代码质量
- **[FAQ](./faq.md)** - 常见问题解答

---

## 🎯 按场景查找

### 我想要...

#### 🔰 学习插件开发

1. 阅读[快速入门](./getting-started.md)
2. 查看[示例插件](../../plugins/examples/)
3. 参考[API文档](./api-reference.md)

---

#### 🛠️ 创建特定功能的插件

**数据处理**:
- [Data API](./api-reference.md#data-api) - 数据导入导出
- [示例: 数据导入插件](../../plugins/examples/data-import/)

**参数优化**:
- [Simulation API](./api-reference.md#simulation-api) - 运行仿真
- [示例: 参数优化插件](../../plugins/examples/parameter-optimization/)

**可视化**:
- [Visualization API](./api-reference.md#visualization-api) - 自定义图表
- [示例: 自定义可视化插件](../../plugins/examples/custom-visualization/)

**UI扩展**:
- [UI API](./api-reference.md#ui-api) - 按钮、面板、对话框

---

#### 🔍 解决问题

1. 查看[FAQ](./faq.md) - 常见问题
2. 搜索[GitHub Issues](https://github.com/hydroclaude/hydroclaude/issues)
3. 在[论坛](https://forum.hydroclaude.com)提问

---

#### 📦 发布插件

1. 完成开发和测试
2. 编写README文档
3. 更新CHANGELOG
4. 执行发布命令

```bash
hydroclaude-cli publish
```

---

## 📋 API速查表

### 8个标准API

| API | 用途 | 常用方法 |
|-----|------|----------|
| **Simulation** | 仿真控制 | `run()`, `getResult()`, `onProgress()` |
| **Visualization** | 可视化 | `registerChart()`, `createChart()` |
| **Data** | 数据处理 | `import()`, `export()`, `registerImporter()` |
| **UI** | 用户界面 | `addButton()`, `showNotification()`, `showDialog()` |
| **Utils** | 工具函数 | `log()`, `fetch()`, `downloadFile()` |
| **Storage** | 数据存储 | `get()`, `set()`, `keys()` |
| **Events** | 事件系统 | `on()`, `emit()`, `once()` |
| **Commands** | 命令系统 | `register()`, `execute()` |

完整文档: [API参考](./api-reference.md)

---

## 💻 代码示例

### Hello World

```typescript
import type { Plugin, PluginAPI } from '@hydroclaude/types';

class HelloPlugin implements Plugin {
  manifest = {
    id: 'hello-world',
    name: 'Hello World',
    version: '1.0.0',
    description: 'My first plugin',
    author: 'Me',
    main: 'dist/index.js',
    permissions: ['ui:modify' as const],
    license: 'MIT',
  };

  async onActivate(api: PluginAPI): Promise<void> {
    api.ui.addButton({
      id: 'hello-btn',
      label: 'Say Hello',
      icon: 'smile',
      position: 'toolbar',
      onClick: () => {
        api.ui.showNotification({
          type: 'success',
          message: 'Hello, HydroClaude!',
        });
      },
    });
  }

  async onDeactivate(): Promise<void> {
    console.log('Goodbye!');
  }
}

export default new HelloPlugin();
```

---

### 运行仿真

```typescript
async function runSimulation(api: PluginAPI) {
  try {
    // 监听进度
    api.simulation.onProgress((progress) => {
      console.log(`进度: ${(progress * 100).toFixed(0)}%`);
    });

    // 运行仿真
    const result = await api.simulation.run({
      roughness: 0.025,
      slope: 0.001,
      duration: 3600,
    });

    // 显示结果
    api.ui.showNotification({
      type: 'success',
      message: `仿真完成！流量: ${result.flow.toFixed(2)} m³/s`,
    });
  } catch (error) {
    api.utils.error('仿真失败:', error);
  }
}
```

---

### 数据导入

```typescript
async function importData(api: PluginAPI, file: File) {
  try {
    // 导入文件
    const data = await api.data.import(file, 'xlsx');
    
    // 验证数据
    if (!Array.isArray(data) || data.length === 0) {
      throw new Error('数据为空');
    }

    // 保存到存储
    await api.storage.set('imported-data', data);

    // 通知成功
    api.ui.showNotification({
      type: 'success',
      message: `成功导入${data.length}条数据`,
    });
  } catch (error) {
    api.ui.showNotification({
      type: 'error',
      message: `导入失败: ${error.message}`,
    });
  }
}
```

---

## 🎓 学习路径

### 初级 (1-2天)

- [ ] 完成[快速入门](./getting-started.md)
- [ ] 理解项目结构
- [ ] 学习基础API
- [ ] 创建Hello World插件

### 中级 (3-5天)

- [ ] 掌握所有8个API
- [ ] 使用事件系统
- [ ] 数据持久化
- [ ] 错误处理
- [ ] 查看[最佳实践](./best-practices.md)

### 高级 (1-2周)

- [ ] 复杂算法实现（参考[参数优化插件](../../plugins/examples/parameter-optimization/)）
- [ ] 性能优化
- [ ] 插件间通信
- [ ] 发布到市场

---

## 🛠️ 开发工具

### 推荐工具

- **编辑器**: VS Code
- **Node.js**: v18+
- **包管理器**: npm或yarn
- **测试**: Jest
- **调试**: Chrome DevTools

### VS Code扩展

- TypeScript
- ESLint
- Prettier
- GitLens

---

## 📦 项目模板

快速创建新插件：

```bash
# 使用模板
git clone https://github.com/hydroclaude/plugin-template my-plugin
cd my-plugin
npm install

# 开发
npm run dev

# 构建
npm run build

# 测试
npm test
```

---

## 🔗 相关资源

### 官方资源

- **文档**: https://docs.hydroclaude.com
- **GitHub**: https://github.com/hydroclaude/hydroclaude
- **插件市场**: https://plugins.hydroclaude.com
- **更新日志**: https://github.com/hydroclaude/hydroclaude/releases

### 社区资源

- **论坛**: https://forum.hydroclaude.com
- **Discord**: https://discord.gg/hydroclaude
- **Stack Overflow**: 使用标签 `hydroclaude`

### 示例和教程

- **官方示例**: [plugins/examples/](../../plugins/examples/)
- **社区插件**: https://github.com/topics/hydroclaude-plugin
- **视频教程**: https://www.youtube.com/@hydroclaude

---

## 📊 统计数据

### 插件系统能力

```
✅ 8个标准API
✅ 完整的生命周期管理
✅ 权限系统
✅ 事件通信
✅ 数据持久化
✅ UI扩展
✅ 命令系统
✅ 类型安全（TypeScript）
```

### 已有示例插件

```
✅ 参数优化插件      (~550行)
✅ 数据导入插件      (~480行)
✅ 自定义可视化插件  (~460行)
```

---

## 💡 提示和技巧

### 快速技巧

1. **使用TypeScript** - 获得类型检查和自动补全
2. **查看示例** - 学习最佳实践
3. **最小权限** - 只请求必需的权限
4. **错误处理** - 全面的try-catch
5. **资源清理** - 在onDeactivate()中清理

### 调试技巧

```typescript
// 使用api.utils.log()
api.utils.log('调试信息:', value);

// 使用console（开发模式）
console.log('Debug:', value);

// 使用浏览器DevTools
debugger;  // 设置断点
```

---

## 🎯 下一步

**新手？** 从这里开始：
1. 阅读[快速入门](./getting-started.md)
2. 创建Hello World插件
3. 查看[示例插件](../../plugins/examples/)

**有经验？** 深入学习：
1. 查看[API参考](./api-reference.md)
2. 阅读[最佳实践](./best-practices.md)
3. 开发你的插件

**遇到问题？** 获取帮助：
1. 查看[FAQ](./faq.md)
2. 搜索[GitHub Issues](https://github.com/hydroclaude/hydroclaude/issues)
3. 在[论坛](https://forum.hydroclaude.com)提问

---

## 📮 反馈

文档有问题或建议？

- **GitHub Issue**: https://github.com/hydroclaude/hydroclaude/issues
- **论坛**: https://forum.hydroclaude.com
- **邮件**: docs@hydroclaude.com

---

<p align="center">
  <b>🎉 开始你的插件开发之旅！🎉</b>
</p>

<p align="center">
  <i>Happy Coding! 💻</i>
</p>
