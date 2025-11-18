/**
 * 组件配置表单生成器
 * Component Configuration Form Generator
 * 
 * 根据组件定义自动生成配置表单
 * 支持验证和类型转换
 * 
 * @author HydroClaude Team
 * @date 2025-11-17
 */

import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Space,
  Card,
  Alert,
  Divider,
  Typography,
  Row,
  Col,
  Collapse,
  Tag
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';
import {
  ComponentConfig,
  validateComponentConfig
} from '../features/modeling/utils/unifiedComponentLibrary';

const { Title, Text } = Typography;
const { Panel } = Collapse;
const { Option } = Select;

// ==================== 类型定义 ====================

interface ComponentConfigFormProps {
  component: ComponentConfig;
  initialValues?: Record<string, any>;
  onSubmit?: (values: Record<string, any>) => void;
  onCancel?: () => void;
}

// ==================== 字段类型判断 ====================

const getFieldType = (fieldName: string, defaultValue: any): string => {
  if (typeof defaultValue === 'boolean') return 'switch';
  if (typeof defaultValue === 'number') return 'number';
  if (Array.isArray(defaultValue)) return 'array';
  if (typeof defaultValue === 'object' && defaultValue !== null) return 'object';
  
  // 根据字段名推断类型
  if (fieldName.includes('type') || fieldName.includes('mode')) return 'select';
  if (fieldName.includes('description') || fieldName.includes('note')) return 'textarea';
  
  return 'text';
};

// ==================== 字段选项 ====================

const getFieldOptions = (fieldName: string, componentId: string): string[] => {
  // 根据组件和字段名返回选项
  const optionsMap: Record<string, Record<string, string[]>> = {
    'turbine': {
      'type': ['francis', 'kaplan', 'pelton']
    },
    'valve': {
      'type': ['butterfly', 'ball', 'gate', 'globe', 'needle']
    },
    'surge-tank': {
      'type': ['simple', 'throttled', 'differential']
    },
    'pump-station': {
      'pump_type': ['single', 'parallel', 'series']
    },
    // ... 其他组件的选项
  };

  return optionsMap[componentId]?.[fieldName] || [];
};

// ==================== 字段渲染 ====================

const renderField = (
  fieldName: string,
  fieldValue: any,
  componentId: string,
  isRequired: boolean
): React.ReactNode => {
  const fieldType = getFieldType(fieldName, fieldValue);
  const label = fieldName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  
  const rules = [
    {
      required: isRequired,
      message: `请输入${label}`
    }
  ];

  switch (fieldType) {
    case 'number':
      return (
        <Form.Item
          label={label}
          name={fieldName}
          rules={rules}
          tooltip={isRequired ? '必填项' : '可选项'}
        >
          <InputNumber
            style={{ width: '100%' }}
            placeholder={`输入${label}`}
            min={0}
            step={fieldName.includes('coeff') || fieldName.includes('efficiency') ? 0.01 : 1}
          />
        </Form.Item>
      );

    case 'switch':
      return (
        <Form.Item
          label={label}
          name={fieldName}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      );

    case 'select':
      const options = getFieldOptions(fieldName, componentId);
      return (
        <Form.Item
          label={label}
          name={fieldName}
          rules={rules}
        >
          <Select placeholder={`选择${label}`}>
            {options.map(opt => (
              <Option key={opt} value={opt}>
                {opt.toUpperCase()}
              </Option>
            ))}
          </Select>
        </Form.Item>
      );

    case 'textarea':
      return (
        <Form.Item
          label={label}
          name={fieldName}
          rules={rules}
        >
          <Input.TextArea
            rows={3}
            placeholder={`输入${label}`}
          />
        </Form.Item>
      );

    case 'text':
    default:
      return (
        <Form.Item
          label={label}
          name={fieldName}
          rules={rules}
        >
          <Input placeholder={`输入${label}`} />
        </Form.Item>
      );
  }
};

// ==================== 主组件 ====================

