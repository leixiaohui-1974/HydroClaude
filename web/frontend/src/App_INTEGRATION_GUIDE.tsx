/**
 * App Integration Guide - 应用集成指南
 * 
 * 此文件展示如何将Week 3-5开发的所有新功能集成到主应用中
 * This file demonstrates how to integrate all new features from Week 3-5 into the main app
 * 
 * 新增功能模块 / New Feature Modules:
 * 1. Control System Panel - 控制系统面板 (Week 3)
 * 2. Water Quality Panel - 水质模拟面板 (Week 4)
 * 3. Parameter Optimization Panel - 参数优化面板 (Week 5)
 * 4. Test Case Library - 测试案例库 (Week 6)
 * 5. Enhanced Charts - 增强可视化 (Additional)
 * 
 * Author: HydroClaude Team
 * Date: 2025-11-13
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  ExperimentOutlined,
  ControlOutlined,
  BarChartOutlined,
  RocketOutlined,
  BookOutlined,
  LineChartOutlined,
  SettingOutlined
} from '@ant-design/icons';

// ============================================================================
// Import New Components
// ============================================================================

// Week 3: Control System
import ControlSystemPanel from './features/control-systems/ControlSystemPanel';

// Week 4: Water Quality
import WaterQualityPanel from './features/water-quality/WaterQualityPanel';

// Week 5: Parameter Optimization
import ParameterOptimizationPanel from './features/optimization/ParameterOptimizationPanel';

// Week 6: Test Case Library
import TestCaseLibrary from './features/test-cases/TestCaseLibrary';

// Additional: Enhanced Visualization
import VisualizationDemo from './pages/VisualizationDemo';
import EnhancedCharts from './components/visualization/EnhancedCharts';

// Existing Pages (假设已存在)
// import Dashboard from './pages/Dashboard';
// import SimulationPage from './pages/SimulationPage';
// import ResultsPage from './pages/ResultsPage';

const { Header, Sider, Content } = Layout;

// ============================================================================
// Menu Configuration
// ============================================================================

const menuItems = [
  {
    key: 'dashboard',
    icon: <DashboardOutlined />,
    label: 'Dashboard / 仪表盘',
    path: '/'
  },
  {
    key: 'simulation',
    icon: <ExperimentOutlined />,
    label: 'Simulation / 模拟',
    path: '/simulation'
  },
  {
    key: 'control',
    icon: <ControlOutlined />,
    label: 'Control Systems / 控制系统',
    path: '/control',
    badge: 'NEW' // 新功能标记
  },
  {
    key: 'water-quality',
    icon: <ExperimentOutlined />,
    label: 'Water Quality / 水质',
    path: '/water-quality',
    badge: 'NEW'
  },
  {
    key: 'optimization',
    icon: <RocketOutlined />,
    label: 'Optimization / 优化',
    path: '/optimization',
    badge: 'NEW'
  },
  {
    key: 'test-cases',
    icon: <BookOutlined />,
    label: 'Test Library / 测试库',
    path: '/test-cases',
    badge: '541'
  },
  {
    key: 'visualization',
    icon: <BarChartOutlined />,
    label: 'Visualization / 可视化',
    path: '/visualization'
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: 'Settings / 设置',
    path: '/settings'
  }
];

// ============================================================================
// Main App Component
// ============================================================================

const App: React.FC = () => {
  const [collapsed, setCollapsed] = React.useState(false);

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        {/* Sidebar Menu */}
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={(value) => setCollapsed(value)}
          width={250}
          style={{
            overflow: 'auto',
            height: '100vh',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0
          }}
        >
          <div style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 20,
            fontWeight: 'bold'
          }}>
            {collapsed ? 'HC' : 'HydroClaude'}
          </div>
          
          <Menu
            theme="dark"
            mode="inline"
            defaultSelectedKeys={['dashboard']}
            items={menuItems.map(item => ({
              key: item.key,
              icon: item.icon,
              label: item.badge ? (
                <span>
                  {item.label}
                  <span style={{
                    marginLeft: 8,
                    padding: '2px 8px',
                    background: '#52c41a',
                    borderRadius: 10,
                    fontSize: 10
                  }}>
                    {item.badge}
                  </span>
                </span>
              ) : item.label
            }))}
          />
        </Sider>

        {/* Main Content Area */}
        <Layout style={{ marginLeft: collapsed ? 80 : 250, transition: 'margin-left 0.2s' }}>
          {/* Header */}
          <Header style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontSize: 20, fontWeight: 500 }}>
              HydroClaude Web System
            </div>
            <div>
              <span style={{ marginRight: 16, color: '#52c41a' }}>● Backend Online</span>
              <span>User: Admin</span>
            </div>
          </Header>

          {/* Content */}
          <Content style={{ margin: '24px', minHeight: 'calc(100vh - 112px)' }}>
            <Routes>
              {/* Dashboard */}
              <Route path="/" element={
                <div style={{ padding: 24, background: '#fff', borderRadius: 8 }}>
                  <h1>Dashboard</h1>
                  <p>Welcome to HydroClaude Web System</p>
                </div>
              } />

              {/* Simulation Page */}
              <Route path="/simulation" element={
                <div style={{ padding: 24, background: '#fff', borderRadius: 8 }}>
                  <h1>Simulation Configuration</h1>
                  <p>Configure and run hydraulic simulations</p>
                </div>
              } />

              {/* NEW: Control Systems (Week 3) */}
              <Route path="/control" element={<ControlSystemPanel />} />

              {/* NEW: Water Quality (Week 4) */}
              <Route path="/water-quality" element={<WaterQualityPanel />} />

              {/* NEW: Parameter Optimization (Week 5) */}
              <Route path="/optimization" element={<ParameterOptimizationPanel />} />

              {/* NEW: Test Case Library (Week 6) */}
              <Route path="/test-cases" element={<TestCaseLibrary />} />

              {/* Visualization */}
              <Route path="/visualization" element={<VisualizationDemo />} />

              {/* Settings */}
              <Route path="/settings" element={
                <div style={{ padding: 24, background: '#fff', borderRadius: 8 }}>
                  <h1>Settings</h1>
                  <p>Application settings and preferences</p>
                </div>
              } />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Router>
  );
};

