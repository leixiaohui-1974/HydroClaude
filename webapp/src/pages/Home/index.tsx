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

const { Title, Paragraph, Link } = Typography;

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div>
      {/* 欢迎标题 */}
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Title>欢迎使用 HydroClaude v2.0 🌊</Title>
          <Paragraph style={{ fontSize: '16px' }}>
            开源水力学仿真平台 - 现代化图形界面版本
          </Paragraph>
          <Space size="large">
            <Button type="primary" size="large" icon={<RocketOutlined />} onClick={() => navigate('/projects')}>
              开始使用
            </Button>
            <Button size="large" icon={<BookOutlined />} onClick={() => navigate('/plugins')}>
              查看文档
            </Button>
            <Button size="large" icon={<ApiOutlined />} onClick={() => navigate('/plugins')}>
              API参考
            </Button>
          </Space>
        </div>

        {/* 统计卡片 */}
        <Row gutter={16}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="总项目数"
                value={12}
                prefix={<ProjectOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="运行中"
                value={3}
                prefix={<PlayCircleOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="已完成"
                value={24}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="排队中"
                value={2}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 快速操作 */}
        <Card title="快速开始" bordered={false}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Card
                type="inner"
                title="创建新项目"
                extra={<Button type="link">开始 →</Button>}
                hoverable
                onClick={() => navigate('/editor')}
              >
                使用配置编辑器创建一个新的水力学仿真项目
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card
                type="inner"
                title="浏览示例"
                extra={<Button type="link">查看 →</Button>}
                hoverable
                onClick={() => navigate('/projects')}
              >
                查看预置的示例项目，快速了解系统功能
              </Card>
            </Col>
          </Row>
        </Card>

        {/* 最近活动 */}
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Card title="最近项目" bordered={false}>
              <Timeline
                items={[
                  {
                    color: 'green',
                    children: (
                      <>
                        <p><strong>渠道稳态流</strong></p>
                        <p>2分钟前 · 已完成</p>
                      </>
                    ),
                  },
                  {
                    color: 'blue',
                    children: (
                      <>
                        <p><strong>闸门流动分析</strong></p>
                        <p>1小时前 · 运行中</p>
                      </>
                    ),
                  },
                  {
                    color: 'gray',
                    children: (
                      <>
                        <p><strong>非恒定流仿真</strong></p>
                        <p>昨天 · 已完成</p>
                      </>
                    ),
                  },
                ]}
              />
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card title="功能特性" bordered={false}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>可视化配置编辑器</strong> - 无需编写JSON代码
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>GIS地图集成</strong> - 在地图上绘制和查看渠道
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>交互式结果查看</strong> - Plotly图表，支持缩放和导出
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>实时监控</strong> - 查看仿真进度和性能指标
                </Paragraph>
                <Paragraph>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <strong>插件系统</strong> - 扩展功能，自定义工作流
                </Paragraph>
              </Space>
            </Card>
          </Col>
        </Row>

        {/* 帮助资源 */}
        <Card title="帮助与资源" bordered={false}>
          <Row gutter={16}>
            <Col xs={24} sm={8}>
              <Card type="inner" title="📚 文档">
                <Paragraph>
                  查看完整的使用文档和API参考
                </Paragraph>
                <Link onClick={() => navigate('/plugins')}>查看文档 →</Link>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card type="inner" title="💡 示例">
                <Paragraph>
                  学习预置的示例项目和最佳实践
                </Paragraph>
                <Link onClick={() => navigate('/projects')}>浏览示例 →</Link>
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card type="inner" title="🔌 插件">
                <Paragraph>
                  探索插件市场，扩展系统功能
                </Paragraph>
                <Link onClick={() => navigate('/plugins')}>插件市场 →</Link>
              </Card>
            </Col>
          </Row>
        </Card>
      </Space>
    </div>
  );
};

export default HomePage;
