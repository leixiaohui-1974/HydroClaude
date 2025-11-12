/**
 * Comparison View Component
 * 多场景对比组件
 *
 * v1.5.0 Feature: Multi-Scenario Comparison
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
  Card,
  Space,
  Button,
  Select,
  Radio,
  Switch,
  Slider,
  Table,
  Tag,
  Alert,
  Row,
  Col,
  Statistic,
  Tooltip,
  message,
  Typography
} from 'antd';
import {
  LineChartOutlined,
  ColumnWidthOutlined,
  DiffOutlined,
  DownloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  EyeInvisibleOutlined
} from '@ant-design/icons';
import Plot from 'react-plotly.js';
import type {
  ComparisonScenario,
  ComparisonMode,
  ComparisonMetrics
} from '@/types/comparison';
import {
  validateScenarios,
  calculateComparisonMetrics,
  calculateDifferenceData,
  formatMetricValue,
  exportComparisonCSV
} from '@/utils/comparisonUtils';
import { DEFAULT_SCENARIO_COLORS, VARIABLE_NAMES } from '@/types/comparison';

const { Text, Title } = Typography;
const { Option } = Select;

interface ComparisonViewProps {
  /**
   * List of scenarios to compare
   * 对比场景列表
   */
  scenarios: ComparisonScenario[];

  /**
   * Callback when scenarios change
   * 场景变化回调
   */
  onScenariosChange?: (scenarios: ComparisonScenario[]) => void;
}

/**
 * ComparisonView Component
 *
 * Displays multiple simulation scenarios for comparison with:
 * - Overlay mode: All scenarios on same plot
 * - Side-by-side mode: Separate plots for each scenario
 * - Diff mode: Difference visualization between two scenarios
 */
