import React, { useState } from 'react';
import { Card, Typography, Form, Input, Button, Avatar, Space, Descriptions, message } from 'antd';
import { UserOutlined, MailOutlined, SaveOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import useAuthStore from '@/stores/authStore';
import api from '@/services/api';

const { Title, Paragraph } = Typography;

const ProfilePage: React.FC = () => {
  const { t } = useTranslation();
  const { user, setUser } = useAuthStore();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      const updated: any = await api.put('/users/me', values);
      setUser(updated);
      message.success(t('profile.updateSuccess', 'Profile updated successfully'));
    } catch {
      message.error(t('profile.updateFailed', 'Failed to update profile'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Title level={3}>
        <UserOutlined style={{ marginRight: 8 }} />
        {t('profile.title', 'User Profile')}
      </Title>

      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" align="center" style={{ width: '100%', padding: '24px 0' }}>
          <Avatar
            size={96}
            src={user?.avatar_url}
            icon={!user?.avatar_url ? <UserOutlined /> : undefined}
            style={{ backgroundColor: '#1890ff' }}
          />
          <Title level={4} style={{ margin: '8px 0 0' }}>{user?.username}</Title>
          <Paragraph type="secondary">{user?.email}</Paragraph>
        </Space>

        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label={t('profile.userId', 'User ID')}>{user?.id}</Descriptions.Item>
          <Descriptions.Item label={t('profile.username', 'Username')}>{user?.username}</Descriptions.Item>
          <Descriptions.Item label={t('profile.email', 'Email')}>{user?.email}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={t('profile.editProfile', 'Edit Profile')}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{ email: user?.email, bio: '', avatar_url: user?.avatar_url || '' }}
          onFinish={handleSave}
        >
          <Form.Item
            label={t('profile.email', 'Email')}
            name="email"
            rules={[
              { type: 'email', message: t('registerPage.emailInvalid') },
            ]}
          >
            <Input prefix={<MailOutlined />} />
          </Form.Item>
          <Form.Item
            label={t('profile.avatarUrl', 'Avatar URL')}
            name="avatar_url"
          >
            <Input placeholder="https://example.com/avatar.png" />
          </Form.Item>
          <Form.Item
            label={t('profile.bio', 'Bio')}
            name="bio"
          >
            <Input.TextArea rows={3} placeholder={t('profile.bioPlaceholder', 'Tell us about yourself...')} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />}>
              {t('common.save')}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default ProfilePage;
