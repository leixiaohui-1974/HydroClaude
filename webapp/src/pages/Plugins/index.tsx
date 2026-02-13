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
import type { MarketplacePlugin, PluginSearchOptions } from '@/types/plugin';
import PluginCard from '@/components/PluginCard';
import { pluginManager } from '@/services/pluginManager';
import './index.css';

const { Content } = Layout;
const { Text, Paragraph } = Typography;

/**
 * 插件市场页面
 * 
 * 功能：
 * - 浏览所有可用插件
 * - 搜索和筛选插件
 * - 安装/卸载插件
 * - 查看插件详情
 */
const PluginsPage: React.FC = () => {
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

  // 模拟插件数据（实际应该从API获取）
  const mockPlugins: MarketplacePlugin[] = [
    {
      id: 'parameter-optimization',
      name: '参数优化',
      version: '1.2.0',
      description: '使用遗传算法和梯度下降法优化渠道参数，提高仿真精度',
      author: 'HydroClaude Team',
      icon: 'https://via.placeholder.com/80/667eea/ffffff?text=OPT',
      category: 'optimization',
      keywords: ['优化', '遗传算法', '参数'],
      rating: 4.8,
      downloads: 15420,
      lastUpdated: new Date('2025-11-10'),
      homepage: 'https://hydroclaude.com/plugins/optimization',
      repository: 'https://github.com/hydroclaude/plugin-optimization',
    },
    {
      id: 'data-import-excel',
      name: 'Excel数据导入',
      version: '2.0.1',
      description: '从Excel文件导入渠道几何、边界条件和其他数据',
      author: 'Community',
      icon: 'https://via.placeholder.com/80/52c41a/ffffff?text=XLS',
      category: 'import-export',
      keywords: ['导入', 'Excel', '数据'],
      rating: 4.6,
      downloads: 23100,
      lastUpdated: new Date('2025-11-12'),
      homepage: 'https://hydroclaude.com/plugins/excel-import',
    },
    {
      id: 'visualization-3d',
      name: '3D可视化',
      version: '0.9.5',
      description: '使用Three.js创建渠道和水流的3D可视化效果',
      author: 'VizTeam',
      icon: 'https://via.placeholder.com/80/722ed1/ffffff?text=3D',
      category: 'visualization',
      keywords: ['3D', '可视化', 'Three.js'],
      rating: 4.5,
      downloads: 8720,
      lastUpdated: new Date('2025-11-08'),
      repository: 'https://github.com/hydroclaude/plugin-3d-viz',
    },
    {
      id: 'report-generator',
      name: '报告生成器',
      version: '1.0.0',
      description: '自动生成专业的仿真报告，支持PDF和Word格式',
      author: 'ReportTeam',
      icon: 'https://via.placeholder.com/80/fa8c16/ffffff?text=PDF',
      category: 'extension',
      keywords: ['报告', 'PDF', 'Word'],
      rating: 4.3,
      downloads: 12500,
      lastUpdated: new Date('2025-11-05'),
    },
    {
      id: 'hdf5-importer',
      name: 'HDF5数据处理',
      version: '1.5.2',
      description: '导入导出HDF5格式的大数据文件',
      author: 'DataTeam',
      icon: 'https://via.placeholder.com/80/13c2c2/ffffff?text=HDF',
      category: 'data-processing',
      keywords: ['HDF5', '大数据', '导入导出'],
      rating: 4.7,
      downloads: 9800,
      lastUpdated: new Date('2025-11-11'),
    },
    {
      id: 'sensitivity-analysis',
      name: '敏感性分析',
      version: '2.1.0',
      description: '分析参数变化对结果的影响，生成敏感性图表',
      author: 'AnalysisTeam',
      icon: 'https://via.placeholder.com/80/eb2f96/ffffff?text=SEN',
      category: 'analysis',
      keywords: ['敏感性', '分析', '参数'],
      rating: 4.9,
      downloads: 6540,
      lastUpdated: new Date('2025-11-13'),
    },
  ];

  // 加载插件列表
  useEffect(() => {
    loadPlugins();
    loadInstalledPlugins();
  }, [searchOptions]);

  const loadPlugins = async () => {
    setLoading(true);
    try {
      // 模拟API调用延迟
      await new Promise((resolve) => setTimeout(resolve, 500));

      // 过滤和排序
      let filtered = [...mockPlugins];

      // 搜索
      if (searchOptions.query) {
        const query = searchOptions.query.toLowerCase();
        filtered = filtered.filter(
          (p) =>
            p.name.toLowerCase().includes(query) ||
            p.description.toLowerCase().includes(query) ||
            p.keywords.some((k) => k.toLowerCase().includes(query))
        );
      }

      // 分类筛选
      if (searchOptions.category) {
        filtered = filtered.filter((p) => p.category === searchOptions.category);
      }

      // 排序
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
      message.success(`${plugin.name} 安装成功`);
    } catch (error) {
      message.error(`安装 ${plugin.name} 失败`);
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
      message.success('插件已卸载');
    } catch (error) {
      message.error('卸载插件失败');
    }
  };

  const handleConfigure = (pluginId: string) => {
    setConfigPluginId(pluginId);
  };

  const handleViewDetails = (plugin: MarketplacePlugin) => {
    setDetailPlugin(plugin);
  };

  // 统计数据
  const stats = {
    total: mockPlugins.length,
    installed: installedPlugins.size,
    avgRating: (mockPlugins.reduce((sum, p) => sum + p.rating, 0) / mockPlugins.length).toFixed(1),
  };

  return (
    <Layout className="plugins-page">
      <Content className="plugins-content">
        {/* 头部统计 */}
        <Card className="plugins-stats">
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="可用插件"
                value={stats.total}
                prefix={<AppstoreOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="已安装"
                value={stats.installed}
                prefix={<DownloadOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="平均评分"
                value={stats.avgRating}
                prefix={<StarOutlined />}
                suffix="/ 5.0"
                valueStyle={{ color: '#fa8c16' }}
              />
            </Col>
          </Row>
        </Card>

        {/* 搜索和筛选 */}
        <Card className="plugins-search">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Input
              size="large"
              placeholder="搜索插件名称、描述或关键词..."
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
                <Text>分类:</Text>
                <Select
                  style={{ width: 150 }}
                  placeholder="全部分类"
                  value={searchOptions.category}
                  onChange={(category) =>
                    setSearchOptions({ ...searchOptions, category, page: 1 })
                  }
                  allowClear
                  options={[
                    { label: '优化', value: 'optimization' },
                    { label: '数据处理', value: 'data-processing' },
                    { label: '可视化', value: 'visualization' },
                    { label: '导入导出', value: 'import-export' },
                    { label: '分析', value: 'analysis' },
                    { label: '自动化', value: 'automation' },
                    { label: '集成', value: 'integration' },
                    { label: '扩展', value: 'extension' },
                  ]}
                />
              </Space>

              <Space>
                <Text>排序:</Text>
                <Select
                  style={{ width: 120 }}
                  value={searchOptions.sortBy}
                  onChange={(sortBy) => setSearchOptions({ ...searchOptions, sortBy })}
                  options={[
                    { label: '下载量', value: 'downloads' },
                    { label: '评分', value: 'rating' },
                    { label: '更新时间', value: 'updated' },
                    { label: '名称', value: 'name' },
                  ]}
                />
              </Space>
            </Space>
          </Space>
        </Card>

        {/* 插件列表 */}
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
                description="没有找到匹配的插件"
                style={{ marginTop: 64 }}
              />
            )}
          </Spin>
        </div>
      </Content>

      {/* 插件详情模态框 */}
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
              安装插件
            </Button>
          ) : null
        }
        width={600}
      >
        {detailPlugin && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Paragraph>{detailPlugin.description}</Paragraph>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="版本">v{detailPlugin.version}</Descriptions.Item>
              <Descriptions.Item label="作者">{detailPlugin.author}</Descriptions.Item>
              <Descriptions.Item label="分类">
                <Tag color="blue">{detailPlugin.category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="评分">{detailPlugin.rating} / 5.0</Descriptions.Item>
              <Descriptions.Item label="下载量">{detailPlugin.downloads.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {detailPlugin.lastUpdated.toLocaleDateString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>
            <Space>
              <Text strong>关键词: </Text>
              {detailPlugin.keywords.map(kw => <Tag key={kw}>{kw}</Tag>)}
            </Space>
            {detailPlugin.repository && (
              <Space>
                <GithubOutlined />
                <a href={detailPlugin.repository} target="_blank" rel="noreferrer">源代码仓库</a>
              </Space>
            )}
            {detailPlugin.homepage && (
              <Space>
                <LinkOutlined />
                <a href={detailPlugin.homepage} target="_blank" rel="noreferrer">主页</a>
              </Space>
            )}
          </Space>
        )}
      </Modal>

      {/* 插件配置模态框 */}
      <Modal
        title="插件配置"
        open={!!configPluginId}
        onCancel={() => setConfigPluginId(null)}
        onOk={() => {
          message.success('配置已保存');
          setConfigPluginId(null);
        }}
      >
        <Paragraph>
          插件 <Text strong>{configPluginId}</Text> 的配置选项：
        </Paragraph>
        <Paragraph type="secondary">
          该插件暂无可配置项，或配置界面由插件自身提供。
        </Paragraph>
      </Modal>
    </Layout>
  );
};

export default PluginsPage;
