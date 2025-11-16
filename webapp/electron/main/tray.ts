/**
 * 系统托盘
 */

import { Tray, Menu, app, BrowserWindow, nativeImage } from 'electron';
import { join } from 'path';

let tray: Tray | null = null;

export function createTray(mainWindow: BrowserWindow | null): void {
  // 创建托盘图标
  const icon = nativeImage.createFromPath(
    join(__dirname, '../../build/icons/icon.png')
  ).resize({ width: 16, height: 16 });

  tray = new Tray(icon);

  // 设置托盘菜单
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'HydroClaude',
      type: 'normal',
      enabled: false,
    },
    { type: 'separator' },
    {
      label: '显示主窗口',
      click: () => {
        mainWindow?.show();
        mainWindow?.focus();
      },
    },
    {
      label: '新建项目',
      click: () => {
        mainWindow?.show();
        mainWindow?.focus();
        // TODO: 触发新建项目
      },
    },
    { type: 'separator' },
    {
      label: '关于',
      click: () => {
        // TODO: 显示关于对话框
      },
    },
    {
      label: '退出',
      click: () => {
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
  tray.setToolTip('HydroClaude - 水力学仿真软件');

  // 点击托盘图标显示主窗口
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });

  // 双击托盘图标显示主窗口
  tray.on('double-click', () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
}

export function destroyTray(): void {
  tray?.destroy();
  tray = null;
}
