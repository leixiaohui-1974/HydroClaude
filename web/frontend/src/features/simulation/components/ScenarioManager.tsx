/**
 * Scenario Manager Component
 * 场景管理器组件
 *
 * v1.5.0 Feature: Multi-Scenario Comparison
 */

import React, { useState } from 'react';
import {
  Modal,
  Button,
  Form,
  Input,
  ColorPicker,
  Space,
  message,
  Alert
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { Color } from 'antd/es/color-picker';
import type { SimulationResultResponse } from '@/services/api';
import type { ComparisonScenario } from '@/types/comparison';
import { DEFAULT_SCENARIO_COLORS } from '@/types/comparison';

interface ScenarioManagerProps {
  /**
   * Current scenarios
   * 当前场景列表
   */
  scenarios: ComparisonScenario[];

  /**
   * Callback when a scenario is added
   * 添加场景回调
   */
  onAddScenario: (scenario: ComparisonScenario) => void;

  /**
   * Available simulation results to add as scenarios
   * 可用的仿真结果
   */
  availableResults?: SimulationResultResponse[];
}

/**
 * ScenarioManager Component
 *
 * Provides UI for adding and managing comparison scenarios
 */
const ScenarioManager: React.FC<ScenarioManagerProps> = ({
  scenarios,
  onAddScenario,
  availableResults = []
}) => {
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [selectedColor, setSelectedColor] = useState<string>(
    DEFAULT_SCENARIO_COLORS[scenarios.length % DEFAULT_SCENARIO_COLORS.length]
  );

  /**
   * Handle add scenario from current result
   * 从当前结果添加场景
   */
  const handleAddFromResult = (result: SimulationResultResponse) => {
    const scenario: ComparisonScenario = {
      id: `scenario-${Date.now()}`,
      name: `场景 ${scenarios.length + 1}`,
      color: DEFAULT_SCENARIO_COLORS[scenarios.length % DEFAULT_SCENARIO_COLORS.length],
      result,
      visible: true,
      description: `Task: ${result.task_id.substring(0, 8)}`
    };

    onAddScenario(scenario);
    message.success(`已添加场景: ${scenario.name}`);
  };

  /**
   * Handle custom scenario creation
   * 处理自定义场景创建
   */
  const handleCustomAdd = () => {
    form.validateFields().then(values => {
      // In a real application, this would select from saved results
      // For now, we'll just show the modal
      setModalVisible(true);
    }).catch(err => {
      message.error('请填写完整信息');
    });
  };

  /**
   * Get next available color
   * 获取下一个可用颜色
   */
  const getNextColor = (): string => {
    const usedColors = scenarios.map(s => s.color);
    const availableColors = DEFAULT_SCENARIO_COLORS.filter(c => !usedColors.includes(c));
    return availableColors.length > 0
      ? availableColors[0]
      : DEFAULT_SCENARIO_COLORS[scenarios.length % DEFAULT_SCENARIO_COLORS.length];
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Quick Add Button */}
      {availableResults.length > 0 && (
        <Space wrap>
          {availableResults.slice(0, 3).map((result, index) => (
            <Button
              key={result.task_id}
              icon={<PlusOutlined />}
              onClick={() => handleAddFromResult(result)}
              disabled={scenarios.some(s => s.result.task_id === result.task_id)}
            >
              添加场景: {result.task_id.substring(0, 8)}
            </Button>
          ))}
        </Space>
      )}

      {/* Custom Add Button */}
      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={() => setModalVisible(true)}
        block
      >
        自定义添加场景
      </Button>

      {/* Add Scenario Modal */}
      <Modal
        title="添加对比场景 Add Comparison Scenario"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>
            取消 Cancel
          </Button>,
          <Button
            key="add"
            type="primary"
            onClick={handleCustomAdd}
          >
            添加 Add
          </Button>
        ]}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            name: `场景 ${scenarios.length + 1}`,
            color: getNextColor()
          }}
        >
          <Form.Item
            name="name"
            label="场景名称 Scenario Name"
            rules={[{ required: true, message: '请输入场景名称' }]}
          >
            <Input placeholder="例如：高水位场景" />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述 Description"
          >
            <Input.TextArea
              placeholder="场景描述（可选）"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            name="color"
            label="颜色 Color"
          >
            <ColorPicker
              value={selectedColor}
              onChange={(color: Color) => {
                setSelectedColor(color.toHexString());
              }}
              showText
              presets={[
                {
                  label: '推荐颜色 Recommended',
                  colors: DEFAULT_SCENARIO_COLORS
                }
              ]}
            />
          </Form.Item>

          <Alert
            message="提示 Tip"
            description="在实际应用中，这里将显示已保存的仿真结果列表供选择。当前版本需要从结果页面直接添加场景。"
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* Scenario Limit Warning */}
      {scenarios.length >= 8 && (
        <Alert
          message="场景数量较多 Many Scenarios"
          description="为保证可视化效果和性能，建议保持场景数量在8个以内。"
          type="warning"
          showIcon
          closable
        />
      )}

      {/* Empty State */}
      {scenarios.length === 0 && (
        <Alert
          message="暂无场景 No Scenarios"
          description="请添加至少一个场景以开始对比分析。您可以从仿真结果页面添加场景。"
          type="info"
          showIcon
        />
      )}
    </Space>
  );
};

export default ScenarioManager;
