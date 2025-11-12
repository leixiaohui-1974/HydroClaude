/**
 * Template Gallery Component
 * 模板画廊组件
 *
 * v1.5.0 Feature: Model Templates
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Space,
  Button,
  Input,
  Select,
  Tag,
  Modal,
  Descriptions,
  Empty,
  Typography,
  Badge,
  Rate,
  Divider,
  List,
  message
} from 'antd';
import {
  AppstoreOutlined,
  SearchOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  BookOutlined
} from '@ant-design/icons';
import type { ModelTemplate, TemplateFilter, TemplateCategory, TemplateDifficulty } from '@/types/template';
import {
  TEMPLATE_CATEGORY_NAMES,
  DIFFICULTY_NAMES,
  DEFAULT_TEMPLATE_FILTER
} from '@/types/template';
import { filterTemplates, applyTemplate, incrementTemplateUsage } from '@/utils/templateUtils';
import { TEMPLATES } from '@/data/templates';

const { Text, Title, Paragraph } = Typography;
const { Option } = Select;
const { Search } = Input;

interface TemplateGalleryProps {
  /**
   * Callback when template is applied
   * 应用模板回调
   */
  onApplyTemplate?: (template: ModelTemplate) => void;

  /**
   * Show only specific categories
   * 仅显示特定分类
   */
  categories?: TemplateCategory[];
}

/**
 * Template Gallery Component
 *
 * Displays a gallery of model templates with filtering, search, and preview
 */
