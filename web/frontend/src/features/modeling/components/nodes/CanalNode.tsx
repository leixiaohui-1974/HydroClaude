/**
 * Canal Node Component
 * 明渠节点组件
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { CanalNodeData } from '../../types/model.types';
import './NodeStyles.css';

const CanalNode: React.FC<NodeProps<CanalNodeData>> = ({ data, selected }) => {
  const hasErrors = data.errors && data.errors.length > 0;
  const hasWarnings = data.warnings && data.warnings.length > 0;

  return (
    <div className={`custom-node canal-node ${selected ? 'selected' : ''} ${hasErrors ? 'error' : ''}`}>
      {/* 输入句柄 */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        isConnectable
      />

      {/* 节点内容 */}
      <div className="node-header">
        <span className="node-icon">🌊</span>
        <span className="node-title">{data.name}</span>
      </div>

      <div className="node-body">
        <div className="node-param">
          <span className="param-label">长度:</span>
          <span className="param-value">{data.length}m</span>
        </div>
        <div className="node-param">
          <span className="param-label">宽度:</span>
          <span className="param-value">{data.width}m</span>
        </div>
        <div className="node-param">
          <span className="param-label">坡度:</span>
          <span className="param-value">{data.slope}</span>
        </div>
      </div>

      {/* 验证状态指示器 */}
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

      {/* 输出句柄 */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        isConnectable
      />
    </div>
  );
};

export default memo(CanalNode);
