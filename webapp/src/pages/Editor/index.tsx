import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, message } from 'antd';
import ConfigEditor from '@/components/ConfigEditor';
import api from '@/services/api';
import type { SimulationConfig } from '@/services/simulations';
import simulationService from '@/services/simulations';

const { Title } = Typography;

const EditorPage: React.FC = () => {
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
      message.success('项目配置已加载');
    } catch (error) {
      console.warn('从后端加载项目失败，使用本地模式:', error);
      message.info('使用本地编辑模式');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (newConfig: SimulationConfig) => {
    try {
      if (projectId && projectId !== 'new') {
        await api.put(`/projects/${projectId}`, { config: newConfig });
        message.success('项目已保存');
      } else {
        const result = await api.post('/projects', {
          name: projectName || `项目-${Date.now()}`,
          config: newConfig,
        });
        message.success('项目已创建');
        navigate(`/editor/${result.id}`);
      }
    } catch (error) {
      // 后端不可用时降级为本地保存
      console.warn('保存到后端失败，本地保存:', error);
      localStorage.setItem('hydroclaude_config', JSON.stringify(newConfig));
      message.success('配置已本地保存');
    }
  };

  const handleRun = async (newConfig: SimulationConfig) => {
    try {
      const job = await simulationService.createJob(newConfig, `仿真-${Date.now()}`);
      await simulationService.runJob(job.id);

      message.success('仿真已启动');
      navigate(`/simulation/${job.id}`);
    } catch (error) {
      message.error('启动仿真失败，请确保后端服务运行中');
    }
  };

  if (loading) {
    return (
      <Card>
        <Spin tip="加载中..." />
      </Card>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 140px)' }}>
      <Title level={2} style={{ marginBottom: 16 }}>
        配置编辑器
        {projectId && projectId !== 'new' && (
          <span style={{ fontSize: '14px', color: '#999', marginLeft: 16 }}>
            项目ID: {projectId}
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
