import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { Card, Select, Space, Typography, Button, Tooltip } from 'antd';
import {
  RotateLeftOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  BorderOutlined
} from '@ant-design/icons';

const { Text } = Typography;

interface Plot3DProps {
  x: number[];        // Spatial positions
  time: number[];     // Time points
  h: number[][];      // Water depth [time][space]
  title?: string;
  variable?: 'h' | 'V' | 'Q';
  V?: number[][];     // Velocity (optional)
  Q?: number[][];     // Discharge (optional)
}

type ColorScale =
  | 'Viridis'
  | 'Jet'
  | 'Hot'
  | 'Cool'
  | 'Rainbow'
  | 'Portland'
  | 'Blackbody'
  | 'Earth'
  | 'Electric'
  | 'Bluered';

type SurfaceMode = 'surface' | 'wireframe' | 'both';

/**
 * Plot3D Component
 *
 * Renders interactive 3D surface plot of simulation data:
 * - Water depth/velocity/discharge as Z-axis
 * - Position as X-axis
 * - Time as Y-axis
 * - Color-coded by magnitude
 * - Interactive rotation, zoom, and pan
 *
 * Features:
 * - Multiple color schemes
 * - Surface/wireframe toggle
 * - Camera control
 * - Export functionality (via Plotly controls)
 *
 * @param x - Array of spatial positions (m)
 * @param time - Array of time points (s)
 * @param h - 2D array of water depth [time][space]
 * @param title - Plot title
 * @param variable - Variable to plot ('h', 'V', 'Q')
 * @param V - Velocity data (optional)
 * @param Q - Discharge data (optional)
 */
