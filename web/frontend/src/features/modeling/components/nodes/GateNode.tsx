/**
 * Gate Node Component
 * 闸门节点组件
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { GateNodeData } from '../../types/model.types';
import './NodeStyles.css';

const GateNode: React.FC<NodeProps<GateNodeData>> = ({ data, selected }) => {
  const hasErrors = data.errors && data.errors.length > 0;
  const hasWarnings = data.warnings && data.warnings.length > 0;

  return (
    <div className={`custom-node gate-node ${selected ? 'selected' : ''} ${hasErrors ? 'error' : ''}`}>
      {/* 输入句柄 */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        isConnectable
      />

      {/* 节点内容 */}
      <div className="node-header">
        <span className="node-icon">⫿</span>
        <span className="node-title">{data.name}</span>
      </div>

      <div className="node-body">
        <div className="node-param">
          <span className="param-label">开度:</span>
          <span className="param-value">{(data.opening * 100).toFixed(0)}%</span>
        </div>
        <div className="node-param">
          <span className="param-label">宽度:</span>
          <span className="param-value">{data.width}m</span>
        </div>
        <div className="node-param">
          <span className="param-label">流量系数:</span>
          <span className="param-value">{data.discharge_coeff}</span>
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

export default memo(GateNode);
