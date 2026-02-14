import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, Space, Button, Avatar, Dropdown } from 'antd';
import {
  HomeOutlined,
  ProjectOutlined,
  EditOutlined,
  PlayCircleOutlined,
  BarChartOutlined,
  EnvironmentOutlined,
  AppstoreOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useTranslation } from 'react-i18next';
import useAuthStore from '@/stores/authStore';
import LanguageSwitcher from '../LanguageSwitcher';
import './MainLayout.css';

const { Header, Sider, Content, Footer } = Layout;
const { Title, Text } = Typography;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { t } = useTranslation();

  // 侧边栏菜单项
  const menuItems: MenuProps['items'] = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: t('nav.home'),
      onClick: () => navigate('/'),
    },
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: t('nav.projects'),
      onClick: () => navigate('/projects'),
    },
    {
      key: '/editor',
      icon: <EditOutlined />,
      label: t('nav.editor'),
      onClick: () => navigate('/editor'),
    },
    {
      key: '/simulation',
      icon: <PlayCircleOutlined />,
      label: t('nav.simulation'),
      onClick: () => navigate('/simulation'),
    },
    {
      key: '/results',
      icon: <BarChartOutlined />,
      label: t('nav.results'),
      onClick: () => navigate('/results/latest'),
    },
    {
      key: '/map',
      icon: <EnvironmentOutlined />,
      label: t('nav.map'),
      onClick: () => navigate('/map'),
    },
    {
      key: '/plugins',
      icon: <AppstoreOutlined />,
      label: t('nav.plugins'),
      onClick: () => navigate('/plugins'),
    },
  ];

  // 用户菜单点击处理
  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    switch (key) {
      case 'profile':
        // TODO: Navigate to profile page when available
        break;
      case 'settings':
        // TODO: Navigate to settings page when available
        break;
      case 'logout':
        logout();
        break;
    }
  };

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: t('layout.userProfile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: t('layout.settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: t('layout.logout'),
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
            aria-label={collapsed ? t('layout.expandSidebar') : t('layout.collapseSidebar')}
            style={{ fontSize: '16px', width: 64, height: 64 }}
          />

          <Space size="middle">
            <LanguageSwitcher />
            <Button type="primary">{t('layout.newProject')}</Button>
            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar
                  src={user?.avatar_url}
                  icon={!user?.avatar_url ? <UserOutlined /> : undefined}
                  style={{ backgroundColor: '#1890ff' }}
                />
                <Text style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user?.username || t('auth.username')}
                </Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ margin: '24px 16px', padding: 24, background: '#fff', minHeight: 280 }}>
          <Outlet />
        </Content>

        <Footer style={{ textAlign: 'center' }}>
          {t('layout.footer')}
        </Footer>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
