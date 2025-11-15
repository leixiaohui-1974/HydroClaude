import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, Space, Button, Avatar, Dropdown } from 'antd';
import {
  HomeOutlined,
  ProjectOutlined,
  EditOutlined,
  PlayCircleOutlined,
  BarChartOutlined,
  AppstoreOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import './MainLayout.css';

const { Header, Sider, Content, Footer } = Layout;
const { Title } = Typography;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // 侧边栏菜单项
  const menuItems: MenuProps['items'] = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
      onClick: () => navigate('/'),
    },
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: '项目管理',
      onClick: () => navigate('/projects'),
    },
    {
      key: '/editor',
      icon: <EditOutlined />,
      label: '配置编辑器',
      onClick: () => navigate('/editor'),
    },
    {
      key: '/simulation',
      icon: <PlayCircleOutlined />,
      label: '仿真执行',
      onClick: () => navigate('/simulation'),
    },
    {
      key: '/results',
      icon: <BarChartOutlined />,
      label: '结果查看',
      onClick: () => navigate('/results/latest'),
    },
    {
      key: '/plugins',
      icon: <AppstoreOutlined />,
      label: '插件市场',
      onClick: () => navigate('/plugins'),
    },
  ];

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '用户资料',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  // 获取当前路径
  const currentPath = location.pathname;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
        <div className="logo">
          <Space>
            <span style={{ fontSize: '24px' }}>🌊</span>
            {!collapsed && <Title level={4} style={{ color: 'white', margin: 0 }}>HydroClaude</Title>}
          </Space>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPath]}
          items={menuItems}
        />
      </Sider>

      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 64, height: 64 }}
          />

          <Space>
            <Button type="primary">新建项目</Button>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ margin: '24px 16px', padding: 24, background: '#fff', minHeight: 280 }}>
          <Outlet />
        </Content>

        <Footer style={{ textAlign: 'center' }}>
          HydroClaude v2.0.0 | Open Source Hydraulic Simulation Platform | MIT License
        </Footer>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
