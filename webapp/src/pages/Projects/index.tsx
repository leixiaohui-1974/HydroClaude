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
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import projectService, { Project } from '@/services/projects';

const { Option } = Select;

const typeColorMap: Record<string, string> = {
  steady: 'blue',
  unsteady: 'purple',
  gate: 'cyan',
  network: 'geekblue',
  draft: 'default',
};

const typeI18nMap: Record<string, string> = {
  steady: 'projects.steadyFlow',
  unsteady: 'projects.unsteadyFlow',
  gate: 'projects.gateFlow',
  network: 'projects.canalNetwork',
  draft: 'projects.draft',
};

const statusColorMap: Record<string, string> = {
  draft: 'default',
  completed: 'success',
  running: 'processing',
  pending: 'warning',
  failed: 'error',
};

const statusI18nMap: Record<string, string> = {
  draft: 'projects.statusDraft',
  completed: 'projects.statusCompleted',
  running: 'projects.statusRunning',
  pending: 'projects.statusPending',
  failed: 'projects.statusFailed',
};

const ProjectsPage: React.FC = () => {
  const { t } = useTranslation();
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
      // API not available - use demo data
      setProjects([
        { id: 1, name: t('home.canalSteadyFlow'), status: 'completed', config: { simulation: { type: 'steady' } }, created_at: '2025-11-10T00:00:00Z' },
        { id: 2, name: t('home.gateFlowAnalysis'), status: 'running', config: { simulation: { type: 'gate' } }, created_at: '2025-11-12T00:00:00Z' },
        { id: 3, name: t('home.unsteadyFlowSim'), status: 'pending', config: { simulation: { type: 'unsteady' } }, created_at: '2025-11-13T00:00:00Z' },
      ]);
      setTotal(3);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const getProjectType = (project: Project): string => {
    return project.config?.simulation?.type || 'draft';
  };

  const columns: ColumnsType<Project> = [
    {
      title: t('projects.projectName'),
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: t('projects.type'),
      key: 'type',
      render: (_, record) => {
        const type = getProjectType(record);
        const color = typeColorMap[type] || 'default';
        const text = typeI18nMap[type] ? t(typeI18nMap[type]) : type;
        return <Tag color={color}>{text}</Tag>;
      },
      filters: [
        { text: t('projects.steadyFlow'), value: 'steady' },
        { text: t('projects.unsteadyFlow'), value: 'unsteady' },
        { text: t('projects.gateFlow'), value: 'gate' },
      ],
      onFilter: (value, record) => getProjectType(record) === value,
    },
    {
      title: t('projects.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const color = statusColorMap[status] || 'default';
        const text = statusI18nMap[status] ? t(statusI18nMap[status]) : status;
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: t('projects.createdDate'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => date ? new Date(date).toLocaleDateString() : '-',
      sorter: (a, b) => new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime(),
    },
    {
      title: t('projects.updatedDate'),
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date: string) => date ? new Date(date).toLocaleDateString() : '-',
    },
    {
      title: t('projects.actions'),
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/editor/${record.id}`)}
          >
            {t('projects.editBtn')}
          </Button>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRun(record)}
          >
            {t('projects.runBtn')}
          </Button>
          <Button
            type="link"
            icon={<CopyOutlined />}
            onClick={() => handleClone(record)}
          >
            {t('projects.cloneBtn')}
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            {t('projects.deleteBtn')}
          </Button>
        </Space>
      ),
    },
  ];

  const handleRun = (project: Project) => {
    message.success(t('projects.runStarted', { key: project.name }));
    navigate(`/simulation/${project.id}`);
  };

  const handleClone = async (project: Project) => {
    try {
      const cloned = await projectService.create({
        name: `${project.name} ${t('projects.cloneSuffix')}`,
        description: project.description,
        config: project.config,
      });
      setProjects((prev) => [cloned, ...prev]);
      message.success(t('projects.cloneSuccess', { name: project.name }));
    } catch {
      // Offline mode - local clone
      const cloned: Project = {
        ...project,
        id: Date.now(),
        name: `${project.name} ${t('projects.cloneSuffix')}`,
        status: 'draft',
        created_at: new Date().toISOString(),
      };
      setProjects((prev) => [cloned, ...prev]);
      message.success(t('projects.cloneSuccess', { name: project.name }));
    }
  };

  const handleDelete = (project: Project) => {
    Modal.confirm({
      title: t('projects.confirmDelete'),
      content: t('projects.confirmDeleteSpecific', { name: project.name }),
      okText: t('common.delete'),
      okType: 'danger',
      cancelText: t('common.cancel'),
      onOk: async () => {
        try {
          await projectService.delete(project.id);
        } catch {
          // Offline mode
        }
        setProjects((prev) => prev.filter((p) => p.id !== project.id));
        message.success(t('projects.projectDeleted'));
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
      message.success(t('projects.projectCreated'));
      setIsModalVisible(false);
      form.resetFields();
      navigate(`/editor/${newProject.id}`);
    } catch {
      // Offline mode - local creation
      const values = form.getFieldsValue();
      if (!values.name) { message.error(t('projects.pleaseEnterProjectName')); return; }
      const localProject: Project = {
        id: Date.now(),
        name: values.name,
        description: values.description,
        status: 'draft',
        config: { simulation: { type: values.type || 'steady', mode: 'single_canal' } },
        created_at: new Date().toISOString(),
      };
      setProjects((prev) => [localProject, ...prev]);
      message.success(t('projects.projectCreated'));
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
        title={`${t('projects.title')} (${total})`}
        extra={
          <Space>
            <Input
              placeholder={t('projects.searchPlaceholder')}
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
              <Option value="all">{t('projects.allTypes')}</Option>
              <Option value="steady">{t('projects.steadyFlow')}</Option>
              <Option value="unsteady">{t('projects.unsteadyFlow')}</Option>
              <Option value="gate">{t('projects.gateFlow')}</Option>
              <Option value="network">{t('projects.canalNetwork')}</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={loadProjects} />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsModalVisible(true)}
            >
              {t('projects.newProject')}
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
              showTotal: (total) => t('projects.totalProjects', { total }),
              total: filteredProjects.length,
            }}
          />
        </Spin>
      </Card>

      <Modal
        title={t('projects.createProjectTitle')}
        open={isModalVisible}
        onOk={handleCreateProject}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        okText={t('common.create')}
        cancelText={t('common.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('projects.projectName')}
            rules={[{ required: true, message: t('projects.pleaseEnterProjectName') }]}
          >
            <Input placeholder={t('projects.enterProjectName')} />
          </Form.Item>
          <Form.Item
            name="type"
            label={t('projects.projectType')}
            rules={[{ required: true, message: t('projects.pleaseSelectProjectType') }]}
          >
            <Select placeholder={t('projects.selectProjectType')}>
              <Option value="steady">{t('projects.steadyFlow')}</Option>
              <Option value="unsteady">{t('projects.unsteadyFlow')}</Option>
              <Option value="gate">{t('projects.gateFlow')}</Option>
              <Option value="network">{t('projects.canalNetwork')}</Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label={t('projects.projectDescription')}>
            <Input.TextArea rows={4} placeholder={t('projects.enterProjectDescription')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProjectsPage;
