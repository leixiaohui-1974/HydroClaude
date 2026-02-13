import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Alert, Descriptions, Tag, Button, Space } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ResultsViewer from '@/components/ResultsViewer';
import simulationService from '@/services/simulations';

const { Title } = Typography;

/**
 * Transform backend simulation results to ResultsViewer expected format
 */
function transformResults(apiResult: any, t: (key: string, opts?: any) => string): any {
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
      case_name: t('results.simResultId', { id: apiResult.job_id }),
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
  const { t } = useTranslation();
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
      setResults(transformResults(data, t));
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || t('results.loadError');
      if (msg.includes('not completed')) {
        setError(t('results.notCompleted'));
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
        case_name: t('results.demoData'),
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
        <Spin tip={t('results.loading')} size="large" />
      </Card>
    );
  }

  if (error && !results) {
    return (
      <Card>
        <Alert
          message={t('results.loadFailed')}
          description={error}
          type="error"
          showIcon
          action={
            <Space>
              <Button onClick={() => navigate(-1)}>{t('results.back')}</Button>
              {jobId && <Button type="primary" onClick={() => loadResults(jobId)}>{t('results.retry')}</Button>}
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
          message={t('results.noResults')}
          description={t('results.noResultsDesc')}
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
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>{t('results.back')}</Button>
        </Space>

        <Title level={3}>
          <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
          {t('results.simulationResults')}
        </Title>

        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label={t('results.sceneName')}>
            {results.metadata.case_name}
          </Descriptions.Item>
          <Descriptions.Item label={t('results.simType')}>
            <Tag color={results.metadata.simulation_type === 'steady' ? 'blue' : 'purple'}>
              {results.metadata.simulation_type === 'steady' ? t('results.steadyFlow') : t('results.unsteadyFlow')}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('results.solver')}>
            {results.metadata.solver || 'hydrostatic'}
          </Descriptions.Item>
          <Descriptions.Item label={t('results.completionTime')}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {new Date(results.metadata.timestamp).toLocaleString()}
          </Descriptions.Item>
          {results.metadata.convergence && (
            <>
              <Descriptions.Item label={t('results.totalSteps')}>
                {results.metadata.convergence.iterations} {t('results.stepsUnit')}
              </Descriptions.Item>
              <Descriptions.Item label={t('results.massError')}>
                {results.metadata.convergence.error?.toExponential(2)}
              </Descriptions.Item>
            </>
          )}
          <Descriptions.Item label={t('results.dataPoints')} span={2}>
            {results.spatial.positions.length} {t('results.spatialNodes')}
            {results.temporal && ` × ${results.temporal.times.length} ${t('results.timeSteps')}`}
          </Descriptions.Item>
          {apiResult?.summary && (
            <>
              <Descriptions.Item label={t('results.maxDepth')}>
                {apiResult.summary.h_max?.toFixed(4)} m
              </Descriptions.Item>
              <Descriptions.Item label={t('results.minDepth')}>
                {apiResult.summary.h_min?.toFixed(4)} m
              </Descriptions.Item>
              <Descriptions.Item label={t('results.avgDepth')}>
                {apiResult.summary.h_mean?.toFixed(4)} m
              </Descriptions.Item>
              <Descriptions.Item label={t('results.stability')}>
                <Tag color={apiResult.summary.stable ? 'success' : 'error'}>
                  {apiResult.summary.stable ? t('results.stable') : t('results.unstable')}
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
