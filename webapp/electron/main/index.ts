/**
 * Electron Main Process
 * HydroClaude Desktop Application
 */

import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron';
import { join } from 'path';
import { readFile, writeFile } from 'fs/promises';
import { createMenu } from './menu';
import { createTray } from './tray';
import { setupAutoUpdater } from './updater';

// 窗口实例
let mainWindow: BrowserWindow | null = null;

// 开发环境检测
const isDev = process.env.NODE_ENV === 'development';

/**
 * 创建主窗口
 */
function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 768,
    title: 'HydroClaude',
    icon: join(__dirname, '../../build/icons/icon.png'),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
    },
    show: false, // 等待ready-to-show事件再显示
  });

  // 优化窗口显示
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
    if (isDev) {
      mainWindow?.webContents.openDevTools();
    }
  });

  // 加载应用
  if (isDev) {
    // 开发模式：加载Vite开发服务器
    mainWindow.loadURL('http://localhost:5173');
  } else {
    // 生产模式：加载构建后的文件
    mainWindow.loadFile(join(__dirname, '../../dist/index.html'));
  }

  // 窗口关闭事件
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 外部链接在浏览器中打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

/**
 * 应用就绪
 */
app.whenReady().then(() => {
  // 创建主窗口
  createWindow();

  // 创建菜单
  createMenu();

  // 创建系统托盘
  createTray(mainWindow);

  // 设置自动更新
  if (!isDev) {
    setupAutoUpdater(mainWindow);
  }

  // macOS：点击dock图标时重新创建窗口
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

/**
 * 所有窗口关闭
 */
app.on('window-all-closed', () => {
  // macOS：除非用户明确退出，否则应用保持活动状态
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// ========== IPC处理 ==========

/**
 * 打开文件对话框
 */
ipcMain.handle('dialog:openFile', async () => {
  const result = await dialog.showOpenDialog({
    title: '打开项目文件',
    filters: [
      { name: 'HydroClaude项目', extensions: ['hc', 'json'] },
      { name: '所有文件', extensions: ['*'] },
    ],
    properties: ['openFile'],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  try {
    const filePath = result.filePaths[0];
    const content = await readFile(filePath, 'utf-8');
    return {
      path: filePath,
      content: JSON.parse(content),
    };
  } catch (error) {
    console.error('读取文件失败:', error);
    throw error;
  }
});

/**
 * 保存文件对话框
 */
ipcMain.handle('dialog:saveFile', async (_event, data: any) => {
  const result = await dialog.showSaveDialog({
    title: '保存项目文件',
    defaultPath: 'project.hc',
    filters: [
      { name: 'HydroClaude项目', extensions: ['hc'] },
      { name: 'JSON文件', extensions: ['json'] },
    ],
  });

  if (result.canceled || !result.filePath) {
    return null;
  }

  try {
    const content = JSON.stringify(data, null, 2);
    await writeFile(result.filePath, content, 'utf-8');
    return result.filePath;
  } catch (error) {
    console.error('保存文件失败:', error);
    throw error;
  }
});

/**
 * 选择目录
 */
ipcMain.handle('dialog:selectDirectory', async () => {
  const result = await dialog.showOpenDialog({
    title: '选择目录',
    properties: ['openDirectory'],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  return result.filePaths[0];
});

/**
 * 显示消息框
 */
ipcMain.handle('dialog:showMessage', async (_event, options: {
  type: 'info' | 'warning' | 'error' | 'question';
  title: string;
  message: string;
  buttons?: string[];
}) => {
  const result = await dialog.showMessageBox({
    type: options.type,
    title: options.title,
    message: options.message,
    buttons: options.buttons || ['确定'],
  });

  return result.response;
});

/**
 * 读取本地文件
 */
ipcMain.handle('fs:readFile', async (_event, filePath: string) => {
  try {
    const content = await readFile(filePath, 'utf-8');
    return content;
  } catch (error) {
    console.error('读取文件失败:', error);
    throw error;
  }
});

/**
 * 写入本地文件
 */
ipcMain.handle('fs:writeFile', async (_event, filePath: string, content: string) => {
  try {
    await writeFile(filePath, content, 'utf-8');
    return true;
  } catch (error) {
    console.error('写入文件失败:', error);
    throw error;
  }
});

/**
 * 获取应用信息
 */
ipcMain.handle('app:getInfo', () => {
  return {
    version: app.getVersion(),
    name: app.getName(),
    platform: process.platform,
    arch: process.arch,
  };
});

/**
 * 退出应用
 */
ipcMain.handle('app:quit', () => {
  app.quit();
});

/**
 * 最小化窗口
 */
ipcMain.handle('window:minimize', () => {
  mainWindow?.minimize();
});

/**
 * 最大化/恢复窗口
 */
ipcMain.handle('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});

/**
 * 关闭窗口
 */
ipcMain.handle('window:close', () => {
  mainWindow?.close();
});

// ========== 错误处理 ==========

process.on('uncaughtException', (error) => {
  console.error('未捕获的异常:', error);
  dialog.showErrorBox('应用错误', error.message);
});

process.on('unhandledRejection', (reason) => {
  console.error('未处理的Promise拒绝:', reason);
});
