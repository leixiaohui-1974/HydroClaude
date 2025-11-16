/**
 * Electron工具函数
 */

/**
 * 检查是否在Electron环境中运行
 */
export function isElectron(): boolean {
  return window.electron?.isElectron === true;
}

/**
 * 获取Electron API
 */
export function getElectronAPI(): ElectronAPI | null {
  return window.electron || null;
}

/**
 * 打开文件对话框
 */
export async function openFileDialog(): Promise<{ path: string; content: any } | null> {
  const api = getElectronAPI();
  if (!api) {
    console.warn('Not running in Electron environment');
    return null;
  }
  
  return await api.dialog.openFile();
}

/**
 * 保存文件对话框
 */
export async function saveFileDialog(data: any): Promise<string | null> {
  const api = getElectronAPI();
  if (!api) {
    console.warn('Not running in Electron environment');
    return null;
  }
  
  return await api.dialog.saveFile(data);
}

/**
 * 选择目录对话框
 */
export async function selectDirectoryDialog(): Promise<string | null> {
  const api = getElectronAPI();
  if (!api) {
    console.warn('Not running in Electron environment');
    return null;
  }
  
  return await api.dialog.selectDirectory();
}

/**
 * 显示消息框
 */
export async function showMessageBox(options: {
  type: 'info' | 'warning' | 'error' | 'question';
  title: string;
  message: string;
  buttons?: string[];
}): Promise<number> {
  const api = getElectronAPI();
  if (!api) {
    console.warn('Not running in Electron environment');
    // Fallback to browser alert
    window.alert(`${options.title}\n\n${options.message}`);
    return 0;
  }
  
  return await api.dialog.showMessage(options);
}

/**
 * 读取本地文件
 */
export async function readLocalFile(filePath: string): Promise<string | null> {
  const api = getElectronAPI();
  if (!api) {
    console.warn('Not running in Electron environment');
    return null;
  }
  
  try {
    return await api.fs.readFile(filePath);
  } catch (error) {
    console.error('Failed to read file:', error);
    return null;
  }
}

/**
 * 写入本地文件
 */
export async function writeLocalFile(filePath: string, content: string): Promise<boolean> {
  const api = getElectronAPI();
  if (!api) {
    console.warn('Not running in Electron environment');
    return false;
  }
  
  try {
    return await api.fs.writeFile(filePath, content);
  } catch (error) {
    console.error('Failed to write file:', error);
    return false;
  }
}

/**
 * 获取应用信息
 */
export async function getAppInfo(): Promise<{
  version: string;
  name: string;
  platform: string;
  arch: string;
} | null> {
  const api = getElectronAPI();
  if (!api) {
    return null;
  }
  
  return await api.app.getInfo();
}

/**
 * 退出应用
 */
export async function quitApp(): Promise<void> {
  const api = getElectronAPI();
  if (api) {
    await api.app.quit();
  }
}

/**
 * 最小化窗口
 */
export async function minimizeWindow(): Promise<void> {
  const api = getElectronAPI();
  if (api) {
    await api.window.minimize();
  }
}

/**
 * 最大化窗口
 */
export async function maximizeWindow(): Promise<void> {
  const api = getElectronAPI();
  if (api) {
    await api.window.maximize();
  }
}

/**
 * 关闭窗口
 */
export async function closeWindow(): Promise<void> {
  const api = getElectronAPI();
  if (api) {
    await api.window.close();
  }
}

/**
 * 获取平台信息
 */
export function getPlatform(): string {
  return window.electron?.platform || 'web';
}
