import React from 'react';
import { Card, Typography } from 'antd';

const { Title, Paragraph } = Typography;

const SimulationPage: React.FC = () => {
  return (
    <Card>
      <Title level={2}>仿真执行</Title>
      <Paragraph>
        仿真执行和监控功能正在开发中...
      </Paragraph>
      <Paragraph>
        将支持：
        <ul>
          <li>一键启动仿真</li>
          <li>实时进度显示</li>
          <li>性能指标监控</li>
          <li>日志查看</li>
          <li>中断和恢复</li>
        </ul>
      </Paragraph>
    </Card>
  );
};

export default SimulationPage;
