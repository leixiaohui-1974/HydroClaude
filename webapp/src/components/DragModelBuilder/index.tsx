/**
 * 拖拽式建模组件 - Drag & Drop Model Builder
 * 
 * 功能：
 * 1. 拖拽式渠道建模
 * 2. 可视化添加水工结构（闸门、堰、泵站等）
 * 3. 参数配置面板
 * 4. 实时预览
 * 5. 导出JSON配置
 */

import React, { useState, useRef, useCallback } from 'react';
import { Card, Button, InputNumber, Select, message, Space, Divider, Modal } from 'antd';
import { DeleteOutlined, EditOutlined, ExportOutlined } from '@ant-design/icons';
import './styles.css';

const { Option } = Select;

// 水工结构类型
const STRUCTURE_TYPES = {
  GATE: { type: 'gate', label: '闸门', icon: '🚪', color: '#1890ff' },
  WEIR: { type: 'weir', label: '堰', icon: '⛰️', color: '#52c41a' },
  PUMP: { type: 'pump', label: '泵站', icon: '💧', color: '#722ed1' },
  ORIFICE: { type: 'orifice', label: '孔口', icon: '⭕', color: '#fa8c16' },
};

interface Structure {
  id: string;
  type: string;
  position: number; // 在渠道上的位置 (m)
  params: Record<string, number>;
  label: string;
}

interface CanalConfig {
  length: number;
  width: number;
  slope: number;
  roughness: number;
  nx: number;
}

interface FlowConfig {
  flow_rate: number;
  type: string;
}