const Plot3D = ({
  x,
  time,
  h,
  title = '3D水深演化',
  variable = 'h',
  V,
  Q
}: Plot3DProps) => {
  const [colorScale, setColorScale] = useState<ColorScale>('Viridis');
  const [surfaceMode, setSurfaceMode] = useState<SurfaceMode>('surface');
  const [cameraKey, setCameraKey] = useState(0);

  // Select data based on variable
  const data = useMemo(() => {
    switch (variable) {
      case 'V':
        return V || h;
      case 'Q':
        return Q || h;
      default:
        return h;
    }
  }, [variable, h, V, Q]);

  // Variable metadata
  const variableInfo = useMemo(() => {
    const info = {
      'h': { label: '水深', unit: 'm', title: '3D水深演化' },
      'V': { label: '流速', unit: 'm/s', title: '3D流速演化' },
      'Q': { label: '流量', unit: 'm³/s', title: '3D流量演化' }
    };
    return info[variable];
  }, [variable]);

  // Prepare 3D plot data
  const plot3DData = useMemo(() => {
    const traces: any[] = [];

    // Surface trace
    if (surfaceMode === 'surface' || surfaceMode === 'both') {
      traces.push({
        type: 'surface',
        x: x,
        y: time,
        z: data,
        colorscale: colorScale,
        showscale: true,
        colorbar: {
          title: {
            text: `${variableInfo.label}<br>(${variableInfo.unit})`,
            side: 'right'
          },
          thickness: 20,
          len: 0.7
        },
        opacity: surfaceMode === 'both' ? 0.8 : 1.0,
        contours: {
          z: {
            show: true,
            usecolormap: true,
            highlightcolor: 'limegreen',
            project: { z: true }
          }
        },
        name: '表面'
      });
    }

    // Wireframe trace
    if (surfaceMode === 'wireframe' || surfaceMode === 'both') {
      traces.push({
        type: 'surface',
        x: x,
        y: time,
        z: data,
        colorscale: colorScale,
        showscale: surfaceMode === 'wireframe',
        colorbar: {
          title: {
            text: `${variableInfo.label}<br>(${variableInfo.unit})`,
            side: 'right'
          },
          thickness: 20,
          len: 0.7
        },
        opacity: surfaceMode === 'wireframe' ? 1.0 : 0.5,
        hidesurface: surfaceMode === 'wireframe',
        contours: {
          x: { show: true, color: '#ffffff', width: 2 },
          y: { show: true, color: '#ffffff', width: 2 },
          z: { show: true, color: '#ffffff', width: 2 }
        },
        name: '网格'
      });
    }

    return traces;
  }, [x, time, data, colorScale, surfaceMode, variableInfo]);

  const layout = useMemo(() => ({
    title: {
      text: title || variableInfo.title,
      font: { size: 16 }
    },
    scene: {
      xaxis: {
        title: { text: '位置 (m)' },
        backgroundcolor: 'rgb(230, 230,230)',
        gridcolor: 'rgb(255, 255, 255)',
        showbackground: true,
        zerolinecolor: 'rgb(255, 255, 255)'
      },
      yaxis: {
        title: { text: '时间 (s)' },
        backgroundcolor: 'rgb(230, 230,230)',
        gridcolor: 'rgb(255, 255, 255)',
        showbackground: true,
        zerolinecolor: 'rgb(255, 255, 255)'
      },
      zaxis: {
        title: { text: `${variableInfo.label} (${variableInfo.unit})` },
        backgroundcolor: 'rgb(230, 230,230)',
        gridcolor: 'rgb(255, 255, 255)',
        showbackground: true,
        zerolinecolor: 'rgb(255, 255, 255)'
      },
      camera: {
        eye: { x: 1.5, y: 1.5, z: 1.3 },
        center: { x: 0, y: 0, z: 0 },
        up: { x: 0, y: 0, z: 1 }
      },
      aspectmode: 'auto'
    },
    height: 600,
    margin: { t: 50, r: 20, b: 20, l: 20 },
    autosize: true,
    hovermode: 'closest',
    paper_bgcolor: '#fafafa',
    plot_bgcolor: '#fafafa'
  }), [title, variableInfo]);

  const config = useMemo(() => ({
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['toImage'],
    modeBarButtonsToAdd: [
      {
        name: 'Reset Camera',
        icon: {
          width: 1000,
          height: 1000,
          path: 'M500 100 L900 500 L500 900 L100 500 Z',
          transform: 'matrix(1 0 0 -1 0 850)'
        },
        click: function(gd: any) {
          const update = {
            'scene.camera': {
              eye: { x: 1.5, y: 1.5, z: 1.3 },
              center: { x: 0, y: 0, z: 0 },
              up: { x: 0, y: 0, z: 1 }
            }
          };
          (window as any).Plotly.relayout(gd, update);
        }
      }
    ]
  }), []);

  const handleResetCamera = () => {
    // Force re-render to reset camera
    setCameraKey(prev => prev + 1);
  };

  const colorScaleOptions = [
    { label: 'Viridis (默认)', value: 'Viridis' },
    { label: 'Jet (彩虹)', value: 'Jet' },
    { label: 'Hot (热力)', value: 'Hot' },
    { label: 'Cool (冷色)', value: 'Cool' },
    { label: 'Rainbow (彩虹2)', value: 'Rainbow' },
    { label: 'Portland', value: 'Portland' },
    { label: 'Blackbody (黑体)', value: 'Blackbody' },
    { label: 'Earth (地球)', value: 'Earth' },
    { label: 'Electric (电力)', value: 'Electric' },
    { label: 'Bluered (蓝红)', value: 'Bluered' }
  ];

  const surfaceModeOptions = [
    { label: '表面', value: 'surface' },
    { label: '网格', value: 'wireframe' },
    { label: '表面+网格', value: 'both' }
  ];

  return (
    <Card
      title={
        <Space>
          <Text strong>{title || variableInfo.title}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            ({x.length} 点 × {time.length} 时间步)
          </Text>
        </Space>
      }
      size="small"
      extra={
        <Space>
          <Tooltip title="重置相机视角">
            <Button
              icon={<RotateLeftOutlined />}
              onClick={handleResetCamera}
              size="small"
            >
              重置视角
            </Button>
          </Tooltip>
        </Space>
      }
    >
      {/* Controls */}
      <Space wrap style={{ marginBottom: 12, width: '100%' }}>
        <Space>
          <Text>配色方案:</Text>
          <Select
            value={colorScale}
            onChange={setColorScale}
            options={colorScaleOptions}
            style={{ width: 150 }}
            size="small"
            aria-label="配色方案"
          />
        </Space>

        <Space>
          <Text>显示模式:</Text>
          <Select
            value={surfaceMode}
            onChange={setSurfaceMode}
            options={surfaceModeOptions}
            style={{ width: 130 }}
            size="small"
            aria-label="显示模式"
          />
        </Space>
      </Space>

      {/* 3D Plot */}
      <Plot
        key={cameraKey}
        data={plot3DData}
        layout={layout as any}
        config={config}
        style={{ width: '100%' }}
      />

      {/* Help Text */}
      <div style={{ marginTop: 8, padding: 8, background: '#f0f0f0', borderRadius: 4 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          💡 提示: 拖动旋转视角，滚轮缩放，双击重置。点击上方"重置视角"按钮恢复默认视角。
        </Text>
      </div>
    </Card>
  );
};

export default Plot3D;
