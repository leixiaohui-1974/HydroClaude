/**
 * Visualization Demo Page - 可视化演示页面
 * 展示所有增强型图表组件的用法
 */

import React, { useState, useEffect } from 'react';
import { Layout, Card, Tabs, Space, Button, message } from 'antd';
import {
  BarChartOutlined,
  LineChartOutlined,
  PlayCircleOutlined,
  ExperimentOutlined
} from '@ant-design/icons';
import {
  LongitudinalProfile,
  TimeSeriesChart,
  AnimationPlayer,
  ComparisonChart
} from '../components/visualization/EnhancedCharts';

const { Content } = Layout;
const { TabPane } = Tabs;

const VisualizationDemo: React.FC = () => {
  // Mock data for demonstration
  const [loading, setLoading] = useState(false);

  // Mock data: Longitudinal profile
  const x = Array.from({ length: 100 }, (_, i) => i * 10); // 0 to 990m
  const bed = x.map(xi => 5 - xi * 0.001); // Mild slope
  const h = x.map((xi, i) => bed[i] + 3 + Math.sin(xi / 100) * 0.5); // Water surface

  const structures = [
    { x: 300, type: 'gate', name: 'Sluice Gate' },
    { x: 600, type: 'weir', name: 'Overflow Weir' },
    { x: 850, type: 'pump', name: 'Pump Station' }
  ];

  // Mock data: Time series
  const time = Array.from({ length: 50 }, (_, i) => i * 2); // 0 to 98s
  const timeSeriesData = {
    'Upstream Level': time.map(t => 5 + Math.sin(t / 10) * 0.5),
    'Downstream Level': time.map(t => 4 + Math.sin(t / 12 + Math.PI / 4) * 0.3),
    'Gate Opening': time.map(t => 50 + Math.cos(t / 15) * 20),
    'Discharge': time.map(t => 100 + Math.sin(t / 8) * 30)
  };

  // Mock data: Animation
  const timeSteps = Array.from({ length: 30 }, (_, i) => i * 2);
  const getDataAtTime = (t: number) => {
    const phase = t / 10;
    return {
      h: x.map((xi, i) => bed[i] + 3 + Math.sin(xi / 100 + phase) * 0.8),
      Q: x.map(xi => 100 + Math.sin(xi / 150 + phase) * 30)
    };
  };

  // Mock data: Comparison
  const scenarios = [
    {
      name: 'Baseline',
      x,
      h: x.map((xi, i) => bed[i] + 3),
      color: 'rgb(54, 162, 235)'
    },
    {
      name: 'High Flow',
      x,
      h: x.map((xi, i) => bed[i] + 4.5),
      color: 'rgb(255, 99, 132)'
    },
    {
      name: 'Low Flow',
      x,
      h: x.map((xi, i) => bed[i] + 2),
      color: 'rgb(75, 192, 192)'
    },
    {
      name: 'Optimized',
      x,
      h: x.map((xi, i) => bed[i] + 3.2 + Math.sin(xi / 200) * 0.3),
      color: 'rgb(255, 206, 86)'
    }
  ];

  const fetchSimulationData = async () => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      message.success('Simulation data loaded successfully');
    } catch (error) {
      message.error('Failed to load simulation data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSimulationData();
  }, []);

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px' }}>
          <h1 style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '8px' }}>
            <BarChartOutlined /> Visualization Demo / 可视化演示
          </h1>
          <p style={{ color: '#666', fontSize: '14px' }}>
            Explore all enhanced chart components for hydraulic simulations / 
            探索所有用于水力学模拟的增强型图表组件
          </p>
        </div>

        <Tabs defaultActiveKey="1" size="large">
          {/* Tab 1: Longitudinal Profile */}
          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                Longitudinal Profile / 纵剖面
              </span>
            }
            key="1"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <LongitudinalProfile
                x={x}
                h={h}
                bed={bed}
                structures={structures}
                title="Canal Water Surface Profile / 渠道水面线"
              />

              <Card title="About This Chart / 关于此图表" size="small">
                <p>
                  <strong>English:</strong> The longitudinal profile shows water surface elevation 
                  along the canal length. It includes the bed level and locations of hydraulic structures. 
                  This is essential for understanding flow behavior and identifying critical sections.
                </p>
                <p>
                  <strong>中文:</strong> 纵剖面图显示了渠道长度方向上的水面高程。它包括河床高程和水工结构的位置。
                  这对于理解流动行为和识别关键断面至关重要。
                </p>
              </Card>
            </Space>
          </TabPane>

          {/* Tab 2: Time Series */}
          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                Time Series / 时间序列
              </span>
            }
            key="2"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <TimeSeriesChart
                time={time}
                data={timeSeriesData}
                title="Flow Variables Over Time / 流动变量随时间变化"
                yAxisLabel="Various Units / 不同单位"
              />

              <Card title="About This Chart / 关于此图表" size="small">
                <p>
                  <strong>English:</strong> Time series charts show how hydraulic variables evolve over time. 
                  Multiple variables can be plotted together for comparison. Useful for analyzing transient 
                  behavior, control system response, and periodic phenomena.
                </p>
                <p>
                  <strong>中文:</strong> 时间序列图显示水力学变量随时间的演变。可以同时绘制多个变量进行对比。
                  适用于分析瞬态行为、控制系统响应和周期现象。
                </p>
              </Card>
            </Space>
          </TabPane>

          {/* Tab 3: Animation */}
          <TabPane
            tab={
              <span>
                <PlayCircleOutlined />
                Animation / 动画
              </span>
            }
            key="3"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <AnimationPlayer
                x={x}
                timeSteps={timeSteps}
                dataAtTime={getDataAtTime}
                title="Wave Propagation Animation / 波动传播动画"
              />

              <Card title="About This Chart / 关于此图表" size="small">
                <p>
                  <strong>English:</strong> The animation player visualizes the spatiotemporal evolution 
                  of flow. Use play/pause controls to observe wave propagation, gate operation effects, 
                  or any transient phenomena. Adjust playback speed for detailed analysis.
                </p>
                <p>
                  <strong>中文:</strong> 动画播放器可视化流动的时空演变。使用播放/暂停控件观察波动传播、
                  闸门操作效果或任何瞬态现象。调整播放速度以进行详细分析。
                </p>
              </Card>
            </Space>
          </TabPane>

          {/* Tab 4: Comparison */}
          <TabPane
            tab={
              <span>
                <ExperimentOutlined />
                Comparison / 对比
              </span>
            }
            key="4"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <ComparisonChart
                scenarios={scenarios}
                title="Multi-Scenario Comparison / 多场景对比"
              />

              <Card title="About This Chart / 关于此图表" size="small">
                <p>
                  <strong>English:</strong> Comparison charts allow you to overlay multiple simulation 
                  results or scenarios. This is invaluable for design optimization, sensitivity analysis, 
                  and understanding the impact of different parameters or control strategies.
                </p>
                <p>
                  <strong>中文:</strong> 对比图表允许您叠加多个模拟结果或场景。这对于设计优化、灵敏度分析
                  以及理解不同参数或控制策略的影响非常有价值。
                </p>
              </Card>
            </Space>
          </TabPane>

          {/* Tab 5: Combined View */}
          <TabPane
            tab={
              <span>
                <BarChartOutlined />
                Combined / 综合视图
              </span>
            }
            key="5"
          >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
                gap: '24px' 
              }}>
                <LongitudinalProfile
                  x={x.slice(0, 50)}
                  h={h.slice(0, 50)}
                  bed={bed.slice(0, 50)}
                  title="Profile View"
                />
                <TimeSeriesChart
                  time={time.slice(0, 25)}
                  data={{
                    'Level': timeSeriesData['Upstream Level'].slice(0, 25),
                    'Discharge': timeSeriesData['Discharge'].slice(0, 25)
                  }}
                  title="Time View"
                />
              </div>

              <Card 
                title="Real-Time Dashboard Example / 实时仪表板示例" 
                extra={
                  <Button 
                    type="primary" 
                    loading={loading}
                    onClick={fetchSimulationData}
                  >
                    Refresh Data / 刷新数据
                  </Button>
                }
              >
                <p style={{ marginBottom: '16px' }}>
                  This demonstrates how multiple chart types can be combined in a dashboard layout 
                  for comprehensive monitoring and analysis. / 
                  这展示了如何在仪表板布局中组合多种图表类型，以进行全面的监测和分析。
                </p>
                
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(4, 1fr)', 
                  gap: '16px',
                  padding: '16px',
                  background: '#f5f5f5',
                  borderRadius: '8px'
                }}>
                  <Card size="small">
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                        {h[0].toFixed(2)}m
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Upstream Level</div>
                    </div>
                  </Card>
                  <Card size="small">
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                        {h[h.length - 1].toFixed(2)}m
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Downstream Level</div>
                    </div>
                  </Card>
                  <Card size="small">
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fa8c16' }}>
                        120.5
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Discharge (m³/s)</div>
                    </div>
                  </Card>
                  <Card size="small">
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#722ed1' }}>
                        0.45
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>Froude Number</div>
                    </div>
                  </Card>
                </div>
              </Card>
            </Space>
          </TabPane>
        </Tabs>
      </Content>
    </Layout>
  );
};

export default VisualizationDemo;


