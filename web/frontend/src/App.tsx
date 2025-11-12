import { useState, lazy, Suspense } from 'react';
import { Layout, Typography, Space, Tabs, Spin, Modal } from 'antd';
import { AppstoreOutlined, PlayCircleOutlined } from '@ant-design/icons';
import QuickActionsToolbar from './components/QuickActionsToolbar';
import { useKeyboardShortcuts, DEFAULT_SHORTCUTS } from './hooks/useKeyboardShortcuts';
import './App.css';

// Lazy load workspace components for code splitting
const SimulationWorkspace = lazy(() => import('./features/simulation/SimulationWorkspace'));
const ModelingWorkspace = lazy(() => import('./features/modeling/ModelingWorkspace'));

const { Header, Content, Footer } = Layout;
const { Title } = Typography;

function App() {
  const [activeTab, setActiveTab] = useState('modeling');
  const [helpModalVisible, setHelpModalVisible] = useState(false);

  // Global keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: DEFAULT_SHORTCUTS.HELP,
      handler: () => setHelpModalVisible(true),
      description: 'Show keyboard shortcuts help'
    },
    {
      key: DEFAULT_SHORTCUTS.CLOSE,
      handler: () => {
        if (helpModalVisible) {
          setHelpModalVisible(false);
        }
      },
      description: 'Close modals',
      enabled: helpModalVisible
    }
  ]);

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

      {/* Quick Actions Toolbar */}
      <QuickActionsToolbar
        onShowHelp={() => setHelpModalVisible(true)}
      />

      {/* Help Modal */}
      <Modal
        title="键盘快捷键 Keyboard Shortcuts"
        open={helpModalVisible}
        onCancel={() => setHelpModalVisible(false)}
        footer={null}
        width={600}
      >
        <div style={{ fontSize: 14, lineHeight: 1.8 }}>
          <p style={{ color: '#666', marginBottom: 16 }}>
            使用键盘快捷键可以更快地执行常用操作。
          </p>
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ marginBottom: 8 }}>全局快捷键 Global Shortcuts</h4>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li><kbd>F1</kbd> - 显示帮助 Show Help</li>
              <li><kbd>Esc</kbd> - 关闭弹窗 Close Modal</li>
            </ul>
          </div>
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ marginBottom: 8 }}>建模工作台 Modeling Workspace</h4>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li><kbd>Ctrl+S</kbd> / <kbd>Cmd+S</kbd> - 保存模型 Save Model</li>
              <li><kbd>Ctrl+N</kbd> / <kbd>Cmd+N</kbd> - 新建模型 New Model</li>
              <li><kbd>Ctrl+O</kbd> / <kbd>Cmd+O</kbd> - 打开模型 Open Model</li>
              <li><kbd>Ctrl+E</kbd> / <kbd>Cmd+E</kbd> - 导出模型 Export Model</li>
              <li><kbd>Ctrl+Z</kbd> / <kbd>Cmd+Z</kbd> - 撤销 Undo</li>
              <li><kbd>Ctrl+Y</kbd> / <kbd>Cmd+Y</kbd> - 重做 Redo</li>
            </ul>
          </div>
          <div>
            <h4 style={{ marginBottom: 8 }}>仿真结果 Simulation Results</h4>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li><kbd>Space</kbd> - 播放/暂停动画 Play/Pause Animation</li>
            </ul>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}

export default App;
