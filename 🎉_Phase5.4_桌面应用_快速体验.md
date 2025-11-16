# 🎉 Phase 5.4 桌面应用 - 快速体验指南

**更新**: 2025-11-15  
**版本**: HydroClaude v2.0.0  
**状态**: ✅ 已完成

---

## 📖 概述

HydroClaude现在可以作为独立的桌面应用运行！支持Windows、macOS和Linux。

---

## 🚀 快速开始

### 步骤1: 查看项目结构

```bash
cd webapp/
ls -la
```

**新增目录**:
```
electron/                  # Electron代码
├── main/                  # 主进程
│   ├── index.ts           # 主进程入口
│   ├── menu.ts            # 应用菜单
│   ├── tray.ts            # 系统托盘
│   └── updater.ts         # 自动更新
└── preload/               # 预加载脚本
    └── index.ts           # API暴露

src/
├── types/
│   └── electron.d.ts      # 类型定义
└── utils/
    └── electron.ts        # 工具函数
```

---

### 步骤2: 安装依赖

```bash
cd webapp/

# 安装Electron相关依赖
npm install

# 主要依赖:
# - electron@^28.0.0
# - electron-builder@^24.9.1
# - electron-vite@^2.0.0
# - electron-updater@^6.1.7
```

---

### 步骤3: 开发模式运行

```bash
# 启动Electron开发模式
npm run dev:electron
```

**这将做什么？**
1. 启动Vite开发服务器（React应用）
2. 启动Electron主进程
3. 打开桌面应用窗口
4. 自动打开开发者工具
5. 支持热重载

**预期效果**:
```
✓ Vite开发服务器启动在 http://localhost:5173
✓ Electron窗口打开
✓ 开发者工具已打开
✓ 修改代码自动刷新
```

---

### 步骤4: 构建桌面应用

```bash
# 构建并打包应用
npm run build:electron
```

**构建过程**:
```
1. 编译TypeScript
2. 构建React应用 (Vite)
3. 编译Electron主进程
4. 打包成安装程序
5. 输出到 release/ 目录
```

**生成的文件** (根据平台):

**Windows**:
```
release/2.0.0/
├── HydroClaude-Setup-2.0.0.exe        # 安装程序
└── HydroClaude-2.0.0-portable.exe     # 便携版
```

**macOS**:
```
release/2.0.0/
├── HydroClaude-2.0.0.dmg              # DMG镜像
└── HydroClaude-2.0.0-mac.zip          # ZIP归档
```

**Linux**:
```
release/2.0.0/
├── HydroClaude-2.0.0.AppImage         # 通用版本
├── hydroclaude_2.0.0_amd64.deb        # Debian/Ubuntu
└── hydroclaude-2.0.0.x86_64.rpm       # Fedora/CentOS
```

---

### 步骤5: 测试构建（快速）

```bash
# 只构建，不打包（快速测试）
npm run build:dir
```

**输出**:
```
release/
└── win-unpacked/          # Windows
    └── HydroClaude.exe
或
└── mac/                   # macOS
    └── HydroClaude.app
或
└── linux-unpacked/        # Linux
    └── hydroclaude
```

**运行测试**:
```bash
# Windows
./release/win-unpacked/HydroClaude.exe

# macOS
open ./release/mac/HydroClaude.app

# Linux
./release/linux-unpacked/hydroclaude
```

---

## 🎯 核心功能体验

### 1. 本地文件访问

在React组件中使用：

```typescript
import { openFileDialog, saveFileDialog } from '@/utils/electron';
import { Button } from 'antd';

function MyComponent() {
  const handleOpen = async () => {
    // 打开文件对话框
    const file = await openFileDialog();
    if (file) {
      console.log('文件路径:', file.path);
      console.log('文件内容:', file.content);
    }
  };

  const handleSave = async () => {
    // 保存文件对话框
    const data = { config: '...' };
    const path = await saveFileDialog(data);
    if (path) {
      console.log('保存到:', path);
    }
  };

  return (
    <>
      <Button onClick={handleOpen}>打开文件</Button>
      <Button onClick={handleSave}>保存文件</Button>
    </>
  );
}
```

---

### 2. 系统托盘

**功能**:
- 点击托盘图标显示/隐藏窗口
- 右键显示托盘菜单
- 最小化到托盘

**托盘菜单**:
```
• HydroClaude
• ─────────────
• 显示主窗口
• 新建项目
• ─────────────
• 关于
• 退出
```

**体验方式**:
1. 启动应用
2. 点击窗口右上角的最小化
3. 查看系统托盘（任务栏右下角）
4. 点击托盘图标重新显示窗口

---

### 3. 原生菜单

**菜单栏**:
```
文件 | 编辑 | 视图 | 窗口 | 帮助
```

**文件菜单**:
```
• 新建项目     Ctrl+N
• 打开项目     Ctrl+O
• ─────────────
• 保存         Ctrl+S
• 另存为       Ctrl+Shift+S
• ─────────────
• 导入数据
• 导出结果
• ─────────────
• 退出         Alt+F4
```

