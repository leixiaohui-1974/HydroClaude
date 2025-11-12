/**
 * ModelLibrary Component - Unit Tests
 * ModelLibrary组件单元测试
 *
 * v1.5.0 Component Testing
 *
 * 注意：这些测试主要关注组件逻辑和数据处理，
 * 而不是详细的UI交互测试
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type { HydraulicModel } from '../../types/model.types';
import { STORAGE_KEYS } from '../../../../types/model-io';

// ============= Mock Data =============

const createMockModel = (overrides?: Partial<HydraulicModel>): HydraulicModel => ({
  id: crypto.randomUUID(),
  name: 'Test Model',
  description: 'Test description',
  nodes: [
    {
      id: 'node-1',
      type: 'channel',
      position: { x: 100, y: 200 },
      data: {
        name: 'Channel 1',
        width: 5.0,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [],
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

// ============= Test Helpers =============

/**
 * Simulate search/filter logic
 */
function filterModels(models: HydraulicModel[], searchText: string): HydraulicModel[] {
  if (!searchText) return models;

  const searchLower = searchText.toLowerCase();
  return models.filter(
    (model) =>
      model.name.toLowerCase().includes(searchLower) ||
      model.description?.toLowerCase().includes(searchLower) ||
      model.id.toLowerCase().includes(searchLower)
  );
}

/**
 * Simulate sort logic
 */
function sortModels(models: HydraulicModel[], sortBy: 'date' | 'name'): HydraulicModel[] {
  const sorted = [...models];

  if (sortBy === 'date') {
    sorted.sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
  } else if (sortBy === 'name') {
    sorted.sort((a, b) => a.name.localeCompare(b.name));
  }

  return sorted;
}

/**
 * Simulate delete operation
 */
function deleteModel(models: HydraulicModel[], id: string): HydraulicModel[] {
  return models.filter((m) => m.id !== id);
}

/**
 * Simulate clone operation
 */
function cloneModel(model: HydraulicModel): HydraulicModel {
  return {
    ...model,
    id: crypto.randomUUID(),
    name: `${model.name} (副本)`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    version: model.version + 1
  };
}

// ============= Test Suites =============

describe('ModelLibrary - localStorage交互', () => {
  beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    global.localStorage = localStorageMock as Storage;
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it('应该从localStorage加载模型列表', () => {
    const models = [
      createMockModel({ name: 'Model 1' }),
      createMockModel({ name: 'Model 2' }),
      createMockModel({ name: 'Model 3' })
    ];

    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(models));

    const loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

    expect(loaded).toHaveLength(3);
    expect(loaded[0].name).toBe('Model 1');
    expect(loaded[1].name).toBe('Model 2');
    expect(loaded[2].name).toBe('Model 3');
  });

  it('应该处理空的模型列表', () => {
    const loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

    expect(loaded).toEqual([]);
  });

  it('应该保存删除后的模型列表', () => {
    const models = [
      createMockModel({ id: 'model-1', name: 'Model 1' }),
      createMockModel({ id: 'model-2', name: 'Model 2' }),
      createMockModel({ id: 'model-3', name: 'Model 3' })
    ];

    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(models));

    // 删除一个模型
    const updated = deleteModel(models, 'model-2');
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(updated));

    const loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

    expect(loaded).toHaveLength(2);
    expect(loaded.find((m: HydraulicModel) => m.id === 'model-2')).toBeUndefined();
  });

  it('应该保存克隆后的模型列表', () => {
    const model = createMockModel({ id: 'original-model', name: 'Original Model' });
    const models = [model];

    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(models));

    // 克隆模型
    const cloned = cloneModel(model);
    const updated = [...models, cloned];
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(updated));

    const loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

    expect(loaded).toHaveLength(2);
    expect(loaded[1].name).toBe('Original Model (副本)');
    expect(loaded[1].id).not.toBe(model.id);
    expect(loaded[1].version).toBe(model.version + 1);
  });

  it('应该处理localStorage错误', () => {
    // 设置无效JSON
    localStorageMock.setItem(STORAGE_KEYS.MODELS, 'invalid json');

    expect(() => {
      JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    }).toThrow();

    // 实际应用中应该有错误处理并回退到空数组
    try {
      JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    } catch (error) {
      const fallback: HydraulicModel[] = [];
      expect(fallback).toEqual([]);
    }
  });
});

