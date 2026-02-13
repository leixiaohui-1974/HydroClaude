import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import ErrorBoundary from './components/ErrorBoundary';
import RouteErrorBoundary from './components/ErrorBoundary/RouteErrorBoundary';
import HomePage from './pages/Home';
import ProjectsPage from './pages/Projects';
import EditorPage from './pages/Editor';
import DragModelBuilder from './components/DragModelBuilder';
import ResultsPage from './pages/Results';
import MapPage from './pages/Map';
import PluginsPage from './pages/Plugins';
import SimulationPage from './pages/Simulation';
import NotFoundPage from './pages/NotFound';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';
import MainLayout from './components/Layout/MainLayout';
import useAuthStore from '@/stores/authStore';

// Protected route wrapper - redirects to /login if not authenticated
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
      }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// Public route wrapper - redirects to / if already authenticated
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          }
        />

        {/* Protected routes wrapped in MainLayout */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<HomePage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/projects" element={<ProjectsPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/editor" element={<EditorPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/editor/:projectId" element={<EditorPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/drag-model" element={<DragModelBuilder />} errorElement={<RouteErrorBoundary />} />
          <Route path="/results" element={<ResultsPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/results/:jobId" element={<ResultsPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/simulation/:jobId" element={<SimulationPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/map" element={<MapPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="/plugins" element={<PluginsPage />} errorElement={<RouteErrorBoundary />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export default App;
