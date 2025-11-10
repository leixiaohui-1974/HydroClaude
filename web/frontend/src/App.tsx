import { useState } from 'react';
import { Layout, Typography, Space } from 'antd';
import SimulationWorkspace from './features/simulation/SimulationWorkspace';
import './App.css';

const { Header, Content, Footer } = Layout;
const { Title } = Typography;

function App() {
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

      <Content style={{ padding: '24px' }}>
        <SimulationWorkspace />
      </Content>

      <Footer style={{ textAlign: 'center', background: '#f0f2f5' }}>
        HydroClaude Web ©{new Date().getFullYear()} -
        Professional Hydraulic Simulation Platform
      </Footer>
    </Layout>
  );
}

export default App;
