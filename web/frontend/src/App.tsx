import { useState, lazy, Suspense } from 'react';
import { Layout, Typography, Space, Tabs, Spin } from 'antd';
import { AppstoreOutlined, PlayCircleOutlined } from '@ant-design/icons';
import './App.css';

// Lazy load workspace components for code splitting
const SimulationWorkspace = lazy(() => import('./features/simulation/SimulationWorkspace'));
const ModelingWorkspace = lazy(() => import('./features/modeling/ModelingWorkspace'));

const { Header, Content, Footer } = Layout;
const { Title } = Typography;

function App() {
  const [activeTab, setActiveTab] = useState('modeling');

  const tabItems = [
    {
      key: 'modeling',
      label: (
        <span>
          <AppstoreOutlined />
          建模工作台
        </span>
      ),
      children: (
        <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载中..." /></div>}>
          <ModelingWorkspace />
        </Suspense>
      )
    },
    {
      key: 'simulation',
      label: (
        <span>
          <PlayCircleOutlined />
          仿真管理
        </span>
      ),
      children: (
        <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载中..." /></div>}>
          <SimulationWorkspace />
        </Suspense>
      )
    }
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        background: '#001529',
        padding: '0 50px'
      }}>
        <Space>
          <Title level={3} style={{ color: '#fff', margin: 0 }}>
            HydroClaude Web
          </Title>
          <span style={{ color: '#888', fontSize: '14px' }}>
            水力学仿真管理平台
          </span>
        </Space>
      </Header>

      <Content style={{ padding: 0, background: '#f0f2f5' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
          style={{
            background: 'white',
            padding: '0 24px',
            margin: 0
          }}
          tabBarStyle={{
            marginBottom: 0
          }}
        />
      </Content>

      <Footer style={{ textAlign: 'center', background: '#f0f2f5', padding: '12px 50px' }}>
        HydroClaude Web ©{new Date().getFullYear()} -
        Professional Hydraulic Simulation Platform
      </Footer>
    </Layout>
  );
}

export default App;
