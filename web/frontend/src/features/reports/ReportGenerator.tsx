/**
 * 报告生成器
 * 对标 HEC-RAS 和 MIKE 11 的专业报告生成功能
 */

import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Divider,
  Checkbox,
  Radio,
  DatePicker,
  Upload,
  message,
  Steps
} from 'antd';
import {
  FileTextOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  DownloadOutlined,
  PictureOutlined
} from '@ant-design/icons';

const { TextArea } = Input;
const { Step } = Steps;

interface ReportSection {
  key: string;
  title: string;
  description: string;
  required: boolean;
}

export const ReportGenerator: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [reportConfig, setReportConfig] = useState<any>({});
  const [form] = Form.useForm();

  // 报告章节选项
  const reportSections: ReportSection[] = [
    {
      key: 'executive_summary',
      title: '执行摘要',
      description: '项目概述和主要发现',
      required: true
    },
    {
      key: 'project_info',
      title: '项目信息',
      description: '项目基本信息和背景',
      required: true
    },
    {
      key: 'model_description',
      title: '模型描述',
      description: '模型几何和参数配置',
      required: true
    },
    {
      key: 'calculation_settings',
      title: '计算设置',
      description: '计算参数和边界条件',
      required: true
    },
    {
      key: 'results_analysis',
      title: '结果分析',
      description: '计算结果和图表',
      required: true
    },
    {
      key: 'validation',
      title: '模型验证',
      description: '验证方法和结果',
      required: false
    },
    {
      key: 'sensitivity_analysis',
      title: '敏感性分析',
      description: '参数敏感性分析',
      required: false
    },
    {
      key: 'conclusions',
      title: '结论和建议',
      description: '主要结论和改进建议',
      required: true
    },
    {
      key: 'appendix',
      title: '附录',
      description: '详细数据和计算结果',
      required: false
    }
  ];

  // 生成报告
  const handleGenerateReport = () => {
    const values = form.getFieldsValue();
    
    message.loading('正在生成报告...', 0);

    // 模拟报告生成
    setTimeout(() => {
      message.destroy();
      message.success('报告生成成功！');

      // 模拟下载
      const reportData = {
        ...reportConfig,
        ...values,
        generatedAt: new Date().toISOString()
      };

      const dataStr = JSON.stringify(reportData, null, 2);
      const blob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `hydraulic_report_${Date.now()}.json`;
      link.click();
    }, 2000);
  };

  // 步骤内容
  const steps = [
    {
      title: '基本信息',
      content: (
        <>
          <Form.Item
            label="报告标题"
            name="title"
            rules={[{ required: true, message: '请输入报告标题' }]}
          >
            <Input placeholder="例如：XX渠道水力计算分析报告" />
          </Form.Item>

          <Form.Item
            label="项目名称"
            name="projectName"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="项目名称" />
          </Form.Item>

          <Form.Item
            label="编制单位"
            name="organization"
            rules={[{ required: true, message: '请输入编制单位' }]}
          >
            <Input placeholder="编制单位" />
          </Form.Item>

          <Form.Item
            label="报告日期"
            name="reportDate"
            rules={[{ required: true, message: '请选择报告日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="项目简介"
            name="description"
          >
            <TextArea
              rows={4}
              placeholder="简要描述项目背景、目标和范围"
            />
          </Form.Item>
        </>
      )
    },
    {
      title: '章节选择',
      content: (
        <>
          <Form.Item
            label="选择报告章节"
            name="sections"
            initialValue={reportSections.filter(s => s.required).map(s => s.key)}
          >
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {reportSections.map(section => (
                  <Checkbox
                    key={section.key}
                    value={section.key}
                    disabled={section.required}
                  >
                    <Space direction="vertical" size={0}>
                      <strong>{section.title}</strong>
                      <span style={{ color: '#999', fontSize: '12px' }}>
                        {section.description}
                        {section.required && ' (必需)'}
                      </span>
                    </Space>
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          </Form.Item>
        </>
      )
    },
    {
      title: '格式设置',
      content: (
        <>
          <Form.Item
            label="输出格式"
            name="format"
            initialValue="pdf"
          >
            <Radio.Group>
              <Radio.Button value="pdf">
                <FilePdfOutlined /> PDF
              </Radio.Button>
              <Radio.Button value="word">
                <FileWordOutlined /> Word
              </Radio.Button>
              <Radio.Button value="html">
                <FileTextOutlined /> HTML
              </Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item
            label="页面尺寸"
            name="pageSize"
            initialValue="A4"
          >
            <Select>
              <Select.Option value="A4">A4 (210 × 297 mm)</Select.Option>
              <Select.Option value="A3">A3 (297 × 420 mm)</Select.Option>
              <Select.Option value="Letter">Letter (216 × 279 mm)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="图表质量"
            name="imageQuality"
            initialValue="high"
          >
            <Select>
              <Select.Option value="low">低 (72 DPI)</Select.Option>
              <Select.Option value="medium">中 (150 DPI)</Select.Option>
              <Select.Option value="high">高 (300 DPI)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="包含内容"
            name="includeOptions"
            initialValue={['tables', 'charts', 'maps']}
          >
            <Checkbox.Group>
              <Space direction="vertical">
                <Checkbox value="tables">数据表格</Checkbox>
                <Checkbox value="charts">图表</Checkbox>
                <Checkbox value="maps">地图</Checkbox>
                <Checkbox value="photos">照片</Checkbox>
                <Checkbox value="code">计算代码</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Form.Item
            label="封面图片"
            name="coverImage"
          >
            <Upload
              listType="picture-card"
              maxCount={1}
              beforeUpload={() => false}
            >
              <div>
                <PictureOutlined />
                <div style={{ marginTop: 8 }}>上传封面</div>
              </div>
            </Upload>
          </Form.Item>
        </>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card title="报告生成器">
        <Steps current={currentStep} style={{ marginBottom: '24px' }}>
          {steps.map(item => (
            <Step key={item.title} title={item.title} />
          ))}
        </Steps>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleGenerateReport}
        >
          <div style={{ minHeight: '400px' }}>
            {steps[currentStep].content}
          </div>

          <Divider />

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button
              disabled={currentStep === 0}
              onClick={() => setCurrentStep(currentStep - 1)}
            >
              上一步
            </Button>

            <Space>
              {currentStep < steps.length - 1 && (
                <Button
                  type="primary"
                  onClick={() => setCurrentStep(currentStep + 1)}
                >
                  下一步
                </Button>
              )}

              {currentStep === steps.length - 1 && (
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={() => form.submit()}
                >
                  生成报告
                </Button>
              )}
            </Space>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default ReportGenerator;
