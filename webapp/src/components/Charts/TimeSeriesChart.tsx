import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { Card, Empty } from 'antd';

interface TimeSeriesData {
  times: number[];
  values: number[][];
  positions?: number[];
  variable_name?: string;
}

interface TimeSeriesChartProps {
  data: TimeSeriesData;
  title?: string;
  height?: number;
  selectedPositions?: number[];
}

const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  data,
  title = '时间序列图',
  height = 400,
  selectedPositions,
}) => {
  const plotData = useMemo(() => {
    if (!data || !data.times || data.times.length === 0) {
      return [];
    }

    const traces: any[] = [];
    const positions = selectedPositions || data.positions || [];
    
    // 为每个监测位置创建一条曲线
    positions.forEach((pos, idx) => {
      if (data.values[idx]) {
        traces.push({
          x: data.times,
          y: data.values[idx],
          type: 'scatter',
          mode: 'lines',
          name: `x = ${pos} m`,
          line: { width: 2 },
        });
      }
    });

    return traces;
  }, [data, selectedPositions]);

  const layout = useMemo(() => ({
    title: {
      text: title,
      font: { size: 16, family: 'Arial, sans-serif' },
    },
    xaxis: {
      title: '时间 (s)',
      gridcolor: '#e8e8e8',
      showgrid: true,
    },
    yaxis: {
      title: data.variable_name || '值',
      gridcolor: '#e8e8e8',
      showgrid: true,
    },
    hovermode: 'x unified',
    showlegend: true,
    legend: {
      x: 1,
      xanchor: 'right',
      y: 1,
      bgcolor: 'rgba(255, 255, 255, 0.8)',
      bordercolor: '#ddd',
      borderwidth: 1,
    },
    margin: { l: 60, r: 60, t: 60, b: 60 },
    plot_bgcolor: '#fafafa',
    paper_bgcolor: 'white',
  }), [title, data]);

  if (!data || !data.times || data.times.length === 0) {
    return (
      <Card>
        <Empty description="暂无时间序列数据" />
      </Card>
    );
  }

  return (
    <Plot
      data={plotData}
      layout={layout}
      config={{
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
        toImageButtonOptions: {
          format: 'png',
          filename: 'time_series',
          height: 800,
          width: 1200,
          scale: 2,
        },
      }}
      style={{ width: '100%', height }}
    />
  );
};

export default TimeSeriesChart;
