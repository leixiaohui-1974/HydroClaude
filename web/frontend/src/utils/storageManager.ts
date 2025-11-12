/**
 * Storage Manager Utilities
 * 存储管理工具
 *
 * v1.5.0 Feature: localStorage management
 */

import type { HydraulicModel } from '../features/modeling/types/model.types';
import type { RecentModel, StorageQuota } from '../types/model-io';
import { STORAGE_KEYS } from '../types/model-io';

// ============= Storage Quota =============

/**
 * Check localStorage quota and usage
 * 检查localStorage配额和使用情况
 *
 * @returns Storage quota information
 */
export function checkStorageQuota(): StorageQuota {
  let used = 0;
  let itemCount = 0;

  // Calculate used space
  for (const key in localStorage) {
    if (key.startsWith('hydroclaude_')) {
      const value = localStorage.getItem(key);
      if (value) {
        used += key.length + value.length;

        // Count models
        if (key === STORAGE_KEYS.MODELS) {
          try {
            const models = JSON.parse(value);
            if (Array.isArray(models)) {
              itemCount = models.length;
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
  }

  // Conservative limit: 5 MB
  const available = 5 * 1024 * 1024;
  const percentage = (used / available) * 100;

  return {
    used,
    available,
    percentage: Math.min(percentage, 100),
    itemCount
  };
}

/**
 * Format bytes to human-readable string
 * 格式化字节为可读字符串
 *
 * @param bytes - Number of bytes
 * @returns Formatted string
 */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  } else {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
}

/**
 * Check if storage is near quota
 * 检查存储是否接近配额
 *
 * @param threshold - Warning threshold (0-100)
 * @returns True if near quota
 */
export function isStorageNearQuota(threshold: number = 80): boolean {
  const quota = checkStorageQuota();
  return quota.percentage >= threshold;
}

// ============= Model Management =============

/**
 * Get all saved models
 * 获取所有保存的模型
 *
 * @returns Array of models
 */
export function getSavedModels(): HydraulicModel[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.MODELS);
    if (!saved) return [];

    const models = JSON.parse(saved);
    return Array.isArray(models) ? models : [];
  } catch (error) {
    console.error('Failed to get saved models:', error);
    return [];
  }
}

/**
 * Save models to localStorage
 * 保存模型到localStorage
 *
 * @param models - Array of models
 * @returns Success status
 */
export function saveModels(models: HydraulicModel[]): boolean {
  try {
    localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(models));
    return true;
  } catch (error) {
    console.error('Failed to save models:', error);
    return false;
  }
}

/**
 * Get a single model by ID
 * 通过ID获取单个模型
 *
 * @param id - Model ID
 * @returns Model or null if not found
 */
export function getModelById(id: string): HydraulicModel | null {
  const models = getSavedModels();
  return models.find((m) => m.id === id) || null;
}

/**
 * Delete models by IDs
 * 通过ID删除模型
 *
 * @param ids - Array of model IDs to delete
 * @returns Number of models deleted
 */
export function deleteModels(ids: string[]): number {
  const models = getSavedModels();
  const filtered = models.filter((m) => !ids.includes(m.id));
  const deletedCount = models.length - filtered.length;

  if (deletedCount > 0) {
    saveModels(filtered);
  }

  return deletedCount;
}

// ============= Cleanup =============

/**
 * Clean up old models (keep most recent N models)
 * 清理旧模型（保留最近的N个模型）
 *
 * @param keepCount - Number of models to keep
 * @returns Number of models deleted
 */
export function cleanupOldModels(keepCount: number = 10): number {
  const models = getSavedModels();

  if (models.length <= keepCount) {
    return 0; // Nothing to cleanup
  }

  // Sort by updated_at (most recent first)
  const sorted = models.sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  // Keep only the most recent N
  const keep = sorted.slice(0, keepCount);
  saveModels(keep);

  return models.length - keep.length;
}

/**
 * Clean up models larger than size threshold
 * 清理超过大小阈值的模型
 *
 * @param maxSizeKB - Maximum size in KB
 * @returns Number of models deleted
 */
export function cleanupLargeModels(maxSizeKB: number = 500): number {
  const models = getSavedModels();
  const maxBytes = maxSizeKB * 1024;

  const filtered = models.filter((model) => {
    const size = JSON.stringify(model).length;
    return size <= maxBytes;
  });

  const deletedCount = models.length - filtered.length;

  if (deletedCount > 0) {
    saveModels(filtered);
  }

  return deletedCount;
}

/**
 * Clean up all HydroClaude data from localStorage
 * 清理localStorage中的所有HydroClaude数据
 *
 * WARNING: This will delete all saved models and settings!
 */
export function clearAllData(): void {
  Object.values(STORAGE_KEYS).forEach((key) => {
    localStorage.removeItem(key);
  });
}

// ============= Recent Models =============

/**
 * Get recent models list
 * 获取最近使用的模型列表
 *
 * @param limit - Maximum number of recent models
 * @returns Array of recent models
 */
export function getRecentModels(limit: number = 10): RecentModel[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.RECENT);
    if (!saved) return [];

    const recent = JSON.parse(saved);
    if (!Array.isArray(recent)) return [];

    return recent.slice(0, limit);
  } catch (error) {
    console.error('Failed to get recent models:', error);
    return [];
  }
}

