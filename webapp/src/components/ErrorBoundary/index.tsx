import React from 'react';
import { Result, Button, Typography } from 'antd';
import i18n from '@/i18n';

const { Paragraph, Text } = Typography;

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  handleBackHome = (): void => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const isDev = import.meta.env.DEV;

      return (
        <div style={{ padding: '48px 24px' }}>
          <Result
            status="error"
            title={i18n.t('errorBoundary.pageError')}
            subTitle={i18n.t('errorBoundary.errorDescription')}
            extra={[
              <Button type="primary" key="retry" onClick={this.handleRetry}>
                {i18n.t('errorBoundary.retry')}
              </Button>,
              <Button key="home" onClick={this.handleBackHome}>
                {i18n.t('errorBoundary.backHome')}
              </Button>,
            ]}
          >
            {isDev && this.state.error && (
              <div style={{ textAlign: 'left' }}>
                <Paragraph>
                  <Text strong style={{ fontSize: 16 }}>
                    {i18n.t('errorBoundary.errorInfo')}
                  </Text>
                </Paragraph>
                <Paragraph>
                  <Text type="danger">{this.state.error.message}</Text>
                </Paragraph>
                {this.state.error.stack && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ cursor: 'pointer', color: '#1677ff' }}>
                      {i18n.t('errorBoundary.viewErrorStack')}
                    </summary>
                    <pre
                      style={{
                        marginTop: 8,
                        padding: 12,
                        background: '#f5f5f5',
                        borderRadius: 4,
                        overflow: 'auto',
                        fontSize: 12,
                        lineHeight: 1.6,
                        maxHeight: 300,
                      }}
                    >
                      {this.state.error.stack}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </Result>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