const TemplateGallery: React.FC<TemplateGalleryProps> = ({
  onApplyTemplate,
  categories
}) => {
  // State
  const [filter, setFilter] = useState<TemplateFilter>(DEFAULT_TEMPLATE_FILTER);
  const [selectedTemplate, setSelectedTemplate] = useState<ModelTemplate | null>(null);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);

  // Filter templates
  const filteredTemplates = useMemo(() => {
    let templates = TEMPLATES;

    // Filter by categories prop if provided
    if (categories && categories.length > 0) {
      templates = templates.filter(t => categories.includes(t.metadata.category));
    }

    return filterTemplates(templates, filter);
  }, [filter, categories]);

  // Handle search
  const handleSearch = (value: string) => {
    setFilter({ ...filter, searchText: value });
  };

  // Handle category filter
  const handleCategoryChange = (value: TemplateCategory | undefined) => {
    setFilter({ ...filter, category: value });
  };

  // Handle difficulty filter
  const handleDifficultyChange = (value: TemplateDifficulty | undefined) => {
    setFilter({ ...filter, difficulty: value });
  };

  // Handle sort change
  const handleSortChange = (value: TemplateFilter['sortBy']) => {
    setFilter({ ...filter, sortBy: value });
  };

  // Show template details
  const showTemplateDetails = (template: ModelTemplate) => {
    setSelectedTemplate(template);
    setDetailsModalVisible(true);
  };

  // Apply template
  const handleApplyTemplate = (template: ModelTemplate) => {
    if (onApplyTemplate) {
      onApplyTemplate(template);
      incrementTemplateUsage(template.metadata.id);
      message.success(`已应用模板: ${template.metadata.nameCN}`);
      setDetailsModalVisible(false);
    }
  };

  // Render template card
  const renderTemplateCard = (template: ModelTemplate) => {
    const difficultyInfo = DIFFICULTY_NAMES[template.metadata.difficulty];

    return (
      <Col xs={24} sm={12} lg={8} xl={6} key={template.metadata.id}>
        <Badge.Ribbon
          text={difficultyInfo.cn}
          color={difficultyInfo.color}
        >
          <Card
            hoverable
            style={{ height: '100%' }}
            actions={[
              <Button
                key="details"
                type="text"
                icon={<InfoCircleOutlined />}
                onClick={() => showTemplateDetails(template)}
              >
                详情
              </Button>,
              <Button
                key="apply"
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => handleApplyTemplate(template)}
              >
                使用
              </Button>
            ]}
          >
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {/* Title */}
              <Title level={5} style={{ marginBottom: 0 }}>
                {template.metadata.nameCN}
              </Title>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {template.metadata.name}
              </Text>

              {/* Category */}
              <Tag color="blue">
                {TEMPLATE_CATEGORY_NAMES[template.metadata.category].cn}
              </Tag>

              {/* Description */}
              <Paragraph
                ellipsis={{ rows: 2 }}
                style={{ marginBottom: 8, fontSize: 13 }}
              >
                {template.metadata.descriptionCN}
              </Paragraph>

              {/* Rating and Usage */}
              <Space split={<Divider type="vertical" />} style={{ fontSize: 12 }}>
                <span>
                  <Rate
                    disabled
                    defaultValue={template.metadata.rating || 0}
                    style={{ fontSize: 12 }}
                  />
                </span>
                <Text type="secondary">
                  使用 {template.metadata.usageCount || 0} 次
                </Text>
              </Space>

              {/* Tags */}
              <div>
                {template.metadata.tags.slice(0, 3).map(tag => (
                  <Tag key={tag} style={{ fontSize: 11, marginBottom: 4 }}>
                    {tag}
                  </Tag>
                ))}
              </div>
            </Space>
          </Card>
        </Badge.Ribbon>
      </Col>
    );
  };

  // Render template details modal
  const renderDetailsModal = () => {
    if (!selectedTemplate) return null;

    const difficultyInfo = DIFFICULTY_NAMES[selectedTemplate.metadata.difficulty];

    return (
      <Modal
        title={
          <Space>
            <BookOutlined />
            <span>{selectedTemplate.metadata.nameCN}</span>
            <Tag color={difficultyInfo.color}>{difficultyInfo.cn}</Tag>
          </Space>
        }
        open={detailsModalVisible}
        onCancel={() => setDetailsModalVisible(false)}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setDetailsModalVisible(false)}>
            关闭
          </Button>,
          <Button
            key="apply"
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => handleApplyTemplate(selectedTemplate)}
          >
            使用此模板
          </Button>
        ]}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {/* Basic Info */}
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="英文名称">
              {selectedTemplate.metadata.name}
            </Descriptions.Item>
            <Descriptions.Item label="分类">
              {TEMPLATE_CATEGORY_NAMES[selectedTemplate.metadata.category].cn}
            </Descriptions.Item>
            <Descriptions.Item label="难度">
              <Tag color={difficultyInfo.color}>{difficultyInfo.cn}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="版本">
              {selectedTemplate.metadata.version}
            </Descriptions.Item>
            <Descriptions.Item label="作者">
              {selectedTemplate.metadata.author}
            </Descriptions.Item>
            <Descriptions.Item label="使用次数">
              {selectedTemplate.metadata.usageCount || 0}
            </Descriptions.Item>
          </Descriptions>

          {/* Description */}
          <div>
            <Title level={5}>模板描述</Title>
            <Paragraph>{selectedTemplate.metadata.descriptionCN}</Paragraph>
            <Paragraph type="secondary" style={{ fontSize: 13 }}>
              {selectedTemplate.metadata.description}
            </Paragraph>
          </div>

          {/* Configuration */}
          <div>
            <Title level={5}>配置参数</Title>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="区域长度">
                {selectedTemplate.config.domainLength} m
              </Descriptions.Item>
              <Descriptions.Item label="模拟时长">
                {selectedTemplate.config.duration} s
              </Descriptions.Item>
              <Descriptions.Item label="时间步长">
                {selectedTemplate.config.timeStep} s
              </Descriptions.Item>
              <Descriptions.Item label="曼宁系数">
                {selectedTemplate.config.manning}
              </Descriptions.Item>
              <Descriptions.Item label="计算单元数">
                {selectedTemplate.config.nCells}
              </Descriptions.Item>
            </Descriptions>
          </div>

          {/* Learning Objectives */}
          {selectedTemplate.learningObjectives && selectedTemplate.learningObjectives.length > 0 && (
            <div>
              <Title level={5}>学习目标</Title>
              <List
                size="small"
                dataSource={selectedTemplate.learningObjectives}
                renderItem={obj => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                      title={obj.objectiveCN}
                      description={obj.objective}
                    />
                  </List.Item>
                )}
              />
            </div>
          )}

          {/* Instructions */}
          {selectedTemplate.instructions && (
            <div>
              <Title level={5}>使用说明</Title>
              <Paragraph>{selectedTemplate.instructions.cn}</Paragraph>
              <Paragraph type="secondary" style={{ fontSize: 13 }}>
                {selectedTemplate.instructions.en}
              </Paragraph>
            </div>
          )}

          {/* Expected Results */}
          {selectedTemplate.expectedResults && (
            <div>
              <Title level={5}>预期结果</Title>
              <Paragraph>{selectedTemplate.expectedResults.cn}</Paragraph>
            </div>
          )}

          {/* Tags */}
          <div>
            <Title level={5}>标签</Title>
            <Space wrap>
              {selectedTemplate.metadata.tags.map(tag => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
          </div>
        </Space>
      </Modal>
    );
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* Header */}
      <div>
        <Title level={3}>
          <AppstoreOutlined /> 模板画廊 Template Gallery
        </Title>
        <Text type="secondary">
          选择一个模板快速开始建模。模板包含预配置的节点、边和参数。
        </Text>
      </div>

      {/* Filters */}
      <Card>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="搜索模板..."
              allowClear
              onSearch={handleSearch}
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="分类"
              allowClear
              style={{ width: '100%' }}
              onChange={handleCategoryChange}
              value={filter.category}
            >
              {Object.entries(TEMPLATE_CATEGORY_NAMES).map(([key, value]) => (
                <Option key={key} value={key}>
                  {value.cn}
                </Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="难度"
              allowClear
              style={{ width: '100%' }}
              onChange={handleDifficultyChange}
              value={filter.difficulty}
            >
              {Object.entries(DIFFICULTY_NAMES).map(([key, value]) => (
                <Option key={key} value={key}>
                  <Tag color={value.color} style={{ marginRight: 4 }}>
                    {value.cn}
                  </Tag>
                </Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Select
              placeholder="排序方式"
              style={{ width: '100%' }}
              onChange={handleSortChange}
              value={filter.sortBy}
            >
              <Option value="usageCount">使用次数</Option>
              <Option value="rating">评分</Option>
              <Option value="name">名称</Option>
              <Option value="createdAt">创建时间</Option>
              <Option value="updatedAt">更新时间</Option>
            </Select>
          </Col>
        </Row>
      </Card>

      {/* Template Grid */}
      {filteredTemplates.length > 0 ? (
        <Row gutter={[16, 16]}>
          {filteredTemplates.map(template => renderTemplateCard(template))}
        </Row>
      ) : (
        <Empty
          description="没有找到匹配的模板"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {/* Details Modal */}
      {renderDetailsModal()}
    </Space>
  );
};

export default TemplateGallery;
