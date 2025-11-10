import { useState } from 'react';
import { Row, Col, Card } from 'antd';
import SimulationConfigForm from './SimulationConfigForm';
import SimulationResults from './SimulationResults';
import { SimulationResultResponse } from '@/services/api';

const SimulationWorkspace = () => {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [simulationResult, setSimulationResult] = useState<SimulationResultResponse | null>(null);

  const handleSimulationComplete = (taskId: string, result: SimulationResultResponse) => {
    setCurrentTaskId(taskId);
    setSimulationResult(result);
  };

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={10}>
        <Card title="仿真配置" bordered={false}>
          <SimulationConfigForm onSimulationComplete={handleSimulationComplete} />
        </Card>
      </Col>

      <Col xs={24} lg={14}>
        <Card title="仿真结果" bordered={false}>
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
  );
};

export default SimulationWorkspace;
