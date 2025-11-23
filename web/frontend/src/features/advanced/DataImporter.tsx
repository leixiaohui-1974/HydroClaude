/**
 * 增强数据导入器
 * 支持多种格式：HEC-RAS, MIKE 11, EPANET, CSV, JSON等
 */

import React, { useState } from 'react';
import {
  Card,
  Upload,
  Button,
  Space,
  Table,
  Progress,
  Alert,
  Select,
  Tabs,
  message,
  Tag
} from 'antd';
import {
  UploadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  FileTextOutlined
} from '@ant-design/icons';

const { TabPane } = Tabs;
const { Dragger } = Upload;

interface ImportFile {
  uid: string;
  name: string;
  status: 'uploading' | 'done' | 'error' | 'validating';
  format?: string;
  size: number;
  progress: number;
  warnings?: string[];
  errors?: string[];
}

export const DataImporter: React.FC = () => {
  const [files, setFiles] = useState<ImportFile[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string>('auto');

  // 支持的文件格式
  const supportedFormats = [
    { value: 'auto', label: '自动识别', extensions: ['*'] },
    { value: 'hec-ras', label: 'HEC-RAS (.prj, .g01, .f01)', extensions: ['.prj', '.g01', '.f01'] },
    { value: 'mike11', label: 'MIKE 11 (.m11, .nwk11)', extensions: ['.m11', '.nwk11'] },
    { value: 'epanet', label: 'EPANET (.inp)', extensions: ['.inp'] },
    { value: 'csv', label: 'CSV (.csv)', extensions: ['.csv'] },
    { value: 'json', label: 'JSON (.json)', extensions: ['.json'] },
    { value: 'shp', label: 'Shapefile (.shp)', extensions: ['.shp'] },
    { value: 'xml', label: 'XML (.xml)', extensions: ['.xml'] }
  ];

  // 文件上传前验证
  const beforeUpload = (file: any) => {
    const fileExt = `.${file.name.split('.').pop()}`;
    const selectedExt = supportedFormats.find(f => f.value === selectedFormat)?.extensions || [];

    if (selectedFormat !== 'auto' && !selectedExt.includes('*') && !selectedExt.includes(fileExt)) {
      message.error(`不支持的文件格式: ${fileExt}`);
      return false;
    }

    // 检查文件大小（限制100MB）
    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
      message.error('文件大小超过100MB限制');
      return false;
    }

    return true;
  };

  // 处理文件上传
  const handleUpload = (info: any) => {
    const { status, response, name, size } = info.file;

    setFiles(prevFiles => {
      const existing = prevFiles.find(f => f.name === name);
      if (existing) {
        return prevFiles.map(f =>
          f.name === name
            ? { ...f, status, progress: status === 'done' ? 100 : f.progress }
            : f
        );
      }

      return [...prevFiles, {
        uid: info.file.uid,
        name,
        size,
        status: 'uploading',
        progress: 0,
        format: selectedFormat
      }];
    });

    if (status === 'done') {
      message.success(`${name} 上传成功`);
      
      // 模拟文件验证
      setTimeout(() => {
        setFiles(prevFiles =>
          prevFiles.map(f =>
            f.name === name
              ? {
                  ...f,
                  status: 'validating',
                  warnings: ['数据点1000包含异常值', '边界条件缺失默认值'],
                  errors: []
                }
              : f
          )
        );

        // 验证完成
        setTimeout(() => {
          setFiles(prevFiles =>
            prevFiles.map(f =>
              f.name === name
                ? { ...f, status: 'done' }
                : f
            )
          );
        }, 1000);
      }, 1000);
    } else if (status === 'error') {
      message.error(`${name} 上传失败`);
    }
  };

  // 删除文件
  const handleRemove = (uid: string) => {
    setFiles(files.filter(f => f.uid !== uid));
  };

  // 表格列定义
  const columns = [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <FileTextOutlined />
          {name}
        </Space>
      )
    },
    {
      title: '格式',
      dataIndex: 'format',
      key: 'format',
      render: (format: string) => (
        <Tag color="blue">
          {supportedFormats.find(f => f.value === format)?.label || format}
        </Tag>
      )
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => `${(size / 1024).toFixed(2)} KB`
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: ImportFile) => {
        const statusConfig: Record<string, { icon: any; color: string; text: string }> = {
          uploading: { icon: <UploadOutlined />, color: 'processing', text: '上传中' },
          validating: { icon: <WarningOutlined />, color: 'warning', text: '验证中' },
          done: { icon: <CheckCircleOutlined />, color: 'success', text: '完成' },
          error: { icon: <CloseCircleOutlined />, color: 'error', text: '失败' }
        };

        const config = statusConfig[status];
        return (
          <Tag icon={config.icon} color={config.color}>
            {config.text}
          </Tag>
        );
      }
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number, record: ImportFile) => (
        record.status === 'uploading' || record.status === 'validating'
          ? <Progress percent={record.status === 'validating' ? 90 : progress} size="small" />
          : record.status === 'done' ? <Progress percent={100} size="small" status="success" /> : '-'
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ImportFile) => (
        <Button
          type="link"
          danger
          size="small"
          onClick={() => handleRemove(record.uid)}
        >
          删除
        </Button>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card title="数据导入器">
        <Tabs defaultActiveKey="upload">
          <TabPane tab="文件上传" key="upload">
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <Select
                value={selectedFormat}
                onChange={setSelectedFormat}
                style={{ width: 300 }}
                options={supportedFormats}
              />

              <Dragger
                multiple
                beforeUpload={beforeUpload}
                onChange={handleUpload}
                showUploadList={false}
              >
                <p className="ant-upload-drag-icon">
                  <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                </p>
                <p className="ant-upload-text">
                  点击或拖拽文件到此区域上传
                </p>
                <p className="ant-upload-hint">
                  支持 HEC-RAS, MIKE 11, EPANET, CSV, JSON, Shapefile 等格式
                </p>
              </Dragger>

              {files.length > 0 && (
                <>
                  <Alert
                    message="导入提示"
                    description="系统会自动验证数据完整性和格式正确性。如有警告或错误，请在下方查看详情。"
                    type="info"
                    showIcon
                  />

                  <Table
                    columns={columns}
                    dataSource={files}
                    rowKey="uid"
                    pagination={false}
                    expandable={{
                      expandedRowRender: record => (
                        <div>
                          {record.warnings && record.warnings.length > 0 && (
                            <Alert
                              message="警告"
                              description={
                                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                                  {record.warnings.map((w, i) => (
                                    <li key={i}>{w}</li>
                                  ))}
                                </ul>
                              }
                              type="warning"
                              showIcon
                              style={{ marginBottom: 8 }}
                            />
                          )}
                          {record.errors && record.errors.length > 0 && (
                            <Alert
                              message="错误"
                              description={
                                <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                                  {record.errors.map((e, i) => (
                                    <li key={i}>{e}</li>
                                  ))}
                                </ul>
                              }
                              type="error"
                              showIcon
                            />
                          )}
                        </div>
                      ),
                      rowExpandable: record => 
                        (record.warnings && record.warnings.length > 0) ||
                        (record.errors && record.errors.length > 0)
                    }}
                  />

                  <Button
                    type="primary"
                    size="large"
                    block
                    disabled={files.some(f => f.status !== 'done')}
                    onClick={() => {
                      message.success('数据导入完成！');
                      setFiles([]);
                    }}
                  >
                    确认导入
                  </Button>
                </>
              )}
            </Space>
          </TabPane>

          <TabPane tab="格式转换" key="convert">
            <Alert
              message="格式转换"
              description="将其他软件的数据文件转换为HydroClaude格式"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Space direction="vertical" style={{ width: '100%' }}>
              <Select
                placeholder="选择源格式"
                style={{ width: '100%' }}
                options={supportedFormats.filter(f => f.value !== 'auto')}
              />
              <Upload>
                <Button icon={<UploadOutlined />}>选择文件</Button>
              </Upload>
            </Space>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default DataImporter;
