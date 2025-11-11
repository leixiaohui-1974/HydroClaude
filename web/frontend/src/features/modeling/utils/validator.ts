/**
 * Model Validator
 * 模型验证器 - 拓扑检查和参数验证
 */

import {
  HydraulicModel,
  ModelNode,
  ModelEdge,
  ValidationError,
  ValidationResult,
  ValidationErrorType,
  ValidationSeverity,
  NodeType,
  CanalNodeData,
  GateNodeData,
  BoundaryNodeData
} from '../types/model.types';

/**
 * 验证整个模型
 */
export const validateModel = (model: HydraulicModel): ValidationResult => {
  const errors: ValidationError[] = [];

  // 1. 基本检查
  if (!model || !model.nodes || !model.edges) {
    errors.push({
      id: 'model_empty',
      type: ValidationErrorType.TOPOLOGY,
      severity: ValidationSeverity.ERROR,
      message: '模型为空',
      suggestion: '请添加至少一个组件'
    });
    return {
      valid: false,
      errors,
      timestamp: new Date().toISOString()
    };
  }

  // 2. 拓扑验证
  errors.push(...validateTopology(model.nodes, model.edges));

  // 3. 参数验证
  errors.push(...validateParameters(model.nodes));

  // 4. 边界条件验证
  errors.push(...validateBoundaryConditions(model.nodes, model.edges));

  // 5. 物理一致性验证
  errors.push(...validatePhysicalConsistency(model.nodes, model.edges));

  const hasErrors = errors.some(e => e.severity === ValidationSeverity.ERROR);

  return {
    valid: !hasErrors,
    errors,
    timestamp: new Date().toISOString()
  };
};

/**
 * 拓扑验证
 */
const validateTopology = (nodes: ModelNode[], edges: ModelEdge[]): ValidationError[] => {
  const errors: ValidationError[] = [];

  if (nodes.length === 0) {
    errors.push({
      id: 'no_nodes',
      type: ValidationErrorType.TOPOLOGY,
      severity: ValidationSeverity.ERROR,
      message: '模型中没有任何节点',
      suggestion: '请从组件面板添加节点'
    });
    return errors;
  }

  // 检查孤立节点
  const connectedNodeIds = new Set<string>();
  edges.forEach(edge => {
    connectedNodeIds.add(edge.source);
    connectedNodeIds.add(edge.target);
  });

  nodes.forEach(node => {
    if (!connectedNodeIds.has(node.id)) {
      errors.push({
        id: `isolated_${node.id}`,
        type: ValidationErrorType.TOPOLOGY,
        severity: ValidationSeverity.WARNING,
        node_id: node.id,
        message: `节点 "${node.data.name}" 未连接到任何其他节点`,
        suggestion: '请连接此节点或删除它'
      });
    }
  });

  // 检查循环（简单检查：有向图中的环）
  const hasCircle = detectCircle(nodes, edges);
  if (hasCircle) {
    errors.push({
      id: 'circular_topology',
      type: ValidationErrorType.TOPOLOGY,
      severity: ValidationSeverity.WARNING,
      message: '检测到循环拓扑结构',
      suggestion: '请确认这是否符合您的设计意图'
    });
  }

  // 检查边的有效性
  edges.forEach(edge => {
    const sourceNode = nodes.find(n => n.id === edge.source);
    const targetNode = nodes.find(n => n.id === edge.target);

    if (!sourceNode) {
      errors.push({
        id: `edge_invalid_source_${edge.id}`,
        type: ValidationErrorType.TOPOLOGY,
        severity: ValidationSeverity.ERROR,
        edge_id: edge.id,
        message: `连接的源节点不存在 (${edge.source})`,
        suggestion: '请删除此无效连接'
      });
    }

    if (!targetNode) {
      errors.push({
        id: `edge_invalid_target_${edge.id}`,
        type: ValidationErrorType.TOPOLOGY,
        severity: ValidationSeverity.ERROR,
        edge_id: edge.id,
        message: `连接的目标节点不存在 (${edge.target})`,
        suggestion: '请删除此无效连接'
      });
    }
  });

  return errors;
};

/**
 * 参数验证
 */
const validateParameters = (nodes: ModelNode[]): ValidationError[] => {
  const errors: ValidationError[] = [];

  nodes.forEach(node => {
    switch (node.type) {
      case NodeType.CANAL:
        errors.push(...validateCanalParameters(node.id, node.data as CanalNodeData));
        break;
      case NodeType.GATE:
        errors.push(...validateGateParameters(node.id, node.data as GateNodeData));
        break;
      case NodeType.BOUNDARY_FLOW:
      case NodeType.BOUNDARY_DEPTH:
        errors.push(...validateBoundaryParameters(node.id, node.data as BoundaryNodeData));
        break;
    }
  });

  return errors;
};