const DragModelBuilder: React.FC = () => {
  // 状态管理
  const [canalConfig, setCanalConfig] = useState<CanalConfig>({
    length: 10000,
    width: 10,
    slope: 0.001,
    roughness: 0.025,
    nx: 500,
  });

  const [flowConfig, setFlowConfig] = useState<FlowConfig>({
    flow_rate: 50,
    type: 'steady',
  });

  const [structures, setStructures] = useState<Structure[]>([]);
  const [selectedStructure, setSelectedStructure] = useState<Structure | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState<string>('');
  const [showConfigModal, setShowConfigModal] = useState(false);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 绘制渠道
  const drawCanal = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 绘制渠道主体
    const canalHeight = 100;
    const canalY = canvas.height / 2 - canalHeight / 2;

    // 渠道轮廓
    ctx.fillStyle = '#e6f7ff';
    ctx.fillRect(50, canalY, canvas.width - 100, canalHeight);
    ctx.strokeStyle = '#1890ff';
    ctx.lineWidth = 2;
    ctx.strokeRect(50, canalY, canvas.width - 100, canalHeight);

    // 水流方向箭头
    ctx.fillStyle = '#1890ff';
    ctx.font = '14px Arial';
    ctx.fillText('→ 流向', canvas.width / 2 - 30, canalY - 10);

    // 绘制长度标注
    ctx.fillStyle = '#666';
    ctx.font = '12px Arial';
    ctx.fillText('0 m', 45, canvas.height / 2 + canalHeight / 2 + 25);
    ctx.fillText(`${canalConfig.length} m`, canvas.width - 100, canvas.height / 2 + canalHeight / 2 + 25);

    // 绘制网格线
    const gridCount = 10;
    ctx.strokeStyle = '#d9d9d9';
    ctx.lineWidth = 0.5;
    for (let i = 1; i < gridCount; i++) {
      const x = 50 + (canvas.width - 100) * (i / gridCount);
      ctx.beginPath();
      ctx.moveTo(x, canalY);
      ctx.lineTo(x, canalY + canalHeight);
      ctx.stroke();
    }

    // 绘制结构
    structures.forEach((structure) => {
      const posRatio = structure.position / canalConfig.length;
      const x = 50 + (canvas.width - 100) * posRatio;
      const structureInfo = Object.values(STRUCTURE_TYPES).find(s => s.type === structure.type);

      if (structureInfo) {
        // 结构图标
        ctx.fillStyle = structureInfo.color;
        ctx.fillRect(x - 15, canalY + 20, 30, 60);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeRect(x - 15, canalY + 20, 30, 60);

        // 图标和标签
        ctx.font = '24px Arial';
        ctx.fillText(structureInfo.icon, x - 12, canalY + 50);

        ctx.font = '10px Arial';
        ctx.fillStyle = '#000';
        ctx.fillText(structure.label, x - 20, canalY + 95);
        ctx.fillText(`${structure.position.toFixed(0)}m`, x - 15, canalY + 105);
      }

      // 高亮选中的结构
      if (selectedStructure?.id === structure.id) {
        ctx.strokeStyle = '#ff4d4f';
        ctx.lineWidth = 3;
        ctx.strokeRect(x - 18, canalY + 17, 36, 66);
      }
    });
  }, [canalConfig, structures, selectedStructure]);

  // 重绘画布
  React.useEffect(() => {
    drawCanal();
  }, [drawCanal]);

  // 处理画布调整大小
  React.useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resizeCanvas = () => {
      canvas.width = container.clientWidth;
      canvas.height = 300;
      drawCanal();
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    return () => window.removeEventListener('resize', resizeCanvas);
  }, [drawCanal]);

  // 开始拖拽
  const handleDragStart = (type: string) => {
    setIsDragging(true);
    setDragType(type);
  };

  // 处理放置
  const handleDrop = (e: React.DragEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas || !isDragging) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const canvasWidth = canvas.width;

    // 计算在渠道上的位置
    const posRatio = Math.max(0, Math.min(1, (x - 50) / (canvasWidth - 100)));
    const position = posRatio * canalConfig.length;

    // 创建新结构
    const structureInfo = Object.values(STRUCTURE_TYPES).find(s => s.type === dragType);
    if (!structureInfo) return;

    const newStructure: Structure = {
      id: `${dragType}_${Date.now()}`,
      type: dragType,
      position: Math.round(position),
      label: `${structureInfo.label}${structures.filter(s => s.type === dragType).length + 1}`,
      params: getDefaultParams(dragType),
    };

    setStructures([...structures, newStructure]);
    setIsDragging(false);
    setDragType('');
    message.success(`已添加${structureInfo.label}`);
  };

  // 获取默认参数
  const getDefaultParams = (type: string): Record<string, number> => {
    switch (type) {
      case 'gate':
        return { width: canalConfig.width, opening: 5.0 };
      case 'weir':
        return { width: canalConfig.width, crest_height: 0.5 };
      case 'pump':
        return { flow_rate: 10.0, head: 5.0 };
      case 'orifice':
        return { diameter: 1.0, elevation: 0.0 };
      default:
        return {};
    }
  };

  // 处理拖拽悬停
  const handleDragOver = (e: React.DragEvent<HTMLCanvasElement>) => {
    e.preventDefault();
  };

  // 点击画布选择结构
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const canvasWidth = canvas.width;

    // 查找点击的结构
    const clickedStructure = structures.find((structure) => {
      const posRatio = structure.position / canalConfig.length;
      const structureX = 50 + (canvasWidth - 100) * posRatio;
      return Math.abs(x - structureX) < 20;
    });

    setSelectedStructure(clickedStructure || null);
  };

  // 删除结构
  const handleDeleteStructure = () => {
    if (!selectedStructure) return;
    setStructures(structures.filter(s => s.id !== selectedStructure.id));
    setSelectedStructure(null);
    message.success('已删除结构');
  };

  // 编辑结构
  const handleEditStructure = () => {
    if (!selectedStructure) return;
    setShowConfigModal(true);
  };

  // 更新结构参数
  const handleUpdateStructure = (params: Record<string, number>) => {
    if (!selectedStructure) return;
    const updated = structures.map(s =>
      s.id === selectedStructure.id ? { ...s, params } : s
    );
    setStructures(updated);
    setSelectedStructure({ ...selectedStructure, params });
    setShowConfigModal(false);
    message.success('参数已更新');
  };

  // 导出配置
  const handleExportConfig = () => {
    const config = {
      name: 'drag_model',
      description: '拖拽式建模生成的配置',
      canal: canalConfig,
      flow: flowConfig,
      structures: structures.map(s => ({
        type: s.type,
        position: s.position,
        ...s.params,
      })),
      solver: {
        type: 'hydrostatic',
        max_iterations: 100,
        convergence_tol: 0.1,
      },
    };

    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'canal_model.json';
    a.click();
    URL.revokeObjectURL(url);
    message.success('配置已导出');
  };

  return (
    <div className="drag-model-builder">
      <Card title="🎨 拖拽式渠道建模" style={{ marginBottom: 20 }}>
        {/* 渠道参数配置 */}
        <div className="canal-config">
          <h4>渠道参数</h4>
          <Space wrap>
            <span>长度(m):</span>
            <InputNumber
              value={canalConfig.length}
              onChange={(val) => setCanalConfig({ ...canalConfig, length: val || 10000 })}
              min={100}
              max={100000}
              step={1000}
            />
            <span>宽度(m):</span>
            <InputNumber
              value={canalConfig.width}
              onChange={(val) => setCanalConfig({ ...canalConfig, width: val || 10 })}
              min={1}
              max={100}
              step={1}
            />
            <span>坡度:</span>
            <InputNumber
              value={canalConfig.slope}
              onChange={(val) => setCanalConfig({ ...canalConfig, slope: val || 0.001 })}
              min={0.0001}
              max={0.1}
              step={0.0001}
            />
            <span>糙率:</span>
            <InputNumber
              value={canalConfig.roughness}
              onChange={(val) => setCanalConfig({ ...canalConfig, roughness: val || 0.025 })}
              min={0.01}
              max={0.1}
              step={0.001}
            />
          </Space>
        </div>

        <Divider />

        {/* 流量配置 */}
        <div className="flow-config">
          <h4>流量参数</h4>
          <Space>
            <span>流量(m³/s):</span>
            <InputNumber
              value={flowConfig.flow_rate}
              onChange={(val) => setFlowConfig({ ...flowConfig, flow_rate: val || 50 })}
              min={0.1}
              max={1000}
              step={1}
            />
            <span>类型:</span>
            <Select
              value={flowConfig.type}
              onChange={(val) => setFlowConfig({ ...flowConfig, type: val })}
              style={{ width: 120 }}
            >
              <Option value="steady">稳态</Option>
              <Option value="unsteady">非稳态</Option>
            </Select>
          </Space>
        </div>
      </Card>

      {/* 结构工具箱 */}
      <Card title="🧰 水工结构工具箱" style={{ marginBottom: 20 }}>
        <Space size="large">
          {Object.values(STRUCTURE_TYPES).map((structure) => (
            <div
              key={structure.type}
              className="structure-tool"
              draggable
              onDragStart={() => handleDragStart(structure.type)}
              style={{
                padding: '10px 20px',
                border: `2px solid ${structure.color}`,
                borderRadius: '8px',
                cursor: 'grab',
                backgroundColor: '#fafafa',
              }}
            >
              <div style={{ fontSize: '24px', textAlign: 'center' }}>{structure.icon}</div>
              <div style={{ fontSize: '12px', textAlign: 'center' }}>{structure.label}</div>
            </div>
          ))}
        </Space>
        <div style={{ marginTop: 10, color: '#666', fontSize: '12px' }}>
          💡 提示: 拖拽水工结构到下方渠道上进行建模
        </div>
      </Card>

      {/* 渠道画布 */}
      <Card
        title="🏞️ 渠道可视化"
        extra={
          <Space>
            {selectedStructure && (
              <>
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  onClick={handleEditStructure}
                  size="small"
                >
                  编辑
                </Button>
                <Button
                  danger
                  icon={<DeleteOutlined />}
                  onClick={handleDeleteStructure}
                  size="small"
                >
                  删除
                </Button>
              </>
            )}
            <Button
              type="default"
              icon={<ExportOutlined />}
              onClick={handleExportConfig}
              disabled={structures.length === 0}
            >
              导出配置
            </Button>
          </Space>
        }
      >
        <div ref={containerRef} style={{ width: '100%', height: 300 }}>
          <canvas
            ref={canvasRef}
            onClick={handleCanvasClick}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            style={{ border: '1px solid #d9d9d9', borderRadius: '4px', cursor: 'pointer' }}
          />
        </div>
        <div style={{ marginTop: 10, color: '#666', fontSize: '12px' }}>
          已添加 {structures.length} 个结构
          {selectedStructure && ` | 已选中: ${selectedStructure.label} (位置: ${selectedStructure.position}m)`}
        </div>
      </Card>

      {/* 结构参数配置模态框 */}
      <Modal
        title={`编辑 ${selectedStructure?.label}`}
        open={showConfigModal}
        onCancel={() => setShowConfigModal(false)}
        onOk={() => {
          if (selectedStructure) {
            handleUpdateStructure(selectedStructure.params);
          }
        }}
      >
        {selectedStructure && (
          <Space direction="vertical" style={{ width: '100%' }}>
            {Object.entries(selectedStructure.params).map(([key, value]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>{key}:</span>
                <InputNumber
                  value={value}
                  onChange={(val) => {
                    setSelectedStructure({
                      ...selectedStructure,
                      params: { ...selectedStructure.params, [key]: val || 0 },
                    });
                  }}
                  step={0.1}
                  style={{ width: 200 }}
                />
              </div>
            ))}
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default DragModelBuilder;
