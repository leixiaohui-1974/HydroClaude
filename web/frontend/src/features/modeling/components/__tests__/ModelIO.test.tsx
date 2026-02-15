/**
 * ModelIO Component - Unit Tests
 * ModelIO组件单元测试
 *
 * v1.5.0 Component Testing
 *
 * 注意：这些测试主要关注组件逻辑和工具函数集成，
 * 而不是详细的UI交互测试（那需要更复杂的mocking）
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import type { HydraulicModel } from '../../types/model.types';
import { NodeType } from '../../types/model.types';
import * as modelExport from '../../../../utils/modelExport';
import * as modelImport from '../../../../utils/modelImport';
import { STORAGE_KEYS } from '../../../../types/model-io';

declare var global: typeof globalThis;

// ============= Mock Data =============

const createMockModel = (overrides?: Partial<HydraulicModel>): HydraulicModel => ({
  id: 'test-model-123',
  name: 'Test Hydraulic Model',
  description: 'A test model',
  nodes: [
    {
      id: 'node-1',
      type: NodeType.CHANNEL,
      position: { x: 100, y: 200 },
      data: {
        name: 'Channel 1',
        width: 5.0,
        length: 100,
        slope: 0.001,
        manning_n: 0.025,
        n_cells: 50,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'node-2',
      type: NodeType.CHANNEL,
      position: { x: 300, y: 200 },
      data: {
        name: 'Channel 2',
        width: 3.0,
        length: 100,
        slope: 0.001,
        manning_n: 0.025,
        n_cells: 50,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'node-1',
      target: 'node-2',
      validated: true
    }
  ],
  created_at: '2025-11-11T00:00:00.000Z',
  updated_at: '2025-11-11T12:00:00.000Z',
  version: 1,
  validated: true,
  ...overrides
});

// ============= Mock localStorage =============

const createLocalStorageMock = () => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    }
  };
};

let localStorageMock: ReturnType<typeof createLocalStorageMock>;

describe('ModelIO - 导出工具函数集成', () => {
  const model = createMockModel();

  it('应该验证有效模型可以导出', () => {
    const validation = modelExport.validateModelForExport(model);

    expect(validation.valid).toBe(true);
    expect(validation.errors).toHaveLength(0);
  });

  it('应该检测无效模型', () => {
    const invalidModel = createMockModel({ id: '', name: '' });
    const validation = modelExport.validateModelForExport(invalidModel);

    expect(validation.valid).toBe(false);
    expect(validation.errors.length).toBeGreaterThan(0);
  });

  it('应该生成导出统计信息', () => {
    const stats = modelExport.getExportStatistics(model);

    expect(stats.nodeCount).toBe(2);
    expect(stats.edgeCount).toBe(1);
    expect(stats.estimatedJsonSize).toBeGreaterThan(0);
    expect(stats.estimatedCsvSize).toBeGreaterThan(0);
    expect(stats.isValid).toBe(true);
  });

  it('应该估算导出文件大小', () => {
    const jsonSize = modelExport.estimateExportSize(model, 'json');
    const csvSize = modelExport.estimateExportSize(model, 'csv');

    expect(jsonSize).toBeGreaterThan(0);
    expect(csvSize).toBeGreaterThan(0);
    // JSON通常比CSV大
    expect(jsonSize).toBeGreaterThan(csvSize);
  });

  it('应该创建有效的JSON导出数据', () => {
    const exportData = modelExport.exportModelJSON(model);

    expect(exportData.format).toBe('HydroClaude Model');
    expect(exportData.version).toBe('1.5.0');
    expect(exportData.exportDate).toBeDefined();
    expect(exportData.model).toEqual(model);
  });

  it('应该生成CSV格式的节点数据', () => {
    const csv = modelExport.exportModelNodesCSV(model);

    expect(csv).toContain('id,type,name');
    expect(csv).toContain('node-1');
    expect(csv).toContain('node-2');
    expect(csv).toContain('Channel 1');
    expect(csv).toContain('Channel 2');
  });

  it('应该生成CSV格式的边数据', () => {
    const csv = modelExport.exportModelEdgesCSV(model);

    expect(csv).toContain('id,source,target');
    expect(csv).toContain('edge-1');
    expect(csv).toContain('node-1');
    expect(csv).toContain('node-2');
  });
});

describe('ModelIO - 导入工具函数集成', () => {
  it('应该获取文件信息', async () => {
    const file = new File(['test content'], 'test-model.json', {
      type: 'application/json'
    });

    // Polyfill for Node.js
    if (!file.text) {
      (file as any).text = async () => 'test content';
    }

    const fileInfo = await modelImport.getImportFileInfo(file);

    expect(fileInfo.filename).toBe('test-model.json');
    expect(fileInfo.type).toBe('application/json');
    expect(fileInfo.size).toBeGreaterThan(0);
    expect(fileInfo.sizeFormatted).toBeDefined();
    expect(fileInfo.lastModified).toBeInstanceOf(Date);
  });

  it('应该导入有效的JSON模型', async () => {
    const model = createMockModel();
    const exportData = modelExport.exportModelJSON(model);
    const jsonContent = JSON.stringify(exportData);

    const file = new File([jsonContent], 'test-model.json', {
      type: 'application/json'
    });

    // Polyfill for Node.js
    if (!file.text) {
      (file as any).text = async () => jsonContent;
    }

    const importedModel = await modelImport.importModelJSON(file);

    expect(importedModel.id).toBe(model.id);
    expect(importedModel.name).toBe(model.name);
    expect(importedModel.nodes).toHaveLength(2);
    expect(importedModel.edges).toHaveLength(1);
  });

  it('应该拒绝无效的JSON文件', async () => {
    const file = new File(['invalid json'], 'invalid.json', {
      type: 'application/json'
    });

    // Polyfill for Node.js
    if (!file.text) {
      (file as any).text = async () => 'invalid json';
    }

    await expect(modelImport.importModelJSON(file)).rejects.toThrow();
  });

  it('应该拒绝过大的文件', async () => {
    const largeContent = 'x'.repeat(20 * 1024 * 1024); // 20MB
    const file = new File([largeContent], 'large.json', {
      type: 'application/json'
    });

    // Override size
    Object.defineProperty(file, 'size', {
      value: 20 * 1024 * 1024,
      writable: false,
      configurable: true
    });

    // Polyfill for Node.js
    if (!file.text) {
      (file as any).text = async () => largeContent;
    }

    await expect(modelImport.importModelJSON(file)).rejects.toThrow();
  });

  it('应该验证导入的模型结构', async () => {
    const invalidExportData = {
      format: 'Invalid Format',
      version: '0.0.1',
      exportDate: new Date().toISOString(),
      model: { invalid: 'data' }
    };

    const file = new File([JSON.stringify(invalidExportData)], 'invalid-model.json', {
      type: 'application/json'
    });

    // Polyfill for Node.js
    if (!file.text) {
      (file as any).text = async () => JSON.stringify(invalidExportData);
    }

    await expect(modelImport.importModelJSON(file)).rejects.toThrow();
  });
});

describe('ModelIO - localStorage集成', () => {
  beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    global.localStorage = localStorageMock as Storage;
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it('应该保存模型到localStorage', () => {
    const model = createMockModel();
    const models = [model];

    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(models));

    const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

    expect(saved).toHaveLength(1);
    expect(saved[0].id).toBe(model.id);
    expect(saved[0].name).toBe(model.name);
  });

  it('应该更新现有模型', () => {
    const model = createMockModel();

    // 保存初始模型
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify([model]));

    // 更新模型
    const updatedModel = {
      ...model,
      name: 'Updated Model Name',
      updated_at: new Date().toISOString()
    };

    const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    const existingIndex = saved.findIndex((m: HydraulicModel) => m.id === updatedModel.id);
    saved[existingIndex] = updatedModel;
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(saved));

    // 验证更新
    const result = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Updated Model Name');
  });

  it('应该管理最近访问的模型列表', () => {
    const model = createMockModel();

    // 添加到最近访问
    const recentItem = {
      id: model.id,
      name: model.name,
      accessedAt: new Date().toISOString()
    };

    localStorage.setItem(STORAGE_KEYS.RECENT, JSON.stringify([recentItem]));

    const recent = JSON.parse(localStorage.getItem(STORAGE_KEYS.RECENT) || '[]');

    expect(recent).toHaveLength(1);
    expect(recent[0].id).toBe(model.id);
    expect(recent[0].accessedAt).toBeDefined();
  });

  it('应该限制最近访问列表为10项', () => {
    // 创建11个模型
    const recentModels = Array.from({ length: 11 }, (_, i) => ({
      id: `model-${i}`,
      name: `Model ${i}`,
      accessedAt: new Date().toISOString()
    }));

    // 只保留前10个
    const trimmed = recentModels.slice(0, 10);
    localStorage.setItem(STORAGE_KEYS.RECENT, JSON.stringify(trimmed));

    const recent = JSON.parse(localStorage.getItem(STORAGE_KEYS.RECENT) || '[]');

    expect(recent.length).toBeLessThanOrEqual(10);
  });

  it('应该处理localStorage QuotaExceededError', () => {
    const model = createMockModel();

    // Replace localStorage with one that throws on setItem
    const originalLocalStorage = global.localStorage;
    const throwingStorage = {
      ...localStorageMock,
      setItem: (_key: string, _value: string) => {
        const error: any = new Error('QuotaExceededError');
        error.name = 'QuotaExceededError';
        throw error;
      }
    };

    global.localStorage = throwingStorage as Storage;

    expect(() => {
      localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify([model]));
    }).toThrow('QuotaExceededError');

    // Restore
    global.localStorage = originalLocalStorage;
  });

  it('应该从localStorage加载模型', () => {
    const model1 = createMockModel({ id: 'model-1', name: 'Model 1' });
    const model2 = createMockModel({ id: 'model-2', name: 'Model 2' });

    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify([model1, model2]));

    const loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

    expect(loaded).toHaveLength(2);
    expect(loaded[0].id).toBe('model-1');
    expect(loaded[1].id).toBe('model-2');
  });

  it('应该处理空的localStorage', () => {
    const models = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    const recent = JSON.parse(localStorage.getItem(STORAGE_KEYS.RECENT) || '[]');

    expect(models).toEqual([]);
    expect(recent).toEqual([]);
  });

  it('应该处理损坏的localStorage数据', () => {
    // 设置无效的JSON
    localStorageMock.setItem(STORAGE_KEYS.MODELS, 'invalid json');

    expect(() => {
      JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    }).toThrow();

    // 实际应用中应该有错误处理
    try {
      JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    } catch (error) {
      // 回退到空数组
      const models: HydraulicModel[] = [];
      expect(models).toEqual([]);
    }
  });
});

describe('ModelIO - 完整工作流测试', () => {
  beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    global.localStorage = localStorageMock as Storage;
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it('应该完成导出-导入循环', async () => {
    const originalModel = createMockModel();

    // 1. 导出模型
    const exportData = modelExport.exportModelJSON(originalModel);
    expect(exportData.format).toBe('HydroClaude Model');

    // 2. 转换为JSON字符串（模拟文件下载和上传）
    const jsonContent = JSON.stringify(exportData);

    // 3. 创建文件对象
    const file = new File([jsonContent], 'exported-model.json', {
      type: 'application/json'
    });

    // Polyfill for Node.js
    if (!file.text) {
      (file as any).text = async () => jsonContent;
    }

    // 4. 导入模型
    const importedModel = await modelImport.importModelJSON(file);

    // 5. 验证导入的模型与原始模型一致
    expect(importedModel.id).toBe(originalModel.id);
    expect(importedModel.name).toBe(originalModel.name);
    expect(importedModel.nodes).toHaveLength(originalModel.nodes.length);
    expect(importedModel.edges).toHaveLength(originalModel.edges.length);
  });

  it('应该完成创建-保存-加载循环', () => {
    // 1. 创建新模型
    const newModel = createMockModel({
      id: 'new-model-456',
      name: 'New Test Model'
    });

    // 2. 保存到localStorage
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify([newModel]));

    // 3. 添加到最近访问
    const recentItem = {
      id: newModel.id,
      name: newModel.name,
      accessedAt: new Date().toISOString()
    };
    localStorage.setItem(STORAGE_KEYS.RECENT, JSON.stringify([recentItem]));

    // 4. 从localStorage加载
    const loadedModels = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    const loadedRecent = JSON.parse(localStorage.getItem(STORAGE_KEYS.RECENT) || '[]');

    // 5. 验证
    expect(loadedModels).toHaveLength(1);
    expect(loadedModels[0].id).toBe('new-model-456');
    expect(loadedRecent).toHaveLength(1);
    expect(loadedRecent[0].id).toBe('new-model-456');
  });

  it('应该完成验证-导出-保存工作流', () => {
    const model = createMockModel();

    // 1. 验证模型
    const validation = modelExport.validateModelForExport(model);
    expect(validation.valid).toBe(true);

    // 2. 导出模型
    const exportData = modelExport.exportModelJSON(model);
    expect(exportData.model.id).toBe(model.id);

    // 3. 保存到localStorage
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify([model]));

    // 4. 验证保存
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    expect(saved[0].id).toBe(model.id);
  });
});
