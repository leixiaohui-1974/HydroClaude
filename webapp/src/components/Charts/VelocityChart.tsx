import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { Card, Empty } from 'antd';

interface VelocityData {
  positions: number[];
  velocities: number[];
  froude_numbers?: number[];
}

interface VelocityChartProps {
  data: VelocityData;
  title?: string;
  height?: number;
  showFroude?: boolean;
}

const VelocityChart: React.FC<VelocityChartProps> = ({
  data,
  title = '流速分布图',
  height = 400,
  showFroude = true,
}) => {
  const plotData = useMemo(() => {
    if (!data || !data.positions || data.positions.length === 0) {
      return [];
    }

    const traces: any[] = [];

    // 流速曲线
    traces.push({
      x: data.positions,
      y: data.velocities,
      type: 'scatter',
      mode: 'lines+markers',
      name: '流速',
      line: { color: '#52c41a', width: 3 },
      marker: { size: 6, color: '#52c41a' },
    });

    // Froude数曲线（如果有）
    if (showFroude && data.froude_numbers) {
      traces.push({
        x: data.positions,
        y: data.froude_numbers,
        type: 'scatter',
        mode: 'lines',
        name: 'Froude数',
        line: { color: '#ff7875', width: 2, dash: 'dash' },
        yaxis: 'y2',
      });

      // 临界线 (Fr = 1)
      traces.push({
        x: [data.positions[0], data.positions[data.positions.length - 1]],
        y: [1, 1],
        type: 'scatter',
        mode: 'lines',
        name: '临界流 (Fr=1)',
        line: { color: '#faad14', width: 1, dash: 'dot' },
        yaxis: 'y2',
        showlegend: true,
      });
    }

    return traces;
  }, [data, showFroude]);

  const layout = useMemo(() => {
    const baseLayout: any = {
      title: {
        text: title,
        font: { size: 16, family: 'Arial, sans-serif' },
      },
      xaxis: {
        title: '距离 (m)',
        gridcolor: '#e8e8e8',
        showgrid: true,
      },
      yaxis: {
        title: '流速 (m/s)',
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
      margin: { l: 60, r: 80, t: 60, b: 60 },
      plot_bgcolor: '#fafafa',
      paper_bgcolor: 'white',
    };

    // 如果显示Froude数，添加第二个y轴
    if (showFroude && data.froude_numbers) {
      baseLayout.yaxis2 = {
        title: 'Froude数',
        overlaying: 'y',
        side: 'right',
        gridcolor: '#e8e8e8',
        showgrid: false,
      };
    }

    return baseLayout;
  }, [title, showFroude, data]);

  if (!data || !data.positions || data.positions.length === 0) {
    return (
      <Card>
        <Empty description="暂无数据" />
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
          filename: 'velocity_profile',
          height: 800,
          width: 1200,
          scale: 2,
        },
      }}
      style={{ width: '100%', height }}
    />
  );
};

export default VelocityChart;
