/**
 * Template Utility Functions
 * 模板工具函数
 *
 * v1.5.0 Feature: Model Templates
 */

import type { ModelTemplate, TemplateFilter } from '../types/template';
import type { ModelNode, ModelEdge } from '../types/model-io';

/**
 * Filter templates based on criteria
 * 根据条件筛选模板
 */
export function filterTemplates(
  templates: ModelTemplate[],
  filter: TemplateFilter
): ModelTemplate[] {
  let filtered = [...templates];

  // Filter by category
  if (filter.category) {
    filtered = filtered.filter(t => t.metadata.category === filter.category);
  }

  // Filter by difficulty
  if (filter.difficulty) {
    filtered = filtered.filter(t => t.metadata.difficulty === filter.difficulty);
  }

  // Filter by tags
  if (filter.tags && filter.tags.length > 0) {
    filtered = filtered.filter(t =>
      filter.tags!.some(tag => t.metadata.tags.includes(tag))
    );
  }

  // Search by text
  if (filter.searchText) {
    const query = filter.searchText.toLowerCase();
    filtered = filtered.filter(t =>
      t.metadata.name.toLowerCase().includes(query) ||
      t.metadata.nameCN.includes(filter.searchText!) ||
      t.metadata.description.toLowerCase().includes(query) ||
      t.metadata.descriptionCN.includes(filter.searchText!) ||
      t.metadata.tags.some(tag => tag.toLowerCase().includes(query))
    );
  }

  // Sort templates
  if (filter.sortBy) {
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (filter.sortBy) {
        case 'name':
          comparison = a.metadata.name.localeCompare(b.metadata.name);
          break;
        case 'usageCount':
          comparison = (a.metadata.usageCount || 0) - (b.metadata.usageCount || 0);
          break;
        case 'rating':
          comparison = (a.metadata.rating || 0) - (b.metadata.rating || 0);
          break;
        case 'createdAt':
          comparison = new Date(a.metadata.createdAt).getTime() - new Date(b.metadata.createdAt).getTime();
          break;
        case 'updatedAt':
          comparison = new Date(a.metadata.updatedAt).getTime() - new Date(b.metadata.updatedAt).getTime();
          break;
      }

      return filter.sortOrder === 'desc' ? -comparison : comparison;
    });
  }

  return filtered;
}

/**
 * Apply template to model
 * 将模板应用到模型
 *
 * @param template - Template to apply
 * @returns Model data from template
 */
export function applyTemplate(template: ModelTemplate): {
  nodes: ModelNode[];
  edges: ModelEdge[];
  config: any;
} {
  // Deep clone to avoid mutating the original template
  const nodes = JSON.parse(JSON.stringify(template.nodes)) as ModelNode[];
  const edges = JSON.parse(JSON.stringify(template.edges)) as ModelEdge[];

  // Build config object for the model
  const config = {
    duration: template.config.duration,
    timeStep: template.config.timeStep,
    outputInterval: template.config.timeStep * 10, // Output every 10 time steps
    manning: template.config.manning,
    gravity: 9.81,
    theta: 0.6 // Implicit scheme parameter
  };

  return { nodes, edges, config };
}

/**
 * Clone template with new ID
 * 克隆模板并分配新ID
 */
export function cloneTemplate(template: ModelTemplate, newName: string): ModelTemplate {
  const cloned = JSON.parse(JSON.stringify(template)) as ModelTemplate;

  cloned.metadata.id = `custom-${Date.now()}`;
  cloned.metadata.name = newName;
  cloned.metadata.nameCN = newName;
  cloned.metadata.category = 'custom';
  cloned.metadata.createdAt = new Date().toISOString();
  cloned.metadata.updatedAt = new Date().toISOString();
  cloned.metadata.usageCount = 0;

  return cloned;
}

/**
 * Validate template structure
 * 验证模板结构
 */
