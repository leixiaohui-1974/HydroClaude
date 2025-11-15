import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Typography, Spin, Alert, Descriptions, Tag } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import ResultsViewer from '@/components/ResultsViewer';
import type { SimulationResults } from '@/services/simulations';
import simulationService from '@/services/simulations';

const { Title } = Typography;

const ResultsPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);

  useEffect(() => {
    if (jobId && jobId !== 'latest') {
      loadResults(jobId);
    } else {
      // 加载模拟数据用于演示
      loadMockResults();
    }
  }, [jobId]);

  const loadResults = async (id: string) => {
    setLoading(true);
    setError(null);

    try {
      const data = await simulationService.getResults(id);
      setResults(data.results);
    } catch (err: any) {
      setError(err.message || '加载结果失败');
    } finally {
      setLoading(false);
    }
  };

  // 模拟数据（演示用）
  const loadMockResults = () => {
    const positions = Array.from({ length: 101 }, (_, i) => i * 10);
    const depths = positions.map(x => 3 + 0.5 * Math.sin(x / 100) + Math.random() * 0.1);
    const velocities = positions.map(x => 1.5 + 0.3 * Math.cos(x / 150) + Math.random() * 0.05);
    const froude_numbers = depths.map((h, i) => velocities[i] / Math.sqrt(9.81 * h));

    const mockResults = {
      metadata: {
        simulation_type: 'steady',
        case_name: '渠道稳态流分析',
        timestamp: new Date().toISOString(),
        solver: 'hydrostatic',
        convergence: {
          iterations: 5,
          error: 0.000001,
        },
      },
      spatial: {
        positions,
        depths,
        velocities,
        froude_numbers,
        discharge: velocities.map((v, i) => v * depths[i] * 10), // Q = V * A, 假设宽度10m
      },
    };

    setResults(mockResults);
  };

  if (loading) {
    return (
      <Card>
        <Spin tip="加载结果中..." size="large" />
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
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
      {/* 结果摘要 */}
      <Card style={{ marginBottom: 16 }}>
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
              <Descriptions.Item label="迭代次数">
                {results.metadata.convergence.iterations} 次
              </Descriptions.Item>
              <Descriptions.Item label="收敛误差">
                {results.metadata.convergence.error?.toExponential(2)}
              </Descriptions.Item>
            </>
          )}
          <Descriptions.Item label="数据点数" span={2}>
            {results.spatial.positions.length} 个空间节点
            {results.temporal && ` × ${results.temporal.times.length} 个时间步`}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 结果可视化 */}
      <ResultsViewer results={results} />
    </div>
  );
};

export default ResultsPage;
