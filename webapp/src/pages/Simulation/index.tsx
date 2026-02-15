import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Progress, Button, Space, Tag, Descriptions, Alert, Spin, message } from 'antd';
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  BarChartOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import simulationService, { SimulationJob } from '@/services/simulations';

const { Title, Text } = Typography;

const SimulationPage: React.FC = () => {
  const { t } = useTranslation();
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<SimulationJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<string[]>([]);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (jobId) {
      loadJob(jobId);
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [jobId]);

  useEffect(() => {
    if (job && (job.status === 'running' || job.status === 'pending')) {
      startPolling();
    } else {
      stopPolling();
    }
  }, [job?.status]);

  const loadJob = async (id: string) => {
    setLoading(true);
    try {
      const data = await simulationService.getJob(id);
      setJob(data);
      addLog(t('simulation.jobLoaded', { name: data.name, status: getStatusText(data.status) }));
    } catch (err: any) {
      message.error(t('simulation.loadFailed'));
      addLog(t('simulation.loadFailedMsg', { msg: err.message }));
    } finally {
      setLoading(false);
    }
  };

  const startPolling = () => {
    if (pollingRef.current) return;
    pollingRef.current = setInterval(async () => {
      if (!jobId) return;
      try {
        const data = await simulationService.getJob(jobId);
        setJob(data);
        if (data.status === 'running') {
          addLog(t('simulation.progressLog', { progress: (data.progress ?? 0).toFixed(1) }));
        }
        if (data.status === 'completed') {
          addLog(t('simulation.simCompleted'));
          message.success(t('simulation.simCompletedMsg'));
          stopPolling();
        }
        if (data.status === 'failed') {
          addLog(t('simulation.simFailedLog', { error: data.error || t('simulation.unknownError') }));
          message.error(t('simulation.simFailedMsg'));
          stopPolling();
        }
      } catch {
        // Continue polling on network errors
      }
    }, 2000);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const addLog = (msg: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-49), `[${timestamp}] ${msg}`]);
  };

  const handleRerun = async () => {
    if (!jobId) return;
    try {
      await simulationService.runJob(jobId);
      addLog(t('simulation.restarted'));
      message.info(t('simulation.restartedMsg'));
      loadJob(jobId);
    } catch (err: any) {
      message.error(t('simulation.startFailed', { msg: err.message || t('simulation.unknownError') }));
    }
  };

  const handleViewResults = () => {
    navigate(`/results/${jobId}`);
  };

  const getStatusText = (s: string) => {
    const map: Record<string, string> = {
      pending: t('simulation.statusPending'),
      running: t('simulation.statusRunning'),
      completed: t('simulation.statusCompleted'),
      failed: t('simulation.statusFailed'),
    };
    return map[s] || s;
  };

  const getStatusTag = (s: string) => {
    const map: Record<string, { color: string; icon: React.ReactNode }> = {
      pending: { color: 'default', icon: <ClockCircleOutlined /> },
      running: { color: 'processing', icon: <LoadingOutlined /> },
      completed: { color: 'success', icon: <CheckCircleOutlined /> },
      failed: { color: 'error', icon: <CloseCircleOutlined /> },
    };
    const cfg = map[s] || { color: 'default', icon: null };
    return <Tag color={cfg.color} icon={cfg.icon}>{getStatusText(s)}</Tag>;
  };

  if (loading) {
    return (
      <Card>
        <Spin tip={t('simulation.loadingJob')} size="large" />
      </Card>
    );
  }

  if (!job) {
    return (
      <Card>
        <Alert
          message={t('simulation.jobNotFound')}
          description={t('simulation.jobNotFoundDesc')}
          type="error"
          showIcon
          action={
            <Button onClick={() => navigate('/projects')}>{t('simulation.backToProjects')}</Button>
          }
        />
      </Card>
    );
  }

  const isRunning = job.status === 'running' || job.status === 'pending';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';

  return (
    <div>
      <Title level={3}>
        <PlayCircleOutlined style={{ marginRight: 8 }} />
        {t('simulation.monitor')}
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label={t('simulation.jobName')}>{job.name}</Descriptions.Item>
          <Descriptions.Item label={t('simulation.status')}>{getStatusTag(job.status)}</Descriptions.Item>
          <Descriptions.Item label={t('simulation.jobId')}>{job.id}</Descriptions.Item>
          <Descriptions.Item label={t('simulation.createdTime')}>
            {job.created_at ? new Date(job.created_at).toLocaleString() : '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('simulation.startedTime')}>
            {job.started_at ? new Date(job.started_at).toLocaleString() : '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('simulation.completedTime')}>
            {job.completed_at ? new Date(job.completed_at).toLocaleString() : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={t('simulation.progress')} style={{ marginBottom: 16 }}>
        <Progress
          percent={Math.round(job.progress ?? 0)}
          status={isFailed ? 'exception' : isCompleted ? 'success' : 'active'}
          strokeWidth={20}
          format={(percent) => `${percent}%`}
        />
        {isRunning && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            {t('simulation.calculating')}
          </Text>
        )}
      </Card>

      {isFailed && job.error && (
        <Alert
          message={t('simulation.simFailed')}
          description={<pre style={{ maxHeight: 200, overflow: 'auto', fontSize: 12 }}>{job.error}</pre>}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Space>
          {isCompleted && (
            <Button
              type="primary"
              icon={<BarChartOutlined />}
              onClick={handleViewResults}
            >
              {t('simulation.viewResults')}
            </Button>
          )}
          {(isCompleted || isFailed) && (
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRerun}
            >
              {t('simulation.rerun')}
            </Button>
          )}
          <Button onClick={() => navigate('/projects')}>{t('simulation.backToProjects')}</Button>
        </Space>
      </Card>

      <Card title={t('simulation.runLogs')} style={{ marginBottom: 16 }}>
        <div
          style={{
            maxHeight: 300,
            overflow: 'auto',
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: 16,
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 12,
            lineHeight: 1.6,
          }}
        >
          {logs.length === 0 ? (
            <Text style={{ color: '#666' }}>{t('simulation.noLogs')}</Text>
          ) : (
            logs.map((log, idx) => (
              <div key={idx}>{log}</div>
            ))
          )}
        </div>
      </Card>

      {job.config && (() => {
        const cfg = job.config as any;
        return (
          <Card title={t('simulation.configSummary')}>
            <Descriptions bordered column={2} size="small">
              {cfg.simulation && (
                <>
                  <Descriptions.Item label={t('simulation.simType')}>
                    {cfg.simulation.type || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('simulation.endTime')}>
                    {cfg.simulation.end_time || '-'} s
                  </Descriptions.Item>
                </>
              )}
              {cfg.canal && (
                <>
                  <Descriptions.Item label={t('simulation.canalLength')}>
                    {cfg.canal.length || '-'} m
                  </Descriptions.Item>
                  <Descriptions.Item label={t('simulation.canalWidth')}>
                    {cfg.canal.width || '-'} m
                  </Descriptions.Item>
                  <Descriptions.Item label={t('simulation.bottomSlope')}>
                    {cfg.canal.slope || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('simulation.manningCoeff')}>
                    {cfg.canal.manning_n || '-'}
                  </Descriptions.Item>
                </>
              )}
              {cfg.solver && (
                <>
                  <Descriptions.Item label={t('simulation.solverMethod')}>
                    {cfg.solver.method || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label={t('simulation.cflNumber')}>
                    {cfg.solver.cfl || '-'}
                  </Descriptions.Item>
                </>
              )}
            </Descriptions>
          </Card>
        );
      })()}
    </div>
  );
};

export default SimulationPage;
