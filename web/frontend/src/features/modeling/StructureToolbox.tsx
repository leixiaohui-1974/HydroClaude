/**
 * Structure Toolbox Component
 * 水工结构工具箱
 * 
 * 综合的建模工具面板，对标商业软件
 * 
 * @author HydroClaude Team
 * @date 2025-11-15
 */

import React, { useState } from 'react';
import {
  Card,
  Button,
  Space,
  Modal,
  Row,
  Col,
  Tooltip,
  Badge,
  Statistic,
  Alert,
  Divider,
  List,
  Typography
} from 'antd';
import {
  PlusOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  AppstoreAddOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { PumpStationEditor, GateEditor, WeirEditor } from './components';

const { Title, Text } = Typography;

interface Structure {
  id: string;
  type: 'pump' | 'gate' | 'weir';
  name: string;
  position: number;
  config: any;
}

interface Props {
  onAddStructure?: (structure: Structure) => void;
  structures?: Structure[];
}

export const StructureToolbox: React.FC<Props> = ({
  onAddStructure,
  structures = []
}) => {
  const [activeEditor, setActiveEditor] = useState<'pump' | 'gate' | 'weir' | null>(null);
  const [editingStructure, setEditingStructure] = useState<Structure | null>(null);
  
  // 统计各类结构数量
  const stats = {
    pumps: structures.filter(s => s.type === 'pump').length,
    gates: structures.filter(s => s.type === 'gate').length,
    weirs: structures.filter(s => s.type === 'weir').length,
    total: structures.length
  };
  
  // 处理保存
  const handleSave = (type: 'pump' | 'gate' | 'weir', config: any) => {
    const newStructure: Structure = {
      id: `${type}-${Date.now()}`,
      type,
      name: config.name,
      position: config.position,
      config
    };
    
    if (onAddStructure) {
      onAddStructure(newStructure);
    }
    
    setActiveEditor(null);
    setEditingStructure(null);
  };
  
  // 处理取消
  const handleCancel = () => {
    setActiveEditor(null);
    setEditingStructure(null);
  };
  
  return (
    <div style={{ padding: '24px' }}>
      {/* 顶部标题 */}
      <Card bordered={false} style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              <ToolOutlined style={{ marginRight: 8 }} />
              水工结构工具箱
            </Title>
            <Text type="secondary">
              对标商业软件（HEC-RAS、MIKE）的完整建模工具
            </Text>
          </Col>
          <Col>
            <Badge count={stats.total} showZero>
              <Button type="primary" size="large" icon={<RocketOutlined />}>
                已添加 {stats.total} 个结构
              </Button>
            </Badge>
          </Col>
        </Row>
      </Card>
      
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="泵站"
              value={stats.pumps}
              prefix="⚙️"
              suffix="个"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="闸门"
              value={stats.gates}
              prefix="🚪"
              suffix="个"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="堰"
              value={stats.weirs}
              prefix="📐"
              suffix="个"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总计"
              value={stats.total}
              prefix="📊"
              suffix="个"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>
      
      {/* 功能亮点 */}
      <Alert
        message="🎉 对标商业软件的完整功能"
        description={
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text>
              ⭐ 泵站：单泵/多泵、4种控制模式、自动启停、效率计算
            </Text>
            <Text>
              ⭐ 闸门：5种类型（滑动/径向/垂直提升/滚轮/翻板）、智能流态识别
            </Text>
            <Text>
              ⭐ 堰：6种类型（尖顶/宽顶/V型/矩形/梯形/溢流）、流量曲线生成
            </Text>
          </Space>
        }
        type="success"
        showIcon
        style={{ marginBottom: 24 }}
      />
      
      {/* 添加结构按钮 */}
      <Card title="添加水工结构" bordered={false}>
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Card
              hoverable
              onClick={() => setActiveEditor('pump')}
              style={{ textAlign: 'center' }}
            >
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div style={{ fontSize: 48 }}>⚙️</div>
                <Title level={4}>泵站</Title>
                <Text type="secondary">
                  单泵/多泵、自动控制、泵曲线
                </Text>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  size="large"
                  block
                >
                  添加泵站
                </Button>
              </Space>
            </Card>
          </Col>
          
          <Col span={8}>
            <Card
              hoverable
              onClick={() => setActiveEditor('gate')}
              style={{ textAlign: 'center' }}
            >
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div style={{ fontSize: 48 }}>🚪</div>
                <Title level={4}>闸门</Title>
                <Text type="secondary">
                  5种类型、智能流态识别
                </Text>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  size="large"
                  block
                >
                  添加闸门
                </Button>
              </Space>
            </Card>
          </Col>
          
          <Col span={8}>
            <Card
              hoverable
              onClick={() => setActiveEditor('weir')}
              style={{ textAlign: 'center' }}
            >
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div style={{ fontSize: 48 }}>📐</div>
                <Title level={4}>堰</Title>
                <Text type="secondary">
                  6种类型、流量曲线生成
                </Text>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  size="large"
                  block
                >
                  添加堰
                </Button>
              </Space>
            </Card>
          </Col>
        </Row>
      </Card>
      
      <Divider />
      
      {/* 已添加的结构列表 */}
      {structures.length > 0 && (
        <Card title="已添加的结构" bordered={false} style={{ marginTop: 24 }}>
          <List
            dataSource={structures}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button type="link" onClick={() => {
                    setEditingStructure(item);
                    setActiveEditor(item.type);
                  }}>
                    编辑
                  </Button>,
                  <Button type="link" danger>
                    删除
                  </Button>
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <div style={{ fontSize: 32 }}>
                      {item.type === 'pump' ? '⚙️' : item.type === 'gate' ? '🚪' : '📐'}
                    </div>
                  }
                  title={item.name}
                  description={`位置: ${item.position}m | 类型: ${
                    item.type === 'pump' ? '泵站' :
                    item.type === 'gate' ? '闸门' : '堰'
                  }`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
      
      {/* 编辑器Modal */}
      <Modal
        title={null}
        open={activeEditor !== null}
        onCancel={handleCancel}
        footer={null}
        width={1200}
        style={{ top: 20 }}
        destroyOnClose
      >
        {activeEditor === 'pump' && (
          <PumpStationEditor
            initialConfig={editingStructure?.config}
            onSave={(config) => handleSave('pump', config)}
            onCancel={handleCancel}
          />
        )}
        
        {activeEditor === 'gate' && (
          <GateEditor
            initialConfig={editingStructure?.config}
            onSave={(config) => handleSave('gate', config)}
            onCancel={handleCancel}
          />
        )}
        
        {activeEditor === 'weir' && (
          <WeirEditor
            initialConfig={editingStructure?.config}
            onSave={(config) => handleSave('weir', config)}
            onCancel={handleCancel}
          />
        )}
      </Modal>
      
      {/* 底部提示 */}
      <Alert
        message="💡 使用提示"
        description={
          <Space direction="vertical">
            <Text>1. 点击对应的卡片添加水工结构</Text>
            <Text>2. 在编辑器中配置参数（支持实时预览）</Text>
            <Text>3. 保存后结构将添加到模型中</Text>
            <Text>4. 支持后续编辑和删除操作</Text>
          </Space>
        }
        type="info"
        showIcon
        style={{ marginTop: 24 }}
      />
    </div>
  );
};

export default StructureToolbox;
