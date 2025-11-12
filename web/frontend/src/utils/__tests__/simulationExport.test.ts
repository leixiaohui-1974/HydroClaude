/**
 * Unit Tests for Simulation Export Utilities
 * 仿真结果导出工具函数单元测试
 *
 * v1.5.0 Feature: Results Export
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import type { SimulationResultResponse } from '@/services/api';
import {
  generateExportFilename,
  validateExportOptions,
  getExportStatistics,
  exportTimeSeriesCSV,
  exportSpatialProfilesCSV,
  exportMetricsCSV,
  csvDataToString,
  sanitizeFilename
} from '../simulationExport';
import type {
  SimulationExportOptions,
  ExportValidationResult,
  ExportStatistics
} from '@/types/simulation-export';

/**
 * Mock simulation result for testing
 */
const createMockResult = (): SimulationResultResponse => ({
  task_id: 'test-task-123',
  status: 'completed' as const,
  timestamp: '2025-01-15T10:30:00Z',
  duration: 1.234,
  time: [0, 1, 2, 3, 4], // 5 time steps
  x: [0, 10, 20, 30], // 4 spatial points
  h: [
    [1.0, 1.1, 1.2, 1.3],
    [1.1, 1.2, 1.3, 1.4],
    [1.2, 1.3, 1.4, 1.5],
    [1.3, 1.4, 1.5, 1.6],
    [1.4, 1.5, 1.6, 1.7]
  ],
  Q: [
    [10.0, 10.5, 11.0, 11.5],
    [10.1, 10.6, 11.1, 11.6],
    [10.2, 10.7, 11.2, 11.7],
    [10.3, 10.8, 11.3, 11.8],
    [10.4, 10.9, 11.4, 11.9]
  ],
  V: [
    [0.5, 0.6, 0.7, 0.8],
    [0.51, 0.61, 0.71, 0.81],
    [0.52, 0.62, 0.72, 0.82],
    [0.53, 0.63, 0.73, 0.83],
    [0.54, 0.64, 0.74, 0.84]
  ],
  metrics: {
    max_depth: 1.7,
    min_depth: 0.5,
    max_velocity: 0.84,
    max_discharge: 11.9,
    max_froude: 0.23,
    total_iterations: 100,
    mean_depth_final: 1.5,
    mean_discharge_final: 11.0,
    mass_conservation_error: 1e-8,
    converged: true
  }
});

