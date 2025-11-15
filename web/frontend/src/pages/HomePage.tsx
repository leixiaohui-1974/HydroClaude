import { Card, Row, Col, Statistic, Typography, Space, Button } from 'antd'
import {
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Paragraph } = Typography

const HomePage = () => {
  const navigate = useNavigate()

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* 欢迎横幅 */}
      <Card>
        <Title level={2}>🌊 欢迎使用 HydroClaude 水力学仿真平台</Title>
        <Paragraph>
          对标商业软件（HEC-RAS、MIKE、EPANET）的开源水力学仿真系统
        </Paragraph>
        <Space>
          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            onClick={() => navigate('/simulation')}
          >
            开始仿真
          </Button>
          <Button size="large" onClick={() => navigate('/about')}>
            了解更多
          </Button>
        </Space>
      </Card>

      {/* 统计卡片 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="可用方法"
              value={13}
              prefix={<ThunderboltOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="API端点"
              value={20}
              prefix={<CheckCircleOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="支持结构"
              value={14}
              prefix={<CheckCircleOutlined />}
              suffix="种"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="测试通过率"
              value={94.7}
              precision={1}
              prefix={<ClockCircleOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 功能模块 */}
      <Row gutter={16}>
        <Col span={8}>
          <Card title="💧 明渠水动力" hoverable>
            <Paragraph>
              • Godunov FVM求解器
              <br />
              • HLL Riemann求解器
              <br />
              • 2阶MUSCL重构
              <br />• Well-Balanced格式
            </Paragraph>
            <Button type="link">了解详情 →</Button>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="🏗️ 水工结构" hoverable>
            <Paragraph>
              • 泵站仿真
              <br />
              • 闸门计算
              <br />
              • 堰流分析
              <br />• 水库调度
            </Paragraph>
            <Button type="link">了解详情 →</Button>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="🔗 管网系统" hoverable>
            <Paragraph>
              • 管道流动
              <br />
              • Hardy-Cross法
              <br />
              • 复杂系统
              <br />• 综合调度
            </Paragraph>
            <Button type="link">了解详情 →</Button>
          </Card>
        </Col>
      </Row>

      {/* 版本信息 */}
      <Card title="📊 系统信息">
        <Row>
          <Col span={12}>
            <Paragraph>
              <strong>引擎版本：</strong> v2.0.0
              <br />
              <strong>开发阶段：</strong> Phase 2 (React前端)
              <br />
              <strong>完成度：</strong> Phase 1 (100%)
            </Paragraph>
          </Col>
          <Col span={12}>
            <Paragraph>
              <strong>对标软件：</strong>
              <br />
              • HEC-RAS (明渠水动力)
              <br />
              • MIKE (水工结构)
              <br />• EPANET (管网仿真)
            </Paragraph>
          </Col>
        </Row>
      </Card>
    </Space>
  )
}

export default HomePage
