/**
 * Water Quality Panel - 水质模拟面板
 * 完整的水质参数配置和模拟界面
 * 
 * Features:
 * - DO/BOD Configuration (溶解氧/生化需氧量配置)
 * - Nutrient Transport (营养物质传输 - 氮、磷)
 * - Temperature Modeling (水温模型)
 * - Pollution Source Management (污染源管理)
 * - Water Quality Standards (水质标准)
 * - Real-time Monitoring (实时监控)
 */

import React, { useState } from 'react';
import {
  Layout,
  Card,
  Tabs,
  Form,
  InputNumber,
  Slider,
  Switch,
  Button,
  Select,
  Space,
  Row,
  Col,
  Divider,
  Alert,
  Table,
  Tag,
  Progress,
  Statistic,
  Typography,
  Tooltip,
  Badge,
  Modal,
  List
} from 'antd';
import {
  ExperimentOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
  FireOutlined,
  AlertOutlined,
  PlusOutlined,
  DeleteOutlined,
  LineChartOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { Line } from 'react-chartjs-2';
import './WaterQualityPanel.css';

const { Content } = Layout;
const { TabPane } = Tabs;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ============================================================================
// DO/BOD Configuration
// ============================================================================

interface DOBODConfig {
  initialDO: number;
  initialBOD: number;
  saturatedDO: number;
  deoxygenationRate: number;
  rearationRate: number;
  sedimentOxygenDemand: number;
  photosynthesisRate: number;
  respirationRate: number;
  temperature: number;
  enableAdvancedModel: boolean;
}

const DOBODConfiguration: React.FC<{
  config: DOBODConfig;
  onChange: (config: DOBODConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof DOBODConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  // Calculate DO deficit and critical point
  const getDODeficit = () => {
    return config.saturatedDO - config.initialDO;
  };

  const getCriticalTime = () => {
    if (config.rearationRate === 0 || config.deoxygenationRate === 0) return 0;
    const K1 = config.deoxygenationRate;
    const K2 = config.rearationRate;
    const D0 = getDODeficit();
    const L0 = config.initialBOD;

    if (K2 <= K1) return 0;
    return Math.log((K2 * (1 - D0 * (K2 - K1) / (K1 * L0))) / K1) / (K2 - K1);
  };

  const getWaterQualityStatus = () => {
    if (config.initialDO >= 6) return { status: 'success', text: 'Excellent / 优秀' };
    if (config.initialDO >= 4) return { status: 'warning', text: 'Acceptable / 可接受' };
    return { status: 'error', text: 'Poor / 差' };
  };

  const status = getWaterQualityStatus();

  return (
    <Card
      title={
        <Space>
          <ExperimentOutlined style={{ color: '#1890ff' }} />
          <span>DO/BOD Configuration / 溶解氧/生化需氧量配置</span>
        </Space>
      }
      extra={
        <Tag color={status.status === 'success' ? 'green' : status.status === 'warning' ? 'orange' : 'red'}>
          {status.text}
        </Tag>
      }
    >
      <Alert
        message="Streeter-Phelps Model"
        description="经典的DO-BOD平衡模型，用于河流水质预测"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Form layout="vertical">
        <Divider orientation="left">Dissolved Oxygen (DO) / 溶解氧</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label={
              <span>
                Initial DO / 初始溶解氧 (mg/L)
                <Tooltip title="Current dissolved oxygen concentration in water">
                  <InfoCircleOutlined style={{ marginLeft: 8, color: '#1890ff' }} />
                </Tooltip>
              </span>
            }>
              <InputNumber
                value={config.initialDO}
                onChange={(v) => handleChange('initialDO', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={15}
                step={0.1}
                precision={2}
              />
              <Slider
                value={config.initialDO}
                onChange={(v) => handleChange('initialDO', v)}
                min={0}
                max={12}
                step={0.1}
                marks={{ 0: '0', 4: '4', 8: '8', 12: '12' }}
                style={{ marginTop: 8 }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Saturated DO / 饱和溶解氧 (mg/L)">
              <InputNumber
                value={config.saturatedDO}
                onChange={(v) => handleChange('saturatedDO', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={15}
                step={0.1}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Temperature / 水温 (°C)">
              <InputNumber
                value={config.temperature}
                onChange={(v) => handleChange('temperature', v || 20)}
                style={{ width: '100%' }}
                min={0}
                max={40}
                step={0.5}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Biochemical Oxygen Demand (BOD) / 生化需氧量</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label="Initial BOD / 初始BOD (mg/L)">
              <InputNumber
                value={config.initialBOD}
                onChange={(v) => handleChange('initialBOD', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={100}
                step={1}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label={
              <span>
                Deoxygenation Rate (K1) / 脱氧系数 (1/day)
                <Tooltip title="Rate at which BOD consumes oxygen">
                  <InfoCircleOutlined style={{ marginLeft: 8, color: '#1890ff' }} />
                </Tooltip>
              </span>
            }>
              <Slider
                value={config.deoxygenationRate}
                onChange={(v) => handleChange('deoxygenationRate', v)}
                min={0}
                max={5}
                step={0.01}
                marks={{ 0: '0', 0.1: '0.1', 1: '1', 5: '5' }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label={
              <span>
                Rearation Rate (K2) / 复氧系数 (1/day)
                <Tooltip title="Rate at which atmospheric oxygen dissolves into water">
                  <InfoCircleOutlined style={{ marginLeft: 8, color: '#1890ff' }} />
                </Tooltip>
              </span>
            }>
              <Slider
                value={config.rearationRate}
                onChange={(v) => handleChange('rearationRate', v)}
                min={0}
                max={10}
                step={0.01}
                marks={{ 0: '0', 0.5: '0.5', 2: '2', 10: '10' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Advanced Parameters / 高级参数</Divider>

        <Form.Item label="Advanced Model / 高级模型">
          <Switch
            checked={config.enableAdvancedModel}
            onChange={(v) => handleChange('enableAdvancedModel', v)}
            checkedChildren="ON"
            unCheckedChildren="OFF"
          />
        </Form.Item>

        {config.enableAdvancedModel && (
          <Row gutter={24}>
            <Col span={8}>
              <Form.Item label="Sediment O2 Demand / 底泥耗氧 (mg/L/day)">
                <InputNumber
                  value={config.sedimentOxygenDemand}
                  onChange={(v) => handleChange('sedimentOxygenDemand', v || 0)}
                  style={{ width: '100%' }}
                  min={0}
                  max={10}
                  step={0.1}
                />
              </Form.Item>
            </Col>

            <Col span={8}>
              <Form.Item label="Photosynthesis Rate / 光合作用速率 (mg/L/day)">
                <InputNumber
                  value={config.photosynthesisRate}
                  onChange={(v) => handleChange('photosynthesisRate', v || 0)}
                  style={{ width: '100%' }}
                  min={0}
                  max={10}
                  step={0.1}
                />
              </Form.Item>
            </Col>

            <Col span={8}>
              <Form.Item label="Respiration Rate / 呼吸作用速率 (mg/L/day)">
                <InputNumber
                  value={config.respirationRate}
                  onChange={(v) => handleChange('respirationRate', v || 0)}
                  style={{ width: '100%' }}
                  min={0}
                  max={10}
                  step={0.1}
                />
              </Form.Item>
            </Col>
          </Row>
        )}

        <Divider />

        <div className="water-quality-info-panel">
          <Row gutter={16}>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="DO Deficit / 溶解氧亏损"
                  value={getDODeficit()}
                  precision={2}
                  suffix="mg/L"
                  valueStyle={{ color: getDODeficit() > 4 ? '#cf1322' : '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="Critical Time / 临界时间"
                  value={getCriticalTime()}
                  precision={2}
                  suffix="days"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic
                  title="DO Saturation / 饱和度"
                  value={(config.initialDO / config.saturatedDO) * 100}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: (config.initialDO / config.saturatedDO) > 0.7 ? '#3f8600' : '#cf1322' }}
                />
              </Card>
            </Col>
          </Row>

          <Divider />

          <Title level={5}>Streeter-Phelps Equation / 氧垂曲线方程</Title>
          <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', fontFamily: 'monospace' }}>
            <Text>
              D(t) = (K₁·L₀)/(K₂-K₁) · (e^(-K₁·t) - e^(-K₂·t)) + D₀·e^(-K₂·t)
            </Text>
            <br />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              D: DO deficit | L: BOD | K₁: Deoxygenation | K₂: Rearation
            </Text>
          </div>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// Nutrient Configuration
// ============================================================================

interface NutrientConfig {
  totalNitrogen: number;
  totalPhosphorus: number;
  ammonia: number;
  nitrate: number;
  nitrite: number;
  orthophosphate: number;
  nitrificationRate: number;
  denitrificationRate: number;
  phosphorusAdsorption: number;
  algaeGrowthRate: number;
  algaeDeathRate: number;
}

const NutrientConfiguration: React.FC<{
  config: NutrientConfig;
  onChange: (config: NutrientConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof NutrientConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const getEutrophicationLevel = () => {
    const TN = config.totalNitrogen;
    const TP = config.totalPhosphorus;

    if (TN < 0.2 && TP < 0.01) return { level: 'Oligotrophic / 贫营养', color: 'green' };
    if (TN < 0.5 && TP < 0.03) return { level: 'Mesotrophic / 中营养', color: 'blue' };
    if (TN < 1.5 && TP < 0.1) return { level: 'Eutrophic / 富营养', color: 'orange' };
    return { level: 'Hypertrophic / 超富营养', color: 'red' };
  };

  const eutrophication = getEutrophicationLevel();

  return (
    <Card
      title={
        <Space>
          <DashboardOutlined style={{ color: '#52c41a' }} />
          <span>Nutrient Configuration / 营养物质配置</span>
        </Space>
      }
      extra={
        <Tag color={eutrophication.color}>
          {eutrophication.level}
        </Tag>
      }
    >
      <Alert
        message="Nutrient Cycling Model"
        description="氮、磷营养物质的迁移转化模型"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Form layout="vertical">
        <Divider orientation="left">Nitrogen (N) / 氮</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label="Total Nitrogen (TN) / 总氮 (mg/L)">
              <InputNumber
                value={config.totalNitrogen}
                onChange={(v) => handleChange('totalNitrogen', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={10}
                step={0.01}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Ammonia (NH₃-N) / 氨氮 (mg/L)">
              <InputNumber
                value={config.ammonia}
                onChange={(v) => handleChange('ammonia', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={5}
                step={0.01}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Nitrate (NO₃-N) / 硝酸盐氮 (mg/L)">
              <InputNumber
                value={config.nitrate}
                onChange={(v) => handleChange('nitrate', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={5}
                step={0.01}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="Nitrification Rate / 硝化速率 (1/day)">
              <Slider
                value={config.nitrificationRate}
                onChange={(v) => handleChange('nitrificationRate', v)}
                min={0}
                max={2}
                step={0.01}
                marks={{ 0: '0', 0.5: '0.5', 1: '1', 2: '2' }}
              />
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item label="Denitrification Rate / 反硝化速率 (1/day)">
              <Slider
                value={config.denitrificationRate}
                onChange={(v) => handleChange('denitrificationRate', v)}
                min={0}
                max={1}
                step={0.01}
                marks={{ 0: '0', 0.2: '0.2', 0.5: '0.5', 1: '1' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Phosphorus (P) / 磷</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label="Total Phosphorus (TP) / 总磷 (mg/L)">
              <InputNumber
                value={config.totalPhosphorus}
                onChange={(v) => handleChange('totalPhosphorus', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={1}
                step={0.001}
                precision={3}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Orthophosphate (PO₄-P) / 正磷酸盐 (mg/L)">
              <InputNumber
                value={config.orthophosphate}
                onChange={(v) => handleChange('orthophosphate', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={0.5}
                step={0.001}
                precision={3}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="P Adsorption Rate / 磷吸附速率 (1/day)">
              <Slider
                value={config.phosphorusAdsorption}
                onChange={(v) => handleChange('phosphorusAdsorption', v)}
                min={0}
                max={1}
                step={0.01}
                marks={{ 0: '0', 0.5: '0.5', 1: '1' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Algae / 藻类</Divider>

        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="Algae Growth Rate / 藻类生长速率 (1/day)">
              <Slider
                value={config.algaeGrowthRate}
                onChange={(v) => handleChange('algaeGrowthRate', v)}
                min={0}
                max={3}
                step={0.01}
                marks={{ 0: '0', 1: '1', 2: '2', 3: '3' }}
              />
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item label="Algae Death Rate / 藻类死亡速率 (1/day)">
              <Slider
                value={config.algaeDeathRate}
                onChange={(v) => handleChange('algaeDeathRate', v)}
                min={0}
                max={1}
                step={0.01}
                marks={{ 0: '0', 0.2: '0.2', 0.5: '0.5', 1: '1' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider />

        <div className="nutrient-info-panel">
          <Title level={5}>Eutrophication Assessment / 富营养化评估</Title>
          <Row gutter={16}>
            <Col span={12}>
              <Progress
                type="dashboard"
                percent={(config.totalNitrogen / 2) * 100}
                format={() => `TN: ${config.totalNitrogen.toFixed(2)}`}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </Col>
            <Col span={12}>
              <Progress
                type="dashboard"
                percent={(config.totalPhosphorus / 0.2) * 100}
                format={() => `TP: ${config.totalPhosphorus.toFixed(3)}`}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </Col>
          </Row>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// Main Water Quality Panel
// ============================================================================

const WaterQualityPanel: React.FC = () => {
  const [dobodConfig, setDOBODConfig] = useState<DOBODConfig>({
    initialDO: 7.5,
    initialBOD: 10.0,
    saturatedDO: 9.2,
    deoxygenationRate: 0.3,
    rearationRate: 0.5,
    sedimentOxygenDemand: 1.0,
    photosynthesisRate: 2.0,
    respirationRate: 1.5,
    temperature: 20,
    enableAdvancedModel: false
  });

  const [nutrientConfig, setNutrientConfig] = useState<NutrientConfig>({
    totalNitrogen: 1.0,
    totalPhosphorus: 0.05,
    ammonia: 0.3,
    nitrate: 0.6,
    nitrite: 0.05,
    orthophosphate: 0.02,
    nitrificationRate: 0.5,
    denitrificationRate: 0.1,
    phosphorusAdsorption: 0.2,
    algaeGrowthRate: 1.5,
    algaeDeathRate: 0.3
  });

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px' }}>
          <Title level={2}>
            <ExperimentOutlined /> Water Quality Simulation / 水质模拟配置
          </Title>
          <Paragraph>
            Configure water quality parameters for DO, BOD, nutrients, and pollutants /
            配置溶解氧、生化需氧量、营养物质和污染物参数
          </Paragraph>
        </div>

        <Tabs defaultActiveKey="dobod" size="large">
          <TabPane
            tab={
              <span>
                <ExperimentOutlined />
                DO/BOD
              </span>
            }
            key="dobod"
          >
            <DOBODConfiguration
              config={dobodConfig}
              onChange={setDOBODConfig}
            />
          </TabPane>

          <TabPane
            tab={
              <span>
                <DashboardOutlined />
                Nutrients
              </span>
            }
            key="nutrients"
          >
            <NutrientConfiguration
              config={nutrientConfig}
              onChange={setNutrientConfig}
            />
          </TabPane>

          <TabPane
            tab={
              <span>
                <EnvironmentOutlined />
                Pollution Sources
              </span>
            }
            key="sources"
          >
            <Card title="Pollution Source Management / 污染源管理">
              <Button type="primary" icon={<PlusOutlined />} size="large">
                Add Pollution Source / 添加污染源
              </Button>
              <Paragraph style={{ marginTop: 16 }}>
                Configure point and non-point pollution sources /
                配置点源和面源污染
              </Paragraph>
            </Card>
          </TabPane>

          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                Monitoring
              </span>
            }
            key="monitoring"
          >
            <Card title="Water Quality Monitoring / 水质监控">
              <Paragraph>
                Real-time water quality visualization and alerts /
                实时水质可视化和警报
              </Paragraph>
            </Card>
          </TabPane>
        </Tabs>
      </Content>
    </Layout>
  );
};

export default WaterQualityPanel;


