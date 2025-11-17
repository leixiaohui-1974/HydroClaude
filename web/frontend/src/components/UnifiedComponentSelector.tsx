/**
 * 统一组件选择器
 * Unified Component Selector
 * 
 * 基于unifiedComponentLibrary的完整UI组件
 * 支持23种水工组件的可视化选择和配置
 * 
 * @author HydroClaude Team
 * @date 2025-11-17
 * @version 2.0.0
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Tabs,
  Input,
  Space,
  Button,
  Badge,
  Typography,
  Row,
  Col,
  Tooltip,
  Tag,
  Empty,
  Divider,
  Alert
} from 'antd';
import {
  SearchOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import {
  UNIFIED_COMPONENT_LIBRARY,
  ComponentConfig,
  ComponentCategory,
  getComponentStats,
  COMPONENT_LIBRARY_INFO
} from '../features/modeling/utils/unifiedComponentLibrary';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Search } = Input;

// ==================== 类型定义 ====================

interface UnifiedComponentSelectorProps {
  onSelectComponent?: (component: ComponentConfig) => void;
  selectedCategory?: string;
  mode?: 'grid' | 'list';
}

interface ComponentCardProps {
  component: ComponentConfig;
  onSelect: (component: ComponentConfig) => void;
  mode: 'grid' | 'list';
}

// ==================== 组件卡片 ====================

const ComponentCard: React.FC<ComponentCardProps> = ({ component, onSelect, mode }) => {
  const [hovered, setHovered] = useState(false);

  if (mode === 'list') {
    return (
      <Card
        size="small"
        hoverable
        style={{ marginBottom: 8 }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => onSelect(component)}
      >
        <Row align="middle" gutter={16}>
          <Col span={2}>
            <div style={{ fontSize: 32, textAlign: 'center' }}>
              {component.icon}
            </div>
          </Col>
          <Col span={14}>
            <Space direction="vertical" size={0}>
              <Text strong>{component.nameCN}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {component.name}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {component.description}
              </Text>
            </Space>
          </Col>
          <Col span={8} style={{ textAlign: 'right' }}>
            <Space direction="vertical" size={4} style={{ width: '100%', alignItems: 'flex-end' }}>
              <Tag color="blue">{component.category}</Tag>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {component.requiredFields.length} 必填项
              </Text>
              {hovered && (
                <Button
                  type="primary"
                  size="small"
                  icon={<PlusOutlined />}
                >
                  添加
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>
    );
  }

  // Grid mode
  return (
    <Card
      hoverable
      style={{
        height: 200,
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.3s'
      }}
      bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onSelect(component)}
    >
      <Space direction="vertical" size={8} style={{ width: '100%', flex: 1 }}>
        <div style={{ fontSize: 48, textAlign: 'center' }}>
          {component.icon}
        </div>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <Title level={5} style={{ margin: 0 }}>
            {component.nameCN}
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {component.name}
          </Text>
        </div>
        <div style={{ textAlign: 'center' }}>
          <Tag color="blue" style={{ fontSize: 10 }}>
            {component.requiredFields.length} 必填项
          </Tag>
        </div>
        {hovered && (
          <Button
            type="primary"
            block
            icon={<PlusOutlined />}
          >
            添加组件
          </Button>
        )}
      </Space>
    </Card>
  );
};

// ==================== 类别视图 ====================

const CategoryView: React.FC<{
  category: ComponentCategory;
  onSelectComponent: (component: ComponentConfig) => void;
  mode: 'grid' | 'list';
  searchText: string;
}> = ({ category, onSelectComponent, mode, searchText }) => {
  const filteredComponents = useMemo(() => {
    if (!searchText) return category.components;
    
    const lowerSearch = searchText.toLowerCase();
    return category.components.filter(comp =>
      comp.name.toLowerCase().includes(lowerSearch) ||
      comp.nameCN.includes(searchText) ||
      comp.description.includes(searchText)
    );
  }, [category.components, searchText]);

  if (filteredComponents.length === 0) {
    return <Empty description="没有匹配的组件" />;
  }

  if (mode === 'grid') {
    return (
      <Row gutter={[16, 16]}>
        {filteredComponents.map(component => (
          <Col key={component.id} xs={24} sm={12} md={8} lg={6}>
            <ComponentCard
              component={component}
              onSelect={onSelectComponent}
              mode="grid"
            />
          </Col>
        ))}
      </Row>
    );
  }

  return (
    <div>
      {filteredComponents.map(component => (
        <ComponentCard
          key={component.id}
          component={component}
          onSelect={onSelectComponent}
          mode="list"
        />
      ))}
    </div>
  );
};

// ==================== 主组件 ====================

export const UnifiedComponentSelector: React.FC<UnifiedComponentSelectorProps> = ({
  onSelectComponent,
  selectedCategory,
  mode: initialMode = 'grid'
}) => {
  const [searchText, setSearchText] = useState('');
  const [mode, setMode] = useState<'grid' | 'list'>(initialMode);
  const [activeCategory, setActiveCategory] = useState(
    selectedCategory || UNIFIED_COMPONENT_LIBRARY[0].id
  );

  const stats = useMemo(() => getComponentStats(), []);

  const handleSelectComponent = (component: ComponentConfig) => {
    console.log('选择组件:', component);
    if (onSelectComponent) {
      onSelectComponent(component);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      {/* 头部信息 */}
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Space direction="vertical" size={4}>
              <Title level={3} style={{ margin: 0 }}>
                <AppstoreOutlined style={{ marginRight: 8 }} />
                水工组件库
              </Title>
              <Space size={16}>
                <Text type="secondary">
                  版本: {COMPONENT_LIBRARY_INFO.version}
                </Text>
                <Text type="secondary">
                  总组件: <Badge count={stats.totalComponents} showZero color="blue" />
                </Text>
                <Text type="secondary">
                  分类: <Badge count={stats.totalCategories} showZero color="green" />
                </Text>
              </Space>
            </Space>
          </Col>
          <Col>
            <Space>
              <Tooltip title="网格视图">
                <Button
                  type={mode === 'grid' ? 'primary' : 'default'}
                  icon={<AppstoreOutlined />}
                  onClick={() => setMode('grid')}
                />
              </Tooltip>
              <Tooltip title="列表视图">
                <Button
                  type={mode === 'list' ? 'primary' : 'default'}
                  icon={<UnorderedListOutlined />}
                  onClick={() => setMode('list')}
                />
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 高级组件提示 */}
      <Alert
        message="⭐ 水电系统组件"
        description="包含水轮机、阀门、调压井等高级水电组件，市场独有功能！"
        type="info"
        icon={<ThunderboltOutlined />}
        showIcon
        closable
        style={{ marginBottom: 16 }}
      />

      {/* 搜索栏 */}
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Search
          placeholder="搜索组件名称、类别或描述..."
          allowClear
          size="large"
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          prefix={<SearchOutlined />}
        />
      </Card>

      {/* 组件分类标签页 */}
      <Card>
        <Tabs
          activeKey={activeCategory}
          onChange={setActiveCategory}
          type="card"
          tabBarExtraContent={
            <Space>
              <Tooltip title="组件信息">
                <InfoCircleOutlined style={{ fontSize: 16, color: '#1890ff' }} />
              </Tooltip>
            </Space>
          }
        >
          {UNIFIED_COMPONENT_LIBRARY.map(category => (
            <TabPane
              key={category.id}
              tab={
                <span>
                  {category.icon} {category.nameCN}
                  <Badge
                    count={category.components.length}
                    style={{ marginLeft: 8, backgroundColor: '#52c41a' }}
                  />
                </span>
              }
            >
              <div style={{ padding: '16px 0' }}>
                {/* 类别描述 */}
                <Alert
                  message={category.nameCN}
                  description={category.description}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                {/* 组件列表 */}
                <CategoryView
                  category={category}
                  onSelectComponent={handleSelectComponent}
                  mode={mode}
                  searchText={searchText}
                />
              </div>
            </TabPane>
          ))}
        </Tabs>
      </Card>

      {/* 底部统计 */}
      <Card bordered={false} style={{ marginTop: 16, textAlign: 'center' }}>
        <Space size={32}>
          {stats.byCategory.map(cat => (
            <div key={cat.id}>
              <Text type="secondary">{cat.name}</Text>
              <br />
              <Text strong style={{ fontSize: 20, color: '#1890ff' }}>
                {cat.count}
              </Text>
            </div>
          ))}
        </Space>
        <Divider />
        <Text type="secondary" style={{ fontSize: 12 }}>
          {COMPONENT_LIBRARY_INFO.description}
        </Text>
      </Card>
    </div>
  );
};

export default UnifiedComponentSelector;
