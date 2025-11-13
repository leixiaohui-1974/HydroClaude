/**
 * Control System Panel - 控制系统面板
 * PID和MPC控制器的完整配置和调优界面
 * 
 * Features:
 * - PID Controller Configuration (PID控制器配置)
 * - MPC Controller Configuration (MPC控制器配置)
 * - Auto-tuning Tools (自动调优工具)
 * - Performance Visualization (性能可视化)
 * - Real-time Monitoring (实时监控)
 * - Controller Comparison (控制器对比)
 */

import React, { useState, useEffect } from 'react';
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
  Statistic,
  Typography,
  Badge,
  Tag,
  Table,
  Progress,
  Tooltip,
  message,
  Modal
} from 'antd';
import {
  ControlOutlined,
  RocketOutlined,
  LineChartOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { Line } from 'react-chartjs-2';
import './ControlSystemPanel.css';

const { Content, Sider } = Layout;
const { TabPane } = Tabs;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ============================================================================
// PID Controller Configuration
// ============================================================================

interface PIDConfig {
  Kp: number;
  Ki: number;
  Kd: number;
  setpoint: number;
  outputMin: number;
  outputMax: number;
  sampleTime: number;
  integralWindup: boolean;
  integralMax?: number;
  derivativeFilter: boolean;
  filterConstant?: number;
  mode: 'manual' | 'automatic';
}

const PIDControllerConfig: React.FC<{
  config: PIDConfig;
  onChange: (config: PIDConfig) => void;
  onAutoTune: () => void;
  tuning: boolean;
}> = ({ config, onChange, onAutoTune, tuning }) => {
  const handleChange = (field: keyof PIDConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const getStabilityInfo = () => {
    const { Kp, Ki, Kd } = config;
    
    if (Kp > 10 || Ki > 5 || Kd > 2) {
      return {
        status: 'warning',
        message: 'High gains may cause oscillation / 高增益可能导致振荡'
      };
    }
    
    if (Ki > 0 && !config.integralWindup) {
      return {
        status: 'info',
        message: 'Consider enabling integral windup protection / 建议启用积分饱和保护'
      };
    }
    
    return {
      status: 'success',
      message: 'Parameters look stable / 参数看起来稳定'
    };
  };

  const stability = getStabilityInfo();

  return (
    <Card
      title={
        <Space>
          <ControlOutlined style={{ color: '#1890ff' }} />
          <span>PID Controller Configuration / PID控制器配置</span>
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={tuning ? <SyncOutlined spin /> : <ThunderboltOutlined />}
          onClick={onAutoTune}
          loading={tuning}
        >
          Auto-Tune / 自动调优
        </Button>
      }
    >
      <Alert
        message={stability.message}
        type={stability.status as any}
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Form layout="vertical">
        <Divider orientation="left">PID Gains / PID增益</Divider>
        
        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label={
              <span>
                Proportional Gain (Kp) / 比例增益
                <Tooltip title="Controls reaction to current error. Higher values = faster response but may overshoot.">
                  <WarningOutlined style={{ marginLeft: 8, color: '#faad14' }} />
                </Tooltip>
              </span>
            }>
              <InputNumber
                value={config.Kp}
                onChange={(v) => handleChange('Kp', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={100}
                step={0.1}
                precision={2}
              />
              <Slider
                value={config.Kp}
                onChange={(v) => handleChange('Kp', v)}
                min={0}
                max={20}
                step={0.1}
                marks={{ 0: '0', 5: '5', 10: '10', 20: '20' }}
                style={{ marginTop: 8 }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label={
              <span>
                Integral Gain (Ki) / 积分增益
                <Tooltip title="Eliminates steady-state error. Higher values = faster error elimination but may cause windup.">
                  <WarningOutlined style={{ marginLeft: 8, color: '#faad14' }} />
                </Tooltip>
              </span>
            }>
              <InputNumber
                value={config.Ki}
                onChange={(v) => handleChange('Ki', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={50}
                step={0.01}
                precision={3}
              />
              <Slider
                value={config.Ki}
                onChange={(v) => handleChange('Ki', v)}
                min={0}
                max={10}
                step={0.01}
                marks={{ 0: '0', 2: '2', 5: '5', 10: '10' }}
                style={{ marginTop: 8 }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label={
              <span>
                Derivative Gain (Kd) / 微分增益
                <Tooltip title="Dampens oscillation by predicting future error. Higher values = more damping but sensitive to noise.">
                  <WarningOutlined style={{ marginLeft: 8, color: '#faad14' }} />
                </Tooltip>
              </span>
            }>
              <InputNumber
                value={config.Kd}
                onChange={(v) => handleChange('Kd', v || 0)}
                style={{ width: '100%' }}
                min={0}
                max={10}
                step={0.01}
                precision={3}
              />
              <Slider
                value={config.Kd}
                onChange={(v) => handleChange('Kd', v)}
                min={0}
                max={5}
                step={0.01}
                marks={{ 0: '0', 1: '1', 2: '2', 5: '5' }}
                style={{ marginTop: 8 }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Setpoint & Limits / 设定点与限制</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label="Setpoint / 设定点 (m)">
              <InputNumber
                value={config.setpoint}
                onChange={(v) => handleChange('setpoint', v || 0)}
                style={{ width: '100%' }}
                min={0}
                step={0.1}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Output Min / 输出最小值">
              <InputNumber
                value={config.outputMin}
                onChange={(v) => handleChange('outputMin', v || 0)}
                style={{ width: '100%' }}
                step={0.1}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Output Max / 输出最大值">
              <InputNumber
                value={config.outputMax}
                onChange={(v) => handleChange('outputMax', v || 0)}
                style={{ width: '100%' }}
                step={0.1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Advanced Settings / 高级设置</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label="Sample Time / 采样时间 (s)">
              <InputNumber
                value={config.sampleTime}
                onChange={(v) => handleChange('sampleTime', v || 0.1)}
                style={{ width: '100%' }}
                min={0.01}
                max={10}
                step={0.01}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Integral Windup Protection / 积分饱和保护">
              <Switch
                checked={config.integralWindup}
                onChange={(v) => handleChange('integralWindup', v)}
                checkedChildren="ON"
                unCheckedChildren="OFF"
              />
              {config.integralWindup && (
                <InputNumber
                  value={config.integralMax || 100}
                  onChange={(v) => handleChange('integralMax', v)}
                  style={{ width: '100%', marginTop: 8 }}
                  placeholder="Max integral value"
                  min={0}
                />
              )}
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Derivative Filter / 微分滤波">
              <Switch
                checked={config.derivativeFilter}
                onChange={(v) => handleChange('derivativeFilter', v)}
                checkedChildren="ON"
                unCheckedChildren="OFF"
              />
              {config.derivativeFilter && (
                <InputNumber
                  value={config.filterConstant || 0.1}
                  onChange={(v) => handleChange('filterConstant', v)}
                  style={{ width: '100%', marginTop: 8 }}
                  placeholder="Filter constant"
                  min={0}
                  max={1}
                  step={0.01}
                />
              )}
            </Form.Item>
          </Col>
        </Row>

        <Divider />

        <div className="control-info-panel">
          <Title level={5}>PID Control Equation / PID控制方程</Title>
          <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', fontFamily: 'monospace' }}>
            <Text>u(t) = Kp·e(t) + Ki·∫e(τ)dτ + Kd·de(t)/dt</Text>
            <br />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              where e(t) = setpoint - measurement / 其中e(t) = 设定值 - 测量值
            </Text>
          </div>
          
          <Paragraph style={{ marginTop: 16, fontSize: '12px', color: '#666' }}>
            <strong>Tuning Guidelines / 调优指南:</strong><br />
            • Start with Kp only, increase until system oscillates / 先只用Kp，增加直到系统振荡<br />
            • Add Ki to eliminate steady-state error / 添加Ki消除稳态误差<br />
            • Add Kd to reduce overshoot and oscillation / 添加Kd减少超调和振荡<br />
            • Use Ziegler-Nichols method for initial tuning / 使用Ziegler-Nichols方法初调
          </Paragraph>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// MPC Controller Configuration
// ============================================================================

interface MPCConfig {
  predictionHorizon: number;
  controlHorizon: number;
  sampleTime: number;
  weightOutput: number;
  weightControl: number;
  constraintsEnabled: boolean;
  outputMin?: number;
  outputMax?: number;
  rateMin?: number;
  rateMax?: number;
  modelType: 'linear' | 'nonlinear' | 'adaptive';
  solver: 'qp' | 'nlp' | 'milp';
  maxIterations: number;
  tolerance: number;
}

const MPCControllerConfig: React.FC<{
  config: MPCConfig;
  onChange: (config: MPCConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof MPCConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const getPerformanceEstimate = () => {
    const computationalLoad = 
      config.predictionHorizon * config.controlHorizon * 
      (config.modelType === 'nonlinear' ? 10 : 1);
    
    if (computationalLoad > 1000) return { level: 'high', color: '#ff4d4f' };
    if (computationalLoad > 500) return { level: 'medium', color: '#faad14' };
    return { level: 'low', color: '#52c41a' };
  };

  const performance = getPerformanceEstimate();

  return (
    <Card
      title={
        <Space>
          <RocketOutlined style={{ color: '#722ed1' }} />
          <span>MPC Controller Configuration / MPC控制器配置</span>
        </Space>
      }
      extra={
        <Tag color={performance.color}>
          Computational Load: {performance.level.toUpperCase()}
        </Tag>
      }
    >
      <Alert
        message="Model Predictive Control uses optimization to compute optimal control actions"
        description="模型预测控制使用优化算法计算最优控制动作"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Form layout="vertical">
        <Divider orientation="left">Horizons / 预测与控制时域</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label={
              <span>
                Prediction Horizon (Np) / 预测时域
                <Tooltip title="Number of future time steps to predict. Longer horizon = better control but higher computation.">
                  <WarningOutlined style={{ marginLeft: 8, color: '#faad14' }} />
                </Tooltip>
              </span>
            }>
              <InputNumber
                value={config.predictionHorizon}
                onChange={(v) => handleChange('predictionHorizon', v || 10)}
                style={{ width: '100%' }}
                min={1}
                max={100}
                step={1}
              />
              <Slider
                value={config.predictionHorizon}
                onChange={(v) => handleChange('predictionHorizon', v)}
                min={5}
                max={50}
                marks={{ 5: '5', 20: '20', 50: '50' }}
                style={{ marginTop: 8 }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label={
              <span>
                Control Horizon (Nc) / 控制时域
                <Tooltip title="Number of future control moves to optimize. Should be ≤ Np.">
                  <WarningOutlined style={{ marginLeft: 8, color: '#faad14' }} />
                </Tooltip>
              </span>
            }>
              <InputNumber
                value={config.controlHorizon}
                onChange={(v) => handleChange('controlHorizon', v || 5)}
                style={{ width: '100%' }}
                min={1}
                max={config.predictionHorizon}
                step={1}
              />
              <Slider
                value={config.controlHorizon}
                onChange={(v) => handleChange('controlHorizon', v)}
                min={1}
                max={Math.min(config.predictionHorizon, 30)}
                marks={{ 1: '1', 10: '10', 20: '20' }}
                style={{ marginTop: 8 }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Sample Time / 采样时间 (s)">
              <InputNumber
                value={config.sampleTime}
                onChange={(v) => handleChange('sampleTime', v || 1)}
                style={{ width: '100%' }}
                min={0.1}
                max={60}
                step={0.1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Weighting / 权重</Divider>

        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="Output Tracking Weight / 输出跟踪权重 (Q)">
              <Paragraph style={{ fontSize: '12px', color: '#666', marginBottom: 8 }}>
                Higher weight = prioritize tracking setpoint / 更高权重 = 优先跟踪设定值
              </Paragraph>
              <Slider
                value={config.weightOutput}
                onChange={(v) => handleChange('weightOutput', v)}
                min={0}
                max={100}
                marks={{ 0: '0', 10: '10', 50: '50', 100: '100' }}
              />
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item label="Control Effort Weight / 控制努力权重 (R)">
              <Paragraph style={{ fontSize: '12px', color: '#666', marginBottom: 8 }}>
                Higher weight = smoother control actions / 更高权重 = 更平滑控制
              </Paragraph>
              <Slider
                value={config.weightControl}
                onChange={(v) => handleChange('weightControl', v)}
                min={0}
                max={100}
                marks={{ 0: '0', 10: '10', 50: '50', 100: '100' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Constraints / 约束</Divider>

        <Form.Item label="Enable Constraints / 启用约束">
          <Switch
            checked={config.constraintsEnabled}
            onChange={(v) => handleChange('constraintsEnabled', v)}
            checkedChildren="ON"
            unCheckedChildren="OFF"
          />
        </Form.Item>

        {config.constraintsEnabled && (
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item label="Output Constraints / 输出约束">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <InputNumber
                    value={config.outputMin}
                    onChange={(v) => handleChange('outputMin', v)}
                    style={{ width: '100%' }}
                    placeholder="Min output"
                    addonBefore="Min"
                  />
                  <InputNumber
                    value={config.outputMax}
                    onChange={(v) => handleChange('outputMax', v)}
                    style={{ width: '100%' }}
                    placeholder="Max output"
                    addonBefore="Max"
                  />
                </Space>
              </Form.Item>
            </Col>

            <Col span={12}>
              <Form.Item label="Rate Constraints / 速率约束">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <InputNumber
                    value={config.rateMin}
                    onChange={(v) => handleChange('rateMin', v)}
                    style={{ width: '100%' }}
                    placeholder="Min rate"
                    addonBefore="Min"
                  />
                  <InputNumber
                    value={config.rateMax}
                    onChange={(v) => handleChange('rateMax', v)}
                    style={{ width: '100%' }}
                    placeholder="Max rate"
                    addonBefore="Max"
                  />
                </Space>
              </Form.Item>
            </Col>
          </Row>
        )}

        <Divider orientation="left">Model & Solver / 模型与求解器</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label="Model Type / 模型类型">
              <Select
                value={config.modelType}
                onChange={(v) => handleChange('modelType', v)}
                style={{ width: '100%' }}
              >
                <Option value="linear">Linear / 线性</Option>
                <Option value="nonlinear">Nonlinear / 非线性</Option>
                <Option value="adaptive">Adaptive / 自适应</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Solver / 求解器">
              <Select
                value={config.solver}
                onChange={(v) => handleChange('solver', v)}
                style={{ width: '100%' }}
              >
                <Option value="qp">QP (Quadratic Programming)</Option>
                <Option value="nlp">NLP (Nonlinear Programming)</Option>
                <Option value="milp">MILP (Mixed-Integer Linear)</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Max Iterations / 最大迭代次数">
              <InputNumber
                value={config.maxIterations}
                onChange={(v) => handleChange('maxIterations', v || 100)}
                style={{ width: '100%' }}
                min={10}
                max={1000}
                step={10}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="Convergence Tolerance / 收敛容差">
              <InputNumber
                value={config.tolerance}
                onChange={(v) => handleChange('tolerance', v || 1e-6)}
                style={{ width: '100%' }}
                min={1e-10}
                max={1e-2}
                step={1e-7}
                precision={10}
              />
            </Form.Item>
          </Col>
        </Row>

        <Divider />

        <div className="control-info-panel">
          <Title level={5}>MPC Optimization Problem / MPC优化问题</Title>
          <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', fontFamily: 'monospace' }}>
            <Text>
              min J = Σ[Q·(y - r)² + R·Δu²]<br />
              subject to:<br />
              &nbsp;&nbsp;y(k+1) = f(y(k), u(k))<br />
              &nbsp;&nbsp;u_min ≤ u ≤ u_max<br />
              &nbsp;&nbsp;Δu_min ≤ Δu ≤ Δu_max
            </Text>
          </div>
          
          <Paragraph style={{ marginTop: 16, fontSize: '12px', color: '#666' }}>
            <strong>MPC Advantages / MPC优势:</strong><br />
            • Handles constraints explicitly / 显式处理约束<br />
            • Optimizes future behavior / 优化未来行为<br />
            • Works with MIMO systems / 适用于多输入多输出系统<br />
            • Provides predictive control / 提供预测性控制
          </Paragraph>
        </div>
      </Form>
    </Card>
  );
};

// ============================================================================
// Performance Visualization
// ============================================================================

const PerformanceVisualization: React.FC<{
  data: {
    time: number[];
    setpoint: number[];
    output: number[];
    control: number[];
  };
  metrics: {
    riseTime: number;
    settlingTime: number;
    overshoot: number;
    steadyStateError: number;
    iae: number;
    ise: number;
  };
}> = ({ data, metrics }) => {
  const chartData = {
    labels: data.time.map(t => t.toFixed(1)),
    datasets: [
      {
        label: 'Setpoint / 设定值',
        data: data.setpoint,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.1)',
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 0
      },
      {
        label: 'Output / 输出',
        data: data.output,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.1)',
        borderWidth: 2,
        pointRadius: 0
      },
      {
        label: 'Control Signal / 控制信号',
        data: data.control,
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        borderWidth: 2,
        pointRadius: 0,
        yAxisID: 'y1'
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Output / 输出'
        }
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        title: {
          display: true,
          text: 'Control Signal / 控制信号'
        },
        grid: {
          drawOnChartArea: false
        }
      }
    }
  };

  return (
    <Card title="Performance Visualization / 性能可视化">
      <div style={{ height: '400px', marginBottom: '24px' }}>
        <Line data={chartData} options={options} />
      </div>

      <Row gutter={16}>
        <Col span={6}>
          <Statistic
            title="Rise Time / 上升时间"
            value={metrics.riseTime}
            suffix="s"
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Settling Time / 稳定时间"
            value={metrics.settlingTime}
            suffix="s"
            valueStyle={{ color: '#1890ff' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Overshoot / 超调"
            value={metrics.overshoot}
            suffix="%"
            valueStyle={{ color: metrics.overshoot > 10 ? '#cf1322' : '#3f8600' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Steady-State Error / 稳态误差"
            value={metrics.steadyStateError}
            precision={3}
            valueStyle={{ color: Math.abs(metrics.steadyStateError) > 0.1 ? '#cf1322' : '#3f8600' }}
          />
        </Col>
      </Row>

      <Divider />

      <Row gutter={16}>
        <Col span={12}>
          <Card size="small" title="IAE (Integral Absolute Error)">
            <Progress
              percent={Math.min(metrics.iae / 10 * 100, 100)}
              status={metrics.iae < 5 ? 'success' : 'exception'}
              format={() => metrics.iae.toFixed(2)}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="ISE (Integral Square Error)">
            <Progress
              percent={Math.min(metrics.ise / 10 * 100, 100)}
              status={metrics.ise < 5 ? 'success' : 'exception'}
              format={() => metrics.ise.toFixed(2)}
            />
          </Card>
        </Col>
      </Row>
    </Card>
  );
};

// ============================================================================
// Main Control System Panel
// ============================================================================

const ControlSystemPanel: React.FC = () => {
  const [pidConfig, setPidConfig] = useState<PIDConfig>({
    Kp: 1.0,
    Ki: 0.1,
    Kd: 0.05,
    setpoint: 5.0,
    outputMin: 0,
    outputMax: 100,
    sampleTime: 0.1,
    integralWindup: true,
    integralMax: 100,
    derivativeFilter: true,
    filterConstant: 0.1,
    mode: 'automatic'
  });

  const [mpcConfig, setMPCConfig] = useState<MPCConfig>({
    predictionHorizon: 20,
    controlHorizon: 5,
    sampleTime: 1.0,
    weightOutput: 10,
    weightControl: 1,
    constraintsEnabled: true,
    outputMin: 0,
    outputMax: 100,
    rateMin: -10,
    rateMax: 10,
    modelType: 'linear',
    solver: 'qp',
    maxIterations: 100,
    tolerance: 1e-6
  });

  const [tuning, setTuning] = useState(false);
  const [simulating, setSimulating] = useState(false);

  // Mock performance data
  const mockPerformanceData = {
    time: Array.from({ length: 100 }, (_, i) => i * 0.1),
    setpoint: Array.from({ length: 100 }, () => 5.0),
    output: Array.from({ length: 100 }, (_, i) => 
      5.0 * (1 - Math.exp(-i * 0.05)) + Math.sin(i * 0.3) * 0.2
    ),
    control: Array.from({ length: 100 }, (_, i) => 
      50 + Math.cos(i * 0.2) * 20
    )
  };

  const mockMetrics = {
    riseTime: 2.5,
    settlingTime: 8.2,
    overshoot: 5.3,
    steadyStateError: 0.02,
    iae: 2.8,
    ise: 1.5
  };

  const handleAutoTune = () => {
    setTuning(true);
    message.info('Starting auto-tune procedure... / 开始自动调优...');
    
    setTimeout(() => {
      setPidConfig({
        ...pidConfig,
        Kp: 2.5,
        Ki: 0.3,
        Kd: 0.15
      });
      setTuning(false);
      message.success('Auto-tune complete! / 自动调优完成！');
    }, 3000);
  };

  const handleSimulate = () => {
    setSimulating(true);
    message.loading('Running simulation... / 运行仿真...', 0);
    
    setTimeout(() => {
      message.destroy();
      setSimulating(false);
      message.success('Simulation complete! / 仿真完成！');
    }, 2000);
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px' }}>
          <Title level={2}>
            <ControlOutlined /> Control System Configuration / 控制系统配置
          </Title>
          <Paragraph>
            Configure and tune PID and MPC controllers for optimal performance /
            配置和调优PID和MPC控制器以获得最佳性能
          </Paragraph>
        </div>

        <Tabs defaultActiveKey="pid" size="large">
          <TabPane
            tab={
              <span>
                <ControlOutlined />
                PID Controller
              </span>
            }
            key="pid"
          >
            <PIDControllerConfig
              config={pidConfig}
              onChange={setPidConfig}
              onAutoTune={handleAutoTune}
              tuning={tuning}
            />
          </TabPane>

          <TabPane
            tab={
              <span>
                <RocketOutlined />
                MPC Controller
              </span>
            }
            key="mpc"
          >
            <MPCControllerConfig
              config={mpcConfig}
              onChange={setMPCConfig}
            />
          </TabPane>

          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                Performance
              </span>
            }
            key="performance"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <Card>
                <Space>
                  <Button
                    type="primary"
                    size="large"
                    icon={simulating ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                    onClick={handleSimulate}
                    loading={simulating}
                  >
                    {simulating ? 'Stop' : 'Run Simulation'} / {simulating ? '停止' : '运行仿真'}
                  </Button>
                  <Button icon={<ExperimentOutlined />} size="large">
                    Compare Controllers / 对比控制器
                  </Button>
                </Space>
              </Card>

              <PerformanceVisualization
                data={mockPerformanceData}
                metrics={mockMetrics}
              />
            </Space>
          </TabPane>
        </Tabs>
      </Content>
    </Layout>
  );
};

export default ControlSystemPanel;


