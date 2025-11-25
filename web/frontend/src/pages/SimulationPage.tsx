import { Card, Typography, Space } from 'antd'
import SimulationWorkspace from '@/features/simulation/SimulationWorkspace'

const { Title } = Typography

const SimulationPage = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={2}>⚗️ 仿真计算</Title>
        <p>配置仿真参数，运行水力学计算</p>
      </Card>

      <SimulationWorkspace />
    </Space>
  )
}

export default SimulationPage
