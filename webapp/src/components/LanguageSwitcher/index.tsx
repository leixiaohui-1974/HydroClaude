import React from 'react';
import { Select } from 'antd';
import { useTranslation } from 'react-i18next';
import { GlobalOutlined } from '@ant-design/icons';

const LanguageSwitcher: React.FC = () => {
  const { i18n, t } = useTranslation();
  return (
    <Select
      value={i18n.language.startsWith('zh') ? 'zh' : 'en'}
      onChange={(lang) => i18n.changeLanguage(lang)}
      options={[
        { value: 'zh', label: '中文' },
        { value: 'en', label: 'English' },
      ]}
      style={{ width: 100 }}
      suffixIcon={<GlobalOutlined />}
      variant="borderless"
      aria-label={t('layout.switchLanguage')}
    />
  );
};

export default LanguageSwitcher;
