/**
 * Model Export Utilities
 * 模型导出工具函数
 *
 * v1.5.0 Feature: Model Export (JSON, CSV)
 */

import type {
  HydraulicModel,
  ExtendedHydraulicModel,
  ModelExportData,
  ExportOptions
} from '../types/model-io';

// ============= JSON Export =============

/**
 * Export model to JSON format
 * 将模型导出为JSON格式
 *
 * @param model - The hydraulic model to export
 * @param options - Export options
 */
export function exportModelJSON(
  model: HydraulicModel,
  options: ExportOptions = {}
): ModelExportData {
  const {
    includeMetadata = true,
    includeThumbnail = true
  } = options;

  // Create export data structure
  const exportData: ModelExportData = {
    format: 'HydroClaude Model',
    version: '1.5.0',
    exportDate: new Date().toISOString(),
    model: { ...model }
  };

  // Remove optional fields if requested
  if (!includeMetadata && exportData.model.metadata) {
    delete exportData.model.metadata;
  }

  if (!includeThumbnail) {
    const extendedModel = exportData.model as ExtendedHydraulicModel;
    if (extendedModel.thumbnail) {
      delete extendedModel.thumbnail;
    }
  }

  return exportData;
}

/**
 * Download model as JSON file
 * 下载模型为JSON文件
 *
 * @param model - The hydraulic model
 * @param options - Export options
 */
export function downloadModelJSON(
  model: HydraulicModel,
  options: ExportOptions = {}
): void {
  const exportData = exportModelJSON(model, options);
  const prettyPrint = options.prettyPrint !== false; // default true
  const json = JSON.stringify(exportData, null, prettyPrint ? 2 : 0);
  const blob = new Blob([json], { type: 'application/json' });
  const filename = `${sanitizeFilename(model.name)}.hydro.json`;

  downloadBlob(blob, filename);
}

// ============= CSV Export =============

/**
 * Export model nodes to CSV format
 * 将模型节点导出为CSV格式
 *
 * @param model - The hydraulic model
 * @returns CSV string
 */
