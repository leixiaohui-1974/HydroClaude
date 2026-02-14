import React, { useState, useEffect } from 'react';
import { Layout, Input, Select, Row, Col, Spin, Empty, Space, Typography, Card, Statistic, Modal, Descriptions, Tag, Button, message } from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  AppstoreOutlined,
  DownloadOutlined,
  StarOutlined,
  GithubOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { MarketplacePlugin, PluginSearchOptions } from '@/types/plugin';
import PluginCard from '@/components/PluginCard';
import { pluginManager } from '@/services/pluginManager';
import './index.css';

const { Content } = Layout;
const { Text, Paragraph } = Typography;

const PluginsPage: React.FC = () => {
  const { t } = useTranslation();
  const [plugins, setPlugins] = useState<MarketplacePlugin[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchOptions, setSearchOptions] = useState<PluginSearchOptions>({
    query: '',
    category: undefined,
    sortBy: 'downloads',
    page: 1,
    pageSize: 12,
  });
  const [installedPlugins, setInstalledPlugins] = useState<Set<string>>(new Set());
  const [detailPlugin, setDetailPlugin] = useState<MarketplacePlugin | null>(null);
  const [configPluginId, setConfigPluginId] = useState<string | null>(null);

  const mockPlugins: MarketplacePlugin[] = [
    {
      id: 'parameter-optimization',
      name: 'Parameter Optimization',
      version: '1.2.0',
      description: t('plugins.descOptimization'),
      author: 'HydroClaude Team',
      icon: 'https://via.placeholder.com/80/667eea/ffffff?text=OPT',
      category: 'optimization',
      keywords: ['optimization', 'genetic algorithm', 'parameters'],
      rating: 4.8,
      downloads: 15420,
      lastUpdated: new Date('2025-11-10'),
      homepage: 'https://hydroclaude.com/plugins/optimization',
      repository: 'https://github.com/hydroclaude/plugin-optimization',
    },
    {
      id: 'data-import-excel',
      name: 'Excel Data Import',
      version: '2.0.1',
      description: t('plugins.descExcelImport'),
      author: 'Community',
      icon: 'https://via.placeholder.com/80/52c41a/ffffff?text=XLS',
      category: 'import-export',
      keywords: ['import', 'Excel', 'data'],
      rating: 4.6,
      downloads: 23100,
      lastUpdated: new Date('2025-11-12'),
      homepage: 'https://hydroclaude.com/plugins/excel-import',
    },
    {
      id: 'visualization-3d',
      name: '3D Visualization',
      version: '0.9.5',
      description: t('plugins.desc3dViz'),
      author: 'VizTeam',
      icon: 'https://via.placeholder.com/80/722ed1/ffffff?text=3D',
      category: 'visualization',
      keywords: ['3D', 'visualization', 'Three.js'],
      rating: 4.5,
      downloads: 8720,
      lastUpdated: new Date('2025-11-08'),
      repository: 'https://github.com/hydroclaude/plugin-3d-viz',
    },
    {
      id: 'report-generator',
      name: 'Report Generator',
      version: '1.0.0',
      description: t('plugins.descReportGen'),
      author: 'ReportTeam',
      icon: 'https://via.placeholder.com/80/fa8c16/ffffff?text=PDF',
      category: 'extension',
      keywords: ['report', 'PDF', 'Word'],
      rating: 4.3,
      downloads: 12500,
      lastUpdated: new Date('2025-11-05'),
    },
    {
      id: 'hdf5-importer',
      name: 'HDF5 Data Processing',
      version: '1.5.2',
      description: t('plugins.descHdf5'),
      author: 'DataTeam',
      icon: 'https://via.placeholder.com/80/13c2c2/ffffff?text=HDF',
      category: 'data-processing',
      keywords: ['HDF5', 'big data', 'import/export'],
      rating: 4.7,
      downloads: 9800,
      lastUpdated: new Date('2025-11-11'),
    },
    {
      id: 'sensitivity-analysis',
      name: 'Sensitivity Analysis',
      version: '2.1.0',
      description: t('plugins.descSensitivity'),
      author: 'AnalysisTeam',
      icon: 'https://via.placeholder.com/80/eb2f96/ffffff?text=SEN',
      category: 'analysis',
      keywords: ['sensitivity', 'analysis', 'parameters'],
      rating: 4.9,
      downloads: 6540,
      lastUpdated: new Date('2025-11-13'),
    },
  ];

  useEffect(() => {
    loadPlugins();
    loadInstalledPlugins();
  }, [searchOptions]);

  const loadPlugins = async () => {
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
      let filtered = [...mockPlugins];

      if (searchOptions.query) {
        const query = searchOptions.query.toLowerCase();
        filtered = filtered.filter(
          (p) =>
            p.name.toLowerCase().includes(query) ||
            p.description.toLowerCase().includes(query) ||
            p.keywords.some((k) => k.toLowerCase().includes(query))
        );
      }

      if (searchOptions.category) {
        filtered = filtered.filter((p) => p.category === searchOptions.category);
      }

      switch (searchOptions.sortBy) {
        case 'downloads':
          filtered.sort((a, b) => b.downloads - a.downloads);
          break;
        case 'rating':
          filtered.sort((a, b) => b.rating - a.rating);
          break;
        case 'updated':
          filtered.sort((a, b) => b.lastUpdated.getTime() - a.lastUpdated.getTime());
          break;
        case 'name':
          filtered.sort((a, b) => a.name.localeCompare(b.name));
          break;
      }

      setPlugins(filtered);
    } finally {
      setLoading(false);
    }
  };

  const loadInstalledPlugins = () => {
    const installed = pluginManager.getAllPlugins().map((p) => p.manifest.id);
    setInstalledPlugins(new Set(installed));
  };

  const handleInstall = async (plugin: MarketplacePlugin) => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setInstalledPlugins((prev) => new Set([...prev, plugin.id]));
      message.success(t('plugins.installSuccess'));
    } catch {
      message.error(t('plugins.installFailed'));
    }
  };

  const handleUninstall = async (pluginId: string) => {
    try {
      await pluginManager.uninstall(pluginId);
      setInstalledPlugins((prev) => {
        const newSet = new Set(prev);
        newSet.delete(pluginId);
        return newSet;
      });
      message.success(t('plugins.uninstallSuccess'));
    } catch {
      message.error(t('plugins.uninstallFailed'));
    }
  };

  const handleConfigure = (pluginId: string) => {
    setConfigPluginId(pluginId);
  };

  const handleViewDetails = (plugin: MarketplacePlugin) => {
    setDetailPlugin(plugin);
  };

  const stats = {
    total: mockPlugins.length,
    installed: installedPlugins.size,
    avgRating: (mockPlugins.reduce((sum, p) => sum + p.rating, 0) / mockPlugins.length).toFixed(1),
  };

  return (
    <Layout className="plugins-page">
      <Content className="plugins-content">
        <Card className="plugins-stats">
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title={t('plugins.availablePlugins')}
                value={stats.total}
                prefix={<AppstoreOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={t('plugins.installed')}
                value={stats.installed}
                prefix={<DownloadOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={t('plugins.averageRating')}
                value={stats.avgRating}
                prefix={<StarOutlined />}
                suffix="/ 5.0"
                valueStyle={{ color: '#fa8c16' }}
              />
            </Col>
          </Row>
        </Card>

        <Card className="plugins-search">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Input
              size="large"
              placeholder={t('plugins.searchPlaceholder')}
              prefix={<SearchOutlined />}
              value={searchOptions.query}
              onChange={(e) =>
                setSearchOptions({ ...searchOptions, query: e.target.value, page: 1 })
              }
              allowClear
            />

            <Space size="middle">
              <Space>
                <FilterOutlined />
                <Text>{t('plugins.category')}:</Text>
                <Select
                  style={{ width: 150 }}
                  placeholder={t('plugins.allCategories')}
                  value={searchOptions.category}
                  onChange={(category) =>
                    setSearchOptions({ ...searchOptions, category, page: 1 })
                  }
                  allowClear
                  options={[
                    { label: t('plugins.catOptimization'), value: 'optimization' },
                    { label: t('plugins.catDataProcessing'), value: 'data-processing' },
                    { label: t('plugins.catVisualization'), value: 'visualization' },
                    { label: t('plugins.catImportExport'), value: 'import-export' },
                    { label: t('plugins.catAnalysis'), value: 'analysis' },
                    { label: t('plugins.catAutomation'), value: 'automation' },
                    { label: t('plugins.catIntegration'), value: 'integration' },
                    { label: t('plugins.catExtension'), value: 'extension' },
                  ]}
                />
              </Space>

              <Space>
                <Text>{t('plugins.sortBy')}:</Text>
                <Select
                  style={{ width: 120 }}
                  value={searchOptions.sortBy}
                  onChange={(sortBy) => setSearchOptions({ ...searchOptions, sortBy })}
                  options={[
                    { label: t('plugins.sortDownloads'), value: 'downloads' },
                    { label: t('plugins.sortRating'), value: 'rating' },
                    { label: t('plugins.sortUpdated'), value: 'updated' },
                    { label: t('plugins.sortName'), value: 'name' },
                  ]}
                />
              </Space>
            </Space>
          </Space>
        </Card>

        <div className="plugins-list">
          <Spin spinning={loading}>
            {plugins.length > 0 ? (
              <Row gutter={[16, 16]}>
                {plugins.map((plugin) => (
                  <Col key={plugin.id} xs={24} sm={12} md={8} lg={6}>
                    <PluginCard
                      plugin={plugin}
                      installed={installedPlugins.has(plugin.id)}
                      onInstall={handleInstall}
                      onUninstall={handleUninstall}
                      onConfigure={handleConfigure}
                      onViewDetails={handleViewDetails}
                    />
                  </Col>
                ))}
              </Row>
            ) : (
              <Empty
                description={t('plugins.noPluginsFound')}
                style={{ marginTop: 64 }}
              />
            )}
          </Spin>
        </div>
      </Content>

      <Modal
        title={detailPlugin?.name}
        open={!!detailPlugin}
        onCancel={() => setDetailPlugin(null)}
        footer={
          detailPlugin && !installedPlugins.has(detailPlugin.id) ? (
            <Button type="primary" icon={<DownloadOutlined />} onClick={() => {
              handleInstall(detailPlugin);
              setDetailPlugin(null);
            }}>
              {t('plugins.installPlugin')}
            </Button>
          ) : null
        }
        width={600}
      >
        {detailPlugin && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Paragraph>{detailPlugin.description}</Paragraph>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label={t('plugins.version')}>v{detailPlugin.version}</Descriptions.Item>
              <Descriptions.Item label={t('plugins.author')}>{detailPlugin.author}</Descriptions.Item>
              <Descriptions.Item label={t('plugins.category')}>
                <Tag color="blue">{detailPlugin.category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('plugins.rating')}>{detailPlugin.rating} / 5.0</Descriptions.Item>
              <Descriptions.Item label={t('plugins.downloads')}>{detailPlugin.downloads.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label={t('plugins.updateTime')}>
                {detailPlugin.lastUpdated.toLocaleDateString()}
              </Descriptions.Item>
            </Descriptions>
            <Space>
              <Text strong>{t('plugins.keywords')}: </Text>
              {detailPlugin.keywords.map(kw => <Tag key={kw}>{kw}</Tag>)}
            </Space>
            {detailPlugin.repository && (
              <Space>
                <GithubOutlined />
                <a href={detailPlugin.repository} target="_blank" rel="noreferrer">{t('plugins.sourceRepo')}</a>
              </Space>
            )}
            {detailPlugin.homepage && (
              <Space>
                <LinkOutlined />
                <a href={detailPlugin.homepage} target="_blank" rel="noreferrer">{t('plugins.homepage')}</a>
              </Space>
            )}
          </Space>
        )}
      </Modal>

      <Modal
        title={t('plugins.pluginConfig')}
        open={!!configPluginId}
        onCancel={() => setConfigPluginId(null)}
        onOk={() => {
          message.success(t('plugins.configSaved'));
          setConfigPluginId(null);
        }}
      >
        <Paragraph>
          {t('plugins.pluginConfigOptions', { id: configPluginId })}
        </Paragraph>
        <Paragraph type="secondary">
          {t('plugins.noConfigAvailable')}
        </Paragraph>
      </Modal>
    </Layout>
  );
};

export default PluginsPage;
