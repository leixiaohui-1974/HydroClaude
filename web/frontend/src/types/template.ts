/**
 * Model Template Type Definitions
 * 模型模板类型定义
 *
 * v1.5.0 Feature: Model Templates
 */

import type { ModelNode, ModelEdge } from '@/features/modeling/types/model.types';

/**
 * Template category
 * 模板分类
 */
export type TemplateCategory =
  | 'dam-break'      // 溃坝
  | 'reservoir'      // 水库
  | 'channel'        // 渠道
  | 'river'          // 河流
  | 'flood'          // 洪水
  | 'drainage'       // 排水
  | 'irrigation'     // 灌溉
  | 'urban'          // 城市水文
  | 'custom';        // 自定义

/**
 * Template difficulty level
 * 模板难度等级
 */
export type TemplateDifficulty = 'beginner' | 'intermediate' | 'advanced';

/**
 * Template metadata
 * 模板元数据
 */
export interface TemplateMetadata {
  /**
   * Template ID
   * 模板ID
   */
  id: string;

  /**
   * Template name
   * 模板名称
   */
  name: string;

  /**
   * Template name in Chinese
   * 中文名称
   */
  nameCN: string;

  /**
   * Short description
   * 简短描述
   */
  description: string;

  /**
   * Description in Chinese
   * 中文描述
   */
  descriptionCN: string;

  /**
   * Template category
   * 模板分类
   */
  category: TemplateCategory;

  /**
   * Difficulty level
   * 难度等级
   */
  difficulty: TemplateDifficulty;

  /**
   * Tags for search
   * 搜索标签
   */
  tags: string[];

  /**
   * Author/Creator
   * 作者
   */
  author: string;

  /**
   * Creation date
   * 创建日期
   */
  createdAt: string;

  /**
   * Last update date
   * 最后更新日期
   */
  updatedAt: string;

  /**
   * Version
   * 版本
   */
  version: string;

  /**
   * Thumbnail URL or icon
   * 缩略图URL或图标
   */
  thumbnail?: string;

  /**
   * Usage count
   * 使用次数
   */
  usageCount?: number;

  /**
   * Rating (1-5)
   * 评分
   */
  rating?: number;
}

/**
 * Template configuration
 * 模板配置
 */
export interface TemplateConfig {
  /**
   * Recommended domain length (meters)
   * 推荐区域长度
   */
  domainLength: number;

  /**
   * Recommended time duration (seconds)
   * 推荐时长
   */
  duration: number;

  /**
   * Recommended time step (seconds)
   * 推荐时间步长
   */
  timeStep: number;

  /**
   * Manning coefficient
   * 曼宁系数
   */
  manning: number;

  /**
   * Recommended number of cells
   * 推荐单元数
   */
  nCells: number;

  /**
   * Initial conditions notes
   * 初始条件说明
   */
  initialConditions?: string;

  /**
   * Boundary conditions notes
   * 边界条件说明
   */
  boundaryConditions?: string;
}

/**
 * Template learning objectives
 * 模板学习目标
 */
export interface TemplateLearningObjective {
  /**
   * Objective description
   * 目标描述
   */
  objective: string;

  /**
   * Objective in Chinese
   * 中文目标
   */
  objectiveCN: string;

  /**
   * Expected outcome
   * 预期结果
   */
  outcome?: string;
}

/**
 * Model Template
 * 模型模板
 */
export interface ModelTemplate {
  /**
   * Template metadata
   * 模板元数据
   */
  metadata: TemplateMetadata;

  /**
   * Template configuration
   * 模板配置
   */
  config: TemplateConfig;

  /**
   * Model nodes
   * 模型节点
   */
  nodes: ModelNode[];

  /**
   * Model edges/connections
   * 模型连接
   */
  edges: ModelEdge[];

  /**
   * Learning objectives
   * 学习目标
   */
  learningObjectives?: TemplateLearningObjective[];

  /**
   * Usage instructions
   * 使用说明
   */
  instructions?: {
    en: string;
    cn: string;
  };

  /**
   * Expected results description
   * 预期结果描述
   */
  expectedResults?: {
    en: string;
    cn: string;
  };

  /**
   * References and resources
   * 参考资料
   */
  references?: string[];
}

/**
 * Template filter options
 * 模板筛选选项
 */
export interface TemplateFilter {
  /**
   * Filter by category
   * 按分类筛选
   */
  category?: TemplateCategory;

  /**
   * Filter by difficulty
   * 按难度筛选
   */
  difficulty?: TemplateDifficulty;

  /**
   * Search by text
   * 文本搜索
   */
  searchText?: string;

  /**
   * Filter by tags
   * 按标签筛选
   */
  tags?: string[];

  /**
   * Sort by field
   * 排序字段
   */
  sortBy?: 'name' | 'usageCount' | 'rating' | 'createdAt' | 'updatedAt';

  /**
   * Sort order
   * 排序方向
   */
  sortOrder?: 'asc' | 'desc';
}

/**
 * Category display names
 * 分类显示名称
 */
export const TEMPLATE_CATEGORY_NAMES: Record<TemplateCategory, { en: string; cn: string }> = {
  'dam-break': { en: 'Dam Break', cn: '溃坝' },
  'reservoir': { en: 'Reservoir', cn: '水库' },
  'channel': { en: 'Channel', cn: '渠道' },
  'river': { en: 'River', cn: '河流' },
  'flood': { en: 'Flood', cn: '洪水' },
  'drainage': { en: 'Drainage', cn: '排水' },
  'irrigation': { en: 'Irrigation', cn: '灌溉' },
  'urban': { en: 'Urban Hydrology', cn: '城市水文' },
  'custom': { en: 'Custom', cn: '自定义' }
};

/**
 * Difficulty display names
 * 难度显示名称
 */
export const DIFFICULTY_NAMES: Record<TemplateDifficulty, { en: string; cn: string; color: string }> = {
  'beginner': { en: 'Beginner', cn: '初级', color: '#52c41a' },
  'intermediate': { en: 'Intermediate', cn: '中级', color: '#1890ff' },
  'advanced': { en: 'Advanced', cn: '高级', color: '#fa8c16' }
};

/**
 * Default template filter
 * 默认模板筛选
 */
export const DEFAULT_TEMPLATE_FILTER: TemplateFilter = {
  sortBy: 'usageCount',
  sortOrder: 'desc'
};