**快捷键**:
- `Ctrl+N` - 新建项目
- `Ctrl+O` - 打开项目
- `Ctrl+S` - 保存
- `Ctrl+Shift+S` - 另存为
- `F12` - 开发者工具
- `F11` - 全屏

---

### 4. 窗口管理

```typescript
import { minimizeWindow, maximizeWindow, closeWindow } from '@/utils/electron';

// 最小化窗口
await minimizeWindow();

// 最大化/恢复窗口
await maximizeWindow();

// 关闭窗口
await closeWindow();
```

---

### 5. 自动更新

**更新流程**:
```
1. 启动时自动检查更新 (3秒后)
2. 发现新版本 → 提示用户
3. 后台下载更新
4. 下载完成 → 询问是否安装
5. 用户确认 → 重启并更新
```

**手动检查**:
- 菜单栏 → 帮助 → 检查更新

**更新配置**:
```typescript
// electron/main/updater.ts
autoUpdater.setFeedURL({
  provider: 'github',
  owner: 'hydroclaude',
  repo: 'hydroclaude',
});
```

---

## 🔧 开发技巧

### 1. 检测Electron环境

```typescript
import { isElectron } from '@/utils/electron';

if (isElectron()) {
  console.log('运行在Electron中');
  // 使用Electron功能
} else {
  console.log('运行在浏览器中');
  // 使用Web功能
}
```

---

### 2. 访问Electron API

```typescript
import { getElectronAPI } from '@/utils/electron';

const api = getElectronAPI();
if (api) {
  const info = await api.app.getInfo();
  console.log('应用版本:', info.version);
  console.log('平台:', info.platform);
}
```

---

### 3. 调试主进程

在 `electron/main/index.ts` 中添加日志：

```typescript
console.log('主进程启动');
console.log('窗口创建完成');
```

查看输出：
```bash
npm run dev:electron
# 在终端查看console.log输出
```

---

### 4. 调试渲染进程

按 `F12` 打开开发者工具，像调试Web应用一样。

---

## 📊 配置选项

### 修改窗口大小

```typescript
// electron/main/index.ts
mainWindow = new BrowserWindow({
  width: 1280,      // 宽度
  height: 800,      // 高度
  minWidth: 1024,   // 最小宽度
  minHeight: 768,   // 最小高度
});
```

---

### 修改应用名称和ID

```json
// package.json
{
  "build": {
    "appId": "com.hydroclaude.app",
    "productName": "HydroClaude"
  }
}
```

---

### 添加应用图标

替换 `build/icons/` 下的文件：
```
build/icons/
├── icon.png        # 通用图标 (512x512)
├── icon.icns       # macOS图标
└── icon.ico        # Windows图标
```

**生成图标工具**:
- [electron-icon-builder](https://www.npmjs.com/package/electron-icon-builder)
- [iconutil](https://developer.apple.com/library/archive/documentation/GraphicsAnimation/Conceptual/HighResolutionOSX/Optimizing/Optimizing.html) (macOS)

---

## 📚 完整文档

详细文档: `webapp/ELECTRON_README.md`

**内容包括**:
- 完整的配置说明
- API详细文档
- 打包和发布流程
- 测试和调试
- 常见问题解答

---

## 🎯 快速任务

### 任务1: 运行开发模式

```bash
cd webapp/
npm install
npm run dev:electron
```

**预期**: 应用窗口打开，显示HydroClaude界面

---

### 任务2: 测试文件对话框

在React组件中添加按钮：

```typescript
<Button onClick={async () => {
  const file = await openFileDialog();
  console.log(file);
}}>
  打开文件
</Button>
```

**预期**: 点击按钮显示文件选择对话框

---

### 任务3: 构建桌面应用

```bash
npm run build:electron
```

**预期**: 在 `release/2.0.0/` 中生成安装包

---

### 任务4: 体验系统托盘

1. 启动应用
2. 最小化窗口
3. 点击托盘图标
4. 右键托盘图标查看菜单

---

## 💡 提示

### Windows用户

```bash
# 管理员权限可能需要（用于创建快捷方式）
# 首次运行可能需要允许防火墙访问
```

---

### macOS用户

```bash
# 首次运行可能提示"无法验证开发者"
# 解决: 系统偏好设置 → 安全性与隐私 → 允许
```

---

### Linux用户

```bash
# AppImage需要执行权限
chmod +x HydroClaude-2.0.0.AppImage
./HydroClaude-2.0.0.AppImage
```

---

## 🎊 特性总结

```
✅ 跨平台支持 (Windows/macOS/Linux)
✅ 本地文件访问
✅ 系统托盘集成
✅ 原生菜单和快捷键
✅ 自动更新
✅ 窗口管理
✅ 安全的IPC通信
✅ TypeScript类型安全
✅ 完整的开发工具链
```

---

<p align="center">
  <b>🎉 HydroClaude桌面应用已准备就绪！🎉</b>
</p>

<p align="center">
  <i>立即体验离线水力学仿真！</i>
</p>
