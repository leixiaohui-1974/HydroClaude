/**
 * Gate Editor Component
 * 闸门编辑器组件
 * 
 * 支持5种闸门类型，对标商业软件功能
 * 
 * @author HydroClaude Team
 * @date 2025-11-15
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Space,
  Card,
  Row,
  Col,
  Alert,
  Divider,
  Tabs,
  Radio,
  Tooltip,
  Statistic
} from 'antd';
import {
  SaveOutlined,
  CloseOutlined,
  CalculatorOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';

const { Option } = Select;
const { TabPane } = Tabs;

// 闸门类型
enum GateType {
  SLUICE = 'sluice',           // 滑动闸门
  RADIAL = 'radial',           // 径向闸门
  VERTICAL_LIFT = 'vertical',  // 垂直提升闸门
  ROLLER = 'roller',           // 滚轮闸门
  FLAP = 'flap'                // 翻板闸门
}

// 流态
enum FlowRegime {
  FREE_FLOW = 'free',
  SUBMERGED = 'submerged',
  ORIFICE = 'orifice',
  WEIR = 'weir'
}

// 闸门配置
interface GateConfig {
  name: string;
  type: GateType;
  position: number;
  width: number;
  opening: number;
  dischargeCoeff: number;
  
  // 径向闸门特有
  radius?: number;
  
  // 垂直提升闸门特有
  gateHeight?: number;
  weirCoeff?: number;
  
  // 翻板闸门特有
  gateLength?: number;
  angle?: number;
}

// 计算预览结果
interface FlowPreview {
  discharge: number;
  regime: string;
  velocity?: number;
  froudeNumber?: number;
}

interface Props {
  initialConfig?: Partial<GateConfig>;
  onSave: (config: GateConfig) => void;
  onCancel: () => void;
}

export const GateEditor: React.FC<Props> = ({
  initialConfig,
  onSave,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [gateType, setGateType] = useState<GateType>(GateType.SLUICE);
  const [flowPreview, setFlowPreview] = useState<FlowPreview | null>(null);
  
  // 测试条件（用于预览）
  const [testConditions, setTestConditions] = useState({
    h_upstream: 8.0,
    h_downstream: 3.0
  });
  
  useEffect(() => {
    if (initialConfig) {
      form.setFieldsValue(initialConfig);
      if (initialConfig.type) {
        setGateType(initialConfig.type);
      }
    }
  }, [initialConfig, form]);
  
  // 闸门类型描述
  const gateTypeDescriptions = {
    [GateType.SLUICE]: {
      name: '滑动闸门',
      icon: '🚪',
      description: '最常见的闸门类型，垂直提升，底部出流',
      applications: '一般水闸、灌溉渠系',
      formula: 'Q = Cd × b × a × √(2gh)'
    },
    [GateType.RADIAL]: {
      name: '径向闸门',
      icon: '🌉',
      description: '弧形门叶，铰链在圆心，启闭力小',
      applications: '大型水工建筑、水库闸门',
      formula: 'Q = Cd(θ) × b × a × √(2gh), Cd随开度调整'
    },
    [GateType.VERTICAL_LIFT]: {
      name: '垂直提升闸门',
      icon: '⬆️',
      description: '整体垂直提升，可堰流或孔流',
      applications: '船闸、大型水闸',
      formula: '智能识别：孔流/堰流/过渡流'
    },
    [GateType.ROLLER]: {
      name: '滚轮闸门',
      icon: '🎢',
      description: '门叶沿轨道运行，摩擦力小',
      applications: '大跨度闸门',
      formula: 'Q = Cd × b × a × √(2gh), Cd略高于滑动闸门'
    },
    [GateType.FLAP]: {
      name: '翻板闸门',
      icon: '🔄',
      description: '门叶绕底部铰链旋转，可自动翻转',
      applications: '防洪、自动调节',
      formula: 'Q = Cd × b × L_eff × √(2gH)'
    }
  };
  
  // 计算流量预览
  const calculateFlowPreview = () => {
    const values = form.getFieldsValue();
    const { width, opening, dischargeCoeff } = values;
    const { h_upstream, h_downstream } = testConditions;
    
    if (!width || !opening || !dischargeCoeff || !h_upstream) {
      return;
    }
    
    const g = 9.81;
    let Q = 0;
    let regime = FlowRegime.FREE_FLOW;
    
    // 根据闸门类型计算
    switch (gateType) {
      case GateType.SLUICE:
      case GateType.ROLLER:
        // 判断流态
        if (h_downstream < 0.67 * h_upstream) {
          // 自由流
          Q = dischargeCoeff * width * opening * Math.sqrt(2 * g * h_upstream);
          regime = FlowRegime.FREE_FLOW;
        } else {
          // 淹没流
          const dh = Math.max(h_upstream - h_downstream, 0.01);
          Q = dischargeCoeff * width * opening * Math.sqrt(2 * g * dh);
          regime = FlowRegime.SUBMERGED;
        }
        break;
        
      case GateType.RADIAL:
        const radius = values.radius || 5.0;
        const openingRatio = Math.min(opening / radius, 1.0);
        // 调整流量系数
        const Cd_max = dischargeCoeff * 1.15;
        const Cd_min = dischargeCoeff * 0.85;
        const Cd_adjusted = Cd_min + (Cd_max - Cd_min) * (1 - Math.pow((openingRatio - 0.5), 2) / 0.25);
        
        if (h_downstream < 0.67 * h_upstream) {
          Q = Cd_adjusted * width * opening * Math.sqrt(2 * g * h_upstream);
          regime = FlowRegime.FREE_FLOW;
        } else {
          const dh = Math.max(h_upstream - h_downstream, 0.01);
          Q = Cd_adjusted * width * opening * Math.sqrt(2 * g * dh);
          regime = FlowRegime.SUBMERGED;
        }
        break;
        
      case GateType.VERTICAL_LIFT:
        // 智能流态识别
        if (opening < 0.5 * h_upstream) {
          // 孔流
          if (h_downstream < 0.67 * h_upstream) {
            Q = dischargeCoeff * width * opening * Math.sqrt(2 * g * h_upstream);
          } else {
            const dh = Math.max(h_upstream - h_downstream, 0.01);
            Q = dischargeCoeff * width * opening * Math.sqrt(2 * g * dh);
          }
          regime = FlowRegime.ORIFICE;
        } else if (opening > 0.8 * h_upstream) {
          // 堰流
          const gateHeight = values.gateHeight || 10.0;
          const gateBottom = gateHeight - opening;
          const H = Math.max(h_upstream - gateBottom, 0.0);
          const weirCoeff = values.weirCoeff || 1.7;
          Q = weirCoeff * width * Math.pow(H, 1.5);
          regime = FlowRegime.WEIR;
        } else {
          // 过渡流
          Q = dischargeCoeff * width * opening * Math.sqrt(2 * g * h_upstream);
          regime = FlowRegime.FREE_FLOW;
        }
        break;
        
      case GateType.FLAP:
        const gateLength = values.gateLength || 5.0;
        const angle = (values.angle || 45) * Math.PI / 180;
        const gateTop = gateLength * Math.cos(angle);
        
        if (h_upstream > gateTop) {
          const H = h_upstream - gateTop;
          const L_eff = gateLength * Math.sin(angle);
          Q = dischargeCoeff * width * L_eff * Math.sqrt(2 * g * H);
          regime = FlowRegime.WEIR;
        } else {
          Q = 0;
        }
        break;
    }
    
    // 计算流速和Froude数
    const area = width * opening;
    const velocity = area > 0 ? Q / area : 0;
    const froudeNumber = opening > 0 ? velocity / Math.sqrt(g * opening) : 0;
    
    setFlowPreview({
      discharge: Q,
      regime: regime,
      velocity: velocity,
      froudeNumber: froudeNumber
    });
  };
  
  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const config: GateConfig = {
        ...values,
        type: gateType
      };
      onSave(config);
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };
  
  const currentGateInfo = gateTypeDescriptions[gateType];
  
  return (
    <Card
      title={`${currentGateInfo.icon} 闸门编辑器 - ${currentGateInfo.name}`}
      extra={
        <Space>
          <Button icon={<CloseOutlined />} onClick={onCancel}>
            取消
          </Button>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSubmit}>
            保存
          </Button>
        </Space>
      }
    >
      <Alert
        message="对标商业软件功能"
        description={`${currentGateInfo.description}。应用场景：${currentGateInfo.applications}`}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          type: GateType.SLUICE,
          dischargeCoeff: 0.6,
          width: 10.0,
          opening: 2.0,
          radius: 6.0,
          gateHeight: 12.0,
          weirCoeff: 1.7,
          gateLength: 5.0,
          angle: 45
        }}
      >
        <Tabs defaultActiveKey="basic" onChange={() => calculateFlowPreview()}>
          {/* 基本信息 */}
          <TabPane tab="📋 基本信息" key="basic">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="闸门名称"
                  name="name"
                  rules={[{ required: true, message: '请输入闸门名称' }]}
                >
                  <Input placeholder="例如：RG-001" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="位置 (m)"
                  name="position"
                  rules={[{ required: true, message: '请输入位置' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    placeholder="渠道上的位置"
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item label="闸门类型">
              <Radio.Group
                value={gateType}
                onChange={(e) => {
                  setGateType(e.target.value);
                  setFlowPreview(null);
                }}
                buttonStyle="solid"
              >
                <Radio.Button value={GateType.SLUICE}>
                  {gateTypeDescriptions[GateType.SLUICE].icon} 滑动闸门
                </Radio.Button>
                <Radio.Button value={GateType.RADIAL}>
                  {gateTypeDescriptions[GateType.RADIAL].icon} 径向闸门
                </Radio.Button>
                <Radio.Button value={GateType.VERTICAL_LIFT}>
                  {gateTypeDescriptions[GateType.VERTICAL_LIFT].icon} 垂直提升
                </Radio.Button>
                <Radio.Button value={GateType.ROLLER}>
                  {gateTypeDescriptions[GateType.ROLLER].icon} 滚轮闸门
                </Radio.Button>
                <Radio.Button value={GateType.FLAP}>
                  {gateTypeDescriptions[GateType.FLAP].icon} 翻板闸门
                </Radio.Button>
              </Radio.Group>
            </Form.Item>
            
            <Alert
              message={`流量公式: ${currentGateInfo.formula}`}
              type="success"
              showIcon
              icon={<InfoCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
            
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  label="闸门宽度 (m)"
                  name="width"
                  rules={[{ required: true, message: '请输入宽度' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0.1}
                    step={0.1}
                    onChange={calculateFlowPreview}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label={gateType === GateType.FLAP ? "翻转角度 (度)" : "开度 (m)"}
                  name={gateType === GateType.FLAP ? "angle" : "opening"}
                  rules={[{ required: true, message: '请输入开度' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    step={gateType === GateType.FLAP ? 1 : 0.1}
                    onChange={calculateFlowPreview}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label="流量系数"
                  name="dischargeCoeff"
                  tooltip="通常在0.5-0.8之间"
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0.1}
                    max={1.0}
                    step={0.01}
                    onChange={calculateFlowPreview}
                  />
                </Form.Item>
              </Col>
            </Row>
            
            {/* 特定类型参数 */}
            {gateType === GateType.RADIAL && (
              <Form.Item
                label="闸门半径 (m)"
                name="radius"
                tooltip="径向闸门的圆弧半径"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={1}
                  step={0.1}
                  onChange={calculateFlowPreview}
                />
              </Form.Item>
            )}
            
            {gateType === GateType.VERTICAL_LIFT && (
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="闸门总高度 (m)"
                    name="gateHeight"
                    tooltip="闸门的总高度"
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={1}
                      step={0.1}
                      onChange={calculateFlowPreview}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="堰流系数"
                    name="weirCoeff"
                    tooltip="堰流模式下的流量系数"
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0.1}
                      max={3.0}
                      step={0.1}
                      onChange={calculateFlowPreview}
                    />
                  </Form.Item>
                </Col>
              </Row>
            )}
            
            {gateType === GateType.FLAP && (
              <Form.Item
                label="闸门长度 (m)"
                name="gateLength"
                tooltip="翻板闸门的门叶长度"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={1}
                  step={0.1}
                  onChange={calculateFlowPreview}
                />
              </Form.Item>
            )}
          </TabPane>
          
          {/* 流量预览 */}
          <TabPane tab="📊 流量预览" key="preview">
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Alert
                message="流量计算预览"
                description="输入测试条件，预览闸门流量和流态"
                type="info"
                showIcon
              />
              
              <Card title="测试条件" size="small">
                <Row gutter={16}>
                  <Col span={12}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <label>上游水深 (m)</label>
                      <InputNumber
                        style={{ width: '100%' }}
                        value={testConditions.h_upstream}
                        onChange={(v) => {
                          setTestConditions({ ...testConditions, h_upstream: v || 0 });
                          setTimeout(calculateFlowPreview, 100);
                        }}
                        min={0}
                        step={0.1}
                      />
                    </Space>
                  </Col>
                  <Col span={12}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <label>下游水深 (m)</label>
                      <InputNumber
                        style={{ width: '100%' }}
                        value={testConditions.h_downstream}
                        onChange={(v) => {
                          setTestConditions({ ...testConditions, h_downstream: v || 0 });
                          setTimeout(calculateFlowPreview, 100);
                        }}
                        min={0}
                        step={0.1}
                      />
                    </Space>
                  </Col>
                </Row>
                
                <Divider />
                
                <Button
                  type="primary"
                  icon={<CalculatorOutlined />}
                  onClick={calculateFlowPreview}
                  block
                >
                  计算流量
                </Button>
              </Card>
              
              {flowPreview && (
                <Card title="计算结果" size="small">
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic
                        title="流量"
                        value={flowPreview.discharge.toFixed(2)}
                        suffix="m³/s"
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="流态"
                        value={flowPreview.regime}
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="流速"
                        value={flowPreview.velocity?.toFixed(2) || '-'}
                        suffix="m/s"
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="Froude数"
                        value={flowPreview.froudeNumber?.toFixed(3) || '-'}
                        valueStyle={{
                          color: (flowPreview.froudeNumber || 0) > 1 ? '#cf1322' : '#3f8600'
                        }}
                      />
                    </Col>
                  </Row>
                  
                  <Divider />
                  
                  <Alert
                    message={
                      (flowPreview.froudeNumber || 0) < 1
                        ? '亚临界流（Fr < 1）'
                        : (flowPreview.froudeNumber || 0) > 1
                        ? '超临界流（Fr > 1）'
                        : '临界流（Fr ≈ 1）'
                    }
                    type={(flowPreview.froudeNumber || 0) > 1 ? 'warning' : 'success'}
                    showIcon
                  />
                </Card>
              )}
            </Space>
          </TabPane>
        </Tabs>
      </Form>
    </Card>
  );
};

export default GateEditor;
