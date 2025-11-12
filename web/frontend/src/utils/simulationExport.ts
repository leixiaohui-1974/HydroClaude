/**
 * Simulation Results Export Utilities
 * 仿真结果导出工具函数
 *
 * v1.5.0 Feature: Results Export (CSV, Excel, JSON)
 */

import * as XLSX from 'xlsx';
import type { SimulationResultResponse } from '../services/api';
import type {
  SimulationExportOptions,
  ExportMetadata,
  CSVExportData,
  JSONExportData,
  ExportValidationResult,
  ExportStatistics,
  ExportDataType
} from '../types/simulation-export';
import {
  DEFAULT_EXPORT_OPTIONS,
  HYDROCLAUDE_VERSION,
  MAX_EXPORT_SIZE
} from '../types/simulation-export';

// ============= Utility Functions =============

/**
 * Format number with specified precision
 * 按指定精度格式化数字
 */
function formatNumber(num: number, precision: number): string {
  return num.toFixed(precision);
}

/**
 * Format file size
 * 格式化文件大小
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

/**
 * Create export metadata
 * 创建导出元数据
 */
function createExportMetadata(
  result: SimulationResultResponse,
  format: 'csv' | 'excel' | 'json'
): ExportMetadata {
  return {
    exportedAt: new Date().toISOString(),
    format,
    simulationTimestamp: result.timestamp,
    taskId: result.task_id,
    timeSteps: result.time.length,
    spatialPoints: result.x.length,
    simulationDuration: result.duration,
    version: HYDROCLAUDE_VERSION
  };
}

// ============= CSV Export =============

/**
 * Export time series data to CSV
 * 导出时间序列数据为CSV
 *
 * Format: time, x1_h, x1_Q, x1_V, x2_h, x2_Q, x2_V, ...
 */
export function exportTimeSeriesCSV(
  result: SimulationResultResponse,
  options: Partial<SimulationExportOptions> = {}
): CSVExportData {
  const opts = { ...DEFAULT_EXPORT_OPTIONS, ...options };
  const precision = opts.precision!;

  // Prepare headers
  const headers: string[] = ['time'];
  for (let i = 0; i < result.x.length; i++) {
    const x = formatNumber(result.x[i], precision);
    headers.push(`x${x}_h`, `x${x}_Q`, `x${x}_V`);
  }

  // Prepare rows
  const rows: string[][] = [];
  const timeIndices = opts.timeSteps || Array.from({ length: result.time.length }, (_, i) => i);

  for (const ti of timeIndices) {
    const row: string[] = [formatNumber(result.time[ti], precision)];

    for (let xi = 0; xi < result.x.length; xi++) {
      row.push(
        formatNumber(result.h[ti][xi], precision),
        formatNumber(result.Q[ti][xi], precision),
        formatNumber(result.V[ti][xi], precision)
      );
    }

    rows.push(row);
  }

  // Metadata comments
  const metadata: string[] = [];
  if (opts.includeMetadata) {
    const meta = createExportMetadata(result, 'csv');
    metadata.push(`# HydroClaude Simulation Results Export`);
    metadata.push(`# Exported: ${meta.exportedAt}`);
    metadata.push(`# Task ID: ${meta.taskId}`);
    metadata.push(`# Time Steps: ${meta.timeSteps}`);
    metadata.push(`# Spatial Points: ${meta.spatialPoints}`);
    metadata.push(`# Duration: ${meta.simulationDuration}s`);
    metadata.push(`#`);
  }

  return { headers, rows, metadata };
}

/**
 * Export spatial profiles to CSV
 * 导出空间剖面数据为CSV
 *
 * Format: x, t1_h, t1_Q, t1_V, t2_h, t2_Q, t2_V, ...
 */
export function exportSpatialProfilesCSV(
  result: SimulationResultResponse,
  options: Partial<SimulationExportOptions> = {}
): CSVExportData {
  const opts = { ...DEFAULT_EXPORT_OPTIONS, ...options };
  const precision = opts.precision!;

  // Prepare headers
  const headers: string[] = ['x'];
  for (let i = 0; i < result.time.length; i++) {
    const t = formatNumber(result.time[i], precision);
    headers.push(`t${t}_h`, `t${t}_Q`, `t${t}_V`);
  }

  // Prepare rows
  const rows: string[][] = [];
  const spatialIndices = opts.spatialIndices || Array.from({ length: result.x.length }, (_, i) => i);

  for (const xi of spatialIndices) {
    const row: string[] = [formatNumber(result.x[xi], precision)];

    for (let ti = 0; ti < result.time.length; ti++) {
      row.push(
        formatNumber(result.h[ti][xi], precision),
        formatNumber(result.Q[ti][xi], precision),
        formatNumber(result.V[ti][xi], precision)
      );
    }

    rows.push(row);
  }

  // Metadata
  const metadata: string[] = [];
  if (opts.includeMetadata) {
    const meta = createExportMetadata(result, 'csv');
    metadata.push(`# HydroClaude Simulation Results Export (Spatial Profiles)`);
    metadata.push(`# Exported: ${meta.exportedAt}`);
    metadata.push(`# Task ID: ${meta.taskId}`);
    metadata.push(`#`);
  }

  return { headers, rows, metadata };
}

