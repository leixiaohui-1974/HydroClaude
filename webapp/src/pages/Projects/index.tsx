import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, Button, Space, Tag, Input, Select, Modal, Form, message, Spin } from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CopyOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import projectService, { Project } from '@/services/projects';

const { Option } = Select;

const typeMap: Record<string, { color: string; text: string }> = {
  steady: { color: 'blue', text: '稳态流' },
  unsteady: { color: 'purple', text: '非恒定流' },
  gate: { color: 'cyan', text: '闸门流' },
  network: { color: 'geekblue', text: '渠道网络' },
  draft: { color: 'default', text: '草稿' },
};

const statusMap: Record<string, { color: string; text: string }> = {
  draft: { color: 'default', text: '草稿' },
  completed: { color: 'success', text: '已完成' },
  running: { color: 'processing', text: '运行中' },
  pending: { color: 'warning', text: '待运行' },
  failed: { color: 'error', text: '失败' },
};

const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const data = await projectService.list();
      setProjects(data.items);
      setTotal(data.total);
    } catch {
      // API不可用时使用演示数据
      setProjects([
        { id: 1, name: '渠道稳态流分析', status: 'completed', config: { simulation: { type: 'steady' } }, created_at: '2025-11-10T00:00:00Z' },
        { id: 2, name: '闸门流动仿真', status: 'running', config: { simulation: { type: 'gate' } }, created_at: '2025-11-12T00:00:00Z' },
        { id: 3, name: '非恒定流计算', status: 'pending', config: { simulation: { type: 'unsteady' } }, created_at: '2025-11-13T00:00:00Z' },
      ]);
      setTotal(3);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const getProjectType = (project: Project): string => {
    return project.config?.simulation?.type || 'draft';
  };

  const columns: ColumnsType<Project> = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '类型',
      key: 'type',
      render: (_, record) => {
        const type = getProjectType(record);
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
      filters: [
        { text: '稳态流', value: 'steady' },
        { text: '非恒定流', value: 'unsteady' },
        { text: '闸门流', value: 'gate' },
      ],
      onFilter: (value, record) => getProjectType(record) === value,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '创建日期',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => date ? new Date(date).toLocaleDateString('zh-CN') : '-',
      sorter: (a, b) => new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime(),
    },
    {
      title: '更新日期',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date: string) => date ? new Date(date).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/editor/${record.id}`)}
          >
            编辑
          </Button>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRun(record)}
          >
            运行
          </Button>
          <Button
            type="link"
            icon={<CopyOutlined />}
            onClick={() => handleClone(record)}
          >
            克隆
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const handleRun = (project: Project) => {
    message.success(`开始运行项目: ${project.name}`);
    navigate(`/simulation/${project.id}`);
  };

  const handleClone = async (project: Project) => {
    try {
      const cloned = await projectService.create({
        name: `${project.name} (副本)`,
        description: project.description,
        config: project.config,
      });
      setProjects((prev) => [cloned, ...prev]);
      message.success(`已克隆项目: ${project.name}`);
    } catch {
      // 离线模式下的本地克隆
      const cloned: Project = {
        ...project,
        id: Date.now(),
        name: `${project.name} (副本)`,
        status: 'draft',
        created_at: new Date().toISOString(),
      };
      setProjects((prev) => [cloned, ...prev]);
      message.success(`已克隆项目: ${project.name}`);
    }
  };

  const handleDelete = (project: Project) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除项目"${project.name}"吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await projectService.delete(project.id);
        } catch {
          // 离线模式
        }
        setProjects((prev) => prev.filter((p) => p.id !== project.id));
        message.success('项目已删除');
      },
    });
  };

  const handleCreateProject = async () => {
    try {
      const values = await form.validateFields();
      const newProject = await projectService.create({
        name: values.name,
        description: values.description,
        config: { simulation: { type: values.type || 'steady', mode: 'single_canal' } },
      });
      setProjects((prev) => [newProject, ...prev]);
      message.success('项目创建成功！');
      setIsModalVisible(false);
      form.resetFields();
      navigate(`/editor/${newProject.id}`);
    } catch {
      // 离线模式 - 本地创建
      const values = form.getFieldsValue();
      if (!values.name) { message.error('请输入项目名称'); return; }
      const localProject: Project = {
        id: Date.now(),
        name: values.name,
        description: values.description,
        status: 'draft',
        config: { simulation: { type: values.type || 'steady', mode: 'single_canal' } },
        created_at: new Date().toISOString(),
      };
      setProjects((prev) => [localProject, ...prev]);
      message.success('项目创建成功！');
      setIsModalVisible(false);
      form.resetFields();
      navigate('/editor/new');
    }
  };

  const filteredProjects = projects.filter((p) => {
    const matchSearch = !searchText || p.name.toLowerCase().includes(searchText.toLowerCase());
    const matchType = filterType === 'all' || getProjectType(p) === filterType;
    return matchSearch && matchType;
  });

  return (
    <div>
      <Card
        title={`项目管理 (${total})`}
        extra={
          <Space>
            <Input
              placeholder="搜索项目"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 200 }}
              allowClear
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
              <Option value="network">渠道网络</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadProjects} />
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
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={filteredProjects}
            rowKey="id"
            pagination={{
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 个项目`,
              total: filteredProjects.length,
            }}
          />
        </Spin>
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
