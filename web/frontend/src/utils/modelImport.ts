/**
 * Model Import Utilities
 * 模型导入工具函数
 *
 * v1.5.0 Feature: Model Import (JSON, CSV)
 */

import type {
  HydraulicModel,
  ImportValidationResult,
  IOError
} from '../types/model-io';
import { isModelExportData, isCompatibleVersion, IOErrorType } from '../types/model-io';

// ============= JSON Import =============

/**
 * Import model from JSON file
 * 从JSON文件导入模型
 *
 * @param file - The JSON file to import
 * @returns Promise resolving to hydraulic model
 * @throws IOError if import fails
 */
export async function importModelJSON(file: File): Promise<HydraulicModel> {
  try {
    // Check file size (max 10 MB)
    if (file.size > 10 * 1024 * 1024) {
      throw createIOError(
        IOErrorType.FILE_TOO_LARGE,
        `File size ${(file.size / 1024 / 1024).toFixed(1)} MB exceeds limit of 10 MB`,
        false
      );
    }

    // Read file content
    const text = await file.text();

    // Parse JSON
    let data: any;
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw createIOError(
        IOErrorType.PARSE_ERROR,
        'Failed to parse JSON file. Please ensure the file is valid JSON.',
        false
      );
    }

    // Validate format
    if (!isModelExportData(data)) {
      throw createIOError(
        IOErrorType.INVALID_FORMAT,
        'Invalid file format. Expected HydroClaude Model format.',
        false
      );
    }

    // Version check
    if (!isCompatibleVersion(data.version)) {
      throw createIOError(
        IOErrorType.UNSUPPORTED_VERSION,
        `Model version ${data.version} is not compatible with current version`,
        false
      );
    }

    // Validate model structure
    const validation = validateImportedModel(data.model);
    if (!validation.valid) {
      throw createIOError(
        IOErrorType.VALIDATION_FAILED,
        `Model validation failed: ${validation.errors.join(', ')}`,
        false
      );
    }

    // Update timestamps
    const model: HydraulicModel = {
      ...data.model,
      updated_at: new Date().toISOString()
    };

    return model;
  } catch (error) {
    if ((error as any).type) {
      // Already an IOError
      throw error;
    }

    // Wrap unexpected errors
    throw createIOError(
      IOErrorType.PARSE_ERROR,
      `Import failed: ${(error as Error).message}`,
      false
    );
  }
}

/**
 * Import model from JSON string
 * 从JSON字符串导入模型
 *
 * @param jsonString - JSON string containing model data
 * @returns Hydraulic model
 */
export function importModelFromJSON(jsonString: string): HydraulicModel {
  const data = JSON.parse(jsonString);

  if (!isModelExportData(data)) {
    throw new Error('Invalid model format');
  }

  return data.model;
}

// ============= CSV Import =============

/**
 * Import model from CSV files (nodes + edges)
 * 从CSV文件导入模型（节点+边）
 *
 * Note: CSV import requires both nodes and edges files
 * This is a simplified version, full implementation would use a CSV parser library
 *
 * @param nodesFile - CSV file containing nodes
 * @param edgesFile - CSV file containing edges
 * @returns Promise resolving to hydraulic model
 */
export async function importModelCSV(
  nodesFile: File,
  edgesFile: File
): Promise<HydraulicModel> {
  try {
    // Read both files
    const nodesText = await nodesFile.text();
    const edgesText = await edgesFile.text();

    // Parse CSV
    const nodes = parseNodesCSV(nodesText);
    const edges = parseEdgesCSV(edgesText);

    // Create model
    const model: HydraulicModel = {
      id: crypto.randomUUID(),
      name: 'Imported Model',
      description: `Imported from ${nodesFile.name}`,
      nodes,
      edges,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      version: 1,
      validated: false
    };

    // Validate
    const validation = validateImportedModel(model);
    if (!validation.valid) {
      throw createIOError(
        IOErrorType.VALIDATION_FAILED,
        `CSV import validation failed: ${validation.errors.join(', ')}`,
        false
      );
    }

    return model;
  } catch (error) {
    throw createIOError(
      IOErrorType.PARSE_ERROR,
      `CSV import failed: ${(error as Error).message}`,
      false
    );
  }
}

