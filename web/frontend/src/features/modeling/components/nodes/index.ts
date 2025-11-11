/**
 * Node Components Index
 * 节点组件导出
 */

import CanalNode from './CanalNode';
import GateNode from './GateNode';
import BoundaryNode from './BoundaryNode';
import { NodeType } from '../../types/model.types';

// 节点类型映射
export const nodeTypes = {
  [NodeType.CANAL]: CanalNode,
  [NodeType.GATE]: GateNode,
  [NodeType.WEIR]: GateNode,  // 堰暂时使用闸门组件
  [NodeType.BOUNDARY_FLOW]: BoundaryNode,
  [NodeType.BOUNDARY_DEPTH]: BoundaryNode
};

export { CanalNode, GateNode, BoundaryNode };
