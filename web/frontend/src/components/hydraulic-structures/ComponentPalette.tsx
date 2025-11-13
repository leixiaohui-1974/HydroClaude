/**
 * Component Palette - 组件面板
 * 管理所有7种水工结构组件的选择和配置
 * 
 * Features:
 * - 拖放式添加组件
 * - 实时预览
 * - 参数配置
 * - 导出配置
 */

import React, { useState } from 'react';
import {
  Layout,
  Card,
  Tabs,
  Button,
  Space,
  Drawer,
  Badge,
  Empty,
  message,
  Collapse,
  Tag,
  Row,
  Col,
  Typography
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  CopyOutlined,
  DownloadOutlined,
  UploadOutlined,
  BuildOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  ExperimentOutlined,
  SettingOutlined,
  AppstoreAddOutlined
} from '@ant-design/icons';
import {
  OverflowWeirComponent,
  OverflowWeirConfig,
  OrificeComponent,
  OrificeConfig,
  VariableSpeedPumpComponent,
  VariableSpeedPumpConfig,
  CheckValveComponent,
  CheckValveConfig,
  PressureReliefValveComponent,
  PressureReliefValveConfig,
  SurgeTankComponent,
  SurgeTankConfig,
  AirValveComponent,
  AirValveConfig
} from './HydraulicStructures';
import './ComponentPalette.css';

const { Sider, Content } = Layout;
const { TabPane } = Tabs;
const { Panel } = Collapse;
const { Title, Text } = Typography;

// Component definitions
interface ComponentDefinition {
  id: string;
  name: string;
  nameCN: string;
  icon: React.ReactNode;
  color: string;
  category: string;
  description: string;
  descriptionCN: string;
}

const COMPONENT_LIBRARY: ComponentDefinition[] = [
  {
    id: 'overflow-weir',
    name: 'Overflow Weir',
    nameCN: '溢流堰',
    icon: <BuildOutlined />,
    color: '#1890ff',
    category: 'flow-control',
    description: 'Controls flow by overflow',
    descriptionCN: '通过溢流控制流量'
  },
  {
    id: 'orifice',
    name: 'Orifice',
    nameCN: '孔口',
    icon: <DashboardOutlined />,
    color: '#52c41a',
    category: 'flow-control',
    description: 'Openings for flow measurement',
    descriptionCN: '用于流量测量的孔口'
  },
  {
    id: 'variable-pump',
    name: 'Variable Speed Pump',
    nameCN: '变速泵',
    icon: <ThunderboltOutlined />,
    color: '#faad14',
    category: 'active',
    description: 'Adjustable flow pump',
    descriptionCN: '可调流量的泵'
  },
  {
    id: 'check-valve',
    name: 'Check Valve',
    nameCN: '止回阀',
    icon: <SafetyOutlined />,
    color: '#eb2f96',
    category: 'protection',
    description: 'Prevents backflow',
    descriptionCN: '防止回流'
  },
  {
    id: 'relief-valve',
    name: 'Pressure Relief Valve',
    nameCN: '泄压阀',
    icon: <ExperimentOutlined />,
    color: '#ff4d4f',
    category: 'protection',
    description: 'Protects from overpressure',
    descriptionCN: '防止超压'
  },
  {
    id: 'surge-tank',
    name: 'Surge Tank',
    nameCN: '调压塔',
    icon: <SettingOutlined />,
    color: '#13c2c2',
    category: 'protection',
    description: 'Dampens pressure surges',
    descriptionCN: '抑制压力波动'
  },
  {
    id: 'air-valve',
    name: 'Air Valve',
    nameCN: '排气阀',
    icon: <ExperimentOutlined />,
    color: '#722ed1',
    category: 'protection',
    description: 'Releases air pockets',
    descriptionCN: '排除空气'
  }
];

// Instance type
interface ComponentInstance {
  instanceId: string;
  componentId: string;
  config: any;
  position: number;
}

