import React, { useState, useMemo } from 'react';
import { Tabs, Card, Space, Button, Select, Switch, message, Descriptions, Tag } from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  TableOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  ExperimentOutlined,
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
    // Multi-physics fields
    concentrations?: number[];
    temperatures?: number[];
    ice_thickness?: number[];
    pressure_head?: number[];
  };
  temporal?: {
    times: number[];
    depth_series: number[][];
    velocity_series: number[][];
  };
  // From backend dispatcher
  summary?: Record<string, any>;
  time_series?: Record<string, any>;
  solver_metadata?: Record<string, any>;
}

interface ResultsViewerProps {
  results: SimulationResults;
}

/** Detect simulation category for UI rendering. */
function getSimCategory(results: SimulationResults): string {
  const type = results.metadata?.simulation_type ??
    results.summary?.simulation_type ?? 'open_channel';
  return type;
}

const ResultsViewer: React.FC<ResultsViewerProps> = ({ results }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('profile');
  const [currentFrame, setCurrentFrame] = useState(0);
  const [showVelocity, setShowVelocity] = useState(false);
  const [showFroude, setShowFroude] = useState(true);

  const simCategory = getSimCategory(results);
  const isUnsteady = simCategory === 'unsteady' ||
    (results.metadata?.simulation_type === 'unsteady');
  const isWaterQuality = simCategory === 'water_quality';
  const isTemperature = simCategory === 'water_temperature';
  const isIce = simCategory === 'ice_simulation';
  const isCoupled = simCategory === 'coupled_ice_wq';
  const isWaterHammer = simCategory === 'water_hammer';

  // Build spatial data from dispatcher result if backend format
  const spatialData = useMemo(() => {
    const ts = results.time_series;
    if (ts && !results.spatial?.positions?.length) {
      const x: number[] = ts.x ?? [];
      const baseDepths = ts.h_final ?? ts.C_final ?? ts.T_final ??
        ts.ice_thickness_final ?? ts.H_final ?? [];
      const baseVelocities = ts.Q_final ?? [];
      return {
        positions: x,
        depths: baseDepths,
        velocities: baseVelocities,
        concentrations: ts.C_final,
        temperatures: ts.T_final,
        ice_thickness: ts.ice_thickness_final,
        pressure_head: ts.H_final,
      };
    }
    return results.spatial ?? { positions: [], depths: [], velocities: [] };
  }, [results]);

  const handleExportCSV = () => {
    const { positions, depths, velocities } = spatialData;
    const headers = ['Position(m)', 'Depth(m)', 'Velocity(m/s)'];
    if ((spatialData as any).concentrations) headers.push('Concentration(mg/L)');
    if ((spatialData as any).temperatures) headers.push('Temperature(C)');
    if ((spatialData as any).ice_thickness) headers.push('IceThickness(m)');
    if ((spatialData as any).pressure_head) headers.push('PressureHead(m)');

    const rows = (positions ?? []).map((pos: number, i: number) => {
      const row: (number | string)[] = [pos, depths?.[i] ?? '', velocities?.[i] ?? ''];
      if ((spatialData as any).concentrations) row.push((spatialData as any).concentrations[i] ?? '');
      if ((spatialData as any).temperatures) row.push((spatialData as any).temperatures[i] ?? '');
      if ((spatialData as any).ice_thickness) row.push((spatialData as any).ice_thickness[i] ?? '');
      if ((spatialData as any).pressure_head) row.push((spatialData as any).pressure_head[i] ?? '');
      return row.join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `results_${results.metadata?.case_name || simCategory || 'data'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(t('results.dataExportedCSV'));
  };

  const handleDownloadReport = () => {
    const report = {
      metadata: results.metadata,
      summary: results.summary ?? {
        total_points: spatialData.positions?.length ?? 0,
      },
      solver_metadata: results.solver_metadata,
      spatial: spatialData,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${results.metadata?.case_name || simCategory || 'simulation'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(t('results.reportDownloaded'));
  };

  // Summary card for multi-physics results
  const summaryCard = results.summary ? (
    <Card size="small" title={t('results.simulationResults')} style={{ marginBottom: 16 }}>
      <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
        <Descriptions.Item label={t('results.simType')}>
          <Tag color="blue">{results.summary.simulation_type}</Tag>
        </Descriptions.Item>
        {results.summary.final_time != null && (
          <Descriptions.Item label={t('simulation.endTime')}>
            {Number(results.summary.final_time).toFixed(1)} s
          </Descriptions.Item>
        )}
        {results.summary.total_steps != null && (
          <Descriptions.Item label={t('results.totalSteps')}>
            {results.summary.total_steps}
          </Descriptions.Item>
        )}
        {results.summary.stable != null && (
          <Descriptions.Item label={t('results.stability')}>
            <Tag color={results.summary.stable ? 'green' : 'red'}>
              {results.summary.stable ? t('results.stable') : t('results.unstable')}
            </Tag>
          </Descriptions.Item>
        )}
        {/* Water quality specific */}
        {results.summary.C_max != null && (
          <Descriptions.Item label={`C max`}>{Number(results.summary.C_max).toFixed(3)} mg/L</Descriptions.Item>
        )}
        {results.summary.C_mean != null && (
          <Descriptions.Item label={`C mean`}>{Number(results.summary.C_mean).toFixed(3)} mg/L</Descriptions.Item>
        )}
        {/* Temperature specific */}
        {results.summary.T_max != null && (
          <Descriptions.Item label={`T max`}>{Number(results.summary.T_max).toFixed(2)} °C</Descriptions.Item>
        )}
        {results.summary.T_mean != null && (
          <Descriptions.Item label={`T mean`}>{Number(results.summary.T_mean).toFixed(2)} °C</Descriptions.Item>
        )}
        {/* Ice specific */}
        {results.summary.ice_max_thickness != null && (
          <Descriptions.Item label={t('results.iceThicknessM')}>
            {Number(results.summary.ice_max_thickness).toFixed(3)} m
          </Descriptions.Item>
        )}
        {results.summary.ice_coverage_percent != null && (
          <Descriptions.Item label={t('results.iceCoverage')}>
            {Number(results.summary.ice_coverage_percent).toFixed(1)}%
          </Descriptions.Item>
        )}
        {/* Water hammer specific */}
        {results.summary.pressure_surge != null && (
          <Descriptions.Item label={t('results.pressureSurge')}>
            {Number(results.summary.pressure_surge).toFixed(2)} m
          </Descriptions.Item>
        )}
        {results.summary.wave_speed != null && (
          <Descriptions.Item label={t('results.waveSpeed')}>
            {Number(results.summary.wave_speed).toFixed(1)} m/s
          </Descriptions.Item>
        )}
        {/* Open channel specific */}
        {results.summary.h_max != null && (
          <Descriptions.Item label={t('results.maxDepth')}>
            {Number(results.summary.h_max).toFixed(3)} m
          </Descriptions.Item>
        )}
        {results.summary.h_mean != null && (
          <Descriptions.Item label={t('results.avgDepth')}>
            {Number(results.summary.h_mean).toFixed(3)} m
          </Descriptions.Item>
        )}
        {results.summary.mass_error_percent != null && (
          <Descriptions.Item label={t('results.massError')}>
            {Number(results.summary.mass_error_percent).toFixed(4)}%
          </Descriptions.Item>
        )}
      </Descriptions>
    </Card>
  ) : null;

  // Standard hydraulic tabs
  const tabItems = [
    {
      key: 'profile',
      label: (
        <span>
          <LineChartOutlined />
          {isWaterQuality ? t('results.concentrationProfile') :
           isTemperature ? t('results.temperatureProfile') :
           isIce ? t('results.iceThicknessProfile') :
           isWaterHammer ? t('results.pressureHeadProfile') :
           t('results.waterProfile')}
        </span>
      ),
      children: (
        <WaterProfileChart
          data={spatialData}
          showVelocity={showVelocity}
          height={500}
        />
      ),
    },
    // Velocity tab only for hydraulic/open channel types
    ...(!isWaterQuality && !isTemperature && !isIce && !isCoupled ? [{
      key: 'velocity',
      label: (
        <span>
          <BarChartOutlined />
          {t('results.velocityDistribution')}
        </span>
      ),
      children: (
        <VelocityChart
          data={spatialData}
          showFroude={showFroude}
          height={500}
        />
      ),
    }] : []),
    // Time-series snapshots tab (from dispatcher)
    ...(results.time_series?.snapshots?.length ? [{
      key: 'snapshots',
      label: (
        <span>
          <ExperimentOutlined />
          {t('results.timeSeries')}
        </span>
      ),
      children: (
        <TimeSeriesChart
          data={{
            times: results.time_series.snapshots.map((s: any) => s.t),
            values: [results.time_series.snapshots.map((s: any) =>
              s.h_max ?? s.C_max ?? s.T_max ?? s.ice_max ?? s.H_max ?? 0
            )],
            positions: [0],
            variable_name: isWaterQuality ? t('results.concentrationMgL') :
              isTemperature ? t('results.temperatureC') :
              isIce ? t('results.iceThicknessM') :
              isWaterHammer ? t('results.pressureHeadM') :
              t('results.waterDepthM'),
          }}
          title={t('chart.timeSeriesTitle')}
          height={450}
        />
      ),
    }] : []),
    // Standard unsteady animation tabs
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
                      defaultValue={[0, Math.floor(spatialData.positions.length / 2)]}
                    >
                      {spatialData.positions.map((pos: number, idx: number) => (
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
                    positions: spatialData.positions,
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
                    positions: spatialData.positions,
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
      children: <ResultsTable data={spatialData} />,
    },
  ];

  return (
    <div>
      {summaryCard}

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
