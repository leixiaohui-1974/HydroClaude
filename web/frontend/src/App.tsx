import { useState } from 'react';
import { Layout, Typography, Space, Tabs } from 'antd';
import { AppstoreOutlined, PlayCircleOutlined } from '@ant-design/icons';
import SimulationWorkspace from './features/simulation/SimulationWorkspace';
import ModelingWorkspace from './features/modeling/ModelingWorkspace';
import './App.css';

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
      children: <ModelingWorkspace />
    },
    {
      key: 'simulation',
      label: (
        <span>
          <PlayCircleOutlined />
          仿真管理
        </span>
      ),
      children: <SimulationWorkspace />
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