describe('simulationExport - Utility Functions', () => {
  describe('sanitizeFilename', () => {
    it('should remove invalid characters', () => {
      expect(sanitizeFilename('file/with\\invalid:chars*')).not.toContain('/');
      expect(sanitizeFilename('file/with\\invalid:chars*')).not.toContain('\\');
      expect(sanitizeFilename('file/with\\invalid:chars*')).not.toContain(':');
      expect(sanitizeFilename('file/with\\invalid:chars*')).not.toContain('*');
    });

    it('should allow normal characters', () => {
      const clean = sanitizeFilename('normal_file-name.123');
      expect(clean).toContain('normal');
      expect(clean).toContain('file');
      expect(clean).toContain('name');
    });

    it('should handle empty string', () => {
      const result = sanitizeFilename('');
      expect(typeof result).toBe('string');
    });
  });

  describe('generateExportFilename', () => {
    const result = createMockResult();

    it('should generate CSV filename for timeseries', () => {
      const filename = generateExportFilename(result, 'csv', 'timeseries');
      expect(filename).toMatch(/^hydroclaude_results_test-tas_timeseries_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.csv$/);
      expect(filename).toContain('timeseries');
    });

    it('should generate Excel filename for all data', () => {
      const filename = generateExportFilename(result, 'excel', 'all');
      expect(filename).toMatch(/^hydroclaude_results_test-tas_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.xlsx$/);
      expect(filename).toContain('.xlsx');
    });

    it('should generate JSON filename for spatial', () => {
      const filename = generateExportFilename(result, 'json', 'spatial');
      expect(filename).toMatch(/^hydroclaude_results_test-tas_spatial_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.json$/);
      expect(filename).toContain('spatial');
    });

    it('should generate filename for metrics', () => {
      const filename = generateExportFilename(result, 'csv', 'metrics');
      expect(filename).toMatch(/^hydroclaude_results_test-tas_metrics_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.csv$/);
      expect(filename).toContain('metrics');
    });

    it('should truncate task_id to 8 characters', () => {
      const filename = generateExportFilename(result, 'csv', 'all');
      expect(filename).toContain('test-tas'); // First 8 chars of "test-task-123"
    });

    it('should sanitize filename', () => {
      const resultWithSpecialChars = {
        ...result,
        task_id: 'task/with\\special:chars*'
      };
      const filename = generateExportFilename(resultWithSpecialChars, 'csv', 'all');
      expect(filename).not.toContain('/');
      expect(filename).not.toContain('\\');
      expect(filename).not.toContain(':');
      expect(filename).not.toContain('*');
    });
  });


  describe('validateExportOptions', () => {
    const result = createMockResult();

    it('should validate correct options', () => {
      const options: Partial<SimulationExportOptions> = {
        format: 'csv',
        dataType: 'all',
        precision: 6
      };

      const validation = validateExportOptions(result, options);

      expect(validation.valid).toBe(true);
      expect(validation.errors).toHaveLength(0);
    });

    it('should detect invalid time step indices', () => {
      const options: Partial<SimulationExportOptions> = {
        format: 'csv',
        dataType: 'timeseries',
        timeSteps: [0, 5, 10] // 5 and 10 are out of range
      };

      const validation = validateExportOptions(result, options);

      expect(validation.valid).toBe(false);
      expect(validation.errors.length).toBeGreaterThan(0);
      expect(validation.errors.some(err => err.includes('Invalid time step'))).toBe(true);
    });

    it('should detect invalid spatial indices', () => {
      const options: Partial<SimulationExportOptions> = {
        format: 'csv',
        dataType: 'spatial',
        spatialIndices: [0, 1, 10] // 10 is out of range
      };

      const validation = validateExportOptions(result, options);

      expect(validation.valid).toBe(false);
      expect(validation.errors.some(err => err.includes('Invalid spatial'))).toBe(true);
    });

    it('should detect invalid precision (negative)', () => {
      const options: Partial<SimulationExportOptions> = {
        format: 'csv',
        dataType: 'all',
        precision: -1
      };

      const validation = validateExportOptions(result, options);

      expect(validation.valid).toBe(false);
      expect(validation.errors.some(err => err.toLowerCase().includes('precision'))).toBe(true);
    });

    it('should detect invalid precision (too large)', () => {
      const options: Partial<SimulationExportOptions> = {
        format: 'csv',
        dataType: 'all',
        precision: 20
      };

      const validation = validateExportOptions(result, options);

      expect(validation.valid).toBe(false);
      expect(validation.errors.some(err => err.toLowerCase().includes('precision'))).toBe(true);
    });

    it('should warn about large exports', () => {
      // Create a large result that exceeds 50MB (52,428,800 bytes)
      // Need > 52,428,800 / 12 bytes = ~4.37M data points
      // With 3 variables: need ~1.46M time*spatial combinations
      // Use 2200 time steps * 700 spatial points = 1.54M * 3 = 4.62M data points = 55.44 MB
      const largeResult: SimulationResultResponse = {
        ...result,
        time: Array(2200).fill(0).map((_, i) => i),
        x: Array(700).fill(0).map((_, i) => i * 10),
        h: Array(2200).fill(Array(700).fill(1.0)),
        Q: Array(2200).fill(Array(700).fill(10.0)),
        V: Array(2200).fill(Array(700).fill(0.5))
      };

      const validation = validateExportOptions(largeResult, { format: 'csv', dataType: 'all' });

      expect(validation.warnings.length).toBeGreaterThan(0);
      expect(validation.warnings.some(w => w.toLowerCase().includes('large'))).toBe(true);
    });

    it('should estimate file size', () => {
      const validation = validateExportOptions(result, { format: 'csv', dataType: 'all' });

      expect(validation.estimatedSize).toBeGreaterThan(0);
      expect(typeof validation.estimatedSize).toBe('number');
    });
  });

  describe('getExportStatistics', () => {
    const result = createMockResult();

    it('should calculate statistics for all data', () => {
      const stats = getExportStatistics(result, { format: 'csv', dataType: 'all' });

      expect(stats.timeStepsExported).toBe(5);
      expect(stats.spatialPointsExported).toBe(4);
      expect(stats.totalDataPoints).toBe(5 * 4 * 3); // time * space * variables
      expect(stats.estimatedFileSize).toBeGreaterThan(0);
      expect(stats.format).toBe('csv');
      expect(stats.dataType).toBe('all');
      expect(stats.formattedFileSize).toContain('B');
    });

    it('should calculate statistics for timeseries only', () => {
      const stats = getExportStatistics(result, { format: 'csv', dataType: 'timeseries' });

      expect(stats.dataType).toBe('timeseries');
      expect(stats.totalDataPoints).toBe(5 * 4 * 3);
    });

    it('should calculate statistics for spatial only', () => {
      const stats = getExportStatistics(result, { format: 'csv', dataType: 'spatial' });

      expect(stats.dataType).toBe('spatial');
      expect(stats.totalDataPoints).toBe(4 * 5 * 3);
    });

    it('should calculate statistics for metrics only', () => {
      const stats = getExportStatistics(result, { format: 'csv', dataType: 'metrics' });

      expect(stats.dataType).toBe('metrics');
      expect(stats.totalDataPoints).toBeGreaterThan(0); // Metrics count
    });

    it('should respect custom time steps', () => {
      const stats = getExportStatistics(result, {
        format: 'csv',
        dataType: 'timeseries',
        timeSteps: [0, 2, 4]
      });

      expect(stats.timeStepsExported).toBe(3);
    });

    it('should respect custom spatial indices', () => {
      const stats = getExportStatistics(result, {
        format: 'csv',
        dataType: 'spatial',
        spatialIndices: [0, 2]
      });

      expect(stats.spatialPointsExported).toBe(2);
    });

    it('should estimate different sizes for different formats', () => {
      const csvStats = getExportStatistics(result, { format: 'csv', dataType: 'all' });
      const jsonStats = getExportStatistics(result, { format: 'json', dataType: 'all' });
      const excelStats = getExportStatistics(result, { format: 'excel', dataType: 'all' });

      // JSON typically larger than CSV and Excel
      expect(jsonStats.estimatedFileSize).toBeGreaterThan(csvStats.estimatedFileSize);
      expect(jsonStats.estimatedFileSize).toBeGreaterThan(excelStats.estimatedFileSize);
    });
  });
});

