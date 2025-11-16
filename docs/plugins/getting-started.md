# 插件开发快速入门

**版本**: 1.0.0  
**更新**: 2025-11-15

---

## 📖 概述

本指南将帮助你快速创建第一个HydroClaude插件。

### 前置知识

- ✅ JavaScript/TypeScript基础
- ✅ Node.js和npm
- ✅ React基础（可选）
- ✅ 异步编程

### 预计时间

- **第一个插件**: 30分钟
- **掌握基础**: 2-3小时
- **高级功能**: 1-2天

---

## 🚀 5分钟快速开始

### 1. 创建项目

```bash
# 克隆插件模板
git clone https://github.com/hydroclaude/plugin-template my-plugin
cd my-plugin

# 安装依赖
npm install
```

### 2. 编辑插件清单

编辑 `plugin.json`:

```json
{
  "id": "my-first-plugin",
  "name": "我的第一个插件",
  "version": "1.0.0",
  "description": "Hello World插件",
  "author": "你的名字",
  "main": "dist/index.js",
  "permissions": ["ui:modify"],
  "license": "MIT"
}
```

### 3. 编写插件代码

编辑 `src/index.ts`:

```typescript
import type { Plugin, PluginAPI } from '@hydroclaude/types';

class MyFirstPlugin implements Plugin {
  manifest = {
    id: 'my-first-plugin',
    name: '我的第一个插件',
    version: '1.0.0',
    description: 'Hello World插件',
    author: '你的名字',
    main: 'dist/index.js',
    permissions: ['ui:modify' as const],
    license: 'MIT',
  };

  async onActivate(api: PluginAPI): Promise<void> {
    // 添加工具栏按钮
    api.ui.addButton({
      id: 'my-button',
      label: '点我',
      icon: 'star',
      position: 'toolbar',
      onClick: () => {
        api.ui.showNotification({
          type: 'success',
          message: 'Hello from my plugin!',
        });
      },
    });

    api.utils.log('插件已激活！');
  }

  async onDeactivate(): Promise<void> {
    api.utils.log('插件已停用');
  }
}

export default new MyFirstPlugin();
```

### 4. 构建插件

```bash
npm run build
```

### 5. 测试插件

```bash
# 在HydroClaude中加载插件
# 方式1: 开发模式
npm run dev

# 方式2: 手动安装
# 将dist/目录复制到HydroClaude的plugins目录
```

---

## 📂 项目结构

### 标准结构

```
my-plugin/
├── plugin.json           # 插件清单
├── package.json          # NPM配置
├── tsconfig.json         # TypeScript配置
├── src/                  # 源代码
│   ├── index.ts          # 入口文件
│   └── ...               # 其他文件
├── dist/                 # 编译输出
│   └── index.js
├── test/                 # 测试文件
│   └── index.test.ts
├── README.md             # 文档
└── LICENSE               # 许可证
```

### 关键文件

#### plugin.json
插件的元数据和配置：

```json
{
  "id": "plugin-id",              // 唯一标识
  "name": "插件名称",             // 显示名称
  "version": "1.0.0",             // 版本号
  "description": "插件描述",      // 简短描述
  "author": "作者",               // 作者信息
  "main": "dist/index.js",        // 入口文件
  "permissions": [],              // 权限列表
  "contributes": {},              // 贡献点
  "dependencies": {}              // 依赖
}
```

#### package.json
NPM包配置：

```json
{
  "name": "hydroclaude-plugin-xxx",
  "version": "1.0.0",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "test": "jest"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@hydroclaude/types": "^2.0.0"
  }
}
```

#### tsconfig.json
TypeScript配置：

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ES2020",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "moduleResolution": "node"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "test"]
}
```

---

## 🔧 开发环境

### 推荐工具

1. **代码编辑器**: VS Code
   - 安装扩展: TypeScript, ESLint, Prettier

2. **Node.js**: v18+
   - 下载: https://nodejs.org/

3. **包管理器**: npm或yarn
   - npm自带Node.js
   - yarn: `npm install -g yarn`

### VS Code配置

创建 `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "node_modules/typescript/lib"
}
```

---

## 🎯 开发流程

### 标准流程

```
1. 规划功能
   ↓
2. 创建项目
   ↓
3. 编写代码
   ↓
4. 本地测试
   ↓
5. 编写文档
   ↓
6. 发布插件
```

### 开发模式

```bash
# 终端1: 监视文件变化，自动编译
npm run dev

