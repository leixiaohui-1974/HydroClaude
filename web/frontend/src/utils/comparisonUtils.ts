/**
 * Comparison Utility Functions
 * 对比工具函数
 *
 * v1.5.0 Feature: Multi-Scenario Comparison
 */

import type {
  ComparisonScenario,
  ComparisonMetrics,
  DifferenceData
} from '../types/comparison';

/**
 * Validate that two scenarios can be compared
 * 验证两个场景是否可以对比
 */
export function validateScenarios(
  scenarioA: ComparisonScenario,
  scenarioB: ComparisonScenario
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  const resultA = scenarioA.result;
  const resultB = scenarioB.result;

  // Check if both simulations completed successfully
  if (resultA.status !== 'completed') {
    errors.push(`Scenario "${scenarioA.name}" simulation did not complete successfully`);
  }
  if (resultB.status !== 'completed') {
    errors.push(`Scenario "${scenarioB.name}" simulation did not complete successfully`);
  }

  // Check spatial dimensions
  if (resultA.x.length !== resultB.x.length) {
    errors.push('Scenarios have different spatial dimensions');
  }

  // Check if spatial points are similar (allow small tolerance)
  const tolerance = 1e-6;
  for (let i = 0; i < Math.min(resultA.x.length, resultB.x.length); i++) {
    if (Math.abs(resultA.x[i] - resultB.x[i]) > tolerance) {
      errors.push(`Spatial points differ at index ${i}`);
      break;
    }
  }

  // Check time dimensions
  if (resultA.time.length !== resultB.time.length) {
    errors.push('Scenarios have different time dimensions');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Calculate comparison metrics between two scenarios
 * 计算两个场景之间的对比指标
 */
export function calculateComparisonMetrics(
  scenarioA: ComparisonScenario,
  scenarioB: ComparisonScenario,
  variable: 'h' | 'Q' | 'V'
): ComparisonMetrics {
  const resultA = scenarioA.result;
  const resultB = scenarioB.result;

  // Get data arrays for the specified variable
  const dataA = resultA[variable];
  const dataB = resultB[variable];

  let maxDiff = 0;
  let sumDiff = 0;
  let sumSquaredDiff = 0;
  let maxPercentDiff = 0;
  let sumPercentDiff = 0;
  let totalPoints = 0;
  let maxDiffLocation = {
    x: 0,
    time: 0,
    valueA: 0,
    valueB: 0
  };

  // Calculate differences
  for (let ti = 0; ti < dataA.length; ti++) {
    for (let xi = 0; xi < dataA[ti].length; xi++) {
      const valueA = dataA[ti][xi];
      const valueB = dataB[ti][xi];
      const diff = Math.abs(valueA - valueB);
      const percentDiff = valueA !== 0 ? (diff / Math.abs(valueA)) * 100 : 0;

      sumDiff += diff;
      sumSquaredDiff += diff * diff;
      sumPercentDiff += percentDiff;
      totalPoints++;

      if (diff > maxDiff) {
        maxDiff = diff;
        maxDiffLocation = {
          x: resultA.x[xi],
          time: resultA.time[ti],
          valueA,
          valueB
        };
      }

      if (percentDiff > maxPercentDiff) {
        maxPercentDiff = percentDiff;
      }
    }
  }

  const meanDiff = sumDiff / totalPoints;
  const rmse = Math.sqrt(sumSquaredDiff / totalPoints);
  const meanPercentDiff = sumPercentDiff / totalPoints;

  // Calculate correlation coefficient
  const correlation = calculateCorrelation(dataA, dataB);

  return {
    scenarioA: scenarioA.id,
    scenarioB: scenarioB.id,
    variable,
    maxDifference: maxDiff,
    meanDifference: meanDiff,
    rmse,
    maxPercentDifference: maxPercentDiff,
    meanPercentDifference: meanPercentDiff,
    correlation,
    maxDiffLocation
  };
}

/**
 * Calculate correlation coefficient between two data arrays
 * 计算两个数据数组之间的相关系数
 */
function calculateCorrelation(dataA: number[][], dataB: number[][]): number {
  let sumA = 0;
  let sumB = 0;
  let sumA2 = 0;
  let sumB2 = 0;
  let sumAB = 0;
  let n = 0;

  for (let ti = 0; ti < dataA.length; ti++) {
    for (let xi = 0; xi < dataA[ti].length; xi++) {
      const a = dataA[ti][xi];
      const b = dataB[ti][xi];
      sumA += a;
      sumB += b;
      sumA2 += a * a;
      sumB2 += b * b;
      sumAB += a * b;
      n++;
    }
  }

  const meanA = sumA / n;
  const meanB = sumB / n;
  const varA = (sumA2 / n) - (meanA * meanA);
  const varB = (sumB2 / n) - (meanB * meanB);
  const covariance = (sumAB / n) - (meanA * meanB);

  if (varA === 0 || varB === 0) {
    return 0;
  }

  return covariance / Math.sqrt(varA * varB);
}

/**
 * Calculate difference data between two scenarios
 * 计算两个场景之间的差异数据
 */
export function calculateDifferenceData(
  scenarioA: ComparisonScenario,
  scenarioB: ComparisonScenario,
  variable: 'h' | 'Q' | 'V'
): DifferenceData {
  const resultA = scenarioA.result;
  const resultB = scenarioB.result;

  const dataA = resultA[variable];
  const dataB = resultB[variable];

  const diff: number[][] = [];
  const percentDiff: number[][] = [];

  for (let ti = 0; ti < dataA.length; ti++) {
    const diffRow: number[] = [];
    const percentDiffRow: number[] = [];

    for (let xi = 0; xi < dataA[ti].length; xi++) {
      const valueA = dataA[ti][xi];
      const valueB = dataB[ti][xi];
      const difference = valueB - valueA; // B - A (not absolute)
      const percentDifference = valueA !== 0 ? (difference / valueA) * 100 : 0;

      diffRow.push(difference);
      percentDiffRow.push(percentDifference);
    }

    diff.push(diffRow);
    percentDiff.push(percentDiffRow);
  }

  return {
    x: resultA.x,
    time: resultA.time,
    diff,
    percentDiff
  };
}

/**
 * Get interpolated value at a specific time index
 * 获取指定时间索引的插值
 */
export function getInterpolatedValue(
  data: number[][],
  timeIndex: number,
  spatialIndex: number
): number {
  if (timeIndex < 0 || timeIndex >= data.length) {
    return 0;
  }
  if (spatialIndex < 0 || spatialIndex >= data[0].length) {
    return 0;
  }
  return data[timeIndex][spatialIndex];
}

/**
 * Find common time range across scenarios
 * 找到场景之间的公共时间范围
 */
export function findCommonTimeRange(scenarios: ComparisonScenario[]): {
  minTime: number;
  maxTime: number;
  minLength: number;
} {
  if (scenarios.length === 0) {
    return { minTime: 0, maxTime: 0, minLength: 0 };
  }

  let minTime = scenarios[0].result.time[0];
  let maxTime = scenarios[0].result.time[scenarios[0].result.time.length - 1];
  let minLength = scenarios[0].result.time.length;

  for (const scenario of scenarios) {
    const time = scenario.result.time;
    minTime = Math.max(minTime, time[0]);
    maxTime = Math.min(maxTime, time[time.length - 1]);
    minLength = Math.min(minLength, time.length);
  }

  return { minTime, maxTime, minLength };
}

/**
 * Format comparison metric for display
 * 格式化对比指标用于显示
 */
export function formatMetricValue(value: number, precision: number = 4): string {
  if (Math.abs(value) < 0.0001) {
    return value.toExponential(precision);
  }
  return value.toFixed(precision);
}

/**
 * Generate comparison report text
 * 生成对比报告文本
 */
export function generateComparisonReport(
  scenarioA: ComparisonScenario,
  scenarioB: ComparisonScenario,
  metrics: ComparisonMetrics
): string {
  const variable = metrics.variable;
  const variableNames = {
    h: '水深 (Water Depth)',
    Q: '流量 (Discharge)',
    V: '流速 (Velocity)'
  };

  const report = [
    '# 多场景对比报告',
    '# Multi-Scenario Comparison Report',
    '',
    `## 场景对比 / Scenario Comparison`,
    `- Scenario A: ${scenarioA.name}`,
    `- Scenario B: ${scenarioB.name}`,
    `- Variable: ${variableNames[variable]}`,
    '',
    `## 统计指标 / Statistical Metrics`,
    `- Max Difference: ${formatMetricValue(metrics.maxDifference)}`,
    `- Mean Difference: ${formatMetricValue(metrics.meanDifference)}`,
    `- RMSE: ${formatMetricValue(metrics.rmse)}`,
    `- Max % Difference: ${formatMetricValue(metrics.maxPercentDifference)}%`,
    `- Mean % Difference: ${formatMetricValue(metrics.meanPercentDifference)}%`,
    `- Correlation: ${formatMetricValue(metrics.correlation, 6)}`,
    '',
    `## 最大差异位置 / Maximum Difference Location`,
    `- Position (x): ${formatMetricValue(metrics.maxDiffLocation.x)} m`,
    `- Time: ${formatMetricValue(metrics.maxDiffLocation.time)} s`,
    `- Value A: ${formatMetricValue(metrics.maxDiffLocation.valueA)}`,
    `- Value B: ${formatMetricValue(metrics.maxDiffLocation.valueB)}`,
    `- Difference: ${formatMetricValue(metrics.maxDiffLocation.valueB - metrics.maxDiffLocation.valueA)}`,
    '',
    `Generated at: ${new Date().toISOString()}`
  ];

  return report.join('\n');
}

/**
 * Export comparison data as CSV
 * 导出对比数据为CSV
 */
export function exportComparisonCSV(
  scenarioA: ComparisonScenario,
  scenarioB: ComparisonScenario,
  variable: 'h' | 'Q' | 'V',
  timeIndex: number
): string {
  const resultA = scenarioA.result;
  const resultB = scenarioB.result;
  const dataA = resultA[variable][timeIndex];
  const dataB = resultB[variable][timeIndex];

  const headers = ['x (m)', `${scenarioA.name}`, `${scenarioB.name}`, 'Difference', '% Difference'];
  const rows: string[][] = [headers];

  for (let xi = 0; xi < dataA.length; xi++) {
    const x = resultA.x[xi];
    const valueA = dataA[xi];
    const valueB = dataB[xi];
    const diff = valueB - valueA;
    const percentDiff = valueA !== 0 ? (diff / valueA) * 100 : 0;

    rows.push([
      x.toFixed(2),
      valueA.toFixed(6),
      valueB.toFixed(6),
      diff.toFixed(6),
      percentDiff.toFixed(2)
    ]);
  }

  return rows.map(row => row.join(',')).join('\n');
}