describe('simulationExport - CSV Export Functions', () => {
  const result = createMockResult();

  describe('exportTimeSeriesCSV', () => {
    it('should export time series with correct headers', () => {
      const csvData = exportTimeSeriesCSV(result, { precision: 2 });

      expect(csvData.headers).toContain('time');
      expect(csvData.headers).toContain('x0.00_h');
      expect(csvData.headers).toContain('x10.00_h');
      expect(csvData.headers).toContain('x0.00_Q');
      expect(csvData.headers).toContain('x0.00_V');
    });

    it('should export correct number of rows', () => {
      const csvData = exportTimeSeriesCSV(result);

      expect(csvData.rows).toHaveLength(5); // 5 time steps
    });

    it('should export correct data values', () => {
      const csvData = exportTimeSeriesCSV(result, { precision: 2 });

      // First row: time=0
      expect(csvData.rows[0][0]).toBe('0.00'); // time
      expect(csvData.rows[0][1]).toBe('1.00'); // h at x=0
      expect(csvData.rows[0][2]).toBe('10.00'); // Q at x=0
      expect(csvData.rows[0][3]).toBe('0.50'); // V at x=0
    });

    it('should respect custom time steps', () => {
      const csvData = exportTimeSeriesCSV(result, {
        timeSteps: [0, 2, 4],
        precision: 2
      });

      expect(csvData.rows).toHaveLength(3);
      expect(csvData.rows[0][0]).toBe('0.00');
      expect(csvData.rows[1][0]).toBe('2.00');
      expect(csvData.rows[2][0]).toBe('4.00');
    });

    it('should include metadata when requested', () => {
      const csvData = exportTimeSeriesCSV(result, { includeMetadata: true });

      expect(csvData.metadata).toBeDefined();
      expect(csvData.metadata!.length).toBeGreaterThan(0);
      expect(csvData.metadata!.some(line => line.includes('Task ID'))).toBe(true);
    });

    it('should exclude metadata when not requested', () => {
      const csvData = exportTimeSeriesCSV(result, { includeMetadata: false });

      expect(csvData.metadata).toEqual([]);
    });

    it('should respect precision setting', () => {
      const csvData2 = exportTimeSeriesCSV(result, { precision: 2 });
      const csvData6 = exportTimeSeriesCSV(result, { precision: 6 });

      // Check first data value
      expect(csvData2.rows[0][1]).toBe('1.00');
      expect(csvData6.rows[0][1]).toBe('1.000000');
    });
  });

  describe('exportSpatialProfilesCSV', () => {
    it('should export spatial profiles with correct headers', () => {
      const csvData = exportSpatialProfilesCSV(result, { precision: 2 });

      expect(csvData.headers).toContain('x');
      expect(csvData.headers).toContain('t0.00_h');
      expect(csvData.headers).toContain('t1.00_h');
      expect(csvData.headers).toContain('t0.00_Q');
      expect(csvData.headers).toContain('t0.00_V');
    });

    it('should export correct number of rows', () => {
      const csvData = exportSpatialProfilesCSV(result);

      expect(csvData.rows).toHaveLength(4); // 4 spatial points
    });

    it('should export correct data values', () => {
      const csvData = exportSpatialProfilesCSV(result, { precision: 2 });

      // First row: x=0
      expect(csvData.rows[0][0]).toBe('0.00'); // x
      expect(csvData.rows[0][1]).toBe('1.00'); // h at t=0
      expect(csvData.rows[0][2]).toBe('10.00'); // Q at t=0
      expect(csvData.rows[0][3]).toBe('0.50'); // V at t=0
    });

    it('should respect custom spatial indices', () => {
      const csvData = exportSpatialProfilesCSV(result, {
        spatialIndices: [0, 2],
        precision: 2
      });

      expect(csvData.rows).toHaveLength(2);
      expect(csvData.rows[0][0]).toBe('0.00');
      expect(csvData.rows[1][0]).toBe('20.00');
    });

    it('should include metadata when requested', () => {
      const csvData = exportSpatialProfilesCSV(result, { includeMetadata: true });

      expect(csvData.metadata).toBeDefined();
      expect(csvData.metadata!.length).toBeGreaterThan(0);
    });
  });

  describe('exportMetricsCSV', () => {
    it('should export metrics with correct headers', () => {
      const csvData = exportMetricsCSV(result);

      expect(csvData.headers).toContain('Metric');
      expect(csvData.headers).toContain('Value');
      expect(csvData.headers).toContain('Unit');
    });

    it('should export all metrics', () => {
      const csvData = exportMetricsCSV(result);

      // Should have rows for each metric (11 total)
      expect(csvData.rows.length).toBeGreaterThan(5);

      const metricNames = csvData.rows.map(row => row[0]);
      expect(metricNames).toContain('Max Depth');
      expect(metricNames).toContain('Min Depth');
      expect(metricNames).toContain('Max Velocity');
      expect(metricNames).toContain('Converged');
    });

    it('should format metric values correctly', () => {
      const csvData = exportMetricsCSV(result, { precision: 4 });

      // Find Max Depth row
      const maxDepthRow = csvData.rows.find(row => row[0] === 'Max Depth');
      expect(maxDepthRow).toBeDefined();
      expect(maxDepthRow![1]).toBe('1.7000');
      expect(maxDepthRow![2]).toBe('m');
    });

    it('should handle boolean metrics', () => {
      const csvData = exportMetricsCSV(result);

      const convergedRow = csvData.rows.find(row => row[0] === 'Converged');
      expect(convergedRow).toBeDefined();
      expect(convergedRow![1]).toBe('Yes'); // 'Yes' not 'true'
    });

    it('should include metadata', () => {
      const csvData = exportMetricsCSV(result, { includeMetadata: true });

      expect(csvData.metadata).toBeDefined();
      expect(csvData.metadata!.length).toBeGreaterThan(0);
    });
  });

  describe('csvDataToString', () => {
    it('should convert CSV data to string', () => {
      const csvData = {
        headers: ['col1', 'col2', 'col3'],
        rows: [
          ['a', 'b', 'c'],
          ['d', 'e', 'f']
        ]
      };

      const csvString = csvDataToString(csvData);

      expect(csvString).toContain('col1,col2,col3');
      expect(csvString).toContain('a,b,c');
      expect(csvString).toContain('d,e,f');
    });

    it('should include metadata as comments', () => {
      const csvData = {
        headers: ['col1', 'col2'],
        rows: [['a', 'b']],
        metadata: ['# Metadata line 1', '# Metadata line 2']
      };

      const csvString = csvDataToString(csvData);

      expect(csvString).toContain('# Metadata line 1');
      expect(csvString).toContain('# Metadata line 2');
      expect(csvString.indexOf('# Metadata line 1')).toBeLessThan(csvString.indexOf('col1'));
    });

    it('should handle empty rows', () => {
      const csvData = {
        headers: ['col1'],
        rows: []
      };

      const csvString = csvDataToString(csvData);

      expect(csvString).toBe('col1'); // No trailing newline for single line
    });

    it('should use custom delimiter', () => {
      const csvData = {
        headers: ['col1', 'col2'],
        rows: [['a', 'b']]
      };

      const csvString = csvDataToString(csvData, ';');

      expect(csvString).toContain('col1;col2');
      expect(csvString).toContain('a;b');
    });

    it('should join rows with newlines', () => {
      const csvData = {
        headers: ['col1', 'col2'],
        rows: [
          ['a', 'b'],
          ['c', 'd']
        ]
      };

      const csvString = csvDataToString(csvData);

      const lines = csvString.split('\n');
      expect(lines).toHaveLength(3); // header + 2 rows
      expect(lines[0]).toBe('col1,col2');
      expect(lines[1]).toBe('a,b');
      expect(lines[2]).toBe('c,d');
    });
  });
});
