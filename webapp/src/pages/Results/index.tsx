import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Alert, Descriptions, Tag, Button, Space } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import ResultsViewer from '@/components/ResultsViewer';
import simulationService from '@/services/simulations';

const { Title } = Typography;

/**
 * 将后端仿真结果转换为 ResultsViewer 期望的格式
 */
function transformResults(apiResult: any): any {
  const summary = apiResult.summary || {};
  const timeSeries = apiResult.time_series || {};
  const metadata = apiResult.solver_metadata || {};

  const positions = timeSeries.x || [];
  const h_final = timeSeries.h_final || [];
  const Q_final = timeSeries.Q_final || [];

  const width = 10.0;
  const velocities = h_final.map((h: number, i: number) => {
    if (h < 1e-6) return 0;
    return Q_final[i] / (h * width);
  });
  const froude_numbers = h_final.map((h: number, i: number) => {
    if (h < 1e-6) return 0;
    return Math.abs(velocities[i]) / Math.sqrt(9.81 * h);
  });

  return {
    metadata: {
      simulation_type: 'unsteady',
      case_name: `仿真结果 #${apiResult.job_id}`,
      timestamp: apiResult.created_at || new Date().toISOString(),
      solver: metadata.solver || 'godunov_fvm',
      convergence: {
        iterations: summary.total_steps || 0,
        error: summary.mass_error_percent || 0,
      },
    },
    spatial: {
      positions,
      depths: h_final,
      velocities,
      froude_numbers,
      discharge: Q_final,
    },
  };
}

const ResultsPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [apiResult, setApiResult] = useState<any>(null);

  useEffect(() => {
    if (jobId && jobId !== 'latest') {
      loadResults(jobId);
    } else {
      loadMockResults();
    }
  }, [jobId]);

  const loadResults = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await simulationService.getResults(id);
      setApiResult(data);
      setResults(transformResults(data));
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || '加载结果失败';
      if (msg.includes('not completed')) {
        setError('仿真尚未完成，请等待计算完成后查看结果');
      } else {
        setError(msg);
        loadMockResults();
      }
    } finally {
      setLoading(false);
    }
  };

  const loadMockResults = () => {
    const positions = Array.from({ length: 101 }, (_, i) => i * 10);
    const depths = positions.map(x => 3 + 0.5 * Math.sin(x / 100) + Math.random() * 0.1);
    const velocities = positions.map(x => 1.5 + 0.3 * Math.cos(x / 150) + Math.random() * 0.05);
    const froude_numbers = depths.map((h, i) => velocities[i] / Math.sqrt(9.81 * h));

    setResults({
      metadata: {
        simulation_type: 'steady',
        case_name: '渠道稳态流分析（演示数据）',
        timestamp: new Date().toISOString(),
        solver: 'hydrostatic',
        convergence: { iterations: 5, error: 0.000001 },
      },
      spatial: {
        positions,
        depths,
        velocities,
        froude_numbers,
        discharge: velocities.map((v, i) => v * depths[i] * 10),
      },
    });
  };

  if (loading) {
    return (
      <Card>
        <Spin tip="加载结果中..." size="large" />
      </Card>
    );
  }

  if (error && !results) {
    return (
      <Card>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          action={
            <Space>
              <Button onClick={() => navigate(-1)}>返回</Button>
              {jobId && <Button type="primary" onClick={() => loadResults(jobId)}>重试</Button>}
            </Space>
          }
        />
      </Card>
    );
  }

  if (!results) {
    return (
      <Card>
        <Alert
          message="暂无结果"
          description="请先运行仿真或选择一个已完成的作业"
          type="info"
          showIcon
        />
      </Card>
    );
  }

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        </Space>

        <Title level={3}>
          <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
          仿真结果
        </Title>

        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="场景名称">
            {results.metadata.case_name}
          </Descriptions.Item>
          <Descriptions.Item label="仿真类型">
            <Tag color={results.metadata.simulation_type === 'steady' ? 'blue' : 'purple'}>
              {results.metadata.simulation_type === 'steady' ? '稳态流' : '非恒定流'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="求解器">
            {results.metadata.solver || 'hydrostatic'}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {new Date(results.metadata.timestamp).toLocaleString('zh-CN')}
          </Descriptions.Item>
          {results.metadata.convergence && (
            <>
              <Descriptions.Item label="总步数">
                {results.metadata.convergence.iterations} 步
              </Descriptions.Item>
              <Descriptions.Item label="质量误差">
                {results.metadata.convergence.error?.toExponential(2)}
              </Descriptions.Item>
            </>
          )}
          <Descriptions.Item label="数据点数" span={2}>
            {results.spatial.positions.length} 个空间节点
            {results.temporal && ` × ${results.temporal.times.length} 个时间步`}
          </Descriptions.Item>
          {apiResult?.summary && (
            <>
              <Descriptions.Item label="最大水深">
                {apiResult.summary.h_max?.toFixed(4)} m
              </Descriptions.Item>
              <Descriptions.Item label="最小水深">
                {apiResult.summary.h_min?.toFixed(4)} m
              </Descriptions.Item>
              <Descriptions.Item label="平均水深">
                {apiResult.summary.h_mean?.toFixed(4)} m
              </Descriptions.Item>
              <Descriptions.Item label="计算稳定性">
                <Tag color={apiResult.summary.stable ? 'success' : 'error'}>
                  {apiResult.summary.stable ? '稳定' : '不稳定'}
                </Tag>
              </Descriptions.Item>
            </>
          )}
        </Descriptions>
      </Card>

      <ResultsViewer results={results} />
    </div>
  );
};

export default ResultsPage;
