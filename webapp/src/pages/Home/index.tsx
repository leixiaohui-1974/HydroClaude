import React from 'react';
import { Card, Row, Col, Statistic, Typography, Space, Button, Timeline } from 'antd';
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

const { Title, Paragraph, Link } = Typography;

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div>
      {/* Welcome Header */}
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Title>{t('home.welcomeTitle')} 🌊</Title>
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

        {/* Statistics Cards */}
        <Row gutter={16}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('home.totalProjects')}
                value={12}
                prefix={<ProjectOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('home.running')}
                value={3}
                prefix={<PlayCircleOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('home.completed')}
                value={24}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title={t('home.queued')}
                value={2}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
        </Row>

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

        {/* Recent Activity */}
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Card title={t('home.recentProjects')} bordered={false}>
              <Timeline
                items={[
                  {
                    color: 'green',
                    children: (
                      <>
                        <p><strong>{t('home.canalSteadyFlow')}</strong></p>
                        <p>{t('home.minutesAgoCompleted')}</p>
                      </>
                    ),
                  },
                  {
                    color: 'blue',
                    children: (
                      <>
                        <p><strong>{t('home.gateFlowAnalysis')}</strong></p>
                        <p>{t('home.hourAgoRunning')}</p>
                      </>
                    ),
                  },
                  {
                    color: 'gray',
                    children: (
                      <>
                        <p><strong>{t('home.unsteadyFlowSim')}</strong></p>
                        <p>{t('home.yesterdayCompleted')}</p>
                      </>
                    ),
                  },
                ]}
              />
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
              <Card type="inner" title={`📚 ${t('home.documentation')}`}>
                <Paragraph>
                  {t('home.documentationDesc')}
                </Paragraph>
                <Link onClick={() => navigate('/plugins')}>{t('home.viewDocsArrow')}</Link>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card type="inner" title={`💡 ${t('home.examples')}`}>
                <Paragraph>
                  {t('home.examplesDesc')}
                </Paragraph>
                <Link onClick={() => navigate('/projects')}>{t('home.browseExamplesArrow')}</Link>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card type="inner" title={`🔌 ${t('home.pluginsTitle')}`}>
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
