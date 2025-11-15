import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { Card, Empty } from 'antd';

interface WaterProfileData {
  positions: number[];
  depths: number[];
  velocities?: number[];
  bottom_elevation?: number[];
  water_surface?: number[];
}

interface WaterProfileChartProps {
  data: WaterProfileData;
  title?: string;
  height?: number;
  showVelocity?: boolean;
}

const WaterProfileChart: React.FC<WaterProfileChartProps> = ({
  data,
  title = '水位剖面图',
  height = 400,
  showVelocity = false,
}) => {
  const plotData = useMemo(() => {
    if (!data || !data.positions || data.positions.length === 0) {
      return [];
    }

    const traces: any[] = [];

    // 底部高程（如果有）
    if (data.bottom_elevation) {
      traces.push({
        x: data.positions,
        y: data.bottom_elevation,
        type: 'scatter',
        mode: 'lines',
        name: '渠底高程',
        line: { color: '#8B4513', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(139, 69, 19, 0.3)',
      });
    }

    // 水面线
    if (data.water_surface) {
      traces.push({
        x: data.positions,
        y: data.water_surface,
        type: 'scatter',
        mode: 'lines',
        name: '水面线',
        line: { color: '#1890ff', width: 3 },
      });
    } else {
      // 如果没有水面线，用深度绘制
      traces.push({
        x: data.positions,
        y: data.depths,
        type: 'scatter',
        mode: 'lines',
        name: '水深',
        line: { color: '#1890ff', width: 3 },
      });
    }

    // 流速（如果需要显示）
    if (showVelocity && data.velocities) {
      traces.push({
        x: data.positions,
        y: data.velocities,
        type: 'scatter',
        mode: 'lines',
        name: '流速',
        line: { color: '#52c41a', width: 2, dash: 'dash' },
        yaxis: 'y2',
      });
    }

    return traces;
  }, [data, showVelocity]);

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
        title: data.water_surface ? '高程 (m)' : '水深 (m)',
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
    };

    // 如果显示流速，添加第二个y轴
    if (showVelocity && data.velocities) {
      baseLayout.yaxis2 = {
        title: '流速 (m/s)',
        overlaying: 'y',
        side: 'right',
        gridcolor: '#e8e8e8',
        showgrid: false,
      };
    }

    return baseLayout;
  }, [title, showVelocity, data]);

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
          filename: 'water_profile',
          height: 800,
          width: 1200,
          scale: 2,
        },
      }}
      style={{ width: '100%', height }}
    />
  );
};

export default WaterProfileChart;