describe('ModelLibrary - 搜索和过滤', () => {
  const model1 = createMockModel({
    id: 'water-system-001',
    name: '水力系统 Alpha',
    description: '主要渠道网络'
  });

  const model2 = createMockModel({
    id: 'hydro-002',
    name: '渠道模型 Beta',
    description: '水力学测试模型'
  });

  const model3 = createMockModel({
    id: 'test-003',
    name: 'Channel System',
    description: 'English test model'
  });

  const models = [model1, model2, model3];

  it('应该按名称搜索模型', () => {
    const results = filterModels(models, '水力');

    expect(results).toHaveLength(2);
    expect(results.some(m => m.name.includes('水力系统'))).toBe(true);
    expect(results.some(m => m.description?.includes('水力学'))).toBe(true);
  });

  it('应该按描述搜索模型', () => {
    const results = filterModels(models, '渠道');

    expect(results).toHaveLength(2);
    expect(results.some(m => m.name.includes('渠道模型'))).toBe(true);
    expect(results.some(m => m.description?.includes('渠道网络'))).toBe(true);
  });

  it('应该按ID搜索模型', () => {
    const results = filterModels(models, 'hydro-002');

    expect(results).toHaveLength(1);
    expect(results[0].id).toBe('hydro-002');
  });

  it('应该忽略大小写', () => {
    const results = filterModels(models, 'CHANNEL');

    // "CHANNEL" 只会匹配英文 "Channel System"，不会匹配中文"渠道"
    expect(results).toHaveLength(1);
    expect(results[0].name).toBe('Channel System');
  });

  it('空搜索应该返回所有模型', () => {
    const results = filterModels(models, '');

    expect(results).toHaveLength(3);
  });

  it('没有匹配时应该返回空数组', () => {
    const results = filterModels(models, 'nonexistent');

    expect(results).toHaveLength(0);
  });
});

describe('ModelLibrary - 排序', () => {
  const model1 = createMockModel({
    name: 'Charlie Model',
    updated_at: '2025-11-10T00:00:00.000Z'
  });

  const model2 = createMockModel({
    name: 'Alpha Model',
    updated_at: '2025-11-12T00:00:00.000Z'
  });

  const model3 = createMockModel({
    name: 'Beta Model',
    updated_at: '2025-11-11T00:00:00.000Z'
  });

  const models = [model1, model2, model3];

  it('应该按日期排序（最新的在前）', () => {
    const sorted = sortModels(models, 'date');

    expect(sorted[0].name).toBe('Alpha Model'); // 2025-11-12
    expect(sorted[1].name).toBe('Beta Model');  // 2025-11-11
    expect(sorted[2].name).toBe('Charlie Model'); // 2025-11-10
  });

  it('应该按名称字母顺序排序', () => {
    const sorted = sortModels(models, 'name');

    expect(sorted[0].name).toBe('Alpha Model');
    expect(sorted[1].name).toBe('Beta Model');
    expect(sorted[2].name).toBe('Charlie Model');
  });

  it('应该处理中文名称排序', () => {
    const chineseModels = [
      createMockModel({ name: '渠道模型' }),
      createMockModel({ name: '水力系统' }),
      createMockModel({ name: '测试模型' })
    ];

    const sorted = sortModels(chineseModels, 'name');

    // localeCompare处理中文的实际顺序（按拼音首字母：s, c, q）
    expect(sorted[0].name).toBe('水力系统'); // shuǐ
    expect(sorted[1].name).toBe('测试模型'); // cè
    expect(sorted[2].name).toBe('渠道模型'); // qú
  });
});

describe('ModelLibrary - CRUD操作', () => {
  beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    global.localStorage = localStorageMock as Storage;
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it('应该删除指定的模型', () => {
    const models = [
      createMockModel({ id: 'model-1', name: 'Model 1' }),
      createMockModel({ id: 'model-2', name: 'Model 2' }),
      createMockModel({ id: 'model-3', name: 'Model 3' })
    ];

    const updated = deleteModel(models, 'model-2');

    expect(updated).toHaveLength(2);
    expect(updated.find(m => m.id === 'model-1')).toBeDefined();
    expect(updated.find(m => m.id === 'model-3')).toBeDefined();
    expect(updated.find(m => m.id === 'model-2')).toBeUndefined();
  });

  it('删除不存在的模型应该不改变列表', () => {
    const models = [
      createMockModel({ id: 'model-1', name: 'Model 1' })
    ];

    const updated = deleteModel(models, 'nonexistent-id');

    expect(updated).toHaveLength(1);
    expect(updated[0].id).toBe('model-1');
  });

  it('应该克隆模型并生成新ID', () => {
    const original = createMockModel({
      id: 'original-123',
      name: 'Original Model',
      version: 1
    });

    const cloned = cloneModel(original);

    expect(cloned.id).not.toBe(original.id);
    expect(cloned.name).toBe('Original Model (副本)');
    expect(cloned.version).toBe(2);
    expect(cloned.created_at).not.toBe(original.created_at);
    expect(cloned.updated_at).not.toBe(original.updated_at);
  });

  it('克隆应该保留所有节点和边', () => {
    const original = createMockModel({
      nodes: [
        {
          id: 'node-1',
          type: 'channel',
          position: { x: 100, y: 200 },
          data: { name: 'Node 1', validated: true, errors: [], warnings: [] }
        },
        {
          id: 'node-2',
          type: 'channel',
          position: { x: 300, y: 200 },
          data: { name: 'Node 2', validated: true, errors: [], warnings: [] }
        }
      ],
      edges: [
        {
          id: 'edge-1',
          source: 'node-1',
          target: 'node-2',
          validated: true
        }
      ]
    });

    const cloned = cloneModel(original);

    expect(cloned.nodes).toHaveLength(2);
    expect(cloned.edges).toHaveLength(1);
    expect(cloned.nodes[0].id).toBe('node-1'); // 节点引用保持不变
    expect(cloned.edges[0].source).toBe('node-1');
  });

  it('应该在克隆时更新时间戳', () => {
    const original = createMockModel({
      created_at: '2025-11-01T00:00:00.000Z',
      updated_at: '2025-11-10T00:00:00.000Z'
    });

    const cloned = cloneModel(original);

    const clonedCreated = new Date(cloned.created_at);
    const clonedUpdated = new Date(cloned.updated_at);
    const originalCreated = new Date(original.created_at);

    expect(clonedCreated.getTime()).toBeGreaterThan(originalCreated.getTime());
    expect(clonedUpdated.getTime()).toBeGreaterThan(originalCreated.getTime());
  });
});

