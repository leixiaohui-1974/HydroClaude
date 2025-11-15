/**
 * Weir Editor Component
 * 堰编辑器组件
 * 
 * 支持6种堰类型，对标商业软件功能
 * 
 * @author HydroClaude Team
 * @date 2025-11-15
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
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
  Statistic,
  Table
} from 'antd';
import {
  SaveOutlined,
  CloseOutlined,
  CalculatorOutlined,
  InfoCircleOutlined,
  LineChartOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { TabPane } = Tabs;

// 堰类型
enum WeirType {
  SHARP_CRESTED = 'sharp',
  BROAD_CRESTED = 'broad',
  V_NOTCH = 'v_notch',
  RECTANGULAR = 'rectangular',
  TRAPEZOIDAL = 'trapezoidal',
  OGEE = 'ogee'
}

// 堰配置
interface WeirConfig {
  name: string;
  type: WeirType;
  position: number;
  width?: number;
  crestHeight: number;
  dischargeCoeff: number;
  
  // 宽顶堰特有
  crestLength?: number;
  
  // V型堰特有
  notchAngle?: number;
  
  // 梯形堰特有
  sideSlope?: number;
  
  // 溢流堰特有
  designHead?: number;
}

// 流量-水头数据点
interface FlowHeadData {
  head: number;
  discharge: number;
  velocity: number;
}

interface Props {
  initialConfig?: Partial<WeirConfig>;
  onSave: (config: WeirConfig) => void;
  onCancel: () => void;
}

export const WeirEditor: React.FC<Props> = ({
  initialConfig,
  onSave,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [weirType, setWeirType] = useState<WeirType>(WeirType.RECTANGULAR);
  const [flowCurveData, setFlowCurveData] = useState<FlowHeadData[]>([]);
  
  useEffect(() => {
    if (initialConfig) {
      form.setFieldsValue(initialConfig);
      if (initialConfig.type) {
        setWeirType(initialConfig.type);
      }
    }
  }, [initialConfig, form]);
  
  // 堰类型描述
  const weirTypeDescriptions = {
    [WeirType.SHARP_CRESTED]: {
      name: '尖顶堰',
      icon: '📐',
      description: '堰顶尖锐，流量公式精确，常用于测流',
      applications: '流量测量站、水文监测',
      formula: 'Q = 1.84 × b × H^1.5',
      range: '小流量测量（< 50 m³/s）'
    },
    [WeirType.BROAD_CRESTED]: {
      name: '宽顶堰',
      icon: '📏',
      description: '堰顶较宽，水流在堰顶达到临界流',
      applications: '大流量测量、灌溉渠系',
      formula: 'Q = 1.7 × b × √g × H^1.5',
      range: '大流量测量（> 100 m³/s）'
    },
    [WeirType.V_NOTCH]: {
      name: 'V型堰',
      icon: '🔺',
      description: 'V型切口，流量与水头的2.5次方成正比',
      applications: '小流量高精度测量',
      formula: 'Q = 1.4 × (8/15) × √(2g) × tan(θ/2) × H^2.5',
      range: '小流量测量（< 10 m³/s）'
    },
    [WeirType.RECTANGULAR]: {
      name: '矩形堰',
      icon: '▭',
      description: '最常见的堰型，适用范围广',
      applications: '一般测流、灌溉工程',
      formula: 'Q = 1.7 × b × H^1.5',
      range: '中等流量（20-200 m³/s）'
    },
    [WeirType.TRAPEZOIDAL]: {
      name: '梯形堰',
      icon: '⏢',
      description: '侧边坡度1:4，可补偿端部收缩',
      applications: '灌溉渠系、测流站',
      formula: 'Q = 1.86 × b_eff × H^1.5 (b_eff = b + 2×m×H)',
      range: '中等流量（30-300 m³/s）'
    },
    [WeirType.OGEE]: {
      name: '溢流堰',
      icon: '🌊',
      description: '堰面为抛物线形，过流能力强',
      applications: '大坝溢洪道、水库泄洪',
      formula: 'Q = 2.1 × L × H^1.5 (设计水头时)',
      range: '大流量（> 500 m³/s）'
    }
  };
  
  // 计算流量曲线
  const calculateFlowCurve = () => {
    const values = form.getFieldsValue();
    const { width, crestHeight, dischargeCoeff } = values;
    
    if (!crestHeight || !dischargeCoeff) {
      return;
    }
    
    const g = 9.81;
    const data: FlowHeadData[] = [];
    
    // 生成水头范围（0.1m 到 5m）
    for (let H = 0.1; H <= 5.0; H += 0.5) {
      let Q = 0;
      
      switch (weirType) {
        case WeirType.SHARP_CRESTED:
          Q = dischargeCoeff * (width || 5.0) * Math.pow(H, 1.5);
          break;
          
        case WeirType.BROAD_CRESTED:
          Q = dischargeCoeff * (width || 5.0) * Math.sqrt(g) * Math.pow(H, 1.5);
          break;
          
        case WeirType.V_NOTCH:
          const angle = ((values.notchAngle || 90) * Math.PI) / 180;
          Q = dischargeCoeff * (8.0/15.0) * Math.sqrt(2*g) * Math.tan(angle/2) * Math.pow(H, 2.5);
          break;
          
        case WeirType.RECTANGULAR:
          Q = dischargeCoeff * (width || 5.0) * Math.pow(H, 1.5);
          break;
          
        case WeirType.TRAPEZOIDAL:
          const sideSlope = values.sideSlope || 0.25;
          const b_eff = (width || 5.0) + 2 * sideSlope * H;
          Q = dischargeCoeff * b_eff * Math.pow(H, 1.5);
          break;
          
        case WeirType.OGEE:
          const designHead = values.designHead || 3.0;
          const headRatio = H / designHead;
          let Cd_adjusted = dischargeCoeff;
          
          if (headRatio < 1.0) {
            Cd_adjusted = dischargeCoeff * (0.9 + 0.1 * headRatio);
          } else {
            Cd_adjusted = dischargeCoeff * (1.0 - 0.05 * (headRatio - 1.0));
          }
          Cd_adjusted = Math.max(Cd_adjusted, dischargeCoeff * 0.85);
          
          Q = Cd_adjusted * (width || 5.0) * Math.pow(H, 1.5);
          break;
      }
      
      // 计算流速（近似）
      const area = weirType === WeirType.V_NOTCH
        ? 0.5 * H * H * Math.tan(((values.notchAngle || 90) * Math.PI) / 360)
        : (width || 5.0) * H;
      const velocity = area > 0 ? Q / area : 0;
      
      data.push({
        head: H,
        discharge: Q,
        velocity: velocity
      });
    }
    
    setFlowCurveData(data);
  };
  
  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const config: WeirConfig = {
        ...values,
        type: weirType
      };
      onSave(config);
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };
  
  const currentWeirInfo = weirTypeDescriptions[weirType];
  
  // 流量曲线表格列
  const flowCurveColumns: ColumnsType<FlowHeadData> = [
    {
      title: '水头 H (m)',
      dataIndex: 'head',
      key: 'head',
      render: (val) => val.toFixed(2)
    },
    {
      title: '流量 Q (m³/s)',
      dataIndex: 'discharge',
      key: 'discharge',
      render: (val) => val.toFixed(2)
    },
    {
      title: '流速 V (m/s)',
      dataIndex: 'velocity',
      key: 'velocity',
      render: (val) => val.toFixed(2)
    }
  ];
  
  return (
    <Card
      title={`${currentWeirInfo.icon} 堰编辑器 - ${currentWeirInfo.name}`}
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
        description={`${currentWeirInfo.description}。应用场景：${currentWeirInfo.applications}`}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          type: WeirType.RECTANGULAR,
          dischargeCoeff: 1.7,
          width: 5.0,
          crestHeight: 2.0,
          crestLength: 3.0,
          notchAngle: 90,
          sideSlope: 0.25,
          designHead: 3.0
        }}
      >
        <Tabs defaultActiveKey="basic">
          {/* 基本信息 */}
          <TabPane tab="📋 基本信息" key="basic">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="堰名称"
                  name="name"
                  rules={[{ required: true, message: '请输入堰名称' }]}
                >
                  <Input placeholder="例如：SW-001" />
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
            
            <Form.Item label="堰类型">
              <Radio.Group
                value={weirType}
                onChange={(e) => {
                  setWeirType(e.target.value);
                  setFlowCurveData([]);
                }}
                buttonStyle="solid"
              >
                <Radio.Button value={WeirType.SHARP_CRESTED}>
                  {weirTypeDescriptions[WeirType.SHARP_CRESTED].icon} 尖顶堰
                </Radio.Button>
                <Radio.Button value={WeirType.BROAD_CRESTED}>
                  {weirTypeDescriptions[WeirType.BROAD_CRESTED].icon} 宽顶堰
                </Radio.Button>
                <Radio.Button value={WeirType.V_NOTCH}>
                  {weirTypeDescriptions[WeirType.V_NOTCH].icon} V型堰
                </Radio.Button>
                <Radio.Button value={WeirType.RECTANGULAR}>
                  {weirTypeDescriptions[WeirType.RECTANGULAR].icon} 矩形堰
                </Radio.Button>
                <Radio.Button value={WeirType.TRAPEZOIDAL}>
                  {weirTypeDescriptions[WeirType.TRAPEZOIDAL].icon} 梯形堰
                </Radio.Button>
                <Radio.Button value={WeirType.OGEE}>
                  {weirTypeDescriptions[WeirType.OGEE].icon} 溢流堰
                </Radio.Button>
              </Radio.Group>
            </Form.Item>
            
            <Alert
              message={`流量公式: ${currentWeirInfo.formula}`}
              type="success"
              showIcon
              icon={<InfoCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
            
            <Alert
              message={`适用范围: ${currentWeirInfo.range}`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <Row gutter={16}>
              {weirType !== WeirType.V_NOTCH && (
                <Col span={8}>
                  <Form.Item
                    label="堰宽 (m)"
                    name="width"
                    rules={[{ required: true, message: '请输入宽度' }]}
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0.1}
                      step={0.1}
                    />
                  </Form.Item>
                </Col>
              )}
              <Col span={8}>
                <Form.Item
                  label="堰顶高程 (m)"
                  name="crestHeight"
                  rules={[{ required: true, message: '请输入堰顶高程' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    step={0.1}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  label="流量系数"
                  name="dischargeCoeff"
                  tooltip={
                    weirType === WeirType.SHARP_CRESTED ? "尖顶堰: 1.7-1.84" :
                    weirType === WeirType.BROAD_CRESTED ? "宽顶堰: 1.6-1.7" :
                    weirType === WeirType.V_NOTCH ? "V型堰: 1.3-1.4" :
                    weirType === WeirType.OGEE ? "溢流堰: 2.0-2.2" :
                    "通常在1.6-2.0之间"
                  }
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0.1}
                    max={3.0}
                    step={0.01}
                  />
                </Form.Item>
              </Col>
            </Row>
            
            {/* 特定类型参数 */}
            {weirType === WeirType.BROAD_CRESTED && (
              <Form.Item
                label="堰顶长度 (m)"
                name="crestLength"
                tooltip="宽顶堰的堰顶长度"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.5}
                  step={0.1}
                />
              </Form.Item>
            )}
            
            {weirType === WeirType.V_NOTCH && (
              <Form.Item
                label="V型角度 (度)"
                name="notchAngle"
                tooltip="常用90°或60°"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={30}
                  max={120}
                  step={15}
                />
              </Form.Item>
            )}
            
            {weirType === WeirType.TRAPEZOIDAL && (
              <Form.Item
                label="侧边坡度"
                name="sideSlope"
                tooltip="水平/垂直，Cipolletti堰为1:4 (0.25)"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  max={1}
                  step={0.05}
                />
              </Form.Item>
            )}
            
            {weirType === WeirType.OGEE && (
              <Form.Item
                label="设计水头 (m)"
                name="designHead"
                tooltip="溢流堰的设计水头，在此水头时流量系数最大"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.5}
                  step={0.1}
                />
              </Form.Item>
            )}
          </TabPane>
          
          {/* 流量曲线 */}
          <TabPane tab="📊 流量曲线" key="curve">
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Alert
                message="Q-H关系曲线"
                description="流量-水头关系曲线，用于设计和选型参考"
                type="info"
                showIcon
              />
              
              <Button
                type="primary"
                icon={<LineChartOutlined />}
                onClick={calculateFlowCurve}
                block
                size="large"
              >
                生成流量曲线
              </Button>
              
              {flowCurveData.length > 0 && (
                <>
                  <Card title="流量曲线数据" size="small">
                    <Table
                      dataSource={flowCurveData}
                      columns={flowCurveColumns}
                      rowKey="head"
                      pagination={false}
                      size="small"
                      scroll={{ y: 400 }}
                    />
                  </Card>
                  
                  <Card title="曲线分析" size="small">
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="最小流量"
                          value={Math.min(...flowCurveData.map(d => d.discharge)).toFixed(2)}
                          suffix="m³/s"
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="最大流量"
                          value={Math.max(...flowCurveData.map(d => d.discharge)).toFixed(2)}
                          suffix="m³/s"
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="平均流速"
                          value={(flowCurveData.reduce((sum, d) => sum + d.velocity, 0) / flowCurveData.length).toFixed(2)}
                          suffix="m/s"
                        />
                      </Col>
                    </Row>
                    
                    <Divider />
                    
                    <Alert
                      message="设计建议"
                      description={
                        weirType === WeirType.V_NOTCH
                          ? "V型堰适合小流量高精度测量，建议流量< 10 m³/s"
                          : weirType === WeirType.BROAD_CRESTED
                          ? "宽顶堰适合大流量测量，建议流量> 100 m³/s"
                          : weirType === WeirType.SHARP_CRESTED
                          ? "尖顶堰测流精度高，建议用于流量监测站"
                          : weirType === WeirType.OGEE
                          ? "溢流堰过流能力强，适合大坝溢洪道"
                          : "矩形堰和梯形堰适用范围广，是最常用的堰型"
                      }
                      type="success"
                      showIcon
                    />
                  </Card>
                </>
              )}
            </Space>
          </TabPane>
        </Tabs>
      </Form>
    </Card>
  );
};

export default WeirEditor;
