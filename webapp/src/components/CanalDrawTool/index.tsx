import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Polyline, Marker, useMapEvents } from 'react-leaflet';
import { Card, Space, Button, InputNumber, Tooltip, message } from 'antd';
import {
  EditOutlined,
  SaveOutlined,
  UndoOutlined,
  RedoOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import L from 'leaflet';
import type { LatLng } from 'leaflet';
import type { Position } from 'geojson';
import {
  calculateTotalLength,
  calculateAverageSlope,
  calculateDistancesFromStart,
  formatDistance,
  formatSlope,
} from '@/utils/geoUtils';
import './index.css';

// 节点图标
const createNodeIcon = (isStart: boolean, isEnd: boolean) => {
  let color = '#1890ff'; // 中间节点
  if (isStart) color = '#52c41a'; // 起点
  if (isEnd) color = '#f5222d'; // 终点
  
  return L.divIcon({
    className: 'canal-node-icon',
    html: `<div style="background-color: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
};

interface CanalNode {
  position: LatLng;
  elevation: number;
}

interface CanalDrawToolProps {
  onSave?: (data: CanalGeoJSON) => void;
  initialData?: CanalGeoJSON;
}

export interface CanalGeoJSON {
  type: 'Feature';
  geometry: {
    type: 'LineString';
    coordinates: Position[];
  };
  properties: {
    name: string;
    length: number;
    slope: number;
    width: number;
    roughness: number;
    nodes: {
      position: Position;
      elevation: number;
      distance: number;
    }[];
  };
}

/**
 * 渠道绘制工具组件
 * 
 * 功能：
 * - 点击绘制渠道线
 * - 节点拖动编辑
 * - 节点添加/删除
 * - 实时长度计算
 * - 坡度计算
 * - 撤销/重做
 */
const CanalDrawTool: React.FC<CanalDrawToolProps> = ({ onSave, initialData: _initialData }) => {
  const { t } = useTranslation();
  const [isDrawing, setIsDrawing] = useState(false);
  const [nodes, setNodes] = useState<CanalNode[]>([]);
  const [_draggingIndex, setDraggingIndex] = useState<number | null>(null);
  
  // 历史记录（撤销/重做）
  const [history, setHistory] = useState<CanalNode[][]>([[]]);
  const [historyIndex, setHistoryIndex] = useState(0);
  
  // 渠道属性
  const [canalName, _setCanalName] = useState(t('canalDraw.newCanal'));
  const [canalWidth, setCanalWidth] = useState(10);
  const [canalRoughness, setCanalRoughness] = useState(0.025);
  const [startElevation, setStartElevation] = useState(100);
  const [endElevation, setEndElevation] = useState(98);

  // 计算属性
  const coordinates: Position[] = nodes.map(node => [
    node.position.lng,
    node.position.lat,
  ]);
  
  const elevations = nodes.map((_, index) => {
    const ratio = nodes.length > 1 ? index / (nodes.length - 1) : 0;
    return startElevation + (endElevation - startElevation) * ratio;
  });
  
  const totalLength = calculateTotalLength(coordinates);
  const averageSlope = calculateAverageSlope(coordinates, elevations);
  const distances = calculateDistancesFromStart(coordinates);

  // 添加到历史记录
  const addToHistory = useCallback((newNodes: CanalNode[]) => {
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push([...newNodes]);
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  }, [history, historyIndex]);

  // 地图点击事件
  useMapEvents({
    click: (e) => {
      if (isDrawing) {
        const newNode: CanalNode = {
          position: e.latlng,
          elevation: 0, // 将由插值计算
        };
        const newNodes = [...nodes, newNode];
        setNodes(newNodes);
        addToHistory(newNodes);
      }
    },
  });

  // 开始绘制
  const handleStartDrawing = () => {
    setIsDrawing(true);
    message.info(t('canalDraw.clickMapToDraw'));
  };

  // 停止绘制
  const handleStopDrawing = () => {
    setIsDrawing(false);
    if (nodes.length >= 2) {
      message.success(t('canalDraw.drawingComplete', { count: nodes.length }));
    }
  };

  // 清空
  const handleClear = () => {
    setNodes([]);
    setHistory([[]]);
    setHistoryIndex(0);
    setIsDrawing(false);
    message.info(t('canalDraw.cleared'));
  };

  // 撤销
  const handleUndo = () => {
    if (historyIndex > 0) {
      setHistoryIndex(historyIndex - 1);
      setNodes([...history[historyIndex - 1]]);
    }
  };

  // 重做
  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(historyIndex + 1);
      setNodes([...history[historyIndex + 1]]);
    }
  };

  // 删除节点
  const handleDeleteNode = (index: number) => {
    if (nodes.length <= 2) {
      message.warning(t('canalDraw.needAtLeast2Nodes'));
      return;
    }
    const newNodes = nodes.filter((_, i) => i !== index);
    setNodes(newNodes);
    addToHistory(newNodes);
  };

  // 节点拖动开始
  const handleNodeDragStart = (index: number) => {
    setDraggingIndex(index);
  };

  // 节点拖动结束
  const handleNodeDragEnd = (index: number, e: L.DragEndEvent) => {
    const newPosition = (e.target as L.Marker).getLatLng();
    const newNodes = [...nodes];
    newNodes[index] = { ...newNodes[index], position: newPosition };
    setNodes(newNodes);
    addToHistory(newNodes);
    setDraggingIndex(null);
  };

  // 保存为GeoJSON
  const handleSave = () => {
    if (nodes.length < 2) {
      message.error(t('canalDraw.needAtLeast2NodesToSave'));
      return;
    }

    const geoJSON: CanalGeoJSON = {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: coordinates,
      },
      properties: {
        name: canalName,
        length: totalLength,
        slope: averageSlope,
        width: canalWidth,
        roughness: canalRoughness,
        nodes: nodes.map((node, i) => ({
          position: [node.position.lng, node.position.lat],
          elevation: elevations[i],
          distance: distances[i],
        })),
      },
    };

    onSave?.(geoJSON);
    
    // 下载JSON文件
    const blob = new Blob([JSON.stringify(geoJSON, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${canalName.replace(/\s+/g, '_')}.geojson`;
    link.click();
    URL.revokeObjectURL(url);

    message.success(t('canalDraw.savedAsGeoJSON'));
  };

  return (
    <>
      {/* 控制面板 */}
      <Card
        className="canal-draw-controls"
        style={{
          position: 'absolute',
          top: 80,
          left: 20,
          zIndex: 1000,
          width: 300,
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* 绘制控制 */}
          <Space>
            <Button
              type={isDrawing ? 'primary' : 'default'}
              icon={<EditOutlined />}
              onClick={isDrawing ? handleStopDrawing : handleStartDrawing}
            >
              {isDrawing ? t('canalDraw.stopDrawing') : t('canalDraw.startDrawing')}
            </Button>
            <Tooltip title={t('canalDraw.undo')}>
              <Button
                icon={<UndoOutlined />}
                onClick={handleUndo}
                disabled={historyIndex <= 0}
              />
            </Tooltip>
            <Tooltip title={t('canalDraw.redo')}>
              <Button
                icon={<RedoOutlined />}
                onClick={handleRedo}
                disabled={historyIndex >= history.length - 1}
              />
            </Tooltip>
            <Tooltip title={t('canalDraw.clear')}>
              <Button
                icon={<ClearOutlined />}
                onClick={handleClear}
                danger
              />
            </Tooltip>
          </Space>

          {/* 渠道信息 */}
          <div style={{ fontSize: '14px', color: '#666' }}>
            <div><strong>{t('canalDraw.nodeCount')}</strong> {nodes.length}</div>
            <div><strong>{t('canalDraw.totalLength')}</strong> {formatDistance(totalLength)}</div>
            <div><strong>{t('canalDraw.averageSlope')}</strong> {formatSlope(averageSlope)}</div>
          </div>

          {/* 渠道参数 */}
          <div>
            <div style={{ marginBottom: 8 }}>
              <label>{t('canalDraw.canalWidth')}</label>
              <InputNumber
                value={canalWidth}
                onChange={(v) => setCanalWidth(v || 10)}
                min={1}
                max={100}
                style={{ width: '100%', marginTop: 4 }}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>{t('canalDraw.roughness')}</label>
              <InputNumber
                value={canalRoughness}
                onChange={(v) => setCanalRoughness(v || 0.025)}
                min={0.001}
                max={0.1}
                step={0.001}
                style={{ width: '100%', marginTop: 4 }}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>{t('canalDraw.startElevation')}</label>
              <InputNumber
                value={startElevation}
                onChange={(v) => setStartElevation(v || 100)}
                style={{ width: '100%', marginTop: 4 }}
              />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label>{t('canalDraw.endElevation')}</label>
              <InputNumber
                value={endElevation}
                onChange={(v) => setEndElevation(v || 98)}
                style={{ width: '100%', marginTop: 4 }}
              />
            </div>
          </div>

          {/* 保存按钮 */}
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            block
            disabled={nodes.length < 2}
          >
            {t('canalDraw.saveAsGeoJSON')}
          </Button>
        </Space>
      </Card>

      {/* 渠道线 */}
      {nodes.length >= 2 && (
        <Polyline
          positions={nodes.map(n => n.position)}
          color="#1890ff"
          weight={4}
          opacity={0.8}
        />
      )}

      {/* 节点标记 */}
      {nodes.map((node, index) => (
        <Marker
          key={index}
          position={node.position}
          icon={createNodeIcon(index === 0, index === nodes.length - 1)}
          draggable={!isDrawing}
          eventHandlers={{
            dragstart: () => handleNodeDragStart(index),
            dragend: (e) => handleNodeDragEnd(index, e),
            dblclick: () => handleDeleteNode(index),
          }}
        />
      ))}
    </>
  );
};

export default CanalDrawTool;
