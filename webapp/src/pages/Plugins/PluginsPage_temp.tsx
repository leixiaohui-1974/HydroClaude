import React from 'react';
import { Layout, Result, Button, Typography } from 'antd';
import { RocketOutlined } from '@ant-design/icons';

const { Content } = Layout;
const { Paragraph } = Typography;

/**
 * 插件市场临时页面
 * Phase 5.3开发中
 */
const PluginsPageTemp: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '50px' }}>
        <Result
          icon={<RocketOutlined style={{ color: '#1890ff' }} />}
          title="插件市场即将推出"
          subTitle="Phase 5.3: 插件系统正在开发中..."
          extra={[
            <Paragraph key="info" style={{ textAlign: 'left', maxWidth: 600, margin: '0 auto' }}>
              <strong>即将推出的功能：</strong>
              <ul>
                <li>✅ 插件接口设计（已完成）</li>
                <li>✅ 插件管理器（已完成）</li>
                <li>✅ 插件API（已完成）</li>
                <li>🔄 插件市场UI（开发中）</li>
                <li>⏳ 示例插件</li>
                <li>⏳ 开发者文档</li>
              </ul>
              <br />
              <strong>预计完成时间：</strong> 2025-12-15
            </Paragraph>,
          ]}
        />
      </Content>
    </Layout>
  );
};

export default PluginsPageTemp;
