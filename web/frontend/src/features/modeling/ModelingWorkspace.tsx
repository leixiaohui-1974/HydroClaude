/**
 * Modeling Workspace
 * 建模工作台主页面
 */

import React, { useState } from 'react';
import { Layout, Button, Space, message, Modal, Tooltip } from 'antd';
import {
  SaveOutlined,
  FolderOpenOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  UndoOutlined,
  RedoOutlined,
  AppstoreOutlined,
  LayoutOutlined
} from '@ant-design/icons';

import { useAppDispatch, useAppSelector } from '@/shared/hooks/redux';
import {
  createNewModel,
  undo,
  redo,
  toggleComponentPalette,
  togglePropertyPanel
} from './store/modelSlice';
import {
  selectCanUndo,
  selectCanRedo,
  selectShowComponentPalette,
  selectShowPropertyPanel,
  selectCurrentModel,
  selectIsModelEmpty
} from './store/selectors';

import ComponentPalette from './components/ComponentPalette';
import ModelCanvas from './components/ModelCanvas';
import PropertyPanel from './components/PropertyPanel';
import { ComponentTemplate } from './types/model.types';

import './ModelingWorkspace.css';

const { Header, Sider, Content } = Layout;

const ModelingWorkspace: React.FC = () => {
  const dispatch = useAppDispatch();

  // Redux状态
  const canUndo = useAppSelector(selectCanUndo);
  const canRedo = useAppSelector(selectCanRedo);
  const showPalette = useAppSelector(selectShowComponentPalette);
  const showProperty = useAppSelector(selectShowPropertyPanel);
  const currentModel = useAppSelector(selectCurrentModel);
  const isEmpty = useAppSelector(selectIsModelEmpty);

  // 本地状态
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);

  // 处理组件拖拽开始
  const handleComponentDragStart = (template: ComponentTemplate, event: React.DragEvent) => {
    // 可以在这里添加拖拽开始的视觉反馈
    console.log('Drag start:', template.name);
  };

  // 处理节点选择
  const handleNodeSelect = (nodeIds: string[]) => {
    setSelectedNodeIds(nodeIds);
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

  // 处理保存
  const handleSave = () => {
    if (!currentModel) {
      message.warning('没有可保存的模型');
      return;
    }

    // 保存为JSON文件
    const modelJson = JSON.stringify(currentModel, null, 2);
    const blob = new Blob([modelJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${currentModel.name || 'model'}.json`;
    link.click();
    URL.revokeObjectURL(url);

    message.success('模型已导出');
  };

  // 处理验证
  const handleValidate = () => {
    if (isEmpty) {
      message.warning('模型为空,无法验证');
      return;
    }

    // TODO: 实现完整的验证逻辑
    message.info('验证功能开发中...');
  };

  // 处理运行仿真
  const handleRun = () => {
    if (isEmpty) {
      message.warning('模型为空,无法运行');
      return;
    }

    // TODO: 转换模型为仿真配置并运行
    message.info('仿真功能开发中...');
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

          <Tooltip title="导入模型 (开发中)">
            <Button
              icon={<FolderOpenOutlined />}
              disabled
            >
              导入
            </Button>
          </Tooltip>

          <Tooltip title="导出模型">
            <Button
              icon={<SaveOutlined />}
              onClick={handleSave}
              disabled={isEmpty}
            >
              导出
            </Button>
          </Tooltip>

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
    </Layout>
  );
};

export default ModelingWorkspace;
