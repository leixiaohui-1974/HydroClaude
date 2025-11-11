/**
 * Model Import/Export Component
 * 模型导入/导出组件
 *
 * v1.5.0 Feature: Model I/O
 */

import React, { useState } from 'react';
import { Button, Space, message, Upload, Dropdown, Modal, Statistic, Row, Col, Alert } from 'antd';
import {
  DownloadOutlined,
  UploadOutlined,
  SaveOutlined,
  FileTextOutlined,
  TableOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import type { HydraulicModel } from '../types/model.types';
import {
  downloadModelJSON,
  downloadModelCSV,
  validateModelForExport,
  getExportStatistics
} from '../../../utils/modelExport';
import {
  importModelJSON,
  getImportFileInfo
} from '../../../utils/modelImport';
import type { IOError } from '../../../types/model-io';
import { STORAGE_KEYS } from '../../../types/model-io';

interface ModelIOProps {
  currentModel: HydraulicModel | null;
  onModelLoad?: (model: HydraulicModel) => void;
  onModelSave?: (model: HydraulicModel) => void;
  disabled?: boolean;
}

/**
 * ModelIO Component
 * Provides import/export functionality for hydraulic models
 */
const ModelIO: React.FC<ModelIOProps> = ({
  currentModel,
  onModelLoad,
  onModelSave,
  disabled = false
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);

  // ============= Export Handlers =============

  /**
   * Handle JSON export
   */
  const handleExportJSON = () => {
    if (!currentModel) {
      message.warning('没有可导出的模型');
      return;
    }

    try {
      setIsExporting(true);

      // Validate before export
      const validation = validateModelForExport(currentModel);
      if (!validation.valid) {
        Modal.error({
          title: '导出验证失败',
          content: (
            <div>
              <p>模型验证未通过，无法导出：</p>
              <ul>
                {validation.errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )
        });
        return;
      }

      // Show warnings if any
      if (validation.warnings.length > 0) {
        Modal.warning({
          title: '导出警告',
          content: (
            <div>
              <p>模型可以导出，但存在以下警告：</p>
              <ul>
                {validation.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
              <p>是否继续导出？</p>
            </div>
          ),
          onOk: () => {
            downloadModelJSON(currentModel, {
              prettyPrint: true,
              includeMetadata: true,
              includeThumbnail: true
            });
            message.success('模型已导出为JSON格式');
          }
        });
      } else {
        // Direct export
        downloadModelJSON(currentModel, {
          prettyPrint: true,
          includeMetadata: true,
          includeThumbnail: true
        });
        message.success('模型已导出为JSON格式');
      }
    } catch (error) {
      message.error(`导出失败: ${(error as Error).message}`);
    } finally {
      setIsExporting(false);
    }
  };

  /**
   * Handle CSV export
   */
  const handleExportCSV = () => {
    if (!currentModel) {
      message.warning('没有可导出的模型');
      return;
    }

    try {
      setIsExporting(true);

      downloadModelCSV(currentModel);
      message.success('模型已导出为CSV格式（节点和边）');
    } catch (error) {
      message.error(`CSV导出失败: ${(error as Error).message}`);
    } finally {
      setIsExporting(false);
    }
  };

  /**
   * Show export statistics modal
   */
  const handleShowExportInfo = () => {
    if (!currentModel) {
      message.warning('没有可导出的模型');
      return;
    }

    setShowExportModal(true);
  };

  // ============= Import Handlers =============

  /**
   * Handle file import
   */
  const handleImport = async (file: File) => {
    try {
      setIsImporting(true);

      // Get file info
      const fileInfo = await getImportFileInfo(file);
      console.log('Importing file:', fileInfo);

      // Import model
      const model = await importModelJSON(file);

      // Notify parent component
      if (onModelLoad) {
        onModelLoad(model);
      }

      message.success(`已成功导入模型: ${model.name}`);
    } catch (error) {
      const ioError = error as IOError;

      Modal.error({
        title: '导入失败',
        content: (
          <div>
            <p><strong>错误类型:</strong> {ioError.type || 'unknown'}</p>
            <p><strong>错误消息:</strong> {ioError.message}</p>
            {ioError.details && (
              <p><strong>详细信息:</strong> {ioError.details}</p>
            )}
          </div>
        )
      });
    } finally {
      setIsImporting(false);
    }

    // Prevent auto upload
    return false;
  };

  // ============= Local Storage Handlers =============

  /**
   * Save model to localStorage
   */
  const handleSaveLocal = () => {
    if (!currentModel) {
      message.warning('没有可保存的模型');
      return;
    }

    try {
      // Update timestamps
      const modelToSave: HydraulicModel = {
        ...currentModel,
        updated_at: new Date().toISOString()
      };

      // Get existing models from localStorage
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.MODELS) || '[]');

      // Check if model already exists
      const existingIndex = saved.findIndex((m: HydraulicModel) => m.id === modelToSave.id);

      if (existingIndex >= 0) {
        // Update existing model
        saved[existingIndex] = modelToSave;
        message.success('模型已更新');
      } else {
        // Add new model
        saved.push(modelToSave);
        message.success('模型已保存');
      }

      // Save back to localStorage
      localStorage.setItem(STORAGE_KEYS.MODELS, JSON.stringify(saved));

      // Update last saved time
      setLastSaved(new Date());

      // Notify parent component
      if (onModelSave) {
        onModelSave(modelToSave);
      }

      // Add to recent models
      addToRecent(modelToSave);
    } catch (error) {
      if ((error as any).name === 'QuotaExceededError') {
        message.error('存储空间不足，请删除一些旧模型后重试');
      } else {
        message.error(`保存失败: ${(error as Error).message}`);
      }
    }
  };

  /**
   * Add model to recent list
   */
  const addToRecent = (model: HydraulicModel) => {
    try {
      const recent = JSON.parse(localStorage.getItem(STORAGE_KEYS.RECENT) || '[]');

      // Remove if already exists
      const filtered = recent.filter((r: any) => r.id !== model.id);

      // Add to front
      filtered.unshift({
        id: model.id,
        name: model.name,
        accessedAt: new Date().toISOString()
      });

      // Keep only last 10
      const trimmed = filtered.slice(0, 10);

      localStorage.setItem(STORAGE_KEYS.RECENT, JSON.stringify(trimmed));
    } catch (error) {
      console.error('Failed to update recent models:', error);
    }
  };

  // ============= Export Menu =============

  const exportMenuItems: MenuProps['items'] = [
    {
      key: 'json',
      label: 'JSON格式',
      icon: <FileTextOutlined />,
      onClick: handleExportJSON
    },
    {
      key: 'csv',
      label: 'CSV格式',
      icon: <TableOutlined />,
      onClick: handleExportCSV
    },
    {
      type: 'divider'
    },
    {
      key: 'info',
      label: '导出信息',
      icon: <ExclamationCircleOutlined />,
      onClick: handleShowExportInfo
    }
  ];

  // ============= Export Info Modal =============

  const renderExportModal = () => {
    if (!currentModel) return null;

    const stats = getExportStatistics(currentModel);

    return (
      <Modal
        title="导出信息"
        open={showExportModal}
        onCancel={() => setShowExportModal(false)}
        footer={[
          <Button key="close" onClick={() => setShowExportModal(false)}>
            关闭
          </Button>,
          <Button key="export-json" type="primary" icon={<DownloadOutlined />} onClick={() => {
            setShowExportModal(false);
            handleExportJSON();
          }}>
            导出JSON
          </Button>
        ]}
      >
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic title="节点数量" value={stats.nodeCount} />
          </Col>
          <Col span={12}>
            <Statistic title="连接数量" value={stats.edgeCount} />
          </Col>
          <Col span={12}>
            <Statistic
              title="JSON大小"
              value={(stats.estimatedJsonSize / 1024).toFixed(1)}
              suffix="KB"
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="CSV大小"
              value={(stats.estimatedCsvSize / 1024).toFixed(1)}
              suffix="KB"
            />
          </Col>
        </Row>

        {!stats.isValid && (
          <Alert
            message="验证失败"
            description="模型包含错误，可能无法正常导出"
            type="error"
            style={{ marginTop: 16 }}
          />
        )}

        {stats.hasMetadata && (
          <Alert
            message="包含元数据"
            description="模型包含额外的元数据信息"
            type="info"
            style={{ marginTop: 16 }}
          />
        )}
      </Modal>
    );
  };

  // ============= Render =============

  return (
    <>
      <Space size="small">
        {/* Save to localStorage */}
        <Button
          icon={<SaveOutlined />}
          onClick={handleSaveLocal}
          disabled={disabled || !currentModel}
          loading={false}
          title="保存模型到本地存储"
        >
          保存模型
        </Button>

        {/* Export dropdown */}
        <Dropdown
          menu={{ items: exportMenuItems }}
          placement="bottomRight"
          disabled={disabled || !currentModel}
        >
          <Button
            icon={<DownloadOutlined />}
            loading={isExporting}
            disabled={disabled || !currentModel}
          >
            导出
          </Button>
        </Dropdown>

        {/* Import */}
        <Upload
          beforeUpload={handleImport}
          accept=".json,.hydro.json"
          showUploadList={false}
          disabled={disabled}
        >
          <Button
            icon={<UploadOutlined />}
            loading={isImporting}
            disabled={disabled}
          >
            导入模型
          </Button>
        </Upload>
      </Space>

      {/* Last saved indicator */}
      {lastSaved && (
        <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
          最后保存: {lastSaved.toLocaleTimeString()}
        </div>
      )}

      {/* Export info modal */}
      {renderExportModal()}
    </>
  );
};

export default ModelIO;