export function validateTemplate(template: ModelTemplate): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check metadata
  if (!template.metadata.id) {
    errors.push('Template ID is required');
  }
  if (!template.metadata.name) {
    errors.push('Template name is required');
  }

  // Check config
  if (!template.config.domainLength || template.config.domainLength <= 0) {
    errors.push('Domain length must be positive');
  }
  if (!template.config.duration || template.config.duration <= 0) {
    errors.push('Duration must be positive');
  }
  if (!template.config.timeStep || template.config.timeStep <= 0) {
    errors.push('Time step must be positive');
  }

  // Check nodes
  if (!template.nodes || template.nodes.length === 0) {
    errors.push('Template must have at least one node');
  }

  // Check for at least one canal node
  const hasCanalNode = template.nodes.some(n => n.type === 'canal');
  if (!hasCanalNode) {
    warnings.push('Template should have at least one canal node');
  }

  // Check edges
  if (!template.edges || template.edges.length === 0) {
    warnings.push('Template has no edges - nodes may be disconnected');
  }

  // Validate edge references
  if (template.edges) {
    for (const edge of template.edges) {
      const sourceExists = template.nodes.some(n => n.id === edge.source);
      const targetExists = template.nodes.some(n => n.id === edge.target);

      if (!sourceExists) {
        errors.push(`Edge ${edge.id} references non-existent source node ${edge.source}`);
      }
      if (!targetExists) {
        errors.push(`Edge ${edge.id} references non-existent target node ${edge.target}`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Get unique tags from templates
 * 从模板中获取唯一标签
 */
export function getUniqueTags(templates: ModelTemplate[]): string[] {
  const tagSet = new Set<string>();
  templates.forEach(t => {
    t.metadata.tags.forEach(tag => tagSet.add(tag));
  });
  return Array.from(tagSet).sort();
}

/**
 * Get template statistics
 * 获取模板统计信息
 */
export function getTemplateStatistics(templates: ModelTemplate[]): {
  totalTemplates: number;
  categoryCounts: Record<string, number>;
  difficultyCounts: Record<string, number>;
  averageRating: number;
  totalUsage: number;
} {
  const categoryCounts: Record<string, number> = {};
  const difficultyCounts: Record<string, number> = {};
  let totalRating = 0;
  let ratingCount = 0;
  let totalUsage = 0;

  templates.forEach(t => {
    // Count categories
    categoryCounts[t.metadata.category] = (categoryCounts[t.metadata.category] || 0) + 1;

    // Count difficulties
    difficultyCounts[t.metadata.difficulty] = (difficultyCounts[t.metadata.difficulty] || 0) + 1;

    // Sum ratings
    if (t.metadata.rating) {
      totalRating += t.metadata.rating;
      ratingCount++;
    }

    // Sum usage
    totalUsage += t.metadata.usageCount || 0;
  });

  return {
    totalTemplates: templates.length,
    categoryCounts,
    difficultyCounts,
    averageRating: ratingCount > 0 ? totalRating / ratingCount : 0,
    totalUsage
  };
}

/**
 * Increment template usage count
 * 增加模板使用次数
 */
export function incrementTemplateUsage(templateId: string): void {
  // In a real app, this would update the database
  // For now, we'll just store in localStorage
  const usageKey = `template_usage_${templateId}`;
  const currentUsage = parseInt(localStorage.getItem(usageKey) || '0', 10);
  localStorage.setItem(usageKey, (currentUsage + 1).toString());
}

/**
 * Get template usage count from localStorage
 * 从localStorage获取模板使用次数
 */
export function getTemplateUsageCount(templateId: string): number {
  const usageKey = `template_usage_${templateId}`;
  return parseInt(localStorage.getItem(usageKey) || '0', 10);
}

/**
 * Export template to JSON
 * 导出模板为JSON
 */
export function exportTemplateToJSON(template: ModelTemplate): string {
  return JSON.stringify(template, null, 2);
}

/**
 * Import template from JSON
 * 从JSON导入模板
 */
export function importTemplateFromJSON(jsonString: string): {
  success: boolean;
  template?: ModelTemplate;
  error?: string;
} {
  try {
    const template = JSON.parse(jsonString) as ModelTemplate;
    const validation = validateTemplate(template);

    if (!validation.valid) {
      return {
        success: false,
        error: `Template validation failed: ${validation.errors.join(', ')}`
      };
    }

    return {
      success: true,
      template
    };
  } catch (error) {
    return {
      success: false,
      error: `Failed to parse JSON: ${(error as Error).message}`
    };
  }
}
