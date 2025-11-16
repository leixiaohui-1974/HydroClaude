import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, message } from 'antd';
import ConfigEditor from '@/components/ConfigEditor';
import type { SimulationConfig } from '@/services/simulations';
import simulationService from '@/services/simulations';

const { Title } = Typography;

const EditorPage: React.FC = () => {
  const { projectId } = useParams<{ projectId?: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<SimulationConfig | undefined>();

  useEffect(() => {
    if (projectId && projectId !== 'new') {
      loadProject(projectId);
    }
  }, [projectId]);

  const loadProject = async (id: string) => {
    setLoading(true);
    try {
      // TODO: 从API加载项目配置
      // const project = await api.get(`/projects/${id}`);
      // setConfig(project.config);
      
      message.info('加载项目配置...');
    } catch (error) {
      message.error('加载项目失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (newConfig: SimulationConfig) => {
    try {
      // TODO: 保存到后端
      // if (projectId && projectId !== 'new') {
      //   await api.put(`/projects/${projectId}`, { config: newConfig });
      // } else {
      //   const result = await api.post('/projects', { config: newConfig });
      //   navigate(`/editor/${result.id}`);
      // }
      
      console.log('保存配置:', newConfig);
      message.success('配置已保存');
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleRun = async (newConfig: SimulationConfig) => {
    try {
      // 创建并运行仿真作业
      const job = await simulationService.createJob(newConfig, `仿真-${Date.now()}`);
      await simulationService.runJob(job.id);
      
      message.success('仿真已启动');
      navigate(`/simulation/${job.id}`);
    } catch (error) {
      message.error('启动仿真失败');
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
