import { Layout, Menu, Typography } from 'antd'
import {
  HomeOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Header } = Layout
const { Title } = Typography

const AppHeader = () => {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/simulation',
      icon: <ExperimentOutlined />,
      label: '仿真计算',
    },
    {
      key: '/results',
      icon: <BarChartOutlined />,
      label: '结果分析',
    },
    {
      key: '/about',
      icon: <InfoCircleOutlined />,
      label: '关于',
    },
  ]

  return (
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        background: '#001529',
      }}
    >
      <Title
        level={3}
        style={{
          color: 'white',
          margin: 0,
          marginRight: 50,
          whiteSpace: 'nowrap',
        }}
      >
        💧 HydroClaude
      </Title>
      <Menu
        theme="dark"
        mode="horizontal"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ flex: 1, minWidth: 0 }}
      />
    </Header>
  )
}

export default AppHeader
