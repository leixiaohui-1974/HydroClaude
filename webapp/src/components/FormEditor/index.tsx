import React from 'react';
import { Form, InputNumber, Select, Card, Space, Collapse, Button, Row, Col } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { SimulationConfig } from '@/services/simulations';

const { Option } = Select;

interface FormEditorProps {
  config: SimulationConfig;
  onChange: (config: SimulationConfig) => void;
}

const FormEditor: React.FC<FormEditorProps> = ({ config, onChange }) => {
  const [form] = Form.useForm();

  // 表单值变化时更新配置
  const handleValuesChange = (_: any, allValues: any) => {
    onChange(allValues as SimulationConfig);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={config}
      onValuesChange={handleValuesChange}
      scrollToFirstError
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 仿真设置 */}
        <Card title="仿真设置" size="small">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="仿真类型"
                name={['simulation', 'type']}
                rules={[{ required: true, message: '请选择仿真类型' }]}
              >
                <Select placeholder="选择仿真类型">
                  <Option value="steady">稳态流</Option>
                  <Option value="unsteady">非恒定流</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="仿真模式"
                name={['simulation', 'mode']}
                rules={[{ required: true, message: '请选择仿真模式' }]}
              >
                <Select placeholder="选择仿真模式">
                  <Option value="single_canal">单一渠道</Option>
                  <Option value="network">渠道网络</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 渠道参数 */}
        <Card title="渠道参数" size="small">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="渠道长度 (m)"
                name={['canal', 'length']}
                rules={[
                  { required: true, message: '请输入渠道长度' },
                  { type: 'number', min: 1, message: '长度必须大于0' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="输入渠道长度"
                  min={1}
                  step={100}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="渠道宽度 (m)"
                name={['canal', 'width']}
                rules={[
                  { required: true, message: '请输入渠道宽度' },
                  { type: 'number', min: 0.1, message: '宽度必须大于0' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="输入渠道宽度"
                  min={0.1}
                  step={1}
                />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="渠道坡度"
                name={['canal', 'slope']}
                rules={[
                  { required: true, message: '请输入渠道坡度' },
                  { type: 'number', min: 0.0001, message: '坡度必须大于0' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="输入渠道坡度"
                  min={0.0001}
                  step={0.0001}
                  precision={4}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Manning糙率系数"
                name={['canal', 'manning_n']}
                rules={[
                  { required: true, message: '请输入Manning系数' },
                  { type: 'number', min: 0.01, max: 0.1, message: 'Manning系数范围: 0.01-0.1' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="输入Manning系数"
                  min={0.01}
                  max={0.1}
                  step={0.001}
                  precision={3}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 求解器设置 */}
        <Card title="求解器设置" size="small">
          <Form.Item
            label="求解方法"
            name={['solver', 'method']}
            rules={[{ required: true, message: '请选择求解方法' }]}
          >
            <Select placeholder="选择求解方法">
              <Option value="hydrostatic">静水压求解器（推荐）</Option>
              <Option value="godunov">Godunov格式</Option>
              <Option value="simple">简单求解器</Option>
            </Select>
          </Form.Item>
        </Card>

        {/* 边界条件 */}
        <Card title="边界条件" size="small">
          <Collapse
            defaultActiveKey={['upstream', 'downstream']}
            items={[
              {
                key: 'upstream',
                label: '上游边界条件',
                children: (
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="边界类型"
                        name={['boundary_conditions', 'upstream', 'type']}
                        rules={[{ required: true, message: '请选择边界类型' }]}
                      >
                        <Select placeholder="选择边界类型">
                          <Option value="flow">流量边界</Option>
                          <Option value="depth">水深边界</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="边界值"
                        name={['boundary_conditions', 'upstream', 'value']}
                        rules={[
                          { required: true, message: '请输入边界值' },
                          { type: 'number', min: 0, message: '边界值必须大于0' }
                        ]}
                      >
                        <InputNumber
                          style={{ width: '100%' }}
                          placeholder="输入边界值"
                          min={0}
                          step={0.1}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                ),
              },
              {
                key: 'downstream',
                label: '下游边界条件',
                children: (
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="边界类型"
                        name={['boundary_conditions', 'downstream', 'type']}
                        rules={[{ required: true, message: '请选择边界类型' }]}
                      >
                        <Select placeholder="选择边界类型">
                          <Option value="depth">水深边界</Option>
                          <Option value="flow">流量边界</Option>
                          <Option value="rating_curve">水位流量关系</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item
                        label="计算方法"
                        name={['boundary_conditions', 'downstream', 'method']}
                      >
                        <Select placeholder="选择计算方法" allowClear>
                          <Option value="uniform_flow">均匀流</Option>
                          <Option value="critical_depth">临界水深</Option>
                          <Option value="specified">指定值</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                ),
              },
            ]}
          />
        </Card>

        {/* 水工结构（可选） */}
        <Card 
          title="水工结构" 
          size="small"
          extra={<Button type="dashed" icon={<PlusOutlined />}>添加结构</Button>}
        >
          <Form.List name="structures">
            {(fields, { add, remove }) => (
              <>
                {fields.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                    暂无水工结构，点击"添加结构"按钮添加
                  </div>
                )}
                {fields.map((field, index) => (
                  <Card
                    key={field.key}
                    size="small"
                    type="inner"
                    title={`结构 ${index + 1}`}
                    extra={
                      <Button
                        type="link"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => remove(field.name)}
                      >
                        删除
                      </Button>
                    }
                    style={{ marginBottom: 16 }}
                  >
                    <Row gutter={16}>
                      <Col xs={24} md={8}>
                        <Form.Item
                          {...field}
                          label="结构类型"
                          name={[field.name, 'type']}
                          rules={[{ required: true, message: '请选择结构类型' }]}
                        >
                          <Select placeholder="选择结构类型">
                            <Option value="sluice_gate">闸门</Option>
                            <Option value="weir">堰</Option>
                            <Option value="orifice">孔板</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item
                          {...field}
                          label="位置 (m)"
                          name={[field.name, 'position']}
                          rules={[{ required: true, message: '请输入位置' }]}
                        >
                          <InputNumber
                            style={{ width: '100%' }}
                            placeholder="输入位置"
                            min={0}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item
                          {...field}
                          label="宽度 (m)"
                          name={[field.name, 'parameters', 'width']}
                        >
                          <InputNumber
                            style={{ width: '100%' }}
                            placeholder="输入宽度"
                            min={0.1}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                ))}
                <Button
                  type="dashed"
                  onClick={() => add()}
                  block
                  icon={<PlusOutlined />}
                >
                  添加结构
                </Button>
              </>
            )}
          </Form.List>
        </Card>
      </Space>
    </Form>
  );
};

export default FormEditor;
