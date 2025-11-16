/**
 * 应用菜单
 */

import { Menu, shell, app } from 'electron';

const isMac = process.platform === 'darwin';

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
            // TODO: 实现新建项目
          },
        },
        {
          label: '打开项目',
          accelerator: 'CmdOrCtrl+O',
          click: () => {
            // TODO: 实现打开项目
          },
        },
        { type: 'separator' },
        {
          label: '保存',
          accelerator: 'CmdOrCtrl+S',
          click: () => {
            // TODO: 实现保存
          },
        },
        {
          label: '另存为',
          accelerator: 'CmdOrCtrl+Shift+S',
          click: () => {
            // TODO: 实现另存为
          },
        },
        { type: 'separator' },
        {
          label: '导入数据',
          click: () => {
            // TODO: 实现导入
          },
        },
        {
          label: '导出结果',
          click: () => {
            // TODO: 实现导出
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
            // TODO: 实现检查更新
          },
        },
        { type: 'separator' },
        ...(!isMac
          ? [
              {
                label: '关于HydroClaude',
                click: () => {
                  // TODO: 显示关于对话框
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
