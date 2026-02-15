import React, { useState } from 'react';
import { Card, Button, Tag, Rate, Space, Tooltip, Typography, Badge } from 'antd';
import {
  DownloadOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  SettingOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { MarketplacePlugin } from '@/types/plugin';
import './index.css';

const { Text, Paragraph } = Typography;

interface PluginCardProps {
  plugin: MarketplacePlugin;
  installed?: boolean;
  onInstall?: (plugin: MarketplacePlugin) => void;
  onUninstall?: (pluginId: string) => void;
  onConfigure?: (pluginId: string) => void;
  onViewDetails?: (plugin: MarketplacePlugin) => void;
}

/**
 * 插件卡片组件
 * 
 * 功能：
 * - 显示插件基本信息
 * - 显示安装状态
 * - 提供安装/卸载操作
 * - 显示评分和下载量
 */
const PluginCard: React.FC<PluginCardProps> = ({
  plugin,
  installed = false,
  onInstall,
  onUninstall,
  onConfigure,
  onViewDetails,
}) => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);

  const handleInstall = async () => {
    if (!onInstall) return;
    setLoading(true);
    try {
      await onInstall(plugin);
    } finally {
      setLoading(false);
    }
  };

  const handleUninstall = async () => {
    if (!onUninstall) return;
    setLoading(true);
    try {
      await onUninstall(plugin.id);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigure = () => {
    if (onConfigure) {
      onConfigure(plugin.id);
    }
  };

  const handleViewDetails = () => {
    if (onViewDetails) {
      onViewDetails(plugin);
    }
  };

  // 格式化下载数
  const formatDownloads = (count: number): string => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K`;
    }
    return count.toString();
  };

  // 获取分类颜色
  const getCategoryColor = (category: string): string => {
    const colorMap: Record<string, string> = {
      optimization: 'blue',
      'data-processing': 'green',
      visualization: 'purple',
      'import-export': 'cyan',
      analysis: 'orange',
      automation: 'red',
      integration: 'magenta',
      theme: 'gold',
      extension: 'lime',
      other: 'default',
    };
    return colorMap[category] || 'default';
  };

  const cardContent = (
      <Card
        className="plugin-card"
        hoverable
        cover={
          plugin.icon ? (
            <div className="plugin-card-icon">
              <img src={plugin.icon} alt={plugin.name} />
            </div>
          ) : (
            <div className="plugin-card-icon-placeholder">
              <InfoCircleOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            </div>
          )
        }
        actions={[
          installed ? (
            <Tooltip title={t('common.configure')}>
              <SettingOutlined key="configure" onClick={handleConfigure} />
            </Tooltip>
          ) : null,
          <Tooltip title={t('pluginCard.viewDetails')}>
            <InfoCircleOutlined key="details" onClick={handleViewDetails} />
          </Tooltip>,
          installed ? (
            <Tooltip title={t('common.uninstall')}>
              <DeleteOutlined key="uninstall" onClick={handleUninstall} />
            </Tooltip>
          ) : (
            <Tooltip title={t('common.install')}>
              <DownloadOutlined key="install" onClick={handleInstall} />
            </Tooltip>
          ),
        ].filter(Boolean)}
      >
        <Card.Meta
          title={
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div className="plugin-card-title">
                <Text strong ellipsis>
                  {plugin.name}
                </Text>
                {installed && (
                  <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
                )}
              </div>
              <Space size={8}>
                <Tag color={getCategoryColor(plugin.category)}>{plugin.category}</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  v{plugin.version}
                </Text>
              </Space>
            </Space>
          }
          description={
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Paragraph
                ellipsis={{ rows: 2 }}
                style={{ marginBottom: 0, minHeight: 40 }}
              >
                {plugin.description}
              </Paragraph>

              <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
                <Space size={4}>
                  <Rate disabled defaultValue={plugin.rating} count={5} style={{ fontSize: 14 }} />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {plugin.rating.toFixed(1)}
                  </Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {formatDownloads(plugin.downloads)} {t('pluginCard.downloads')}
                </Text>
              </Space>

              <Space wrap>
                {plugin.keywords.slice(0, 3).map((keyword) => (
                  <Tag key={keyword} style={{ fontSize: 11 }}>
                    {keyword}
                  </Tag>
                ))}
              </Space>

              {installed ? (
                <Button
                  danger
                  icon={<DeleteOutlined />}
                  loading={loading}
                  onClick={handleUninstall}
                  block
                >
                  {t('pluginCard.uninstallPlugin')}
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  loading={loading}
                  onClick={handleInstall}
                  block
                >
                  {t('pluginCard.installPlugin')}
                </Button>
              )}
            </Space>
          }
        />
      </Card>
  );

  return installed ? (
    <Badge.Ribbon text={t('pluginCard.installed')} color="green">
      {cardContent}
    </Badge.Ribbon>
  ) : (
    cardContent
  );
};

export default PluginCard;
