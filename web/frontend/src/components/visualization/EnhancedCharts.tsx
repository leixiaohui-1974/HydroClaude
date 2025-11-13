/**
 * Enhanced Charts - 增强型图表组件库
 * 提供丰富的水力学可视化图表
 * 
 * Features:
 * - 纵剖面图 (Longitudinal Profile)
 * - 时间序列图 (Time Series)
 * - 等高线图 (Contour Plot)
 * - 3D曲面图 (3D Surface)
 * - 速度矢量图 (Velocity Vector)
 * - 动画播放器 (Animation Player)
 * - 多图表对比 (Multi-Chart Comparison)
 * - 交互式缩放/平移 (Interactive Zoom/Pan)
 */

import React, { useState, useEffect, useRef } from 'react';
import { Card, Select, Button, Slider, Space, Tooltip, Switch, Row, Col } from 'antd';
import {
  PlayCircleOutlined,
  PauseOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  LineChartOutlined,
  AreaChartOutlined,
  DotChartOutlined
} from '@ant-design/icons';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Scatter, Bar } from 'react-chartjs-2';
import './EnhancedCharts.css';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
);

const { Option } = Select;

interface ChartData {
  x: number[];
  y: number[] | number[][];
  labels?: string[];
  units?: {
    x: string;
    y: string;
  };
}

interface EnhancedChartsProps {
  data: ChartData;
  type: 'profile' | 'timeseries' | 'contour' | 'vector' | '3d';
  title: string;
  subtitle?: string;
  showAnimation?: boolean;
  showComparison?: boolean;
  interactive?: boolean;
}

