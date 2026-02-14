import React, { useState } from 'react';
import { Tabs, Card, Space, Button, Select, Switch, message } from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  TableOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import WaterProfileChart from '../Charts/WaterProfileChart';
import VelocityChart from '../Charts/VelocityChart';
import TimeSeriesChart from '../Charts/TimeSeriesChart';
import ResultsTable from '../DataTable/ResultsTable';
import AnimationPlayer from '../AnimationPlayer';

const { Option } = Select;

interface SimulationResults {
  metadata: {
    simulation_type: string;
    case_name: string;
    timestamp: string;
  };
  spatial: {
    positions: number[];
    depths: number[];
    velocities: number[];
    froude_numbers?: number[];
    discharge?: number[];
  };
  temporal?: {
    times: number[];
    depth_series: number[][];
    velocity_series: number[][];
  };
}

interface ResultsViewerProps {
  results: SimulationResults;
}

const ResultsViewer: React.FC<ResultsViewerProps> = ({ results }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('profile');
  const [currentFrame, setCurrentFrame] = useState(0);
  const [showVelocity, setShowVelocity] = useState(false);
  const [showFroude, setShowFroude] = useState(true);

  const isUnsteady = results.metadata.simulation_type === 'unsteady';

  const handleExportCSV = () => {
    const { positions, depths, velocities, froude_numbers, discharge } = results.spatial;
    const headers = ['Position(m)', 'Depth(m)', 'Velocity(m/s)'];
    if (froude_numbers) headers.push('Froude');
    if (discharge) headers.push('Discharge(m3/s)');

    const rows = positions.map((pos, i) => {
      const row = [pos, depths[i], velocities[i]];
      if (froude_numbers) row.push(froude_numbers[i]);
      if (discharge) row.push(discharge[i]);
      return row.join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `results_${results.metadata.case_name || 'data'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(t('results.dataExportedCSV'));
  };

  const handleDownloadReport = () => {
    const report = {
      metadata: results.metadata,
      summary: {
        total_points: results.spatial.positions.length,
        depth_range: [Math.min(...results.spatial.depths), Math.max(...results.spatial.depths)],
        velocity_range: [Math.min(...results.spatial.velocities), Math.max(...results.spatial.velocities)],
      },
      spatial: results.spatial,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${results.metadata.case_name || 'simulation'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(t('results.reportDownloaded'));
  };

  const tabItems = [
    {
      key: 'profile',
      label: (
        <span>
          <LineChartOutlined />
          {t('results.waterProfile')}
        </span>
      ),
      children: (
        <WaterProfileChart
          data={results.spatial}
          showVelocity={showVelocity}
          height={500}
        />
      ),
    },
    {
      key: 'velocity',
      label: (
        <span>
          <BarChartOutlined />
          {t('results.velocityDistribution')}
        </span>
      ),
      children: (
        <VelocityChart
          data={results.spatial}
          showFroude={showFroude}
          height={500}
        />
      ),
    },
    ...(isUnsteady && results.temporal
      ? [
          {
            key: 'timeseries',
            label: (
              <span>
                <PlayCircleOutlined />
                {t('results.timeSeries')}
              </span>
            ),
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Card size="small" type="inner">
                  <Space>
                    <span>{t('results.selectMonitoringPosition')}</span>
                    <Select
                      mode="multiple"
                      placeholder={t('results.selectPosition')}
                      style={{ width: 300 }}
                      defaultValue={[0, Math.floor(results.spatial.positions.length / 2)]}
                    >
                      {results.spatial.positions.map((pos, idx) => (
                        <Option key={idx} value={idx}>
                          x = {pos.toFixed(1)} m
                        </Option>
                      ))}
                    </Select>
                  </Space>
                </Card>

                <TimeSeriesChart
                  data={{
                    times: results.temporal!.times,
                    values: results.temporal!.depth_series,
                    positions: results.spatial.positions,
                    variable_name: t('results.waterDepthM'),
                  }}
                  title={t('results.waterDepthTimeSeries')}
                  height={450}
                />
              </Space>
            ),
          },
          {
            key: 'animation',
            label: (
              <span>
                <PlayCircleOutlined />
                {t('results.animation')}
              </span>
            ),
            children: (
              <AnimationPlayer
                totalFrames={results.temporal!.times.length}
                currentFrame={currentFrame}
                onFrameChange={setCurrentFrame}
                fps={10}
              >
                <WaterProfileChart
                  data={{
                    positions: results.spatial.positions,
                    depths: results.temporal!.depth_series.map(series => series[currentFrame] ?? 0),
                    velocities: results.temporal!.velocity_series?.map(series => series[currentFrame] ?? 0),
                  }}
                  title={t('results.timeLabel', { time: results.temporal!.times[currentFrame]?.toFixed(2) ?? '0' })}
                  showVelocity={showVelocity}
                  height={400}
                />
              </AnimationPlayer>
            ),
          },
        ]
      : []),
    {
      key: 'table',
      label: (
        <span>
          <TableOutlined />
          {t('results.dataTable')}
        </span>
      ),
      children: <ResultsTable data={results.spatial} />,
    },
  ];

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownloadReport}>
            {t('results.downloadReport')}
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExportCSV}>
            {t('results.exportAllData')}
          </Button>
          {isUnsteady && (
            <Button icon={<PlayCircleOutlined />} onClick={() => setActiveTab('animation')}>
              {t('results.generateAnimation')}
            </Button>
          )}
        </Space>

        <div style={{ float: 'right' }}>
          <Space>
            <span id="show-velocity-label">{t('results.showVelocity')}:</span>
            <Switch checked={showVelocity} onChange={setShowVelocity} aria-labelledby="show-velocity-label" />
            <span id="show-froude-label" style={{ marginLeft: 16 }}>{t('results.showFroude')}:</span>
            <Switch checked={showFroude} onChange={setShowFroude} aria-labelledby="show-froude-label" />
          </Space>
        </div>
      </Card>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  );
};

export default ResultsViewer;
