import React, { useEffect, useState } from 'react';
import { Card, List, Space, Button, Select, Typography, message } from 'antd';
import api from '../../services/api';

const { Text } = Typography;

const TeamTasks = () => {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      const { data } = await api.get('/api/v1/tasks/team/', { params });
      const list = Array.isArray(data) ? data : data?.results || [];
      setTasks(list);
    } catch (e) {
      message.error('Failed to load team tasks');
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [statusFilter]);

  const escalate = async (id) => {
    try {
      await api.post(`/api/v1/tasks/${id}/escalate/`);
      message.success('Escalated');
      load();
    } catch (e) {
      message.error('Could not escalate');
    }
  };

  return (
    <Card
      title="Delegated / Team Tasks"
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
              <Button type="link" onClick={() => escalate(task.id)}>
                Escalate
              </Button>,
            ]}
          >
            <Space direction="vertical" size={0} style={{ width: '100%' }}>
              <Text strong>{task.title}</Text>
              <Text type="secondary">
                {task.assigned_to_name ? `Assignee: ${task.assigned_to_name} · ` : ''}
                {(task.status || '').replace('_', ' ')}
              </Text>
              {task.description ? <Text>{task.description}</Text> : null}
            </Space>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default TeamTasks;