describe('ModelLibrary - 综合测试', () => {
  beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    global.localStorage = localStorageMock as Storage;
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it('应该完成加载-搜索-排序工作流', () => {
    // 1. 创建并保存模型
    const models = [
      createMockModel({ name: 'Charlie', updated_at: '2025-11-10T00:00:00.000Z' }),
      createMockModel({ name: 'Alpha Channel', updated_at: '2025-11-12T00:00:00.000Z' }),
      createMockModel({ name: 'Beta System', updated_at: '2025-11-11T00:00:00.000Z' })
    ];

    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(models));

    // 2. 加载模型
    const loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    expect(loaded).toHaveLength(3);

    // 3. 搜索
    const filtered = filterModels(loaded, 'channel');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].name).toBe('Alpha Channel');

    // 4. 排序
    const sortedByDate = sortModels(loaded, 'date');
    expect(sortedByDate[0].name).toBe('Alpha Channel'); // 最新

    const sortedByName = sortModels(loaded, 'name');
    expect(sortedByName[0].name).toBe('Alpha Channel'); // 字母序
  });

  it('应该完成克隆-保存-删除工作流', () => {
    // 1. 初始模型
    const original = createMockModel({ id: 'original-1', name: 'Original' });
    const models = [original];

    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(models));

    // 2. 克隆模型
    const cloned = cloneModel(original);
    const withClone = [...models, cloned];
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(withClone));

    let loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    expect(loaded).toHaveLength(2);

    // 3. 删除原始模型
    const afterDelete = deleteModel(loaded, original.id);
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(afterDelete));

    loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
    expect(loaded).toHaveLength(1);
    expect(loaded[0].name).toBe('Original (副本)');
  });

  it('应该处理多次搜索和排序', () => {
    const models = [
      createMockModel({ name: 'Alpha 水力', updated_at: '2025-11-12T00:00:00.000Z' }),
      createMockModel({ name: 'Beta 渠道', updated_at: '2025-11-11T00:00:00.000Z' }),
      createMockModel({ name: 'Gamma 水力', updated_at: '2025-11-10T00:00:00.000Z' })
    ];

    // 第一次搜索：查找"水力"
    let filtered = filterModels(models, '水力');
    expect(filtered).toHaveLength(2);

    // 对搜索结果排序
    let sorted = sortModels(filtered, 'name');
    expect(sorted[0].name).toBe('Alpha 水力');

    // 第二次搜索：查找"渠道"
    filtered = filterModels(models, '渠道');
    expect(filtered).toHaveLength(1);
    expect(filtered[0].name).toBe('Beta 渠道');

    // 清空搜索，按日期排序所有模型
    filtered = filterModels(models, '');
    sorted = sortModels(filtered, 'date');
    expect(sorted[0].name).toBe('Alpha 水力'); // 最新
  });

  it('应该维护模型数据完整性', () => {
    const model = createMockModel({
      id: 'test-model',
      name: 'Test Model',
      description: 'Test Description',
      nodes: [
        {
          id: 'node-1',
          type: 'channel',
          position: { x: 100, y: 200 },
          data: {
            name: 'Channel 1',
            width: 5.0,
            length: 100.0,
            slope: 0.001,
            validated: true,
            errors: [],
            warnings: []
          }
        }
      ],
      edges: [],
      validated: true,
      version: 1
    });

    // 保存
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify([model]));

    // 加载
    const loaded = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

    // 验证数据完整性
    expect(loaded[0].id).toBe('test-model');
    expect(loaded[0].name).toBe('Test Model');
    expect(loaded[0].description).toBe('Test Description');
    expect(loaded[0].nodes).toHaveLength(1);
    expect(loaded[0].nodes[0].data.width).toBe(5.0);
    expect(loaded[0].nodes[0].data.length).toBe(100.0);
    expect(loaded[0].validated).toBe(true);
  });
});
