/**
 * Model Export Utilities - Unit Tests
 * 模型导出工具函数单元测试
 *
 * v1.5.0 Feature Testing
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  exportModelJSON,
  exportModelNodesCSV,
  exportModelEdgesCSV,
  sanitizeFilename,
  validateModelForExport,
  estimateExportSize,
  getExportStatistics
} from '../modelExport';
import type { HydraulicModel } from '../../types/model-io';

// ============= Mock Data =============

const createMockModel = (overrides?: Partial<HydraulicModel>): HydraulicModel => ({
  id: 'test-model-123',
  name: 'Test Hydraulic Model',
  description: 'A test model for unit testing',
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
  created_at: '2025-11-11T00:00:00.000Z',
  updated_at: '2025-11-11T12:00:00.000Z',
  version: 1,
  validated: true,
  ...overrides
});

// ============= Test Suites =============

describe('modelExport - exportModelJSON', () => {
  it('应该创建有效的导出数据结构', () => {
    const model = createMockModel();
    const exportData = exportModelJSON(model);

    expect(exportData).toBeDefined();
    expect(exportData.format).toBe('HydroClaude Model');
    expect(exportData.version).toBe('1.5.0');
    expect(exportData.exportDate).toBeDefined();
    expect(exportData.model).toEqual(model);
  });

  it('应该包含元数据（默认）', () => {
    const model = createMockModel({
      metadata: { author: 'Test User', tags: ['test'] }
    });
    const exportData = exportModelJSON(model);

    expect(exportData.model.metadata).toBeDefined();
    expect(exportData.model.metadata).toEqual({
      author: 'Test User',
      tags: ['test']
    });
  });

  it('应该在请求时排除元数据', () => {
    const model = createMockModel({
      metadata: { author: 'Test User' }
    });
    const exportData = exportModelJSON(model, { includeMetadata: false });

    expect(exportData.model.metadata).toBeUndefined();
  });

  it('应该在请求时排除缩略图', () => {
    const model = createMockModel({
      thumbnail: 'data:image/png;base64,iVBORw0KGgo='
    } as any);
    const exportData = exportModelJSON(model, { includeThumbnail: false });

    expect((exportData.model as any).thumbnail).toBeUndefined();
  });

  it('应该生成有效的ISO 8601导出日期', () => {
    const model = createMockModel();
    const exportData = exportModelJSON(model);

    const date = new Date(exportData.exportDate);
    expect(date).toBeInstanceOf(Date);
    expect(date.getTime()).not.toBeNaN();
  });
});

describe('modelExport - exportModelNodesCSV', () => {
  it('应该生成带正确标题的CSV', () => {
    const model = createMockModel();
    const csv = exportModelNodesCSV(model);

    const lines = csv.split('\n');
    expect(lines[0]).toBe('id,type,name,position_x,position_y,width,length,slope,manning_n,n_cells,validated');
  });

  it('应该导出所有节点数据', () => {
    const model = createMockModel();
    const csv = exportModelNodesCSV(model);

    const lines = csv.split('\n');
    expect(lines.length).toBe(3); // header + 2 nodes

    // Check first node
    expect(lines[1]).toContain('node-1');
    expect(lines[1]).toContain('channel');
    expect(lines[1]).toContain('Channel 1');
    expect(lines[1]).toContain('100'); // position_x
    expect(lines[1]).toContain('200'); // position_y
    expect(lines[1]).toContain('5'); // width
    expect(lines[1]).toContain('true'); // validated
  });

  it('应该处理空值字段', () => {
    const model = createMockModel({
      nodes: [
        {
          id: 'node-empty',
          type: 'channel',
          position: { x: 0, y: 0 },
          data: {
            name: 'Empty Node',
            validated: false,
            errors: [],
            warnings: []
          }
        }
      ]
    });
    const csv = exportModelNodesCSV(model);

    const lines = csv.split('\n');
    expect(lines[1]).toContain('node-empty');
    expect(lines[1]).toContain('Empty Node');
    // Empty fields should appear as empty strings
    expect(lines[1].split(',').some(field => field === '')).toBe(true);
  });
});

describe('modelExport - exportModelEdgesCSV', () => {
  it('应该生成带正确标题的CSV', () => {
    const model = createMockModel();
    const csv = exportModelEdgesCSV(model);

    const lines = csv.split('\n');
    expect(lines[0]).toBe('id,source,target,validated,flow_direction');
  });

  it('应该导出所有边数据', () => {
    const model = createMockModel();
    const csv = exportModelEdgesCSV(model);

    const lines = csv.split('\n');
    expect(lines.length).toBe(2); // header + 1 edge

    expect(lines[1]).toContain('edge-1');
    expect(lines[1]).toContain('node-1');
    expect(lines[1]).toContain('node-2');
    expect(lines[1]).toContain('true');
  });

  it('应该处理带流向的边', () => {
    const model = createMockModel({
      edges: [
        {
          id: 'edge-1',
          source: 'node-1',
          target: 'node-2',
          validated: true,
          flow_direction: 'forward'
        } as any
      ]
    });
    const csv = exportModelEdgesCSV(model);

    const lines = csv.split('\n');
    expect(lines[1]).toContain('forward');
  });
});

describe('modelExport - sanitizeFilename', () => {
  it('应该移除无效字符', () => {
    // 点号（.）也会被移除，因为它不在允许字符列表中
    expect(sanitizeFilename('test/file:name*?.txt')).toBe('test_file_name_txt');
    expect(sanitizeFilename('file<>name|.json')).toBe('file_name_json');
  });

  it('应该保留中文字符、字母、数字、下划线和连字符', () => {
    // 中文字符会被保留，但点号会被替换
    expect(sanitizeFilename('水力模型测试.json')).toBe('水力模型测试_json');
    expect(sanitizeFilename('渠道-模型_01.hydro')).toBe('渠道-模型_01_hydro');
    // 纯中文名称
    expect(sanitizeFilename('水力学模型')).toBe('水力学模型');
  });

  it('应该替换多个连续下划线', () => {
    expect(sanitizeFilename('test___file___name')).toBe('test_file_name');
  });

  it('应该限制文件名长度', () => {
    const longName = 'a'.repeat(100);
    const sanitized = sanitizeFilename(longName);
    expect(sanitized.length).toBeLessThanOrEqual(50);
  });

  it('应该保留字母、数字、下划线和连字符', () => {
    expect(sanitizeFilename('test-model_123')).toBe('test-model_123');
    expect(sanitizeFilename('Model_v1-2-3')).toBe('Model_v1-2-3');
  });
});

describe('modelExport - validateModelForExport', () => {
  it('应该验证有效模型', () => {
    const model = createMockModel();
    const result = validateModelForExport(model);

    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('应该检测缺失的模型ID', () => {
    const model = createMockModel({ id: '' });
    const result = validateModelForExport(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model ID is missing');
  });

  it('应该检测缺失的模型名称', () => {
    const model = createMockModel({ name: '' });
    const result = validateModelForExport(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model name is required');
  });

  it('应该检测空白模型名称', () => {
    const model = createMockModel({ name: '   ' });
    const result = validateModelForExport(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model name is required');
  });

  it('应该对空模型发出警告', () => {
    const model = createMockModel({ nodes: [], edges: [] });
    const result = validateModelForExport(model);

    expect(result.valid).toBe(true);
    expect(result.warnings).toContain('Model has no nodes');
  });

  it('应该对大型模型发出警告', () => {
    const largeNodes = Array.from({ length: 1500 }, (_, i) => ({
      id: `node-${i}`,
      type: 'channel',
      position: { x: i, y: i },
      data: { name: `Node ${i}`, validated: true, errors: [], warnings: [] }
    }));
    const model = createMockModel({ nodes: largeNodes });
    const result = validateModelForExport(model);

    expect(result.valid).toBe(true);
    expect(result.warnings.some(w => w.includes('large number of nodes'))).toBe(true);
  });

  it('应该检测无效的节点数组', () => {
    const model = createMockModel({ nodes: null as any });
    const result = validateModelForExport(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model nodes must be an array');
  });

  it('应该检测无效的边数组', () => {
    const model = createMockModel({ edges: 'invalid' as any });
    const result = validateModelForExport(model);

    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Model edges must be an array');
  });
});

describe('modelExport - estimateExportSize', () => {
  it('应该估算JSON导出大小', () => {
    const model = createMockModel();
    const size = estimateExportSize(model, 'json');

    expect(size).toBeGreaterThan(0);
    expect(size).toBeLessThan(10 * 1024); // Should be < 10KB for small model
  });

  it('应该估算CSV导出大小', () => {
    const model = createMockModel();
    const size = estimateExportSize(model, 'csv');

    expect(size).toBeGreaterThan(0);
    expect(size).toBeLessThan(5 * 1024); // Should be < 5KB for small model
  });

  it('大型模型应该有更大的估算大小', () => {
    const smallModel = createMockModel();
    const largeModel = createMockModel({
      nodes: Array.from({ length: 100 }, (_, i) => ({
        id: `node-${i}`,
        type: 'channel',
        position: { x: i * 10, y: i * 10 },
        data: {
          name: `Channel ${i}`,
          width: 5,
          length: 100,
          slope: 0.001,
          manning_n: 0.013,
          n_cells: 50,
          validated: true,
          errors: [],
          warnings: []
        }
      }))
    });

    const smallSize = estimateExportSize(smallModel, 'json');
    const largeSize = estimateExportSize(largeModel, 'json');

    expect(largeSize).toBeGreaterThan(smallSize * 10);
  });
});

describe('modelExport - getExportStatistics', () => {
  it('应该返回完整的导出统计', () => {
    const model = createMockModel();
    const stats = getExportStatistics(model);

    expect(stats).toHaveProperty('nodeCount');
    expect(stats).toHaveProperty('edgeCount');
    expect(stats).toHaveProperty('estimatedJsonSize');
    expect(stats).toHaveProperty('estimatedCsvSize');
    expect(stats).toHaveProperty('hasMetadata');
    expect(stats).toHaveProperty('hasThumbnail');
    expect(stats).toHaveProperty('isValid');
  });

  it('应该正确计算节点和边数量', () => {
    const model = createMockModel();
    const stats = getExportStatistics(model);

    expect(stats.nodeCount).toBe(2);
    expect(stats.edgeCount).toBe(1);
  });

  it('应该检测元数据存在', () => {
    const modelWithMeta = createMockModel({
      metadata: { author: 'Test' }
    });
    const modelWithoutMeta = createMockModel();

    const statsWithMeta = getExportStatistics(modelWithMeta);
    const statsWithoutMeta = getExportStatistics(modelWithoutMeta);

    expect(statsWithMeta.hasMetadata).toBe(true);
    expect(statsWithoutMeta.hasMetadata).toBe(false);
  });

  it('应该检测缩略图存在', () => {
    const modelWithThumb = createMockModel({
      thumbnail: 'data:image/png;base64,abc123'
    } as any);
    const modelWithoutThumb = createMockModel();

    const statsWithThumb = getExportStatistics(modelWithThumb);
    const statsWithoutThumb = getExportStatistics(modelWithoutThumb);

    expect(statsWithThumb.hasThumbnail).toBe(true);
    expect(statsWithoutThumb.hasThumbnail).toBe(false);
  });

  it('应该正确标识有效和无效模型', () => {
    const validModel = createMockModel();
    const invalidModel = createMockModel({ id: '' });

    const validStats = getExportStatistics(validModel);
    const invalidStats = getExportStatistics(invalidModel);

    expect(validStats.isValid).toBe(true);
    expect(invalidStats.isValid).toBe(false);
  });

  it('应该提供合理的大小估算', () => {
    const model = createMockModel();
    const stats = getExportStatistics(model);

    expect(stats.estimatedJsonSize).toBeGreaterThan(0);
    expect(stats.estimatedCsvSize).toBeGreaterThan(0);
    // JSON typically larger than CSV for small models
    expect(stats.estimatedJsonSize).toBeGreaterThan(stats.estimatedCsvSize);
  });
});

// ============= Integration Tests =============

describe('modelExport - 集成测试', () => {
  it('应该正确导出和验证完整工作流', () => {
    const model = createMockModel();

    // 1. 验证模型
    const validation = validateModelForExport(model);
    expect(validation.valid).toBe(true);

    // 2. 获取统计信息
    const stats = getExportStatistics(model);
    expect(stats.isValid).toBe(true);
    expect(stats.nodeCount).toBe(2);

    // 3. 导出为JSON
    const jsonExport = exportModelJSON(model);
    expect(jsonExport.format).toBe('HydroClaude Model');
    expect(jsonExport.model).toEqual(model);

    // 4. 导出为CSV
    const nodesCSV = exportModelNodesCSV(model);
    const edgesCSV = exportModelEdgesCSV(model);
    expect(nodesCSV).toContain('node-1');
    expect(edgesCSV).toContain('edge-1');
  });

  it('应该处理带中文名称的模型', () => {
    const model = createMockModel({
      name: '水力学模型-渠道网络',
      description: '这是一个测试模型'
    });

    const sanitized = sanitizeFilename(model.name);
    expect(sanitized).toContain('水力学模型');
    expect(sanitized).toContain('渠道网络');

    const jsonExport = exportModelJSON(model);
    expect(jsonExport.model.name).toBe('水力学模型-渠道网络');
  });
});
