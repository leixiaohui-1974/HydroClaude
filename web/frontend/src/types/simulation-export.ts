/**
 * Simulation Results Export Type Definitions
 * 仿真结果导出类型定义
 *
 * v1.5.0 Feature: Results Export
 */

import type { SimulationResultResponse } from '../services/api';

/**
 * Export format options
 * 导出格式选项
 */
export type ExportFormat = 'csv' | 'excel' | 'json';

/**
 * Export data type
 * 导出数据类型
 */
export type ExportDataType = 'all' | 'timeseries' | 'spatial' | 'metrics';

/**
 * Export options for simulation results
 * 仿真结果导出选项
 */
export interface SimulationExportOptions {
  /**
   * Export format
   * 导出格式
   */
  format: ExportFormat;

  /**
   * Data type to export
   * 导出的数据类型
   */
  dataType: ExportDataType;

  /**
   * Include headers in CSV/Excel
   * CSV/Excel中包含表头
   * @default true
   */
  includeHeaders?: boolean;

  /**
   * Decimal precision
   * 小数精度
   * @default 6
   */
  precision?: number;

  /**
   * Time step indices to export (null = all)
   * 导出的时间步索引（null表示全部）
   */
  timeSteps?: number[] | null;

  /**
   * Spatial indices to export (null = all)
   * 导出的空间位置索引（null表示全部）
   */
  spatialIndices?: number[] | null;

  /**
   * Include metadata in export
   * 导出中包含元数据
   * @default true
   */
  includeMetadata?: boolean;

  /**
   * Pretty print JSON
   * JSON美化输出
   * @default false
   */
  prettyPrint?: boolean;

  /**
   * Excel sheet name
   * Excel工作表名称
   */
  sheetName?: string;

  /**
   * CSV delimiter
   * CSV分隔符
   * @default ','
   */
  csvDelimiter?: string;
}

/**
 * Export metadata
 * 导出元数据
 */
export interface ExportMetadata {
  /**
   * Export timestamp
   * 导出时间戳
   */
  exportedAt: string;

  /**
   * Export format
   * 导出格式
   */
  format: ExportFormat;

  /**
   * Original simulation timestamp
   * 原始仿真时间戳
   */
  simulationTimestamp: string;

  /**
   * Task ID
   */
  taskId: string;

  /**
   * Number of time steps
   * 时间步数量
   */
  timeSteps: number;

  /**
   * Number of spatial points
   * 空间点数量
   */
  spatialPoints: number;

  /**
   * Simulation duration
   * 仿真持续时间
   */
  simulationDuration: number;

  /**
   * HydroClaude version
   */
  version: string;
}

/**
 * CSV export structure
 * CSV导出结构
 */
export interface CSVExportData {
  /**
   * Headers
   * 表头
   */
  headers: string[];

  /**
   * Rows of data
   * 数据行
   */
  rows: string[][];

  /**
   * Metadata (as comment lines)
   * 元数据（作为注释行）
   */
  metadata?: string[];
}

/**
 * Excel export structure
 * Excel导出结构
 */
export interface ExcelExportData {
  /**
   * Sheet name
   * 工作表名称
   */
  sheetName: string;

  /**
   * Headers
   * 表头
   */
  headers: string[];

  /**
   * Rows of data
   * 数据行
   */
  rows: (string | number)[][];

  /**
   * Metadata sheet (optional)
   * 元数据工作表（可选）
   */
  metadataSheet?: {
    sheetName: string;
    data: Record<string, any>;
  };
}

/**
 * JSON export structure
 * JSON导出结构
 */
export interface JSONExportData {
  /**
   * Metadata
   * 元数据
   */
  metadata: ExportMetadata;

  /**
   * Raw simulation result
   * 原始仿真结果
   */
  result: SimulationResultResponse;

  /**
   * Processed data (optional)
   * 处理后的数据（可选）
   */
  processedData?: {
    timeSeries?: Array<{
      time: number;
      x: number[];
      h: number[];
      Q: number[];
      V: number[];
    }>;
    spatialProfiles?: Array<{
      x: number;
      time: number[];
      h: number[];
      Q: number[];
      V: number[];
    }>;
  };
}

/**
 * Export validation result
 * 导出验证结果
 */
export interface ExportValidationResult {
  /**
   * Is valid
   * 是否有效
   */
  valid: boolean;

  /**
   * Validation errors
   * 验证错误
   */
  errors: string[];

  /**
   * Validation warnings
   * 验证警告
   */
  warnings: string[];

  /**
   * Estimated file size (bytes)
   * 估算文件大小（字节）
   */
  estimatedSize: number;
}

/**
 * Export statistics
 * 导出统计信息
 */
export interface ExportStatistics {
  /**
   * Total data points
   * 总数据点数
   */
  totalDataPoints: number;

  /**
   * Time steps exported
   * 导出的时间步数
   */
  timeStepsExported: number;

  /**
   * Spatial points exported
   * 导出的空间点数
   */
  spatialPointsExported: number;

  /**
   * Estimated file size
   * 估算文件大小
   */
  estimatedFileSize: number;

  /**
   * Formatted file size
   * 格式化文件大小
   */
  formattedFileSize: string;

  /**
   * Export format
   * 导出格式
   */
  format: ExportFormat;

  /**
   * Data type
   * 数据类型
   */
  dataType: ExportDataType;
}

/**
 * Constants
 * 常量
 */
export const DEFAULT_EXPORT_OPTIONS: Partial<SimulationExportOptions> = {
  includeHeaders: true,
  precision: 6,
  timeSteps: null,
  spatialIndices: null,
  includeMetadata: true,
  prettyPrint: false,
  sheetName: 'SimulationResults',
  csvDelimiter: ','
};

export const HYDROCLAUDE_VERSION = '1.5.0';

export const MAX_EXPORT_SIZE = 50 * 1024 * 1024; // 50 MB

export const EXPORT_FILE_EXTENSIONS: Record<ExportFormat, string> = {
  csv: '.csv',
  excel: '.xlsx',
  json: '.json'
};
