import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { Card, Empty } from 'antd';
import { useTranslation } from 'react-i18next';

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
  title,
  height = 400,
  showVelocity = false,
}) => {
  const { t } = useTranslation();
  const chartTitle = title || t('chart.waterProfile');

  const plotData = useMemo(() => {
    if (!data || !data.positions || data.positions.length === 0) {
      return [];
    }

    const traces: any[] = [];

    if (data.bottom_elevation) {
      traces.push({
        x: data.positions,
        y: data.bottom_elevation,
        type: 'scatter',
        mode: 'lines',
        name: t('chart.bottomElevation'),
        line: { color: '#8B4513', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(139, 69, 19, 0.3)',
      });
    }

    if (data.water_surface) {
      traces.push({
        x: data.positions,
        y: data.water_surface,
        type: 'scatter',
        mode: 'lines',
        name: t('chart.waterSurface'),
        line: { color: '#1890ff', width: 3 },
      });
    } else {
      traces.push({
        x: data.positions,
        y: data.depths,
        type: 'scatter',
        mode: 'lines',
        name: t('chart.waterDepth'),
        line: { color: '#1890ff', width: 3 },
      });
    }

    if (showVelocity && data.velocities) {
      traces.push({
        x: data.positions,
        y: data.velocities,
        type: 'scatter',
        mode: 'lines',
        name: t('chart.velocity'),
        line: { color: '#52c41a', width: 2, dash: 'dash' },
        yaxis: 'y2',
      });
    }

    return traces;
  }, [data, showVelocity, t]);

  const layout = useMemo(() => {
    const baseLayout: any = {
      title: {
        text: chartTitle,
        font: { size: 16, family: 'Arial, sans-serif' },
      },
      xaxis: {
        title: t('chart.distanceM'),
        gridcolor: '#e8e8e8',
        showgrid: true,
      },
      yaxis: {
        title: data.water_surface ? t('chart.elevationM') : t('chart.depthM'),
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

    if (showVelocity && data.velocities) {
      baseLayout.yaxis2 = {
        title: t('chart.velocityMs'),
        overlaying: 'y',
        side: 'right',
        gridcolor: '#e8e8e8',
        showgrid: false,
      };
    }

    return baseLayout;
  }, [chartTitle, showVelocity, data, t]);

  if (!data || !data.positions || data.positions.length === 0) {
    return (
      <Card>
        <Empty description={t('chart.noData')} />
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
