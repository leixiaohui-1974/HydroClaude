/**
 * Results Export Component
 * 仿真结果导出组件
 *
 * v1.5.0 Feature: Results Data Export
 */

import React, { useState, useMemo } from 'react';
import {
  Modal,
  Button,
  Space,
  Radio,
  Select,
  InputNumber,
  Switch,
  Statistic,
  Row,
  Col,
  Alert,
  Divider,
  Typography,
  message
} from 'antd';
import {
  DownloadOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import type { SimulationResultResponse } from '@/services/api';
import type {
  ExportFormat,
  ExportDataType,
  SimulationExportOptions
} from '@/types/simulation-export';
import {
  exportSimulationResults,
  getExportStatistics,
  validateExportOptions
} from '@/utils/simulationExport';
import { DEFAULT_EXPORT_OPTIONS } from '@/types/simulation-export';

const { Text, Title } = Typography;
const { Option } = Select;

interface ResultsExportProps {
  /**
   * Simulation result to export
   */
  result: SimulationResultResponse;

  /**
   * Modal visibility
   */
  visible: boolean;

  /**
   * Close modal callback
   */
  onClose: () => void;
}

/**
 * ResultsExport Component
 *
 * Provides UI for exporting simulation results in various formats
 */
const ResultsExport: React.FC<ResultsExportProps> = ({
  result,
  visible,
  onClose
}) => {
  // Export options state
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [dataType, setDataType] = useState<ExportDataType>('all');
  const [precision, setPrecision] = useState<number>(6);
  const [includeMetadata, setIncludeMetadata] = useState<boolean>(true);
  const [prettyPrint, setPrettyPrint] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);

  // Calculate export statistics
  const statistics = useMemo(() => {
    const options: Partial<SimulationExportOptions> = {
      format,
      dataType,
      precision,
      includeMetadata,
      prettyPrint
    };

    return getExportStatistics(result, options);
  }, [result, format, dataType, precision, includeMetadata, prettyPrint]);

  // Validate export options
  const validation = useMemo(() => {
    const options: Partial<SimulationExportOptions> = {
      format,
      dataType,
      precision
    };

    return validateExportOptions(result, options);
  }, [result, format, dataType, precision]);

  /**
   * Handle export
   */
  const handleExport = async () => {
    try {
      setExporting(true);

      const options: SimulationExportOptions = {
        format,
        dataType,
        precision,
        includeMetadata,
        prettyPrint,
        ...DEFAULT_EXPORT_OPTIONS
      };

      // Export
      exportSimulationResults(result, options);

      // Show success message
      message.success(`结果已导出为 ${format.toUpperCase()} 格式`);

      // Close modal after a short delay
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (error) {
      message.error(`导出失败: ${(error as Error).message}`);
      console.error('Export error:', error);
    } finally {
      setExporting(false);
    }
  };

  /**
   * Reset options to defaults
   */
  const handleReset = () => {
    setFormat('csv');
    setDataType('all');
    setPrecision(6);
    setIncludeMetadata(true);
    setPrettyPrint(false);
  };

  return (
    <Modal
      title={
        <Space>
          <DownloadOutlined />
          <span>导出仿真结果</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={700}
      footer={[
        <Button key="reset" onClick={handleReset}>
          重置选项
        </Button>,
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button
          key="export"
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleExport}
          loading={exporting}
          disabled={!validation.valid}
        >
          导出
        </Button>
      ]}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Export Format */}
        <div>
          <Title level={5}>导出格式</Title>
          <Radio.Group
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            buttonStyle="solid"
            size="large"
          >
            <Radio.Button value="csv">
              <Space>
                <FileTextOutlined />
                <span>CSV</span>
              </Space>
            </Radio.Button>
            <Radio.Button value="excel">
              <Space>
                <FileExcelOutlined />
                <span>Excel</span>
              </Space>
            </Radio.Button>
            <Radio.Button value="json">
              <Space>
                <DatabaseOutlined />
                <span>JSON</span>
              </Space>
            </Radio.Button>
          </Radio.Group>
        </div>

        <Divider style={{ margin: '12px 0' }} />

        {/* Data Type */}
        <div>
          <Title level={5}>数据类型</Title>
          <Select
            value={dataType}
            onChange={setDataType}
            style={{ width: '100%' }}
            size="large"
          >
            <Option value="all">
              <Space>
                <DatabaseOutlined />
                <span>全部数据（时间序列 + 空间剖面 + 指标）</span>
              </Space>
            </Option>
            <Option value="timeseries">
              <Space>
                <span>⏱️</span>
                <span>时间序列数据</span>
              </Space>
            </Option>
            <Option value="spatial">
              <Space>
                <span>📍</span>
                <span>空间剖面数据</span>
              </Space>
            </Option>
            <Option value="metrics">
              <Space>
                <InfoCircleOutlined />
                <span>仅指标数据</span>
              </Space>
            </Option>
          </Select>
        </div>

        <Divider style={{ margin: '12px 0' }} />

        {/* Export Options */}
        <div>
          <Title level={5}>导出选项</Title>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Precision */}
            <Row align="middle">
              <Col span={12}>
                <Text>数值精度（小数位数）:</Text>
              </Col>
              <Col span={12}>
                <InputNumber
                  min={0}
                  max={15}
                  value={precision}
                  onChange={(val) => setPrecision(val || 6)}
                  style={{ width: '100%' }}
                />
              </Col>
            </Row>

            {/* Include Metadata */}
            <Row align="middle">
              <Col span={12}>
                <Text>包含元数据:</Text>
              </Col>
              <Col span={12}>
                <Switch
                  checked={includeMetadata}
                  onChange={setIncludeMetadata}
                />
              </Col>
            </Row>

            {/* Pretty Print (JSON only) */}
            {format === 'json' && (
              <Row align="middle">
                <Col span={12}>
                  <Text>格式化输出 (JSON):</Text>
                </Col>
                <Col span={12}>
                  <Switch
                    checked={prettyPrint}
                    onChange={setPrettyPrint}
                  />
                </Col>
              </Row>
            )}
          </Space>
        </div>

        <Divider style={{ margin: '12px 0' }} />

        {/* Export Statistics */}
        <div>
          <Title level={5}>导出信息</Title>
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Statistic
                title="时间步数"
                value={statistics.timeStepsExported}
                suffix={`/ ${result.time.length}`}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="空间点数"
                value={statistics.spatialPointsExported}
                suffix={`/ ${result.x.length}`}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="数据点总数"
                value={statistics.totalDataPoints}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="估算文件大小"
                value={statistics.formattedFileSize}
                valueStyle={{
                  color: statistics.estimatedFileSize > 10 * 1024 * 1024 ? '#ff4d4f' : '#3f8600'
                }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="导出格式"
                value={format.toUpperCase()}
              />
            </Col>
          </Row>
        </div>

        {/* Validation Warnings */}
        {validation.warnings.length > 0 && (
          <Alert
            message="导出警告"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {validation.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            }
            type="warning"
            showIcon
          />
        )}

        {/* Validation Errors */}
        {validation.errors.length > 0 && (
          <Alert
            message="验证错误"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {validation.errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            }
            type="error"
            showIcon
          />
        )}

        {/* Format Info */}
        <Alert
          message="格式说明"
          description={
            format === 'csv'
              ? 'CSV格式将导出纯文本数据文件。如选择"全部数据"，将下载3个CSV文件（时间序列、空间剖面、指标）。'
              : format === 'excel'
              ? 'Excel格式将导出.xlsx文件，包含多个工作表（时间序列、空间剖面、指标、元数据）。'
              : 'JSON格式将导出完整的结构化数据，包含原始结果和处理后的数据，适合程序化处理。'
          }
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />
      </Space>
    </Modal>
  );
};

export default ResultsExport;
