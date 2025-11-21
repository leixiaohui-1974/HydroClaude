/**
 * 批处理管理器
 * 对标 HEC-RAS 和 MIKE 11 的批处理功能
 */

import React, { useState } from 'react';
import {
  Button,
  Table,
  Card,
  Space,
  Progress,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Upload
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  PlusOutlined,
  DownloadOutlined,
  UploadOutlined
} from '@ant-design/icons';

const { TextArea } = Input;

interface BatchJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  config: any;
  results?: any;
  startTime?: Date;
  endTime?: Date;
}

export const BatchManager: React.FC = () => {
  const [jobs, setJobs] = useState<BatchJob[]>([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 添加批处理任务
  const handleAddJob = () => {
    setIsModalVisible(true);
  };

  // 提交新任务
  const handleSubmit = (values: any) => {
    const newJob: BatchJob = {
      id: `job_${Date.now()}`,
      name: values.name,
      status: 'pending',
      progress: 0,
      config: values
    };

    setJobs([...jobs, newJob]);
    message.success('批处理任务已添加');
    setIsModalVisible(false);
    form.resetFields();
  };

  // 运行任务
  const handleRunJob = (jobId: string) => {
    setJobs(jobs.map(job => 
      job.id === jobId 
        ? { ...job, status: 'running', startTime: new Date() }
        : job
    ));

    // 模拟进度更新
    const interval = setInterval(() => {
      setJobs(prevJobs => {
        const job = prevJobs.find(j => j.id === jobId);
        if (!job || job.progress >= 100) {
          clearInterval(interval);
          return prevJobs.map(j =>
            j.id === jobId
              ? { ...j, status: 'completed', progress: 100, endTime: new Date() }
              : j
          );
        }

        return prevJobs.map(j =>
          j.id === jobId
            ? { ...j, progress: Math.min(j.progress + 10, 100) }
            : j
        );
      });
    }, 500);
  };

  // 删除任务
  const handleDeleteJob = (jobId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个批处理任务吗？',
      onOk: () => {
        setJobs(jobs.filter(job => job.id !== jobId));
        message.success('任务已删除');
      }
    });
  };

  // 导出结果
  const handleExportResults = () => {
    const completedJobs = jobs.filter(job => job.status === 'completed');
    if (completedJobs.length === 0) {
      message.warning('没有已完成的任务可导出');
      return;
    }

    const data = completedJobs.map(job => ({
      name: job.name,
      duration: job.endTime && job.startTime
        ? (job.endTime.getTime() - job.startTime.getTime()) / 1000
        : 0,
      config: job.config
    }));

    const dataStr = JSON.stringify(data, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `batch_results_${Date.now()}.json`;
    link.click();
    message.success('结果已导出');
  };

  // 表格列定义
  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          completed: 'success',
          failed: 'error'
        };
        const textMap: Record<string, string> = {
          pending: '等待中',
          running: '运行中',
          completed: '已完成',
          failed: '失败'
        };
        return <Tag color={colorMap[status]}>{textMap[status]}</Tag>;
      }
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number, record: BatchJob) => (
        record.status === 'running' || record.status === 'completed'
          ? <Progress percent={progress} size="small" />
          : '-'
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: BatchJob) => (
        <Space size="small">
          {record.status === 'pending' && (
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => handleRunJob(record.id)}
            >
              运行
            </Button>
          )}
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteJob(record.id)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="批处理管理器"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddJob}
            >
              添加任务
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExportResults}
            >
              导出结果
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={jobs}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 添加任务Modal */}
      <Modal
        title="添加批处理任务"
        open={isModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：多流量场景分析" />
          </Form.Item>

          <Form.Item
            label="计算类型"
            name="calculationType"
            rules={[{ required: true, message: '请选择计算类型' }]}
          >
            <Select placeholder="选择计算类型">
              <Select.Option value="steady">稳态流动</Select.Option>
              <Select.Option value="unsteady">非稳态流动</Select.Option>
              <Select.Option value="water_quality">水质模拟</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="流量范围"
            name="flowRange"
          >
            <Space>
              <InputNumber placeholder="最小流量" min={0} />
              <span>-</span>
              <InputNumber placeholder="最大流量" min={0} />
              <span>m³/s</span>
            </Space>
          </Form.Item>

          <Form.Item
            label="参数配置"
            name="parameters"
          >
            <TextArea
              rows={4}
              placeholder="输入JSON格式的参数配置"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default BatchManager;
