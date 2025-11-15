import React from 'react';
import { Card, Typography } from 'antd';

const { Title, Paragraph } = Typography;

const PluginsPage: React.FC = () => {
  return (
    <Card>
      <Title level={2}>插件市场</Title>
      <Paragraph>
        插件市场功能正在开发中...
      </Paragraph>
      <Paragraph>
        将支持：
        <ul>
          <li>浏览可用插件</li>
          <li>一键安装/卸载</li>
          <li>插件评分和评论</li>
          <li>插件开发指南</li>
          <li>提交自己的插件</li>
        </ul>
      </Paragraph>
    </Card>
  );
};

export default PluginsPage;
