import React from 'react';
import { Routes, Route } from 'react-router-dom';
import MainLayout from './components/Layout/MainLayout';
import HomePage from './pages/Home';
import ProjectsPage from './pages/Projects';
import EditorPage from './pages/Editor';
import SimulationPage from './pages/Simulation';
import ResultsPage from './pages/Results';
import MapPage from './pages/Map';
import PluginsPage from './pages/Plugins';
import NotFoundPage from './pages/NotFound';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<HomePage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="editor/:projectId?" element={<EditorPage />} />
        <Route path="simulation/:jobId?" element={<SimulationPage />} />
        <Route path="results/:jobId" element={<ResultsPage />} />
        <Route path="map" element={<MapPage />} />
        <Route path="plugins" element={<PluginsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};

export default App;
