/**
 * 应用菜单
 */

import { Menu, shell, app, BrowserWindow, dialog } from 'electron';
import { readFile } from 'fs/promises';

const isMac = process.platform === 'darwin';

function getMainWindow(): BrowserWindow | null {
  const windows = BrowserWindow.getAllWindows();
  return windows.length > 0 ? windows[0] : null;
}

function sendToRenderer(channel: string, ...args: unknown[]): void {
  const win = getMainWindow();
  if (win) {
    win.webContents.send(channel, ...args);
  }
}

export function createMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    // 应用菜单 (仅macOS)
    ...(isMac
      ? [
          {
            label: app.name,
            submenu: [
              { role: 'about' as const, label: '关于HydroClaude' },
              { type: 'separator' as const },
              { role: 'services' as const, label: '服务' },
              { type: 'separator' as const },
              { role: 'hide' as const, label: '隐藏HydroClaude' },
              { role: 'hideOthers' as const, label: '隐藏其他' },
              { role: 'unhide' as const, label: '显示全部' },
              { type: 'separator' as const },
              { role: 'quit' as const, label: '退出HydroClaude' },
            ],
          },
        ]
      : []),

    // 文件菜单
    {
      label: '文件',
      submenu: [
        {
          label: '新建项目',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            sendToRenderer('menu:newProject');
            const win = getMainWindow();
            if (win) {
              win.webContents.executeJavaScript(
                "window.location.hash = '#/editor/new'"
              );
            }
          },
        },
        {
          label: '打开项目',
          accelerator: 'CmdOrCtrl+O',
          click: async () => {
            const result = await dialog.showOpenDialog({
              title: '打开项目文件',
              filters: [
                { name: 'HydroClaude项目', extensions: ['hc', 'json'] },
                { name: '所有文件', extensions: ['*'] },
              ],
              properties: ['openFile'],
            });
            if (!result.canceled && result.filePaths.length > 0) {
              try {
                const content = await readFile(result.filePaths[0], 'utf-8');
                const config = JSON.parse(content);
                sendToRenderer('menu:openProject', {
                  path: result.filePaths[0],
                  config,
                });
              } catch (error) {
                dialog.showErrorBox('打开失败', '无法读取项目文件');
              }
            }
          },
        },
        { type: 'separator' },
        {
          label: '保存',
          accelerator: 'CmdOrCtrl+S',
          click: () => {
            sendToRenderer('menu:save');
          },
        },
        {
          label: '另存为',
          accelerator: 'CmdOrCtrl+Shift+S',
          click: () => {
            sendToRenderer('menu:saveAs');
          },
        },
        { type: 'separator' },
        {
          label: '导入数据',
          click: async () => {
            const result = await dialog.showOpenDialog({
              title: '导入数据',
              filters: [
                { name: '数据文件', extensions: ['csv', 'xlsx', 'json'] },
                { name: '所有文件', extensions: ['*'] },
              ],
              properties: ['openFile'],
            });
            if (!result.canceled && result.filePaths.length > 0) {
              sendToRenderer('menu:importData', result.filePaths[0]);
            }
          },
        },
        {
          label: '导出结果',
          click: async () => {
            const result = await dialog.showSaveDialog({
              title: '导出结果',
              defaultPath: 'results.csv',
              filters: [
                { name: 'CSV文件', extensions: ['csv'] },
                { name: 'JSON文件', extensions: ['json'] },
              ],
            });
            if (!result.canceled && result.filePath) {
              sendToRenderer('menu:exportResults', result.filePath);
            }
          },
        },
        { type: 'separator' },
        ...(isMac
          ? []
          : [
              {
                label: '退出',
                accelerator: 'Alt+F4',
                click: () => app.quit(),
              },
            ]),
      ],
    },

    // 编辑菜单
    {
      label: '编辑',
      submenu: [
        { role: 'undo' as const, label: '撤销' },
        { role: 'redo' as const, label: '重做' },
        { type: 'separator' as const },
        { role: 'cut' as const, label: '剪切' },
        { role: 'copy' as const, label: '复制' },
        { role: 'paste' as const, label: '粘贴' },
        ...(isMac
          ? [
              { role: 'pasteAndMatchStyle' as const, label: '粘贴并匹配样式' },
              { role: 'delete' as const, label: '删除' },
              { role: 'selectAll' as const, label: '全选' },
            ]
          : [
              { role: 'delete' as const, label: '删除' },
              { type: 'separator' as const },
              { role: 'selectAll' as const, label: '全选' },
            ]),
      ],
    },

    // 视图菜单
    {
      label: '视图',
      submenu: [
        { role: 'reload' as const, label: '重新加载' },
        { role: 'forceReload' as const, label: '强制重新加载' },
        { role: 'toggleDevTools' as const, label: '开发者工具' },
        { type: 'separator' as const },
        { role: 'resetZoom' as const, label: '实际大小' },
        { role: 'zoomIn' as const, label: '放大' },
        { role: 'zoomOut' as const, label: '缩小' },
        { type: 'separator' as const },
        { role: 'togglefullscreen' as const, label: '全屏' },
      ],
    },

    // 窗口菜单
    {
      label: '窗口',
      submenu: [
        { role: 'minimize' as const, label: '最小化' },
        { role: 'zoom' as const, label: '缩放' },
        ...(isMac
          ? [
              { type: 'separator' as const },
              { role: 'front' as const, label: '前置所有窗口' },
              { type: 'separator' as const },
              { role: 'window' as const, label: '窗口' },
            ]
          : [{ role: 'close' as const, label: '关闭' }]),
      ],
    },

    // 帮助菜单
    {
      label: '帮助',
      submenu: [
        {
          label: '文档',
          click: async () => {
            await shell.openExternal('https://docs.hydroclaude.com');
          },
        },
        {
          label: 'GitHub',
          click: async () => {
            await shell.openExternal('https://github.com/hydroclaude/hydroclaude');
          },
        },
        { type: 'separator' },
        {
          label: '检查更新',
          click: () => {
            const win = getMainWindow();
            if (win) {
              dialog.showMessageBox(win, {
                type: 'info',
                title: '检查更新',
                message: `当前版本: ${app.getVersion()}`,
                detail: '已是最新版本。',
                buttons: ['确定'],
              });
            }
          },
        },
        { type: 'separator' },
        ...(!isMac
          ? [
              {
                label: '关于HydroClaude',
                click: () => {
                  const win = getMainWindow();
                  if (win) {
                    dialog.showMessageBox(win, {
                      type: 'info',
                      title: '关于 HydroClaude',
                      message: 'HydroClaude',
                      detail: [
                        `版本: ${app.getVersion()}`,
                        '水力学仿真平台',
                        '',
                        '功能: 明渠水力学仿真、管网分析、水锤分析',
                        '求解器: Godunov FVM, HLLC Riemann, Preissmann, MOC',
                        '',
                        'HydroClaude Development Team',
                      ].join('\n'),
                      buttons: ['确定'],
                    });
                  }
                },
              },
            ]
          : []),
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}