/**
 * Export metrics to CSV
 * 导出指标数据为CSV
 */
export function exportMetricsCSV(
  result: SimulationResultResponse,
  options: Partial<SimulationExportOptions> = {}
): CSVExportData {
  const opts = { ...DEFAULT_EXPORT_OPTIONS, ...options };
  const precision = opts.precision!;

  const headers = ['Metric', 'Value', 'Unit'];
  const rows: string[][] = [
    ['Mass Conservation Error', formatNumber(result.metrics.mass_conservation_error, precision), '%'],
    ['Max Depth', formatNumber(result.metrics.max_depth, precision), 'm'],
    ['Min Depth', formatNumber(result.metrics.min_depth, precision), 'm'],
    ['Max Velocity', formatNumber(result.metrics.max_velocity, precision), 'm/s'],
    ['Max Discharge', formatNumber(result.metrics.max_discharge, precision), 'm³/s'],
    ['Max Froude Number', formatNumber(result.metrics.max_froude, precision), '-'],
    ['Mean Depth (Final)', formatNumber(result.metrics.mean_depth_final, precision), 'm'],
    ['Mean Discharge (Final)', formatNumber(result.metrics.mean_discharge_final, precision), 'm³/s'],
    ['Total Iterations', result.metrics.total_iterations.toString(), '-'],
    ['Converged', result.metrics.converged ? 'Yes' : 'No', '-'],
    ['Simulation Duration', formatNumber(result.duration, precision), 's']
  ];

  const metadata: string[] = [];
  if (opts.includeMetadata) {
    const meta = createExportMetadata(result, 'csv');
    metadata.push(`# HydroClaude Simulation Metrics`);
    metadata.push(`# Exported: ${meta.exportedAt}`);
    metadata.push(`# Task ID: ${meta.taskId}`);
    metadata.push(`#`);
  }

  return { headers, rows, metadata };
}

/**
 * Convert CSV data to string
 * 将CSV数据转换为字符串
 */
export function csvDataToString(data: CSVExportData, delimiter: string = ','): string {
  const lines: string[] = [];

  // Add metadata as comments
  if (data.metadata && data.metadata.length > 0) {
    lines.push(...data.metadata);
  }

  // Add headers
  lines.push(data.headers.join(delimiter));

  // Add rows
  for (const row of data.rows) {
    lines.push(row.join(delimiter));
  }

  return lines.join('\n');
}

/**
 * Download CSV file
 * 下载CSV文件
 */
export function downloadCSV(
  data: CSVExportData,
  filename: string,
  delimiter: string = ','
): void {
  const csvContent = csvDataToString(data, delimiter);
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ============= Validation =============

/**
 * Validate export options
 * 验证导出选项
 */
export function validateExportOptions(
  result: SimulationResultResponse,
  options: Partial<SimulationExportOptions>
): ExportValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Validate time steps
  if (options.timeSteps) {
    for (const ti of options.timeSteps) {
      if (ti < 0 || ti >= result.time.length) {
        errors.push(`Invalid time step index: ${ti} (valid range: 0-${result.time.length - 1})`);
      }
    }
  }

  // Validate spatial indices
  if (options.spatialIndices) {
    for (const xi of options.spatialIndices) {
      if (xi < 0 || xi >= result.x.length) {
        errors.push(`Invalid spatial index: ${xi} (valid range: 0-${result.x.length - 1})`);
      }
    }
  }

  // Validate precision
  if (options.precision !== undefined && (options.precision < 0 || options.precision > 15)) {
    errors.push('Precision must be between 0 and 15');
  }

  // Estimate file size
  const totalDataPoints = result.time.length * result.x.length * 3; // h, Q, V
  const avgBytesPerValue = 12; // estimate
  const estimatedSize = totalDataPoints * avgBytesPerValue;

  // Check file size
  if (estimatedSize > MAX_EXPORT_SIZE) {
    warnings.push(
      `Large export size (${formatFileSize(estimatedSize)}). ` +
      `Consider filtering time steps or spatial points.`
    );
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    estimatedSize
  };
}