# 终端2: 运行HydroClaude开发版
hydroclaude --dev --plugin-dir ./dist
```

### 调试技巧

**1. 使用console输出**:
```typescript
api.utils.log('调试信息');
api.utils.warn('警告信息');
api.utils.error('错误信息');
```

**2. 使用浏览器开发者工具**:
- 打开: F12
- 查看Console标签
- 设置断点

**3. 使用TypeScript类型检查**:
```bash
# 类型检查
npx tsc --noEmit
```

---

## 📝 编写第一个有用的插件

### 示例: 流量计算器

创建一个计算明渠流量的插件：

```typescript
import type { Plugin, PluginAPI } from '@hydroclaude/types';

interface ChannelParams {
  width: number;      // 渠宽 (m)
  depth: number;      // 水深 (m)
  slope: number;      // 坡度
  roughness: number;  // 糙率
}

class FlowCalculatorPlugin implements Plugin {
  private api!: PluginAPI;

  manifest = {
    id: 'flow-calculator',
    name: '流量计算器',
    version: '1.0.0',
    description: '快速计算明渠流量',
    author: 'Me',
    main: 'dist/index.js',
    permissions: ['ui:modify' as const],
    license: 'MIT',
  };

  async onActivate(api: PluginAPI): Promise<void> {
    this.api = api;

    // 注册命令
    api.commands.register('flow-calculator.calculate', () => {
      this.showCalculator();
    });

    // 添加按钮
    api.ui.addButton({
      id: 'calc-button',
      label: '流量计算',
      icon: 'calculator',
      position: 'toolbar',
      onClick: () => this.showCalculator(),
    });
  }

  private showCalculator(): void {
    // 显示对话框
    this.api.ui.showDialog({
      title: '明渠流量计算',
      content: this.createForm(),
      onOk: () => this.calculate(),
    });
  }

  private createForm(): any {
    // 实际应该返回React组件
    return 'Flow calculator form';
  }

  private calculate(): void {
    // 获取表单数据
    const params: ChannelParams = {
      width: 10,
      depth: 3,
      slope: 0.001,
      roughness: 0.025,
    };

    // 计算流量 (Manning公式)
    const area = params.width * params.depth;
    const perimeter = params.width + 2 * params.depth;
    const radius = area / perimeter;
    const flow = (area * Math.pow(radius, 2/3) * Math.sqrt(params.slope)) / params.roughness;

    // 显示结果
    this.api.ui.showNotification({
      type: 'success',
      message: `计算流量: ${flow.toFixed(2)} m³/s`,
      duration: 5000,
    });
  }
}

export default new FlowCalculatorPlugin();
```

---

## 🧪 测试插件

### 单元测试

创建 `test/index.test.ts`:

```typescript
import { describe, test, expect } from '@jest/globals';
import plugin from '../src/index';

describe('FlowCalculator Plugin', () => {
  test('should have correct manifest', () => {
    expect(plugin.manifest.id).toBe('flow-calculator');
    expect(plugin.manifest.version).toBe('1.0.0');
  });

  test('should activate successfully', async () => {
    const mockAPI = createMockAPI();
    await plugin.onActivate(mockAPI);
    
    expect(mockAPI.commands.register).toHaveBeenCalled();
    expect(mockAPI.ui.addButton).toHaveBeenCalled();
  });
});

function createMockAPI(): any {
  return {
    commands: {
      register: jest.fn(),
    },
    ui: {
      addButton: jest.fn(),
      showNotification: jest.fn(),
    },
    utils: {
      log: jest.fn(),
    },
  };
}
```

### 集成测试

在HydroClaude中测试：

1. 加载插件
2. 点击按钮
3. 验证功能
4. 检查控制台输出
5. 测试边界情况

---

## 📚 下一步

### 深入学习

1. **API参考** - 学习所有可用API
2. **示例插件** - 研究官方示例
3. **最佳实践** - 了解推荐做法
4. **高级功能** - 探索复杂场景

### 推荐阅读

- [API完整参考](./api-reference.md)
- [插件清单规范](./plugin-manifest.md)
- [最佳实践](./best-practices.md)
- [FAQ](./faq.md)

### 获取帮助

- **文档**: https://docs.hydroclaude.com
- **论坛**: https://forum.hydroclaude.com
- **GitHub**: https://github.com/hydroclaude/hydroclaude
- **Discord**: https://discord.gg/hydroclaude

---

## 🎓 学习路径

### 初级 (1-2天)

- [x] 完成快速开始
- [ ] 理解项目结构
- [ ] 学习基础API
- [ ] 创建简单插件

### 中级 (3-5天)

- [ ] 掌握所有API
- [ ] 使用事件系统
- [ ] 数据持久化
- [ ] 错误处理

### 高级 (1-2周)

- [ ] 复杂算法实现
- [ ] 性能优化
- [ ] 插件间通信
- [ ] 发布到市场

---

<p align="center">
  <b>🎉 恭喜！你已完成快速入门 🎉</b>
</p>

<p align="center">
  <i>开始创建你的第一个插件吧！</i>
</p>
