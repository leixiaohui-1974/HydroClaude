/**
 * Boundary Node Component
 * 边界条件节点组件
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { BoundaryNodeData } from '../../types/model.types';
import './NodeStyles.css';

const BoundaryNode: React.FC<NodeProps<BoundaryNodeData>> = ({ data, selected }) => {
  const hasErrors = data.errors && data.errors.length > 0;
  const hasWarnings = data.warnings && data.warnings.length > 0;

  const isUpstream = data.position === 'upstream';
  const boundaryLabel = data.boundary_type === 'flow' ? '流量' : '水深';
  const unit = data.boundary_type === 'flow' ? 'm³/s' : 'm';

  return (
    <div className={`custom-node boundary-node ${selected ? 'selected' : ''} ${hasErrors ? 'error' : ''}`}>
      {/* 只有下游边界有输入句柄 */}
      {!isUpstream && (
        <Handle
          type="target"
          position={Position.Left}
          className="node-handle"
          isConnectable
        />
      )}

      {/* 节点内容 */}
      <div className="node-header">
        <span className="node-icon">{isUpstream ? '➜' : '⬍'}</span>
        <span className="node-title">{data.name}</span>
      </div>

      <div className="node-body">
        <div className="node-param">
          <span className="param-label">类型:</span>
          <span className="param-value">{boundaryLabel}</span>
        </div>
        <div className="node-param">
          <span className="param-label">值:</span>
          <span className="param-value">{data.value} {unit}</span>
        </div>
        <div className="node-param">
          <span className="param-label">位置:</span>
          <span className="param-value">{isUpstream ? '上游' : '下游'}</span>
        </div>
      </div>

      {/* 验证状态 */}
      {hasErrors && (
        <div className="node-status error-status" title={data.errors.join(', ')}>
          ⚠️ {data.errors.length} 错误
        </div>
      )}
      {!hasErrors && hasWarnings && (
        <div className="node-status warning-status" title={data.warnings.join(', ')}>
          ⚠ {data.warnings.length} 警告
        </div>
      )}
      {data.validated && !hasErrors && !hasWarnings && (
        <div className="node-status success-status">
          ✓ 已验证
        </div>
      )}

      {/* 只有上游边界有输出句柄 */}
      {isUpstream && (
        <Handle
          type="source"
          position={Position.Right}
          className="node-handle"
          isConnectable
        />
      )}
    </div>
  );
};

export default memo(BoundaryNode);
