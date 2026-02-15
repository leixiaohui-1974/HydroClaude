import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, Space, Button, Timeline, Spin } from 'antd';
import {
  ProjectOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  BookOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '@/services/api';

const { Title, Paragraph, Link } = Typography;

interface DashboardStats {
  total_projects: number;
  running_jobs: number;
  completed_jobs: number;
  pending_jobs: number;
  failed_jobs: number;
  recent_jobs: Array<{
    id: number;
    name: string;
    status: string;
    created_at: string | null;
    completed_at: string | null;
  }>;
}

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await api.get<DashboardStats>('/dashboard/stats');
      setStats(data);
    } catch {
      // Fallback to zero stats if API unavailable
      setStats({
        total_projects: 0,
        running_jobs: 0,
        completed_jobs: 0,
        pending_jobs: 0,
        recent_jobs: [],
        failed_jobs: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const formatTimeAgo = (dateStr: string | null): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return t('home.justNow', 'Just now');
    if (diffMin < 60) return t('home.minutesAgo', '{{min}} min ago', { min: diffMin });
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return t('home.hoursAgo', '{{hr}} hr ago', { hr: diffHr });
    const diffDay = Math.floor(diffHr / 24);
    return t('home.daysAgo', '{{day}} days ago', { day: diffDay });
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'green';
      case 'running': return 'blue';
      case 'failed': return 'red';
      default: return 'gray';
    }
  };

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Title>{t('home.welcomeTitle')}</Title>
          <Paragraph style={{ fontSize: '16px' }}>
            {t('home.welcomeSubtitle')}
          </Paragraph>
          <Space size="large">
            <Button type="primary" size="large" icon={<RocketOutlined />} onClick={() => navigate('/projects')}>
              {t('home.getStarted')}
            </Button>
            <Button size="large" icon={<BookOutlined />} onClick={() => navigate('/plugins')}>
              {t('home.viewDocs')}
            </Button>
            <Button size="large" icon={<ApiOutlined />} onClick={() => navigate('/plugins')}>
              {t('home.apiReference')}
            </Button>
          </Space>
        </div>

        {/* Statistics Cards - fetched from API */}
        <Spin spinning={loading}>
          <Row gutter={16}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title={t('home.totalProjects')}
                  value={stats?.total_projects ?? 0}
                  prefix={<ProjectOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title={t('home.running')}
                  value={stats?.running_jobs ?? 0}
                  prefix={<PlayCircleOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title={t('home.completed')}
                  value={stats?.completed_jobs ?? 0}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title={t('home.queued')}
                  value={stats?.pending_jobs ?? 0}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
          </Row>
        </Spin>

        {/* Quick Start */}
        <Card title={t('home.quickStart')} bordered={false}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Card
                type="inner"
                title={t('home.createNewProject')}
                extra={<Button type="link">{t('home.startArrow')}</Button>}
                hoverable
                onClick={() => navigate('/editor')}
              >
                {t('home.createNewProjectDesc')}
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card
                type="inner"
                title={t('home.browseExamples')}
                extra={<Button type="link">{t('home.viewArrow')}</Button>}
                hoverable
                onClick={() => navigate('/projects')}
              >
                {t('home.browseExamplesDesc')}
              </Card>
            </Col>
          </Row>
        </Card>

        {/* Recent Activity - dynamic from API */}
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Card title={t('home.recentProjects')} bordered={false}>
              {stats?.recent_jobs && stats.recent_jobs.length > 0 ? (
                <Timeline
                  items={stats.recent_jobs.map((job) => ({
                    color: statusColor(job.status),
                    children: (
                      <>
                        <p>
                          <strong>{job.name}</strong>
                        </p>
                        <p>
                          {formatTimeAgo(job.created_at || job.completed_at)}
                          {' · '}
                          {job.status === 'completed' ? t('simulation.statusCompleted')
                            : job.status === 'running' ? t('simulation.statusRunning')
                            : job.status === 'failed' ? t('simulation.statusFailed')
                            : t('simulation.statusPending')}
                        </p>
                      </>
                    ),
                  }))}
                />
              ) : (
                <Paragraph type="secondary">{t('home.noRecentJobs', 'No recent jobs. Start a simulation!')}</Paragraph>
              )}
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card title={t('home.features')} bordered={false}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>{t('home.featureVisualEditor')}</strong> - {t('home.featureVisualEditorDesc')}
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>{t('home.featureGIS')}</strong> - {t('home.featureGISDesc')}
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>{t('home.featureInteractiveResults')}</strong> - {t('home.featureInteractiveResultsDesc')}
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>{t('home.featureRealTimeMonitor')}</strong> - {t('home.featureRealTimeMonitorDesc')}
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>{t('home.featurePluginSystem')}</strong> - {t('home.featurePluginSystemDesc')}
                </Paragraph>
              </Space>
            </Card>
          </Col>
        </Row>

        {/* Help & Resources */}
        <Card title={t('home.helpAndResources')} bordered={false}>
          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Card type="inner" title={t('home.documentation')}>
                <Paragraph>
                  {t('home.documentationDesc')}
                </Paragraph>
                <Link onClick={() => navigate('/plugins')}>{t('home.viewDocsArrow')}</Link>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card type="inner" title={t('home.examples')}>
                <Paragraph>
                  {t('home.examplesDesc')}
                </Paragraph>
                <Link onClick={() => navigate('/projects')}>{t('home.browseExamplesArrow')}</Link>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card type="inner" title={t('home.pluginsTitle')}>
                <Paragraph>
                  {t('home.pluginsDesc')}
                </Paragraph>
                <Link onClick={() => navigate('/plugins')}>{t('home.pluginsMarketArrow')}</Link>
              </Card>
            </Col>
          </Row>
        </Card>
      </Space>
    </div>
  );
};

export default HomePage;
