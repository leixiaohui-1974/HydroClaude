import { useState, useMemo } from 'react';
import { Card, Descriptions, Space, Tag, Typography, Tabs, Alert, Button } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import Plot from 'react-plotly.js';
import { SimulationResultResponse } from '@/services/simulation-api';
import AnimationController from './components/AnimationController';
import Plot3D from './components/Plot3D';
import EnhancedCharts from './components/EnhancedCharts';
import ResultsExport from './components/ResultsExport';
import { ResultAnalysis } from '@/features/analysis';
import { useKeyboardShortcuts, DEFAULT_SHORTCUTS } from '@/hooks/useKeyboardShortcuts';

const { Text } = Typography;

interface SimulationResultsProps {
  result: SimulationResultResponse;
}

/**
 * SimulationResults Component (Enhanced v1.4.0)
 *
 * Displays simulation results with advanced visualization:
 * - Classic 2D plots (backward compatible)
 * - Animation controls for time evolution
 * - 3D surface plots
 * - Enhanced charts (contour, heatmap, time series)
 *
 * Features:
 * - Multiple visualization modes
 * - Interactive animation
 * - Synchronized time control
 * - Performance metrics display
 */
const SimulationResults = ({ result }: SimulationResultsProps) => {
  const [timeIndex, setTimeIndex] = useState(0); // Start from beginning for animation
  const [exportModalVisible, setExportModalVisible] = useState(false); // Export modal visibility
  const [isPlaying, setIsPlaying] = useState(false); // Animation play state

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: DEFAULT_SHORTCUTS.PLAY_PAUSE,
      handler: () => setIsPlaying(prev => !prev),
      description: 'Toggle play/pause animation'
    },
    {
      key: DEFAULT_SHORTCUTS.EXPORT,
      handler: () => {
        if (result.status === 'completed') {
          setExportModalVisible(true);
        }
      },
      description: 'Export results',
      enabled: result.status === 'completed'
    }
  ]);

  // Prepare data for current time step
  const currentData = useMemo(() => {
    const safeIndex = Math.min(timeIndex, (result.time?.length ?? 1) - 1);
    return {
      x: result.x ?? [],
      h: result.h?.[safeIndex] ?? [],
      Q: result.Q?.[safeIndex] ?? [],
      V: result.V?.[safeIndex] ?? [],
      time: result.time?.[safeIndex] ?? 0
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
        line: { color: '#1890ff', width: 3 },
        fill: 'tozeroy',
        fillcolor: 'rgba(24, 144, 255, 0.2)'
      }
    ],
    layout: {
      title: `水深分布 (t = ${currentData.time.toFixed(2)}s)`,
      xaxis: {
        title: '位置 (m)',
        showgrid: true,
        gridcolor: '#e0e0e0'
      },
      yaxis: {
        title: '水深 (m)',
        showgrid: true,
        gridcolor: '#e0e0e0',
        rangemode: 'tozero'
      },
      height: 350,
      margin: { t: 50, r: 20, b: 50, l: 60 },
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff',
      hovermode: 'closest'
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
        line: { color: '#52c41a', width: 3 }
      }
    ],
    layout: {
      title: `流速分布 (t = ${currentData.time.toFixed(2)}s)`,
      xaxis: {
        title: '位置 (m)',
        showgrid: true,
        gridcolor: '#e0e0e0'
      },
      yaxis: {
        title: '流速 (m/s)',
        showgrid: true,
        gridcolor: '#e0e0e0'
      },
      height: 350,
      margin: { t: 50, r: 20, b: 50, l: 60 },
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff',
      hovermode: 'closest'
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
        line: { color: '#fa8c16', width: 3 }
      }
    ],
    layout: {
      title: `流量分布 (t = ${currentData.time.toFixed(2)}s)`,
      xaxis: {
        title: '位置 (m)',
        showgrid: true,
        gridcolor: '#e0e0e0'
      },
      yaxis: {
        title: '流量 (m³/s)',
        showgrid: true,
        gridcolor: '#e0e0e0'
      },
      height: 350,
      margin: { t: 50, r: 20, b: 50, l: 60 },
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff',
      hovermode: 'closest'
    }
  }), [currentData]);

  // Format scientific notation
  const formatScientific = (value: number) => {
    if (Math.abs(value) < 0.001 || Math.abs(value) > 1000) {
      return value.toExponential(2);
    }
    return value.toFixed(4);
  };

  // Visualization tabs
  const visualizationTabs = [
    {
      key: 'analysis',
      label: '🔍 自动分析',
      children: (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Alert
            message="🎉 专业结果分析（对标商业软件）"
            description="自动分析水力特性、守恒性、关键事件，提供质量评级和可视化建议。"
            type="success"
            showIcon
            closable
          />
          <ResultAnalysis
            result={result}
            taskId={result.task_id}
            autoAnalyze={true}
          />
        </Space>
      )
    },
    {
      key: 'classic',
      label: '📊 经典视图',
      children: (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Card title="水深分布" size="small">
            <Plot
              data={depthPlot.data as any}
              layout={depthPlot.layout as any}
              config={{ responsive: true, displaylogo: false }}
              style={{ width: '100%' }}
            />
          </Card>

          <Card title="流速分布" size="small">
            <Plot
              data={velocityPlot.data as any}
              layout={velocityPlot.layout as any}
              config={{ responsive: true, displaylogo: false }}
              style={{ width: '100%' }}
            />
          </Card>

          <Card title="流量分布" size="small">
            <Plot
              data={dischargePlot.data as any}
              layout={dischargePlot.layout as any}
              config={{ responsive: true, displaylogo: false }}
              style={{ width: '100%' }}
            />
          </Card>
        </Space>
      )
    },
    {
      key: '3d',
      label: '🎨 3D可视化',
      children: (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Alert
            message="3D可视化 (v1.4.0新功能)"
            description="使用鼠标拖动旋转视角，滚轮缩放。支持多种配色方案和显示模式。"
            type="info"
            showIcon
            closable
          />

          <Plot3D
            x={result.x}
            time={result.time}
            h={result.h}
            V={result.V}
            Q={result.Q}
            title="3D水深演化"
            variable="h"
          />

          <Plot3D
            x={result.x}
            time={result.time}
            h={result.h}
            V={result.V}
            Q={result.Q}
            title="3D流速演化"
            variable="V"
          />
        </Space>
      )
    },
    {
      key: 'enhanced',
      label: '📈 增强图表',
      children: (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Alert
            message="增强图表 (v1.4.0新功能)"
            description="包含等值线图、热力图、时间序列和统计分析。支持交互式探索和多变量比较。"
            type="info"
            showIcon
            closable
          />

          <EnhancedCharts
            x={result.x}
            time={result.time}
            h={result.h}
            V={result.V}
            Q={result.Q}
          />
        </Space>
      )
    }
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Status Badge and Export Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Tag color={result.status === 'completed' ? 'success' : 'error'} style={{ fontSize: 14 }}>
            {result.status === 'completed' ? '✓ 模拟完成' : '✗ 模拟失败'}
          </Tag>
          <Text type="secondary">
            任务ID: {result.task_id}
          </Text>
        </div>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          onClick={() => setExportModalVisible(true)}
          disabled={result.status !== 'completed'}
        >
          导出结果
        </Button>
      </div>

      {/* v1.4.0 Feature Banner */}
      <Alert
        message="🎉 v1.4.0 增强可视化功能"
        description="现在支持动画控制、3D可视化、等值线图、热力图和时间序列分析！"
        type="success"
        showIcon
        closable
      />

      {/* Metrics */}
      <Card title="性能指标" size="small">
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label="执行时间">
            {result.duration.toFixed(4)}s
          </Descriptions.Item>
          <Descriptions.Item label="时间步数">
            {result.metrics.total_iterations}
          </Descriptions.Item>
          <Descriptions.Item label="质量守恒误差">
            <Text type={result.metrics.mass_conservation_error < 1e-6 ? 'success' : 'warning'}>
              {formatScientific(result.metrics.mass_conservation_error)}
              {result.metrics.mass_conservation_error < 1e-6 && ' ✓'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="收敛状态">
            {result.metrics.converged ? (
              <Tag color="success">✓ 收敛</Tag>
            ) : (
              <Tag color="warning">⚠ 未收敛</Tag>
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

      {/* Structure Performance Metrics (v1.5.0 NEW) */}
      {result.metrics.system_type && result.metrics.system_type !== 'canal_only' && (
        <Card title="水工结构运行指标" size="small">
          <Descriptions column={2} size="small" bordered>
            {result.metrics.system_type === 'canal_with_gate' && (
              <>
                <Descriptions.Item label="闸门类型">
                  {result.metrics.gate_type === 'sluice' ? '平板闸' : '弧形闸'}
                </Descriptions.Item>
                <Descriptions.Item label="闸门开度">
                  {result.metrics.gate_opening?.toFixed(2)} m
                </Descriptions.Item>
                <Descriptions.Item label="过闸流量">
                  <Text strong style={{ color: '#fa8c16' }}>
                    {result.metrics.gate_discharge?.toFixed(4)} m³/s
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="流态">
                  {result.metrics.gate_regime === 'free' ? <Tag color="green">自由出流</Tag> : <Tag color="blue">淹没出流</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="位置">
                  {result.metrics.gate_position?.toFixed(1)} m
                </Descriptions.Item>
              </>
            )}

            {result.metrics.system_type === 'canal_with_pump' && (
              <>
                <Descriptions.Item label="泵站名称">
                  {result.metrics.pump_name || 'Pump Station'}
                </Descriptions.Item>
                <Descriptions.Item label="运行状态">
                  <Tag color="processing">运行中</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="抽水流量">
                  <Text strong style={{ color: '#1890ff' }}>
                    {result.metrics.pump_flow?.toFixed(4)} m³/s
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="扬程">
                  {result.metrics.pump_head?.toFixed(2)} m
                </Descriptions.Item>
                <Descriptions.Item label="位置">
                  {result.metrics.pump_position?.toFixed(1)} m
                </Descriptions.Item>
                <Descriptions.Item label="总抽水量">
                  {formatScientific(result.metrics.total_pumped_volume ?? 0)} m³
                </Descriptions.Item>
              </>
            )}

            {result.metrics.system_type === 'canal_with_weir' && (
              <>
                <Descriptions.Item label="堰型">
                  {result.metrics.weir_type}
                </Descriptions.Item>
                <Descriptions.Item label="堰顶高程">
                  {result.metrics.crest_height?.toFixed(2)} m
                </Descriptions.Item>
                <Descriptions.Item label="过堰流量">
                  <Text strong style={{ color: '#722ed1' }}>
                    {result.metrics.weir_discharge?.toFixed(4)} m³/s
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="堰上水头">
                  {result.metrics.weir_head?.toFixed(3)} m
                </Descriptions.Item>
                <Descriptions.Item label="位置">
                  {result.metrics.weir_position?.toFixed(1)} m
                </Descriptions.Item>
              </>
            )}
          </Descriptions>
        </Card>
      )}

      {/* Animation Controller (v1.4.0 NEW) */}
      <Card title="🎬 动画控制 (v1.4.0新功能) - 按Space键播放/暂停" size="small">
        <AnimationController
          totalFrames={result.time.length}
          currentFrame={timeIndex}
          onFrameChange={setTimeIndex}
          autoPlay={isPlaying}
          defaultSpeed={1}
        />
      </Card>

      {/* Visualization Tabs */}
      <Tabs items={visualizationTabs} defaultActiveKey="classic" />

      {/* Export Modal (v1.5.0 NEW) */}
      <ResultsExport
        result={result}
        visible={exportModalVisible}
        onClose={() => setExportModalVisible(false)}
      />
    </Space>
  );
};

export default SimulationResults;
