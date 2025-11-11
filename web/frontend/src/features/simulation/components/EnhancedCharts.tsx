import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { Card, Tabs, Select, Space, Typography, Slider, Row, Col } from 'antd';

const { Text } = Typography;

interface EnhancedChartsProps {
  x: number[];        // Spatial positions
  time: number[];     // Time points
  h: number[][];      // Water depth [time][space]
  V: number[][];      // Velocity [time][space]
  Q: number[][];      // Discharge [time][space]
}

type ColorScale = 'Viridis' | 'Jet' | 'Hot' | 'Cool' | 'RdBu' | 'Portland';

/**
 * EnhancedCharts Component
 *
 * Provides advanced visualization options:
 * - Contour plots (isolines of water depth/velocity)
 * - Heatmaps (time-space evolution)
 * - Time series at specific locations
 * - Multi-variable comparison
 * - Statistical analysis
 *
 * Features:
 * - Interactive exploration
 * - Multiple color schemes
 * - Point selection for time series
 * - Synchronized views
 */
const EnhancedCharts = ({ x, time, h, V, Q }: EnhancedChartsProps) => {
  const [colorScale, setColorScale] = useState<ColorScale>('Viridis');
  const [selectedLocation, setSelectedLocation] = useState(Math.floor(x.length / 2));

  // Calculate statistics
  const statistics = useMemo(() => {
    const maxDepth = h.map(frame => Math.max(...frame));
    const meanDepth = h.map(frame => frame.reduce((a, b) => a + b, 0) / frame.length);
    const maxVelocity = V.map(frame => Math.max(...frame));
    const meanVelocity = V.map(frame => frame.reduce((a, b) => a + b, 0) / frame.length);

    return {
      maxDepth,
      meanDepth,
      maxVelocity,
      meanVelocity
    };
  }, [h, V]);

  // Contour Plot - Water Depth
  const contourPlot = useMemo(() => ({
    data: [{
      type: 'contour',
      x: x,
      y: time,
      z: h,
      colorscale: colorScale,
      colorbar: {
        title: '水深 (m)',
        titleside: 'right',
        thickness: 20
      },
      contours: {
        showlabels: true,
        labelfont: {
          size: 10,
          color: 'white',
          family: 'Arial'
        },
        labelformat: '.2f'
      },
      hovertemplate:
        '位置: %{x:.1f} m<br>' +
        '时间: %{y:.2f} s<br>' +
        '水深: %{z:.3f} m<br>' +
        '<extra></extra>'
    }],
    layout: {
      title: '水深等值线图 (Contour Plot)',
      xaxis: {
        title: '位置 (m)',
        showgrid: true,
        zeroline: false
      },
      yaxis: {
        title: '时间 (s)',
        showgrid: true,
        zeroline: false
      },
      height: 500,
      margin: { t: 50, r: 100, b: 50, l: 60 },
      hovermode: 'closest',
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff'
    }
  }), [x, time, h, colorScale]);

  // Heatmap - Velocity
  const heatmapPlot = useMemo(() => ({
    data: [{
      type: 'heatmap',
      x: x,
      y: time,
      z: V,
      colorscale: colorScale,
      colorbar: {
        title: '流速 (m/s)',
        titleside: 'right',
        thickness: 20
      },
      hovertemplate:
        '位置: %{x:.1f} m<br>' +
        '时间: %{y:.2f} s<br>' +
        '流速: %{z:.3f} m/s<br>' +
        '<extra></extra>'
    }],
    layout: {
      title: '流速热力图 (Heatmap)',
      xaxis: {
        title: '位置 (m)',
        showgrid: false
      },
      yaxis: {
        title: '时间 (s)',
        showgrid: false
      },
      height: 500,
      margin: { t: 50, r: 100, b: 50, l: 60 },
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff'
    }
  }), [x, time, V, colorScale]);

  // Time Series at Selected Location
  const timeSeriesPlot = useMemo(() => ({
    data: [
      {
        x: time,
        y: h.map(frame => frame[selectedLocation]),
        type: 'scatter',
        mode: 'lines+markers',
        name: '水深',
        line: { color: '#1890ff', width: 2 },
        marker: { size: 4 },
        yaxis: 'y1'
      },
      {
        x: time,
        y: V.map(frame => frame[selectedLocation]),
        type: 'scatter',
        mode: 'lines+markers',
        name: '流速',
        line: { color: '#52c41a', width: 2 },
        marker: { size: 4 },
        yaxis: 'y2'
      },
      {
        x: time,
        y: Q.map(frame => frame[selectedLocation]),
        type: 'scatter',
        mode: 'lines+markers',
        name: '流量',
        line: { color: '#fa8c16', width: 2 },
        marker: { size: 4 },
        yaxis: 'y3'
      }
    ],
    layout: {
      title: `位置 x = ${x[selectedLocation].toFixed(1)} m 的时间序列`,
      xaxis: {
        title: '时间 (s)',
        showgrid: true,
        domain: [0, 1]
      },
      yaxis: {
        title: '水深 (m)',
        titlefont: { color: '#1890ff' },
        tickfont: { color: '#1890ff' },
        side: 'left',
        showgrid: true,
        position: 0
      },
      yaxis2: {
        title: '流速 (m/s)',
        titlefont: { color: '#52c41a' },
        tickfont: { color: '#52c41a' },
        anchor: 'free',
        overlaying: 'y',
        side: 'right',
        position: 0.85
      },
      yaxis3: {
        title: '流量 (m³/s)',
        titlefont: { color: '#fa8c16' },
        tickfont: { color: '#fa8c16' },
        anchor: 'free',
        overlaying: 'y',
        side: 'right',
        position: 1
      },
      height: 500,
      margin: { t: 50, r: 120, b: 50, l: 60 },
      legend: {
        x: 0.5,
        y: 1.15,
        xanchor: 'center',
        yanchor: 'top',
        orientation: 'h'
      },
      hovermode: 'x unified',
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff'
    }
  }), [time, h, V, Q, selectedLocation, x]);

  // Statistical Evolution Plot
  const statisticsPlot = useMemo(() => ({
    data: [
      {
        x: time,
        y: statistics.maxDepth,
        type: 'scatter',
        mode: 'lines',
        name: '最大水深',
        line: { color: '#1890ff', width: 2 }
      },
      {
        x: time,
        y: statistics.meanDepth,
        type: 'scatter',
        mode: 'lines',
        name: '平均水深',
        line: { color: '#1890ff', width: 2, dash: 'dash' }
      },
      {
        x: time,
        y: statistics.maxVelocity,
        type: 'scatter',
        mode: 'lines',
        name: '最大流速',
        line: { color: '#52c41a', width: 2 },
        yaxis: 'y2'
      },
      {
        x: time,
        y: statistics.meanVelocity,
        type: 'scatter',
        mode: 'lines',
        name: '平均流速',
        line: { color: '#52c41a', width: 2, dash: 'dash' },
        yaxis: 'y2'
      }
    ],
    layout: {
      title: '统计量时间演化',
      xaxis: {
        title: '时间 (s)',
        showgrid: true
      },
      yaxis: {
        title: '水深 (m)',
        titlefont: { color: '#1890ff' },
        tickfont: { color: '#1890ff' },
        side: 'left',
        showgrid: true
      },
      yaxis2: {
        title: '流速 (m/s)',
        titlefont: { color: '#52c41a' },
        tickfont: { color: '#52c41a' },
        overlaying: 'y',
        side: 'right'
      },
      height: 400,
      margin: { t: 50, r: 80, b: 50, l: 60 },
      legend: {
        x: 0.5,
        y: 1.15,
        xanchor: 'center',
        yanchor: 'top',
        orientation: 'h'
      },
      hovermode: 'x unified',
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff'
    }
  }), [time, statistics]);

  // Discharge Heatmap
  const dischargeHeatmap = useMemo(() => ({
    data: [{
      type: 'heatmap',
      x: x,
      y: time,
      z: Q,
      colorscale: 'Portland',
      colorbar: {
        title: '流量 (m³/s)',
        titleside: 'right',
        thickness: 20
      },
      hovertemplate:
        '位置: %{x:.1f} m<br>' +
        '时间: %{y:.2f} s<br>' +
        '流量: %{z:.3f} m³/s<br>' +
        '<extra></extra>'
    }],
    layout: {
      title: '流量热力图',
      xaxis: {
        title: '位置 (m)',
        showgrid: false
      },
      yaxis: {
        title: '时间 (s)',
        showgrid: false
      },
      height: 500,
      margin: { t: 50, r: 100, b: 50, l: 60 },
      plot_bgcolor: '#fafafa',
      paper_bgcolor: '#ffffff'
    }
  }), [x, time, Q]);

  const colorScaleOptions = [
    { label: 'Viridis', value: 'Viridis' },
    { label: 'Jet', value: 'Jet' },
    { label: 'Hot', value: 'Hot' },
    { label: 'Cool', value: 'Cool' },
    { label: 'RdBu', value: 'RdBu' },
    { label: 'Portland', value: 'Portland' }
  ];

  const tabItems = [
    {
      key: 'contour',
      label: '📊 等值线图',
      children: (
        <div>
          <Space style={{ marginBottom: 12 }}>
            <Text>配色方案:</Text>
            <Select
              value={colorScale}
              onChange={setColorScale}
              options={colorScaleOptions}
              style={{ width: 120 }}
              size="small"
            />
          </Space>
          <Plot
            data={contourPlot.data as any}
            layout={contourPlot.layout as any}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%' }}
          />
        </div>
      )
    },
    {
      key: 'heatmap',
      label: '🔥 热力图',
      children: (
        <div>
          <Space style={{ marginBottom: 12 }}>
            <Text>配色方案:</Text>
            <Select
              value={colorScale}
              onChange={setColorScale}
              options={colorScaleOptions}
              style={{ width: 120 }}
              size="small"
            />
          </Space>
          <Plot
            data={heatmapPlot.data as any}
            layout={heatmapPlot.layout as any}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%' }}
          />
        </div>
      )
    },
    {
      key: 'discharge',
      label: '💧 流量热力图',
      children: (
        <Plot
          data={dischargeHeatmap.data as any}
          layout={dischargeHeatmap.layout as any}
          config={{ responsive: true, displaylogo: false }}
          style={{ width: '100%' }}
        />
      )
    },
    {
      key: 'timeseries',
      label: '📈 时间序列',
      children: (
        <div>
          <div style={{ marginBottom: 12, padding: 12, background: '#f0f0f0', borderRadius: 4 }}>
            <Row gutter={16} align="middle">
              <Col span={6}>
                <Text strong>选择监测点:</Text>
              </Col>
              <Col span={18}>
                <Slider
                  min={0}
                  max={x.length - 1}
                  value={selectedLocation}
                  onChange={setSelectedLocation}
                  marks={{
                    0: `${x[0].toFixed(0)}m`,
                    [Math.floor(x.length / 2)]: `${x[Math.floor(x.length / 2)].toFixed(0)}m`,
                    [x.length - 1]: `${x[x.length - 1].toFixed(0)}m`
                  }}
                  tooltip={{
                    formatter: (value) => `位置: ${x[value || 0].toFixed(1)} m`
                  }}
                />
              </Col>
            </Row>
          </div>
          <Plot
            data={timeSeriesPlot.data as any}
            layout={timeSeriesPlot.layout as any}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%' }}
          />
        </div>
      )
    },
    {
      key: 'statistics',
      label: '📊 统计分析',
      children: (
        <div>
          <Plot
            data={statisticsPlot.data as any}
            layout={statisticsPlot.layout as any}
            config={{ responsive: true, displaylogo: false }}
            style={{ width: '100%' }}
          />
          <div style={{ marginTop: 12, padding: 12, background: '#f0f0f0', borderRadius: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              💡 此图显示整个模拟域的最大值和平均值随时间的演化。实线表示最大值，虚线表示平均值。
            </Text>
          </div>
        </div>
      )
    }
  ];

  return (
    <Card
      title={
        <Space>
          <Text strong>增强可视化</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            (等值线、热力图、时间序列、统计分析)
          </Text>
        </Space>
      }
      size="small"
    >
      <Tabs items={tabItems} defaultActiveKey="contour" />
    </Card>
  );
};

export default EnhancedCharts;
