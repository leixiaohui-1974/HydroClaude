/**
 * Hydraulic Structures Components - 水工结构组件库
 * 7种新增水工结构
 * 
 * Components:
 * 1. OverflowWeir - 溢流堰
 * 2. Orifice - 孔口
 * 3. VariableSpeedPump - 变速泵
 * 4. CheckValve - 止回阀
 * 5. PressureReliefValve - 泄压阀
 * 6. SurgeTank - 调压塔
 * 7. AirValve - 排气阀
 */

import React, { useState } from 'react';
import { Card, Form, InputNumber, Select, Switch, Slider, Space, Divider, Row, Col, Typography, Tooltip } from 'antd';
import {
  InfoCircleOutlined,
  SettingOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  BuildOutlined,
  DashboardOutlined
} from '@ant-design/icons';
import './HydraulicStructures.css';

const { Option } = Select;
const { Text, Title } = Typography;

// ============================================================================
// 1. Overflow Weir - 溢流堰
// ============================================================================

export interface OverflowWeirConfig {
  position: number;
  crestHeight: number;
  crestLength: number;
  dischargeCoefficient: number;
  weirType: 'sharp-crested' | 'broad-crested' | 'ogee';
  numberOfSpans: number;
  approach: 'free' | 'submerged';
}

export const OverflowWeirComponent: React.FC<{
  config: OverflowWeirConfig;
  onChange: (config: OverflowWeirConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof OverflowWeirConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <Card
      title={
        <Space>
          <BuildOutlined style={{ color: '#1890ff' }} />
          <span>Overflow Weir / 溢流堰</span>
        </Space>
      }
      extra={
        <Tooltip title="Weirs control flow by overflow, commonly used in irrigation, flood control, and flow measurement">
          <InfoCircleOutlined />
        </Tooltip>
      }
      className="structure-config-card"
    >
      <Form layout="vertical" size="small">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Position / 位置 (m)">
              <InputNumber
                value={config.position}
                onChange={(v) => handleChange('position', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Crest Height / 堰顶高程 (m)">
              <InputNumber
                value={config.crestHeight}
                onChange={(v) => handleChange('crestHeight', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Crest Length / 堰顶长度 (m)">
              <InputNumber
                value={config.crestLength}
                onChange={(v) => handleChange('crestLength', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={1}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Discharge Coefficient / 流量系数">
              <InputNumber
                value={config.dischargeCoefficient}
                onChange={(v) => handleChange('dischargeCoefficient', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={1}
                step={0.01}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Weir Type / 堰型">
              <Select
                value={config.weirType}
                onChange={(v) => handleChange('weirType', v)}
                style={{ width: '100%' }}
              >
                <Option value="sharp-crested">Sharp-Crested / 薄壁堰</Option>
                <Option value="broad-crested">Broad-Crested / 宽顶堰</Option>
                <Option value="ogee">Ogee / 溢流面型</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Number of Spans / 孔数">
              <InputNumber
                value={config.numberOfSpans}
                onChange={(v) => handleChange('numberOfSpans', v || 1)}
                style={{ width: '100%' }}
                min={1}
                step={1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Flow Approach / 流态">
          <Select
            value={config.approach}
            onChange={(v) => handleChange('approach', v)}
            style={{ width: '100%' }}
          >
            <Option value="free">Free Flow / 自由出流</Option>
            <Option value="submerged">Submerged / 淹没出流</Option>
          </Select>
        </Form.Item>

        <Divider />
        
        <div className="structure-info">
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <strong>Hydraulic Formula / 水力学公式:</strong><br />
            Q = C × L × H^(3/2)<br />
            Q: Discharge (m³/s) / 流量<br />
            C: Discharge coefficient / 流量系数<br />
            L: Crest length (m) / 堰顶长度<br />
            H: Head over weir (m) / 堰上水头
          </Text>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// 2. Orifice - 孔口
// ============================================================================

export interface OrificeConfig {
  position: number;
  diameter: number;
  centerElevation: number;
  dischargeCoefficient: number;
  shape: 'circular' | 'rectangular' | 'square';
  width?: number;
  height?: number;
  valveControl: boolean;
  openingPercentage: number;
}

export const OrificeComponent: React.FC<{
  config: OrificeConfig;
  onChange: (config: OrificeConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof OrificeConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <Card
      title={
        <Space>
          <DashboardOutlined style={{ color: '#52c41a' }} />
          <span>Orifice / 孔口</span>
        </Space>
      }
      extra={
        <Tooltip title="Orifices are openings in walls or plates, used for flow measurement and discharge control">
          <InfoCircleOutlined />
        </Tooltip>
      }
      className="structure-config-card"
    >
      <Form layout="vertical" size="small">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Position / 位置 (m)">
              <InputNumber
                value={config.position}
                onChange={(v) => handleChange('position', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Center Elevation / 中心高程 (m)">
              <InputNumber
                value={config.centerElevation}
                onChange={(v) => handleChange('centerElevation', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Shape / 形状">
          <Select
            value={config.shape}
            onChange={(v) => handleChange('shape', v)}
            style={{ width: '100%' }}
          >
            <Option value="circular">Circular / 圆形</Option>
            <Option value="rectangular">Rectangular / 矩形</Option>
            <Option value="square">Square / 方形</Option>
          </Select>
        </Form.Item>

        {config.shape === 'circular' && (
          <Form.Item label="Diameter / 直径 (m)">
            <InputNumber
              value={config.diameter}
              onChange={(v) => handleChange('diameter', v || 0)}
              style={{ width: '100%' }}
              min={0}
              step={0.1}
            />
          </Form.Item>
        )}

        {(config.shape === 'rectangular' || config.shape === 'square') && (
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="Width / 宽度 (m)">
                <InputNumber
                  value={config.width || 0}
                  onChange={(v) => handleChange('width', v || 0)}
                  style={{ width: '100%' }}
                  min={0}
                  step={0.1}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Height / 高度 (m)">
                <InputNumber
                  value={config.height || 0}
                  onChange={(v) => handleChange('height', v || 0)}
                  style={{ width: '100%' }}
                  min={0}
                  step={0.1}
                />
              </Form.Item>
            </Col>
          </Row>
        )}

        <Form.Item label="Discharge Coefficient / 流量系数">
          <Slider
            value={config.dischargeCoefficient}
            onChange={(v) => handleChange('dischargeCoefficient', v)}
            min={0}
            max={1}
            step={0.01}
            marks={{ 0: '0', 0.6: '0.6', 1: '1.0' }}
          />
        </Form.Item>

        <Form.Item label="Valve Control / 阀门控制">
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Switch
              checked={config.valveControl}
              onChange={(v) => handleChange('valveControl', v)}
              checkedChildren="ON"
              unCheckedChildren="OFF"
            />
            {config.valveControl && (
              <Text>Opening: {config.openingPercentage}%</Text>
            )}
          </Space>
        </Form.Item>

        {config.valveControl && (
          <Form.Item label="Opening Percentage / 开度 (%)">
            <Slider
              value={config.openingPercentage}
              onChange={(v) => handleChange('openingPercentage', v)}
              min={0}
              max={100}
              marks={{ 0: '0%', 50: '50%', 100: '100%' }}
            />
          </Form.Item>
        )}

        <Divider />
        
        <div className="structure-info">
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <strong>Hydraulic Formula / 水力学公式:</strong><br />
            Q = C × A × √(2gH)<br />
            Q: Discharge (m³/s) / 流量<br />
            C: Discharge coefficient / 流量系数<br />
            A: Orifice area (m²) / 孔口面积<br />
            H: Head (m) / 水头
          </Text>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// 3. Variable Speed Pump - 变速泵
// ============================================================================

export interface VariableSpeedPumpConfig {
  position: number;
  ratedFlow: number;
  ratedHead: number;
  ratedSpeed: number;
  currentSpeed: number;
  efficiency: number;
  power: number;
  controlMode: 'manual' | 'auto-flow' | 'auto-level';
  targetFlow?: number;
  targetLevel?: number;
  minSpeed: number;
  maxSpeed: number;
}

export const VariableSpeedPumpComponent: React.FC<{
  config: VariableSpeedPumpConfig;
  onChange: (config: VariableSpeedPumpConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof VariableSpeedPumpConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined style={{ color: '#faad14' }} />
          <span>Variable Speed Pump / 变速泵</span>
        </Space>
      }
      extra={
        <Tooltip title="Variable speed pumps allow flow adjustment by changing rotational speed, improving energy efficiency">
          <InfoCircleOutlined />
        </Tooltip>
      }
      className="structure-config-card"
    >
      <Form layout="vertical" size="small">
        <Form.Item label="Position / 位置 (m)">
          <InputNumber
            value={config.position}
            onChange={(v) => handleChange('position', v || 0)}
            style={{ width: '100%' }}
            min={0}
            step={10}
          />
        </Form.Item>

        <Divider orientation="left">Rated Parameters / 额定参数</Divider>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="Rated Flow / 额定流量 (m³/s)">
              <InputNumber
                value={config.ratedFlow}
                onChange={(v) => handleChange('ratedFlow', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.1}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="Rated Head / 额定扬程 (m)">
              <InputNumber
                value={config.ratedHead}
                onChange={(v) => handleChange('ratedHead', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={1}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="Rated Speed / 额定转速 (rpm)">
              <InputNumber
                value={config.ratedSpeed}
                onChange={(v) => handleChange('ratedSpeed', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={100}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Efficiency / 效率 (%)">
              <Slider
                value={config.efficiency}
                onChange={(v) => handleChange('efficiency', v)}
                min={0}
                max={100}
                marks={{ 0: '0%', 70: '70%', 90: '90%', 100: '100%' }}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Power / 功率 (kW)">
              <InputNumber
                value={config.power}
                onChange={(v) => handleChange('power', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Control Settings / 控制设置</Divider>

        <Form.Item label="Control Mode / 控制模式">
          <Select
            value={config.controlMode}
            onChange={(v) => handleChange('controlMode', v)}
            style={{ width: '100%' }}
          >
            <Option value="manual">Manual / 手动</Option>
            <Option value="auto-flow">Auto Flow Control / 自动流量控制</Option>
            <Option value="auto-level">Auto Level Control / 自动水位控制</Option>
          </Select>
        </Form.Item>

        <Form.Item label="Current Speed / 当前转速 (rpm)">
          <Slider
            value={config.currentSpeed}
            onChange={(v) => handleChange('currentSpeed', v)}
            min={config.minSpeed}
            max={config.maxSpeed}
            marks={{
              [config.minSpeed]: `${config.minSpeed}`,
              [config.ratedSpeed]: `${config.ratedSpeed}`,
              [config.maxSpeed]: `${config.maxSpeed}`
            }}
          />
        </Form.Item>

        {config.controlMode === 'auto-flow' && (
          <Form.Item label="Target Flow / 目标流量 (m³/s)">
            <InputNumber
              value={config.targetFlow || 0}
              onChange={(v) => handleChange('targetFlow', v || 0)}
              style={{ width: '100%' }}
              min={0}
              step={0.1}
            />
          </Form.Item>
        )}

        {config.controlMode === 'auto-level' && (
          <Form.Item label="Target Level / 目标水位 (m)">
            <InputNumber
              value={config.targetLevel || 0}
              onChange={(v) => handleChange('targetLevel', v || 0)}
              style={{ width: '100%' }}
              min={0}
              step={0.1}
            />
          </Form.Item>
        )}

        <Divider />
        
        <div className="structure-info">
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <strong>Affinity Laws / 相似律:</strong><br />
            Q₂/Q₁ = N₂/N₁<br />
            H₂/H₁ = (N₂/N₁)²<br />
            P₂/P₁ = (N₂/N₁)³<br />
            where N = speed (rpm) / 其中N = 转速
          </Text>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// 4. Check Valve - 止回阀
// ============================================================================

export interface CheckValveConfig {
  position: number;
  diameter: number;
  crackingPressure: number;
  fullOpenPressure: number;
  valveType: 'swing' | 'lift' | 'ball' | 'diaphragm';
  lossCoefficient: number;
  reverseLeakage: number;
}

export const CheckValveComponent: React.FC<{
  config: CheckValveConfig;
  onChange: (config: CheckValveConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof CheckValveConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <Card
      title={
        <Space>
          <SafetyOutlined style={{ color: '#eb2f96' }} />
          <span>Check Valve / 止回阀</span>
        </Space>
      }
      extra={
        <Tooltip title="Check valves allow flow in one direction only, preventing backflow and protecting equipment">
          <InfoCircleOutlined />
        </Tooltip>
      }
      className="structure-config-card"
    >
      <Form layout="vertical" size="small">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Position / 位置 (m)">
              <InputNumber
                value={config.position}
                onChange={(v) => handleChange('position', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Diameter / 直径 (m)">
              <InputNumber
                value={config.diameter}
                onChange={(v) => handleChange('diameter', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Valve Type / 阀门类型">
          <Select
            value={config.valveType}
            onChange={(v) => handleChange('valveType', v)}
            style={{ width: '100%' }}
          >
            <Option value="swing">Swing / 旋启式</Option>
            <Option value="lift">Lift / 升降式</Option>
            <Option value="ball">Ball / 球形</Option>
            <Option value="diaphragm">Diaphragm / 隔膜式</Option>
          </Select>
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Cracking Pressure / 开启压力 (kPa)">
              <InputNumber
                value={config.crackingPressure}
                onChange={(v) => handleChange('crackingPressure', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={1}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Full Open Pressure / 全开压力 (kPa)">
              <InputNumber
                value={config.fullOpenPressure}
                onChange={(v) => handleChange('fullOpenPressure', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={5}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Loss Coefficient / 损失系数">
          <Slider
            value={config.lossCoefficient}
            onChange={(v) => handleChange('lossCoefficient', v)}
            min={0}
            max={10}
            step={0.1}
            marks={{ 0: '0', 2: '2', 5: '5', 10: '10' }}
          />
        </Form.Item>

        <Form.Item label="Reverse Leakage / 反向泄漏率 (%)">
          <Slider
            value={config.reverseLeakage}
            onChange={(v) => handleChange('reverseLeakage', v)}
            min={0}
            max={5}
            step={0.1}
            marks={{ 0: '0%', 1: '1%', 3: '3%', 5: '5%' }}
          />
        </Form.Item>

        <Divider />
        
        <div className="structure-info">
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <strong>Operation / 工作原理:</strong><br />
            - Forward flow: Opens when ΔP {'>'} cracking pressure<br />
            - Reverse flow: Closes to prevent backflow<br />
            - Pressure loss: ΔP = K × (ρv²/2)<br />
            K: Loss coefficient / 损失系数
          </Text>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// 5. Pressure Relief Valve - 泄压阀
// ============================================================================

export interface PressureReliefValveConfig {
  position: number;
  diameter: number;
  setPressure: number;
  fullOpenPressure: number;
  releaseCapacity: number;
  valveType: 'spring-loaded' | 'pilot-operated' | 'balanced-bellows';
  responseTime: number;
  blowdownPressure: number;
}

export const PressureReliefValveComponent: React.FC<{
  config: PressureReliefValveConfig;
  onChange: (config: PressureReliefValveConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof PressureReliefValveConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <Card
      title={
        <Space>
          <ExperimentOutlined style={{ color: '#ff4d4f' }} />
          <span>Pressure Relief Valve / 泄压阀</span>
        </Space>
      }
      extra={
        <Tooltip title="Pressure relief valves protect systems from overpressure by automatically releasing fluid">
          <InfoCircleOutlined />
        </Tooltip>
      }
      className="structure-config-card"
    >
      <Form layout="vertical" size="small">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Position / 位置 (m)">
              <InputNumber
                value={config.position}
                onChange={(v) => handleChange('position', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Diameter / 直径 (m)">
              <InputNumber
                value={config.diameter}
                onChange={(v) => handleChange('diameter', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.05}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Valve Type / 阀门类型">
          <Select
            value={config.valveType}
            onChange={(v) => handleChange('valveType', v)}
            style={{ width: '100%' }}
          >
            <Option value="spring-loaded">Spring-Loaded / 弹簧式</Option>
            <Option value="pilot-operated">Pilot-Operated / 先导式</Option>
            <Option value="balanced-bellows">Balanced-Bellows / 平衡波纹管式</Option>
          </Select>
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Set Pressure / 设定压力 (kPa)">
              <InputNumber
                value={config.setPressure}
                onChange={(v) => handleChange('setPressure', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Full Open Pressure / 全开压力 (kPa)">
              <InputNumber
                value={config.fullOpenPressure}
                onChange={(v) => handleChange('fullOpenPressure', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Release Capacity / 泄放能力 (m³/s)">
              <InputNumber
                value={config.releaseCapacity}
                onChange={(v) => handleChange('releaseCapacity', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.1}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Response Time / 响应时间 (ms)">
              <InputNumber
                value={config.responseTime}
                onChange={(v) => handleChange('responseTime', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Blowdown Pressure / 回座压力 (kPa)">
          <InputNumber
            value={config.blowdownPressure}
            onChange={(v) => handleChange('blowdownPressure', v || 0)}
            style={{ width: '100%' }}
            min={0}
            step={5}
            addonAfter={`${((config.setPressure - config.blowdownPressure) / config.setPressure * 100).toFixed(1)}% below set`}
          />
        </Form.Item>

        <Divider />
        
        <div className="structure-info">
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <strong>Safety Parameters / 安全参数:</strong><br />
            - Opens at: {config.setPressure} kPa<br />
            - Fully open at: {config.fullOpenPressure} kPa<br />
            - Closes at: {config.blowdownPressure} kPa<br />
            - Blowdown: {((config.setPressure - config.blowdownPressure) / config.setPressure * 100).toFixed(1)}%
          </Text>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// 6. Surge Tank - 调压塔
// ============================================================================

export interface SurgeTankConfig {
  position: number;
  diameter: number;
  height: number;
  bottomElevation: number;
  initialWaterLevel: number;
  orificeArea: number;
  tankType: 'simple' | 'differential' | 'restricted-orifice';
  throttleCoefficient?: number;
}

export const SurgeTankComponent: React.FC<{
  config: SurgeTankConfig;
  onChange: (config: SurgeTankConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof SurgeTankConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const tankVolume = Math.PI * Math.pow(config.diameter / 2, 2) * config.height;
  const waterVolume = Math.PI * Math.pow(config.diameter / 2, 2) * config.initialWaterLevel;

  return (
    <Card
      title={
        <Space>
          <SettingOutlined style={{ color: '#13c2c2' }} />
          <span>Surge Tank / 调压塔</span>
        </Space>
      }
      extra={
        <Tooltip title="Surge tanks protect pipelines from pressure surges by providing a free water surface">
          <InfoCircleOutlined />
        </Tooltip>
      }
      className="structure-config-card"
    >
      <Form layout="vertical" size="small">
        <Form.Item label="Position / 位置 (m)">
          <InputNumber
            value={config.position}
            onChange={(v) => handleChange('position', v || 0)}
            style={{ width: '100%' }}
            min={0}
            step={10}
          />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Diameter / 直径 (m)">
              <InputNumber
                value={config.diameter}
                onChange={(v) => handleChange('diameter', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.5}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Height / 高度 (m)">
              <InputNumber
                value={config.height}
                onChange={(v) => handleChange('height', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Bottom Elevation / 底部高程 (m)">
              <InputNumber
                value={config.bottomElevation}
                onChange={(v) => handleChange('bottomElevation', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={1}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Initial Water Level / 初始水位 (m)">
              <InputNumber
                value={config.initialWaterLevel}
                onChange={(v) => handleChange('initialWaterLevel', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={config.height}
                step={0.5}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Tank Type / 水塔类型">
          <Select
            value={config.tankType}
            onChange={(v) => handleChange('tankType', v)}
            style={{ width: '100%' }}
          >
            <Option value="simple">Simple / 简单型</Option>
            <Option value="differential">Differential / 差动型</Option>
            <Option value="restricted-orifice">Restricted Orifice / 阻抗孔型</Option>
          </Select>
        </Form.Item>

        {config.tankType === 'restricted-orifice' && (
          <>
            <Form.Item label="Orifice Area / 孔口面积 (m²)">
              <InputNumber
                value={config.orificeArea}
                onChange={(v) => handleChange('orificeArea', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.1}
              />
            </Form.Item>
            <Form.Item label="Throttle Coefficient / 节流系数">
              <Slider
                value={config.throttleCoefficient || 0.6}
                onChange={(v) => handleChange('throttleCoefficient', v)}
                min={0}
                max={1}
                step={0.01}
                marks={{ 0: '0', 0.6: '0.6', 0.8: '0.8', 1: '1.0' }}
              />
            </Form.Item>
          </>
        )}

        <Divider />
        
        <div className="structure-info">
          <Row gutter={16}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                <strong>Tank Volume / 水塔容积:</strong><br />
                {tankVolume.toFixed(2)} m³
              </Text>
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                <strong>Water Volume / 水量:</strong><br />
                {waterVolume.toFixed(2)} m³ ({(waterVolume / tankVolume * 100).toFixed(1)}%)
              </Text>
            </Col>
          </Row>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// 7. Air Valve - 排气阀
// ============================================================================

export interface AirValveConfig {
  position: number;
  diameter: number;
  valveType: 'air-release' | 'air-vacuum' | 'combination';
  inletDiameter: number;
  outletDiameter: number;
  openingPressure: number;
  closingPressure: number;
  flowCoefficient: number;
}

export const AirValveComponent: React.FC<{
  config: AirValveConfig;
  onChange: (config: AirValveConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof AirValveConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <Card
      title={
        <Space>
          <ExperimentOutlined style={{ color: '#722ed1' }} />
          <span>Air Valve / 排气阀</span>
        </Space>
      }
      extra={
        <Tooltip title="Air valves release accumulated air and admit air during filling/draining to prevent vacuum">
          <InfoCircleOutlined />
        </Tooltip>
      }
      className="structure-config-card"
    >
      <Form layout="vertical" size="small">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Position / 位置 (m)">
              <InputNumber
                value={config.position}
                onChange={(v) => handleChange('position', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={10}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Body Diameter / 阀体直径 (mm)">
              <InputNumber
                value={config.diameter}
                onChange={(v) => handleChange('diameter', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={5}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Valve Type / 阀门类型">
          <Select
            value={config.valveType}
            onChange={(v) => handleChange('valveType', v)}
            style={{ width: '100%' }}
          >
            <Option value="air-release">Air Release / 排气阀</Option>
            <Option value="air-vacuum">Air-Vacuum / 进排气阀</Option>
            <Option value="combination">Combination / 组合式</Option>
          </Select>
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Inlet Diameter / 进口直径 (mm)">
              <InputNumber
                value={config.inletDiameter}
                onChange={(v) => handleChange('inletDiameter', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={5}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Outlet Diameter / 出口直径 (mm)">
              <InputNumber
                value={config.outletDiameter}
                onChange={(v) => handleChange('outletDiameter', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={5}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="Opening Pressure / 开启压力 (kPa)">
              <InputNumber
                value={config.openingPressure}
                onChange={(v) => handleChange('openingPressure', v || 0)}
                style={{ width: '100%' }}
                min={-100}
                max={100}
                step={1}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Closing Pressure / 关闭压力 (kPa)">
              <InputNumber
                value={config.closingPressure}
                onChange={(v) => handleChange('closingPressure', v || 0)}
                style={{ width: '100%' }}
                min={-100}
                max={100}
                step={1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="Flow Coefficient / 流量系数">
          <Slider
            value={config.flowCoefficient}
            onChange={(v) => handleChange('flowCoefficient', v)}
            min={0}
            max={1}
            step={0.01}
            marks={{ 0: '0', 0.5: '0.5', 0.7: '0.7', 1: '1.0' }}
          />
        </Form.Item>

        <Divider />
        
        <div className="structure-info">
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <strong>Functions / 功能:</strong><br />
            {config.valveType === 'air-release' && '- Release accumulated air during operation / 运行时排除积聚空气'}
            {config.valveType === 'air-vacuum' && '- Release air during filling, admit air during draining / 充水排气、放空进气'}
            {config.valveType === 'combination' && '- Both air release and air-vacuum functions / 排气和进排气双重功能'}<br />
            - Prevents air pockets and vacuum conditions / 防止气囊和真空
          </Text>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// Export all components
// ============================================================================

export default {
  OverflowWeirComponent,
  OrificeComponent,
  VariableSpeedPumpComponent,
  CheckValveComponent,
  PressureReliefValveComponent,
  SurgeTankComponent,
  AirValveComponent
};


