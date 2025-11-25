/**
 * Modeling Workspace
 * 建模工作台主页面
 */

import React, { useState } from 'react';
import { Layout, Button, Space, message, Modal, Tooltip } from 'antd';
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  UndoOutlined,
  RedoOutlined,
  AppstoreOutlined,
  LayoutOutlined,
  DatabaseOutlined,
  BookOutlined
} from '@ant-design/icons';

import { useKeyboardShortcuts, DEFAULT_SHORTCUTS } from '@/hooks/useKeyboardShortcuts';

import { useAppDispatch, useAppSelector } from '@/shared/hooks/redux';
import {
  createNewModel,
  undo,
  redo,
  toggleComponentPalette,
  togglePropertyPanel,
  startValidation,
  completeValidation,
  importModel
} from './store/modelSlice';
import {
  selectCanUndo,
  selectCanRedo,
  selectShowComponentPalette,
  selectShowPropertyPanel,
  selectCurrentModel,
  selectIsModelEmpty
} from './store/selectors';

// 导入验证和转换工具
import { validateModel } from './utils/validator';
import {
  convertModelToSimulationConfig,
  canConvertToSimulation,
  generateConfigSummary
} from './utils/converter';
import { createSimulation } from '@/services/simulation-api';

import ComponentPalette from './components/ComponentPalette';
import ModelCanvas from './components/ModelCanvas';
import PropertyPanel from './components/PropertyPanel';
import ModelIO from './components/ModelIO';
import ModelLibrary from './components/ModelLibrary';
import TemplateGallery from './components/TemplateGallery';
import { ConfigAnalysis } from '@/features/analysis';
import { ComponentTemplate, HydraulicModel } from './types/model.types';

import './ModelingWorkspace.css';

const { Header, Sider, Content } = Layout;

