/**
 * 地理计算工具函数
 * 使用Turf.js进行地理空间计算
 */

import * as turf from '@turf/turf';
import type { Position } from 'geojson';

/**
 * 计算两点之间的距离（米）
 */
export const calculateDistance = (point1: Position, point2: Position): number => {
  const from = turf.point(point1);
  const to = turf.point(point2);
  return turf.distance(from, to, { units: 'meters' });
};

/**
 * 计算线段总长度（米）
 */
export const calculateTotalLength = (coordinates: Position[]): number => {
  if (coordinates.length < 2) return 0;
  
  const line = turf.lineString(coordinates);
  return turf.length(line, { units: 'meters' });
};

/**
 * 计算平均坡度
 * @param coordinates 坐标数组 [lng, lat, elevation]
 * @returns 平均坡度（小数）
 */
export const calculateAverageSlope = (
  coordinates: Position[],
  elevations: number[]
): number => {
  if (coordinates.length < 2 || elevations.length < 2) return 0;
  
  const totalLength = calculateTotalLength(coordinates);
  const elevationDiff = elevations[elevations.length - 1] - elevations[0];
  
  return totalLength > 0 ? Math.abs(elevationDiff) / totalLength : 0;
};

/**
 * 计算相邻节点之间的距离数组
 */
export const calculateSegmentLengths = (coordinates: Position[]): number[] => {
  const lengths: number[] = [];
  
  for (let i = 0; i < coordinates.length - 1; i++) {
    lengths.push(calculateDistance(coordinates[i], coordinates[i + 1]));
  }
  
  return lengths;
};

/**
 * 计算每个节点距起点的距离
 */
export const calculateDistancesFromStart = (coordinates: Position[]): number[] => {
  const distances: number[] = [0];
  let cumulative = 0;
  
  for (let i = 0; i < coordinates.length - 1; i++) {
    cumulative += calculateDistance(coordinates[i], coordinates[i + 1]);
    distances.push(cumulative);
  }
  
  return distances;
};

/**
 * 计算线段的中点
 */
export const calculateMidpoint = (point1: Position, point2: Position): Position => {
  const from = turf.point(point1);
  const to = turf.point(point2);
  const midpoint = turf.midpoint(from, to);
  return midpoint.geometry.coordinates;
};

/**
 * 简化线段（减少点数）
 * @param coordinates 原始坐标
 * @param tolerance 容差（米）
 * @returns 简化后的坐标
 */
export const simplifyLine = (
  coordinates: Position[],
  tolerance: number = 10
): Position[] => {
  if (coordinates.length < 3) return coordinates;
  
  const line = turf.lineString(coordinates);
  const simplified = turf.simplify(line, { tolerance: tolerance / 1000 }); // 转换为km
  return simplified.geometry.coordinates;
};

/**
 * 判断点是否在某个点附近（用于点击检测）
 * @param point 待检测的点
 * @param target 目标点
 * @param threshold 阈值（米）
 */
export const isPointNearby = (
  point: Position,
  target: Position,
  threshold: number = 20
): boolean => {
  const distance = calculateDistance(point, target);
  return distance <= threshold;
};

/**
 * 格式化距离显示
 */
export const formatDistance = (meters: number): string => {
  if (meters < 1000) {
    return `${meters.toFixed(1)} m`;
  } else {
    return `${(meters / 1000).toFixed(2)} km`;
  }
};

/**
 * 格式化坡度显示
 */
export const formatSlope = (slope: number): string => {
  return `${(slope * 100).toFixed(4)}%`;
};

/**
 * 高程插值
 * 根据起点和终点高程，线性插值中间节点的高程
 */
export const interpolateElevations = (
  distances: number[],
  startElevation: number,
  endElevation: number
): number[] => {
  const totalLength = distances[distances.length - 1];
  
  return distances.map((distance) => {
    const ratio = distance / totalLength;
    return startElevation + (endElevation - startElevation) * ratio;
  });
};
