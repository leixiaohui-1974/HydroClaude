/**
 * 插件API实现
 * 提供插件可调用的标准接口
 */

import type {
  PluginAPI,
  SimulationAPI,
  VisualizationAPI,
  DataAPI,
  UIAPI,
  UtilsAPI,
  StorageAPI,
  EventsAPI,
  CommandsAPI,
} from '@/types/plugin';
import { message, Modal } from 'antd';
import { simulationService } from './simulations';

/**
 * 事件总线
 */
class EventBus implements EventsAPI {
  private listeners: Map<string, Set<Function>> = new Map();

  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  off(event: string, callback: Function): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  emit(event: string, ...args: any[]): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(...args);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  once(event: string, callback: Function): void {
    const wrapper = (...args: any[]) => {
      callback(...args);
      this.off(event, wrapper);
    };
    this.on(event, wrapper);
  }
}

/**
 * 命令注册表
 */
class CommandRegistry implements CommandsAPI {
  private commands: Map<string, Function> = new Map();

  register(id: string, handler: Function): void {
    if (this.commands.has(id)) {
      throw new Error(`Command ${id} is already registered`);
    }
    this.commands.set(id, handler);
  }

  async execute(id: string, ...args: any[]): Promise<any> {
    const handler = this.commands.get(id);
    if (!handler) {
      throw new Error(`Command ${id} not found`);
    }
    return await handler(...args);
  }

  unregister(id: string): void {
    this.commands.delete(id);
  }

  getAll(): any[] {
    return Array.from(this.commands.keys()).map((id) => ({ id }));
  }
}

/**
 * 创建仿真API
 */
function createSimulationAPI(events: EventBus): SimulationAPI {
  return {
    async getConfig() {
      const stored = localStorage.getItem('hydroclaude-simulation-config');
      return stored ? JSON.parse(stored) : {};
    },

    async updateConfig(config: any) {
      localStorage.setItem('hydroclaude-simulation-config', JSON.stringify(config));
      events.emit('simulation:configChanged', config);
    },

    async run(config: any) {
      events.emit('simulation:start');
      try {
        const job = await simulationService.createJob(config);
        await simulationService.runJob(job.id);
        const completed = await simulationService.pollJobStatus(job.id);
        const result = await simulationService.getResults(completed.id);
        events.emit('simulation:complete', result);
        return result;
      } catch (error) {
        events.emit('simulation:error', error);
        throw error;
      }
    },

    async stop() {
      events.emit('simulation:stop');
    },

    async getResult(jobId: string) {
      return await simulationService.getResults(jobId);
    },

    onStart(callback: (jobId: string) => void) {
      events.on('simulation:start', callback);
    },

    onProgress(callback: (progress: number) => void) {
      events.on('simulation:progress', callback);
    },

    onComplete(callback: (result: any) => void) {
      events.on('simulation:complete', callback);
    },

    onError(callback: (error: Error) => void) {
      events.on('simulation:error', callback);
    },
  };
}

/**
 * 创建可视化API
 */
function createVisualizationAPI(events: EventBus): VisualizationAPI {
  const customCharts: Map<string, any> = new Map();

  return {
    registerChart(config) {
      if (customCharts.has(config.type)) {
        throw new Error(`Chart type ${config.type} is already registered`);
      }
      customCharts.set(config.type, config);
      events.emit('visualization:chartRegistered', config);
    },

    createChart(type: string, data: any, options?: any) {
      const config = customCharts.get(type);
      if (!config) {
        throw new Error(`Chart type ${type} not found`);
      }
      events.emit('visualization:createChart', { type, data, options });
    },

    updateChart(id: string, data: any) {
      events.emit('visualization:updateChart', { id, data });
    },

    removeChart(id: string) {
      events.emit('visualization:removeChart', { id });
    },
  };
}

/**
 * 创建数据API
 */
function createDataAPI(events: EventBus): DataAPI {
  const importers: Map<string, Function> = new Map();
  const exporters: Map<string, Function> = new Map();

  return {
    async read(path: string) {
      const stored = localStorage.getItem(`hydroclaude-data-${path}`);
      return stored ? JSON.parse(stored) : {};
    },

    async write(path: string, data: any) {
      localStorage.setItem(`hydroclaude-data-${path}`, JSON.stringify(data));
      events.emit('data:written', { path, data });
    },

    async import(file: File, format: string) {
      const importer = importers.get(format);
      if (!importer) {
        throw new Error(`No importer found for format: ${format}`);
      }
      return await importer(file);
    },

    async export(data: any, format: string) {
      const exporter = exporters.get(format);
      if (!exporter) {
        throw new Error(`No exporter found for format: ${format}`);
      }
      return await exporter(data);
    },

    registerImporter(config) {
      config.formats.forEach((format) => {
        importers.set(format, config.handler);
      });
    },

    registerExporter(config) {
      exporters.set(config.format, config.handler);
    },
  };
}

/**
 * 创建UI API
 */
function createUIAPI(events: EventBus): UIAPI {
  return {
    addButton(config) {
      events.emit('ui:addButton', config);
    },

    addPanel(config) {
      events.emit('ui:addPanel', config);
    },

    showNotification(config) {
      const { type, message: msg, duration = 3000 } = config;
      switch (type) {
        case 'success':
          message.success(msg, duration / 1000);
          break;
        case 'warning':
          message.warning(msg, duration / 1000);
          break;
        case 'error':
          message.error(msg, duration / 1000);
          break;
        default:
          message.info(msg, duration / 1000);
      }
    },

    showDialog(config) {
      Modal.confirm({
        title: config.title,
        content: config.content,
        onOk: config.onOk,
        onCancel: config.onCancel,
      });
    },
  };
}

/**
 * 创建工具API
 */
function createUtilsAPI(): UtilsAPI {
  return {
    log: (...args: any[]) => console.log('[Plugin]', ...args),
    warn: (...args: any[]) => console.warn('[Plugin]', ...args),
    error: (...args: any[]) => console.error('[Plugin]', ...args),

    fetch: fetch.bind(window),

    async readFile(file: File) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result!);
        reader.onerror = reject;
        reader.readAsText(file);
      });
    },

    downloadFile(blob: Blob, filename: string) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    },
  };
}

/**
 * 创建存储API
 */
function createStorageAPI(): StorageAPI {
  const prefix = 'hydroclaude-plugin-';

  return {
    async get(key: string) {
      const value = localStorage.getItem(prefix + key);
      return value ? JSON.parse(value) : null;
    },

    async set(key: string, value: any) {
      localStorage.setItem(prefix + key, JSON.stringify(value));
    },

    async remove(key: string) {
      localStorage.removeItem(prefix + key);
    },

    async clear() {
      const keys = await this.keys();
      keys.forEach((key) => localStorage.removeItem(prefix + key));
    },

    async keys() {
      const allKeys = Object.keys(localStorage);
      return allKeys
        .filter((key) => key.startsWith(prefix))
        .map((key) => key.substring(prefix.length));
    },
  };
}

/**
 * 创建插件API
 */
export function createPluginAPI(): PluginAPI {
  const events = new EventBus();
  const commands = new CommandRegistry();

  return {
    simulation: createSimulationAPI(events),
    visualization: createVisualizationAPI(events),
    data: createDataAPI(events),
    ui: createUIAPI(events),
    utils: createUtilsAPI(),
    storage: createStorageAPI(),
    events,
    commands,
  };
}