/**
 * Parse nodes from CSV string
 * 从CSV字符串解析节点
 *
 * @param csv - CSV string
 * @returns Array of model nodes
 */
function parseNodesCSV(csv: string): any[] {
  const lines = csv.split('\n').filter(line => line.trim());
  if (lines.length < 2) {
    throw new Error('Invalid nodes CSV: missing header or data');
  }

  // Skip headers line
  const nodes: any[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim());
    const node: any = {
      id: values[0],
      type: values[1],
      position: {
        x: parseFloat(values[3]) || 0,
        y: parseFloat(values[4]) || 0
      },
      data: {
        name: values[2] || `Node ${i}`,
        width: parseFloat(values[5]) || undefined,
        length: parseFloat(values[6]) || undefined,
        slope: parseFloat(values[7]) || undefined,
        manning_n: parseFloat(values[8]) || undefined,
        n_cells: parseInt(values[9]) || undefined,
        validated: values[10] === 'true',
        errors: [],
        warnings: []
      }
    };

    nodes.push(node);
  }

  return nodes;
}

/**
 * Parse edges from CSV string
 * 从CSV字符串解析边
 *
 * @param csv - CSV string
 * @returns Array of model edges
 */
function parseEdgesCSV(csv: string): any[] {
  const lines = csv.split('\n').filter(line => line.trim());
  if (lines.length < 2) {
    throw new Error('Invalid edges CSV: missing header or data');
  }

  // Skip headers line
  const edges: any[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim());
    const edge: any = {
      id: values[0],
      source: values[1],
      target: values[2],
      validated: values[3] === 'true',
      flow_direction: values[4] || undefined
    };

    edges.push(edge);
  }

  return edges;
}

// ============= Validation =============

/**
 * Validate imported model
 * 验证导入的模型
 *
 * @param model - The model to validate
 * @returns Validation result
 */
export function validateImportedModel(model: any): ImportValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check required fields
  if (!model.id || typeof model.id !== 'string') {
    errors.push('Model ID is missing or invalid');
  }

  if (!model.name || typeof model.name !== 'string') {
    errors.push('Model name is missing or invalid');
  }

  // Validate nodes
  if (!Array.isArray(model.nodes)) {
    errors.push('Model nodes must be an array');
  } else {
    if (model.nodes.length === 0) {
      warnings.push('Model has no nodes');
    }

    if (model.nodes.length > 1000) {
      warnings.push('Model has a large number of nodes (>1000)');
    }

    // Validate each node
    model.nodes.forEach((node: any, index: number) => {
      if (!node.id) {
        errors.push(`Node ${index} is missing ID`);
      }

      if (!node.type) {
        errors.push(`Node ${node.id || index} is missing type`);
      }

      if (!node.position || typeof node.position.x !== 'number' || typeof node.position.y !== 'number') {
        errors.push(`Node ${node.id || index} has invalid position`);
      }

      if (!node.data) {
        errors.push(`Node ${node.id || index} is missing data`);
      }
    });
  }

  // Validate edges
  if (!Array.isArray(model.edges)) {
    errors.push('Model edges must be an array');
  } else {
    // Validate each edge
    model.edges.forEach((edge: any, index: number) => {
      if (!edge.id) {
        errors.push(`Edge ${index} is missing ID`);
      }

      if (!edge.source) {
        errors.push(`Edge ${edge.id || index} is missing source`);
      }

      if (!edge.target) {
        errors.push(`Edge ${edge.id || index} is missing target`);
      }

      // Check if source and target exist
      if (model.nodes && Array.isArray(model.nodes)) {
        const sourceExists = model.nodes.some((n: any) => n.id === edge.source);
        const targetExists = model.nodes.some((n: any) => n.id === edge.target);

        if (!sourceExists) {
          errors.push(`Edge ${edge.id || index}: source node '${edge.source}' not found`);
        }

        if (!targetExists) {
          errors.push(`Edge ${edge.id || index}: target node '${edge.target}' not found`);
        }
      }
    });
  }

  // Check timestamps
  if (model.created_at && !isValidISODate(model.created_at)) {
    warnings.push('Invalid created_at timestamp');
  }

  if (model.updated_at && !isValidISODate(model.updated_at)) {
    warnings.push('Invalid updated_at timestamp');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    modelVersion: model.version?.toString(),
    isCompatible: errors.length === 0
  };
}