/**
 * Get export statistics
 * 获取导出统计信息
 */
export function getExportStatistics(
  result: SimulationResultResponse,
  options: Partial<SimulationExportOptions>
): ExportStatistics {
  const opts = { ...DEFAULT_EXPORT_OPTIONS, ...options };

  const timeSteps = opts.timeSteps?.length || result.time.length;
  const spatialPoints = opts.spatialIndices?.length || result.x.length;
  const totalDataPoints = timeSteps * spatialPoints * 3; // h, Q, V

  // Estimate file size based on format
  let estimatedFileSize: number;
  switch (opts.format) {
    case 'csv':
      estimatedFileSize = totalDataPoints * 12; // ~12 bytes per value
      break;
    case 'json':
      estimatedFileSize = totalDataPoints * 15; // JSON overhead
      break;
    case 'excel':
      estimatedFileSize = totalDataPoints * 10; // Binary format is more compact
      break;
    default:
      estimatedFileSize = totalDataPoints * 12;
  }

  return {
    totalDataPoints,
    timeStepsExported: timeSteps,
    spatialPointsExported: spatialPoints,
    estimatedFileSize,
    formattedFileSize: formatFileSize(estimatedFileSize),
    format: opts.format!,
    dataType: opts.dataType!
  };
}

/**
 * Sanitize filename
 * 清理文件名
 */
export function sanitizeFilename(filename: string): string {
  // Remove invalid characters and limit length
  return filename
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, '_')
    .replace(/^\.+/, '')
    .substring(0, 200);
}

/**
 * Generate export filename
 * 生成导出文件名
 */
export function generateExportFilename(
  result: SimulationResultResponse,
  format: 'csv' | 'excel' | 'json',
  dataType: ExportDataType
): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
  const taskId = result.task_id.substring(0, 8);
  const extension = format === 'excel' ? '.xlsx' : format === 'json' ? '.json' : '.csv';

  let typeStr = '';
  switch (dataType) {
    case 'timeseries':
      typeStr = '_timeseries';
      break;
    case 'spatial':
      typeStr = '_spatial';
      break;
    case 'metrics':
      typeStr = '_metrics';
      break;
    default:
      typeStr = '';
  }

  return sanitizeFilename(`hydroclaude_results_${taskId}${typeStr}_${timestamp}${extension}`);
}
// ============= Excel Export =============

/**
 * Export to Excel
 * 导出到Excel
 */
export function exportToExcel(
  result: SimulationResultResponse,
  dataType: ExportDataType,
  options: Partial<SimulationExportOptions> = {}
): void {
  const opts = { ...DEFAULT_EXPORT_OPTIONS, ...options };
  const workbook = XLSX.utils.book_new();

  if (dataType === 'all' || dataType === 'timeseries') {
    const tsData = exportTimeSeriesCSV(result, opts);
    const tsSheet = XLSX.utils.aoa_to_sheet([tsData.headers, ...tsData.rows]);
    XLSX.utils.book_append_sheet(workbook, tsSheet, 'TimeSeries');
  }

  if (dataType === 'all' || dataType === 'spatial') {
    const spData = exportSpatialProfilesCSV(result, opts);
    const spSheet = XLSX.utils.aoa_to_sheet([spData.headers, ...spData.rows]);
    XLSX.utils.book_append_sheet(workbook, spSheet, 'SpatialProfiles');
  }

  if (dataType === 'all' || dataType === 'metrics') {
    const metricsData = exportMetricsCSV(result, opts);
    const metricsSheet = XLSX.utils.aoa_to_sheet([metricsData.headers, ...metricsData.rows]);
    XLSX.utils.book_append_sheet(workbook, metricsSheet, 'Metrics');
  }

  if (opts.includeMetadata) {
    const meta = createExportMetadata(result, 'excel');
    const metadataRows = [
      ['Property', 'Value'],
      ['Exported At', meta.exportedAt],
      ['Task ID', meta.taskId],
      ['Simulation Timestamp', meta.simulationTimestamp],
      ['Time Steps', meta.timeSteps.toString()],
      ['Spatial Points', meta.spatialPoints.toString()],
      ['Simulation Duration (s)', meta.simulationDuration.toString()],
      ['HydroClaude Version', meta.version]
    ];
    const metadataSheet = XLSX.utils.aoa_to_sheet(metadataRows);
    XLSX.utils.book_append_sheet(workbook, metadataSheet, 'Metadata');
  }

  const filename = generateExportFilename(result, 'excel', dataType);
  XLSX.writeFile(workbook, filename);
}

