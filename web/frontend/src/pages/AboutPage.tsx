import { Card, Typography, Space, Descriptions, Tag } from 'antd'

const { Title, Paragraph } = Typography

const AboutPage = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={2}>ℹ️ 关于 HydroClaude</Title>
        <Paragraph>
          HydroClaude是一个对标商业软件（HEC-RAS、MIKE、EPANET）的开源水力学仿真系统。
        </Paragraph>
      </Card>

      <Card title="系统信息">
        <Descriptions bordered column={2}>
          <Descriptions.Item label="系统名称">
            HydroClaude
          </Descriptions.Item>
          <Descriptions.Item label="版本">v2.0.0</Descriptions.Item>
          <Descriptions.Item label="引擎版本">
            HydraulicEngineV2
          </Descriptions.Item>
          <Descriptions.Item label="开发阶段">
            <Tag color="blue">Phase 2 - React前端</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="核心方法" span={2}>
            13个仿真方法
          </Descriptions.Item>
          <Descriptions.Item label="API端点" span={2}>
            20个RESTful端点
          </Descriptions.Item>
          <Descriptions.Item label="支持结构" span={2}>
            14种水工结构
          </Descriptions.Item>
          <Descriptions.Item label="测试通过率" span={2}>
            <Tag color="green">94.7% (18/19)</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="核心功能">
        <Paragraph>
          <strong>Week 1-2: 泵站和闸门</strong>
          <br />
          • 泵站仿真（单泵/多泵）
          <br />
          • 闸门计算（平面闸/弧形闸）
          <br />• 明渠+泵站/闸门组合
        </Paragraph>

        <Paragraph>
          <strong>Week 3-4: 堰和水库</strong>
          <br />
          • 堰流计算（4种堰类型）
          <br />
          • 水库调度演算
          <br />• 优化调度算法
        </Paragraph>

        <Paragraph>
          <strong>Week 5-6: 管网和复杂系统</strong>
          <br />
          • 管道流动（3种公式）
          <br />
          • 管网仿真（Hardy-Cross）
          <br />
          • 复杂系统集成
          <br />• 综合调度优化
        </Paragraph>
      </Card>

      <Card title="对标商业软件">
        <Descriptions bordered>
          <Descriptions.Item label="HEC-RAS" span={3}>
            明渠水动力学仿真 - ✅ 100%完成
          </Descriptions.Item>
          <Descriptions.Item label="MIKE" span={3}>
            水工结构仿真 - ✅ 100%完成
          </Descriptions.Item>
          <Descriptions.Item label="EPANET" span={3}>
            管网水力分析 - ✅ 80%完成
          </Descriptions.Item>
          <Descriptions.Item label="WaterCAD" span={3}>
            给水管网设计 - ✅ 70%完成
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="技术栈">
        <Paragraph>
          <strong>后端:</strong>
          <br />
          • Python 3.x
          <br />
          • FastAPI
          <br />
          • NumPy/SciPy
          <br />• Godunov FVM求解器
        </Paragraph>

        <Paragraph>
          <strong>前端:</strong>
          <br />
          • React 18
          <br />
          • TypeScript
          <br />
          • Vite
          <br />
          • Ant Design
          <br />• Recharts
        </Paragraph>
      </Card>
    </Space>
  )
}

export default AboutPage