/**
 * 验证明渠参数
 */
const validateCanalParameters = (nodeId: string, data: CanalNodeData): ValidationError[] => {
  const errors: ValidationError[] = [];

  // 长度检查
  if (data.length <= 0) {
    errors.push({
      id: `canal_length_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.ERROR,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的长度必须大于0`,
      suggestion: '请设置一个正数长度值'
    });
  } else if (data.length > 100000) {
    errors.push({
      id: `canal_length_large_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.WARNING,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的长度 (${data.length}m) 非常大`,
      suggestion: '请确认长度值是否正确'
    });
  }

  // 宽度检查
  if (data.width <= 0) {
    errors.push({
      id: `canal_width_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.ERROR,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的宽度必须大于0`,
      suggestion: '请设置一个正数宽度值'
    });
  }

  // 坡度检查
  if (data.slope < 0) {
    errors.push({
      id: `canal_slope_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.ERROR,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的坡度不能为负数`,
      suggestion: '坡度应该是0或正数'
    });
  } else if (data.slope > 0.1) {
    errors.push({
      id: `canal_slope_large_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.WARNING,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的坡度 (${data.slope}) 很大`,
      suggestion: '请确认坡度值是否正确（通常<0.01）'
    });
  }

  // 曼宁系数检查
  if (data.manning_n < 0.01 || data.manning_n > 0.1) {
    errors.push({
      id: `canal_manning_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.WARNING,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的曼宁系数 (${data.manning_n}) 不在常见范围内`,
      suggestion: '曼宁系数通常在0.01-0.1之间'
    });
  }

  // 网格数检查
  if (data.n_cells < 10) {
    errors.push({
      id: `canal_cells_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.WARNING,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的网格数 (${data.n_cells}) 太少`,
      suggestion: '建议至少使用50个网格以获得较好精度'
    });
  } else if (data.n_cells > 1000) {
    errors.push({
      id: `canal_cells_large_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.INFO,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的网格数 (${data.n_cells}) 较多`,
      suggestion: '较多网格会增加计算时间'
    });
  }

  // 初始条件检查
  if (data.initial_depth !== undefined && data.initial_depth < 0) {
    errors.push({
      id: `canal_initial_depth_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.ERROR,
      node_id: nodeId,
      message: `明渠 "${data.name}" 的初始水深不能为负数`,
      suggestion: '请设置一个非负水深值'
    });
  }

  return errors;
};

/**
 * 验证闸门参数
 */
const validateGateParameters = (nodeId: string, data: GateNodeData): ValidationError[] => {
  const errors: ValidationError[] = [];

  // 开度检查
  if (data.opening < 0 || data.opening > 1) {
    errors.push({
      id: `gate_opening_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.ERROR,
      node_id: nodeId,
      message: `闸门 "${data.name}" 的开度必须在0-1之间`,
      suggestion: '开度为0表示全闭，1表示全开'
    });
  }

  // 流量系数检查
  if (data.discharge_coeff < 0.1 || data.discharge_coeff > 1) {
    errors.push({
      id: `gate_coeff_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.WARNING,
      node_id: nodeId,
      message: `闸门 "${data.name}" 的流量系数 (${data.discharge_coeff}) 不在常见范围内`,
      suggestion: '流量系数通常在0.6-0.8之间'
    });
  }

  // 宽度检查
  if (data.width <= 0) {
    errors.push({
      id: `gate_width_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.ERROR,
      node_id: nodeId,
      message: `闸门 "${data.name}" 的宽度必须大于0`,
      suggestion: '请设置一个正数宽度值'
    });
  }

  return errors;
};

/**
 * 验证边界参数
 */
const validateBoundaryParameters = (nodeId: string, data: BoundaryNodeData): ValidationError[] => {
  const errors: ValidationError[] = [];

  // 边界值检查
  if (data.value < 0) {
    errors.push({
      id: `boundary_value_${nodeId}`,
      type: ValidationErrorType.PARAMETER,
      severity: ValidationSeverity.ERROR,
      node_id: nodeId,
      message: `边界条件 "${data.name}" 的值不能为负数`,
      suggestion: '请设置一个非负值'
    });
  }

  return errors;
};

/**
 * 边界条件验证
 */
