import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Select, Space, Switch, Button, Typography, message } from 'antd';
import { LinkOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Text } = Typography;

const CalendarSync = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [icsUrl, setIcsUrl] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/api/v1/tasks/calendar/me/');
      form.setFieldsValue({
        email: data?.email || '',
        provider: data?.provider || 'google',
        enabled: Boolean(data?.enabled),
      });
      setIcsUrl(data?.ics_url || null);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const onSubmit = async (values) => {
    try {
      setSaving(true);
      const { data } = await api.post('/api/v1/tasks/calendar/me/', values);
      setIcsUrl(data?.ics_url || null);
      message.success('Calendar preferences saved');
    } catch (e) {
      message.error('Save failed');
    } finally {
      setSaving(false);
    }
  };

  const openOutlookConnect = async () => {
    try {
      const { data } = await api.get('/api/v1/tasks/calendar/outlook/auth-url');
      if (data?.auth_url) {
        window.open(data.auth_url, '_blank');
      } else {
        message.error('Outlook OAuth not configured');
      }
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || 'Failed to start Outlook connect';
      message.error(detail);
    }
  };

  return (
    <Card title="Calendar Sync" loading={loading}>
      <Form layout="vertical" form={form} onFinish={onSubmit}>
        <Form.Item name="provider" label="Provider">
          <Select options={[{ value: 'google', label: 'Google' }, { value: 'outlook', label: 'Outlook' }]} />
        </Form.Item>
        <Form.Item name="email" label="Calendar Email">
          <Input placeholder="you@example.com" />
        </Form.Item>
        <Form.Item name="enabled" label="Enable Sync" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={saving}>Save</Button>
          <Button onClick={load} disabled={saving}>Reset</Button>
          {form.getFieldValue('provider') === 'outlook' ? (
            <Button onClick={openOutlookConnect} icon={<LinkOutlined />}>Connect Outlook</Button>
          ) : null}
        </Space>
      </Form>
      <div style={{ marginTop: 16 }}>
        <Text type="secondary">Subscribe to this ICS feed in Outlook or Google Calendar:</Text>
        <div>
          {icsUrl ? <Input value={icsUrl} readOnly /> : <Text type="secondary">Enable sync to generate a personal ICS link.</Text>}
        </div>
      </div>
    </Card>
  );
};

export default CalendarSync;
