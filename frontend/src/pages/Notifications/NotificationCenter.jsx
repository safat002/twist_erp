import React, { useEffect, useMemo, useState } from 'react';
import { Card, List, Space, Button, Tag, Select, Typography, Row, Col, message, Divider } from 'antd';
import api from '../../services/api';

const { Text } = Typography;

const NotificationCenter = () => {
  const [loading, setLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [status, setStatus] = useState('');
  const [severity, setSeverity] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (status) params.status = status;
      if (severity) params.severity = severity;
      const { data } = await api.get('/api/v1/notifications/center/', { params });
      const list = Array.isArray(data) ? data : data?.results || [];
      setNotifications(list);
    } catch (e) {
      message.error('Failed to load notifications');
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [status, severity]);

  const handleMark = async (id, next = 'read') => {
    try {
      await api.patch(`/api/v1/notifications/${id}/mark/`, { status: next });
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, status: next } : n)));
    } catch (e) {
      message.error('Could not update notification');
    }
  };

  const handleClearAll = async () => {
    try {
      await api.post('/api/v1/notifications/clear-all/');
      load();
    } catch (e) {
      message.error('Could not clear notifications');
    }
  };

  const severityColor = (sev) => ({ info: 'blue', warning: 'orange', critical: 'red' }[sev] || 'default');

  const groups = useMemo(() => {
    const list = notifications || [];
    const g = { critical: [], warning: [], info: [] };
    list.forEach((n) => {
      const sev = (n.severity || 'info').toLowerCase();
      if (sev === 'critical') g.critical.push(n);
      else if (sev === 'warning') g.warning.push(n);
      else g.info.push(n);
    });
    return g;
  }, [notifications]);

  return (
    <div>
      <Card
        title="Notification Center"
        extra={
          <Space>
            <Select
              value={status}
              onChange={setStatus}
              placeholder="Status"
              style={{ width: 140 }}
              options={[
                { value: '', label: 'All' },
                { value: 'unread', label: 'Unread' },
                { value: 'read', label: 'Read' },
                { value: 'cleared', label: 'Cleared' },
              ]}
            />
            <Select
              value={severity}
              onChange={setSeverity}
              placeholder="Severity"
              style={{ width: 160 }}
              options={[
                { value: '', label: 'All' },
                { value: 'info', label: 'Info' },
                { value: 'warning', label: 'Warning' },
                { value: 'critical', label: 'Critical' },
              ]}
            />
            <Button onClick={load}>Refresh</Button>
            <Button danger onClick={handleClearAll}>
              Clear All
            </Button>
          </Space>
        }
        loading={loading}
      >
        {['critical', 'warning', 'info'].map((sev) => (
          <div key={sev}>
            {groups[sev].length ? (
              <>
                <Divider orientation="left">{sev.toUpperCase()}</Divider>
                <List
                  dataSource={groups[sev]}
                  renderItem={(n) => (
                    <List.Item
                      key={n.id}
                      actions={[
                        n.status !== 'read' ? (
                          <Button type="link" onClick={() => handleMark(n.id, 'read')}>
                            Mark Read
                          </Button>
                        ) : null,
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            <Tag color={severityColor(n.severity || 'info')}>{(n.severity || 'info').toUpperCase()}</Tag>
                            <Text strong>{n.title}</Text>
                          </Space>
                        }
                        description={<Text type="secondary">{n.body}</Text>}
                      />
                    </List.Item>
                  )}
                />
              </>
            ) : null}
          </div>
        ))}
      </Card>
    </div>
  );
};

export default NotificationCenter;
