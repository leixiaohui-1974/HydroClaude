# HydroClaude 桌面应用

HydroClaude的Electron桌面应用版本，提供离线使用和本地文件访问能力。

---

## 🚀 快速开始

### 安装依赖

```bash
cd webapp
npm install
```

### 开发模式

```bash
# 启动Electron开发模式
npm run dev:electron
```

这将同时启动：
- Vite开发服务器（React应用）
- Electron主进程
- 开发者工具

### 生产构建

```bash
# 构建并打包应用
npm run build:electron
```

生成的安装包位于 `release/` 目录：
- **Windows**: `.exe` (安装程序), `.exe` (便携版)
- **macOS**: `.dmg`, `.zip`
- **Linux**: `.AppImage`, `.deb`, `.rpm`

### 仅构建（不打包）

```bash
# 只构建，不生成安装包（用于测试）
npm run build:dir
```

---

## 📂 项目结构

```
webapp/
├── electron/                  # Electron代码
│   ├── main/                  # 主进程
│   │   ├── index.ts           # 主进程入口
│   │   ├── menu.ts            # 应用菜单
│   │   ├── tray.ts            # 系统托盘
│   │   └── updater.ts         # 自动更新
│   └── preload/               # 预加载脚本
│       └── index.ts           # Preload API
├── src/                       # React应用（渲染进程）
│   ├── types/
│   │   └── electron.d.ts      # Electron类型定义
│   └── utils/
│       └── electron.ts        # Electron工具函数
├── build/                     # 构建资源
│   └── icons/                 # 应用图标
│       ├── icon.png
│       ├── icon.icns          # macOS
│       └── icon.ico           # Windows
├── electron.vite.config.ts    # Electron配置
└── package.json               # 包含build配置
```

---

## 🔧 配置说明

### package.json

```json
{
  "main": "dist-electron/main/index.js",
  "scripts": {
    "dev:electron": "electron-vite dev",
    "build:electron": "electron-vite build && electron-builder"
  },
  "build": {
    "appId": "com.hydroclaude.app",
    "productName": "HydroClaude",
    "files": ["dist", "dist-electron"],
    "mac": { ... },
    "win": { ... },
    "linux": { ... }
  }
}
```

### electron.vite.config.ts

配置了三个进程的构建：
- **main**: 主进程（Node.js环境）
- **preload**: 预加载脚本（特殊环境）
- **renderer**: 渲染进程（浏览器环境，React应用）

---

## 🎯 功能特性

### 1. 窗口管理

- ✅ 自定义窗口大小和位置
- ✅ 记忆窗口状态
- ✅ 最小化到托盘
- ✅ 全屏支持
- ✅ 开发者工具（开发模式）

### 2. 本地文件访问

```typescript
import { openFileDialog, saveFileDialog } from '@/utils/electron';

// 打开文件
const file = await openFileDialog();

// 保存文件
const path = await saveFileDialog(data);
```

### 3. 系统集成

**系统托盘**:
- 托盘图标和菜单
- 点击显示/隐藏窗口
- 快速操作

**原生菜单**:
- 文件、编辑、视图、窗口、帮助菜单
- 快捷键支持
- 跨平台适配

### 4. 自动更新

- 启动时检查更新
- 后台下载
- 提示用户安装
- 增量更新（减小下载大小）

---

## 🔌 Electron API

### 在React组件中使用

```typescript
import { isElectron, getElectronAPI } from '@/utils/electron';
import { Button, message } from 'antd';

function MyComponent() {
  const handleOpenFile = async () => {
    if (!isElectron()) {
      message.info('仅桌面应用支持');
      return;
    }

    const file = await window.electron?.dialog.openFile();
    if (file) {
      console.log('打开文件:', file.path);
      // 处理文件内容
    }
  };

  return (
    <Button onClick={handleOpenFile}>
      打开文件
    </Button>
  );
}
```

### 可用API

#### 对话框

```typescript
// 打开文件
window.electron.dialog.openFile()

// 保存文件
window.electron.dialog.saveFile(data)

// 选择目录
window.electron.dialog.selectDirectory()

// 显示消息框
window.electron.dialog.showMessage({ ... })
```

#### 文件系统

```typescript
// 读取文件
window.electron.fs.readFile(filePath)

// 写入文件
window.electron.fs.writeFile(filePath, content)
```

#### 应用

```typescript
// 获取应用信息
window.electron.app.getInfo()

// 退出应用
window.electron.app.quit()
```

