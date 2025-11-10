/**
 * Model Canvas Component
 * 模型画布组件 - React-Flow集成
 */

import React, { useCallback, useRef, DragEvent as ReactDragEvent } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Panel,
  useReactFlow,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  OnConnect,
  OnNodesChange,
  OnEdgesChange
} from 'reactflow';
import 'reactflow/dist/style.css';

import { useAppDispatch, useAppSelector } from '@/shared/hooks/redux';
import {
  addNode,
  addEdge,
  updateNodePosition,
  deleteNode,
  deleteEdge,
  setSelectedNodes,
  setSelectedEdges,
  saveSnapshot
} from '../store/modelSlice';
import {
  selectAllNodes,
  selectAllEdges,
  selectGridEnabled,
  selectSnapToGrid
} from '../store/selectors';
import { nodeTypes } from './nodes';
import { ComponentTemplate, NodeType } from '../types/model.types';
import './ModelCanvas.css';

interface ModelCanvasProps {
  onNodeSelect?: (nodeIds: string[]) => void;
}

const ModelCanvasInner: React.FC<ModelCanvasProps> = ({ onNodeSelect }) => {
  const dispatch = useAppDispatch();
  const reactFlowInstance = useReactFlow();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // Redux状态
  const reduxNodes = useAppSelector(selectAllNodes);
  const reduxEdges = useAppSelector(selectAllEdges);
  const gridEnabled = useAppSelector(selectGridEnabled);
  const snapToGrid = useAppSelector(selectSnapToGrid);

  // React-Flow本地状态
  const [nodes, setNodes, onNodesChange] = useNodesState(reduxNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(reduxEdges);

  // 同步Redux状态到React-Flow
  React.useEffect(() => {
    setNodes(reduxNodes);
  }, [reduxNodes, setNodes]);

  React.useEffect(() => {
    setEdges(reduxEdges);
  }, [reduxEdges, setEdges]);

  /**
   * 处理节点变化
   */
  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);

      // 处理位置变化
      changes.forEach((change) => {
        if (change.type === 'position' && change.position && change.id) {
          dispatch(updateNodePosition({
            id: change.id,
            position: change.position
          }));
        }

        // 处理选择变化
        if (change.type === 'select') {
          const selectedIds = nodes
            .filter(n => n.selected || (n.id === change.id && change.selected))
            .map(n => n.id);
          dispatch(setSelectedNodes(selectedIds));
          onNodeSelect?.(selectedIds);
        }

        // 处理删除
        if (change.type === 'remove' && change.id) {
          dispatch(deleteNode(change.id));
        }
      });
    },
    [dispatch, nodes, onNodesChange, onNodeSelect]
  );

  /**
   * 处理边变化
   */
  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes);

      // 处理删除
      changes.forEach((change) => {
        if (change.type === 'remove' && change.id) {
          dispatch(deleteEdge(change.id));
        }

        // 处理选择变化
        if (change.type === 'select') {
          const selectedIds = edges
            .filter(e => e.selected || (e.id === change.id && change.selected))
            .map(e => e.id);
          dispatch(setSelectedEdges(selectedIds));
        }
      });
    },
    [dispatch, edges, onEdgesChange]
  );

  /**
   * 处理连接
   */
  const handleConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) {
        dispatch(addEdge({
          source: connection.source,
          target: connection.target
        }));
        dispatch(saveSnapshot());
      }
    },
    [dispatch]
  );

  /**
   * 处理拖拽放置
   */
  const handleDrop = useCallback(
    (event: ReactDragEvent<HTMLDivElement>) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!reactFlowBounds) return;

      const templateData = event.dataTransfer.getData('application/reactflow');
      if (!templateData) return;

      try {
        const template: ComponentTemplate = JSON.parse(templateData);

        // 计算画布上的位置
        const position = reactFlowInstance.project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top
        });

        // 添加节点到Redux
        dispatch(addNode({
          type: template.type,
          position,
          data: template.defaultData
        }));

        // 保存快照(用于Undo/Redo)
        dispatch(saveSnapshot());
      } catch (error) {
        console.error('Failed to parse drop data:', error);
      }
    },
    [dispatch, reactFlowInstance]
  );

  /**
   * 处理拖拽进入
   */
  const handleDragOver = useCallback((event: ReactDragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  /**
   * 快捷键处理
   */
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Delete键删除选中元素
      if (event.key === 'Delete' || event.key === 'Backspace') {
        const selectedNodes = nodes.filter(n => n.selected);
        if (selectedNodes.length > 0) {
          selectedNodes.forEach(n => dispatch(deleteNode(n.id)));
          dispatch(saveSnapshot());
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nodes, dispatch]);

  return (
    <div className="model-canvas-wrapper" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid={snapToGrid}
        snapGrid={[15, 15]}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#1890ff', strokeWidth: 2 }
        }}
        className="model-canvas"
      >
        {/* 背景网格 */}
        {gridEnabled && (
          <Background
            variant={BackgroundVariant.Dots}
            gap={15}
            size={1}
            color="#d9d9d9"
          />
        )}

        {/* 控制面板 */}
        <Controls
          showZoom
          showFitView
          showInteractive
          className="canvas-controls"
        />

        {/* 小地图 */}
        <MiniMap
          nodeStrokeWidth={3}
          nodeColor={(node) => {
            switch (node.type) {
              case NodeType.CANAL:
                return '#1890ff';
              case NodeType.GATE:
                return '#fa8c16';
              case NodeType.BOUNDARY_FLOW:
              case NodeType.BOUNDARY_DEPTH:
                return '#52c41a';
              default:
                return '#d9d9d9';
            }
          }}
          className="canvas-minimap"
          zoomable
          pannable
        />

        {/* 顶部信息面板 */}
        <Panel position="top-center" className="canvas-panel-top">
          <div className="canvas-info">
            <span>节点: {nodes.length}</span>
            <span className="separator">|</span>
            <span>连接: {edges.length}</span>
          </div>
        </Panel>

        {/* 底部提示面板 */}
        <Panel position="bottom-center" className="canvas-panel-bottom">
          <div className="canvas-hints">
            <span>💡 提示: 从左侧拖拽组件 | 按Delete删除 | 拖拽连接节点</span>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

/**
 * 画布组件(包含ReactFlowProvider)
 */
const ModelCanvas: React.FC<ModelCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <ModelCanvasInner {...props} />
    </ReactFlowProvider>
  );
};

export default ModelCanvas;
