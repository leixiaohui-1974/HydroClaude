import React, { useState, useCallback } from 'react';
import { Card, Typography, Form, Input, Button, Space, Switch, Select, message } from 'antd';
import { SettingOutlined, LockOutlined, GlobalOutlined, BellOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '@/services/api';

const { Title, Paragraph } = Typography;

const NOTIFICATION_STORAGE_KEY = 'hydroclaude-notification-settings';

interface NotificationSettings {
  notifyComplete: boolean;
  notifyFailed: boolean;
  notifyEmail: boolean;
}

const DEFAULT_NOTIFICATIONS: NotificationSettings = {
  notifyComplete: true,
  notifyFailed: true,
  notifyEmail: false,
};

function loadNotificationSettings(): NotificationSettings {
  try {
    const raw = localStorage.getItem(NOTIFICATION_STORAGE_KEY);
    if (raw) return { ...DEFAULT_NOTIFICATIONS, ...JSON.parse(raw) };
  } catch { /* ignore parse errors */ }
  return { ...DEFAULT_NOTIFICATIONS };
}

const SettingsPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [passwordForm] = Form.useForm();
  const [changingPassword, setChangingPassword] = useState(false);
  const [notifications, setNotifications] = useState<NotificationSettings>(loadNotificationSettings);

  const saveNotifications = useCallback((updated: NotificationSettings) => {
    setNotifications(updated);
    localStorage.setItem(NOTIFICATION_STORAGE_KEY, JSON.stringify(updated));
  }, []);

  const handleChangePassword = async (values: any) => {
    setChangingPassword(true);
    try {
      await api.post('/auth/change-password', {
        current_password: values.currentPassword,
        new_password: values.newPassword,
      });
      message.success(t('settings.passwordChanged', 'Password changed successfully'));
      passwordForm.resetFields();
    } catch {
      message.error(t('settings.passwordChangeFailed', 'Failed to change password'));
    } finally {
      setChangingPassword(false);
    }
  };

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('language', lang);
    message.success(t('settings.languageChanged', 'Language changed'));
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Title level={3}>
        <SettingOutlined style={{ marginRight: 8 }} />
        {t('settings.title', 'Settings')}
      </Title>

      {/* Language Settings */}
      <Card title={<><GlobalOutlined /> {t('settings.language', 'Language')}</>} style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Paragraph>{t('settings.languageDesc', 'Choose your preferred language')}</Paragraph>
          <Select
            value={i18n.language?.startsWith('zh') ? 'zh' : 'en'}
            onChange={handleLanguageChange}
            style={{ width: 200 }}
            options={[
              { label: 'English', value: 'en' },
              { label: '中文', value: 'zh' },
            ]}
          />
        </Space>
      </Card>

      {/* Notification Settings */}
      <Card title={<><BellOutlined /> {t('settings.notifications', 'Notifications')}</>} style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Switch
              checked={notifications.notifyComplete}
              onChange={(v) => saveNotifications({ ...notifications, notifyComplete: v })}
            />
            <span>{t('settings.notifyComplete', 'Notify when simulation completes')}</span>
          </Space>
          <Space>
            <Switch
              checked={notifications.notifyFailed}
              onChange={(v) => saveNotifications({ ...notifications, notifyFailed: v })}
            />
            <span>{t('settings.notifyFailed', 'Notify when simulation fails')}</span>
          </Space>
          <Space>
            <Switch
              checked={notifications.notifyEmail}
              onChange={(v) => saveNotifications({ ...notifications, notifyEmail: v })}
            />
            <span>{t('settings.notifyEmail', 'Send email notifications')}</span>
          </Space>
        </Space>
      </Card>

      {/* Change Password */}
      <Card title={<><LockOutlined /> {t('settings.changePassword', 'Change Password')}</>}>
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={handleChangePassword}
        >
          <Form.Item
            label={t('settings.currentPassword', 'Current Password')}
            name="currentPassword"
            rules={[{ required: true, message: t('settings.currentPasswordRequired', 'Please enter current password') }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            label={t('settings.newPassword', 'New Password')}
            name="newPassword"
            rules={[
              { required: true, message: t('settings.newPasswordRequired', 'Please enter new password') },
              { min: 8, message: t('settings.passwordMinLength', 'Password must be at least 8 characters') },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            label={t('settings.confirmNewPassword', 'Confirm New Password')}
            name="confirmPassword"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: t('registerPage.confirmRequired') },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error(t('registerPage.passwordMismatch')));
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={changingPassword} icon={<LockOutlined />}>
              {t('settings.changePasswordBtn', 'Change Password')}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default SettingsPage;
