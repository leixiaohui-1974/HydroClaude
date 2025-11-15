import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  ControlOutlined,
  BranchesOutlined,
  CloudOutlined,
} from '@ant-design/icons'

const { Sider } = Layout

const AppSidebar = () => {
  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: 'structures',
      icon: <ControlOutlined />,
      label: '水工结构',
      children: [
        { key: 'pump', label: '泵站' },
        { key: 'gate', label: '闸门' },
        { key: 'weir', label: '堰' },
        { key: 'reservoir', label: '水库' },
      ],
    },
    {
      key: 'network',
      icon: <BranchesOutlined />,
      label: '管网系统',
      children: [
        { key: 'pipe', label: '管道' },
        { key: 'network', label: '管网' },
        { key: 'complex', label: '复杂系统' },
      ],
    },
    {
      key: 'simulation',
      icon: <CloudOutlined />,
      label: '仿真类型',
      children: [
        { key: 'canal', label: '明渠流动' },
        { key: 'pressure', label: '压力管道' },
        { key: 'integrated', label: '综合调度' },
      ],
    },
  ]

  return (
    <Sider
      width={200}
      style={{
        background: '#fff',
      }}
    >
      <Menu
        mode="inline"
        defaultSelectedKeys={['dashboard']}
        defaultOpenKeys={['structures']}
        style={{ height: '100%', borderRight: 0 }}
        items={menuItems}
      />
    </Sider>
  )
}

export default AppSidebar
