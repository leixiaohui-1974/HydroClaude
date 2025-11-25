import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  ControlOutlined,
  BranchesOutlined,
  CloudOutlined,
} from '@ant-design/icons'

const { Sider } = Layout

import { useNavigate } from 'react-router-dom'

const AppSidebar = () => {
  const navigate = useNavigate()

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/modeling',
      icon: <ControlOutlined />,
      label: '高级建模',
    },
    {
      key: '/simulation',
      icon: <CloudOutlined />,
      label: '仿真计算',
    },
    {
      key: 'structures',
      icon: <BranchesOutlined />,
      label: '水工结构',
      children: [
        { key: 'pump', label: '泵站' },
        { key: 'gate', label: '闸门' },
        { key: 'weir', label: '堰' },
        { key: 'reservoir', label: '水库' },
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
        defaultSelectedKeys={['/']}
        style={{ height: '100%', borderRight: 0 }}
        items={menuItems}
        onClick={({ key }) => {
          if (key.startsWith('/')) {
            navigate(key)
          }
        }}
      />
    </Sider>
  )
}

export default AppSidebar