export const ComponentConfigForm: React.FC<ComponentConfigFormProps> = ({
  component,
  initialValues,
  onSubmit,
  onCancel
}) => {
  const [form] = Form.useForm();
  const [validationResult, setValidationResult] = useState<{
    isValid: boolean;
    missingFields: string[];
  } | null>(null);

  // 初始化表单值
  useEffect(() => {
    const defaultValues = { ...component.defaultData, ...initialValues };
    form.setFieldsValue(defaultValues);
  }, [component, initialValues, form]);

  // 处理表单提交
  const handleSubmit = (values: Record<string, any>) => {
    // 验证配置
    const validation = validateComponentConfig(component.id, values);
    setValidationResult(validation);

    if (validation.isValid) {
      console.log('配置有效，提交数据:', values);
      if (onSubmit) {
        onSubmit(values);
      }
    } else {
      console.error('配置验证失败:', validation.missingFields);
    }
  };

  // 重置表单
  const handleReset = () => {
    form.setFieldsValue(component.defaultData);
    setValidationResult(null);
  };

  // 分组字段
  const basicFields = Object.keys(component.defaultData).filter(key =>
    component.requiredFields.includes(key)
  );

  const advancedFields = Object.keys(component.defaultData).filter(key =>
    component.advancedFields?.includes(key) ||
    (!component.requiredFields.includes(key) && !['name'].includes(key))
  );

  return (
    <Card
      title={
        <Space>
          <span style={{ fontSize: 24 }}>{component.icon}</span>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {component.nameCN}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {component.name}
            </Text>
          </div>
        </Space>
      }
      extra={
        <Space>
          <Tag color="blue">API: {component.apiEndpoint}</Tag>
          <Tag color="green">{component.requiredFields.length} 必填项</Tag>
        </Space>
      }
    >
      {/* 组件描述 */}
      <Alert
        message={component.description}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 验证结果 */}
      {validationResult && (
        <Alert
          message={validationResult.isValid ? '配置有效' : '配置无效'}
          description={
            validationResult.isValid
              ? '所有必填项已填写完整'
              : `缺少必填项: ${validationResult.missingFields.join(', ')}`
          }
          type={validationResult.isValid ? 'success' : 'error'}
          icon={validationResult.isValid ? <CheckCircleOutlined /> : <WarningOutlined />}
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 配置表单 */}
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={component.defaultData}
      >
        {/* 基本信息 */}
        <Divider orientation="left">基本信息</Divider>
        
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item
              label="组件名称"
              name="name"
              rules={[{ required: true, message: '请输入组件名称' }]}
            >
              <Input placeholder="输入组件名称" />
            </Form.Item>
          </Col>
        </Row>

        {/* 必填参数 */}
        <Divider orientation="left">
          <Space>
            必填参数
            <Tag color="red">必须填写</Tag>
          </Space>
        </Divider>
        
        <Row gutter={16}>
          {basicFields.map(fieldName => (
            <Col key={fieldName} xs={24} sm={12} md={8}>
              {renderField(
                fieldName,
                component.defaultData[fieldName],
                component.id,
                true
              )}
            </Col>
          ))}
        </Row>

        {/* 高级参数（折叠） */}
        {advancedFields.length > 0 && (
          <Collapse
            ghost
            style={{ marginTop: 16 }}
            items={[
              {
                key: 'advanced',
                label: (
                  <Space>
                    高级参数
                    <Tag color="blue">可选</Tag>
                  </Space>
                ),
                children: (
                  <Row gutter={16}>
                    {advancedFields.map(fieldName => (
                      <Col key={fieldName} xs={24} sm={12} md={8}>
                        {renderField(
                          fieldName,
                          component.defaultData[fieldName],
                          component.id,
                          false
                        )}
                      </Col>
                    ))}
                  </Row>
                )
              }
            ]}
          />
        )}

        {/* 操作按钮 */}
        <Divider />
        <Form.Item>
          <Space style={{ float: 'right' }}>
            <Button onClick={onCancel}>
              取消
            </Button>
            <Button onClick={handleReset} icon={<ReloadOutlined />}>
              重置
            </Button>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
              保存配置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default ComponentConfigForm;
