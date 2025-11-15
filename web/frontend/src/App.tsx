import { Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import AppHeader from './components/layout/AppHeader'
import AppSidebar from './components/layout/AppSidebar'
import HomePage from './pages/HomePage'
import SimulationPage from './pages/SimulationPage'
import ResultsPage from './pages/ResultsPage'
import AboutPage from './pages/AboutPage'
import './App.css'

const { Content, Footer } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader />
      <Layout>
        <AppSidebar />
        <Layout style={{ padding: '0 24px 24px' }}>
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: '#fff',
            }}
          >
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/simulation" element={<SimulationPage />} />
              <Route path="/results" element={<ResultsPage />} />
              <Route path="/about" element={<AboutPage />} />
            </Routes>
          </Content>
          <Footer style={{ textAlign: 'center' }}>
            HydroClaude ©{new Date().getFullYear()} - 水力学仿真平台
          </Footer>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default App
