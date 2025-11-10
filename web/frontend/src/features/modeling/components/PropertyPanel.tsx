/**
 * Property Panel Component
 * 属性面板组件 - 用于编辑选中节点的参数
 */

import React, { useEffect } from 'react';
import { Form, Input, InputNumber, Select, Button, Divider, Empty } from 'antd';
import { useAppDispatch, useAppSelector } from '@/shared/hooks/redux';
import { updateNode, saveSnapshot } from '../store/modelSlice';
import { selectSingleSelectedNode } from '../store/selectors';
import {
  NodeType,
  CanalNodeData,
  GateNodeData,
  BoundaryNodeData
} from '../types/model.types';
import './PropertyPanel.css';

const { Option } = Select;

const PropertyPanel: React.FC = () => {
  const dispatch = useAppDispatch();
  const [form] = Form.useForm();
  const selectedNode = useAppSelector(selectSingleSelectedNode);

  // 当选中节点变化时,更新表单
  useEffect(() => {
    if (selectedNode) {
      form.setFieldsValue(selectedNode.data);
    } else {
      form.resetFields();
    }
  }, [selectedNode, form]);

  // 处理表单值变化
  const handleValuesChange = (changedValues: any, allValues: any) => {
    if (!selectedNode) return;

    // 实时更新Redux状态
    dispatch(updateNode({
      id: selectedNode.id,
      data: allValues
    }));
  };

  // 处理表单提交
  const handleFinish = (values: any) => {
    if (!selectedNode) return;

    dispatch(updateNode({
      id: selectedNode.id,
      data: values
    }));

    // 保存快照(用于Undo/Redo)
    dispatch(saveSnapshot());
  };

  // 如果没有选中节点
  if (!selectedNode) {
    return (
      <div className="property-panel">
        <div className="panel-header">
          <h3>属性面板</h3>
        </div>
        <div className="panel-body">
          <Empty
            description="未选中任何节点"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </div>
      </div>
    );
  }

  // 渲染不同类型节点的表单
  const renderForm = () => {
    switch (selectedNode.type) {
      case NodeType.CANAL:
        return renderCanalForm(selectedNode.data as CanalNodeData);
      case NodeType.GATE:
        return renderGateForm(selectedNode.data as GateNodeData);
      case NodeType.BOUNDARY_FLOW:
      case NodeType.BOUNDARY_DEPTH:
        return renderBoundaryForm(selectedNode.data as BoundaryNodeData);
      default:
        return <div>未知节点类型</div>;
    }
  };

  // 明渠节点表单
  const renderCanalForm = (data: CanalNodeData) => (
    <>
      <Form.Item
        label="名称"
        name="name"
        rules={[{ required: true, message: '请输入名称' }]}
      >
        <Input placeholder="明渠名称" />
      </Form.Item>

      <Divider orientation="left" plain style={{ margin: '12px 0' }}>
        几何参数
      </Divider>

      <Form.Item
        label="长度 (m)"
        name="length"
        rules={[
          { required: true, message: '请输入长度' },
          { type: 'number', min: 1, message: '长度必须大于0' }
        ]}
      >
        <InputNumber
          min={1}
          max={100000}
          step={100}
          style={{ width: '100%' }}
          placeholder="1000"
        />
      </Form.Item>

      <Form.Item
        label="宽度 (m)"
        name="width"
        rules={[
          { required: true, message: '请输入宽度' },
          { type: 'number', min: 0.1, message: '宽度必须大于0' }
        ]}
      >
        <InputNumber
          min={0.1}
          max={1000}
          step={0.5}
          style={{ width: '100%' }}
          placeholder="10"
        />
      </Form.Item>

      <Form.Item
        label="坡度"
        name="slope"
        rules={[
          { required: true, message: '请输入坡度' },
          { type: 'number', min: 0, message: '坡度必须大于等于0' }
        ]}
      >
        <InputNumber
          min={0}
          max={1}
          step={0.0001}
          precision={4}
          style={{ width: '100%' }}
          placeholder="0.001"
        />
      </Form.Item>

      <Divider orientation="left" plain style={{ margin: '12px 0' }}>
        水力参数
      </Divider>

      <Form.Item
        label="曼宁系数"
        name="manning_n"
        rules={[
          { required: true, message: '请输入曼宁系数' },
          { type: 'number', min: 0.01, max: 0.1, message: '曼宁系数范围: 0.01-0.1' }
        ]}
      >
        <InputNumber
          min={0.01}
          max={0.1}
          step={0.005}
          precision={3}
          style={{ width: '100%' }}
          placeholder="0.025"
        />
      </Form.Item>

      <Divider orientation="left" plain style={{ margin: '12px 0' }}>
        数值参数
      </Divider>

      <Form.Item
        label="网格数"
        name="n_cells"
        rules={[
          { required: true, message: '请输入网格数' },
          { type: 'number', min: 10, message: '网格数至少10个' }
        ]}
      >
        <InputNumber
          min={10}
          max={1000}
          step={10}
          style={{ width: '100%' }}
          placeholder="100"
        />
      </Form.Item>

      <Divider orientation="left" plain style={{ margin: '12px 0' }}>
        初始条件
      </Divider>

      <Form.Item
        label="初始水深 (m)"
        name="initial_depth"
        rules={[{ type: 'number', min: 0, message: '水深必须大于等于0' }]}
      >
        <InputNumber
          min={0}
          max={100}
          step={0.1}
          precision={2}
          style={{ width: '100%' }}
          placeholder="5.0"
        />
      </Form.Item>

      <Form.Item
        label="初始流量 (m³/s)"
        name="initial_discharge"
        rules={[{ type: 'number', message: '请输入有效流量' }]}
      >
        <InputNumber
          step={1}
          precision={2}
          style={{ width: '100%' }}
          placeholder="0.0"
        />
      </Form.Item>
    </>
  );

  // 闸门节点表单
  const renderGateForm = (data: GateNodeData) => (
    <>
      <Form.Item
        label="名称"
        name="name"
        rules={[{ required: true, message: '请输入名称' }]}
      >
        <Input placeholder="闸门名称" />
      </Form.Item>

      <Form.Item
        label="开度"
        name="opening"
        rules={[
          { required: true, message: '请输入开度' },
          { type: 'number', min: 0, max: 1, message: '开度范围: 0-1' }
        ]}
      >
        <InputNumber
          min={0}
          max={1}
          step={0.1}
          precision={2}
          style={{ width: '100%' }}
          placeholder="0.5"
        />
      </Form.Item>

      <Form.Item
        label="流量系数"
        name="discharge_coeff"
        rules={[
          { required: true, message: '请输入流量系数' },
          { type: 'number', min: 0.1, max: 1, message: '流量系数范围: 0.1-1.0' }
        ]}
      >
        <InputNumber
          min={0.1}
          max={1}
          step={0.05}
          precision={2}
          style={{ width: '100%' }}
          placeholder="0.6"
        />
      </Form.Item>

      <Form.Item
        label="闸门宽度 (m)"
        name="width"
        rules={[
          { required: true, message: '请输入宽度' },
          { type: 'number', min: 0.1, message: '宽度必须大于0' }
        ]}
      >
        <InputNumber
          min={0.1}
          max={100}
          step={0.5}
          style={{ width: '100%' }}
          placeholder="10"
        />
      </Form.Item>

      <Form.Item
        label="堰顶高程 (m)"
        name="crest_height"
      >
        <InputNumber
          min={0}
          max={100}
          step={0.1}
          precision={2}
          style={{ width: '100%' }}
          placeholder="5.0 (可选)"
        />
      </Form.Item>
    </>
  );

  // 边界节点表单
  const renderBoundaryForm = (data: BoundaryNodeData) => (
    <>
      <Form.Item
        label="名称"
        name="name"
        rules={[{ required: true, message: '请输入名称' }]}
      >
        <Input placeholder="边界条件名称" />
      </Form.Item>

      <Form.Item
        label="边界类型"
        name="boundary_type"
        rules={[{ required: true, message: '请选择边界类型' }]}
      >
        <Select placeholder="选择边界类型">
          <Option value="flow">流量边界</Option>
          <Option value="depth">水深边界</Option>
        </Select>
      </Form.Item>

      <Form.Item
        label="边界位置"
        name="position"
        rules={[{ required: true, message: '请选择边界位置' }]}
      >
        <Select placeholder="选择边界位置">
          <Option value="upstream">上游</Option>
          <Option value="downstream">下游</Option>
        </Select>
      </Form.Item>

      <Form.Item
        label={data.boundary_type === 'flow' ? '流量 (m³/s)' : '水深 (m)'}
        name="value"
        rules={[
          { required: true, message: '请输入边界值' },
          { type: 'number', min: 0, message: '值必须大于等于0' }
        ]}
      >
        <InputNumber
          min={0}
          max={10000}
          step={data.boundary_type === 'flow' ? 1 : 0.1}
          precision={2}
          style={{ width: '100%' }}
          placeholder={data.boundary_type === 'flow' ? '100.0' : '5.0'}
        />
      </Form.Item>
    </>
  );

  return (
    <div className="property-panel">
      <div className="panel-header">
        <h3>属性面板</h3>
        <p className="node-type-label">
          {selectedNode.type === NodeType.CANAL && '明渠'}
          {selectedNode.type === NodeType.GATE && '闸门'}
          {selectedNode.type === NodeType.BOUNDARY_FLOW && '流量边界'}
          {selectedNode.type === NodeType.BOUNDARY_DEPTH && '水深边界'}
        </p>
      </div>

      <div className="panel-body">
        <Form
          form={form}
          layout="vertical"
          onValuesChange={handleValuesChange}
          onFinish={handleFinish}
          size="small"
        >
          {renderForm()}

          <Divider style={{ margin: '16px 0' }} />

          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block>
              应用更改
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
};

export default PropertyPanel;