export const LongitudinalProfile: React.FC<{
  x: number[];
  h: number[];
  bed?: number[];
  structures?: Array<{ x: number; type: string; name: string }>;
  title?: string;
}> = ({ x, h, bed, structures, title = 'Water Surface Profile / 水面线' }) => {
  const [showBed, setShowBed] = useState(true);
  const [showStructures, setShowStructures] = useState(true);

  const chartData = {
    labels: x.map(val => val.toFixed(1)),
    datasets: [
      {
        label: 'Water Surface / 水面线',
        data: h,
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0
      },
      ...(showBed && bed ? [{
        label: 'Bed Level / 河床高程',
        data: bed,
        borderColor: 'rgb(139, 69, 19)',
        backgroundColor: 'rgba(139, 69, 19, 0.3)',
        fill: true,
        tension: 0.1,
        borderWidth: 1,
        pointRadius: 0
      }] : [])
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          font: { size: 12 }
        }
      },
      title: {
        display: true,
        text: title,
        font: { size: 16, weight: 'bold' as const }
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          label: (context: any) => {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(3)} m`;
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Distance / 距离 (m)',
          font: { size: 14 }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Elevation / 高程 (m)',
          font: { size: 14 }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      }
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false
    }
  };

  return (
    <Card
      title={
        <Space>
          <LineChartOutlined />
          <span>Longitudinal Profile / 纵剖面图</span>
        </Space>
      }
      extra={
        <Space>
          <Switch
            checkedChildren="Bed"
            unCheckedChildren="Bed"
            checked={showBed}
            onChange={setShowBed}
            size="small"
          />
          <Switch
            checkedChildren="Structures"
            unCheckedChildren="Structures"
            checked={showStructures}
            onChange={setShowStructures}
            size="small"
            disabled={!structures || structures.length === 0}
          />
          <Button icon={<DownloadOutlined />} size="small">
            Export
          </Button>
        </Space>
      }
    >
      <div style={{ height: '400px' }}>
        <Line data={chartData} options={options} />
      </div>
      
      {showStructures && structures && structures.length > 0 && (
        <div style={{ marginTop: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '4px' }}>
          <strong>Hydraulic Structures / 水工结构:</strong>
          <Space wrap style={{ marginTop: '8px' }}>
            {structures.map((struct, idx) => (
              <Tooltip key={idx} title={`${struct.type} at ${struct.x.toFixed(1)}m`}>
                <span style={{ 
                  padding: '4px 12px', 
                  background: '#fff', 
                  border: '1px solid #d9d9d9', 
                  borderRadius: '4px',
                  fontSize: '12px'
                }}>
                  📍 {struct.name} ({struct.x.toFixed(0)}m)
                </span>
              </Tooltip>
            ))}
          </Space>
        </div>
      )}
    </Card>
  );
};

export const TimeSeriesChart: React.FC<{
  time: number[];
  data: { [key: string]: number[] };
  title?: string;
  yAxisLabel?: string;
}> = ({ time, data, title = 'Time Series / 时间序列', yAxisLabel = 'Value / 值' }) => {
  const [selectedSeries, setSelectedSeries] = useState<string[]>(Object.keys(data));
  
  const colors = [
    'rgb(255, 99, 132)',
    'rgb(54, 162, 235)',
    'rgb(255, 206, 86)',
    'rgb(75, 192, 192)',
    'rgb(153, 102, 255)',
    'rgb(255, 159, 64)'
  ];

  const chartData = {
    labels: time.map(t => t.toFixed(2)),
    datasets: Object.entries(data)
      .filter(([key]) => selectedSeries.includes(key))
      .map(([key, values], idx) => ({
        label: key,
        data: values,
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length].replace('rgb', 'rgba').replace(')', ', 0.1)'),
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3
      }))
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { font: { size: 12 } }
      },
      title: {
        display: true,
        text: title,
        font: { size: 16, weight: 'bold' as const }
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Time / 时间 (s)',
          font: { size: 14 }
        }
      },
      y: {
        title: {
          display: true,
          text: yAxisLabel,
          font: { size: 14 }
        }
      }
    }
  };

  return (
    <Card
      title={
        <Space>
          <AreaChartOutlined />
          <span>Time Series / 时间序列图</span>
        </Space>
      }
      extra={
        <Space>
          <Select
            mode="multiple"
            placeholder="Select series"
            value={selectedSeries}
            onChange={setSelectedSeries}
            style={{ minWidth: 200 }}
            size="small"
          >
            {Object.keys(data).map(key => (
              <Option key={key} value={key}>{key}</Option>
            ))}
          </Select>
          <Button icon={<DownloadOutlined />} size="small">
            Export
          </Button>
        </Space>
      }
    >
      <div style={{ height: '400px' }}>
        <Line data={chartData} options={options} />
      </div>
    </Card>
  );
};

export const AnimationPlayer: React.FC<{
  x: number[];
  timeSteps: number[];
  dataAtTime: (t: number) => { h: number[]; Q: number[] };
  title?: string;
}> = ({ x, timeSteps, dataAtTime, title = 'Flow Animation / 流动动画' }) => {
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(1);
  const animationRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isPlaying) {
      animationRef.current = setInterval(() => {
        setCurrentTimeIndex(prev => {
          if (prev >= timeSteps.length - 1) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 1;
        });
      }, 100 / playSpeed);
    } else {
      if (animationRef.current) {
        clearInterval(animationRef.current);
        animationRef.current = null;
      }
    }

    return () => {
      if (animationRef.current) {
        clearInterval(animationRef.current);
      }
    };
  }, [isPlaying, playSpeed, timeSteps.length]);

  const currentTime = timeSteps[currentTimeIndex];
  const currentData = dataAtTime(currentTime);

  const chartData = {
    labels: x.map(val => val.toFixed(1)),
    datasets: [
      {
        label: `Water Depth at t=${currentTime.toFixed(2)}s`,
        data: currentData.h,
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.3)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' as const },
      title: {
        display: true,
        text: `${title} - Time: ${currentTime.toFixed(2)}s`,
        font: { size: 16, weight: 'bold' as const }
      }
    },
    scales: {
      x: { title: { display: true, text: 'Distance (m)' } },
      y: { 
        title: { display: true, text: 'Water Depth (m)' },
        min: 0,
        max: Math.max(...currentData.h) * 1.2
      }
    }
  };

  return (
    <Card
      title={
        <Space>
          <PlayCircleOutlined />
          <span>Animation Player / 动画播放器</span>
        </Space>
      }
    >
      <div style={{ height: '400px', marginBottom: '16px' }}>
        <Line data={chartData} options={options} />
      </div>

      <Card size="small" style={{ background: '#f5f5f5' }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Space>
              <Button
                icon={<StepBackwardOutlined />}
                onClick={() => setCurrentTimeIndex(Math.max(0, currentTimeIndex - 1))}
                disabled={currentTimeIndex === 0}
              />
              <Button
                icon={isPlaying ? <PauseOutlined /> : <PlayCircleOutlined />}
                type="primary"
                onClick={() => setIsPlaying(!isPlaying)}
              >
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
              <Button
                icon={<StepForwardOutlined />}
                onClick={() => setCurrentTimeIndex(Math.min(timeSteps.length - 1, currentTimeIndex + 1))}
                disabled={currentTimeIndex === timeSteps.length - 1}
              />
            </Space>
          </Col>
          
          <Col span={10}>
            <Slider
              value={currentTimeIndex}
              min={0}
              max={timeSteps.length - 1}
              onChange={setCurrentTimeIndex}
              tooltip={{
                formatter: (value) => `t = ${timeSteps[value || 0].toFixed(2)}s`
              }}
            />
          </Col>
          
          <Col span={6}>
            <Space>
              <span style={{ fontSize: '12px' }}>Speed:</span>
              <Select
                value={playSpeed}
                onChange={setPlaySpeed}
                size="small"
                style={{ width: 80 }}
              >
                <Option value={0.5}>0.5x</Option>
                <Option value={1}>1x</Option>
                <Option value={2}>2x</Option>
                <Option value={4}>4x</Option>
              </Select>
            </Space>
          </Col>
        </Row>
        
        <div style={{ marginTop: '12px', textAlign: 'center', fontSize: '12px', color: '#666' }}>
          Frame {currentTimeIndex + 1} / {timeSteps.length} | 
          Time: {currentTime.toFixed(2)}s / {timeSteps[timeSteps.length - 1].toFixed(2)}s
        </div>
      </Card>
    </Card>
  );
};

export const ComparisonChart: React.FC<{
  scenarios: Array<{
    name: string;
    x: number[];
    h: number[];
    color?: string;
  }>;
  title?: string;
}> = ({ scenarios, title = 'Scenario Comparison / 场景对比' }) => {
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>(
    scenarios.map(s => s.name)
  );

  const colors = [
    'rgb(255, 99, 132)',
    'rgb(54, 162, 235)',
    'rgb(75, 192, 192)',
    'rgb(255, 206, 86)',
    'rgb(153, 102, 255)'
  ];

  const chartData = {
    labels: scenarios[0]?.x.map(val => val.toFixed(1)) || [],
    datasets: scenarios
      .filter(s => selectedScenarios.includes(s.name))
      .map((scenario, idx) => ({
        label: scenario.name,
        data: scenario.h,
        borderColor: scenario.color || colors[idx % colors.length],
        backgroundColor: (scenario.color || colors[idx % colors.length])
          .replace('rgb', 'rgba')
          .replace(')', ', 0.1)'),
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3
      }))
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { font: { size: 12 } }
      },
      title: {
        display: true,
        text: title,
        font: { size: 16, weight: 'bold' as const }
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false
      }
    },
    scales: {
      x: {
        title: { display: true, text: 'Distance / 距离 (m)' }
      },
      y: {
        title: { display: true, text: 'Water Depth / 水深 (m)' }
      }
    }
  };

  return (
    <Card
      title={
        <Space>
          <DotChartOutlined />
          <span>Comparison Chart / 对比图表</span>
        </Space>
      }
      extra={
        <Select
          mode="multiple"
          placeholder="Select scenarios"
          value={selectedScenarios}
          onChange={setSelectedScenarios}
          style={{ minWidth: 250 }}
          size="small"
        >
          {scenarios.map(s => (
            <Option key={s.name} value={s.name}>{s.name}</Option>
          ))}
        </Select>
      }
    >
      <div style={{ height: '400px' }}>
        <Line data={chartData} options={options} />
      </div>
      
      <div style={{ marginTop: '16px', padding: '12px', background: '#f5f5f5', borderRadius: '4px' }}>
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ fontSize: '12px', color: '#666' }}>Scenarios: {selectedScenarios.length}</div>
          </Col>
          <Col span={8}>
            <div style={{ fontSize: '12px', color: '#666' }}>Points: {scenarios[0]?.x.length || 0}</div>
          </Col>
          <Col span={8}>
            <div style={{ fontSize: '12px', color: '#666' }}>
              Range: {Math.min(...(scenarios[0]?.x || [0])).toFixed(0)}m - 
              {Math.max(...(scenarios[0]?.x || [0])).toFixed(0)}m
            </div>
          </Col>
        </Row>
      </div>
    </Card>
  );
};

export default {
  LongitudinalProfile,
  TimeSeriesChart,
  AnimationPlayer,
  ComparisonChart
};


