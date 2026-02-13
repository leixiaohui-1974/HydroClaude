import React, { useState } from 'react';
import { Card, Tabs, Space, Button, message } from 'antd';
import { SaveOutlined, PlayCircleOutlined, EyeOutlined, CodeOutlined, FormOutlined } from '@ant-design/icons';
import FormEditor from '../FormEditor';
import JsonEditor from '../JsonEditor';
import ConfigPreview from './ConfigPreview';
import type { SimulationConfig } from '@/services/simulations';

interface ConfigEditorProps {
  initialConfig?: SimulationConfig;
  onSave?: (config: SimulationConfig) => void;
  onRun?: (config: SimulationConfig) => void;
}

const ConfigEditor: React.FC<ConfigEditorProps> = ({ 
  initialConfig, 
  onSave, 
  onRun 
}) => {
  const [config, setConfig] = useState<SimulationConfig>(
    initialConfig || getDefaultConfig()
  );
  const [activeTab, setActiveTab] = useState<string>('form');
  const [isValidating, setIsValidating] = useState(false);

  // 默认配置
  function getDefaultConfig(): SimulationConfig {
    return {
      simulation: {
        type: 'steady',
        mode: 'single_canal',
      },
      canal: {
        length: 1000,
        width: 10,
        slope: 0.001,
        manning_n: 0.025,
      },
      solver: {
        method: 'hydrostatic',
      },
      boundary_conditions: {
        upstream: {
          type: 'flow',
          value: 8.0,
        },
        downstream: {
          type: 'depth',
          method: 'uniform_flow',
        },
      },
    };
  }

  // 配置更新处理
  const handleConfigChange = (newConfig: SimulationConfig) => {
    setConfig(newConfig);
  };

  // 验证配置
  const validateConfig = async (): Promise<boolean> => {
    setIsValidating(true);
    
    try {
      // TODO: 调用后端API验证配置
      // await api.post('/validate', config);
      
      // 简单的客户端验证
      if (!config.canal || config.canal.length <= 0) {
        message.error('渠道长度必须大于0');
        return false;
      }
      
      if (!config.canal.width || config.canal.width <= 0) {
        message.error('渠道宽度必须大于0');
        return false;
      }
      
      if (!config.canal.slope || config.canal.slope <= 0) {
        message.error('渠道坡度必须大于0');
        return false;
      }
      
      message.success('配置验证通过');
      return true;
    } catch (error) {
      message.error('配置验证失败');
      return false;
    } finally {
      setIsValidating(false);
    }
  };

  // 保存配置
  const handleSave = async () => {
    const isValid = await validateConfig();
    if (!isValid) return;
    
    if (onSave) {
      onSave(config);
    }
    message.success('配置已保存');
  };

  // 运行仿真
  const handleRun = async () => {
    const isValid = await validateConfig();
    if (!isValid) return;
    
    if (onRun) {
      onRun(config);
    }
    message.success('仿真已启动');
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 工具栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Button 
            type="primary" 
            icon={<SaveOutlined />} 
            onClick={handleSave}
            loading={isValidating}
          >
            保存配置
          </Button>
          <Button 
            type="primary" 
            icon={<PlayCircleOutlined />} 
            onClick={handleRun}
            loading={isValidating}
          >
            运行仿真
          </Button>
          <Button 
            icon={<EyeOutlined />} 
            onClick={validateConfig}
            loading={isValidating}
          >
            验证配置
          </Button>
        </Space>
      </Card>

      {/* 编辑器主体 */}
      <Card 
        style={{ flex: 1, overflow: 'hidden' }}
        bodyStyle={{ height: '100%', padding: 0 }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ height: '100%' }}
          tabBarStyle={{ padding: '0 16px' }}
          items={[
            {
              key: 'form',
              label: (
                <span>
                  <FormOutlined />
                  表单编辑器
                </span>
              ),
              children: (
                <div style={{ height: 'calc(100vh - 240px)', overflow: 'auto', padding: 16 }}>
                  <FormEditor
                    config={config}
                    onChange={handleConfigChange}
                  />
                </div>
              ),
            },
            {
              key: 'json',
              label: (
                <span>
                  <CodeOutlined />
                  JSON编辑器
                </span>
              ),
              children: (
                <div style={{ height: 'calc(100vh - 240px)' }}>
                  <JsonEditor
                    config={config}
                    onChange={handleConfigChange}
                  />
                </div>
              ),
            },
            {
              key: 'preview',
              label: (
                <span>
                  <EyeOutlined />
                  预览
                </span>
              ),
              children: (
                <div style={{ height: 'calc(100vh - 240px)', overflow: 'auto', padding: 16 }}>
                  <ConfigPreview config={config} />
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default ConfigEditor;