export function exportModelNodesCSV(model: HydraulicModel): string {
  const headers = [
    'id',
    'type',
    'name',
    'position_x',
    'position_y',
    'width',
    'length',
    'slope',
    'manning_n',
    'n_cells',
    'validated'
  ];

  const rows = model.nodes.map(node => {
    const data = node.data as any;
    return [
      node.id,
      node.type,
      data.name || '',
      node.position.x,
      node.position.y,
      data.width || '',
      data.length || '',
      data.slope || '',
      data.manning_n || '',
      data.n_cells || '',
      data.validated ? 'true' : 'false'
    ];
  });

  return [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');
}

/**
 * Export model edges to CSV format
 * 将模型边导出为CSV格式
 *
 * @param model - The hydraulic model
 * @returns CSV string
 */
export function exportModelEdgesCSV(model: HydraulicModel): string {
  const headers = ['id', 'source', 'target', 'validated', 'flow_direction'];

  const rows = model.edges.map(edge => [
    edge.id,
    edge.source,
    edge.target,
    edge.validated ? 'true' : 'false',
    (edge as any).flow_direction || ''
  ]);

  return [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');
}

/**
 * Download model as CSV files (nodes + edges)
 * 下载模型为CSV文件（节点+边）
 *
 * @param model - The hydraulic model
 */
export function downloadModelCSV(model: HydraulicModel): void {
  const baseName = sanitizeFilename(model.name);

  // Download nodes CSV
  const nodesCSV = exportModelNodesCSV(model);
  const nodesBlob = new Blob([nodesCSV], { type: 'text/csv' });
  downloadBlob(nodesBlob, `${baseName}_nodes.csv`);

  // Small delay before downloading second file
  setTimeout(() => {
    // Download edges CSV
    const edgesCSV = exportModelEdgesCSV(model);
    const edgesBlob = new Blob([edgesCSV], { type: 'text/csv' });
    downloadBlob(edgesBlob, `${baseName}_edges.csv`);
  }, 100);
}

// ============= Helper Functions =============

/**
 * Download blob as file
 * 下载Blob为文件
 *
 * @param blob - The blob to download
 * @param filename - The filename
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';

  document.body.appendChild(a);
  a.click();

  // Cleanup
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 100);
}

/**
 * Sanitize filename (remove invalid characters)
 * 清理文件名（移除非法字符）
 *
 * @param filename - The filename to sanitize
 * @returns Sanitized filename
 */
export function sanitizeFilename(filename: string): string {
  return filename
    .replace(/[^a-z0-9_\-\u4e00-\u9fa5]/gi, '_')  // Allow Chinese characters
    .replace(/_{2,}/g, '_')                         // Replace multiple underscores
    .slice(0, 50);                                  // Limit length
}

/**
 * Estimate export file size
 * 估算导出文件大小
 *
 * @param model - The hydraulic model
 * @param format - Export format
 * @returns Estimated size in bytes
 */
export function estimateExportSize(
  model: HydraulicModel,
  format: 'json' | 'csv'
): number {
  if (format === 'json') {
    // Rough estimation based on JSON.stringify
    const json = JSON.stringify(exportModelJSON(model));
    return new Blob([json]).size;
  } else {
    // CSV estimation
    const nodesCSV = exportModelNodesCSV(model);
    const edgesCSV = exportModelEdgesCSV(model);
    return new Blob([nodesCSV]).size + new Blob([edgesCSV]).size;
  }
}

/**
 * Validate model before export
 * 导出前验证模型
 *
 * @param model - The hydraulic model
 * @returns Validation result
 */
export function validateModelForExport(model: HydraulicModel): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check required fields
  if (!model.id) {
    errors.push('Model ID is missing');
  }

  if (!model.name || model.name.trim() === '') {
    errors.push('Model name is required');
  }

  if (!Array.isArray(model.nodes)) {
    errors.push('Model nodes must be an array');
  } else if (model.nodes.length === 0) {
    warnings.push('Model has no nodes');
  } else if (model.nodes.length > 1000) {
    warnings.push('Model has a large number of nodes (>1000), export may be slow');
  }

  if (!Array.isArray(model.edges)) {
    errors.push('Model edges must be an array');
  }

  // Check file size
  if (errors.length === 0) {
    const size = estimateExportSize(model, 'json');
    if (size > 5 * 1024 * 1024) {  // 5 MB
      warnings.push(`Export size is large (${(size / 1024 / 1024).toFixed(1)} MB)`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

// ============= Batch Export =============

/**
 * Export multiple models as a ZIP archive
 * 将多个模型导出为ZIP归档
 *
 * Note: This requires a ZIP library (JSZip), deferred to future version
 *
 * @param models - Array of models to export
 * @param archiveName - Name of the ZIP file
 */
export function exportModelsArchive(
  models: HydraulicModel[],
  _archiveName: string
): void {
  // TODO: Implement when JSZip is added
  console.warn('Batch export not yet implemented. Use individual exports.');

  // Fallback: export models one by one
  models.forEach((model, index) => {
    setTimeout(() => {
      downloadModelJSON(model);
    }, index * 500);  // Stagger downloads
  });
}

// ============= Export Statistics =============

/**
 * Get export statistics
 * 获取导出统计信息
 *
 * @param model - The hydraulic model
 * @returns Export statistics
 */
export interface ExportStatistics {
  nodeCount: number;
  edgeCount: number;
  estimatedJsonSize: number;
  estimatedCsvSize: number;
  hasMetadata: boolean;
  hasThumbnail: boolean;
  isValid: boolean;
}

export function getExportStatistics(model: HydraulicModel): ExportStatistics {
  const validation = validateModelForExport(model);
  const extendedModel = model as ExtendedHydraulicModel;

  return {
    nodeCount: model.nodes.length,
    edgeCount: model.edges.length,
    estimatedJsonSize: estimateExportSize(model, 'json'),
    estimatedCsvSize: estimateExportSize(model, 'csv'),
    hasMetadata: !!model.metadata,
    hasThumbnail: !!extendedModel.thumbnail,
    isValid: validation.valid
  };
}
