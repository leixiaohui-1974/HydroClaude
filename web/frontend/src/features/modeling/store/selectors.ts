/**
 * Model Selectors
 * 建模工作台状态选择器
 */

import { RootState } from '@/shared/store';
import { ModelNode, ModelEdge, NodeType } from '../types/model.types';

// ============= 基础选择器 =============

/**
 * 获取当前模型
 */
export const selectCurrentModel = (state: RootState) => state.model.currentModel;

/**
 * 获取所有节点
 */
export const selectAllNodes = (state: RootState) => state.model.currentModel?.nodes || [];

/**
 * 获取所有边
 */
export const selectAllEdges = (state: RootState) => state.model.currentModel?.edges || [];

// ============= 选中状态 =============

/**
 * 获取选中的节点ID列表
 */
export const selectSelectedNodeIds = (state: RootState) => state.model.selectedNodeIds;

/**
 * 获取选中的边ID列表
 */
export const selectSelectedEdgeIds = (state: RootState) => state.model.selectedEdgeIds;

/**
 * 获取选中的节点
 */
export const selectSelectedNodes = (state: RootState): ModelNode[] => {
  const nodes = selectAllNodes(state);
  const selectedIds = selectSelectedNodeIds(state);
  return nodes.filter(node => selectedIds.includes(node.id));
};

/**
 * 获取当前选中的单个节点 (如果只选中一个)
 */
export const selectSingleSelectedNode = (state: RootState): ModelNode | null => {
  const selectedNodes = selectSelectedNodes(state);
  return selectedNodes.length === 1 ? selectedNodes[0] : null;
};

// ============= 节点查询 =============

/**
 * 根据ID获取节点
 */
export const selectNodeById = (state: RootState, nodeId: string): ModelNode | undefined => {
  return selectAllNodes(state).find(node => node.id === nodeId);
};

/**
 * 根据类型获取节点
 */
export const selectNodesByType = (state: RootState, type: NodeType): ModelNode[] => {
  return selectAllNodes(state).filter(node => node.type === type);
};

/**
 * 获取明渠节点
 */
export const selectCanalNodes = (state: RootState) => {
  return selectNodesByType(state, NodeType.CANAL);
};

/**
 * 获取闸门节点
 */
export const selectGateNodes = (state: RootState) => {
  return selectNodesByType(state, NodeType.GATE);
};

/**
 * 获取边界节点
 */
export const selectBoundaryNodes = (state: RootState) => {
  const flowBoundaries = selectNodesByType(state, NodeType.BOUNDARY_FLOW);
  const depthBoundaries = selectNodesByType(state, NodeType.BOUNDARY_DEPTH);
  return [...flowBoundaries, ...depthBoundaries];
};

// ============= 边查询 =============

/**
 * 根据ID获取边
 */
export const selectEdgeById = (state: RootState, edgeId: string): ModelEdge | undefined => {
  return selectAllEdges(state).find(edge => edge.id === edgeId);
};

/**
 * 获取连接到指定节点的边
 */
export const selectEdgesForNode = (state: RootState, nodeId: string): ModelEdge[] => {
  return selectAllEdges(state).filter(
    edge => edge.source === nodeId || edge.target === nodeId
  );
};

// ============= 验证状态 =============

/**
 * 获取模型验证状态
 */
export const selectModelValidated = (state: RootState) => {
  return state.model.currentModel?.validated || false;
};

/**
 * 获取验证结果
 */
export const selectValidationResult = (state: RootState) => {
  return state.model.currentModel?.validation_result;
};

/**
 * 获取验证错误
 */
export const selectValidationErrors = (state: RootState) => {
  return state.model.currentModel?.validation_result?.errors || [];
};

/**
 * 判断是否有验证错误
 */
export const selectHasValidationErrors = (state: RootState) => {
  const errors = selectValidationErrors(state);
  return errors.some(err => err.severity === 'error');
};

/**
 * 获取是否正在验证
 */
export const selectIsValidating = (state: RootState) => {
  return state.model.validation.isValidating;
};

// ============= UI状态 =============

/**
 * 获取UI状态
 */
export const selectUIState = (state: RootState) => state.model.ui;

/**
 * 获取组件面板显示状态
 */
export const selectShowComponentPalette = (state: RootState) => {
  return state.model.ui.showComponentPalette;
};

/**
 * 获取属性面板显示状态
 */
export const selectShowPropertyPanel = (state: RootState) => {
  return state.model.ui.showPropertyPanel;
};

/**
 * 获取验证面板显示状态
 */
export const selectShowValidationPanel = (state: RootState) => {
  return state.model.ui.showValidationPanel;
};

/**
 * 获取缩放级别
 */
export const selectZoom = (state: RootState) => state.model.ui.zoom;

/**
 * 获取网格启用状态
 */
export const selectGridEnabled = (state: RootState) => state.model.ui.gridEnabled;

/**
 * 获取网格吸附状态
 */
export const selectSnapToGrid = (state: RootState) => state.model.ui.snapToGrid;

// ============= 历史记录 =============

/**
 * 判断是否可以撤销
 */
export const selectCanUndo = (state: RootState) => {
  return state.model.history.past.length > 0;
};

/**
 * 判断是否可以重做
 */
export const selectCanRedo = (state: RootState) => {
  return state.model.history.future.length > 0;
};

// ============= 统计信息 =============

/**
 * 获取节点数量
 */
export const selectNodeCount = (state: RootState) => {
  return selectAllNodes(state).length;
};

/**
 * 获取边数量
 */
export const selectEdgeCount = (state: RootState) => {
  return selectAllEdges(state).length;
};

/**
 * 获取各类型节点数量统计
 */
export const selectNodeTypeStats = (state: RootState) => {
  const nodes = selectAllNodes(state);
  const stats: Record<NodeType, number> = {
    [NodeType.CANAL]: 0,
    [NodeType.GATE]: 0,
    [NodeType.WEIR]: 0,
    [NodeType.BOUNDARY_FLOW]: 0,
    [NodeType.BOUNDARY_DEPTH]: 0
  };

  nodes.forEach(node => {
    stats[node.type] = (stats[node.type] || 0) + 1;
  });

  return stats;
};

/**
 * 获取模型是否为空
 */
export const selectIsModelEmpty = (state: RootState) => {
  const nodeCount = selectNodeCount(state);
  return nodeCount === 0;
};

/**
 * 获取模型是否已修改 (有未保存的更改)
 */
export const selectIsModelModified = (state: RootState) => {
  // 简化版: 通过检查历史记录判断
  // 实际应该对比currentModel和保存的版本
  return state.model.history.past.length > 0;
};
