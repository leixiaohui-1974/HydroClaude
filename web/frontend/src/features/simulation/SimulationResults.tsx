import { useState, useMemo } from 'react';
import { Card, Descriptions, Slider, Space, Tag, Typography } from 'antd';
import Plot from 'react-plotly.js';
import { SimulationResultResponse } from '@/services/api';

const { Text } = Typography;

interface SimulationResultsProps {
  result: SimulationResultResponse;
}

const SimulationResults = ({ result }: SimulationResultsProps) => {
  const [timeIndex, setTimeIndex] = useState(result.time.length - 1);

  // Prepare data for current time step
  const currentData = useMemo(() => {
    return {
      x: result.x,
      h: result.h[timeIndex],
      Q: result.Q[timeIndex],
      V: result.V[timeIndex],
      time: result.time[timeIndex]
    };
  }, [result, timeIndex]);

  // Water depth plot
  const depthPlot = useMemo(() => ({
    data: [
      {
        x: currentData.x,
        y: currentData.h,
        type: 'scatter',
        mode: 'lines',
        name: '水深',
        line: { color: '#1890ff', width: 2 }
      }
    ],
    layout: {
      title: `水深分布 (t = ${currentData.time.toFixed(2)}s)`,
      xaxis: { title: '位置 (m)' },
      yaxis: { title: '水深 (m)' },
      height: 300,
      margin: { t: 40, r: 20, b: 40, l: 50 }
    }
  }), [currentData]);

  // Velocity plot
  const velocityPlot = useMemo(() => ({
    data: [
      {
        x: currentData.x,
        y: currentData.V,
        type: 'scatter',
        mode: 'lines',
        name: '流速',
        line: { color: '#52c41a', width: 2 }
      }
    ],
    layout: {
      title: `流速分布 (t = ${currentData.time.toFixed(2)}s)`,
      xaxis: { title: '位置 (m)' },
      yaxis: { title: '流速 (m/s)' },
      height: 300,
      margin: { t: 40, r: 20, b: 40, l: 50 }
    }
  }), [currentData]);

  // Discharge plot
  const dischargePlot = useMemo(() => ({
    data: [
      {
        x: currentData.x,
        y: currentData.Q,
        type: 'scatter',
        mode: 'lines',
        name: '流量',
        line: { color: '#fa8c16', width: 2 }
      }
    ],
    layout: {
      title: `流量分布 (t = ${currentData.time.toFixed(2)}s)`,
      xaxis: { title: '位置 (m)' },
      yaxis: { title: '流量 (m³/s)' },
      height: 300,
      margin: { t: 40, r: 20, b: 40, l: 50 }
    }
  }), [currentData]);

  // Format scientific notation
  const formatScientific = (value: number) => {
    if (Math.abs(value) < 0.001 || Math.abs(value) > 1000) {
      return value.toExponential(2);
    }
    return value.toFixed(4);
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Status Badge */}
      <div>
        <Tag color={result.status === 'completed' ? 'success' : 'error'}>
          {result.status === 'completed' ? '✓ 完成' : '✗ 失败'}
        </Tag>
        <Text type="secondary">
          任务ID: {result.task_id}
        </Text>
      </div>

      {/* Metrics */}
      <Card title="性能指标" size="small">
        <Descriptions column={2} size="small">
          <Descriptions.Item label="执行时间">
            {result.duration.toFixed(4)}s
          </Descriptions.Item>
          <Descriptions.Item label="时间步数">
            {result.metrics.total_iterations}
          </Descriptions.Item>
          <Descriptions.Item label="质量守恒误差">
            <Text type={result.metrics.mass_conservation_error < 1e-6 ? 'success' : 'warning'}>
              {formatScientific(result.metrics.mass_conservation_error)}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="收敛状态">
            {result.metrics.converged ? (
              <Tag color="success">收敛</Tag>
            ) : (
              <Tag color="warning">未收敛</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="最大水深">
            {result.metrics.max_depth.toFixed(4)} m
          </Descriptions.Item>
          <Descriptions.Item label="最小水深">
            {result.metrics.min_depth.toFixed(4)} m
          </Descriptions.Item>
          <Descriptions.Item label="最大流速">
            {result.metrics.max_velocity.toFixed(4)} m/s
          </Descriptions.Item>
          <Descriptions.Item label="最大Froude数">
            {result.metrics.max_froude.toFixed(4)}
          </Descriptions.Item>
          <Descriptions.Item label="最终平均水深">
            {result.metrics.mean_depth_final.toFixed(4)} m
          </Descriptions.Item>
          <Descriptions.Item label="最终平均流量">
            {result.metrics.mean_discharge_final.toFixed(4)} m³/s
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Time Slider */}
      <Card title="时间控制" size="small">
        <div style={{ padding: '0 10px' }}>
          <Text>时间: {result.time[timeIndex].toFixed(2)}s</Text>
          <Slider
            min={0}
            max={result.time.length - 1}
            value={timeIndex}
            onChange={setTimeIndex}
            marks={{
              0: '0s',
              [result.time.length - 1]: `${result.time[result.time.length - 1].toFixed(1)}s`
            }}
            tooltip={{ formatter: (value) => `${result.time[value || 0].toFixed(2)}s` }}
          />
        </div>
      </Card>

      {/* Plots */}
      <Card title="水深分布" size="small">
        <Plot
          data={depthPlot.data as any}
          layout={depthPlot.layout as any}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </Card>

      <Card title="流速分布" size="small">
        <Plot
          data={velocityPlot.data as any}
          layout={velocityPlot.layout as any}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </Card>

      <Card title="流量分布" size="small">
        <Plot
          data={dischargePlot.data as any}
          layout={dischargePlot.layout as any}
          config={{ responsive: true }}
          style={{ width: '100%' }}
        />
      </Card>
    </Space>
  );
};

export default SimulationResults;
