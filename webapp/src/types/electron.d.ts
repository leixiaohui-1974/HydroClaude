/**
 * Electron API类型定义
 */

interface ElectronAPI {
  // 对话框API
  dialog: {
    openFile: () => Promise<{ path: string; content: any } | null>;
    saveFile: (data: any) => Promise<string | null>;
    selectDirectory: () => Promise<string | null>;
    showMessage: (options: {
      type: 'info' | 'warning' | 'error' | 'question';
      title: string;
      message: string;
      buttons?: string[];
    }) => Promise<number>;
  };

  // 文件系统API
  fs: {
    readFile: (filePath: string) => Promise<string>;
    writeFile: (filePath: string, content: string) => Promise<boolean>;
  };

  // 应用API
  app: {
    getInfo: () => Promise<{
      version: string;
      name: string;
      platform: string;
      arch: string;
    }>;
    quit: () => Promise<void>;
  };

  // 窗口API
  window: {
    minimize: () => Promise<void>;
    maximize: () => Promise<void>;
    close: () => Promise<void>;
  };

  // 平台信息
  platform: string;
  isElectron: boolean;
}

// 扩展Window接口
interface Window {
  electron?: ElectronAPI;
}
