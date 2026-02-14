import React, { useState } from 'react';
import { Card, Tabs, Space, Button, message } from 'antd';
import { SaveOutlined, PlayCircleOutlined, EyeOutlined, CodeOutlined, FormOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
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
        message.error(t('editor.canalLengthError'));
        return false;
      }
      
      if (!config.canal.width || config.canal.width <= 0) {
        message.error(t('editor.canalWidthError'));
        return false;
      }
      
      if (!config.canal.slope || config.canal.slope <= 0) {
        message.error(t('editor.canalSlopeError'));
        return false;
      }
      
      message.success(t('editor.configValid'));
      return true;
    } catch (error) {
      message.error(t('editor.configInvalid'));
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
    message.success(t('editor.configSaved'));
  };

  // 运行仿真
  const handleRun = async () => {
    const isValid = await validateConfig();
    if (!isValid) return;
    
    if (onRun) {
      onRun(config);
    }
    message.success(t('editor.simulationStarted'));
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
            {t('editor.saveConfig')}
          </Button>
          <Button 
            type="primary" 
            icon={<PlayCircleOutlined />} 
            onClick={handleRun}
            loading={isValidating}
          >
            {t('editor.runSimulation')}
          </Button>
          <Button 
            icon={<EyeOutlined />} 
            onClick={validateConfig}
            loading={isValidating}
          >
            {t('editor.validateConfig')}
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
                  {t('editor.formEditor')}
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
                  {t('editor.jsonEditor')}
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
                  {t('editor.preview')}
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
