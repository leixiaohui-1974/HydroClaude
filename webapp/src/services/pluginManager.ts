/**
 * 插件管理器
 * 负责插件的加载、激活、停用和卸载
 */

import type {
  Plugin,
  PluginAPI,
  PluginInfo,
  PluginManifest,
  PluginState,
} from '@/types/plugin';
import { createPluginAPI } from './pluginAPI';

/**
 * 插件管理器类
 */
export class PluginManager {
  private plugins: Map<string, PluginInfo> = new Map();
  private instances: Map<string, Plugin> = new Map();
  private api: PluginAPI;

  constructor() {
    this.api = createPluginAPI();
  }

  /**
   * 安装插件
   */
  async install(manifest: PluginManifest, code: string): Promise<void> {
    const { id } = manifest;

    // 检查是否已安装
    if (this.plugins.has(id)) {
      throw new Error(`Plugin ${id} is already installed`);
    }

    try {
      // 验证清单
      this.validateManifest(manifest);

      // 加载插件代码
      const plugin = await this.loadPlugin(code);

      // 调用安装钩子
      if (plugin.onInstall) {
        await plugin.onInstall();
      }

      // 保存插件信息
      const info: PluginInfo = {
        manifest,
        state: 'installed',
        installedAt: new Date(),
        version: manifest.version,
      };

      this.plugins.set(id, info);
      this.instances.set(id, plugin);

      console.log(`Plugin ${id} installed successfully`);
    } catch (error) {
      console.error(`Failed to install plugin ${id}:`, error);
      throw error;
    }
  }

  /**
   * 激活插件
   */
  async activate(id: string): Promise<void> {
    const info = this.plugins.get(id);
    const instance = this.instances.get(id);

    if (!info || !instance) {
      throw new Error(`Plugin ${id} not found`);
    }

    if (info.state === 'active') {
      console.warn(`Plugin ${id} is already active`);
      return;
    }

    try {
      // 检查权限
      this.checkPermissions(info.manifest);

      // 调用激活钩子
      await instance.onActivate(this.api);

      // 更新状态
      info.state = 'active';
      info.activatedAt = new Date();

      console.log(`Plugin ${id} activated successfully`);
    } catch (error) {
      info.state = 'error';
      info.error = error as Error;
      console.error(`Failed to activate plugin ${id}:`, error);
      throw error;
    }
  }

  /**
   * 停用插件
   */
  async deactivate(id: string): Promise<void> {
    const info = this.plugins.get(id);
    const instance = this.instances.get(id);

    if (!info || !instance) {
      throw new Error(`Plugin ${id} not found`);
    }

    if (info.state !== 'active') {
      console.warn(`Plugin ${id} is not active`);
      return;
    }

    try {
      // 调用停用钩子
      if (instance.onDeactivate) {
        await instance.onDeactivate();
      }

      // 更新状态
      info.state = 'inactive';
      info.activatedAt = undefined;

      console.log(`Plugin ${id} deactivated successfully`);
    } catch (error) {
      info.state = 'error';
      info.error = error as Error;
      console.error(`Failed to deactivate plugin ${id}:`, error);
      throw error;
    }
  }

  /**
   * 卸载插件
   */
  async uninstall(id: string): Promise<void> {
    const info = this.plugins.get(id);
    const instance = this.instances.get(id);

    if (!info || !instance) {
      throw new Error(`Plugin ${id} not found`);
    }

    try {
      // 先停用
      if (info.state === 'active') {
        await this.deactivate(id);
      }

      // 调用卸载钩子
      if (instance.onUninstall) {
        await instance.onUninstall();
      }

      // 删除插件
      this.plugins.delete(id);
      this.instances.delete(id);

      console.log(`Plugin ${id} uninstalled successfully`);
    } catch (error) {
      console.error(`Failed to uninstall plugin ${id}:`, error);
      throw error;
    }
  }

  /**
   * 更新插件
   */
  async update(id: string, manifest: PluginManifest, code: string): Promise<void> {
    const info = this.plugins.get(id);
    const instance = this.instances.get(id);

    if (!info || !instance) {
      throw new Error(`Plugin ${id} not found`);
    }

    const oldVersion = info.version;
    const newVersion = manifest.version;

    try {
      // 先停用
      if (info.state === 'active') {
        await this.deactivate(id);
      }

      // 加载新版本
      const newPlugin = await this.loadPlugin(code);

      // 调用更新钩子
      if (newPlugin.onUpdate) {
        await newPlugin.onUpdate(oldVersion, newVersion);
      }

      // 更新信息
      info.manifest = manifest;
      info.version = newVersion;
      this.instances.set(id, newPlugin);

      console.log(`Plugin ${id} updated from ${oldVersion} to ${newVersion}`);
    } catch (error) {
      console.error(`Failed to update plugin ${id}:`, error);
      throw error;
    }
  }

  /**
   * 获取插件信息
   */
  getPlugin(id: string): PluginInfo | undefined {
    return this.plugins.get(id);
  }

  /**
   * 获取所有插件
   */
  getAllPlugins(): PluginInfo[] {
    return Array.from(this.plugins.values());
  }

  /**
   * 获取激活的插件
   */
  getActivePlugins(): PluginInfo[] {
    return this.getAllPlugins().filter((p) => p.state === 'active');
  }

  /**
   * 验证插件清单
   */
  private validateManifest(manifest: PluginManifest): void {
    const required = ['id', 'name', 'version', 'description', 'author', 'main', 'permissions'];

    for (const field of required) {
      if (!(field in manifest)) {
        throw new Error(`Plugin manifest missing required field: ${field}`);
      }
    }

    // 验证版本格式
    if (!/^\d+\.\d+\.\d+/.test(manifest.version)) {
      throw new Error(`Invalid version format: ${manifest.version}`);
    }

    // 验证ID格式
    if (!/^[a-z0-9-]+$/.test(manifest.id)) {
      throw new Error(`Invalid plugin ID: ${manifest.id}`);
    }
  }

  /**
   * 检查权限
   */
  private checkPermissions(manifest: PluginManifest): void {
    const { permissions } = manifest;

    // 这里可以添加权限检查逻辑
    // 例如：检查用户是否授予了这些权限

    console.log(`Plugin ${manifest.id} requires permissions:`, permissions);
  }

  /**
   * 加载插件代码
   */
  private async loadPlugin(code: string): Promise<Plugin> {
    try {
      // 使用Function构造函数创建插件实例
      // 注意：这是一个简化版本，生产环境需要更安全的沙箱机制
      const pluginFactory = new Function('exports', 'require', code);
      const exports: any = {};
      const require = (name: string) => {
        // 这里可以提供允许的依赖
        throw new Error(`Module ${name} not available in plugin sandbox`);
      };

      pluginFactory(exports, require);

      const plugin = exports.default || exports;

      if (!plugin || typeof plugin.onActivate !== 'function') {
        throw new Error('Plugin must export onActivate method');
      }

      return plugin;
    } catch (error) {
      console.error('Failed to load plugin code:', error);
      throw new Error('Invalid plugin code');
    }
  }
}

// 创建全局插件管理器实例
export const pluginManager = new PluginManager();