const ComponentPalette: React.FC = () => {
  const [instances, setInstances] = useState<ComponentInstance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>('all');

  // Add new component instance
  const addComponent = (componentId: string) => {
    const newInstance: ComponentInstance = {
      instanceId: `${componentId}-${Date.now()}`,
      componentId,
      config: getDefaultConfig(componentId),
      position: instances.length * 1000
    };
    
    setInstances([...instances, newInstance]);
    setSelectedInstance(newInstance.instanceId);
    setDrawerVisible(true);
    message.success(`Added ${COMPONENT_LIBRARY.find(c => c.id === componentId)?.name}`);
  };

  // Get default configuration for each component type
  const getDefaultConfig = (componentId: string): any => {
    switch (componentId) {
      case 'overflow-weir':
        return {
          position: 0,
          crestHeight: 2.0,
          crestLength: 10.0,
          dischargeCoefficient: 0.45,
          weirType: 'broad-crested',
          numberOfSpans: 1,
          approach: 'free'
        } as OverflowWeirConfig;
      
      case 'orifice':
        return {
          position: 0,
          diameter: 0.5,
          centerElevation: 1.0,
          dischargeCoefficient: 0.6,
          shape: 'circular',
          valveControl: false,
          openingPercentage: 100
        } as OrificeConfig;
      
      case 'variable-pump':
        return {
          position: 0,
          ratedFlow: 10.0,
          ratedHead: 50.0,
          ratedSpeed: 1500,
          currentSpeed: 1500,
          efficiency: 85,
          power: 100,
          controlMode: 'manual',
          minSpeed: 500,
          maxSpeed: 2000
        } as VariableSpeedPumpConfig;
      
      case 'check-valve':
        return {
          position: 0,
          diameter: 0.5,
          crackingPressure: 5.0,
          fullOpenPressure: 20.0,
          valveType: 'swing',
          lossCoefficient: 2.0,
          reverseLeakage: 0.5
        } as CheckValveConfig;
      
      case 'relief-valve':
        return {
          position: 0,
          diameter: 0.15,
          setPressure: 300.0,
          fullOpenPressure: 330.0,
          releaseCapacity: 5.0,
          valveType: 'spring-loaded',
          responseTime: 50,
          blowdownPressure: 285.0
        } as PressureReliefValveConfig;
      
      case 'surge-tank':
        return {
          position: 0,
          diameter: 5.0,
          height: 20.0,
          bottomElevation: 100.0,
          initialWaterLevel: 10.0,
          orificeArea: 1.0,
          tankType: 'simple'
        } as SurgeTankConfig;
      
      case 'air-valve':
        return {
          position: 0,
          diameter: 50,
          valveType: 'combination',
          inletDiameter: 100,
          outletDiameter: 50,
          openingPressure: -5.0,
          closingPressure: 2.0,
          flowCoefficient: 0.7
        } as AirValveConfig;
      
      default:
        return {};
    }
  };

  // Update component configuration
  const updateInstanceConfig = (instanceId: string, newConfig: any) => {
    setInstances(instances.map(inst => 
      inst.instanceId === instanceId 
        ? { ...inst, config: newConfig }
        : inst
    ));
  };

  // Delete component instance
  const deleteInstance = (instanceId: string) => {
    setInstances(instances.filter(inst => inst.instanceId !== instanceId));
    if (selectedInstance === instanceId) {
      setSelectedInstance(null);
      setDrawerVisible(false);
    }
    message.success('Component deleted');
  };

  // Duplicate component instance
  const duplicateInstance = (instanceId: string) => {
    const original = instances.find(inst => inst.instanceId === instanceId);
    if (original) {
      const duplicate: ComponentInstance = {
        ...original,
        instanceId: `${original.componentId}-${Date.now()}`,
        position: original.position + 100
      };
      setInstances([...instances, duplicate]);
      message.success('Component duplicated');
    }
  };

  // Export configuration
  const exportConfiguration = () => {
    const config = {
      version: '1.0',
      timestamp: new Date().toISOString(),
      components: instances.map(inst => ({
        type: inst.componentId,
        ...inst.config
      }))
    };
    
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `hydraulic-system-${Date.now()}.json`;
    link.click();
    message.success('Configuration exported');
  };

  // Render component configuration panel
  const renderConfigPanel = () => {
    if (!selectedInstance) return <Empty description="No component selected" />;
    
    const instance = instances.find(inst => inst.instanceId === selectedInstance);
    if (!instance) return <Empty description="Component not found" />;
    
    const componentDef = COMPONENT_LIBRARY.find(c => c.id === instance.componentId);
    
    switch (instance.componentId) {
      case 'overflow-weir':
        return (
          <OverflowWeirComponent
            config={instance.config}
            onChange={(newConfig) => updateInstanceConfig(instance.instanceId, newConfig)}
          />
        );
      
      case 'orifice':
        return (
          <OrificeComponent
            config={instance.config}
            onChange={(newConfig) => updateInstanceConfig(instance.instanceId, newConfig)}
          />
        );
      
      case 'variable-pump':
        return (
          <VariableSpeedPumpComponent
            config={instance.config}
            onChange={(newConfig) => updateInstanceConfig(instance.instanceId, newConfig)}
          />
        );
      
      case 'check-valve':
        return (
          <CheckValveComponent
            config={instance.config}
            onChange={(newConfig) => updateInstanceConfig(instance.instanceId, newConfig)}
          />
        );
      
      case 'relief-valve':
        return (
          <PressureReliefValveComponent
            config={instance.config}
            onChange={(newConfig) => updateInstanceConfig(instance.instanceId, newConfig)}
          />
        );
      
      case 'surge-tank':
        return (
          <SurgeTankComponent
            config={instance.config}
            onChange={(newConfig) => updateInstanceConfig(instance.instanceId, newConfig)}
          />
        );
      
      case 'air-valve':
        return (
          <AirValveComponent
            config={instance.config}
            onChange={(newConfig) => updateInstanceConfig(instance.instanceId, newConfig)}
          />
        );
      
      default:
        return <Empty description="Unknown component type" />;
    }
  };

  // Filter components by category
  const filteredComponents = activeCategory === 'all'
    ? COMPONENT_LIBRARY
    : COMPONENT_LIBRARY.filter(c => c.category === activeCategory);

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      {/* Component Library Sidebar */}
      <Sider width={300} theme="light" style={{ padding: '24px 16px' }}>
        <div style={{ marginBottom: '24px' }}>
          <Title level={4}>
            <AppstoreAddOutlined /> Component Library
          </Title>
          <Text type="secondary">Hydraulic Structures / 水工结构</Text>
        </div>

        {/* Category filter */}
        <div style={{ marginBottom: '16px' }}>
          <Space wrap>
            <Tag
              color={activeCategory === 'all' ? 'blue' : 'default'}
              onClick={() => setActiveCategory('all')}
              style={{ cursor: 'pointer' }}
            >
              All ({COMPONENT_LIBRARY.length})
            </Tag>
            <Tag
              color={activeCategory === 'flow-control' ? 'green' : 'default'}
              onClick={() => setActiveCategory('flow-control')}
              style={{ cursor: 'pointer' }}
            >
              Flow Control (2)
            </Tag>
            <Tag
              color={activeCategory === 'active' ? 'orange' : 'default'}
              onClick={() => setActiveCategory('active')}
              style={{ cursor: 'pointer' }}
            >
              Active (1)
            </Tag>
            <Tag
              color={activeCategory === 'protection' ? 'red' : 'default'}
              onClick={() => setActiveCategory('protection')}
              style={{ cursor: 'pointer' }}
            >
              Protection (4)
            </Tag>
          </Space>
        </div>

        {/* Component cards */}
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {filteredComponents.map(comp => (
            <Card
              key={comp.id}
              hoverable
              size="small"
              className="component-library-card"
              onClick={() => addComponent(comp.id)}
              style={{ borderLeft: `4px solid ${comp.color}` }}
            >
              <Space>
                <div style={{ fontSize: '24px', color: comp.color }}>
                  {comp.icon}
                </div>
                <div>
                  <div style={{ fontWeight: 'bold', fontSize: '14px' }}>
                    {comp.name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#888' }}>
                    {comp.nameCN}
                  </div>
                  <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
                    {comp.descriptionCN}
                  </div>
                </div>
              </Space>
            </Card>
          ))}
        </Space>
      </Sider>

      {/* Main content */}
      <Content style={{ padding: '24px' }}>
        <Card
          title={
            <Space>
              <span>System Configuration / 系统配置</span>
              <Badge count={instances.length} />
            </Space>
          }
          extra={
            <Space>
              <Button
                icon={<UploadOutlined />}
                size="small"
              >
                Import
              </Button>
              <Button
                icon={<DownloadOutlined />}
                type="primary"
                size="small"
                onClick={exportConfiguration}
                disabled={instances.length === 0}
              >
                Export
              </Button>
            </Space>
          }
        >
          {instances.length === 0 ? (
            <Empty
              description="No components added yet. Select from the library on the left."
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <Collapse accordion>
              {instances.map(inst => {
                const compDef = COMPONENT_LIBRARY.find(c => c.id === inst.componentId);
                return (
                  <Panel
                    key={inst.instanceId}
                    header={
                      <Space>
                        <div style={{ color: compDef?.color }}>{compDef?.icon}</div>
                        <span>{compDef?.name} / {compDef?.nameCN}</span>
                        <Tag color="blue">@ {inst.config.position}m</Tag>
                      </Space>
                    }
                    extra={
                      <Space>
                        <Button
                          icon={<SettingOutlined />}
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedInstance(inst.instanceId);
                            setDrawerVisible(true);
                          }}
                        >
                          Config
                        </Button>
                        <Button
                          icon={<CopyOutlined />}
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            duplicateInstance(inst.instanceId);
                          }}
                        />
                        <Button
                          icon={<DeleteOutlined />}
                          danger
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteInstance(inst.instanceId);
                          }}
                        />
                      </Space>
                    }
                  >
                    <pre style={{ fontSize: '11px', background: '#f5f5f5', padding: '12px', borderRadius: '4px', overflow: 'auto' }}>
                      {JSON.stringify(inst.config, null, 2)}
                    </pre>
                  </Panel>
                );
              })}
            </Collapse>
          )}
        </Card>

        {/* System summary */}
        {instances.length > 0 && (
          <Card title="System Summary / 系统摘要" style={{ marginTop: '24px' }}>
            <Row gutter={16}>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1890ff' }}>
                      {instances.length}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Total Components</div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#52c41a' }}>
                      {instances.filter(i => i.componentId.includes('weir') || i.componentId.includes('orifice')).length}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Flow Control</div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#faad14' }}>
                      {instances.filter(i => i.componentId.includes('pump')).length}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Active Components</div>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ff4d4f' }}>
                      {instances.filter(i => 
                        i.componentId.includes('valve') || i.componentId.includes('tank')
                      ).length}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Protection Devices</div>
                  </div>
                </Card>
              </Col>
            </Row>
          </Card>
        )}
      </Content>

      {/* Configuration drawer */}
      <Drawer
        title="Component Configuration / 组件配置"
        placement="right"
        width={600}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {renderConfigPanel()}
      </Drawer>
    </Layout>
  );
};

export default ComponentPalette;


