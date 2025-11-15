/**
 * Result Analysis Component
 * 结果自动分析组件
 * 
 * 对标商业软件的结果分析和质量评估功能
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Alert,
  Descriptions,
  Tag,
  Space,
  Spin,
  Collapse,
  Statistic,
  Row,
  Col,
  Table,
  Typography,
  Empty,
  Badge
} from 'antd';
import {
  CheckCircleOutlined,
  TrophyOutlined,
  WarningOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  BulbOutlined,
  PieChartOutlined
} from '@ant-design/icons';

const { Panel } = Collapse;
const { Text, Title, Paragraph } = Typography;

interface ResultAnalysisProps {
  result: any;
  config?: any;
  taskId?: string;
  autoAnalyze?: boolean;
  onAnalysisComplete?: (report: ResultAnalysisReport) => void;
}

interface ResultAnalysisReport {
  task_id: string;
  timestamp: string;
  quality: 'excellent' | 'good' | 'acceptable' | 'poor' | 'failed';
  quality_score: number;
  summary: string;
  hydraulics: HydraulicCharacteristics;
  conservation: ConservationMetrics;
  performance: PerformanceMetrics;
  key_events: KeyEvent[];
  warnings: string[];
  errors: string[];
  visualization_recommendations: VisualizationRecommendation[];
  recommendations: string[];
  markdown_report?: string;
}

interface HydraulicCharacteristics {
  h_mean: number;
  h_min: number;
  h_max: number;
  h_std: number;
  Q_mean: number;
  Q_min: number;
  Q_max: number;
  Q_std: number;
  V_mean: number;
  V_min: number;
  V_max: number;
  V_std: number;
  Fr_mean: number;
  Fr_min: number;
  Fr_max: number;
  subcritical_percentage: number;
  critical_percentage: number;
  supercritical_percentage: number;
  hydraulic_jumps: any[];
  shock_waves: any[];
}

interface ConservationMetrics {
  mass_conservation: any;
  momentum_conservation: any;
  energy_dissipation: any;
}

interface PerformanceMetrics {
  computation_time: number;
  time_steps: number;
  iterations: number;
  efficiency: number;
}

interface KeyEvent {
  type: string;
  time?: number;
  location?: number;
  value?: number;
  description: string;
}

interface VisualizationRecommendation {
  title: string;
  type: string;
  priority: 'high' | 'medium' | 'low';
  description: string;
  data?: any;
}

const ResultAnalysis: React.FC<ResultAnalysisProps> = ({
  result,
  config,
  taskId,
  autoAnalyze = false,
  onAnalysisComplete
}) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [report, setReport] = useState<ResultAnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (autoAnalyze && result) {
      analyzeResult();
    }
  }, [result, autoAnalyze]);

  const analyzeResult = async () => {
    if (!result) {
      setError('结果为空');
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/analysis/result', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ result, config }),
      });

      if (!response.ok) {
        throw new Error(`分析失败: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      setReport(data);

      if (onAnalysisComplete) {
        onAnalysisComplete(data);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '未知错误';
      setError(errorMessage);
      console.error('结果分析失败:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent':
        return '#52c41a';
      case 'good':
        return '#73d13d';
      case 'acceptable':
        return '#faad14';
      case 'poor':
        return '#ff7875';
      case 'failed':
        return '#ff4d4f';
      default:
        return '#d9d9d9';
    }
  };

  const getQualityIcon = (quality: string) => {
    switch (quality) {
      case 'excellent':
        return '🏆';
      case 'good':
        return '✅';
      case 'acceptable':
        return '👍';
      case 'poor':
        return '⚠️';
      case 'failed':
        return '❌';
      default:
        return '❓';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      case 'low':
        return 'green';
      default:
        return 'default';
    }
  };

  if (!result) {
    return (
      <Card>
        <Empty description="暂无结果数据" />
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <BarChartOutlined />
          结果自动分析
        </Space>
      }
      extra={
        !autoAnalyze && (
          <Button
            type="primary"
            onClick={analyzeResult}
            loading={analyzing}
            icon={<CheckCircleOutlined />}
          >
            分析结果
          </Button>
        )
      }
    >
      {analyzing && (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" tip="正在分析结果..." />
        </div>
      )}

      {error && (
        <Alert
          message="分析失败"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
        />
      )}

      {report && !analyzing && (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 质量评级 */}
          <Card size="small">
            <Row gutter={16} align="middle">
              <Col span={8}>
                <Statistic
                  title="质量评级"
                  value={report.quality.toUpperCase()}
                  prefix={<span style={{ fontSize: '24px' }}>{getQualityIcon(report.quality)}</span>}
                  valueStyle={{
                    color: getQualityColor(report.quality),
                    fontSize: '24px'
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="质量评分"
                  value={report.quality_score}
                  precision={1}
                  suffix="/ 100"
                  valueStyle={{
                    color: getQualityColor(report.quality)
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="问题数量"
                  value={report.warnings.length + report.errors.length}
                  suffix="个"
                  valueStyle={{
                    color: report.errors.length > 0 ? '#ff4d4f' : report.warnings.length > 0 ? '#faad14' : '#52c41a'
                  }}
                />
              </Col>
            </Row>
          </Card>

          {/* 执行摘要 */}
          <Card size="small" title="执行摘要">
            <Paragraph style={{ whiteSpace: 'pre-line' }}>
              {report.summary}
            </Paragraph>
          </Card>

          {/* 水力特性 */}
          <Card
            size="small"
            title={
              <Space>
                <PieChartOutlined />
                水力特性分析
              </Space>
            }
          >
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {/* 基本统计表 */}
              <Table
                size="small"
                pagination={false}
                columns={[
                  { title: '参数', dataIndex: 'param', key: 'param' },
                  { title: '最小值', dataIndex: 'min', key: 'min', render: (v) => v.toFixed(3) },
                  { title: '平均值', dataIndex: 'mean', key: 'mean', render: (v) => v.toFixed(3) },
                  { title: '最大值', dataIndex: 'max', key: 'max', render: (v) => v.toFixed(3) },
                  { title: '标准差', dataIndex: 'std', key: 'std', render: (v) => v ? v.toFixed(3) : '-' },
                ]}
                dataSource={[
                  {
                    key: 'h',
                    param: '水深 (m)',
                    min: report.hydraulics.h_min,
                    mean: report.hydraulics.h_mean,
                    max: report.hydraulics.h_max,
                    std: report.hydraulics.h_std
                  },
                  {
                    key: 'Q',
                    param: '流量 (m³/s)',
                    min: report.hydraulics.Q_min,
                    mean: report.hydraulics.Q_mean,
                    max: report.hydraulics.Q_max,
                    std: report.hydraulics.Q_std
                  },
                  {
                    key: 'V',
                    param: '流速 (m/s)',
                    min: report.hydraulics.V_min,
                    mean: report.hydraulics.V_mean,
                    max: report.hydraulics.V_max,
                    std: report.hydraulics.V_std
                  },
                  {
                    key: 'Fr',
                    param: 'Froude数',
                    min: report.hydraulics.Fr_min,
                    mean: report.hydraulics.Fr_mean,
                    max: report.hydraulics.Fr_max,
                    std: null
                  },
                ]}
              />

              {/* 流态分布 */}
              <Card size="small" type="inner" title="流态分布">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="🔵 亚临界流"
                      value={report.hydraulics.subcritical_percentage}
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="🟡 临界流"
                      value={report.hydraulics.critical_percentage}
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="🔴 超临界流"
                      value={report.hydraulics.supercritical_percentage}
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                </Row>
              </Card>

              {/* 水跃检测 */}
              {report.hydraulics.hydraulic_jumps.length > 0 && (
                <Alert
                  message={`检测到 ${report.hydraulics.hydraulic_jumps.length} 个水跃`}
                  description={
                    <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                      {report.hydraulics.hydraulic_jumps.map((jump: any, idx: number) => (
                        <li key={idx}>
                          位置: {jump.location.toFixed(2)}m, 
                          水深比: {jump.depth_ratio.toFixed(2)}, 
                          上游Fr={jump.upstream_froude.toFixed(2)}, 
                          下游Fr={jump.downstream_froude.toFixed(2)}
                        </li>
                      ))}
                    </ul>
                  }
                  type="warning"
                  showIcon
                />
              )}

              {/* 激波检测 */}
              {report.hydraulics.shock_waves.length > 0 && (
                <Alert
                  message={`检测到 ${report.hydraulics.shock_waves.length} 个激波区域`}
                  type="info"
                  showIcon
                />
              )}
            </Space>
          </Card>

          {/* 守恒性检查 */}
          {report.conservation.mass_conservation && (
            <Card
              size="small"
              title={
                <Space>
                  <InfoCircleOutlined />
                  守恒性检查
                </Space>
              }
            >
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="入口平均流量">
                  {report.conservation.mass_conservation.inlet_Q_mean.toFixed(3)} m³/s
                </Descriptions.Item>
                <Descriptions.Item label="出口平均流量">
                  {report.conservation.mass_conservation.outlet_Q_mean.toFixed(3)} m³/s
                </Descriptions.Item>
                <Descriptions.Item label="平均误差">
                  <Text
                    type={report.conservation.mass_conservation.error_mean > 1 ? 'danger' : 'success'}
                  >
                    {report.conservation.mass_conservation.error_mean.toFixed(4)}%
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="最大误差">
                  <Text
                    type={report.conservation.mass_conservation.error_max > 5 ? 'danger' : 'warning'}
                  >
                    {report.conservation.mass_conservation.error_max.toFixed(4)}%
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="状态" span={2}>
                  <Badge
                    status={report.conservation.mass_conservation.status === 'good' ? 'success' : 'warning'}
                    text={report.conservation.mass_conservation.status}
                  />
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          {/* 性能指标 */}
          <Card
            size="small"
            title={
              <Space>
                <ThunderboltOutlined />
                性能指标
              </Space>
            }
          >
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="计算时间"
                  value={report.performance.computation_time}
                  precision={2}
                  suffix="秒"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="时间步数"
                  value={report.performance.time_steps}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="迭代次数"
                  value={report.performance.iterations}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="计算效率"
                  value={report.performance.efficiency}
                  precision={1}
                  suffix="步/秒"
                />
              </Col>
            </Row>
          </Card>

          {/* 错误和警告 */}
          {report.errors.length > 0 && (
            <Alert
              message={`发现 ${report.errors.length} 个错误`}
              description={
                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                  {report.errors.map((error, idx) => (
                    <li key={idx}>{error}</li>
                  ))}
                </ul>
              }
              type="error"
              showIcon
            />
          )}

          {report.warnings.length > 0 && (
            <Alert
              message={`发现 ${report.warnings.length} 个警告`}
              description={
                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                  {report.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              }
              type="warning"
              showIcon
            />
          )}

          {/* 关键事件 */}
          {report.key_events.length > 0 && (
            <Collapse>
              <Panel
                header={
                  <Space>
                    <InfoCircleOutlined />
                    关键事件 ({report.key_events.length}个)
                  </Space>
                }
                key="events"
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {report.key_events.map((event, idx) => (
                    <Card key={idx} size="small" type="inner" title={event.type}>
                      <Paragraph>{event.description}</Paragraph>
                      {event.time !== undefined && (
                        <Text type="secondary">时间: {event.time.toFixed(2)}s</Text>
                      )}
                      {event.location !== undefined && (
                        <Text type="secondary"> | 位置: {event.location.toFixed(2)}m</Text>
                      )}
                      {event.value !== undefined && (
                        <Text type="secondary"> | 值: {event.value.toFixed(3)}</Text>
                      )}
                    </Card>
                  ))}
                </Space>
              </Panel>
            </Collapse>
          )}

          {/* 可视化建议 */}
          {report.visualization_recommendations.length > 0 && (
            <Collapse>
              <Panel
                header={
                  <Space>
                    <BulbOutlined />
                    可视化建议 ({report.visualization_recommendations.length}条)
                  </Space>
                }
                key="viz"
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {report.visualization_recommendations.map((viz, idx) => (
                    <Card
                      key={idx}
                      size="small"
                      type="inner"
                      title={
                        <Space>
                          <Badge status={viz.priority === 'high' ? 'error' : viz.priority === 'medium' ? 'warning' : 'success'} />
                          {viz.title}
                        </Space>
                      }
                      extra={
                        <Tag color={getPriorityColor(viz.priority)}>
                          {viz.priority} priority
                        </Tag>
                      }
                    >
                      <Paragraph>{viz.description}</Paragraph>
                    </Card>
                  ))}
                </Space>
              </Panel>
            </Collapse>
          )}

          {/* 改进建议 */}
          {report.recommendations.length > 0 && (
            <Collapse>
              <Panel
                header={
                  <Space>
                    <BulbOutlined />
                    改进建议 ({report.recommendations.length}条)
                  </Space>
                }
                key="recommendations"
              >
                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                  {report.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </Panel>
            </Collapse>
          )}

          {/* 总结 */}
          {report.quality === 'excellent' && (
            <Alert
              message="优秀！"
              description="结果完全可靠，可以直接使用。"
              type="success"
              showIcon
              icon={<TrophyOutlined />}
            />
          )}
          {report.quality === 'good' && (
            <Alert
              message="良好"
              description="结果基本可靠，建议查看警告信息。"
              type="success"
              showIcon
            />
          )}
          {report.quality === 'acceptable' && (
            <Alert
              message="可接受"
              description="结果可用，但建议检查问题并考虑优化配置。"
              type="warning"
              showIcon
            />
          )}
          {(report.quality === 'poor' || report.quality === 'failed') && (
            <Alert
              message="质量较差"
              description="结果可靠性不足，建议修改配置后重新计算。"
              type="error"
              showIcon
            />
          )}
        </Space>
      )}
    </Card>
  );
};

export default ResultAnalysis;
