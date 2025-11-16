/**
 * Electron Preload Script
 * 为渲染进程提供安全的API
 */

import { contextBridge, ipcRenderer } from 'electron';

// 定义暴露给渲染进程的API
const electronAPI = {
  // 对话框API
  dialog: {
    openFile: () => ipcRenderer.invoke('dialog:openFile'),
    saveFile: (data: any) => ipcRenderer.invoke('dialog:saveFile', data),
    selectDirectory: () => ipcRenderer.invoke('dialog:selectDirectory'),
    showMessage: (options: {
      type: 'info' | 'warning' | 'error' | 'question';
      title: string;
      message: string;
      buttons?: string[];
    }) => ipcRenderer.invoke('dialog:showMessage', options),
  },

  // 文件系统API
  fs: {
    readFile: (filePath: string) => ipcRenderer.invoke('fs:readFile', filePath),
    writeFile: (filePath: string, content: string) =>
      ipcRenderer.invoke('fs:writeFile', filePath, content),
  },

  // 应用API
  app: {
    getInfo: () => ipcRenderer.invoke('app:getInfo'),
    quit: () => ipcRenderer.invoke('app:quit'),
  },

  // 窗口API
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
  },

  // 平台信息
  platform: process.platform,
  isElectron: true,
};

// 暴露API到渲染进程
contextBridge.exposeInMainWorld('electron', electronAPI);

// 类型定义（用于TypeScript）
export type ElectronAPI = typeof electronAPI;
