import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, message } from 'antd';
import { useTranslation } from 'react-i18next';
import ConfigEditor from '@/components/ConfigEditor';
import api from '@/services/api';
import type { SimulationConfig } from '@/services/simulations';
import simulationService from '@/services/simulations';

const { Title } = Typography;

const EditorPage: React.FC = () => {
  const { t } = useTranslation();
  const { projectId } = useParams<{ projectId?: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<SimulationConfig | undefined>();
  const [projectName, setProjectName] = useState<string>('');

  useEffect(() => {
    if (projectId && projectId !== 'new') {
      loadProject(projectId);
    }
  }, [projectId]);

  const loadProject = async (id: string) => {
    setLoading(true);
    try {
      const project = await api.get(`/projects/${id}`);
      setConfig(project.config);
      setProjectName(project.name || '');
      message.success(t('editor.projectLoaded'));
    } catch {
      message.info(t('editor.projectLoadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (newConfig: SimulationConfig) => {
    try {
      if (projectId && projectId !== 'new') {
        await api.put(`/projects/${projectId}`, { config: newConfig });
        message.success(t('editor.configSaved'));
      } else {
        const result = await api.post('/projects', {
          name: projectName || `Project-${Date.now()}`,
          config: newConfig,
        });
        message.success(t('editor.configSaved'));
        navigate(`/editor/${result.id}`);
      }
    } catch {
      localStorage.setItem('hydroclaude_config', JSON.stringify(newConfig));
      message.success(t('editor.saveToLocalFallback'));
    }
  };

  const handleRun = async (newConfig: SimulationConfig) => {
    try {
      const job = await simulationService.createJob(newConfig, `Sim-${Date.now()}`);
      await simulationService.runJob(job.id);

      message.success(t('editor.simulationStarted'));
      navigate(`/simulation/${job.id}`);
    } catch {
      message.error(t('editor.runFailed'));
    }
  };

  if (loading) {
    return (
      <Card>
        <Spin tip={t('common.loading')} />
      </Card>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 140px)' }}>
      <Title level={2} style={{ marginBottom: 16 }}>
        {t('nav.editor')}
        {projectId && projectId !== 'new' && (
          <span style={{ fontSize: '14px', color: '#999', marginLeft: 16 }}>
            ID: {projectId}
          </span>
        )}
      </Title>

      <ConfigEditor
        initialConfig={config}
        onSave={handleSave}
        onRun={handleRun}
      />
    </div>
  );
};

export default EditorPage;
