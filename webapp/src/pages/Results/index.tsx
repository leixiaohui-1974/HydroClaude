import React from 'react';
import { Card, Typography } from 'antd';

const { Title, Paragraph } = Typography;

const ResultsPage: React.FC = () => {
  return (
    <Card>
      <Title level={2}>结果查看</Title>
      <Paragraph>
        交互式结果查看器正在开发中...
      </Paragraph>
      <Paragraph>
        将支持：
        <ul>
          <li>Plotly交互式图表</li>
          <li>数据表格展示</li>
          <li>3D水面可视化</li>
          <li>动画播放（非恒定流）</li>
          <li>多格式导出</li>
        </ul>
      </Paragraph>
    </Card>
  );
};

export default ResultsPage;
