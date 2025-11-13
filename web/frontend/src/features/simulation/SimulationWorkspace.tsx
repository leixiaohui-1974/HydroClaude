import { useState } from 'react';
import { Row, Col, Card, Tabs, Button, Space, message } from 'antd';
import { AppstoreOutlined, BarChartOutlined, PlusOutlined } from '@ant-design/icons';
import SimulationConfigForm from './SimulationConfigForm';
import SimulationResults from './SimulationResults';
import ComparisonView from './components/ComparisonView';
import { SimulationResultResponse } from '@/services/api';
import type { ComparisonScenario } from '@/types/comparison';

const SimulationWorkspace = () => {
  const [_currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [simulationResult, setSimulationResult] = useState<SimulationResultResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'single' | 'comparison'>('single');
  const [scenarios, setScenarios] = useState<ComparisonScenario[]>([]);

  const handleSimulationComplete = (taskId: string, result: SimulationResultResponse) => {
    setCurrentTaskId(taskId);
    setSimulationResult(result);
  };

  // Add current result to comparison scenarios
  const handleAddToComparison = () => {
    if (!simulationResult) {
      message.warning('没有仿真结果可添加到对比');
      return;
    }

    const newScenario: ComparisonScenario = {
      id: `scenario-${Date.now()}`,
      name: `场景 ${scenarios.length + 1}`,
      description: `任务ID: ${simulationResult.task_id}`,
      result: simulationResult,
      color: getScenarioColor(scenarios.length),
      visible: true
    };

    setScenarios([...scenarios, newScenario]);
    message.success(`已添加到对比 (${scenarios.length + 1}个场景)`);
  };

  // Handle scenarios change from ComparisonView
  const handleScenariosChange = (updatedScenarios: ComparisonScenario[]) => {
    setScenarios(updatedScenarios);
  };

  // Clear all scenarios
  const handleClearScenarios = () => {
    setScenarios([]);
    message.info('已清空所有对比场景');
  };

  // Get color for scenario based on index
  const getScenarioColor = (index: number): string => {
    const colors = ['#1890ff', '#52c41a', '#fa8c16', '#eb2f96', '#722ed1', '#13c2c2'];
    return colors[index % colors.length];
  };

  const tabItems = [
    {
      key: 'single',
      label: (
        <span>
          <AppstoreOutlined />
          单场景结果
        </span>
      ),
      children: (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={10}>
            <Card title="仿真配置" variant="borderless">
              <SimulationConfigForm onSimulationComplete={handleSimulationComplete} />
            </Card>
          </Col>

          <Col xs={24} lg={14}>
            <Card
              title="仿真结果"
              variant="borderless"
              extra={
                simulationResult && (
                  <Button
                    type="primary"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={handleAddToComparison}
                  >
                    添加到对比
                  </Button>
                )
              }
            >
              {simulationResult ? (
                <SimulationResults result={simulationResult} />
              ) : (
                <div style={{
                  textAlign: 'center',
                  padding: '60px 20px',
                  color: '#999'
                }}>
                  <p>配置并运行仿真以查看结果</p>
                </div>
              )}
            </Card>
          </Col>
        </Row>
      )
    },
    {
      key: 'comparison',
      label: (
        <span>
          <BarChartOutlined />
          多场景对比 ({scenarios.length})
        </span>
      ),
      children: (
        <Card
          title={
            <Space>
              <BarChartOutlined />
              多场景对比分析
            </Space>
          }
          extra={
            scenarios.length > 0 && (
              <Button
                danger
                size="small"
                onClick={handleClearScenarios}
              >
                清空所有场景
              </Button>
            )
          }
          variant="borderless"
        >
          {scenarios.length >= 2 ? (
            <ComparisonView
              scenarios={scenarios}
              onScenariosChange={handleScenariosChange}
            />
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '60px 20px',
              color: '#999'
            }}>
              <BarChartOutlined style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }} />
              <p style={{ fontSize: 16, marginBottom: 8 }}>
                请添加至少2个仿真场景进行对比
              </p>
              <p style={{ fontSize: 14, color: '#bbb' }}>
                在"单场景结果"标签页运行仿真，然后点击"添加到对比"按钮
              </p>
              {scenarios.length === 1 && (
                <p style={{ fontSize: 14, color: '#1890ff', marginTop: 16 }}>
                  已添加 1 个场景，再添加至少 1 个场景即可开始对比
                </p>
              )}
            </div>
          )}
        </Card>
      )
    }
  ];

  return (
    <div style={{ padding: '0 24px' }}>
      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key as 'single' | 'comparison')}
        items={tabItems}
        size="large"
      />
    </div>
  );
};

export default SimulationWorkspace;
