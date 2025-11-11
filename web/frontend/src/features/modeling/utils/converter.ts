/**
 * Configuration Converter
 * 配置转换器 - 将图形模型转换为仿真配置
 */

import {
  HydraulicModel,
  NodeType,
  CanalNodeData,
  BoundaryNodeData
} from '../types/model.types';
import { SimulationRequest, SimulationConfig } from '@/services/api';

/**
 * 将图形模型转换为仿真配置
 */
export const convertModelToSimulationConfig = (
  model: HydraulicModel
): SimulationRequest | null => {
  if (!model || !model.nodes || model.nodes.length === 0) {
    return null;
  }

  // 查找明渠节点（作为主要计算域）
  const canalNode = model.nodes.find(n => n.type === NodeType.CANAL);
  if (!canalNode) {
    console.warn('No canal node found in model');
    return null;
  }

  const canalData = canalNode.data as CanalNodeData;

  // 查找边界条件
  const upstreamBoundary = model.nodes.find(
    n => (n.type === NodeType.BOUNDARY_FLOW || n.type === NodeType.BOUNDARY_DEPTH) &&
         (n.data as BoundaryNodeData).position === 'upstream'
  );

  const downstreamBoundary = model.nodes.find(
    n => (n.type === NodeType.BOUNDARY_FLOW || n.type === NodeType.BOUNDARY_DEPTH) &&
         (n.data as BoundaryNodeData).position === 'downstream'
  );

  // 转换边界类型：flow -> Q, depth -> h
  const convertBoundaryType = (type: 'flow' | 'depth'): 'h' | 'Q' => {
    return type === 'flow' ? 'Q' : 'h';
  };

  // 构建仿真配置
  const simulationConfig: SimulationConfig = {
    // 渠道参数
    width: canalData.width,
    length: canalData.length,
    n_cells: canalData.n_cells,
    manning_n: canalData.manning_n,
    slope: canalData.slope,

    // 时间参数（默认值，后续可以让用户配置）
    t_end: 100.0,
    dt_max: 1.0,
    output_interval: 1.0,

    // 初始条件
    initial_conditions: {
      type: 'uniform',
      h: canalData.initial_depth || 5.0,
      Q: canalData.initial_discharge || 0.0
    },

    // 边界条件 (默认使用wall边界)
    boundary_conditions: {
      upstream: { type: 'wall' },
      downstream: { type: 'wall' }
    },

    // 求解器配置
    cfl: 0.5,
    order: 2,
    use_numba: true
  };

  // 添加上游边界条件
  if (upstreamBoundary && simulationConfig.boundary_conditions) {
    const data = upstreamBoundary.data as BoundaryNodeData;
    simulationConfig.boundary_conditions.upstream = {
      type: convertBoundaryType(data.boundary_type),
      value: data.value
    };
  }

  // 添加下游边界条件
  if (downstreamBoundary && simulationConfig.boundary_conditions) {
    const data = downstreamBoundary.data as BoundaryNodeData;
    simulationConfig.boundary_conditions.downstream = {
      type: convertBoundaryType(data.boundary_type),
      value: data.value
    };
  }

  // 构建最终的仿真请求
  const request: SimulationRequest = {
    name: model.name || '未命名仿真',
    description: `从建模工作台生成 - 模型ID: ${model.id} - ${new Date().toLocaleString()}`,
    config: simulationConfig
  };

  return request;
};

/**
 * 检查模型是否可以转换为仿真配置
 */
export const canConvertToSimulation = (model: HydraulicModel | null): {
  canConvert: boolean;
  reason?: string;
} => {
  if (!model) {
    return { canConvert: false, reason: '模型为空' };
  }

  if (!model.nodes || model.nodes.length === 0) {
    return { canConvert: false, reason: '模型中没有节点' };
  }

  // 检查是否有明渠节点
  const hasCanalNode = model.nodes.some(n => n.type === NodeType.CANAL);
  if (!hasCanalNode) {
    return { canConvert: false, reason: '模型中没有明渠节点' };
  }

  // 检查是否已验证
  if (!model.validated) {
    return { canConvert: false, reason: '模型未经验证，请先验证模型' };
  }

  // 检查是否有错误
  if (model.validation_result && model.validation_result.errors.length > 0) {
    const hasErrors = model.validation_result.errors.some(e => e.severity === 'error');
    if (hasErrors) {
      return { canConvert: false, reason: '模型存在验证错误，请修复后再运行' };
    }
  }

  return { canConvert: true };
};

/**
 * 生成仿真配置的可读摘要
 */
export const generateConfigSummary = (config: SimulationRequest): string => {
  const canal = config.config;
  const lines = [
    `仿真名称: ${config.name}`,
    ``,
    `渠道参数:`,
    `- 长度: ${canal.length} m`,
    `- 宽度: ${canal.width} m`,
    `- 坡度: ${canal.slope}`,
    `- 曼宁系数: ${canal.manning_n}`,
    `- 网格数: ${canal.n_cells}`,
    ``,
    `时间参数:`,
    `- 仿真时长: ${canal.t_end} s`,
    `- 最大时间步长: ${canal.dt_max || 'auto'} s`,
    ``,
    `初始条件:`,
    `- 类型: ${canal.initial_conditions.type === 'uniform' ? '均匀流' : '溃坝'}`,
    `- 初始水深: ${canal.initial_conditions.h || 'N/A'} m`,
    `- 初始流量: ${canal.initial_conditions.Q || 'N/A'} m³/s`
  ];

  if (canal.boundary_conditions) {
    lines.push(``);
    lines.push(`边界条件:`);

    const getBoundaryLabel = (type: 'h' | 'Q' | 'wall') => {
      if (type === 'Q') return '流量';
      if (type === 'h') return '水深';
      return '固壁';
    };

    const getBoundaryUnit = (type: 'h' | 'Q' | 'wall') => {
      if (type === 'Q') return 'm³/s';
      if (type === 'h') return 'm';
      return '';
    };

    if (canal.boundary_conditions.upstream) {
      const bc = canal.boundary_conditions.upstream;
      const valueStr = bc.value !== undefined ? `= ${bc.value} ${getBoundaryUnit(bc.type)}` : '';
      lines.push(`- 上游: ${getBoundaryLabel(bc.type)} ${valueStr}`);
    }

    if (canal.boundary_conditions.downstream) {
      const bc = canal.boundary_conditions.downstream;
      const valueStr = bc.value !== undefined ? `= ${bc.value} ${getBoundaryUnit(bc.type)}` : '';
      lines.push(`- 下游: ${getBoundaryLabel(bc.type)} ${valueStr}`);
    }
  }

  return lines.join('\n');
};
