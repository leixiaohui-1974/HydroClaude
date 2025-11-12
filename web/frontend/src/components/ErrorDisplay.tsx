/**
 * Error Display Component
 * 错误显示组件
 *
 * v1.5.0 Feature: UI/UX Enhancement - Enhanced Error Feedback
 */

import React from 'react';
import { Alert, Space, Button, Typography, Collapse } from 'antd';
import {
  ExclamationCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  QuestionCircleOutlined
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

/**
 * Error categories
 * 错误类别
 */
export enum ErrorCategory {
  NETWORK = 'network',
  VALIDATION = 'validation',
  SERVER = 'server',
  CLIENT = 'client',
  UNKNOWN = 'unknown'
}

/**
 * Error information interface
 * 错误信息接口
 */
export interface ErrorInfo {
  /**
   * Error category
   * 错误类别
   */
  category: ErrorCategory;

  /**
   * Error message (English)
   * 错误消息（英文）
   */
  message: string;

  /**
   * Error message (Chinese)
   * 错误消息（中文）
   */
  messageCN: string;

  /**
   * Detailed description
   * 详细描述
   */
  details?: string;

  /**
   * Suggested solutions
   * 建议的解决方案
   */
  suggestions?: string[];

  /**
   * Suggested solutions (Chinese)
   * 建议的解决方案（中文）
   */
  suggestionsCN?: string[];

  /**
   * Recovery action callback
   * 恢复操作回调
   */
  onRetry?: () => void;

  /**
   * Help link
   * 帮助链接
   */
  helpLink?: string;

  /**
   * Original error object
   * 原始错误对象
   */
  error?: Error;
}

interface ErrorDisplayProps {
  /**
   * Error information
   * 错误信息
   */
  errorInfo: ErrorInfo;

  /**
   * Show detailed information
   * 显示详细信息
   */
  showDetails?: boolean;

  /**
   * Close callback
   * 关闭回调
   */
  onClose?: () => void;

  /**
   * Custom style
   * 自定义样式
   */
  style?: React.CSSProperties;
}

/**
 * Get error type and icon
 * 获取错误类型和图标
 */
function getErrorTypeAndIcon(category: ErrorCategory): {
  type: 'error' | 'warning' | 'info';
  icon: React.ReactNode;
} {
  switch (category) {
    case ErrorCategory.NETWORK:
      return { type: 'warning', icon: <WarningOutlined /> };
    case ErrorCategory.VALIDATION:
      return { type: 'warning', icon: <InfoCircleOutlined /> };
    case ErrorCategory.SERVER:
      return { type: 'error', icon: <ExclamationCircleOutlined /> };
    case ErrorCategory.CLIENT:
      return { type: 'error', icon: <ExclamationCircleOutlined /> };
    default:
      return { type: 'error', icon: <QuestionCircleOutlined /> };
  }
}

/**
 * Error Display Component
 *
 * Provides user-friendly error messages with contextual help and recovery actions
 */
const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  errorInfo,
  showDetails = true,
  onClose,
  style
}) => {
  const { type, icon } = getErrorTypeAndIcon(errorInfo.category);

  // Build alert message
  const alertMessage = (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      <Text strong>
        {errorInfo.messageCN} / {errorInfo.message}
      </Text>

      {/* Suggestions */}
      {(errorInfo.suggestions || errorInfo.suggestionsCN) && (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            建议 Suggestions:
          </Text>
          <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
            {errorInfo.suggestionsCN?.map((suggestion, index) => (
              <li key={`cn-${index}`} style={{ fontSize: 13, color: '#666' }}>
                {suggestion}
                {errorInfo.suggestions?.[index] && (
                  <span style={{ color: '#999' }}> / {errorInfo.suggestions[index]}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action buttons */}
      <Space style={{ marginTop: 8 }}>
        {errorInfo.onRetry && (
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={errorInfo.onRetry}
          >
            重试 Retry
          </Button>
        )}
        {errorInfo.helpLink && (
          <Button
            size="small"
            icon={<QuestionCircleOutlined />}
            href={errorInfo.helpLink}
            target="_blank"
          >
            帮助 Help
          </Button>
        )}
      </Space>
    </Space>
  );

  return (
    <div style={style}>
      <Alert
        type={type}
        icon={icon}
        message={alertMessage}
        closable={!!onClose}
        onClose={onClose}
        showIcon
      />

      {/* Detailed error information (collapsible) */}
      {showDetails && (errorInfo.details || errorInfo.error) && (
        <Collapse
          ghost
          style={{ marginTop: 8 }}
          items={[
            {
              key: 'details',
              label: <Text type="secondary" style={{ fontSize: 12 }}>技术详情 Technical Details</Text>,
              children: (
                <div style={{ fontSize: 12, color: '#666' }}>
                  {errorInfo.details && (
                    <Paragraph style={{ marginBottom: 8 }}>
                      {errorInfo.details}
                    </Paragraph>
                  )}
                  {errorInfo.error && (
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 8,
                        borderRadius: 4,
                        fontSize: 11,
                        overflow: 'auto',
                        maxHeight: 200
                      }}
                    >
                      {errorInfo.error.stack || errorInfo.error.message}
                    </pre>
                  )}
                </div>
              )
            }
          ]}
        />
      )}
    </div>
  );
};

export default ErrorDisplay;

/**
 * Parse error to ErrorInfo
 * 解析错误为ErrorInfo
 */
export function parseError(error: unknown, context?: string): ErrorInfo {
  // Network errors
  if (error instanceof Error) {
    if (error.message.includes('fetch') || error.message.includes('network')) {
      return {
        category: ErrorCategory.NETWORK,
        message: 'Network connection failed',
        messageCN: '网络连接失败',
        details: error.message,
        suggestions: [
          'Check your internet connection',
          'Verify the server is running',
          'Try again in a few moments'
        ],
        suggestionsCN: [
          '检查网络连接',
          '验证服务器是否运行',
          '稍后重试'
        ],
        error
      };
    }

    // Validation errors
    if (error.message.includes('validation') || error.message.includes('invalid')) {
      return {
        category: ErrorCategory.VALIDATION,
        message: 'Input validation failed',
        messageCN: '输入验证失败',
        details: error.message,
        suggestions: [
          'Check input values are within valid range',
          'Ensure all required fields are filled',
          'Review parameter constraints'
        ],
        suggestionsCN: [
          '检查输入值是否在有效范围内',
          '确保填写所有必填字段',
          '查看参数约束'
        ],
        error
      };
    }

    // Server errors (5xx)
    if (error.message.includes('500') || error.message.includes('server error')) {
      return {
        category: ErrorCategory.SERVER,
        message: 'Server error occurred',
        messageCN: '服务器错误',
        details: error.message,
        suggestions: [
          'Wait a moment and try again',
          'Contact support if the issue persists',
          'Check server logs for details'
        ],
        suggestionsCN: [
          '稍等片刻后重试',
          '如果问题持续，请联系支持',
          '检查服务器日志了解详情'
        ],
        error
      };
    }

    // Client errors (4xx)
    if (error.message.includes('400') || error.message.includes('404')) {
      return {
        category: ErrorCategory.CLIENT,
        message: 'Request failed',
        messageCN: '请求失败',
        details: error.message,
        suggestions: [
          'Verify the requested resource exists',
          'Check request parameters',
          'Ensure proper authentication'
        ],
        suggestionsCN: [
          '验证请求的资源是否存在',
          '检查请求参数',
          '确保正确认证'
        ],
        error
      };
    }
  }

  // Unknown errors
  const errorMessage = error instanceof Error ? error.message : String(error);
  return {
    category: ErrorCategory.UNKNOWN,
    message: context ? `${context}: ${errorMessage}` : errorMessage,
    messageCN: context ? `${context}: ${errorMessage}` : errorMessage,
    suggestions: [
      'Try refreshing the page',
      'Clear browser cache and cookies',
      'Contact support with error details'
    ],
    suggestionsCN: [
      '尝试刷新页面',
      '清除浏览器缓存和Cookie',
      '联系支持并提供错误详情'
    ],
    error: error instanceof Error ? error : undefined
  };
}
