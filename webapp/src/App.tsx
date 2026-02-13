import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  HomeOutlined,
  SettingOutlined,
  BarChartOutlined,
  DragOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import DragModelBuilder from './components/DragModelBuilder';
import './App.css';

const { Header, Content, Footer } = Layout;

// 占位组件
const HomePage = () => <div style={{ padding: 24 }}><h2>首页</h2></div>;
const ConfigPage = () => <div style={{ padding: 24 }}><h2>配置页面</h2></div>;
const ResultsPage = () => <div style={{ padding: 24 }}><h2>结果页面</h2></div>;
const ReportsPage = () => <div style={{ padding: 24 }}><h2>报告页面</h2></div>;

function App() {
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold', marginRight: 40 }}>
            💧 HydroClaude
          </div>
          <Menu theme="dark" mode="horizontal" defaultSelectedKeys={['home']}>
            <Menu.Item key="home" icon={<HomeOutlined />}>
              <Link to="/">首页</Link>
            </Menu.Item>
            <Menu.Item key="drag-model" icon={<DragOutlined />}>
              <Link to="/drag-model">拖拽建模</Link>
            </Menu.Item>
            <Menu.Item key="config" icon={<SettingOutlined />}>
              <Link to="/config">配置</Link>
            </Menu.Item>
            <Menu.Item key="results" icon={<BarChartOutlined />}>
              <Link to="/results">结果</Link>
            </Menu.Item>
            <Menu.Item key="reports" icon={<FileTextOutlined />}>
              <Link to="/reports">报告</Link>
            </Menu.Item>
          </Menu>
        </Header>
        
        <Content style={{ padding: '24px 50px', marginTop: 64 }}>
          <div style={{ background: '#fff', padding: 24, minHeight: 'calc(100vh - 200px)' }}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/drag-model" element={<DragModelBuilder />} />
              <Route path="/config" element={<ConfigPage />} />
              <Route path="/results" element={<ResultsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
            </Routes>
          </div>
        </Content>
        
        <Footer style={{ textAlign: 'center' }}>
          HydroClaude ©2025 - 水力学计算与建模平台
        </Footer>
      </Layout>
    </Router>
  );
}

export default App;
