import { Card, Typography, Tabs, Space } from 'antd'
import {
  ExperimentOutlined,
  ControlOutlined,
  BranchesOutlined,
} from '@ant-design/icons'

const { Title } = Typography

const SimulationPage = () => {
  const items = [
    {
      key: 'structures',
      label: (
        <span>
          <ControlOutlined />
          水工结构
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>水工结构仿真</Title>
          <p>泵站、闸门、堰、水库等水工结构的仿真计算</p>
          <p>（配置表单开发中...）</p>
        </Card>
      ),
    },
    {
      key: 'network',
      label: (
        <span>
          <BranchesOutlined />
          管网系统
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>管网系统仿真</Title>
          <p>管道、管网、复杂系统的仿真计算</p>
          <p>（配置表单开发中...）</p>
        </Card>
      ),
    },
    {
      key: 'canal',
      label: (
        <span>
          <ExperimentOutlined />
          明渠流动
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>明渠水动力仿真</Title>
          <p>明渠非恒定流的Godunov FVM求解</p>
          <p>（配置表单开发中...）</p>
        </Card>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={2}>⚗️ 仿真计算</Title>
        <p>配置仿真参数，运行水力学计算</p>
      </Card>

      <Tabs defaultActiveKey="structures" items={items} />
    </Space>
  )
}

export default SimulationPage