const ModelingWorkspace: React.FC = () => {
  const dispatch = useAppDispatch();

  // Local state for model library modal
  const [showModelLibrary, setShowModelLibrary] = useState(false);
  const [showTemplateGallery, setShowTemplateGallery] = useState(false);
  const [showConfigAnalysis, setShowConfigAnalysis] = useState(false);
  const [simulationConfig, setSimulationConfig] = useState<any>(null);

  // Redux状态
  const canUndo = useAppSelector(selectCanUndo);
  const canRedo = useAppSelector(selectCanRedo);
  const showPalette = useAppSelector(selectShowComponentPalette);
  const showProperty = useAppSelector(selectShowPropertyPanel);
  const currentModel = useAppSelector(selectCurrentModel);
  const isEmpty = useAppSelector(selectIsModelEmpty);

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: DEFAULT_SHORTCUTS.NEW,
      handler: () => handleNewModel(),
      description: 'New model'
    },
    {
      key: DEFAULT_SHORTCUTS.OPEN,
      handler: () => handleOpenLibrary(),
      description: 'Open model library'
    },
    {
      key: DEFAULT_SHORTCUTS.UNDO,
      handler: () => {
        if (canUndo) handleUndo();
      },
      description: 'Undo',
      enabled: canUndo
    },
    {
      key: DEFAULT_SHORTCUTS.REDO,
      handler: () => {
        if (canRedo) handleRedo();
      },
      description: 'Redo',
      enabled: canRedo
    }
  ]);

  // 处理组件拖拽开始
  const handleComponentDragStart = (template: ComponentTemplate, _event: React.DragEvent) => {
    // 可以在这里添加拖拽开始的视觉反馈
    console.log('Drag start:', template.name);
  };

  // 处理节点选择
  const handleNodeSelect = (_nodeIds: string[]) => {
    // 未来可以在这里处理节点选择逻辑
  };

  // 处理撤销
  const handleUndo = () => {
    dispatch(undo());
    message.success('已撤销');
  };

  // 处理重做
  const handleRedo = () => {
    dispatch(redo());
    message.success('已重做');
  };

  // 处理新建模型
  const handleNewModel = () => {
    if (!isEmpty) {
      Modal.confirm({
        title: '确认新建模型',
        content: '当前模型尚未保存,新建将丢失当前更改,是否继续?',
        onOk: () => {
          dispatch(createNewModel({}));
          message.success('已创建新模型');
        }
      });
    } else {
      dispatch(createNewModel({}));
      message.success('已创建新模型');
    }
  };

  // 处理从模型库加载模型
  const handleLoadModelFromLibrary = (model: HydraulicModel) => {
    if (!isEmpty) {
      Modal.confirm({
        title: '确认加载模型',
        content: '加载新模型将覆盖当前模型，是否继续？',
        onOk: () => {
          dispatch(importModel({ model, replace: true }));
        }
      });
    } else {
      dispatch(importModel({ model, replace: true }));
    }
  };

  // 处理打开模型库
  const handleOpenLibrary = () => {
    setShowModelLibrary(true);
  };

  // 处理打开模板画廊
  const handleOpenTemplates = () => {
    setShowTemplateGallery(true);
  };

  // 处理从模板加载模型
  const handleLoadTemplate = (model: HydraulicModel) => {
    if (!isEmpty) {
      Modal.confirm({
        title: '确认应用模板',
        content: '应用模板将覆盖当前模型，是否继续？',
        onOk: () => {
          dispatch(importModel({ model, replace: true }));
          setShowTemplateGallery(false);
          message.success('模板已应用');
        }
      });
    } else {
      dispatch(importModel({ model, replace: true }));
      setShowTemplateGallery(false);
      message.success('模板已应用');
    }
  };

  // 处理验证
  const handleValidate = () => {
    if (isEmpty || !currentModel) {
      message.warning('模型为空,无法验证');
      return;
    }

    // 开始验证
    dispatch(startValidation());
    message.loading({ content: '正在验证模型...', key: 'validation' });

    try {
      // 执行验证
      const validationResult = validateModel(currentModel);

      // 更新验证结果
      dispatch(completeValidation(validationResult));

      // 根据验证结果显示消息
      if (validationResult.valid) {
        message.success({ content: '模型验证通过!', key: 'validation', duration: 2 });
      } else {
        const errorCount = validationResult.errors.filter(e => e.severity === 'error').length;
        const warningCount = validationResult.errors.filter(e => e.severity === 'warning').length;

        let content = '模型验证失败: ';
        if (errorCount > 0) content += `${errorCount} 个错误`;
        if (warningCount > 0) content += `${errorCount > 0 ? ', ' : ''}${warningCount} 个警告`;

        message.error({ content, key: 'validation', duration: 3 });

        // 显示详细错误信息
        Modal.error({
          title: '验证结果',
          width: 600,
          content: (
            <div>
              {validationResult.errors.map((error, index) => (
                <div key={index} style={{ marginBottom: 8 }}>
                  <strong>[{error.severity.toUpperCase()}]</strong> {error.message}
                  {error.suggestion && (
                    <div style={{ color: '#666', fontSize: '12px', marginTop: 4 }}>
                      💡 {error.suggestion}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )
        });
      }
    } catch (error) {
      console.error('Validation error:', error);
      message.error({ content: '验证过程中发生错误', key: 'validation' });
    }
  };

  // 处理运行仿真
  const handleRun = async () => {
    if (isEmpty || !currentModel) {
      message.warning('模型为空,无法运行');
      return;
    }

    // 检查模型是否可以转换为仿真配置
    const { canConvert, reason } = canConvertToSimulation(currentModel);
    if (!canConvert) {
      message.error(reason || '模型无法转换为仿真配置');
      return;
    }

    // 转换模型为仿真配置
    const simulationRequest = convertModelToSimulationConfig(currentModel);
    if (!simulationRequest) {
      message.error('转换模型失败,请检查模型配置');
      return;
    }

    // 显示配置摘要并确认
    const summary = generateConfigSummary(simulationRequest);
    Modal.confirm({
      title: '确认运行仿真',
      width: 600,
      content: (
        <div>
          <p>将使用以下配置运行仿真:</p>
          <pre style={{
            backgroundColor: '#f5f5f5',
            padding: '12px',
            borderRadius: '4px',
            fontSize: '12px',
            maxHeight: '400px',
            overflow: 'auto'
          }}>
            {summary}
          </pre>
        </div>
      ),
      onOk: async () => {
        const hideLoading = message.loading('正在创建仿真任务...', 0);

        try {
          // 调用API创建仿真
          const simulation = await createSimulation(simulationRequest);

          hideLoading();
          message.success('仿真任务创建成功!');

          // 显示成功信息
          Modal.success({
            title: '仿真任务已创建',
            content: (
              <div>
                <p><strong>任务ID:</strong> {simulation.task_id}</p>
                <p><strong>状态:</strong> {simulation.status}</p>
                <p>请切换到"仿真管理"标签页查看运行状态和结果。</p>
              </div>
            )
          });
        } catch (error: any) {
          hideLoading();
          console.error('Simulation creation error:', error);

          const errorMessage = error.response?.data?.detail || error.message || '创建仿真任务失败';
          Modal.error({
            title: '创建仿真失败',
            content: errorMessage
          });
        }
      }
    });
  };

  return (
    <Layout className="modeling-workspace">
      {/* 顶部工具栏 */}
      <Header className="workspace-header">
        <div className="header-left">
          <h2>建模工作台</h2>
          {currentModel && (
            <span className="model-name">- {currentModel.name}</span>
          )}
        </div>

        <Space className="header-actions" size="middle">
          {/* 文件操作 */}
          <Tooltip title="新建模型">
            <Button
              icon={<AppstoreOutlined />}
              onClick={handleNewModel}
            >
              新建
            </Button>
          </Tooltip>

          <Tooltip title="打开模型库">
            <Button
              icon={<DatabaseOutlined />}
              onClick={handleOpenLibrary}
            >
              模型库
            </Button>
          </Tooltip>

          <Tooltip title="模板画廊">
            <Button
              icon={<BookOutlined />}
              onClick={handleOpenTemplates}
            >
              模板
            </Button>
          </Tooltip>

          {/* ModelIO Component - provides save/import/export */}
          <ModelIO
            currentModel={currentModel}
            onModelLoad={handleLoadModelFromLibrary}
            disabled={false}
          />

          {/* 分隔线 */}
          <div className="header-divider" />

          {/* 编辑操作 */}
          <Tooltip title="撤销 (Ctrl+Z)">
            <Button
              icon={<UndoOutlined />}
              onClick={handleUndo}
              disabled={!canUndo}
            />
          </Tooltip>

          <Tooltip title="重做 (Ctrl+Y)">
            <Button
              icon={<RedoOutlined />}
              onClick={handleRedo}
              disabled={!canRedo}
            />
          </Tooltip>

          <div className="header-divider" />

          {/* 视图切换 */}
          <Tooltip title="切换组件面板">
            <Button
              icon={<AppstoreOutlined />}
              type={showPalette ? 'primary' : 'default'}
              onClick={() => dispatch(toggleComponentPalette())}
            >
              组件
            </Button>
          </Tooltip>

          <Tooltip title="切换属性面板">
            <Button
              icon={<LayoutOutlined />}
              type={showProperty ? 'primary' : 'default'}
              onClick={() => dispatch(togglePropertyPanel())}
            >
              属性
            </Button>
          </Tooltip>

          <div className="header-divider" />

          {/* 模型操作 */}
          <Tooltip title="验证模型">
            <Button
              icon={<CheckCircleOutlined />}
              onClick={handleValidate}
              disabled={isEmpty}
            >
              验证
            </Button>
          </Tooltip>

          <Tooltip title="运行仿真">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleRun}
              disabled={isEmpty}
            >
              运行仿真
            </Button>
          </Tooltip>
        </Space>
      </Header>

      {/* 主工作区 */}
      <Layout className="workspace-body">
        {/* 左侧组件面板 */}
        {showPalette && (
          <Sider
            width={260}
            className="workspace-sider workspace-sider-left"
            theme="light"
          >
            <ComponentPalette onComponentDragStart={handleComponentDragStart} />
          </Sider>
        )}

        {/* 中间画布区域 */}
        <Content className="workspace-content">
          <ModelCanvas onNodeSelect={handleNodeSelect} />
        </Content>

        {/* 右侧属性面板 */}
        {showProperty && (
          <Sider
            width={320}
            className="workspace-sider workspace-sider-right"
            theme="light"
          >
            <PropertyPanel />
          </Sider>
        )}
      </Layout>

      {/* Model Library Modal */}
      <ModelLibrary
        visible={showModelLibrary}
        onClose={() => setShowModelLibrary(false)}
        onLoadModel={handleLoadModelFromLibrary}
        currentModelId={currentModel?.id}
      />

      {/* Template Gallery Modal */}
      <TemplateGallery
        visible={showTemplateGallery}
        onClose={() => setShowTemplateGallery(false)}
        onSelectTemplate={handleLoadTemplate}
      />
    </Layout>
  );
};

export default ModelingWorkspace;
