import React, { useEffect, useMemo, useState } from 'react';
import {
  Avatar,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Form,
  Input,
  List,
  Row,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { UserOutlined, ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useAuth } from '../../contexts/AuthContext';
import { useCompany } from '../../contexts/CompanyContext';

const { Title, Text } = Typography;

const Settings = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, updateProfile, refreshProfile, profileLoading } = useAuth();
  const { companies } = useCompany();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const activeTabFromPath = useMemo(() => {
    if (location.pathname.endsWith('/preferences')) {
      return 'preferences';
    }
    return 'profile';
  }, [location.pathname]);

  const [activeTab, setActiveTab] = useState(activeTabFromPath);

  useEffect(() => {
    setActiveTab(activeTabFromPath);
  }, [activeTabFromPath]);

  useEffect(() => {
    if (!user) {
      form.resetFields();
      return;
    }
    form.setFieldsValue({
      first_name: user.first_name,
      last_name: user.last_name,
      phone: user.phone,
      default_company_id: user?.default_company?.id ?? null,
      default_company_group_id: user?.default_company_group?.id ?? null,
    });
  }, [form, user]);

  const companyOptions = useMemo(() => {
    const membershipCompanies = (user?.memberships || [])
      .filter((membership) => membership.is_active)
      .map((membership) => ({
        value: membership.company?.id,
        label: membership.company
          ? `${membership.company.code} — ${membership.company.name}`
          : 'Unknown Company',
      }))
      .filter((option) => option.value !== undefined && option.value !== null);

    const allOptions = companies
      .map((company) => ({ value: company.id, label: `${company.code} — ${company.name}` }))
      .filter((option) => option.value !== undefined && option.value !== null);

    const merged = [...membershipCompanies];
    allOptions.forEach((option) => {
      if (!merged.some((existing) => String(existing.value) === String(option.value))) {
        merged.push(option);
      }
    });
    return merged;
  }, [companies, user?.memberships]);

  const companyGroupOptions = useMemo(() => {
    return (user?.memberships || [])
      .map((membership) => membership.company_group)
      .filter(Boolean)
      .reduce((acc, group) => {
        if (!acc.find((item) => String(item.value) === String(group.id))) {
          acc.push({ value: group.id, label: group.name });
        }
        return acc;
      }, []);
  }, [user?.memberships]);

  const handleTabChange = (key) => {
    setActiveTab(key);
    if (key === 'profile') {
      navigate('/settings/profile', { replace: true });
    } else if (key === 'preferences') {
      navigate('/settings/preferences', { replace: true });
    } else {
      navigate('/settings', { replace: true });
    }
  };

  const handleProfileSubmit = async (values) => {
    try {
      setSaving(true);
      const payload = {
        first_name: values.first_name ?? '',
        last_name: values.last_name ?? '',
        phone: values.phone ?? '',
        default_company_id: values.default_company_id || null,
        default_company_group_id: values.default_company_group_id || null,
      };
      await updateProfile(payload);
      message.success('Profile updated successfully.');
    } catch (error) {
      const detail = error?.response?.data;
      let description = 'Failed to update profile.';
      if (detail && typeof detail === 'object') {
        const messages = Object.entries(detail).map(([field, errs]) => `${field}: ${errs}`);
        description = messages.join('\n');
      }
      message.error(description);
    } finally {
      setSaving(false);
    }
  };

  const refreshUserProfile = async () => {
    const data = await refreshProfile();
    if (data) {
      message.success('Profile refreshed.');
    }
  };

  const profileTab = (
    <Row gutter={[24, 24]}>
      <Col xs={24} lg={12}>
        <Card
          title="Account Details"
          extra={
            <Button icon={<ReloadOutlined />} onClick={refreshUserProfile} disabled={profileLoading} loading={profileLoading}>
              Refresh
            </Button>
          }
        >
          <Space align="start" size="large">
            <Avatar size={64} icon={<UserOutlined />} src={user?.avatar_url} />
            <div>
              <Title level={4} style={{ marginBottom: 0 }}>
                {user?.display_name || user?.username || 'User'}
              </Title>
              <Text type="secondary">{user?.email}</Text>
              <div style={{ marginTop: 8 }}>
                {user?.is_system_admin ? <Tag color="magenta">System Admin</Tag> : null}
                {user?.is_staff ? <Tag color="geekblue">Staff</Tag> : null}
              </div>
            </div>
          </Space>
          <Divider />
          <Form layout="vertical" form={form} onFinish={handleProfileSubmit}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="first_name" label="First name">
                  <Input placeholder="First name" allowClear />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="last_name" label="Last name">
                  <Input placeholder="Last name" allowClear />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="phone" label="Phone">
              <Input placeholder="Phone" allowClear />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="default_company_id" label="Default company">
                  <Select
                    allowClear
                    placeholder="Select default company"
                    options={companyOptions}
                    showSearch
                    optionFilterProp="label"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="default_company_group_id" label="Default company group">
                  <Select
                    allowClear
                    placeholder="Select company group"
                    options={companyGroupOptions}
                    showSearch
                    optionFilterProp="label"
                  />
                </Form.Item>
              </Col>
            </Row>
            <Space>
              <Button type="primary" icon={<SaveOutlined />} htmlType="submit" loading={saving}>
                Save changes
              </Button>
              <Button onClick={() => form.resetFields()} disabled={saving}>
                Reset
              </Button>
            </Space>
          </Form>
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card title="Memberships">
          <List
            dataSource={user?.memberships || []}
            locale={{ emptyText: 'No company assignments found.' }}
            renderItem={(item) => (
              <List.Item key={item.id}>
                <List.Item.Meta
                  title={
                    <Space size="small">
                      <Text strong>{item.company?.name || 'Unknown company'}</Text>
                      <Tag color={item.is_active ? 'green' : 'default'}>
                        {item.role_name || 'Role'}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={0}>
                      <Text type="secondary">
                        Code: {item.company?.code || '—'} · Currency: {item.company?.currency_code || '—'}
                      </Text>
                      <Text type="secondary">
                        Group: {item.company_group?.name || '—'}
                      </Text>
                      <Text type="secondary">
                        Assigned {dayjs(item.assigned_at).format('MMM D, YYYY HH:mm')}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
        <Card title="Account Flags" style={{ marginTop: 24 }}>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Username">{user?.username}</Descriptions.Item>
            <Descriptions.Item label="Email">{user?.email}</Descriptions.Item>
            <Descriptions.Item label="Staff">{user?.is_staff ? 'Yes' : 'No'}</Descriptions.Item>
            <Descriptions.Item label="System Admin">{user?.is_system_admin ? 'Yes' : 'No'}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  );

  const preferencesTab = (
    <Card>
      <Title level={4}>Preferences</Title>
      <Text type="secondary">
        Preference management is coming soon. In the meantime, profile updates are available under the Profile tab.
      </Text>
    </Card>
  );

  return (
    <div>
      <Title level={2}>User Settings</Title>
      <Text type="secondary">
        Manage your profile information, default company, and personal preferences for the Twist ERP workspace.
      </Text>
      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        style={{ marginTop: 24 }}
        items={[
          { key: 'profile', label: 'Profile', children: profileTab },
          { key: 'preferences', label: 'Preferences', children: preferencesTab },
        ]}
      />
    </div>
  );
};

export default Settings;
