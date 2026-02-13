import React, { useState } from 'react';
import { Tabs, Card, Space, Button, Select, Switch, message } from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  TableOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import WaterProfileChart from '../Charts/WaterProfileChart';
import VelocityChart from '../Charts/VelocityChart';
import TimeSeriesChart from '../Charts/TimeSeriesChart';
import ResultsTable from '../DataTable/ResultsTable';
import AnimationPlayer from '../AnimationPlayer';

const { TabPane } = Tabs;
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
    message.success('数据已导出为CSV');
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
    message.success('报告已下载');
  };

  return (
    <div>
      {/* 工具栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownloadReport}>
            下载报告
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExportCSV}>
            导出所有数据
          </Button>
          {isUnsteady && (
            <Button icon={<PlayCircleOutlined />} onClick={() => setActiveTab('animation')}>
              生成动画
            </Button>
          )}
        </Space>

        <div style={{ float: 'right' }}>
          <Space>
            <span>显示流速:</span>
            <Switch checked={showVelocity} onChange={setShowVelocity} />
            <span style={{ marginLeft: 16 }}>显示Froude数:</span>
            <Switch checked={showFroude} onChange={setShowFroude} />
          </Space>
        </div>
      </Card>

      {/* 结果展示 */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 空间剖面 */}
          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                水位剖面
              </span>
            }
            key="profile"
          >
            <WaterProfileChart
              data={results.spatial}
              showVelocity={showVelocity}
              height={500}
            />
          </TabPane>

          {/* 流速分布 */}
          <TabPane
            tab={
              <span>
                <BarChartOutlined />
                流速分布
              </span>
            }
            key="velocity"
          >
            <VelocityChart
              data={results.spatial}
              showFroude={showFroude}
              height={500}
            />
          </TabPane>

          {/* 时间序列（非恒定流）*/}
          {isUnsteady && results.temporal && (
            <TabPane
              tab={
                <span>
                  <PlayCircleOutlined />
                  时间序列
                </span>
              }
              key="timeseries"
            >
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Card size="small" type="inner">
                  <Space>
                    <span>选择监测位置:</span>
                    <Select
                      mode="multiple"
                      placeholder="选择位置"
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
                    times: results.temporal.times,
                    values: results.temporal.depth_series,
                    positions: results.spatial.positions,
                    variable_name: '水深 (m)',
                  }}
                  title="水深时间序列"
                  height={450}
                />
              </Space>
            </TabPane>
          )}

          {/* 动画播放（非恒定流）*/}
          {isUnsteady && results.temporal && (
            <TabPane
              tab={
                <span>
                  <PlayCircleOutlined />
                  动画播放
                </span>
              }
              key="animation"
            >
              <AnimationPlayer
                totalFrames={results.temporal.times.length}
                currentFrame={currentFrame}
                onFrameChange={setCurrentFrame}
                fps={10}
              >
                <WaterProfileChart
                  data={{
                    positions: results.spatial.positions,
                    depths: results.temporal.depth_series.map(series => series[currentFrame]),
                    velocities: results.temporal.velocity_series?.map(series => series[currentFrame]),
                  }}
                  title={`时间: ${results.temporal.times[currentFrame]?.toFixed(2)} s`}
                  showVelocity={showVelocity}
                  height={400}
                />
              </AnimationPlayer>
            </TabPane>
          )}

          {/* 数据表格 */}
          <TabPane
            tab={
              <span>
                <TableOutlined />
                数据表格
              </span>
            }
            key="table"
          >
            <ResultsTable data={results.spatial} />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default ResultsViewer;
