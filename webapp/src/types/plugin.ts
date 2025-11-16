/**
 * 插件系统类型定义
 */

/**
 * 插件清单文件
 */
export interface PluginManifest {
  // 基本信息
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  email?: string;
  homepage?: string;
  repository?: string;
  license: string;
  
  // 依赖
  dependencies?: Record<string, string>;
  peerDependencies?: Record<string, string>;
  engines?: {
    hydroclaude?: string;
    node?: string;
  };
  
  // 入口
  main: string;
  icon?: string;
  
  // 权限
  permissions: PluginPermission[];
  
  // 贡献点
  contributes?: {
    commands?: PluginCommand[];
    menus?: PluginMenu[];
    views?: PluginView[];
    settings?: PluginSetting[];
  };
  
  // 钩子
  hooks?: PluginHook[];
  
  // 元数据
  keywords?: string[];
  category?: PluginCategory;
  displayName?: string;
  preview?: boolean;
}

/**
 * 插件权限
 */
export type PluginPermission =
  | 'simulation:read'
  | 'simulation:write'
  | 'simulation:execute'
  | 'data:read'
  | 'data:write'
  | 'data:delete'
  | 'visualization:read'
  | 'visualization:create'
  | 'ui:modify'
  | 'ui:theme'
  | 'storage:read'
  | 'storage:write'
  | 'network:request'
  | 'filesystem:read'
  | 'filesystem:write';

/**
 * 插件类别
 */
export type PluginCategory =
  | 'optimization'        // 优化
  | 'data-processing'     // 数据处理
  | 'visualization'       // 可视化
  | 'import-export'       // 导入导出
  | 'analysis'           // 分析
  | 'automation'         // 自动化
  | 'integration'        // 集成
  | 'theme'              // 主题
  | 'extension'          // 扩展
  | 'other';             // 其他

/**
 * 插件钩子
 */
export type PluginHook =
  | 'beforeSimulation'
  | 'afterSimulation'
  | 'beforeDataLoad'
  | 'afterDataLoad'
  | 'beforeVisualize'
  | 'afterVisualize'
  | 'onError'
  | 'onConfigChange';

/**
 * 插件命令
 */
export interface PluginCommand {
  id: string;
  title: string;
  category?: string;
  icon?: string;
  shortcut?: string;
}

/**
 * 插件菜单
 */
export interface PluginMenu {
  id: string;
  label: string;
  position: 'toolbar' | 'sidebar' | 'context';
  when?: string;
  icon?: string;
}

/**
 * 插件视图
 */
export interface PluginView {
  id: string;
  name: string;
  icon?: string;
  when?: string;
  visibility?: 'visible' | 'hidden' | 'collapsed';
}

/**
 * 插件设置
 */
export interface PluginSetting {
  key: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  default?: any;
  title?: string;
  description?: string;
  enum?: any[];
  minimum?: number;
  maximum?: number;
}

/**
 * 插件接口
 */
export interface Plugin {
  // 插件清单
  manifest: PluginManifest;
  
  // 生命周期方法
  onInstall?(): Promise<void>;
  onActivate(api: PluginAPI): Promise<void>;
  onDeactivate?(): Promise<void>;
  onUninstall?(): Promise<void>;
  onUpdate?(oldVersion: string, newVersion: string): Promise<void>;
  
  // 钩子处理
  [key: string]: any;
}

/**
 * 插件API
 */
export interface PluginAPI {
  // 核心API
  simulation: SimulationAPI;
  visualization: VisualizationAPI;
  data: DataAPI;
  ui: UIAPI;
  
  // 工具API
  utils: UtilsAPI;
  storage: StorageAPI;
  events: EventsAPI;
  commands: CommandsAPI;
}

/**
 * 仿真API
 */
export interface SimulationAPI {
  // 获取配置
  getConfig(): Promise<any>;
  
  // 更新配置
  updateConfig(config: any): Promise<void>;
  
  // 运行仿真
  run(config: any): Promise<any>;
  
  // 停止仿真
  stop(): Promise<void>;
  
  // 获取结果
  getResult(jobId: string): Promise<any>;
  
  // 监听事件
  onStart(callback: (jobId: string) => void): void;
  onProgress(callback: (progress: number) => void): void;
  onComplete(callback: (result: any) => void): void;
  onError(callback: (error: Error) => void): void;
}

/**
 * 可视化API
 */
