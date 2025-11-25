import { Card, Typography, Space, Button, message, List, Tag, Progress } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';
import SimulationWorkspace from '@/features/simulation/SimulationWorkspace';
import { useState } from 'react';
import { api as testCaseApi, TestCase } from '@/services/test-cases-api';

const { Title, Text } = Typography;

type BatchResult = {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'passed' | 'failed';
  error?: string;
};

const SimulationPage = () => {
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [batchResults, setBatchResults] = useState<BatchResult[]>([]);

  const runAllCases = async () => {
    setIsBatchRunning(true);
    message.info('开始批量运行所有测试案例...');

    try {
      const response = await testCaseApi.getAllTestCases(550, 0);
      const cases = response.cases;
      const initialResults: BatchResult[] = cases.map(c => ({
        id: c.metadata.id,
        name: c.metadata.nameCN || c.metadata.name,
        status: 'pending',
      }));
      setBatchResults(initialResults);

      for (let i = 0; i < cases.length; i++) {
        const caseInfo = cases[i];

        // Update status to running
        setBatchResults(prev => prev.map(r => r.id === caseInfo.metadata.id ? { ...r, status: 'running' } : r));

        if (window.runSingleTestCase) {
          try {
            await window.runSingleTestCase(caseInfo.metadata.id);
            setBatchResults(prev => prev.map(r => r.id === caseInfo.metadata.id ? { ...r, status: 'passed' } : r));
          } catch (e: any) {
            setBatchResults(prev => prev.map(r => r.id === caseInfo.metadata.id ? { ...r, status: 'failed', error: e.message } : r));
          }
        }
      }
      message.success('所有测试案例运行完毕！');
    } catch (error) {
      message.error('获取测试案例列表或运行时发生严重错误');
    } finally {
      setIsBatchRunning(false);
    }
  };

  const passedCount = batchResults.filter(r => r.status === 'passed').length;
  const failedCount = batchResults.filter(r => r.status === 'failed').length;
  const totalCount = batchResults.length;
  const progressPercent = totalCount > 0 ? Math.round(((passedCount + failedCount) / totalCount) * 100) : 0;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title={<Title level={2} style={{ margin: 0 }}>⚗️ 仿真计算与端到端测试</Title>}
        extra={
          <Button
            id="run-all-cases-button"
            type="primary"
            icon={<ExperimentOutlined />}
            loading={isBatchRunning}
            onClick={runAllCases}
            disabled={isBatchRunning}
          >
            {isBatchRunning ? `运行中 (${passedCount + failedCount}/${totalCount})` : '一键运行所有案例'}
          </Button>
        }
      >
        {isBatchRunning && (
          <Progress percent={progressPercent} status={failedCount > 0 ? 'exception' : 'success'} />
        )}
        {batchResults.length > 0 && (
          <List
            header={<div>批量测试结果</div>}
            bordered
            dataSource={batchResults}
            renderItem={item => (
              <List.Item>
                <Text style={{ flex: 1 }}>{item.name} ({item.id})</Text>
                <Tag color={item.status === 'passed' ? 'success' : item.status === 'failed' ? 'error' : 'processing'}>
                  {item.status}
                </Tag>
              </List.Item>
            )}
          />
        )}
      </Card>

      <SimulationWorkspace />
    </Space>
  );
};

export default SimulationPage;