// ============= JSON Export =============

/**
 * Export to JSON
 */
export function exportToJSON(
  result: SimulationResultResponse,
  dataType: ExportDataType,
  options: Partial<SimulationExportOptions> = {}
): void {
  const opts = { ...DEFAULT_EXPORT_OPTIONS, ...options };
  const metadata = createExportMetadata(result, 'json');

  let exportData: JSONExportData;

  if (dataType === 'all') {
    exportData = {
      metadata,
      result,
      processedData: {
        timeSeries: result.time.map((t, ti) => ({
          time: t,
          x: result.x,
          h: result.h[ti],
          Q: result.Q[ti],
          V: result.V[ti]
        })),
        spatialProfiles: result.x.map((x, xi) => ({
          x,
          time: result.time,
          h: result.h.map(row => row[xi]),
          Q: result.Q.map(row => row[xi]),
          V: result.V.map(row => row[xi])
        }))
      }
    };
  } else if (dataType === 'timeseries') {
    exportData = {
      metadata,
      result,
      processedData: {
        timeSeries: result.time.map((t, ti) => ({
          time: t,
          x: result.x,
          h: result.h[ti],
          Q: result.Q[ti],
          V: result.V[ti]
        }))
      }
    };
  } else if (dataType === 'spatial') {
    exportData = {
      metadata,
      result,
      processedData: {
        spatialProfiles: result.x.map((x, xi) => ({
          x,
          time: result.time,
          h: result.h.map(row => row[xi]),
          Q: result.Q.map(row => row[xi]),
          V: result.V.map(row => row[xi])
        }))
      }
    };
  } else {
    exportData = {
      metadata,
      result: {
        task_id: result.task_id,
        status: result.status,
        duration: result.duration,
        timestamp: result.timestamp,
        metrics: result.metrics,
        x: [],
        time: [],
        h: [],
        Q: [],
        V: []
      }
    };
  }

  const jsonString = opts.prettyPrint
    ? JSON.stringify(exportData, null, 2)
    : JSON.stringify(exportData);

  const blob = new Blob([jsonString], { type: 'application/json' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  const filename = generateExportFilename(result, 'json', dataType);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ============= Main Export Function =============

/**
 * Export simulation results
 */
export function exportSimulationResults(
  result: SimulationResultResponse,
  options: SimulationExportOptions
): void {
  const validation = validateExportOptions(result, options);
  if (!validation.valid) {
    const errorMessage = validation.errors.join(', ');
    throw new Error('Export validation failed: ' + errorMessage);
  }

  switch (options.format) {
    case 'csv':
      exportCSVByDataType(result, options);
      break;
    case 'excel':
      exportToExcel(result, options.dataType, options);
      break;
    case 'json':
      exportToJSON(result, options.dataType, options);
      break;
    default:
      throw new Error('Unsupported format: ' + options.format);
  }
}

function exportCSVByDataType(
  result: SimulationResultResponse,
  options: SimulationExportOptions
): void {
  const dataType = options.dataType;

  if (dataType === 'all') {
    const tsData = exportTimeSeriesCSV(result, options);
    downloadCSV(tsData, generateExportFilename(result, 'csv', 'timeseries'), options.csvDelimiter);

    const spData = exportSpatialProfilesCSV(result, options);
    downloadCSV(spData, generateExportFilename(result, 'csv', 'spatial'), options.csvDelimiter);

    const metricsData = exportMetricsCSV(result, options);
    downloadCSV(metricsData, generateExportFilename(result, 'csv', 'metrics'), options.csvDelimiter);
  } else if (dataType === 'timeseries') {
    const data = exportTimeSeriesCSV(result, options);
    downloadCSV(data, generateExportFilename(result, 'csv', 'timeseries'), options.csvDelimiter);
  } else if (dataType === 'spatial') {
    const data = exportSpatialProfilesCSV(result, options);
    downloadCSV(data, generateExportFilename(result, 'csv', 'spatial'), options.csvDelimiter);
  } else if (dataType === 'metrics') {
    const data = exportMetricsCSV(result, options);
    downloadCSV(data, generateExportFilename(result, 'csv', 'metrics'), options.csvDelimiter);
  }
}
