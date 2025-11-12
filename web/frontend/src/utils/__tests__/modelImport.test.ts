/**
 * Model Import Utilities - Unit Tests
 * 模型导入工具函数单元测试
 *
 * v1.5.0 Feature Testing
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  importModelJSON,
  validateImportedModel,
  importModelCSV
} from '../modelImport';
import { IOErrorType } from '../../types/model-io';
import type { HydraulicModel, ModelExportData } from '../../types/model-io';

// ============= Mock Data =============

const createMockModel = (): HydraulicModel => ({
  id: 'test-model-456',
  name: 'Test Import Model',
  description: 'A test model for import testing',
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
        manning_n: 0.013,
        n_cells: 50,
        validated: true,
        errors: [],
        warnings: []
      }
    },
    {
      id: 'node-2',
      type: 'channel',
      position: { x: 300, y: 200 },
      data: {
        name: 'Channel 2',
        width: 3.0,
        length: 50.0,
        slope: 0.002,
        manning_n: 0.015,
        n_cells: 25,
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
  created_at: '2025-11-10T00:00:00.000Z',
  updated_at: '2025-11-10T12:00:00.000Z',
  version: 1,
  validated: true
});

const createMockExportData = (model?: Partial<HydraulicModel>): ModelExportData => ({
  format: 'HydroClaude Model',
  version: '1.5.0',
  exportDate: '2025-11-11T00:00:00.000Z',
  model: { ...createMockModel(), ...model }
});

const createMockFile = (content: string, size?: number): File => {
  const blob = new Blob([content], { type: 'application/json' });
  const file = new File([blob], 'test-model.json', { type: 'application/json' });

  // Polyfill for Node.js environment - add text() method
  if (!file.text) {
    (file as any).text = async () => content;
  }

  // Override size if specified (for testing file size limits)
  if (size !== undefined) {
    Object.defineProperty(file, 'size', {
      value: size,
      writable: false,
      configurable: true
    });
  }

  return file;
};

// ============= Test Suites =============

describe('modelImport - importModelJSON', () => {
  it('应该成功导入有效的JSON模型文件', async () => {
    const exportData = createMockExportData();
    const file = createMockFile(JSON.stringify(exportData));

    const result = await importModelJSON(file);

    expect(result).toBeDefined();
    expect(result.id).toBe('test-model-456');
    expect(result.name).toBe('Test Import Model');
    expect(result.nodes).toHaveLength(2); // Updated: now has 2 nodes
    expect(result.edges).toHaveLength(1);
  });

  it('应该更新imported_at时间戳', async () => {
    const exportData = createMockExportData();
    const file = createMockFile(JSON.stringify(exportData));

    const beforeImport = new Date().toISOString();
    const result = await importModelJSON(file);
    const afterImport = new Date().toISOString();

    expect(result.updated_at).toBeDefined();
    expect(result.updated_at >= beforeImport).toBe(true);
    expect(result.updated_at <= afterImport).toBe(true);
  });

  it('应该拒绝过大的文件（>10MB）', async () => {
    const exportData = createMockExportData();
    const file = createMockFile(JSON.stringify(exportData), 11 * 1024 * 1024);

    await expect(importModelJSON(file)).rejects.toMatchObject({
      type: IOErrorType.FILE_TOO_LARGE,
      message: expect.stringContaining('exceeds limit')
    });
  });

  it('应该拒绝无效的JSON', async () => {
    const file = createMockFile('{invalid json}');

    await expect(importModelJSON(file)).rejects.toMatchObject({
      type: IOErrorType.PARSE_ERROR,
      message: expect.stringContaining('parse JSON')
    });
  });

  it('应该拒绝错误的文件格式', async () => {
    const wrongFormat = {
      someOtherFormat: true,
      data: {}
    };
    const file = createMockFile(JSON.stringify(wrongFormat));

    await expect(importModelJSON(file)).rejects.toMatchObject({
      type: IOErrorType.INVALID_FORMAT,
      message: expect.stringContaining('Invalid file format')
    });
  });

  it('应该拒绝不兼容的版本', async () => {
    const exportData = createMockExportData();
    exportData.version = '2.0.0'; // 主版本号不同
    const file = createMockFile(JSON.stringify(exportData));

    await expect(importModelJSON(file)).rejects.toMatchObject({
      type: IOErrorType.UNSUPPORTED_VERSION,
      message: expect.stringContaining('not compatible')
    });
  });

  it('应该拒绝验证失败的模型', async () => {
    const invalidModel = createMockModel();
    invalidModel.id = ''; // 缺失ID
    const exportData = createMockExportData(invalidModel);
    const file = createMockFile(JSON.stringify(exportData));

    await expect(importModelJSON(file)).rejects.toMatchObject({
      type: IOErrorType.VALIDATION_FAILED,
      message: expect.stringContaining('validation failed')
    });
  });

  it('应该接受v1.x.x的所有次版本', async () => {
    const versions = ['1.0.0', '1.4.2', '1.5.0', '1.9.9'];

    for (const version of versions) {
      const exportData = createMockExportData();
      exportData.version = version;
      const file = createMockFile(JSON.stringify(exportData));

      const result = await importModelJSON(file);
      expect(result).toBeDefined();
    }
  });

  it('应该处理带元数据的模型', async () => {
    const model = createMockModel();
    model.metadata = {
      author: 'Test Author',
      tags: ['test', 'import']
    };
    const exportData = createMockExportData(model);
    const file = createMockFile(JSON.stringify(exportData));

    const result = await importModelJSON(file);

    expect(result.metadata).toBeDefined();
    expect(result.metadata.author).toBe('Test Author');
    expect(result.metadata.tags).toEqual(['test', 'import']);
  });

  it('应该处理中文内容', async () => {
    const model = createMockModel();
    model.name = '水力学模型';
    model.description = '这是一个测试模型';
    const exportData = createMockExportData(model);
    const file = createMockFile(JSON.stringify(exportData));

    const result = await importModelJSON(file);

    expect(result.name).toBe('水力学模型');
    expect(result.description).toBe('这是一个测试模型');
  });
});

describe('modelImport - validateImportedModel', () => {
  it('应该验证有效的模型', () => {
    const model = createMockModel();
    const result = validateImportedModel(model);

    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
    expect(result.isCompatible).toBe(true);
  });

  it('应该检测缺失的ID', () => {
    const model = createMockModel();
    delete (model as any).id;
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model ID is missing or invalid');
  });

  it('应该检测无效的ID类型', () => {
    const model = createMockModel();
    (model as any).id = 123; // 数字而不是字符串
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model ID is missing or invalid');
  });

  it('应该检测缺失的名称', () => {
    const model = createMockModel();
    delete (model as any).name;
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model name is missing or invalid');
  });

  it('应该检测无效的名称类型', () => {
    const model = createMockModel();
    (model as any).name = null;
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model name is missing or invalid');
  });

  it('应该检测无效的nodes数组', () => {
    const model = createMockModel();
    (model as any).nodes = 'not an array';
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model nodes must be an array');
  });

  it('应该检测无效的edges数组', () => {
    const model = createMockModel();
    (model as any).edges = { invalid: true };
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model edges must be an array');
  });

  it('应该对空模型发出警告', () => {
    const model = createMockModel();
    model.nodes = [];
    model.edges = [];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(true);
    expect(result.warnings).toContain('Model has no nodes');
  });

  it('应该对大型模型发出警告', () => {
    const model = createMockModel();
    model.nodes = Array.from({ length: 1200 }, (_, i) => ({
      id: `node-${i}`,
      type: 'channel',
      position: { x: i, y: i },
      data: { name: `Node ${i}`, validated: true, errors: [], warnings: [] }
    }));
    const result = validateImportedModel(model);

    expect(result.valid).toBe(true);
    expect(result.warnings.some(w => w.includes('large number of nodes'))).toBe(true);
  });

  it('应该验证节点结构', () => {
    const model = createMockModel();
    model.nodes = [
      { id: '', type: 'channel', position: { x: 0, y: 0 }, data: {} } as any
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('missing ID'))).toBe(true);
  });

  it('应该验证节点类型', () => {
    const model = createMockModel();
    model.nodes = [
      { id: 'node-1', type: '', position: { x: 0, y: 0 }, data: {} } as any
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('missing type'))).toBe(true);
  });

  it('应该验证节点位置', () => {
    const model = createMockModel();
    model.nodes = [
      { id: 'node-1', type: 'channel', position: { x: 'invalid', y: 0 }, data: {} } as any
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('invalid position'))).toBe(true);
  });

  it('应该验证节点data存在', () => {
    const model = createMockModel();
    model.nodes = [
      { id: 'node-1', type: 'channel', position: { x: 0, y: 0 } } as any
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('missing data'))).toBe(true);
  });

  it('应该验证边结构', () => {
    const model = createMockModel();
    model.edges = [
      { id: '', source: 'node-1', target: 'node-2' } as any
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('Edge') && e.includes('missing ID'))).toBe(true);
  });

  it('应该验证边的source和target', () => {
    const model = createMockModel();
    model.edges = [
      { id: 'edge-1', source: '', target: 'node-2' } as any
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('missing source'))).toBe(true);
  });

  it('应该验证source节点存在', () => {
    const model = createMockModel();
    model.edges = [
      { id: 'edge-1', source: 'non-existent', target: 'node-1', validated: true }
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('source node') && e.includes('not found'))).toBe(true);
  });

  it('应该验证target节点存在', () => {
    const model = createMockModel();
    model.edges = [
      { id: 'edge-1', source: 'node-1', target: 'non-existent', validated: true }
    ];
    const result = validateImportedModel(model);

    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.includes('target node') && e.includes('not found'))).toBe(true);
  });

  it('应该对无效的时间戳发出警告', () => {
    const model = createMockModel();
    (model as any).created_at = 'invalid date';
    const result = validateImportedModel(model);

    expect(result.valid).toBe(true);
    expect(result.warnings).toContain('Invalid created_at timestamp');
  });

  it('应该返回模型版本', () => {
    const model = createMockModel();
    model.version = 5;
    const result = validateImportedModel(model);

    expect(result.modelVersion).toBe('5');
  });
});

describe('modelImport - importModelCSV', () => {
  const createCSVFile = (content: string, filename: string): File => {
    const file = new File([content], filename, { type: 'text/csv' });
    // Polyfill for Node.js environment
    if (!file.text) {
      (file as any).text = async () => content;
    }
    return file;
  };

  it('应该从CSV文件导入模型', async () => {
    const nodesCSV = `id,type,name,position_x,position_y,width,length,slope,manning_n,n_cells,validated
node-1,channel,Channel 1,100,200,5.0,100.0,0.001,0.013,50,true
node-2,channel,Channel 2,300,200,3.0,50.0,0.002,0.015,25,true`;

    const edgesCSV = `id,source,target,validated,flow_direction
edge-1,node-1,node-2,true,forward`;

    const nodesFile = createCSVFile(nodesCSV, 'nodes.csv');
    const edgesFile = createCSVFile(edgesCSV, 'edges.csv');

    const result = await importModelCSV(nodesFile, edgesFile);

    expect(result).toBeDefined();
    expect(result.nodes).toHaveLength(2);
    expect(result.edges).toHaveLength(1);
    expect(result.name).toBe('Imported Model');
    expect(result.validated).toBe(false);
  });

  it('应该正确解析节点数据', async () => {
    const nodesCSV = `id,type,name,position_x,position_y,width,length,slope,manning_n,n_cells,validated
node-test,channel,Test Channel,150,250,4.5,80.0,0.0015,0.014,40,true`;

    // 边CSV需要至少一个数据行（即使是空边）
    const edgesCSV = `id,source,target,validated,flow_direction
edge-empty,node-test,node-test,false,`;

    const nodesFile = createCSVFile(nodesCSV, 'nodes.csv');
    const edgesFile = createCSVFile(edgesCSV, 'edges.csv');

    const result = await importModelCSV(nodesFile, edgesFile);

    expect(result.nodes[0].id).toBe('node-test');
    expect(result.nodes[0].type).toBe('channel');
    expect(result.nodes[0].data.name).toBe('Test Channel');
    expect(result.nodes[0].position.x).toBe(150);
    expect(result.nodes[0].position.y).toBe(250);
    expect(result.nodes[0].data.width).toBe(4.5);
    expect(result.nodes[0].data.validated).toBe(true);
  });

  it('应该处理空值字段', async () => {
    const nodesCSV = `id,type,name,position_x,position_y,width,length,slope,manning_n,n_cells,validated
node-1,channel,Empty Node,0,0,,,,,false`;

    // 边CSV需要至少一个数据行
    const edgesCSV = `id,source,target,validated,flow_direction
edge-empty,node-1,node-1,false,`;

    const nodesFile = createCSVFile(nodesCSV, 'nodes.csv');
    const edgesFile = createCSVFile(edgesCSV, 'edges.csv');

    const result = await importModelCSV(nodesFile, edgesFile);

    expect(result.nodes[0].data.width).toBeUndefined();
    expect(result.nodes[0].data.length).toBeUndefined();
    expect(result.nodes[0].data.slope).toBeUndefined();
  });

  it('应该拒绝缺少标题行的CSV', async () => {
    const nodesCSV = ''; // 空文件
    const edgesCSV = `id,source,target,validated,flow_direction`;

    const nodesFile = createCSVFile(nodesCSV, 'nodes.csv');
    const edgesFile = createCSVFile(edgesCSV, 'edges.csv');

    await expect(importModelCSV(nodesFile, edgesFile)).rejects.toMatchObject({
      type: IOErrorType.PARSE_ERROR,
      message: expect.stringContaining('CSV import failed')
    });
  });
});

// ============= Integration Tests =============

describe('modelImport - 集成测试', () => {
  it('应该完成完整的导入-验证工作流', async () => {
    const model = createMockModel();
    const exportData = createMockExportData(model);
    const file = createMockFile(JSON.stringify(exportData));

    // 1. 导入模型
    const imported = await importModelJSON(file);

    // 2. 验证导入的模型
    const validation = validateImportedModel(imported);

    expect(imported.id).toBe(model.id);
    expect(imported.name).toBe(model.name);
    expect(validation.valid).toBe(true);
    expect(validation.errors).toHaveLength(0);
  });

  it('应该拒绝并提供详细错误信息', async () => {
    const invalidModel = createMockModel();
    invalidModel.nodes = [];
    (invalidModel as any).edges = 'invalid';
    delete (invalidModel as any).id;

    const validation = validateImportedModel(invalidModel);

    expect(validation.valid).toBe(false);
    expect(validation.errors.length).toBeGreaterThan(1);
    expect(validation.errors).toContain('Model ID is missing or invalid');
    expect(validation.errors).toContain('Model edges must be an array');
  });

  it('应该处理真实世界的复杂模型', async () => {
    const complexModel = createMockModel();
    complexModel.nodes = Array.from({ length: 20 }, (_, i) => ({
      id: `node-${i}`,
      type: i % 2 === 0 ? 'channel' : 'junction',
      position: { x: i * 100, y: Math.sin(i) * 100 },
      data: {
        name: `Element ${i}`,
        width: 3 + i * 0.5,
        length: 50 + i * 10,
        slope: 0.001 + i * 0.0001,
        manning_n: 0.013,
        n_cells: 25 + i * 5,
        validated: i % 3 === 0,
        errors: [],
        warnings: []
      }
    }));

    complexModel.edges = Array.from({ length: 19 }, (_, i) => ({
      id: `edge-${i}`,
      source: `node-${i}`,
      target: `node-${i + 1}`,
      validated: i % 2 === 0
    }));

    const exportData = createMockExportData(complexModel);
    const file = createMockFile(JSON.stringify(exportData));

    const imported = await importModelJSON(file);
    const validation = validateImportedModel(imported);

    expect(imported.nodes).toHaveLength(20);
    expect(imported.edges).toHaveLength(19);
    expect(validation.valid).toBe(true);
  });
});