const validateBoundaryConditions = (nodes: ModelNode[], edges: ModelEdge[]): ValidationError[] => {
  const errors: ValidationError[] = [];

  const boundaryNodes = nodes.filter(
    n => n.type === NodeType.BOUNDARY_FLOW || n.type === NodeType.BOUNDARY_DEPTH
  );

  if (boundaryNodes.length === 0) {
    errors.push({
      id: 'no_boundaries',
      type: ValidationErrorType.BOUNDARY,
      severity: ValidationSeverity.WARNING,
      message: '模型中没有边界条件',
      suggestion: '建议添加上游和下游边界条件'
    });
    return errors;
  }

  // 检查是否有上游和下游边界
  const upstreamBoundaries = boundaryNodes.filter(
    n => (n.data as BoundaryNodeData).position === 'upstream'
  );
  const downstreamBoundaries = boundaryNodes.filter(
    n => (n.data as BoundaryNodeData).position === 'downstream'
  );

  if (upstreamBoundaries.length === 0) {
    errors.push({
      id: 'no_upstream_boundary',
      type: ValidationErrorType.BOUNDARY,
      severity: ValidationSeverity.WARNING,
      message: '缺少上游边界条件',
      suggestion: '建议添加一个上游流量或水深边界'
    });
  }

  if (downstreamBoundaries.length === 0) {
    errors.push({
      id: 'no_downstream_boundary',
      type: ValidationErrorType.BOUNDARY,
      severity: ValidationSeverity.WARNING,
      message: '缺少下游边界条件',
      suggestion: '建议添加一个下游流量或水深边界'
    });
  }

  // 检查边界节点的连接
  boundaryNodes.forEach(node => {
    const data = node.data as BoundaryNodeData;
    const connectedEdges = edges.filter(
      e => e.source === node.id || e.target === node.id
    );

    if (connectedEdges.length === 0) {
      errors.push({
        id: `boundary_not_connected_${node.id}`,
        type: ValidationErrorType.BOUNDARY,
        severity: ValidationSeverity.ERROR,
        node_id: node.id,
        message: `边界条件 "${data.name}" 未连接到模型`,
        suggestion: '请将边界条件连接到明渠或其他组件'
      });
    }
  });

  return errors;
};

/**
 * 物理一致性验证
 */
const validatePhysicalConsistency = (nodes: ModelNode[], edges: ModelEdge[]): ValidationError[] => {
  const errors: ValidationError[] = [];

  // 检查连接的组件宽度是否匹配
  edges.forEach(edge => {
    const sourceNode = nodes.find(n => n.id === edge.source);
    const targetNode = nodes.find(n => n.id === edge.target);

    if (!sourceNode || !targetNode) return;

    // 检查明渠和闸门的宽度匹配
    if (sourceNode.type === NodeType.CANAL && targetNode.type === NodeType.GATE) {
      const canalWidth = (sourceNode.data as CanalNodeData).width;
      const gateWidth = (targetNode.data as GateNodeData).width;

      if (Math.abs(canalWidth - gateWidth) > 0.1) {
        errors.push({
          id: `width_mismatch_${edge.id}`,
          type: ValidationErrorType.PHYSICS,
          severity: ValidationSeverity.WARNING,
          edge_id: edge.id,
          message: `明渠宽度 (${canalWidth}m) 与闸门宽度 (${gateWidth}m) 不匹配`,
          suggestion: '建议调整宽度使其一致'
        });
      }
    }
  });

  return errors;
};

/**
 * 检测拓扑中的循环
 */
const detectCircle = (nodes: ModelNode[], edges: ModelEdge[]): boolean => {
  const graph = new Map<string, string[]>();

  // 构建邻接表
  nodes.forEach(node => {
    graph.set(node.id, []);
  });

  edges.forEach(edge => {
    const neighbors = graph.get(edge.source) || [];
    neighbors.push(edge.target);
    graph.set(edge.source, neighbors);
  });

  // DFS检测环
  const visited = new Set<string>();
  const recStack = new Set<string>();

  const dfs = (nodeId: string): boolean => {
    visited.add(nodeId);
    recStack.add(nodeId);

    const neighbors = graph.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) return true;
      } else if (recStack.has(neighbor)) {
        return true; // 发现环
      }
    }

    recStack.delete(nodeId);
    return false;
  };

  for (const nodeId of graph.keys()) {
    if (!visited.has(nodeId)) {
      if (dfs(nodeId)) return true;
    }
  }

  return false;
};