#### 窗口

```typescript
// 最小化
window.electron.window.minimize()

// 最大化/恢复
window.electron.window.maximize()

// 关闭
window.electron.window.close()
```

---

## 🔒 安全性

### Context Isolation

启用了上下文隔离，确保主进程和渲染进程分离：

```typescript
// electron/main/index.ts
webPreferences: {
  contextIsolation: true,      // 上下文隔离
  nodeIntegration: false,      // 禁用Node集成
  webSecurity: true,           // 启用Web安全
}
```

### 安全的API暴露

通过preload脚本暴露API，只暴露必要功能：

```typescript
// electron/preload/index.ts
contextBridge.exposeInMainWorld('electron', {
  dialog: { ... },
  fs: { ... },
  // 只暴露安全的、必要的API
});
```

---

## 📦 打包和发布

### 构建所有平台

```bash
# 构建当前平台
npm run build:electron

# 构建Windows (在Windows或macOS+wine)
electron-builder --win

# 构建macOS (仅macOS)
electron-builder --mac

# 构建Linux
electron-builder --linux
```

### 发布到GitHub Releases

1. 配置GitHub token:
```bash
export GH_TOKEN="your_github_token"
```

2. 构建并发布:
```bash
npm run build:electron -- --publish always
```

### 文件大小优化

- 使用 `asar` 打包应用文件
- 启用代码压缩
- 排除不必要的依赖

---

## 🧪 测试

### 开发模式测试

```bash
npm run dev:electron
```

### 生产构建测试

```bash
# 构建但不打包（快速）
npm run build:dir

# 运行构建后的应用
./release/win-unpacked/HydroClaude.exe  # Windows
./release/mac/HydroClaude.app          # macOS
./release/linux-unpacked/hydroclaude   # Linux
```

---

## 🐛 调试

### 主进程调试

在 `electron/main/index.ts` 中添加断点，使用VS Code调试：

```json
// .vscode/launch.json
{
  "type": "node",
  "request": "launch",
  "name": "Electron Main",
  "runtimeExecutable": "${workspaceFolder}/node_modules/.bin/electron",
  "args": [".", "--remote-debugging-port=9223"],
  "outputCapture": "std"
}
```

### 渲染进程调试

在开发模式下，按 `F12` 打开开发者工具。

### 日志输出

主进程日志输出到控制台：
```bash
npm run dev:electron
# 查看控制台输出
```

---

## ⚙️ 配置自定义

### 修改应用图标

替换 `build/icons/` 下的图标文件：
- **icon.png** - 通用图标（512x512）
- **icon.icns** - macOS图标
- **icon.ico** - Windows图标

### 修改应用ID和名称

在 `package.json` 的 `build` 部分：

```json
{
  "build": {
    "appId": "com.yourcompany.yourapp",
    "productName": "YourAppName"
  }
}
```

### 配置自动更新服务器

在 `electron/main/updater.ts` 中修改更新源：

```typescript
autoUpdater.setFeedURL({
  provider: 'github',
  owner: 'your-username',
  repo: 'your-repo',
});
```

---

## 📊 性能指标

**目标指标**:
```
启动时间:     < 2秒
内存占用:     < 200MB
安装包大小:   < 100MB
更新大小:     < 50MB (增量)
```

**优化建议**:
- 使用代码分割减小bundle大小
- 懒加载非必要模块
- 使用asar压缩应用文件
- 启用增量更新

---

## 🔗 相关资源

- **Electron文档**: https://www.electronjs.org/docs
- **electron-builder**: https://www.electron.build/
- **electron-vite**: https://electron-vite.org/
- **electron-updater**: https://www.electron.build/auto-update

---

## 📝 常见问题

### Q: 如何调试主进程？

**A**: 使用VS Code的调试配置，或者在主进程代码中添加 `console.log`。

### Q: 打包后的应用很大？

**A**: 检查是否包含了不必要的依赖，使用 `electron-builder` 的 `files` 配置排除不需要的文件。

### Q: 自动更新不工作？

**A**: 确保应用已签名（macOS/Windows），并正确配置了更新服务器。

### Q: 如何支持更多文件格式？

**A**: 在主进程的 IPC 处理中添加对应的文件读取/写入逻辑。

---

## 📄 许可证

MIT License - HydroClaude Development Team

---

<p align="center">
  <b>🎉 HydroClaude Desktop - 专业的水力学仿真桌面应用 🎉</b>
</p>
