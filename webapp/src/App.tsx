import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  HomeOutlined,
  ProjectOutlined,
  DragOutlined,
  BarChartOutlined,
  EnvironmentOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import HomePage from './pages/Home';
import ProjectsPage from './pages/Projects';
import EditorPage from './pages/Editor';
import DragModelBuilder from './components/DragModelBuilder';
import ResultsPage from './pages/Results';
import MapPage from './pages/Map';
import PluginsPage from './pages/Plugins';
import SimulationPage from './pages/Simulation';
import NotFoundPage from './pages/NotFound';
import './App.css';

const { Header, Content, Footer } = Layout;

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: <Link to="/">首页</Link> },
  { key: '/projects', icon: <ProjectOutlined />, label: <Link to="/projects">项目管理</Link> },
  { key: '/drag-model', icon: <DragOutlined />, label: <Link to="/drag-model">拖拽建模</Link> },
  { key: '/map', icon: <EnvironmentOutlined />, label: <Link to="/map">地图工具</Link> },
  { key: '/results', icon: <BarChartOutlined />, label: <Link to="/results">结果查看</Link> },
  { key: '/plugins', icon: <AppstoreOutlined />, label: <Link to="/plugins">插件市场</Link> },
];

function AppContent() {
  const location = useLocation();

  // 根据当前路径选择菜单项
  const selectedKey = menuItems.find(item =>
    item.key !== '/' && location.pathname.startsWith(item.key)
  )?.key || '/';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', position: 'fixed', zIndex: 1, width: '100%' }}>
        <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold', marginRight: 40 }}>
          HydroClaude
        </div>
        <Menu theme="dark" mode="horizontal" selectedKeys={[selectedKey]} items={menuItems} />
      </Header>

      <Content style={{ padding: '24px 50px', marginTop: 64 }}>
        <div style={{ background: '#fff', padding: 24, minHeight: 'calc(100vh - 200px)' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/editor" element={<EditorPage />} />
            <Route path="/editor/:projectId" element={<EditorPage />} />
            <Route path="/drag-model" element={<DragModelBuilder />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/results/:jobId" element={<ResultsPage />} />
            <Route path="/simulation/:jobId" element={<SimulationPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/plugins" element={<PluginsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </div>
      </Content>

      <Footer style={{ textAlign: 'center' }}>
        HydroClaude - 水力学计算与建模平台
      </Footer>
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
