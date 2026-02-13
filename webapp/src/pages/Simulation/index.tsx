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
import simulationService, { SimulationJob } from '@/services/simulations';

const { Title, Text } = Typography;

const SimulationPage: React.FC = () => {
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
      addLog(`已加载作业: ${data.name} (状态: ${getStatusText(data.status)})`);
    } catch (err: any) {
      message.error('加载作业失败');
      addLog(`加载失败: ${err.message}`);
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
          addLog(`进度: ${(data.progress ?? 0).toFixed(1)}%`);
        }
        if (data.status === 'completed') {
          addLog('仿真计算完成！');
          message.success('仿真完成');
          stopPolling();
        }
        if (data.status === 'failed') {
          addLog(`仿真失败: ${data.error || '未知错误'}`);
          message.error('仿真失败');
          stopPolling();
        }
      } catch {
        // 网络错误时继续轮询
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
    const timestamp = new Date().toLocaleTimeString('zh-CN');
    setLogs(prev => [...prev.slice(-49), `[${timestamp}] ${msg}`]);
  };

  const handleRerun = async () => {
    if (!jobId) return;
    try {
      await simulationService.runJob(jobId);
      addLog('已重新启动仿真...');
      message.info('仿真已重新启动');
      loadJob(jobId);
    } catch (err: any) {
      message.error('启动失败: ' + (err.message || '未知错误'));
    }
  };

  const handleViewResults = () => {
    navigate(`/results/${jobId}`);
  };

  const getStatusText = (s: string) => {
    const map: Record<string, string> = {
      pending: '待运行',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
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
        <Spin tip="加载作业信息..." size="large" />
      </Card>
    );
  }

  if (!job) {
    return (
      <Card>
        <Alert
          message="作业不存在"
          description="未找到指定的仿真作业，请检查ID是否正确。"
          type="error"
          showIcon
          action={
            <Button onClick={() => navigate('/projects')}>返回项目列表</Button>
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
        仿真执行监控
      </Title>

      {/* 作业信息卡片 */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="作业名称">{job.name}</Descriptions.Item>
          <Descriptions.Item label="状态">{getStatusTag(job.status)}</Descriptions.Item>
          <Descriptions.Item label="作业ID">{job.id}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {job.created_at ? new Date(job.created_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {job.started_at ? new Date(job.started_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {job.completed_at ? new Date(job.completed_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 进度条 */}
      <Card title="仿真进度" style={{ marginBottom: 16 }}>
        <Progress
          percent={Math.round(job.progress ?? 0)}
          status={isFailed ? 'exception' : isCompleted ? 'success' : 'active'}
          strokeWidth={20}
          format={(percent) => `${percent}%`}
        />
        {isRunning && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            正在计算中，请稍候...
          </Text>
        )}
      </Card>

      {/* 错误信息 */}
      {isFailed && job.error && (
        <Alert
          message="仿真失败"
          description={<pre style={{ maxHeight: 200, overflow: 'auto', fontSize: 12 }}>{job.error}</pre>}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 操作按钮 */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          {isCompleted && (
            <Button
              type="primary"
              icon={<BarChartOutlined />}
              onClick={handleViewResults}
            >
              查看结果
            </Button>
          )}
          {(isCompleted || isFailed) && (
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRerun}
            >
              重新运行
            </Button>
          )}
          <Button onClick={() => navigate('/projects')}>返回项目列表</Button>
        </Space>
      </Card>

      {/* 运行日志 */}
      <Card title="运行日志" style={{ marginBottom: 16 }}>
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
            <Text style={{ color: '#666' }}>暂无日志...</Text>
          ) : (
            logs.map((log, idx) => (
              <div key={idx}>{log}</div>
            ))
          )}
        </div>
      </Card>

      {/* 配置概要 */}
      {job.config && (() => {
        const cfg = job.config as any;
        return (
          <Card title="仿真配置概要">
            <Descriptions bordered column={2} size="small">
              {cfg.simulation && (
                <>
                  <Descriptions.Item label="仿真类型">
                    {cfg.simulation.type || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="结束时间">
                    {cfg.simulation.end_time || '-'} s
                  </Descriptions.Item>
                </>
              )}
              {cfg.canal && (
                <>
                  <Descriptions.Item label="渠道长度">
                    {cfg.canal.length || '-'} m
                  </Descriptions.Item>
                  <Descriptions.Item label="渠道宽度">
                    {cfg.canal.width || '-'} m
                  </Descriptions.Item>
                  <Descriptions.Item label="底坡">
                    {cfg.canal.slope || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Manning系数">
                    {cfg.canal.manning_n || '-'}
                  </Descriptions.Item>
                </>
              )}
              {cfg.solver && (
                <>
                  <Descriptions.Item label="求解方法">
                    {cfg.solver.method || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="CFL数">
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
