import { useState } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Button,
  Select,
  Space,
  Divider,
  message,
  Spin,
  Progress
} from 'antd';
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  createSimulation,
  getSimulationStatus,
  getSimulationResults,
  SimulationRequest,
  SimulationResultResponse
} from '@/services/simulation-api';

const { Option } = Select;

interface SimulationConfigFormProps {
  onSimulationComplete: (taskId: string, result: SimulationResultResponse) => void;
}

const SimulationConfigForm = ({ onSimulationComplete }: SimulationConfigFormProps) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [_currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  // Poll simulation status
  const pollSimulationStatus = async (taskId: string) => {
    const maxAttempts = 60; // 60 seconds max
    let attempts = 0;

    const poll = setInterval(async () => {
      attempts++;

      try {
        const status = await getSimulationStatus(taskId);

        // Update progress
        if (status.progress !== undefined) {
          setProgress(status.progress);
        }

        if (status.status === 'completed') {
          clearInterval(poll);
          // Fetch results
          const result = await getSimulationResults(taskId);
          setLoading(false);
          setProgress(100);
          message.success('仿真完成！');
          onSimulationComplete(taskId, result);
        } else if (status.status === 'failed') {
          clearInterval(poll);
          setLoading(false);
          message.error(`仿真失败: ${status.error || '未知错误'}`);
        } else if (attempts >= maxAttempts) {
          clearInterval(poll);
          setLoading(false);
          message.warning('仿真超时，请稍后查看结果');
        }
      } catch (error) {
        clearInterval(poll);
        setLoading(false);
        message.error('查询仿真状态失败');
        console.error(error);
      }
    }, 1000);
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    setProgress(0);

    try {
      // Prepare simulation request
      const request: SimulationRequest = {
        name: values.name || 'Unnamed Simulation',
        description: values.description,
        config: {
          width: values.width,
          length: values.length,
          n_cells: values.n_cells,
          manning_n: values.manning_n || 0.0,
          slope: values.slope || 0.0,
          t_end: values.t_end,
          dt_max: values.dt_max || 0.1,
          output_interval: values.output_interval || 0.5,
          initial_conditions: {
            type: values.ic_type,
            h: values.ic_type === 'uniform' ? values.ic_h : undefined,
            Q: values.ic_type === 'uniform' ? values.ic_Q : undefined,
            dam_position: values.ic_type === 'dam_break' ? values.dam_position : undefined,
            h_left: values.ic_type === 'dam_break' ? values.h_left : undefined,
            h_right: values.ic_type === 'dam_break' ? values.h_right : undefined,
            Q_left: values.ic_type === 'dam_break' ? values.Q_left : undefined,
            Q_right: values.ic_type === 'dam_break' ? values.Q_right : undefined,
          },
          boundary_conditions: {
            upstream: {
              type: values.bc_upstream_type || 'h',
              value: values.bc_upstream_value
            },
            downstream: {
              type: values.bc_downstream_type || 'h',
              value: values.bc_downstream_value
            }
          }
        }
      };

      // Create simulation
      const response = await createSimulation(request);
      setCurrentTaskId(response.task_id);
      message.info('仿真已提交，正在运行...');

      // Start polling
      await pollSimulationStatus(response.task_id);

    } catch (error: any) {
      setLoading(false);
      message.error(`提交失败: ${error.response?.data?.detail || error.message}`);
      console.error(error);
    }
  };

  const handleReset = () => {
    form.resetFields();
    setProgress(0);
    setCurrentTaskId(null);
  };

  return (
    <Spin spinning={loading} tip={`仿真运行中... ${progress.toFixed(0)}%`}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          name: '均匀流测试',
          width: 10.0,
          length: 1000.0,
          n_cells: 100,
          manning_n: 0.0,
          slope: 0.0,
          t_end: 10.0,
          dt_max: 0.1,
          output_interval: 0.5,
          ic_type: 'uniform',
          ic_h: 5.0,
          ic_Q: 0.0,
          bc_upstream_type: 'h',
          bc_upstream_value: 5.0,
          bc_downstream_type: 'h',
          bc_downstream_value: 5.0
        }}
      >
        {/* Basic Info */}
        <Form.Item label="仿真名称" name="name">
          <Input placeholder="输入仿真名称" />
        </Form.Item>

        <Form.Item label="描述" name="description">
          <Input.TextArea rows={2} placeholder="可选的仿真描述" />
        </Form.Item>

        <Divider orientation="left">几何参数</Divider>

        <Form.Item label="渠道宽度 (m)" name="width" rules={[{ required: true }]}>
          <InputNumber min={0.1} max={1000} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item label="渠道长度 (m)" name="length" rules={[{ required: true }]}>
          <InputNumber min={1} max={100000} step={10} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item label="网格单元数" name="n_cells" rules={[{ required: true }]}>
          <InputNumber min={10} max={10000} step={10} style={{ width: '100%' }} />
        </Form.Item>

        <Divider orientation="left">物理参数</Divider>

        <Form.Item label="曼宁糙率系数" name="manning_n">
          <InputNumber min={0} max={0.1} step={0.001} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item label="底坡" name="slope">
          <InputNumber min={0} max={0.1} step={0.0001} style={{ width: '100%' }} />
        </Form.Item>

        <Divider orientation="left">时间参数</Divider>

        <Form.Item label="结束时间 (s)" name="t_end" rules={[{ required: true }]}>
          <InputNumber min={0.1} max={10000} step={1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item label="最大时间步长 (s)" name="dt_max">
          <InputNumber min={0.001} max={1} step={0.01} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item label="输出间隔 (s)" name="output_interval">
          <InputNumber min={0.1} max={100} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Divider orientation="left">初始条件</Divider>

        <Form.Item label="类型" name="ic_type">
          <Select>
            <Option value="uniform">均匀流</Option>
            <Option value="dam_break">溃坝</Option>
          </Select>
        </Form.Item>

        <Form.Item
          noStyle
          shouldUpdate={(prevValues, currentValues) => prevValues.ic_type !== currentValues.ic_type}
        >
          {({ getFieldValue }) =>
            getFieldValue('ic_type') === 'uniform' ? (
              <>
                <Form.Item label="初始水深 (m)" name="ic_h">
                  <InputNumber min={0} max={100} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="初始流量 (m³/s)" name="ic_Q">
                  <InputNumber min={0} max={10000} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </>
            ) : (
              <>
                <Form.Item label="溃坝位置 (m)" name="dam_position">
                  <InputNumber min={0} max={100000} step={10} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="左侧水深 (m)" name="h_left">
                  <InputNumber min={0} max={100} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="右侧水深 (m)" name="h_right">
                  <InputNumber min={0} max={100} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="左侧流量 (m³/s)" name="Q_left">
                  <InputNumber min={0} max={10000} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="右侧流量 (m³/s)" name="Q_right">
                  <InputNumber min={0} max={10000} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </>
            )
          }
        </Form.Item>

        <Divider orientation="left">边界条件</Divider>

        <Form.Item label="上游边界类型" name="bc_upstream_type">
          <Select>
            <Option value="h">固定水深</Option>
            <Option value="Q">固定流量</Option>
            <Option value="wall">壁面</Option>
          </Select>
        </Form.Item>

        <Form.Item label="上游边界值" name="bc_upstream_value">
          <InputNumber min={0} max={10000} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item label="下游边界类型" name="bc_downstream_type">
          <Select>
            <Option value="h">固定水深</Option>
            <Option value="Q">固定流量</Option>
            <Option value="wall">壁面</Option>
          </Select>
        </Form.Item>

        <Form.Item label="下游边界值" name="bc_downstream_value">
          <InputNumber min={0} max={10000} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        {loading && progress > 0 && (
          <Form.Item>
            <Progress percent={progress} status="active" />
          </Form.Item>
        )}

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<PlayCircleOutlined />}
              loading={loading}
            >
              运行仿真
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Spin>
  );
};

export default SimulationConfigForm;
