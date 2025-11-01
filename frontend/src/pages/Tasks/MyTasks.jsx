import React, { useEffect, useState } from 'react';
import { Card, List, Space, Button, Select, DatePicker, Typography, message } from 'antd';
import dayjs from 'dayjs';
import api from '../../services/api';

const { Text } = Typography;

const MyTasks = () => {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      const { data } = await api.get('/api/v1/tasks/my/', { params });
      const list = Array.isArray(data) ? data : data?.results || [];
      setTasks(list);
    } catch (e) {
      message.error('Failed to load tasks');
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [statusFilter]);

  const updateStatus = async (id, status) => {
    try {
      await api.patch(`/api/v1/tasks/${id}/status/`, { status });
      setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, status } : t)));
    } catch (e) {
      message.error('Could not update status');
    }
  };

  const snooze = async (id, minutes = 60) => {
    try {
      const { data } = await api.post(`/api/v1/tasks/${id}/snooze/`, { minutes });
      setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, due_date: data?.due_date } : t)));
    } catch (e) {
      message.error('Could not snooze task');
    }
  };

  return (
    <Card
      title="My Tasks"
      extra={
        <Space>
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            placeholder="Status"
            style={{ width: 160 }}
            options={[
              { value: '', label: 'All' },
              { value: 'not_started', label: 'Not started' },
              { value: 'in_progress', label: 'In progress' },
              { value: 'blocked', label: 'Blocked' },
              { value: 'done', label: 'Done' },
            ]}
          />
          <Button onClick={load}>Refresh</Button>
        </Space>
      }
      loading={loading}
    >
      <List
        dataSource={tasks}
        renderItem={(task) => (
          <List.Item
            key={task.id}
            actions={[
              <Select
                size="small"
                value={task.status}
                onChange={(v) => updateStatus(task.id, v)}
                style={{ width: 160 }}
                options={[
                  { value: 'not_started', label: 'Not started' },
                  { value: 'in_progress', label: 'In progress' },
                  { value: 'blocked', label: 'Blocked' },
                  { value: 'done', label: 'Done' },
                ]}
              />,
              <Button type="link" onClick={() => snooze(task.id, 60)}>
                Snooze 1h
              </Button>,
            ]}
          >
            <Space direction="vertical" size={0} style={{ width: '100%' }}>
              <Text strong>{task.title}</Text>
              <Text type="secondary">
                {(task.status || '').replace('_', ' ')}
                {task.due_date ? ` · due ${dayjs(task.due_date).format('DD MMM, HH:mm')}` : ''}
              </Text>
              {task.description ? <Text>{task.description}</Text> : null}
            </Space>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default MyTasks;

