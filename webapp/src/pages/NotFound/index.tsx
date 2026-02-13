import React from 'react';
import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <Result
      status="404"
      title="404"
      subTitle={t('notFound.subtitle')}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          {t('notFound.backHome')}
        </Button>
      }
    />
  );
};

export default NotFoundPage;
