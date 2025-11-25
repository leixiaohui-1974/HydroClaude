import { useState, useEffect } from 'react';
import { Form, Input, InputNumber, Button, Select, Space, Divider, message, Spin, Progress, Typography } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, ExperimentOutlined } from '@ant-design/icons';
import { createSimulation, getSimulationStatus, getSimulationResults, SimulationRequest, SimulationResultResponse } from '@/services/simulation-api';
import { api as testCaseApi, TestCase } from '@/services/test-cases-api';

const { Option } = Select;
const { Text } = Typography;

// Define a type for the global test helper
declare global {
  interface Window {
    runSingleTestCase: (caseId: string) => Promise<void>;
  }
}

interface SimulationConfigFormProps {
  onSimulationComplete: (taskId: string, result: SimulationResultResponse) => void;
}

const SimulationConfigForm = ({ onSimulationComplete }: SimulationConfigFormProps) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  // Expose a helper for the parent component to trigger a run
  useEffect(() => {
    window.runSingleTestCase = async (caseId: string) => {
      await handleTestCaseSelect(caseId, true); // Select and auto-submit
    };
    return () => { // @ts-ignore
      delete window.runSingleTestCase;
    };
  }, [form]);

  const [testCases, setTestCases] = useState<TestCase[]>([]);
  useEffect(() => {
    const fetchTestCases = async () => {
      try {
        const response = await testCaseApi.getAllTestCases(550, 0);
        setTestCases(response.cases);
      } catch (error) {
        message.error('加载测试案例列表失败');
      }
    };
    fetchTestCases();
  }, []);

  const handleTestCaseSelect = async (caseId: string, autoSubmit = false) => {
    if (!caseId) return;
    try {
      const caseDetail = await testCaseApi.getTestCaseDetail(caseId);
      const { config = {}, metadata = {} } = caseDetail;
      const formValues = {
        name: metadata.nameCN || metadata.name || `测试: ${caseId}`,
        description: `基于预设案例: ${caseId}`,
        width: config.width,
        length: config.domainLength,
        n_cells: config.nCells,
        manning_n: config.manning,
        slope: config.slope,
        t_end: config.duration || 10.0,
      };
      form.setFieldsValue(formValues);
      if (autoSubmit) {
        setTimeout(() => form.submit(), 100);
      }
    } catch (error) {
      message.error(`加载案例配置失败: ${caseId}`);
    }
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    setProgress(0);
    return new Promise<void>(async (resolve, reject) => {
      try {
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
          }
        };
        const response = await createSimulation(request);

        const poll = setInterval(async () => {
          try {
            const status = await getSimulationStatus(response.task_id);
            if (status.progress !== undefined) setProgress(status.progress);
            if (status.status === 'completed') {
              clearInterval(poll);
              const result = await getSimulationResults(response.task_id);
              setLoading(false);
              onSimulationComplete(response.task_id, result);
              resolve();
            } else if (status.status === 'failed') {
              clearInterval(poll);
              setLoading(false);
              message.error(`案例 ${values.name} 仿真失败!`);
              reject(new Error(status.error || '未知错误'));
            }
          } catch {
            clearInterval(poll);
            setLoading(false);
            reject(new Error('轮询状态失败'));
          }
        }, 2000);
      } catch (error: any) {
        setLoading(false);
        message.error(`提交失败: ${error.message}`);
        reject(error);
      }
    });
  };

  return (
    <Spin spinning={loading} tip={`仿真运行中... ${progress.toFixed(0)}%`}>
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item label={<Text strong><ExperimentOutlined /> 从预设案例加载</Text>}>
          <Select
            id="test-case-selector"
            showSearch
            placeholder="搜索或选择一个案例以自动填充表单..."
            onSelect={(value) => handleTestCaseSelect(value, false)}
            loading={testCases.length === 0}
            filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
            options={testCases.map(tc => ({
              value: tc.metadata.id,
              label: `${tc.metadata.nameCN || tc.metadata.name} (${tc.metadata.id})`
            }))}
          />
        </Form.Item>
        <Divider />
        <Form.Item label="仿真名称" name="name"><Input /></Form.Item>
        <Form.Item label="描述" name="description"><Input.TextArea rows={2} /></Form.Item>
        <Divider orientation="left">几何参数</Divider>
        <Form.Item label="渠道宽度 (m)" name="width" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
        <Form.Item label="渠道长度 (m)" name="length" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
        <Form.Item label="网格单元数" name="n_cells" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
        <Divider orientation="left">物理参数</Divider>
        <Form.Item label="曼宁糙率系数" name="manning_n"><InputNumber style={{ width: '100%' }} /></Form.Item>
        <Form.Item label="底坡" name="slope"><InputNumber style={{ width: '100%' }} /></Form.Item>
        <Divider orientation="left">时间参数</Divider>
        <Form.Item label="结束时间 (s)" name="t_end" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />} loading={loading}>运行仿真</Button>
            <Button icon={<ReloadOutlined />} onClick={() => form.resetFields()}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
    </Spin>
  );
};

export default SimulationConfigForm;
