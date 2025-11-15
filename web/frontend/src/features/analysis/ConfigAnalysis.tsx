/**
 * Configuration Analysis Component
 * 配置自动分析组件
 * 
 * 对标商业软件的配置验证和分析功能
 */

import React, { useState } from 'react';
import {
  Card,
  Button,
  Progress,
  Alert,
  Descriptions,
  Tag,
  Space,
  Spin,
  Collapse,
  Statistic,
  Row,
  Col,
  Divider,
  Typography,
  Empty
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  ClockCircleOutlined,
  BulbOutlined
} from '@ant-design/icons';

const { Panel } = Collapse;
const { Text, Title, Paragraph } = Typography;

interface ConfigAnalysisProps {
  config: any;
  onAnalysisComplete?: (report: ConfigAnalysisReport) => void;
  autoAnalyze?: boolean;
}

interface ConfigAnalysisReport {
  is_valid: boolean;
  quality_score: number;
  estimated_time: number;
  estimated_memory: number;
  estimated_iterations: number;
  spatial_resolution: any;
  temporal_resolution: any;
  numerical_stability: any;
  physical_validity: any;
  issues: Issue[];
  warnings: string[];
  errors: string[];
  recommendations: Recommendation[];
  diagnostics: any;
  markdown_report?: string;
}

interface Issue {
  severity: 'critical' | 'error' | 'warning' | 'info';
  category: string;
  message: string;
  suggestion: string;
  parameter?: string;
  value?: any;
  recommended?: any;
}

interface Recommendation {
  title: string;
  description: string;
  action: string;
  parameters?: any;
}