export interface VisualizationAPI {
  // 注册图表类型
  registerChart(config: {
    type: string;
    component: React.ComponentType<any>;
    icon?: string;
    title?: string;
  }): void;
  
  // 创建图表
  createChart(type: string, data: any, options?: any): void;
  
  // 更新图表
  updateChart(id: string, data: any): void;
  
  // 删除图表
  removeChart(id: string): void;
}

/**
 * 数据API
 */
export interface DataAPI {
  // 读取数据
  read(path: string): Promise<any>;
  
  // 写入数据
  write(path: string, data: any): Promise<void>;
  
  // 导入数据
  import(file: File, format: string): Promise<any>;
  
  // 导出数据
  export(data: any, format: string): Promise<Blob>;
  
  // 注册导入器
  registerImporter(config: {
    formats: string[];
    handler: (file: File) => Promise<any>;
  }): void;
  
  // 注册导出器
  registerExporter(config: {
    format: string;
    handler: (data: any) => Promise<Blob>;
  }): void;
}

/**
 * UI API
 */
export interface UIAPI {
  // 添加按钮
  addButton(config: {
    id: string;
    label: string;
    icon?: string;
    position: 'toolbar' | 'sidebar';
    onClick: () => void;
  }): void;
  
  // 添加面板
  addPanel(config: {
    id: string;
    title: string;
    component: React.ComponentType;
    position: 'left' | 'right' | 'bottom';
  }): void;
  
  // 显示通知
  showNotification(config: {
    type: 'info' | 'success' | 'warning' | 'error';
    message: string;
    duration?: number;
  }): void;
  
  // 显示对话框
  showDialog(config: {
    title: string;
    content: React.ReactNode;
    onOk?: () => void;
    onCancel?: () => void;
  }): void;
}

/**
 * 工具API
 */
export interface UtilsAPI {
  // 日志
  log: (...args: any[]) => void;
  warn: (...args: any[]) => void;
  error: (...args: any[]) => void;
  
  // HTTP请求
  fetch: typeof fetch;
  
  // 文件操作
  readFile: (file: File) => Promise<string | ArrayBuffer>;
  downloadFile: (blob: Blob, filename: string) => void;
}

/**
 * 存储API
 */
export interface StorageAPI {
  // 获取数据
  get(key: string): Promise<any>;
  
  // 设置数据
  set(key: string, value: any): Promise<void>;
  
  // 删除数据
  remove(key: string): Promise<void>;
  
  // 清空数据
  clear(): Promise<void>;
  
  // 获取所有键
  keys(): Promise<string[]>;
}

/**
 * 事件API
 */
export interface EventsAPI {
  // 订阅事件
  on(event: string, callback: (...args: any[]) => void): void;
  
  // 取消订阅
  off(event: string, callback: (...args: any[]) => void): void;
  
  // 发布事件
  emit(event: string, ...args: any[]): void;
  
  // 一次性订阅
  once(event: string, callback: (...args: any[]) => void): void;
}

/**
 * 命令API
 */
export interface CommandsAPI {
  // 注册命令
  register(id: string, handler: (...args: any[]) => any): void;
  
  // 执行命令
  execute(id: string, ...args: any[]): Promise<any>;
  
  // 取消注册
  unregister(id: string): void;
  
  // 获取所有命令
  getAll(): PluginCommand[];
}

/**
 * 插件状态
 */
export type PluginState = 'installed' | 'active' | 'inactive' | 'error';

/**
 * 插件信息
 */
export interface PluginInfo {
  manifest: PluginManifest;
  state: PluginState;
  installedAt: Date;
  activatedAt?: Date;
  version: string;
  error?: Error;
}

/**
 * 插件市场插件
 */
export interface MarketplacePlugin {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  icon?: string;
  category: PluginCategory;
  keywords: string[];
  rating: number;
  downloads: number;
  lastUpdated: Date;
  homepage?: string;
  repository?: string;
  screenshots?: string[];
  readme?: string;
}

/**
 * 插件搜索结果
 */
export interface PluginSearchResult {
  plugins: MarketplacePlugin[];
  total: number;
  page: number;
  pageSize: number;
}

/**
 * 插件搜索选项
 */
export interface PluginSearchOptions {
  query?: string;
  category?: PluginCategory;
  sortBy?: 'downloads' | 'rating' | 'updated' | 'name';
  page?: number;
  pageSize?: number;
}
