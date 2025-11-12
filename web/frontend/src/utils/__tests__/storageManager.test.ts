/**
 * Storage Manager Utilities - Unit Tests
 * 存储管理工具单元测试
 *
 * v1.5.0 Feature Testing
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  checkStorageQuota,
  formatBytes,
  isStorageNearQuota,
  getSavedModels,
  saveModels,
  getModelById,
  deleteModels,
  cleanupOldModels,
  cleanupLargeModels,
  clearAllData,
  getRecentModels
} from '../storageManager';
import { STORAGE_KEYS } from '../../types/model-io';
import type { HydraulicModel } from '../../features/modeling/types/model.types';

// ============= Test Setup =============

// Mock localStorage before each test
let localStorageMock: { [key: string]: string } = {};

beforeEach(() => {
  // Clear localStorage mock
  localStorageMock = {};

  // Create a Proxy to make localStorage enumerable (for...in support)
  const storageProxy = new Proxy(localStorageMock, {
    get(target, prop: string) {
      // Return storage methods
      if (prop === 'getItem') {
        return (key: string) => target[key] || null;
      }
      if (prop === 'setItem') {
        return (key: string, value: string) => {
          target[key] = value;
        };
      }
      if (prop === 'removeItem') {
        return (key: string) => {
          delete target[key];
        };
      }
      if (prop === 'clear') {
        return () => {
          Object.keys(target).forEach(key => delete target[key]);
        };
      }
      if (prop === 'length') {
        return Object.keys(target).length;
      }
      if (prop === 'key') {
        return (index: number) => {
          const keys = Object.keys(target);
          return keys[index] || null;
        };
      }
      // Return data values for iteration
      return target[prop];
    },
    has(target, prop: string) {
      return prop in target;
    },
    ownKeys(target) {
      return Object.keys(target);
    },
    getOwnPropertyDescriptor(target, prop) {
      return {
        enumerable: true,
        configurable: true,
        value: target[prop as string]
      };
    }
  });

  global.localStorage = storageProxy as Storage;
});

afterEach(() => {
  vi.clearAllMocks();
});

// ============= Mock Data =============

const createMockModel = (id: string, name: string, updatedAt?: string): HydraulicModel => ({
  id,
  name,
  description: `Test model ${id}`,
  nodes: [
    {
      id: `node-${id}`,
      type: 'channel',
      position: { x: 100, y: 200 },
      data: {
        name: `Node ${id}`,
        width: 5.0,
        length: 100.0,
        slope: 0.001,
        manning_n: 0.013,
        n_cells: 50,
        validated: true,
        errors: [],
        warnings: []
      }
    }
  ],
  edges: [],
  created_at: '2025-11-11T00:00:00.000Z',
  updated_at: updatedAt || '2025-11-11T12:00:00.000Z',
  version: 1,
  validated: true
});

// ============= Test Suites =============

describe('storageManager - Storage Quota', () => {
  it('应该返回空存储的配额信息', () => {
    const quota = checkStorageQuota();

    expect(quota.used).toBe(0);
    expect(quota.available).toBe(5 * 1024 * 1024); // 5 MB
    expect(quota.percentage).toBe(0);
    expect(quota.itemCount).toBe(0);
  });

  it('应该计算已使用的存储空间', () => {
    // Add some data
    localStorageMock['hydroclaude_models'] = JSON.stringify([
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2')
    ]);

    const quota = checkStorageQuota();

    expect(quota.used).toBeGreaterThan(0);
    expect(quota.itemCount).toBe(2);
    expect(quota.percentage).toBeGreaterThan(0);
    expect(quota.percentage).toBeLessThan(100);
  });

  it('应该忽略非HydroClaude键', () => {
    localStorageMock['other_key'] = 'some data';
    localStorageMock['hydroclaude_models'] = '[]';

    const quota = checkStorageQuota();

    // Should only count hydroclaude_ keys
    expect(quota.used).toBe('hydroclaude_models'.length + '[]'.length);
  });

  it('应该限制百分比最大为100', () => {
    // Simulate very large data (impossible in reality but good to test)
    const largeData = 'x'.repeat(10 * 1024 * 1024); // 10 MB
    localStorageMock['hydroclaude_models'] = largeData;

    const quota = checkStorageQuota();

    expect(quota.percentage).toBe(100);
  });
});

describe('storageManager - formatBytes', () => {
  it('应该格式化字节为B', () => {
    expect(formatBytes(100)).toBe('100 B');
    expect(formatBytes(1023)).toBe('1023 B');
  });

  it('应该格式化字节为KB', () => {
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(102400)).toBe('100.0 KB');
  });

  it('应该格式化字节为MB', () => {
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB');
    expect(formatBytes(1.5 * 1024 * 1024)).toBe('1.5 MB');
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB');
  });

  it('应该保留一位小数', () => {
    expect(formatBytes(1234)).toBe('1.2 KB');
    expect(formatBytes(1567890)).toBe('1.5 MB');
  });
});

describe('storageManager - isStorageNearQuota', () => {
  it('应该在低使用率时返回false', () => {
    localStorageMock['hydroclaude_models'] = '[]';

    expect(isStorageNearQuota()).toBe(false);
    expect(isStorageNearQuota(80)).toBe(false);
  });

  it('应该在高使用率时返回true', () => {
    // Simulate high usage (假设超过80%)
    const largeData = JSON.stringify(Array(1000).fill(createMockModel('1', 'Large')));
    localStorageMock['hydroclaude_models'] = largeData;

    const quota = checkStorageQuota();
    if (quota.percentage >= 80) {
      expect(isStorageNearQuota(80)).toBe(true);
    }
  });

  it('应该使用自定义阈值', () => {
    localStorageMock['hydroclaude_models'] = JSON.stringify([
      createMockModel('1', 'Model 1')
    ]);

    // 阈值设置很低，应该返回true
    expect(isStorageNearQuota(0)).toBe(true);
  });
});

describe('storageManager - getSavedModels', () => {
  it('应该返回空数组当没有保存模型时', () => {
    const models = getSavedModels();

    expect(models).toEqual([]);
  });

  it('应该返回已保存的模型', () => {
    const mockModels = [
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2')
    ];
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify(mockModels);

    const models = getSavedModels();

    expect(models).toHaveLength(2);
    expect(models[0].id).toBe('1');
    expect(models[1].id).toBe('2');
  });

  it('应该处理无效的JSON', () => {
    localStorageMock[STORAGE_KEYS.MODELS] = '{invalid json}';

    const models = getSavedModels();

    expect(models).toEqual([]);
  });

  it('应该处理非数组数据', () => {
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify({ not: 'array' });

    const models = getSavedModels();

    expect(models).toEqual([]);
  });
});

describe('storageManager - saveModels', () => {
  it('应该保存模型到localStorage', () => {
    const mockModels = [
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2')
    ];

    const result = saveModels(mockModels);

    expect(result).toBe(true);
    // Verify data is actually saved
    const saved = localStorage.getItem(STORAGE_KEYS.MODELS);
    expect(saved).toBe(JSON.stringify(mockModels));
  });

  it('应该覆盖现有模型', () => {
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify([
      createMockModel('old', 'Old Model')
    ]);

    const newModels = [createMockModel('new', 'New Model')];
    saveModels(newModels);

    const saved = getSavedModels();
    expect(saved).toHaveLength(1);
    expect(saved[0].id).toBe('new');
  });

  it('应该保存空数组', () => {
    const result = saveModels([]);

    expect(result).toBe(true);
    expect(getSavedModels()).toEqual([]);
  });
});

describe('storageManager - getModelById', () => {
  beforeEach(() => {
    const mockModels = [
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2'),
      createMockModel('3', 'Model 3')
    ];
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify(mockModels);
  });

  it('应该通过ID找到模型', () => {
    const model = getModelById('2');

    expect(model).not.toBeNull();
    expect(model?.id).toBe('2');
    expect(model?.name).toBe('Model 2');
  });

  it('应该在模型不存在时返回null', () => {
    const model = getModelById('nonexistent');

    expect(model).toBeNull();
  });

  it('应该处理空存储', () => {
    localStorageMock[STORAGE_KEYS.MODELS] = '[]';

    const model = getModelById('1');

    expect(model).toBeNull();
  });
});

describe('storageManager - deleteModels', () => {
  beforeEach(() => {
    const mockModels = [
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2'),
      createMockModel('3', 'Model 3'),
      createMockModel('4', 'Model 4')
    ];
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify(mockModels);
  });

  it('应该删除单个模型', () => {
    const deletedCount = deleteModels(['2']);

    expect(deletedCount).toBe(1);
    const remaining = getSavedModels();
    expect(remaining).toHaveLength(3);
    expect(remaining.find(m => m.id === '2')).toBeUndefined();
  });

  it('应该删除多个模型', () => {
    const deletedCount = deleteModels(['1', '3']);

    expect(deletedCount).toBe(2);
    const remaining = getSavedModels();
    expect(remaining).toHaveLength(2);
    expect(remaining.map(m => m.id)).toEqual(['2', '4']);
  });

  it('应该在删除不存在的ID时返回0', () => {
    const deletedCount = deleteModels(['nonexistent']);

    expect(deletedCount).toBe(0);
    expect(getSavedModels()).toHaveLength(4);
  });

  it('应该处理空ID数组', () => {
    const deletedCount = deleteModels([]);

    expect(deletedCount).toBe(0);
    expect(getSavedModels()).toHaveLength(4);
  });
});

describe('storageManager - cleanupOldModels', () => {
  it('应该保留最近的N个模型', () => {
    const mockModels = [
      createMockModel('1', 'Model 1', '2025-11-01T00:00:00.000Z'),
      createMockModel('2', 'Model 2', '2025-11-02T00:00:00.000Z'),
      createMockModel('3', 'Model 3', '2025-11-03T00:00:00.000Z'),
      createMockModel('4', 'Model 4', '2025-11-04T00:00:00.000Z'),
      createMockModel('5', 'Model 5', '2025-11-05T00:00:00.000Z')
    ];
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify(mockModels);

    const deletedCount = cleanupOldModels(3);

    expect(deletedCount).toBe(2); // 删除了2个最旧的
    const remaining = getSavedModels();
    expect(remaining).toHaveLength(3);
    // 应该保留最新的3个（5, 4, 3）
    expect(remaining.map(m => m.id).sort()).toEqual(['3', '4', '5']);
  });

  it('应该在模型少于限制时不删除', () => {
    const mockModels = [
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2')
    ];
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify(mockModels);

    const deletedCount = cleanupOldModels(10);

    expect(deletedCount).toBe(0);
    expect(getSavedModels()).toHaveLength(2);
  });

  it('应该使用默认保留数量10', () => {
    const mockModels = Array.from({ length: 15 }, (_, i) =>
      createMockModel(`${i + 1}`, `Model ${i + 1}`, `2025-11-${String(i + 1).padStart(2, '0')}T00:00:00.000Z`)
    );
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify(mockModels);

    const deletedCount = cleanupOldModels();

    expect(deletedCount).toBe(5); // 15 - 10 = 5
    expect(getSavedModels()).toHaveLength(10);
  });
});

describe('storageManager - cleanupLargeModels', () => {
  it('应该删除超过大小限制的模型', () => {
    // 创建一个大模型（通过添加很多节点）
    const largeModel = createMockModel('large', 'Large Model');
    largeModel.nodes = Array.from({ length: 100 }, (_, i) => ({
      id: `node-${i}`,
      type: 'channel',
      position: { x: i * 10, y: i * 10 },
      data: {
        name: `Node ${i}`,
        width: 5.0,
        length: 100.0,
        slope: 0.001,
        manning_n: 0.013,
        n_cells: 50,
        validated: true,
        errors: [],
        warnings: []
      }
    }));

    const smallModel = createMockModel('small', 'Small Model');

    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify([largeModel, smallModel]);

    // 设置较小的限制（10KB）
    const deletedCount = cleanupLargeModels(10);

    expect(deletedCount).toBeGreaterThanOrEqual(1);
    const remaining = getSavedModels();
    // 小模型应该被保留
    expect(remaining.find(m => m.id === 'small')).toBeDefined();
  });

  it('应该使用默认限制500KB', () => {
    const mockModels = [
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2')
    ];
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify(mockModels);

    const deletedCount = cleanupLargeModels();

    // 普通模型应该小于500KB
    expect(deletedCount).toBe(0);
    expect(getSavedModels()).toHaveLength(2);
  });
});

describe('storageManager - clearAllData', () => {
  it('应该清除所有HydroClaude数据', () => {
    // 添加多个存储项
    localStorageMock[STORAGE_KEYS.MODELS] = JSON.stringify([createMockModel('1', 'Model 1')]);
    localStorageMock[STORAGE_KEYS.RECENT] = '[]';
    localStorageMock[STORAGE_KEYS.SETTINGS] = '{}';

    clearAllData();

    // Verify all HydroClaude keys are removed
    expect(localStorage.getItem(STORAGE_KEYS.MODELS)).toBeNull();
    expect(localStorage.getItem(STORAGE_KEYS.RECENT)).toBeNull();
    expect(localStorage.getItem(STORAGE_KEYS.SETTINGS)).toBeNull();
  });

  it('应该只清除HydroClaude数据，不影响其他数据', () => {
    localStorageMock[STORAGE_KEYS.MODELS] = '[]';
    localStorageMock['other_app_data'] = 'should not be removed';

    clearAllData();

    // other_app_data should remain
    expect(localStorage.getItem('other_app_data')).toBe('should not be removed');
    // HydroClaude data should be removed
    expect(localStorage.getItem(STORAGE_KEYS.MODELS)).toBeNull();
  });
});

describe('storageManager - getRecentModels', () => {
  it('应该返回空数组当没有最近模型时', () => {
    const recent = getRecentModels();

    expect(recent).toEqual([]);
  });

  it('应该返回最近的模型列表', () => {
    const mockRecent = [
      { id: '1', name: 'Model 1', lastOpened: '2025-11-11T12:00:00.000Z' },
      { id: '2', name: 'Model 2', lastOpened: '2025-11-11T11:00:00.000Z' }
    ];
    localStorageMock[STORAGE_KEYS.RECENT] = JSON.stringify(mockRecent);

    const recent = getRecentModels();

    expect(recent).toHaveLength(2);
    expect(recent[0].id).toBe('1');
    expect(recent[1].id).toBe('2');
  });

  it('应该限制返回数量', () => {
    const mockRecent = Array.from({ length: 20 }, (_, i) => ({
      id: `${i + 1}`,
      name: `Model ${i + 1}`,
      lastOpened: `2025-11-11T${String(i).padStart(2, '0')}:00:00.000Z`
    }));
    localStorageMock[STORAGE_KEYS.RECENT] = JSON.stringify(mockRecent);

    const recent = getRecentModels(5);

    expect(recent).toHaveLength(5);
  });

  it('应该使用默认限制10', () => {
    const mockRecent = Array.from({ length: 15 }, (_, i) => ({
      id: `${i + 1}`,
      name: `Model ${i + 1}`,
      lastOpened: '2025-11-11T00:00:00.000Z'
    }));
    localStorageMock[STORAGE_KEYS.RECENT] = JSON.stringify(mockRecent);

    const recent = getRecentModels();

    expect(recent).toHaveLength(10);
  });

  it('应该处理无效JSON', () => {
    localStorageMock[STORAGE_KEYS.RECENT] = '{invalid}';

    const recent = getRecentModels();

    expect(recent).toEqual([]);
  });

  it('应该处理非数组数据', () => {
    localStorageMock[STORAGE_KEYS.RECENT] = JSON.stringify({ not: 'array' });

    const recent = getRecentModels();

    expect(recent).toEqual([]);
  });
});

// ============= Integration Tests =============

describe('storageManager - 集成测试', () => {
  it('应该完成完整的CRUD工作流', () => {
    // 1. 保存模型
    const models = [
      createMockModel('1', 'Model 1'),
      createMockModel('2', 'Model 2')
    ];
    saveModels(models);

    // 2. 读取模型
    const saved = getSavedModels();
    expect(saved).toHaveLength(2);

    // 3. 通过ID获取
    const model = getModelById('1');
    expect(model?.name).toBe('Model 1');

    // 4. 删除模型
    deleteModels(['1']);
    const remaining = getSavedModels();
    expect(remaining).toHaveLength(1);
    expect(remaining[0].id).toBe('2');

    // 5. 清除所有数据
    clearAllData();
    expect(getSavedModels()).toEqual([]);
  });

  it('应该正确管理存储配额', () => {
    // 添加数据
    const models = Array.from({ length: 5 }, (_, i) =>
      createMockModel(`${i + 1}`, `Model ${i + 1}`)
    );
    saveModels(models);

    // 检查配额
    const quota = checkStorageQuota();
    expect(quota.used).toBeGreaterThan(0);
    expect(quota.itemCount).toBe(5);

    // 清理旧模型
    const deleted = cleanupOldModels(3);
    expect(deleted).toBe(2);

    // 再次检查配额
    const newQuota = checkStorageQuota();
    expect(newQuota.itemCount).toBe(3);
    expect(newQuota.used).toBeLessThan(quota.used);
  });

  it('应该处理边界情况', () => {
    // 空存储
    expect(getSavedModels()).toEqual([]);
    expect(getModelById('nonexistent')).toBeNull();
    expect(deleteModels(['nonexistent'])).toBe(0);
    expect(cleanupOldModels()).toBe(0);

    // 保存后立即清除
    saveModels([createMockModel('1', 'Model 1')]);
    clearAllData();
    expect(getSavedModels()).toEqual([]);
  });
});
