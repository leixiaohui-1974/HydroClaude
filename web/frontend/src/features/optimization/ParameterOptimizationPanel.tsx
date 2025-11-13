/**
 * Parameter Optimization Panel - 参数优化面板
 * 完整的参数校准和优化界面
 * 
 * Features:
 * - Sensitivity Analysis (敏感性分析)
 * - Auto-Calibration (自动校准)
 * - Uncertainty Analysis (不确定性分析)
 * - Multi-Objective Optimization (多目标优化)
 * - Optimization History (优化历史)
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
  List,
  Spin,
  Radio,
  Checkbox,
  Timeline,
  Result
} from 'antd';
import {
  ExperimentOutlined,
  RocketOutlined,
  LineChartOutlined,
  FireOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  BulbOutlined,
  AimOutlined
} from '@ant-design/icons';
import { Line, Scatter, Radar } from 'react-chartjs-2';
import './ParameterOptimizationPanel.css';

const { Content } = Layout;
const { TabPane } = Tabs;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ============================================================================
// Types and Interfaces
// ============================================================================

interface OptimizationParameter {
  name: string;
  displayName: string;
  currentValue: number;
  minValue: number;
  maxValue: number;
  unit: string;
  sensitivity: number;
  enabled: boolean;
}

interface OptimizationResult {
  iteration: number;
  parameters: { [key: string]: number };
  objectiveValue: number;
  constraints: { [key: string]: boolean };
  timestamp: string;
}

interface SensitivityResult {
  parameter: string;
  sensitivity: number;
  impact: 'High' | 'Medium' | 'Low';
}

// ============================================================================
// Parameter Selection Component
// ============================================================================

const ParameterSelection: React.FC<{
  parameters: OptimizationParameter[];
  onChange: (parameters: OptimizationParameter[]) => void;
}> = ({ parameters, onChange }) => {
  const handleParameterChange = (index: number, field: keyof OptimizationParameter, value: any) => {
    const updated = [...parameters];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  const columns = [
    {
      title: 'Parameter / 参数',
      dataIndex: 'displayName',
      key: 'displayName',
      render: (text: string, record: OptimizationParameter) => (
        <Space>
          <Checkbox
            checked={record.enabled}
            onChange={(e) => {
              const index = parameters.findIndex(p => p.name === record.name);
              handleParameterChange(index, 'enabled', e.target.checked);
            }}
          />
          <Text strong>{text}</Text>
        </Space>
      )
    },
    {
      title: 'Current / 当前值',
      dataIndex: 'currentValue',
      key: 'currentValue',
      render: (value: number, record: OptimizationParameter) => (
        <Text>{value.toFixed(3)} {record.unit}</Text>
      )
    },
    {
      title: 'Range / 范围',
      key: 'range',
      render: (_: any, record: OptimizationParameter) => (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <InputNumber
              size="small"
              value={record.minValue}
              onChange={(v) => {
                const index = parameters.findIndex(p => p.name === record.name);
                handleParameterChange(index, 'minValue', v || 0);
              }}
              style={{ width: 80 }}
            />
            <Text type="secondary">to</Text>
            <InputNumber
              size="small"
              value={record.maxValue}
              onChange={(v) => {
                const index = parameters.findIndex(p => p.name === record.name);
                handleParameterChange(index, 'maxValue', v || 0);
              }}
              style={{ width: 80 }}
            />
          </Space>
          <Slider
            range
            value={[record.minValue, record.maxValue]}
            min={0}
            max={record.maxValue * 2}
            step={0.001}
            onChange={(v) => {
              const index = parameters.findIndex(p => p.name === record.name);
              handleParameterChange(index, 'minValue', v[0]);
              handleParameterChange(index, 'maxValue', v[1]);
            }}
          />
        </Space>
      )
    },
    {
      title: 'Sensitivity / 敏感性',
      dataIndex: 'sensitivity',
      key: 'sensitivity',
      render: (value: number) => {
        let color = 'green';
        let text = 'Low';
        if (value > 0.7) { color = 'red'; text = 'High'; }
        else if (value > 0.4) { color = 'orange'; text = 'Medium'; }
        
        return (
          <Space>
            <Progress
              percent={value * 100}
              size="small"
              strokeColor={color}
              showInfo={false}
              style={{ width: 100 }}
            />
            <Tag color={color}>{text}</Tag>
          </Space>
        );
      }
    }
  ];

  return (
    <Card
      title={
        <Space>
          <SettingOutlined style={{ color: '#1890ff' }} />
          <span>Parameter Selection / 参数选择</span>
        </Space>
      }
    >
      <Alert
        message="Select parameters to optimize"
        description="选择需要优化的参数，并设置合理的搜索范围。高敏感性参数对结果影响更大。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Table
        dataSource={parameters}
        columns={columns}
        rowKey="name"
        pagination={false}
        size="small"
      />
      
      <Divider />
      
      <Row gutter={16}>
        <Col span={8}>
          <Statistic
            title="Total Parameters / 总参数"
            value={parameters.length}
            prefix={<SettingOutlined />}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="Enabled / 已启用"
            value={parameters.filter(p => p.enabled).length}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="High Sensitivity / 高敏感性"
            value={parameters.filter(p => p.sensitivity > 0.7).length}
            prefix={<FireOutlined />}
            valueStyle={{ color: '#cf1322' }}
          />
        </Col>
      </Row>
    </Card>
  );
};

// ============================================================================
// Optimization Configuration Component
// ============================================================================

interface OptimizationConfig {
  algorithm: 'GA' | 'PSO' | 'SCE-UA' | 'DE' | 'DREAM';
  populationSize: number;
  maxIterations: number;
  convergenceTolerance: number;
  objectiveFunction: 'NSE' | 'RMSE' | 'MAE' | 'KGE' | 'Multi';
  constraints: string[];
  parallelProcesses: number;
}

const OptimizationConfiguration: React.FC<{
  config: OptimizationConfig;
  onChange: (config: OptimizationConfig) => void;
}> = ({ config, onChange }) => {
  const handleChange = (field: keyof OptimizationConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const algorithmInfo = {
    GA: { name: 'Genetic Algorithm / 遗传算法', icon: '🧬', desc: 'Evolutionary optimization, good for discrete problems' },
    PSO: { name: 'Particle Swarm Optimization / 粒子群优化', icon: '🦅', desc: 'Swarm intelligence, fast convergence' },
    'SCE-UA': { name: 'Shuffled Complex Evolution / 混洗复形演化', icon: '🔄', desc: 'Excellent for hydrological calibration' },
    DE: { name: 'Differential Evolution / 差分进化', icon: '⚡', desc: 'Robust and simple, continuous problems' },
    DREAM: { name: 'DiffeRential Evolution Adaptive Metropolis / DREAM', icon: '🎯', desc: 'Bayesian inference, uncertainty analysis' }
  };

  const objectiveFunctions = {
    NSE: { name: 'Nash-Sutcliffe Efficiency', desc: 'NSE = 1 - Σ(Qobs - Qsim)² / Σ(Qobs - Qmean)²', range: '(-∞, 1]', optimal: 'Max' },
    RMSE: { name: 'Root Mean Square Error', desc: 'RMSE = √(Σ(Qobs - Qsim)² / n)', range: '[0, +∞)', optimal: 'Min' },
    MAE: { name: 'Mean Absolute Error', desc: 'MAE = Σ|Qobs - Qsim| / n', range: '[0, +∞)', optimal: 'Min' },
    KGE: { name: 'Kling-Gupta Efficiency', desc: 'KGE = 1 - √((r-1)² + (α-1)² + (β-1)²)', range: '(-∞, 1]', optimal: 'Max' },
    Multi: { name: 'Multi-Objective', desc: 'Optimize multiple objectives simultaneously', range: 'Variable', optimal: 'Pareto' }
  };

  return (
    <Card
      title={
        <Space>
          <RocketOutlined style={{ color: '#52c41a' }} />
          <span>Optimization Configuration / 优化配置</span>
        </Space>
      }
    >
      <Form layout="vertical">
        <Divider orientation="left">Algorithm Selection / 算法选择</Divider>
        
        <Form.Item label="Optimization Algorithm / 优化算法">
          <Radio.Group
            value={config.algorithm}
            onChange={(e) => handleChange('algorithm', e.target.value)}
            buttonStyle="solid"
            style={{ width: '100%' }}
          >
            {Object.entries(algorithmInfo).map(([key, info]) => (
              <Radio.Button key={key} value={key} style={{ marginBottom: 8 }}>
                <Tooltip title={info.desc}>
                  {info.icon} {info.name}
                </Tooltip>
              </Radio.Button>
            ))}
          </Radio.Group>
        </Form.Item>

        <Alert
          message={algorithmInfo[config.algorithm].name}
          description={algorithmInfo[config.algorithm].desc}
          type="success"
          showIcon
          icon={<span style={{ fontSize: 24 }}>{algorithmInfo[config.algorithm].icon}</span>}
          style={{ marginBottom: 24 }}
        />

        <Divider orientation="left">Algorithm Parameters / 算法参数</Divider>

        <Row gutter={24}>
          <Col span={8}>
            <Form.Item label="Population Size / 种群规模">
              <InputNumber
                value={config.populationSize}
                onChange={(v) => handleChange('populationSize', v || 50)}
                style={{ width: '100%' }}
                min={10}
                max={500}
                step={10}
              />
              <Slider
                value={config.populationSize}
                onChange={(v) => handleChange('populationSize', v)}
                min={10}
                max={200}
                step={10}
                marks={{ 10: '10', 50: '50', 100: '100', 200: '200' }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Max Iterations / 最大迭代次数">
              <InputNumber
                value={config.maxIterations}
                onChange={(v) => handleChange('maxIterations', v || 100)}
                style={{ width: '100%' }}
                min={10}
                max={10000}
                step={10}
              />
              <Slider
                value={config.maxIterations}
                onChange={(v) => handleChange('maxIterations', v)}
                min={10}
                max={1000}
                step={10}
                marks={{ 10: '10', 250: '250', 500: '500', 1000: '1k' }}
              />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item label="Convergence Tolerance / 收敛容差">
              <Select
                value={config.convergenceTolerance}
                onChange={(v) => handleChange('convergenceTolerance', v)}
                style={{ width: '100%' }}
              >
                <Option value={0.001}>0.001 (High precision / 高精度)</Option>
                <Option value={0.01}>0.01 (Medium / 中等)</Option>
                <Option value={0.1}>0.1 (Fast / 快速)</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left">Objective Function / 目标函数</Divider>

        <Form.Item label="Objective Function / 目标函数">
          <Select
            value={config.objectiveFunction}
            onChange={(v) => handleChange('objectiveFunction', v)}
            style={{ width: '100%' }}
          >
            {Object.entries(objectiveFunctions).map(([key, info]) => (
              <Option key={key} value={key}>
                <Space direction="vertical" size={0}>
                  <Text strong>{info.name}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {info.desc} | Range: {info.range} | Optimal: {info.optimal}
                  </Text>
                </Space>
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Divider orientation="left">Performance / 性能</Divider>

        <Form.Item label="Parallel Processes / 并行进程">
          <Radio.Group
            value={config.parallelProcesses}
            onChange={(e) => handleChange('parallelProcesses', e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value={1}>1 (Serial / 串行)</Radio.Button>
            <Radio.Button value={4}>4 cores</Radio.Button>
            <Radio.Button value={8}>8 cores</Radio.Button>
            <Radio.Button value={16}>16 cores</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Alert
          message="Estimated Time"
          description={`With ${config.parallelProcesses} processes: ~${Math.ceil((config.populationSize * config.maxIterations) / (config.parallelProcesses * 100))} minutes`}
          type="info"
          showIcon
        />
      </Form>
    </Card>
  );
};

// ============================================================================
// Optimization Progress Component
// ============================================================================

interface OptimizationProgress {
  isRunning: boolean;
  currentIteration: number;
  totalIterations: number;
  bestObjective: number;
  currentObjective: number;
  elapsedTime: number;
  estimatedTimeRemaining: number;
  convergenceHistory: number[];
}

const OptimizationProgressPanel: React.FC<{
  progress: OptimizationProgress;
  onStop: () => void;
}> = ({ progress, onStop }) => {
  const getProgressPercent = () => {
    return (progress.currentIteration / progress.totalIterations) * 100;
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const convergenceData = {
    labels: progress.convergenceHistory.map((_, i) => i + 1),
    datasets: [
      {
        label: 'Objective Value',
        data: progress.convergenceHistory,
        borderColor: '#1890ff',
        backgroundColor: 'rgba(24, 144, 255, 0.2)',
        tension: 0.4
      }
    ]
  };

  return (
    <Card
      title={
        <Space>
          {progress.isRunning ? (
            <LoadingOutlined spin style={{ color: '#1890ff' }} />
          ) : (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          )}
          <span>Optimization Progress / 优化进度</span>
        </Space>
      }
      extra={
        progress.isRunning && (
          <Button danger onClick={onStop} icon={<WarningOutlined />}>
            Stop / 停止
          </Button>
        )
      }
    >
      {progress.isRunning ? (
        <>
          <Progress
            percent={getProgressPercent()}
            status="active"
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          
          <Row gutter={16} style={{ marginTop: 24 }}>
            <Col span={6}>
              <Statistic
                title="Iteration / 迭代"
                value={progress.currentIteration}
                suffix={`/ ${progress.totalIterations}`}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Best Objective / 最佳目标"
                value={progress.bestObjective}
                precision={4}
                valueStyle={{ color: '#3f8600' }}
                prefix={<ThunderboltOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Elapsed Time / 已用时间"
                value={formatTime(progress.elapsedTime)}
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Remaining / 剩余时间"
                value={formatTime(progress.estimatedTimeRemaining)}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Col>
          </Row>

          <Divider />

          <Title level={5}>Convergence History / 收敛历史</Title>
          <div style={{ height: 300 }}>
            <Line
              data={convergenceData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: true },
                  tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                  y: { title: { display: true, text: 'Objective Value' } },
                  x: { title: { display: true, text: 'Iteration' } }
                }
              }}
            />
          </div>
        </>
      ) : (
        <Result
          icon={<RocketOutlined style={{ color: '#1890ff' }} />}
          title="Ready to Optimize / 准备优化"
          subTitle="Click 'Start Optimization' to begin the calibration process"
        />
      )}
    </Card>
  );
};

// ============================================================================
// Main Optimization Panel
// ============================================================================

const ParameterOptimizationPanel: React.FC = () => {
  const [parameters, setParameters] = useState<OptimizationParameter[]>([
    { name: 'manning_n', displayName: "Manning's n / 曼宁系数", currentValue: 0.03, minValue: 0.01, maxValue: 0.1, unit: '', sensitivity: 0.85, enabled: true },
    { name: 'cfl', displayName: 'CFL Number / CFL数', currentValue: 0.5, minValue: 0.1, maxValue: 0.9, unit: '', sensitivity: 0.45, enabled: false },
    { name: 'infiltration', displayName: 'Infiltration Rate / 入渗率', currentValue: 5.0, minValue: 0.0, maxValue: 20.0, unit: 'mm/h', sensitivity: 0.65, enabled: true },
    { name: 'gate_coef', displayName: 'Gate Discharge Coef / 闸门流量系数', currentValue: 0.6, minValue: 0.4, maxValue: 0.8, unit: '', sensitivity: 0.75, enabled: true },
    { name: 'roughness_depth', displayName: 'Roughness-Depth Relation / 糙率-水深关系', currentValue: 1.0, minValue: 0.5, maxValue: 2.0, unit: '', sensitivity: 0.35, enabled: false }
  ]);

  const [config, setConfig] = useState<OptimizationConfig>({
    algorithm: 'SCE-UA',
    populationSize: 50,
    maxIterations: 500,
    convergenceTolerance: 0.01,
    objectiveFunction: 'NSE',
    constraints: [],
    parallelProcesses: 4
  });

  const [progress, setProgress] = useState<OptimizationProgress>({
    isRunning: false,
    currentIteration: 0,
    totalIterations: 500,
    bestObjective: 0.0,
    currentObjective: 0.0,
    elapsedTime: 0,
    estimatedTimeRemaining: 0,
    convergenceHistory: []
  });

  const handleStartOptimization = () => {
    setProgress({
      ...progress,
      isRunning: true,
      currentIteration: 0,
      convergenceHistory: []
    });
    // TODO: Integrate with backend optimization API
  };

  const handleStopOptimization = () => {
    setProgress({ ...progress, isRunning: false });
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px' }}>
          <Title level={2}>
            <RocketOutlined /> Parameter Optimization / 参数优化
          </Title>
          <Paragraph>
            Automatic calibration and sensitivity analysis for hydraulic parameters /
            水力学参数的自动校准和敏感性分析
          </Paragraph>
        </div>

        <Tabs defaultActiveKey="parameters" size="large">
          <TabPane
            tab={
              <span>
                <SettingOutlined />
                Parameters / 参数
              </span>
            }
            key="parameters"
          >
            <ParameterSelection parameters={parameters} onChange={setParameters} />
          </TabPane>

          <TabPane
            tab={
              <span>
                <RocketOutlined />
                Configuration / 配置
              </span>
            }
            key="configuration"
          >
            <OptimizationConfiguration config={config} onChange={setConfig} />
            
            <Divider />
            
            <Space size="large">
              <Button
                type="primary"
                size="large"
                icon={<ThunderboltOutlined />}
                onClick={handleStartOptimization}
                disabled={progress.isRunning || parameters.filter(p => p.enabled).length === 0}
              >
                Start Optimization / 开始优化
              </Button>
              
              <Button size="large" icon={<InfoCircleOutlined />}>
                Load Observed Data / 加载观测数据
              </Button>
            </Space>
          </TabPane>

          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                Progress / 进度
              </span>
            }
            key="progress"
          >
            <OptimizationProgressPanel progress={progress} onStop={handleStopOptimization} />
          </TabPane>

          <TabPane
            tab={
              <span>
                <BarChartOutlined />
                Sensitivity / 敏感性
              </span>
            }
            key="sensitivity"
          >
            <Card title="Sensitivity Analysis / 敏感性分析">
              <Paragraph>
                Analyze parameter sensitivity using Morris or Sobol methods /
                使用Morris或Sobol方法分析参数敏感性
              </Paragraph>
              <Button type="primary" icon={<ExperimentOutlined />}>
                Run Sensitivity Analysis / 运行敏感性分析
              </Button>
            </Card>
          </TabPane>

          <TabPane
            tab={
              <span>
                <HistoryOutlined />
                History / 历史
              </span>
            }
            key="history"
          >
            <Card title="Optimization History / 优化历史">
              <Timeline>
                <Timeline.Item color="green">
                  2025-01-15 10:30 - SCE-UA optimization completed (NSE: 0.892)
                </Timeline.Item>
                <Timeline.Item color="blue">
                  2025-01-14 16:20 - PSO optimization completed (NSE: 0.875)
                </Timeline.Item>
                <Timeline.Item color="red">
                  2025-01-13 09:45 - GA optimization failed (timeout)
                </Timeline.Item>
              </Timeline>
            </Card>
          </TabPane>
        </Tabs>
      </Content>
    </Layout>
  );
};

export default ParameterOptimizationPanel;