const ConfigAnalysis: React.FC<ConfigAnalysisProps> = ({
  config,
  onAnalysisComplete,
  autoAnalyze = false
}) => {
  const [analyzing, setAnalyzing] = useState(false);
  const [report, setReport] = useState<ConfigAnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (autoAnalyze && config) {
      analyzeConfig();
    }
  }, [config, autoAnalyze]);

  const analyzeConfig = async () => {
    if (!config) {
      setError('配置为空');
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/analysis/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
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
      console.error('配置分析失败:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff7875' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'info':
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
      default:
        return <InfoCircleOutlined />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  const getQualityStatus = (score: number) => {
    if (score >= 95) return { status: 'success', text: '优秀' };
    if (score >= 85) return { status: 'normal', text: '良好' };
    if (score >= 70) return { status: 'active', text: '可接受' };
    if (score >= 50) return { status: 'exception', text: '较差' };
    return { status: 'exception', text: '失败' };
  };

  if (!config) {
    return (
      <Card>
        <Empty description="请先配置仿真参数" />
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined />
          配置自动分析
        </Space>
      }
      extra={
        !autoAnalyze && (
          <Button
            type="primary"
            onClick={analyzeConfig}
            loading={analyzing}
            icon={<CheckCircleOutlined />}
          >
            分析配置
          </Button>
        )
      }
    >
      {analyzing && (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" tip="正在分析配置..." />
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
          {/* 质量评分 */}
          <Card size="small">
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="质量评分"
                  value={report.quality_score}
                  precision={1}
                  suffix="/ 100"
                  valueStyle={{
                    color: report.quality_score >= 70 ? '#3f8600' : '#cf1322',
                  }}
                />
                <Progress
                  percent={report.quality_score}
                  status={getQualityStatus(report.quality_score).status as any}
                  strokeColor={{
                    '0%': report.quality_score >= 70 ? '#52c41a' : '#ff4d4f',
                    '100%': report.quality_score >= 70 ? '#95de64' : '#ff7875',
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="配置状态"
                  value={report.is_valid ? '有效' : '无效'}
                  prefix={
                    report.is_valid ? (
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    ) : (
                      <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                    )
                  }
                  valueStyle={{
                    color: report.is_valid ? '#3f8600' : '#cf1322',
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="问题数量"
                  value={report.issues.length}
                  suffix="个"
                  valueStyle={{
                    color: report.issues.length === 0 ? '#3f8600' : '#faad14',
                  }}
                />
              </Col>
            </Row>
          </Card>

          {/* 性能预测 */}
          <Card
            size="small"
            title={
              <Space>
                <ClockCircleOutlined />
                性能预测
              </Space>
            }
          >
            <Descriptions column={3} size="small">
              <Descriptions.Item label="预计计算时间">
                <Text strong>{report.estimated_time.toFixed(2)}</Text> 秒
              </Descriptions.Item>
              <Descriptions.Item label="预计内存使用">
                <Text strong>{report.estimated_memory.toFixed(1)}</Text> MB
              </Descriptions.Item>
              <Descriptions.Item label="预计时间步数">
                <Text strong>{report.estimated_iterations}</Text> 步
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* 错误信息 */}
          {report.errors.length > 0 && (
            <Alert
              message={`发现 ${report.errors.length} 个错误`}
              description={
                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                  {report.errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              }
              type="error"
              showIcon
            />
          )}

          {/* 问题列表 */}
          {report.issues.length > 0 && (
            <Collapse defaultActiveKey={report.issues.some(i => i.severity === 'critical' || i.severity === 'error') ? ['issues'] : []}>
              <Panel
                header={
                  <Space>
                    <WarningOutlined />
                    发现的问题 ({report.issues.length}个)
                  </Space>
                }
                key="issues"
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {report.issues.map((issue, index) => (
                    <Card
                      key={index}
                      size="small"
                      type="inner"
                      title={
                        <Space>
                          {getSeverityIcon(issue.severity)}
                          <Tag color={getSeverityColor(issue.severity)}>
                            {issue.severity.toUpperCase()}
                          </Tag>
                          {issue.category}
                        </Space>
                      }
                    >
                      <Paragraph>
                        <Text strong>问题：</Text>
                        {issue.message}
                      </Paragraph>
                      <Paragraph>
                        <Text strong>建议：</Text>
                        <Text type="secondary">{issue.suggestion}</Text>
                      </Paragraph>
                      {issue.parameter && (
                        <Descriptions size="small" column={3}>
                          <Descriptions.Item label="参数">
                            <Text code>{issue.parameter}</Text>
                          </Descriptions.Item>
                          {issue.value !== null && issue.value !== undefined && (
                            <Descriptions.Item label="当前值">
                              <Text mark>{String(issue.value)}</Text>
                            </Descriptions.Item>
                          )}
                          {issue.recommended !== null && issue.recommended !== undefined && (
                            <Descriptions.Item label="推荐值">
                              <Text type="success">{String(issue.recommended)}</Text>
                            </Descriptions.Item>
                          )}
                        </Descriptions>
                      )}
                    </Card>
                  ))}
                </Space>
              </Panel>
            </Collapse>
          )}

          {/* 优化建议 */}
          {report.recommendations.length > 0 && (
            <Collapse>
              <Panel
                header={
                  <Space>
                    <BulbOutlined />
                    优化建议 ({report.recommendations.length}条)
                  </Space>
                }
                key="recommendations"
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {report.recommendations.map((rec, index) => (
                    <Card key={index} size="small" type="inner" title={rec.title}>
                      <Paragraph>
                        <Text strong>说明：</Text>
                        {rec.description}
                      </Paragraph>
                      <Paragraph>
                        <Text strong>操作：</Text>
                        <Text type="secondary">{rec.action}</Text>
                      </Paragraph>
                      {rec.parameters && (
                        <Descriptions size="small" column={2}>
                          {Object.entries(rec.parameters).map(([key, value]) => (
                            <Descriptions.Item key={key} label={key}>
                              <Text type="success">{String(value)}</Text>
                            </Descriptions.Item>
                          ))}
                        </Descriptions>
                      )}
                    </Card>
                  ))}
                </Space>
              </Panel>
            </Collapse>
          )}

          {/* 详细信息 */}
          <Collapse>
            <Panel header="详细分析信息" key="details">
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                {/* 空间分辨率 */}
                {report.spatial_resolution && (
                  <Card size="small" type="inner" title="空间分辨率">
                    <Descriptions size="small" column={2}>
                      {Object.entries(report.spatial_resolution).map(([key, value]) => (
                        <Descriptions.Item key={key} label={key}>
                          {typeof value === 'number' ? value.toFixed(3) : String(value)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  </Card>
                )}

                {/* 时间分辨率 */}
                {report.temporal_resolution && (
                  <Card size="small" type="inner" title="时间分辨率">
                    <Descriptions size="small" column={2}>
                      {Object.entries(report.temporal_resolution).map(([key, value]) => (
                        <Descriptions.Item key={key} label={key}>
                          {typeof value === 'number' ? value.toFixed(3) : String(value)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  </Card>
                )}

                {/* 数值稳定性 */}
                {report.numerical_stability && (
                  <Card size="small" type="inner" title="数值稳定性">
                    <Descriptions size="small" column={2}>
                      {Object.entries(report.numerical_stability).map(([key, value]) => (
                        <Descriptions.Item key={key} label={key}>
                          {typeof value === 'number' ? value.toFixed(3) : String(value)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  </Card>
                )}

                {/* 物理参数 */}
                {report.physical_validity && (
                  <Card size="small" type="inner" title="物理参数">
                    <Descriptions size="small" column={2}>
                      {Object.entries(report.physical_validity).map(([key, value]) => (
                        <Descriptions.Item key={key} label={key}>
                          {typeof value === 'number' ? value.toFixed(6) : String(value)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  </Card>
                )}
              </Space>
            </Panel>
          </Collapse>

          {/* 总结 */}
          {!report.is_valid && (
            <Alert
              message="配置需要修改"
              description="配置存在严重问题，请根据上述建议修改后重新分析"
              type="error"
              showIcon
            />
          )}
          {report.is_valid && report.quality_score < 70 && (
            <Alert
              message="建议优化配置"
              description="配置有效但质量较低，建议参考优化建议改进配置"
              type="warning"
              showIcon
            />
          )}
          {report.is_valid && report.quality_score >= 70 && (
            <Alert
              message="配置验证通过"
              description="配置质量良好，可以开始仿真计算"
              type="success"
              showIcon
            />
          )}
        </Space>
      )}
    </Card>
  );
};

export default ConfigAnalysis;
