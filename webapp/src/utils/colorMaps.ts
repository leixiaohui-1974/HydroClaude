/**
 * 颜色映射工具
 * 用于将数值映射到颜色
 */

export type ColorMapType = 'viridis' | 'plasma' | 'coolwarm' | 'depth' | 'velocity';

/**
 * RGB颜色
 */
export interface RGBColor {
  r: number;
  g: number;
  b: number;
}

/**
 * 预定义的颜色映射方案
 */
export const COLOR_MAPS = {
  // 水深颜色方案（深蓝 → 浅蓝 → 青 → 黄）
  depth: [
    { value: 0.0, color: { r: 0, g: 0, b: 139 } },       // 深蓝
    { value: 0.25, color: { r: 0, g: 100, b: 255 } },    // 蓝
    { value: 0.5, color: { r: 0, g: 191, b: 255 } },     // 浅蓝
    { value: 0.75, color: { r: 135, g: 206, b: 250 } },  // 天蓝
    { value: 1.0, color: { r: 255, g: 255, b: 0 } },     // 黄色
  ],
  
  // 流速颜色方案（蓝 → 绿 → 黄 → 红）
  velocity: [
    { value: 0.0, color: { r: 0, g: 0, b: 255 } },       // 蓝
    { value: 0.33, color: { r: 0, g: 255, b: 0 } },      // 绿
    { value: 0.67, color: { r: 255, g: 255, b: 0 } },    // 黄
    { value: 1.0, color: { r: 255, g: 0, b: 0 } },       // 红
  ],
  
  // Viridis配色（科学可视化标准）
  viridis: [
    { value: 0.0, color: { r: 68, g: 1, b: 84 } },
    { value: 0.25, color: { r: 59, g: 82, b: 139 } },
    { value: 0.5, color: { r: 33, g: 145, b: 140 } },
    { value: 0.75, color: { r: 94, g: 201, b: 98 } },
    { value: 1.0, color: { r: 253, g: 231, b: 37 } },
  ],
  
  // Plasma配色
  plasma: [
    { value: 0.0, color: { r: 13, g: 8, b: 135 } },
    { value: 0.25, color: { r: 126, g: 3, b: 168 } },
    { value: 0.5, color: { r: 204, g: 71, b: 120 } },
    { value: 0.75, color: { r: 248, g: 149, b: 64 } },
    { value: 1.0, color: { r: 240, g: 249, b: 33 } },
  ],
  
  // CoolWarm配色（冷暖色）
  coolwarm: [
    { value: 0.0, color: { r: 59, g: 76, b: 192 } },     // 冷蓝
    { value: 0.25, color: { r: 144, g: 178, b: 254 } },
    { value: 0.5, color: { r: 221, g: 221, b: 221 } },   // 白
    { value: 0.75, color: { r: 245, g: 156, b: 125 } },
    { value: 1.0, color: { r: 180, g: 4, b: 38 } },      // 暖红
  ],
};

/**
 * 线性插值两个颜色
 */
const interpolateColor = (color1: RGBColor, color2: RGBColor, ratio: number): RGBColor => {
  return {
    r: Math.round(color1.r + (color2.r - color1.r) * ratio),
    g: Math.round(color1.g + (color2.g - color1.g) * ratio),
    b: Math.round(color1.b + (color2.b - color1.b) * ratio),
  };
};

/**
 * 将数值映射到颜色
 * @param value 数值（将被归一化到[0,1]）
 * @param min 最小值
 * @param max 最大值
 * @param colorMapType 颜色映射类型
 * @returns RGB颜色
 */
export const mapValueToColor = (
  value: number,
  min: number,
  max: number,
  colorMapType: ColorMapType = 'depth'
): RGBColor => {
  // 归一化到[0, 1]
  const normalized = Math.max(0, Math.min(1, (value - min) / (max - min)));
  
  const colorMap = COLOR_MAPS[colorMapType];
  
  // 找到相邻的两个颜色点
  for (let i = 0; i < colorMap.length - 1; i++) {
    const point1 = colorMap[i];
    const point2 = colorMap[i + 1];
    
    if (normalized >= point1.value && normalized <= point2.value) {
      const ratio = (normalized - point1.value) / (point2.value - point1.value);
      return interpolateColor(point1.color, point2.color, ratio);
    }
  }
  
  // 边界情况
  return normalized < 0.5 ? colorMap[0].color : colorMap[colorMap.length - 1].color;
};

/**
 * RGB转16进制颜色字符串
 */
export const rgbToHex = (color: RGBColor): string => {
  const toHex = (n: number) => {
    const hex = Math.round(n).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };
  return `#${toHex(color.r)}${toHex(color.g)}${toHex(color.b)}`;
};

/**
 * 获取颜色字符串
 * @param value 数值
 * @param min 最小值
 * @param max 最大值
 * @param colorMapType 颜色映射类型
 * @returns 16进制颜色字符串
 */
export const getColorString = (
  value: number,
  min: number,
  max: number,
  colorMapType: ColorMapType = 'depth'
): string => {
  const rgb = mapValueToColor(value, min, max, colorMapType);
  return rgbToHex(rgb);
};

/**
 * 生成图例数据
 * @param min 最小值
 * @param max 最大值
 * @param steps 步数
 * @param colorMapType 颜色映射类型
 */
export const generateLegendData = (
  min: number,
  max: number,
  steps: number = 10,
  colorMapType: ColorMapType = 'depth'
): Array<{ value: number; color: string; label: string }> => {
  const data = [];
  for (let i = 0; i <= steps; i++) {
    const value = min + (max - min) * (i / steps);
    const color = getColorString(value, min, max, colorMapType);
    const label = value.toFixed(2);
    data.push({ value, color, label });
  }
  return data.reverse(); // 从大到小显示
};

/**
 * 计算合适的颜色范围
 * @param values 数值数组
 * @param percentile 百分位数（用于排除极值）
 */
export const calculateColorRange = (
  values: number[],
  percentile: number = 0.95
): { min: number; max: number } => {
  if (values.length === 0) return { min: 0, max: 1 };
  
  const sorted = [...values].sort((a, b) => a - b);
  const minIndex = Math.floor(sorted.length * (1 - percentile) / 2);
  const maxIndex = Math.floor(sorted.length * (1 + percentile) / 2);
  
  return {
    min: sorted[minIndex] || sorted[0],
    max: sorted[maxIndex] || sorted[sorted.length - 1],
  };
};
