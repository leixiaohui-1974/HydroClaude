import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Input, Select, Modal, Form, message } from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';

const { Option } = Select;

interface ProjectData {
  key: string;
  name: string;
  type: string;
  status: string;
  lastRun: string;
  created: string;
}

const initialData: ProjectData[] = [
  {
    key: '1',
    name: '渠道稳态流分析',
    type: 'steady',
    status: 'completed',
    lastRun: '2025-11-15 10:30',
    created: '2025-11-10',
  },
  {
    key: '2',
    name: '闸门流动仿真',
    type: 'gate',
    status: 'running',
    lastRun: '2025-11-15 09:15',
    created: '2025-11-12',
  },
  {
    key: '3',
    name: '非恒定流计算',
    type: 'unsteady',
    status: 'pending',
    lastRun: '2025-11-14 16:20',
    created: '2025-11-13',
  },
];

const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [projects, setProjects] = useState<ProjectData[]>(initialData);

  const columns: ColumnsType<ProjectData> = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          steady: { color: 'blue', text: '稳态流' },
          unsteady: { color: 'purple', text: '非恒定流' },
          gate: { color: 'cyan', text: '闸门流' },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
      filters: [
        { text: '稳态流', value: 'steady' },
        { text: '非恒定流', value: 'unsteady' },
        { text: '闸门流', value: 'gate' },
      ],
      onFilter: (value, record) => record.type === value,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          completed: { color: 'success', text: '已完成' },
          running: { color: 'processing', text: '运行中' },
          pending: { color: 'warning', text: '待运行' },
          failed: { color: 'error', text: '失败' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '最后运行',
      dataIndex: 'lastRun',
      key: 'lastRun',
      sorter: (a, b) => new Date(a.lastRun).getTime() - new Date(b.lastRun).getTime(),
    },
    {
      title: '创建日期',
      dataIndex: 'created',
      key: 'created',
      sorter: (a, b) => new Date(a.created).getTime() - new Date(b.created).getTime(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/editor/${record.key}`)}
          >
            编辑
          </Button>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRun(record.key)}
          >
            运行
          </Button>
          <Button
            type="link"
            icon={<CopyOutlined />}
            onClick={() => handleClone(record.key)}
          >
            克隆
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.key)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const handleRun = (key: string) => {
    message.success(`开始运行项目: ${key}`);
    navigate(`/simulation/${key}`);
  };

  const handleClone = (key: string) => {
    const source = projects.find((p) => p.key === key);
    if (!source) return;
    const newKey = String(Date.now());
    const cloned: ProjectData = {
      ...source,
      key: newKey,
      name: `${source.name} (副本)`,
      status: 'pending',
      lastRun: '-',
      created: new Date().toISOString().slice(0, 10),
    };
    setProjects((prev) => [...prev, cloned]);
    message.success(`已克隆项目: ${source.name}`);
  };

  const handleDelete = (key: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个项目吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        setProjects((prev) => prev.filter((p) => p.key !== key));
        message.success('项目已删除');
      },
    });
  };

  const handleCreateProject = () => {
    form.validateFields().then((values) => {
      console.log('创建项目:', values);
      message.success('项目创建成功！');
      setIsModalVisible(false);
      form.resetFields();
      navigate('/editor/new');
    });
  };

  return (
    <div>
      <Card
        title="项目管理"
        extra={
          <Space>
            <Input
              placeholder="搜索项目"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 200 }}
            />
            <Select
              value={filterType}
              onChange={setFilterType}
              style={{ width: 120 }}
            >
              <Option value="all">全部类型</Option>
              <Option value="steady">稳态流</Option>
              <Option value="unsteady">非恒定流</Option>
              <Option value="gate">闸门流</Option>
            </Select>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsModalVisible(true)}
            >
              新建项目
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={projects.filter((p) => {
            const matchSearch = !searchText || p.name.toLowerCase().includes(searchText.toLowerCase());
            const matchType = filterType === 'all' || p.type === filterType;
            return matchSearch && matchType;
          })}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个项目`,
          }}
        />
      </Card>

      <Modal
        title="创建新项目"
        open={isModalVisible}
        onOk={handleCreateProject}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="输入项目名称" />
          </Form.Item>
          <Form.Item
            name="type"
            label="项目类型"
            rules={[{ required: true, message: '请选择项目类型' }]}
          >
            <Select placeholder="选择项目类型">
              <Option value="steady">稳态流</Option>
              <Option value="unsteady">非恒定流</Option>
              <Option value="gate">闸门流</Option>
              <Option value="network">渠道网络</Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea rows={4} placeholder="输入项目描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProjectsPage;
