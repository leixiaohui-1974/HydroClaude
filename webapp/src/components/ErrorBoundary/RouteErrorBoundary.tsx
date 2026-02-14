import React from 'react';
import { useRouteError, isRouteErrorResponse, useNavigate } from 'react-router-dom';
import { Result, Button } from 'antd';
import { useTranslation } from 'react-i18next';

const RouteErrorBoundary: React.FC = () => {
  const error = useRouteError();
  const navigate = useNavigate();
  const { t } = useTranslation();

  if (isRouteErrorResponse(error) && error.status === 404) {
    return (
      <Result
        status="404"
        title="404"
        subTitle={t('errorBoundary.pageNotFound')}
        extra={
          <Button type="primary" onClick={() => navigate('/')}>
            {t('errorBoundary.backHome')}
          </Button>
        }
      />
    );
  }

  const errorMessage =
    error instanceof Error
      ? error.message
      : t('errorBoundary.unknownError');

  return (
    <Result
      status="error"
      title={t('errorBoundary.pageError')}
      subTitle={errorMessage}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          {t('errorBoundary.backHome')}
        </Button>
      }
    />
  );
};

export default RouteErrorBoundary;