/**
 * Add model to recent list
 * 添加模型到最近列表
 *
 * @param model - The model to add
 */
export function addToRecent(model: HydraulicModel): void {
  try {
    const recent = getRecentModels(50); // Get more to ensure we don't lose data

    // Remove if already exists
    const filtered = recent.filter((r) => r.id !== model.id);

    // Add to front
    filtered.unshift({
      id: model.id,
      name: model.name,
      accessedAt: new Date().toISOString(),
      thumbnail: (model as any).thumbnail
    });

    // Keep only last 10
    const trimmed = filtered.slice(0, 10);

    localStorage.setItem(STORAGE_KEYS.RECENT, JSON.stringify(trimmed));
  } catch (error) {
    console.error('Failed to update recent models:', error);
  }
}

/**
 * Clear recent models list
 * 清空最近模型列表
 */
export function clearRecentModels(): void {
  localStorage.removeItem(STORAGE_KEYS.RECENT);
}

// ============= Export/Import =============

/**
 * Export all models as JSON string
 * 导出所有模型为JSON字符串
 *
 * @returns JSON string containing all models
 */
export function exportAllModelsJSON(): string {
  const models = getSavedModels();
  const exportData = {
    format: 'HydroClaude Models Archive',
    version: '1.5.0',
    exportDate: new Date().toISOString(),
    modelCount: models.length,
    models
  };

  return JSON.stringify(exportData, null, 2);
}

/**
 * Import models from JSON string
 * 从JSON字符串导入模型
 *
 * @param jsonString - JSON string containing models
 * @param merge - If true, merge with existing models; if false, replace all
 * @returns Number of models imported
 */
export function importModelsFromJSON(
  jsonString: string,
  merge: boolean = true
): number {
  try {
    const data = JSON.parse(jsonString);

    if (
      !data ||
      !data.format ||
      !data.format.includes('HydroClaude') ||
      !Array.isArray(data.models)
    ) {
      throw new Error('Invalid import format');
    }

    const existingModels = merge ? getSavedModels() : [];
    const newModels = data.models as HydraulicModel[];

    // Merge or replace
    let merged: HydraulicModel[];

    if (merge) {
      // Add new models, update existing ones
      merged = [...existingModels];

      newModels.forEach((newModel) => {
        const existingIndex = merged.findIndex((m) => m.id === newModel.id);
        if (existingIndex >= 0) {
          // Update existing
          merged[existingIndex] = newModel;
        } else {
          // Add new
          merged.push(newModel);
        }
      });
    } else {
      // Replace all
      merged = newModels;
    }

    saveModels(merged);
    return newModels.length;
  } catch (error) {
    console.error('Failed to import models:', error);
    throw error;
  }
}

// ============= Statistics =============

/**
 * Get storage statistics
 * 获取存储统计信息
 *
 * @returns Storage statistics
 */
export interface StorageStatistics {
  quota: StorageQuota;
  modelCount: number;
  recentCount: number;
  totalNodes: number;
  totalEdges: number;
  averageModelSize: number;
  largestModel: {
    id: string;
    name: string;
    size: number;
  } | null;
}

