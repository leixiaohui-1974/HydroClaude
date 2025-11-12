/**
 * Model Import/Export Type Definitions
 * 模型导入/导出类型定义
 *
 * v1.5.0 Feature: Model Import/Export
 */

import { HydraulicModel as BaseHydraulicModel } from '../features/modeling/types/model.types';

// Re-export HydraulicModel for convenience
export type HydraulicModel = BaseHydraulicModel;

// ============= Export Format =============

/**
 * Model export format wrapper
 * 模型导出格式包装器
 */
export interface ModelExportData {
  format: 'HydroClaude Model';
  version: string;                    // Format version (e.g., "1.5.0")
  exportDate: string;                 // ISO 8601 datetime
  model: HydraulicModel;              // The actual model data
}

// ============= Extended Model (for v1.5.0) =============

/**
 * Extended hydraulic model with v1.5.0 features
 * 扩展水力学模型（v1.5.0新增功能）
 */
export interface ExtendedHydraulicModel extends HydraulicModel {
  // Additional metadata for v1.5.0
  author?: string;                    // Model author
  tags?: string[];                    // Categorization tags
  thumbnail?: string;                 // base64 encoded PNG (max 100KB)

  // ReactFlow viewport state
  viewport?: {
    x: number;
    y: number;
    zoom: number;
  };

  // Global simulation config (for templates)
  globalConfig?: GlobalSimulationConfig;
}

/**
 * Global simulation configuration
 * 全局仿真配置
 */
export interface GlobalSimulationConfig {
  gravity: number;                    // m/s² (default: 9.81)
  timeStep: number;                   // seconds (default: 0.01)
  duration: number;                   // seconds (default: 10.0)
  saveInterval: number;               // seconds (default: 0.1)
  solver?: {
    type: 'godunov' | 'roe';         // Riemann solver
    limiter?: 'minmod' | 'superbee' | 'vanleer';
    cfl?: number;                     // CFL number (default: 0.9)
  };
}

// ============= Model Templates =============

/**
 * Template category
 * 模板分类
 */
export type TemplateCategory = 'academic' | 'practical' | 'tutorial';

/**
 * Template difficulty level
 * 模板难度等级
 */
export type TemplateDifficulty = 'beginner' | 'intermediate' | 'advanced';

/**
 * Template documentation
 * 模板文档
 */
export interface TemplateDocumentation {
  overview: string;                   // Overview text (markdown supported)
  physicsBackground: string;          // Physics explanation
  expectedResults: string;            // What to expect from simulation
  references: string[];               // Academic/technical references
  tutorial?: {
    steps: {
      title: string;
      description: string;
      action?: string;
    }[];
  };
}

/**
 * Model template
 * 模型模板
 */
export interface ModelTemplate {
  id: string;                         // Template identifier
  name: string;                       // Display name
  category: TemplateCategory;
  description: string;                // Short description
  difficulty: TemplateDifficulty;
  thumbnail: string;                  // URL or base64

  model: ExtendedHydraulicModel;      // The template model

  documentation: TemplateDocumentation;
}

// ============= Recent Models =============

/**
 * Recent model entry
 * 最近使用的模型条目
 */
export interface RecentModel {
  id: string;
  name: string;
  accessedAt: string;                 // ISO 8601 datetime
  thumbnail?: string;
}

// ============= User Settings =============

/**
 * User preferences
 * 用户偏好设置
 */
export interface UserSettings {
  theme: 'light' | 'dark';
  autoSave: boolean;
  autoSaveInterval?: number;          // seconds
  defaultConfig?: GlobalSimulationConfig;
  exportFormat: 'json' | 'csv';
  locale?: 'zh-CN' | 'en-US';
}

// ============= Storage Schema =============

/**
 * localStorage keys
 * 本地存储键名
 */
export const STORAGE_KEYS = {
  MODELS: 'hydroclaude_models',
  RECENT: 'hydroclaude_recent',
  SETTINGS: 'hydroclaude_settings',
  COMPARISONS: 'hydroclaude_comparisons',
  VERSION: 'hydroclaude_version',
  TEMPLATES: 'hydroclaude_templates'
} as const;

/**
 * Storage quota info
 * 存储配额信息
 */
export interface StorageQuota {
  used: number;                       // bytes
  available: number;                  // bytes
  percentage: number;                 // 0-100
  itemCount: number;                  // number of models
}

// ============= Validation =============

/**
 * Import validation result
 * 导入验证结果
 */
export interface ImportValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  modelVersion?: string;
  isCompatible: boolean;
}

/**
 * File type for import
 * 导入文件类型
 */
export type ImportFileType = 'json' | 'csv' | 'xml' | 'inp';

/**
 * Export options
 * 导出选项
 */
export interface ExportOptions {
  format?: 'json' | 'csv';
  includeMetadata?: boolean;
  includeThumbnail?: boolean;
  prettyPrint?: boolean;              // For JSON
}

// ============= Error Handling =============

/**
 * Import/Export error types
 * 导入/导出错误类型
 */
export enum IOErrorType {
  INVALID_FORMAT = 'invalid_format',
  UNSUPPORTED_VERSION = 'unsupported_version',
  VALIDATION_FAILED = 'validation_failed',
  FILE_TOO_LARGE = 'file_too_large',
  QUOTA_EXCEEDED = 'quota_exceeded',
  PARSE_ERROR = 'parse_error',
  STORAGE_ERROR = 'storage_error'
}

/**
 * Import/Export error
 * 导入/导出错误
 */
export interface IOError {
  type: IOErrorType;
  message: string;
  details?: string;
  recoverable: boolean;
}

// ============= Comparison (v1.5.0) =============

/**
 * Comparison scenario
 * 对比场景
 */
export interface ComparisonScenario {
  id: string;
  name: string;
  description?: string;
  color: string;                      // Hex color for plots
  modelId?: string;                   // Reference to source model
  resultId?: string;                  // Reference to simulation result
  metadata: {
    parameterVariations?: Record<string, any>;
    createdAt: string;
  };
}

/**
 * Comparison session
 * 对比会话
 */
export interface ComparisonSession {
  id: string;
  name: string;
  scenarios: ComparisonScenario[];
  createdAt: string;
  updatedAt: string;
}

/**
 * Comparison metrics
 * 对比指标
 */
export interface ComparisonMetrics {
  maxDepthDifference: number;
  peakTimeDifference: number;
  volumeDifference: number;
  rmseDepth: number;                  // Root mean square error
  correlationCoeff: number;           // Pearson correlation
}

// ============= Type Guards =============

/**
 * Check if data is valid model export format
 */
export function isModelExportData(data: any): data is ModelExportData {
  return (
    data &&
    typeof data === 'object' &&
    data.format === 'HydroClaude Model' &&
    typeof data.version === 'string' &&
    typeof data.exportDate === 'string' &&
    data.model &&
    typeof data.model === 'object'
  );
}

/**
 * Check if model version is compatible
 */
export function isCompatibleVersion(version: string): boolean {
  const [major] = version.split('.').map(Number);
  return major === 1; // v1.x.x compatible
}

/**
 * Check if model is extended model
 */
export function isExtendedModel(model: any): model is ExtendedHydraulicModel {
  return (
    model &&
    typeof model === 'object' &&
    typeof model.id === 'string' &&
    typeof model.name === 'string' &&
    Array.isArray(model.nodes) &&
    Array.isArray(model.edges)
  );
}
