import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, Space, Progress, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import useAuthStore from '@/stores/authStore';

const { Title, Text } = Typography;

interface RegisterFormValues {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const getPasswordStrength = (password: string): { percent: number; status: 'exception' | 'active' | 'success'; textKey: string } => {
  if (!password) return { percent: 0, status: 'exception', textKey: '' };

  let score = 0;
  if (password.length >= 6) score += 20;
  if (password.length >= 8) score += 10;
  if (password.length >= 12) score += 10;
  if (/[a-z]/.test(password)) score += 15;
  if (/[A-Z]/.test(password)) score += 15;
  if (/[0-9]/.test(password)) score += 15;
  if (/[^a-zA-Z0-9]/.test(password)) score += 15;

  if (score <= 30) return { percent: score, status: 'exception', textKey: 'registerPage.passwordStrengthWeak' };
  if (score <= 60) return { percent: score, status: 'active', textKey: 'registerPage.passwordStrengthMedium' };
  return { percent: score, status: 'success', textKey: 'registerPage.passwordStrengthStrong' };
};

const RegisterPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { register, isLoading } = useAuthStore();
  const [form] = Form.useForm();
  const [passwordStrength, setPasswordStrength] = useState<{ percent: number; status: 'exception' | 'active' | 'success'; textKey: string }>({
    percent: 0,
    status: 'exception',
    textKey: '',
  });

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const strength = getPasswordStrength(e.target.value);
    setPasswordStrength(strength);
  };

  const handleSubmit = async (values: RegisterFormValues) => {
    try {
      await register(values.username, values.email, values.password);
      message.success(t('registerPage.registerSuccess'));
      navigate('/', { replace: true });
    } catch (error: any) {
      const errorMsg = error?.response?.data?.message || t('registerPage.registerFailed');
      message.error(errorMsg);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '24px',
    }}>
      <Card
        style={{
          width: 420,
          borderRadius: 12,
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
        }}
        bodyStyle={{ padding: '40px 32px' }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Space direction="vertical" size={4}>
            <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
              HydroClaude
            </Title>
            <Text type="secondary" style={{ fontSize: 14 }}>
              {t('loginPage.subtitle')}
            </Text>
          </Space>
          <Title level={4} style={{ marginTop: 16, marginBottom: 0 }}>
            {t('registerPage.title')}
          </Title>
        </div>

        <Form
          form={form}
          name="register"
          onFinish={handleSubmit}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: t('registerPage.usernameRequired') },
              { min: 3, message: t('registerPage.usernameRequired') },
              { max: 20, message: t('registerPage.usernameRequired') },
              { pattern: /^[a-zA-Z0-9_]+$/, message: t('registerPage.usernameRequired') },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder={t('registerPage.usernamePlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="email"
            rules={[
              { required: true, message: t('registerPage.emailRequired') },
              { type: 'email', message: t('registerPage.emailInvalid') },
            ]}
          >
            <Input
              prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
              placeholder={t('registerPage.emailPlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: t('registerPage.passwordRequired') },
              { min: 6, message: t('registerPage.passwordMin') },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder={t('registerPage.passwordPlaceholder')}
              onChange={handlePasswordChange}
            />
          </Form.Item>

          {passwordStrength.textKey && (
            <Form.Item style={{ marginTop: -16, marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Progress
                  percent={passwordStrength.percent}
                  status={passwordStrength.status}
                  showInfo={false}
                  size="small"
                  style={{ flex: 1 }}
                />
                <Text
                  style={{
                    fontSize: 12,
                    flexShrink: 0,
                    color: passwordStrength.status === 'exception'
                      ? '#ff4d4f'
                      : passwordStrength.status === 'active'
                        ? '#faad14'
                        : '#52c41a',
                  }}
                >
                  {t(passwordStrength.textKey)}
                </Text>
              </div>
            </Form.Item>
          )}

          <Form.Item
            name="confirmPassword"
            dependencies={['password']}
            rules={[
              { required: true, message: t('registerPage.confirmRequired') },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error(t('registerPage.passwordMismatch')));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder={t('registerPage.confirmPassword')}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
              style={{ height: 44, borderRadius: 6 }}
            >
              {t('registerPage.registerBtn')}
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            <Text type="secondary">
              {t('auth.hasAccount')}{' '}
              <Link to="/login">{t('auth.loginNow')}</Link>
            </Text>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default RegisterPage;