export default App;

// ============================================================================
// Alternative: Nested Routes Example
// ============================================================================

/**
 * 如果需要嵌套路由，可以这样组织：
 * For nested routes, you can organize like this:
 */

export const AppWithNestedRoutes: React.FC = () => {
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Routes>
          {/* Main Layout with Sidebar */}
          <Route path="/" element={<MainLayout />}>
            <Route index element={<div>Dashboard</div>} />
            <Route path="simulation" element={<div>Simulation</div>} />
            <Route path="control" element={<ControlSystemPanel />} />
            <Route path="water-quality" element={<WaterQualityPanel />} />
            <Route path="optimization" element={<ParameterOptimizationPanel />} />
            <Route path="test-cases" element={<TestCaseLibrary />} />
            <Route path="visualization" element={<VisualizationDemo />} />
          </Route>
        </Routes>
      </Layout>
    </Router>
  );
};

// Main Layout Component (for nested routes)
const MainLayout: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider>
        {/* Sidebar content */}
      </Sider>
      <Layout>
        <Header>{/* Header content */}</Header>
        <Content>
          {/* Outlet for nested routes */}
          {/* <Outlet /> */}
        </Content>
      </Layout>
    </Layout>
  );
};

// ============================================================================
// Usage Instructions / 使用说明
// ============================================================================

/**
 * 集成步骤 / Integration Steps:
 * 
 * 1. 复制此文件到 src/App.tsx
 *    Copy this file to src/App.tsx
 * 
 * 2. 安装必要的依赖 (如果还没有)
 *    Install required dependencies (if not already):
 *    ```bash
 *    npm install react-router-dom antd @ant-design/icons chart.js react-chartjs-2
 *    ```
 * 
 * 3. 确保所有新组件的路径正确
 *    Ensure all new component paths are correct
 * 
 * 4. 更新 index.tsx 以使用新的 App
 *    Update index.tsx to use the new App:
 *    ```tsx
 *    import App from './App';
 *    ```
 * 
 * 5. 启动开发服务器
 *    Start development server:
 *    ```bash
 *    npm run dev
 *    ```
 * 
 * 6. 访问应用
 *    Access the application:
 *    http://localhost:3000
 * 
 * 导航到新功能 / Navigate to new features:
 * - Control Systems: http://localhost:3000/control
 * - Water Quality: http://localhost:3000/water-quality
 * - Optimization: http://localhost:3000/optimization
 * - Test Library: http://localhost:3000/test-cases
 * - Visualization: http://localhost:3000/visualization
 */

// ============================================================================
// Menu Configuration with Submenu Example
// ============================================================================

export const advancedMenuItems = [
  {
    key: 'dashboard',
    icon: <DashboardOutlined />,
    label: 'Dashboard'
  },
  {
    key: 'simulation',
    icon: <ExperimentOutlined />,
    label: 'Simulation',
    children: [
      { key: 'sim-basic', label: 'Basic Flow' },
      { key: 'sim-dambreak', label: 'Dam Break' },
      { key: 'sim-pressurized', label: 'Pressurized' }
    ]
  },
  {
    key: 'advanced',
    icon: <RocketOutlined />,
    label: 'Advanced Features',
    children: [
      { key: 'control', label: 'Control Systems' },
      { key: 'water-quality', label: 'Water Quality' },
      { key: 'optimization', label: 'Optimization' }
    ]
  },
  {
    key: 'tools',
    icon: <BarChartOutlined />,
    label: 'Tools',
    children: [
      { key: 'test-cases', label: 'Test Library (541)' },
      { key: 'visualization', label: 'Visualization' },
      { key: 'reports', label: 'Reports' }
    ]
  }
];

// ============================================================================
// API Integration Example
// ============================================================================

/**
 * 在组件中使用API的示例
 * Example of using API in components:
 */

export const useSimulationAPI = () => {
  const API_BASE = 'http://localhost:8000/api/v1';

  const runSimulation = async (config: any) => {
    const response = await fetch(`${API_BASE}/simulation/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return response.json();
  };

  const getTestCases = async () => {
    const response = await fetch(`${API_BASE}/test-cases/catalog`);
    return response.json();
  };

  const runTestCase = async (caseId: string) => {
    const response = await fetch(`${API_BASE}/test-runner/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: caseId })
    });
    return response.json();
  };

  return { runSimulation, getTestCases, runTestCase };
};

/**
 * 在组件中使用
 * Usage in component:
 * 
 * ```tsx
 * const { runSimulation } = useSimulationAPI();
 * 
 * const handleRun = async () => {
 *   const result = await runSimulation({
 *     length: 10000,
 *     width: 10,
 *     discharge: 50
 *   });
 *   console.log(result);
 * };
 * ```
 */