export function getStorageStatistics(): StorageStatistics {
  const quota = checkStorageQuota();
  const models = getSavedModels();
  const recent = getRecentModels();

  let totalNodes = 0;
  let totalEdges = 0;
  let largestModel: StorageStatistics['largestModel'] = null;
  let largestSize = 0;

  models.forEach((model) => {
    totalNodes += model.nodes.length;
    totalEdges += model.edges.length;

    const size = JSON.stringify(model).length;
    if (size > largestSize) {
      largestSize = size;
      largestModel = {
        id: model.id,
        name: model.name,
        size
      };
    }
  });

  const averageModelSize =
    models.length > 0
      ? models.reduce((sum, m) => sum + JSON.stringify(m).length, 0) /
        models.length
      : 0;

  return {
    quota,
    modelCount: models.length,
    recentCount: recent.length,
    totalNodes,
    totalEdges,
    averageModelSize,
    largestModel
  };
}

// ============= Validation =============

/**
 * Validate storage integrity
 * 验证存储完整性
 *
 * @returns Validation result
 */
export interface StorageValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function validateStorage(): StorageValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  try {
    // Check models
    const modelsData = localStorage.getItem(STORAGE_KEYS.MODELS);
    if (modelsData) {
      try {
        const models = JSON.parse(modelsData);
        if (!Array.isArray(models)) {
          errors.push('Models data is not an array');
        } else {
          models.forEach((model, index) => {
            if (!model.id) {
              errors.push(`Model at index ${index} is missing ID`);
            }
            if (!model.name) {
              errors.push(`Model at index ${index} is missing name`);
            }
            if (!Array.isArray(model.nodes)) {
              errors.push(`Model at index ${index} has invalid nodes`);
            }
            if (!Array.isArray(model.edges)) {
              errors.push(`Model at index ${index} has invalid edges`);
            }
          });
        }
      } catch (e) {
        errors.push('Failed to parse models data');
      }
    }

    // Check recent models
    const recentData = localStorage.getItem(STORAGE_KEYS.RECENT);
    if (recentData) {
      try {
        const recent = JSON.parse(recentData);
        if (!Array.isArray(recent)) {
          warnings.push('Recent models data is not an array');
        }
      } catch (e) {
        warnings.push('Failed to parse recent models data');
      }
    }

    // Check quota
    const quota = checkStorageQuota();
    if (quota.percentage > 90) {
      warnings.push(
        `Storage is ${quota.percentage.toFixed(1)}% full (${formatBytes(quota.used)} / ${formatBytes(quota.available)})`
      );
    }
  } catch (error) {
    errors.push(`Storage validation failed: ${(error as Error).message}`);
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Repair storage (attempt to fix common issues)
 * 修复存储（尝试修复常见问题）
 *
 * @returns Repair result
 */
export function repairStorage(): {
  success: boolean;
  fixed: string[];
  errors: string[];
} {
  const fixed: string[] = [];
  const errors: string[] = [];

  try {
    // Try to parse and fix models
    const modelsData = localStorage.getItem(STORAGE_KEYS.MODELS);
    if (modelsData) {
      try {
        let models = JSON.parse(modelsData);

        if (!Array.isArray(models)) {
          models = [];
          fixed.push('Reset invalid models array');
        }

        // Remove invalid models
        const validModels = models.filter((model: any) => {
          return (
            model &&
            typeof model === 'object' &&
            model.id &&
            model.name &&
            Array.isArray(model.nodes) &&
            Array.isArray(model.edges)
          );
        });

        if (validModels.length < models.length) {
          fixed.push(
            `Removed ${models.length - validModels.length} invalid models`
          );
        }

        saveModels(validModels);
      } catch (e) {
        errors.push('Failed to repair models data');
      }
    }

    // Try to fix recent models
    const recentData = localStorage.getItem(STORAGE_KEYS.RECENT);
    if (recentData) {
      try {
        let recent = JSON.parse(recentData);

        if (!Array.isArray(recent)) {
          recent = [];
          fixed.push('Reset invalid recent models array');
        }

        localStorage.setItem(STORAGE_KEYS.RECENT, JSON.stringify(recent));
      } catch (e) {
        errors.push('Failed to repair recent models data');
      }
    }
  } catch (error) {
    errors.push(`Storage repair failed: ${(error as Error).message}`);
  }

  return {
    success: errors.length === 0,
    fixed,
    errors
  };
}