const ComparisonView: React.FC<ComparisonViewProps> = ({
  scenarios: initialScenarios,
  onScenariosChange
}) => {
  // State
  const [scenarios, setScenarios] = useState<ComparisonScenario[]>(initialScenarios);
  const [mode, setMode] = useState<ComparisonMode>('overlay');
  const [variable, setVariable] = useState<'h' | 'Q' | 'V'>('h');
  const [timeIndex, setTimeIndex] = useState(0);
  const [syncTime, setSyncTime] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [selectedPair, setSelectedPair] = useState<[string, string] | null>(null);

  // Update parent when scenarios change
  const updateScenarios = useCallback((newScenarios: ComparisonScenario[]) => {
    setScenarios(newScenarios);
    onScenariosChange?.(newScenarios);
  }, [onScenariosChange]);

  // Get visible scenarios
  const visibleScenarios = useMemo(
    () => scenarios.filter(s => s.visible),
    [scenarios]
  );

  // Find common time range
  const timeRange = useMemo(() => {
    if (visibleScenarios.length === 0) {
      return { max: 0, times: [] };
    }

    const minLength = Math.min(...visibleScenarios.map(s => s.result.time.length));
    const firstScenario = visibleScenarios[0];

    return {
      max: minLength - 1,
      times: firstScenario.result.time.slice(0, minLength)
    };
  }, [visibleScenarios]);

  // Calculate comparison metrics for selected pair
  const metrics = useMemo((): ComparisonMetrics | null => {
    if (!selectedPair || mode !== 'diff') return null;

    const scenarioA = scenarios.find(s => s.id === selectedPair[0]);
    const scenarioB = scenarios.find(s => s.id === selectedPair[1]);

    if (!scenarioA || !scenarioB) return null;

    const validation = validateScenarios(scenarioA, scenarioB);
    if (!validation.valid) {
      return null;
    }

    return calculateComparisonMetrics(scenarioA, scenarioB, variable);
  }, [selectedPair, scenarios, variable, mode]);

  // Toggle scenario visibility
  const toggleScenarioVisibility = (id: string) => {
    const newScenarios = scenarios.map(s =>
      s.id === id ? { ...s, visible: !s.visible } : s
    );
    updateScenarios(newScenarios);
  };

  // Remove scenario
  const removeScenario = (id: string) => {
    const newScenarios = scenarios.filter(s => s.id !== id);
    updateScenarios(newScenarios);

    // Clear selected pair if it includes the removed scenario
    if (selectedPair && (selectedPair[0] === id || selectedPair[1] === id)) {
      setSelectedPair(null);
    }
  };

  // Render overlay mode (all scenarios on one plot)
  const renderOverlayMode = () => {
    if (visibleScenarios.length === 0) {
      return <Alert message="没有可见的场景" type="info" />;
    }

    const plotData = visibleScenarios.map(scenario => {
      const data = scenario.result[variable][timeIndex];
      return {
        x: scenario.result.x,
        y: data,
        type: 'scatter',
        mode: 'lines',
        name: scenario.name,
        line: {
          color: scenario.color,
          width: 2
        }
      };
    });

    const currentTime = timeRange.times[timeIndex] || 0;
    const varInfo = VARIABLE_NAMES[variable];

    return (
      <Card>
        <Plot
          data={plotData as any}
          layout={{
            title: `${varInfo.zh} / ${varInfo.en} (t = ${currentTime.toFixed(2)}s)`,
            xaxis: {
              title: '位置 Position (m)',
              showgrid: true
            },
            yaxis: {
              title: `${varInfo.zh} ${varInfo.en} (${varInfo.unit})`,
              showgrid: true
            },
            showlegend: showLegend,
            height: 450,
            margin: { t: 50, r: 20, b: 50, l: 60 },
            hovermode: 'closest'
          } as any}
          config={{ responsive: true, displaylogo: false }}
          style={{ width: '100%' }}
        />
      </Card>
    );
  };

  // Render side-by-side mode (separate plots)
  const renderSideBySideMode = () => {
    if (visibleScenarios.length === 0) {
      return <Alert message="没有可见的场景" type="info" />;
    }

    const varInfo = VARIABLE_NAMES[variable];
    const currentTime = timeRange.times[timeIndex] || 0;

    return (
      <Row gutter={[16, 16]}>
        {visibleScenarios.map(scenario => {
          const data = scenario.result[variable][timeIndex];

          return (
            <Col span={visibleScenarios.length === 1 ? 24 : 12} key={scenario.id}>
              <Card title={scenario.name} size="small">
                <Plot
                  data={[{
                    x: scenario.result.x,
                    y: data,
                    type: 'scatter',
                    mode: 'lines',
                    line: {
                      color: scenario.color,
                      width: 2
                    }
                  } as any]}
                  layout={{
                    xaxis: {
                      title: 'Position (m)',
                      showgrid: true
                    },
                    yaxis: {
                      title: `${varInfo.en} (${varInfo.unit})`,
                      showgrid: true
                    },
                    showlegend: false,
                    height: 300,
                    margin: { t: 20, r: 20, b: 40, l: 50 }
                  } as any}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
                <Text type="secondary">Time: {currentTime.toFixed(2)}s</Text>
              </Card>
            </Col>
          );
        })}
      </Row>
    );
  };

  // Render diff mode (difference between two scenarios)
  const renderDiffMode = () => {
    if (!selectedPair) {
      return (
        <Alert
          message="请选择两个场景进行对比"
          description="从下方的场景选择器中选择要对比的两个场景"
          type="info"
          showIcon
        />
      );
    }

    const scenarioA = scenarios.find(s => s.id === selectedPair[0]);
    const scenarioB = scenarios.find(s => s.id === selectedPair[1]);

    if (!scenarioA || !scenarioB) {
      return <Alert message="找不到选中的场景" type="error" />;
    }

    // Validate scenarios
    const validation = validateScenarios(scenarioA, scenarioB);
    if (!validation.valid) {
      return (
        <Alert
          message="场景不兼容"
          description={
            <ul>
              {validation.errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          }
          type="error"
          showIcon
        />
      );
    }

    // Calculate difference
    const diffData = calculateDifferenceData(scenarioA, scenarioB, variable);
    const diff = diffData.diff[timeIndex];
    const percentDiff = diffData.percentDiff[timeIndex];

    const varInfo = VARIABLE_NAMES[variable];
    const currentTime = timeRange.times[timeIndex] || 0;

    return (
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* Difference Plot */}
        <Card title="差异对比 Difference Comparison">
          <Plot
            data={[
              {
                x: diffData.x,
                y: diff,
                type: 'scatter',
                mode: 'lines',
                name: 'Difference',
                line: { color: '#fa8c16', width: 2 },
                fill: 'tozeroy',
                fillcolor: 'rgba(250, 140, 22, 0.2)'
              } as any
            ]}
            layout={{
              title: `${varInfo.zh} Difference (${scenarioB.name} - ${scenarioA.name}, t=${currentTime.toFixed(2)}s)`,
              xaxis: {
                title: 'Position (m)',
                showgrid: true
              },
              yaxis: {
                title: `Δ${varInfo.en} (${varInfo.unit})`,
                showgrid: true,
                zeroline: true
              },
              height: 350,
              hovermode: 'closest'
            } as any}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%' }}
          />
        </Card>

        {/* Percent Difference Plot */}
        <Card title="百分比差异 Percentage Difference">
          <Plot
            data={[
              {
                x: diffData.x,
                y: percentDiff,
                type: 'scatter',
                mode: 'lines',
                name: '% Difference',
                line: { color: '#eb2f96', width: 2 }
              } as any
            ]}
            layout={{
              title: `Percentage Difference (t=${currentTime.toFixed(2)}s)`,
              xaxis: {
                title: 'Position (m)',
                showgrid: true
              },
              yaxis: {
                title: '% Difference',
                showgrid: true,
                zeroline: true
              },
              height: 300,
              hovermode: 'closest'
            } as any}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%' }}
          />
        </Card>

        {/* Comparison Metrics */}
        {metrics && (
          <Card title="统计指标 Statistical Metrics">
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Statistic
                  title="最大差异 Max Diff"
                  value={formatMetricValue(metrics.maxDifference)}
                  suffix={varInfo.unit}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="平均差异 Mean Diff"
                  value={formatMetricValue(metrics.meanDifference)}
                  suffix={varInfo.unit}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="RMSE"
                  value={formatMetricValue(metrics.rmse)}
                  suffix={varInfo.unit}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="相关系数 Correlation"
                  value={formatMetricValue(metrics.correlation, 4)}
                  valueStyle={{
                    color: metrics.correlation > 0.9 ? '#3f8600' : '#faad14'
                  }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="最大百分比差异 Max % Diff"
                  value={formatMetricValue(metrics.maxPercentDifference, 2)}
                  suffix="%"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="平均百分比差异 Mean % Diff"
                  value={formatMetricValue(metrics.meanPercentDifference, 2)}
                  suffix="%"
                />
              </Col>
            </Row>
          </Card>
        )}
      </Space>
    );
  };

  // Export comparison data
  const handleExport = () => {
    if (mode === 'diff' && selectedPair) {
      const scenarioA = scenarios.find(s => s.id === selectedPair[0]);
      const scenarioB = scenarios.find(s => s.id === selectedPair[1]);

      if (scenarioA && scenarioB) {
        const csv = exportComparisonCSV(scenarioA, scenarioB, variable, timeIndex);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `comparison_${scenarioA.name}_${scenarioB.name}_t${timeIndex}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        message.success('对比数据已导出');
      }
    } else {
      message.info('仅在差异模式下支持导出');
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* Control Panel */}
      <Card title="对比控制 Comparison Controls">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* Mode Selection */}
          <div>
            <Text strong>对比模式 Comparison Mode:</Text>
            <Radio.Group
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              buttonStyle="solid"
              style={{ marginLeft: 16 }}
            >
              <Radio.Button value="overlay">
                <LineChartOutlined /> 叠加 Overlay
              </Radio.Button>
              <Radio.Button value="sideBySide">
                <ColumnWidthOutlined /> 并排 Side-by-Side
              </Radio.Button>
              <Radio.Button value="diff">
                <DiffOutlined /> 差异 Difference
              </Radio.Button>
            </Radio.Group>
          </div>

          {/* Variable Selection */}
          <div>
            <Text strong>变量 Variable:</Text>
            <Select
              value={variable}
              onChange={setVariable}
              style={{ width: 200, marginLeft: 16 }}
            >
              <Option value="h">水深 Water Depth (h)</Option>
              <Option value="Q">流量 Discharge (Q)</Option>
              <Option value="V">流速 Velocity (V)</Option>
            </Select>
          </div>

          {/* Diff Mode: Scenario Pair Selection */}
          {mode === 'diff' && (
            <div>
              <Text strong>选择对比场景 Select Scenarios:</Text>
              <Space style={{ marginLeft: 16 }}>
                <Select
                  placeholder="场景 A"
                  style={{ width: 200 }}
                  value={selectedPair?.[0]}
                  onChange={(value) => {
                    if (selectedPair) {
                      setSelectedPair([value, selectedPair[1]]);
                    } else {
                      setSelectedPair([value, '']);
                    }
                  }}
                >
                  {scenarios.map(s => (
                    <Option key={s.id} value={s.id}>{s.name}</Option>
                  ))}
                </Select>
                <Text>vs</Text>
                <Select
                  placeholder="场景 B"
                  style={{ width: 200 }}
                  value={selectedPair?.[1]}
                  onChange={(value) => {
                    if (selectedPair) {
                      setSelectedPair([selectedPair[0], value]);
                    } else {
                      setSelectedPair(['', value]);
                    }
                  }}
                >
                  {scenarios.map(s => (
                    <Option key={s.id} value={s.id}>{s.name}</Option>
                  ))}
                </Select>
              </Space>
            </div>
          )}

          {/* Options */}
          <div>
            <Space size="large">
              <div>
                <Text>同步时间 Sync Time: </Text>
                <Switch checked={syncTime} onChange={setSyncTime} />
              </div>
              <div>
                <Text>显示图例 Show Legend: </Text>
                <Switch checked={showLegend} onChange={setShowLegend} />
              </div>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                导出 Export
              </Button>
            </Space>
          </div>
        </Space>
      </Card>

      {/* Time Slider */}
      {visibleScenarios.length > 0 && (
        <Card title={`时间控制 Time Control: ${timeRange.times[timeIndex]?.toFixed(2) || 0}s`}>
          <Slider
            min={0}
            max={timeRange.max}
            value={timeIndex}
            onChange={setTimeIndex}
            marks={{
              0: '0s',
              [timeRange.max]: `${(timeRange.times[timeRange.max] || 0).toFixed(2)}s`
            }}
            tooltip={{
              formatter: (value) => `${(timeRange.times[value || 0] || 0).toFixed(2)}s`
            }}
          />
        </Card>
      )}

      {/* Visualization */}
      {mode === 'overlay' && renderOverlayMode()}
      {mode === 'sideBySide' && renderSideBySideMode()}
      {mode === 'diff' && renderDiffMode()}

      {/* Scenario List */}
      <Card title="场景列表 Scenario List">
        <Table
          dataSource={scenarios}
          rowKey="id"
          pagination={false}
          size="small"
          columns={[
            {
              title: '名称 Name',
              dataIndex: 'name',
              key: 'name',
              render: (name: string, record: ComparisonScenario) => (
                <Space>
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      backgroundColor: record.color,
                      borderRadius: 2
                    }}
                  />
                  <Text>{name}</Text>
                </Space>
              )
            },
            {
              title: '任务ID Task ID',
              dataIndex: ['result', 'task_id'],
              key: 'taskId',
              render: (taskId: string) => (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {taskId.substring(0, 8)}...
                </Text>
              )
            },
            {
              title: '时间步数 Time Steps',
              key: 'timeSteps',
              render: (_, record: ComparisonScenario) => record.result.time.length
            },
            {
              title: '空间点数 Spatial Points',
              key: 'spatialPoints',
              render: (_, record: ComparisonScenario) => record.result.x.length
            },
            {
              title: '状态 Status',
              dataIndex: ['result', 'status'],
              key: 'status',
              render: (status: string) => (
                <Tag color={status === 'completed' ? 'success' : 'error'}>
                  {status}
                </Tag>
              )
            },
            {
              title: '操作 Actions',
              key: 'actions',
              render: (_, record: ComparisonScenario) => (
                <Space>
                  <Tooltip title={record.visible ? '隐藏 Hide' : '显示 Show'}>
                    <Button
                      type="text"
                      size="small"
                      icon={record.visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                      onClick={() => toggleScenarioVisibility(record.id)}
                    />
                  </Tooltip>
                  <Tooltip title="删除 Remove">
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => removeScenario(record.id)}
                    />
                  </Tooltip>
                </Space>
              )
            }
          ]}
        />
      </Card>
    </Space>
  );
};

export default ComparisonView;
