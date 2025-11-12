/**
 * Quick Actions Toolbar Component
 * 快速操作工具栏组件
 *
 * v1.5.0 Feature: UI/UX Enhancement
 */

import React, { useState } from 'react';
import {
  FloatButton,
  Tooltip,
  Space,
  Modal
} from 'antd';
import {
  QuestionCircleOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import { formatShortcut, getModifierKeyName } from '@/hooks/useKeyboardShortcuts';

interface QuickAction {
  key: string;
  icon: React.ReactNode;
  label: string;
  labelCN: string;
  shortcut?: string;
  onClick: () => void;
  disabled?: boolean;
}

interface QuickActionsToolbarProps {
  /**
   * Available actions
   * 可用操作
   */
  actions?: QuickAction[];

  /**
   * Show keyboard shortcuts help
   * 显示快捷键帮助
   */
  onShowHelp?: () => void;
}

/**
 * Quick Actions Toolbar Component
 *
 * Floating action buttons for quick access to common operations
 */
const QuickActionsToolbar: React.FC<QuickActionsToolbarProps> = ({
  actions = [],
  onShowHelp
}) => {
  const [helpModalVisible, setHelpModalVisible] = useState(false);

  // Show help modal
  const handleShowHelp = () => {
    if (onShowHelp) {
      onShowHelp();
    } else {
      setHelpModalVisible(true);
    }
  };

  // Render action buttons
  const renderActionButtons = () => {
    return actions.map(action => (
      <Tooltip
        key={action.key}
        title={
          <div>
            <div>{action.labelCN} {action.label}</div>
            {action.shortcut && (
              <div style={{ fontSize: 11, opacity: 0.8 }}>
                {formatShortcut(action.shortcut)}
              </div>
            )}
          </div>
        }
        placement="left"
      >
        <FloatButton
          icon={action.icon}
          onClick={action.onClick}
          disabled={action.disabled}
        />
      </Tooltip>
    ));
  };

  // Default keyboard shortcuts help content
  const renderHelpContent = () => {
    const modKey = getModifierKeyName();

    const shortcuts = [
      { key: `${modKey}+S`, desc: '保存模型', descEN: 'Save Model' },
      { key: `${modKey}+E`, desc: '导出结果', descEN: 'Export Results' },
      { key: `${modKey}+N`, desc: '新建模型', descEN: 'New Model' },
      { key: `${modKey}+O`, desc: '打开模型', descEN: 'Open Model' },
      { key: `${modKey}+Z`, desc: '撤销', descEN: 'Undo' },
      { key: `${modKey}+Y`, desc: '重做', descEN: 'Redo' },
      { key: 'Space', desc: '播放/暂停', descEN: 'Play/Pause' },
      { key: 'Esc', desc: '关闭弹窗', descEN: 'Close Modal' },
      { key: 'F1', desc: '帮助', descEN: 'Help' }
    ];

    return (
      <div>
        <p style={{ marginBottom: 16, color: '#666' }}>
          使用键盘快捷键可以更快地执行常用操作。
        </p>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {shortcuts.map((shortcut, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 12px',
                background: '#f5f5f5',
                borderRadius: 4
              }}
            >
              <span>
                {shortcut.desc} <span style={{ color: '#999', fontSize: 12 }}>({shortcut.descEN})</span>
              </span>
              <kbd
                style={{
                  padding: '2px 8px',
                  background: 'white',
                  border: '1px solid #d9d9d9',
                  borderRadius: 3,
                  fontSize: 12,
                  fontFamily: 'monospace'
                }}
              >
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </Space>
      </div>
    );
  };

  return (
    <>
      {/* Floating Action Buttons Group */}
      <FloatButton.Group
        trigger="hover"
        type="primary"
        style={{ right: 24, bottom: 24 }}
        icon={<ThunderboltOutlined />}
        tooltip={<div>快速操作 Quick Actions</div>}
      >
        {/* Help Button */}
        <Tooltip title={<div>键盘快捷键 Keyboard Shortcuts (F1)</div>} placement="left">
          <FloatButton
            icon={<QuestionCircleOutlined />}
            onClick={handleShowHelp}
          />
        </Tooltip>

        {/* Custom Action Buttons */}
        {renderActionButtons()}
      </FloatButton.Group>

      {/* Keyboard Shortcuts Help Modal */}
      <Modal
        title="键盘快捷键 Keyboard Shortcuts"
        open={helpModalVisible}
        onCancel={() => setHelpModalVisible(false)}
        footer={null}
        width={500}
      >
        {renderHelpContent()}
      </Modal>
    </>
  );
};

export default QuickActionsToolbar;
