import React from 'react';
import { Card, Typography } from 'antd';

const { Title, Paragraph } = Typography;

const EditorPage: React.FC = () => {
  return (
    <Card>
      <Title level={2}>配置编辑器</Title>
      <Paragraph>
        可视化配置编辑器功能正在开发中...
      </Paragraph>
      <Paragraph>
        将支持：
        <ul>
          <li>渠道参数可视化编辑</li>
          <li>边界条件设置</li>
          <li>水工结构添加和配置</li>
          <li>实时JSON预览</li>
          <li>配置验证</li>
        </ul>
      </Paragraph>
    </Card>
  );
};

export default EditorPage;
