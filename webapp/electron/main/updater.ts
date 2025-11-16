/**
 * 自动更新
 */

import { autoUpdater } from 'electron-updater';
import { BrowserWindow, dialog } from 'electron';

export function setupAutoUpdater(mainWindow: BrowserWindow | null): void {
  // 配置更新源
  autoUpdater.setFeedURL({
    provider: 'github',
    owner: 'hydroclaude',
    repo: 'hydroclaude',
  });

  // 检查更新时
  autoUpdater.on('checking-for-update', () => {
    console.log('正在检查更新...');
  });

  // 有可用更新
  autoUpdater.on('update-available', (info) => {
    console.log('发现新版本:', info.version);
    
    dialog.showMessageBox({
      type: 'info',
      title: '发现新版本',
      message: `发现新版本 ${info.version}`,
      detail: '更新将在后台下载',
      buttons: ['确定'],
    });
  });

  // 没有可用更新
  autoUpdater.on('update-not-available', (info) => {
    console.log('当前已是最新版本:', info.version);
  });

  // 下载进度
  autoUpdater.on('download-progress', (progressObj) => {
    const percent = progressObj.percent.toFixed(2);
    console.log(`下载进度: ${percent}%`);
    
    // 更新窗口标题显示进度
    mainWindow?.setTitle(`HydroClaude - 下载更新中 ${percent}%`);
  });

  // 更新下载完成
  autoUpdater.on('update-downloaded', (info) => {
    console.log('更新下载完成:', info.version);
    
    // 恢复窗口标题
    mainWindow?.setTitle('HydroClaude');

    dialog.showMessageBox({
      type: 'info',
      title: '更新下载完成',
      message: '新版本已下载完成',
      detail: '点击"重启"按钮安装更新',
      buttons: ['稍后', '重启'],
    }).then((result) => {
      if (result.response === 1) {
        // 退出并安装更新
        autoUpdater.quitAndInstall();
      }
    });
  });

  // 更新错误
  autoUpdater.on('error', (error) => {
    console.error('更新错误:', error);
    
    dialog.showErrorBox('更新错误', `检查更新时出错:\n${error.message}`);
  });

  // 启动时自动检查更新
  setTimeout(() => {
    autoUpdater.checkForUpdates();
  }, 3000);

  // 每6小时检查一次更新
  setInterval(() => {
    autoUpdater.checkForUpdates();
  }, 6 * 60 * 60 * 1000);
}

// 手动检查更新
export function checkForUpdates(): void {
  autoUpdater.checkForUpdates();
}
