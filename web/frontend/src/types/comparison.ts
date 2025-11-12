/**
 * Multi-Scenario Comparison Type Definitions
 * 多场景对比类型定义
 *
 * v1.5.0 Feature: Multi-Scenario Comparison
 */

import type { SimulationResultResponse } from '../services/api';

/**
 * Comparison mode
 * 对比模式
 */
export type ComparisonMode = 'overlay' | 'sideBySide' | 'diff';

/**
 * Scenario for comparison
 * 对比场景
 */
export interface ComparisonScenario {
  /**
   * Unique identifier
   * 唯一标识符
   */
  id: string;

  /**
   * Display name
   * 显示名称
   */
  name: string;

  /**
   * Scenario color (for visualization)
   * 场景颜色（用于可视化）
   */
  color: string;

  /**
   * Simulation result
   * 仿真结果
   */
  result: SimulationResultResponse;

  /**
   * Visibility toggle
   * 可见性开关
   */
  visible: boolean;

  /**
   * Optional description
   * 可选描述
   */
  description?: string;
}

/**
 * Comparison configuration
 * 对比配置
 */
export interface ComparisonConfig {
  /**
   * Comparison mode
   * 对比模式
   */
  mode: ComparisonMode;

  /**
   * Synchronized time control
   * 同步时间控制
   */
  syncTime: boolean;

  /**
   * Show legend
   * 显示图例
   */
  showLegend: boolean;

  /**
   * Show difference statistics
   * 显示差异统计
   */
  showStats: boolean;

  /**
   * Variable to compare (h, Q, or V)
   * 对比的变量
   */
  variable: 'h' | 'Q' | 'V';
}

/**
 * Comparison metrics between two scenarios
 * 两个场景之间的对比指标
 */
export interface ComparisonMetrics {
  /**
   * Scenario A ID
   */
  scenarioA: string;

  /**
   * Scenario B ID
   */
  scenarioB: string;

  /**
   * Variable being compared
   * 对比的变量
   */
  variable: 'h' | 'Q' | 'V';

  /**
   * Maximum absolute difference
   * 最大绝对差异
   */
  maxDifference: number;

  /**
   * Mean absolute difference
   * 平均绝对差异
   */
  meanDifference: number;

  /**
   * Root mean square error
   * 均方根误差
   */
  rmse: number;

  /**
   * Maximum percentage difference
   * 最大百分比差异
   */
  maxPercentDifference: number;

  /**
   * Mean percentage difference
   * 平均百分比差异
   */
  meanPercentDifference: number;

  /**
   * Correlation coefficient
   * 相关系数
   */
  correlation: number;

  /**
   * Location of maximum difference (x, time)
   * 最大差异位置
   */
  maxDiffLocation: {
    x: number;
    time: number;
    valueA: number;
    valueB: number;
  };
}

/**
 * Difference data for visualization
 * 差异数据（用于可视化）
 */
export interface DifferenceData {
  /**
   * Spatial positions
   * 空间位置
   */
  x: number[];

  /**
   * Time points
   * 时间点
   */
  time: number[];

  /**
   * Difference values (2D array: [timeIndex][spatialIndex])
   * 差异值（二维数组）
   */
  diff: number[][];

  /**
   * Percentage difference (2D array)
   * 百分比差异（二维数组）
   */
  percentDiff: number[][];
}

/**
 * Comparison state
 * 对比状态
 */
export interface ComparisonState {
  /**
   * List of scenarios
   * 场景列表
   */
  scenarios: ComparisonScenario[];

  /**
   * Current comparison configuration
   * 当前对比配置
   */
  config: ComparisonConfig;

  /**
   * Current time index (synchronized across scenarios)
   * 当前时间索引（跨场景同步）
   */
  currentTimeIndex: number;

  /**
   * Selected scenarios for comparison (2 IDs)
   * 选中的对比场景（2个ID）
   */
  selectedPair: [string, string] | null;

  /**
   * Computed metrics
   * 计算的指标
   */
  metrics: ComparisonMetrics | null;
}

/**
 * Default color palette for scenarios
 * 默认场景颜色调色板
 */
export const DEFAULT_SCENARIO_COLORS = [
  '#1890ff', // Blue
  '#52c41a', // Green
  '#fa8c16', // Orange
  '#eb2f96', // Pink
  '#722ed1', // Purple
  '#13c2c2', // Cyan
  '#faad14', // Gold
  '#f5222d'  // Red
];

/**
 * Default comparison configuration
 * 默认对比配置
 */
export const DEFAULT_COMPARISON_CONFIG: ComparisonConfig = {
  mode: 'overlay',
  syncTime: true,
  showLegend: true,
  showStats: true,
  variable: 'h'
};

/**
 * Variable display names
 * 变量显示名称
 */
export const VARIABLE_NAMES: Record<'h' | 'Q' | 'V', { zh: string; en: string; unit: string }> = {
  h: { zh: '水深', en: 'Water Depth', unit: 'm' },
  Q: { zh: '流量', en: 'Discharge', unit: 'm³/s' },
  V: { zh: '流速', en: 'Velocity', unit: 'm/s' }
};
