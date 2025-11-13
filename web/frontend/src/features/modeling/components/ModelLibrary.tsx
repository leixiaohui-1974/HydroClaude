/**
 * Model Library Component
 * 模型库组件
 *
 * v1.5.0 Feature: Model Library
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  List,
  Card,
  Button,
  Space,
  Tag,
  Input,
  Popconfirm,
  Empty,
  Radio,
  Row,
  Col,
  Statistic,
  message
} from 'antd';
import {
  DeleteOutlined,
  CopyOutlined,
  FolderOpenOutlined,
  SearchOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  ClockCircleOutlined,
  FontSizeOutlined
} from '@ant-design/icons';
import type { HydraulicModel } from '../types/model.types';
import { STORAGE_KEYS } from '../../../types/model-io';

const { Search } = Input;

interface ModelLibraryProps {
  visible: boolean;
  onClose: () => void;
  onLoadModel: (model: HydraulicModel) => void;
  currentModelId?: string;
}

type SortBy = 'date' | 'name';
type ViewMode = 'grid' | 'list';

/**
 * ModelLibrary Component
 * Displays saved models with search, filter, and CRUD operations
 */
const ModelLibrary: React.FC<ModelLibraryProps> = ({
  visible,
  onClose,
  onLoadModel,
  currentModelId
}) => {
  const [models, setModels] = useState<HydraulicModel[]>([]);
  const [filteredModels, setFilteredModels] = useState<HydraulicModel[]>([]);
  const [searchText, setSearchText] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('date');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [loading, setLoading] = useState(false);

  // ============= Load Models =============

  /**
   * Load models from localStorage
   */
  const loadModels = () => {
    try {
      setLoading(true);
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');
      setModels(saved);
      setFilteredModels(saved);
    } catch (error) {
      message.error('加载模型失败');
      console.error('Failed to load models:', error);
    } finally {
      setLoading(false);
    }
  };

  // Load models when modal opens
  useEffect(() => {
    if (visible) {
      loadModels();
    }
  }, [visible]);

  // ============= Search and Filter =============

  /**
   * Handle search input change
   */
  const handleSearch = (value: string) => {
    setSearchText(value);
    filterAndSortModels(value, sortBy);
  };

  /**
   * Handle sort change
   */
  const handleSortChange = (newSortBy: SortBy) => {
    setSortBy(newSortBy);
    filterAndSortModels(searchText, newSortBy);
  };

  /**
   * Filter and sort models
   */
  const filterAndSortModels = (search: string, sort: SortBy) => {
    let filtered = [...models];

    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(
        (model) =>
          model.name.toLowerCase().includes(searchLower) ||
          model.description?.toLowerCase().includes(searchLower) ||
          model.id.toLowerCase().includes(searchLower)
      );
    }

    // Apply sorting
    if (sort === 'date') {
      filtered.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
    } else if (sort === 'name') {
      filtered.sort((a, b) => a.name.localeCompare(b.name));
    }

    setFilteredModels(filtered);
  };

  // ============= CRUD Operations =============

  /**
   * Delete a model
   */
  const handleDelete = (id: string) => {
    try {
      const updated = models.filter((m) => m.id !== id);
      localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(updated));
      setModels(updated);
      filterAndSortModels(searchText, sortBy);
      message.success('模型已删除');
    } catch (error) {
      message.error('删除失败');
    }
  };

  /**
   * Clone a model
   */
  const handleClone = (model: HydraulicModel) => {
    try {
      const cloned: HydraulicModel = {
        ...model,
        id: crypto.randomUUID(),
        name: `${model.name} (副本)`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        version: model.version + 1
      };

      const updated = [...models, cloned];
      localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(updated));
      setModels(updated);
      filterAndSortModels(searchText, sortBy);
      message.success(`已克隆模型: ${cloned.name}`);
    } catch (error) {
      message.error('克隆失败');
    }
  };

  /**
   * Load a model
   */
  const handleLoad = (model: HydraulicModel) => {
    onLoadModel(model);
    onClose();
    message.success(`已加载模型: ${model.name}`);
  };

  // ============= Render Helpers =============

  /**
   * Render model card (grid view)
   */
  const renderModelCard = (model: HydraulicModel) => {
    const isCurrentModel = model.id === currentModelId;

    return (
      <Card
        key={model.id}
        hoverable={!isCurrentModel}
        style={{
          marginBottom: 16,
          borderColor: isCurrentModel ? '#1890ff' : undefined
        }}
        bodyStyle={{ padding: 16 }}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
            <div style={{ flex: 1 }}>
              <h4 style={{ margin: 0, marginBottom: 4 }}>
                {model.name}
                {isCurrentModel && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    当前
                  </Tag>
                )}
              </h4>
              <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
                {model.description || '无描述'}
              </div>
            </div>
          </div>

          <Row gutter={8}>
            <Col span={12}>
              <Statistic
                title="节点"
                value={model.nodes.length}
                valueStyle={{ fontSize: 14 }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="连接"
                value={model.edges.length}
                valueStyle={{ fontSize: 14 }}
              />
            </Col>
          </Row>

          <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            更新: {new Date(model.updated_at).toLocaleString()}
          </div>

          {model.validated && (
            <Tag color="green" style={{ marginTop: 8 }}>
              已验证
            </Tag>
          )}
        </div>

        <Space size="small">
          <Button
            type="primary"
            size="small"
            icon={<FolderOpenOutlined />}
            onClick={() => handleLoad(model)}
            disabled={isCurrentModel}
          >
            打开
          </Button>
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleClone(model)}
          >
            克隆
          </Button>
          <Popconfirm
            title="确定删除此模型？"
            description="此操作无法撤销"
            onConfirm={() => handleDelete(model.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      </Card>
    );
  };

  /**
   * Render model list item (list view)
   */
  const renderModelListItem = (model: HydraulicModel) => {
    const isCurrentModel = model.id === currentModelId;

    return (
      <List.Item
        key={model.id}
        style={{
          backgroundColor: isCurrentModel ? '#f0f5ff' : undefined,
          padding: '12px 16px'
        }}
        actions={[
          <Button
            type="primary"
            size="small"
            icon={<FolderOpenOutlined />}
            onClick={() => handleLoad(model)}
            disabled={isCurrentModel}
            key="open"
          >
            打开
          </Button>,
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleClone(model)}
            key="clone"
          >
            克隆
          </Button>,
          <Popconfirm
            title="确定删除此模型？"
            description="此操作无法撤销"
            onConfirm={() => handleDelete(model.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            key="delete"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        ]}
      >
        <List.Item.Meta
          title={
            <Space>
              {model.name}
              {isCurrentModel && <Tag color="blue">当前</Tag>}
              {model.validated && <Tag color="green">已验证</Tag>}
            </Space>
          }
          description={
            <Space direction="vertical" size="small">
              <div>{model.description || '无描述'}</div>
              <div style={{ fontSize: 12, color: '#999' }}>
                节点: {model.nodes.length} | 连接: {model.edges.length} | 更新:{' '}
                {new Date(model.updated_at).toLocaleDateString()}
              </div>
            </Space>
          }
        />
      </List.Item>
    );
  };

  // ============= Render =============

  return (
    <Modal
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>模型库</span>
          <Space>
            <Tag color="blue">{filteredModels.length} 个模型</Tag>
          </Space>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>
      ]}
      destroyOnClose={true}
    >
      {/* Toolbar */}
      <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }} size="middle">
        {/* Search and View Controls */}
        <Row gutter={16}>
          <Col flex="auto">
            <Search
              placeholder="搜索模型名称、描述或ID..."
              allowClear
              value={searchText}
              onChange={(e) => handleSearch(e.target.value)}
              prefix={<SearchOutlined />}
              size="large"
            />
          </Col>
          <Col>
            <Radio.Group
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              size="large"
            >
              <Radio.Button value="grid">
                <AppstoreOutlined /> 网格
              </Radio.Button>
              <Radio.Button value="list">
                <UnorderedListOutlined /> 列表
              </Radio.Button>
            </Radio.Group>
          </Col>
        </Row>

        {/* Sort Controls */}
        <Row>
          <Col>
            <Space>
              <span style={{ color: '#999' }}>排序方式:</span>
              <Radio.Group
                value={sortBy}
                onChange={(e) => handleSortChange(e.target.value)}
                size="small"
              >
                <Radio.Button value="date">
                  <ClockCircleOutlined /> 最近更新
                </Radio.Button>
                <Radio.Button value="name">
                  <FontSizeOutlined /> 名称
                </Radio.Button>
              </Radio.Group>
            </Space>
          </Col>
        </Row>
      </Space>

      {/* Models List */}
      <div style={{ maxHeight: 500, overflowY: 'auto' }}>
        {filteredModels.length === 0 ? (
          <Empty
            description={
              searchText ? '未找到匹配的模型' : '暂无保存的模型'
            }
            style={{ padding: '40px 0' }}
          />
        ) : viewMode === 'grid' ? (
          <Row gutter={[16, 16]}>
            {filteredModels.map((model) => (
              <Col span={12} key={model.id}>
                {renderModelCard(model)}
              </Col>
            ))}
          </Row>
        ) : (
          <List
            dataSource={filteredModels}
            renderItem={renderModelListItem}
            loading={loading}
          />
        )}
      </div>
    </Modal>
  );
};

export default ModelLibrary;