/**
 * Check if string is valid ISO 8601 date
 * 检查字符串是否为有效的ISO 8601日期
 *
 * @param dateString - Date string to check
 * @returns True if valid
 */
function isValidISODate(dateString: string): boolean {
  const date = new Date(dateString);
  return date instanceof Date && !isNaN(date.getTime());
}

// ============= Error Handling =============

/**
 * Create IO error
 * 创建IO错误
 *
 * @param type - Error type
 * @param message - Error message
 * @param recoverable - Whether error is recoverable
 * @param details - Additional details
 * @returns IOError object
 */
function createIOError(
  type: IOErrorType,
  message: string,
  recoverable: boolean,
  details?: string
): IOError {
  return {
    type,
    message,
    details,
    recoverable
  };
}

// ============= File Selection Helpers =============

/**
 * Create file input for model import
 * 创建文件输入用于模型导入
 *
 * @param onFileSelected - Callback when file is selected
 * @param accept - Accepted file types
 */
export function createFileInput(
  onFileSelected: (file: File) => void,
  accept: string = '.json,.hydro.json'
): HTMLInputElement {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = accept;
  input.style.display = 'none';

  input.addEventListener('change', (e) => {
    const files = (e.target as HTMLInputElement).files;
    if (files && files.length > 0) {
      onFileSelected(files[0]);
    }
  });

  return input;
}

/**
 * Prompt user to select and import model file
 * 提示用户选择并导入模型文件
 *
 * @returns Promise resolving to imported model or null if cancelled
 */
export function promptImportModel(): Promise<HydraulicModel | null> {
  return new Promise((resolve, reject) => {
    const input = createFileInput(async (file) => {
      try {
        const model = await importModelJSON(file);
        resolve(model);
      } catch (error) {
        reject(error);
      } finally {
        document.body.removeChild(input);
      }
    });

    input.addEventListener('cancel', () => {
      document.body.removeChild(input);
      resolve(null);
    });

    document.body.appendChild(input);
    input.click();
  });
}

// ============= Migration Helpers =============

/**
 * Migrate old model format to current version
 * 将旧模型格式迁移到当前版本
 *
 * @param oldModel - Old model data
 * @param fromVersion - Source version
 * @returns Migrated model
 */
export function migrateModel(oldModel: any, fromVersion: string): HydraulicModel {
  const [major, minor] = fromVersion.split('.').map(Number);

  let model = { ...oldModel };

  // Migration logic based on version
  if (major === 1 && minor < 5) {
    // Add v1.5.0 fields
    if (!model.tags) {
      model.tags = [];
    }
  }

  // Ensure all required fields exist
  if (!model.id) {
    model.id = crypto.randomUUID();
  }

  if (!model.created_at) {
    model.created_at = new Date().toISOString();
  }

  if (!model.updated_at) {
    model.updated_at = new Date().toISOString();
  }

  if (typeof model.version !== 'number') {
    model.version = 1;
  }

  if (typeof model.validated !== 'boolean') {
    model.validated = false;
  }

  return model as HydraulicModel;
}

// ============= Import Statistics =============

/**
 * Get import file information
 * 获取导入文件信息
 *
 * @param file - The file to analyze
 * @returns File information
 */
export interface ImportFileInfo {
  filename: string;
  size: number;
  sizeFormatted: string;
  type: string;
  lastModified: Date;
}

export async function getImportFileInfo(file: File): Promise<ImportFileInfo> {
  return {
    filename: file.name,
    size: file.size,
    sizeFormatted: formatFileSize(file.size),
    type: file.type || 'unknown',
    lastModified: new Date(file.lastModified)
  };
}

/**
 * Format file size in human-readable format
 * 格式化文件大小为可读格式
 *
 * @param bytes - File size in bytes
 * @returns Formatted string
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  } else {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
}
