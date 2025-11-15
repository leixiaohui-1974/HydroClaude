/**
 * Pump Station Editor Component
 * 泵站编辑器组件
 * 
 * 对标商业软件（HEC-RAS、MIKE）的泵站建模功能
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
  Switch,
  Button,
  Space,
  Card,
  Table,
  Tabs,
  message,
  Divider,
  Row,
  Col,
  Alert
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  LineChartOutlined,
  SettingOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Option } = Select;
const { TabPane } = Tabs;

// 泵站类型
enum PumpType {
  SINGLE = 'single',
  PARALLEL = 'parallel',
  SERIES = 'series'
}

// 控制模式
enum ControlMode {
  MANUAL = 'manual',
  AUTO_LEVEL = 'auto_level',
  AUTO_FLOW = 'auto_flow',
  SCHEDULE = 'schedule'
}

// 泵曲线数据点
interface PumpCurvePoint {
  Q: number;  // 流量 (m³/s)
  H: number;  // 扬程 (m)
  eff?: number;  // 效率 (0-1)
}

// 泵站配置
interface PumpStationConfig {
  name: string;
  position: number;
  pumpType: PumpType;
  numPumps: number;
  controlMode: ControlMode;
  
  // 泵曲线
  curveType: 'polynomial' | 'table';
  polynomial?: [number, number, number];  // [a, b, c]
  curveData?: PumpCurvePoint[];
  
  // 运行范围
  Q_min: number;
  Q_max: number;
  H_min: number;
  H_max: number;
  
  // 控制规则
  startLevel?: number;
  stopLevel?: number;
  startFlow?: number;
  stopFlow?: number;
  hysteresis?: number;
  minRunTime?: number;
  minOffTime?: number;
}

interface Props {
  initialConfig?: Partial<PumpStationConfig>;
  onSave: (config: PumpStationConfig) => void;
  onCancel: () => void;
}

export const PumpStationEditor: React.FC<Props> = ({
  initialConfig,
  onSave,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [curveData, setCurveData] = useState<PumpCurvePoint[]>([]);
  const [curveType, setCurveType] = useState<'polynomial' | 'table'>('polynomial');
  
  useEffect(() => {
    if (initialConfig) {
      form.setFieldsValue(initialConfig);
      if (initialConfig.curveData) {
        setCurveData(initialConfig.curveData);
      }
      if (initialConfig.curveType) {
        setCurveType(initialConfig.curveType);
      }
    }
  }, [initialConfig, form]);
  
  // 预定义泵曲线
  const loadStandardCurve = (size: 'small' | 'medium' | 'large') => {
    const curves = {
      small: {
        polynomial: [10.0, -0.1, -0.001],
        Q_min: 0, Q_max: 5, H_min: 0, H_max: 10
      },
      medium: {
        polynomial: [25.0, -0.2, -0.002],
        Q_min: 0, Q_max: 10, H_min: 0, H_max: 25
      },
      large: {
        polynomial: [50.0, -0.3, -0.003],
        Q_min: 0, Q_max: 20, H_min: 0, H_max: 50
      }
    };
    
    const curve = curves[size];
    form.setFieldsValue({
      polynomial: curve.polynomial,
      Q_min: curve.Q_min,
      Q_max: curve.Q_max,
      H_min: curve.H_min,
      H_max: curve.H_max
    });
    
    message.success(`已加载${size === 'small' ? '小型' : size === 'medium' ? '中型' : '大型'}泵标准曲线`);
  };
  
  // 添加曲线数据点
  const addCurvePoint = () => {
    const newPoint: PumpCurvePoint = { Q: 0, H: 0, eff: 0.8 };
    setCurveData([...curveData, newPoint]);
  };
  
  // 删除曲线数据点
  const deleteCurvePoint = (index: number) => {
    const newData = curveData.filter((_, i) => i !== index);
    setCurveData(newData);
  };
  
  // 更新曲线数据点
  const updateCurvePoint = (index: number, field: keyof PumpCurvePoint, value: number) => {
    const newData = [...curveData];
    newData[index] = { ...newData[index], [field]: value };
    setCurveData(newData);
  };
  
  // 表格列定义
  const curveColumns: ColumnsType<PumpCurvePoint> = [
    {
      title: '流量 Q (m³/s)',
      dataIndex: 'Q',
      render: (value, record, index) => (
        <InputNumber
          value={value}
          onChange={(v) => updateCurvePoint(index, 'Q', v || 0)}
          min={0}
          step={0.1}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: '扬程 H (m)',
      dataIndex: 'H',
      render: (value, record, index) => (
        <InputNumber
          value={value}
          onChange={(v) => updateCurvePoint(index, 'H', v || 0)}
          min={0}
          step={0.1}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: '效率 η',
      dataIndex: 'eff',
      render: (value, record, index) => (
        <InputNumber
          value={value}
          onChange={(v) => updateCurvePoint(index, 'eff', v || 0)}
          min={0}
          max={1}
          step={0.01}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: '操作',
      render: (_, record, index) => (
        <Button
          type="link"
          danger
          icon={<DeleteOutlined />}
          onClick={() => deleteCurvePoint(index)}
        >
          删除
        </Button>
      )
    }
  ];
  
  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      const config: PumpStationConfig = {
        ...values,
        curveType,
        curveData: curveType === 'table' ? curveData : undefined
      };
      
      onSave(config);
      message.success('泵站配置已保存');
    } catch (error) {
      message.error('请检查表单输入');
    }
  };
  
  return (
    <Card
      title="⚙️ 泵站编辑器"
      extra={
        <Space>
          <Button onClick={onCancel}>取消</Button>
          <Button type="primary" onClick={handleSubmit}>
            保存
          </Button>
        </Space>
      }
    >
      <Alert
        message="对标商业软件功能"
        description="支持单泵/多泵、多种控制模式、泵特性曲线、自动启停控制等功能，与HEC-RAS和MIKE泵站模块对标。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          pumpType: PumpType.SINGLE,
          numPumps: 1,
          controlMode: ControlMode.MANUAL,
          curveType: 'polynomial',
          Q_min: 0,
          Q_max: 10,
          H_min: 0,
          H_max: 25,
          hysteresis: 0.1,
          minRunTime: 60,
          minOffTime: 60
        }}
      >
        <Tabs defaultActiveKey="basic">
          {/* 基本信息 */}
          <TabPane tab="📋 基本信息" key="basic">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="泵站名称"
                  name="name"
                  rules={[{ required: true, message: '请输入泵站名称' }]}
                >
                  <Input placeholder="例如：PS-001" />
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
            
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="泵站类型" name="pumpType">
                  <Select>
                    <Option value={PumpType.SINGLE}>单泵</Option>
                    <Option value={PumpType.PARALLEL}>并联泵组</Option>
                    <Option value={PumpType.SERIES}>串联泵组</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="泵数量" name="numPumps">
                  <InputNumber
                    style={{ width: '100%' }}
                    min={1}
                    max={10}
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item label="控制模式" name="controlMode">
              <Select>
                <Option value={ControlMode.MANUAL}>手动控制</Option>
                <Option value={ControlMode.AUTO_LEVEL}>自动水位控制</Option>
                <Option value={ControlMode.AUTO_FLOW}>自动流量控制</Option>
                <Option value={ControlMode.SCHEDULE}>时间表控制</Option>
              </Select>
            </Form.Item>
          </TabPane>
          
          {/* 泵特性曲线 */}
          <TabPane tab="📈 泵特性曲线" key="curve">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="泵特性曲线"
                description="定义泵的Q-H关系。可使用多项式或查表法。"
                type="info"
                showIcon
              />
              
              <Space>
                <span>曲线类型：</span>
                <Select
                  value={curveType}
                  onChange={setCurveType}
                  style={{ width: 150 }}
                >
                  <Option value="polynomial">多项式</Option>
                  <Option value="table">数据表</Option>
                </Select>
                
                <Divider type="vertical" />
                
                <span>快速加载：</span>
                <Button size="small" onClick={() => loadStandardCurve('small')}>
                  小型泵
                </Button>
                <Button size="small" onClick={() => loadStandardCurve('medium')}>
                  中型泵
                </Button>
                <Button size="small" onClick={() => loadStandardCurve('large')}>
                  大型泵
                </Button>
              </Space>
              
              {curveType === 'polynomial' ? (
                <>
                  <Divider>多项式系数 (Q = a + b*H + c*H²)</Divider>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item label="系数 a" name={['polynomial', 0]}>
                        <InputNumber style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="系数 b" name={['polynomial', 1]}>
                        <InputNumber style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="系数 c" name={['polynomial', 2]}>
                        <InputNumber style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                </>
              ) : (
                <>
                  <Divider>数据点表</Divider>
                  <Table
                    dataSource={curveData}
                    columns={curveColumns}
                    rowKey={(_, index) => index!}
                    pagination={false}
                    size="small"
                  />
                  <Button
                    type="dashed"
                    block
                    icon={<PlusOutlined />}
                    onClick={addCurvePoint}
                  >
                    添加数据点
                  </Button>
                </>
              )}
              
              <Divider>运行范围</Divider>
              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item label="最小流量 (m³/s)" name="Q_min">
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="最大流量 (m³/s)" name="Q_max">
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="最小扬程 (m)" name="H_min">
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="最大扬程 (m)" name="H_max">
                    <InputNumber style={{ width: '100%' }} min={0} />
                  </Form.Item>
                </Col>
              </Row>
            </Space>
          </TabPane>
          
          {/* 控制规则 */}
          <TabPane tab="🎛️ 控制规则" key="control">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="自动控制规则"
                description="定义泵的启动和停止条件，支持水位控制、流量控制和时间控制。"
                type="info"
                showIcon
              />
              
              <Divider>启动条件</Divider>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="启动水位 (m)"
                    name="startLevel"
                    tooltip="水位达到此值时启动泵"
                  >
                    <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="启动流量 (m³/s)"
                    name="startFlow"
                    tooltip="流量达到此值时启动泵"
                  >
                    <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
                  </Form.Item>
                </Col>
              </Row>
              
              <Divider>停止条件</Divider>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="停止水位 (m)"
                    name="stopLevel"
                    tooltip="水位降到此值时停止泵"
                  >
                    <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="停止流量 (m³/s)"
                    name="stopFlow"
                    tooltip="流量降到此值时停止泵"
                  >
                    <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
                  </Form.Item>
                </Col>
              </Row>
              
              <Divider>控制参数</Divider>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="迟滞带"
                    name="hysteresis"
                    tooltip="防止频繁启停的缓冲区"
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0}
                      step={0.01}
                      addonAfter="m"
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="最小运行时间"
                    name="minRunTime"
                    tooltip="泵启动后的最小运行时间"
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0}
                      addonAfter="秒"
                    />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="最小停机时间"
                    name="minOffTime"
                    tooltip="泵停止后的最小停机时间"
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0}
                      addonAfter="秒"
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Space>
          </TabPane>
        </Tabs>
      </Form>
    </Card>
  );
};

export default PumpStationEditor;
