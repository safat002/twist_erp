import React, { useEffect, useState } from 'react';
import { Card, Table, Tabs, Button, message } from 'antd';
import api from '../../services/api';

const MyAcknowledgements = () => {
  const [pending, setPending] = useState([]);
  const [acks, setAcks] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [p, a] = await Promise.all([
        api.get('/api/v1/policies/policies/my-pending/'),
        api.get('/api/v1/policies/acknowledgements/my-acks/'),
      ]);
      setPending(Array.isArray(p.data) ? p.data : p.data?.results || []);
      setAcks(Array.isArray(a.data) ? a.data : a.data?.results || []);
    } catch (e) {
      message.error('Failed to load acknowledgements');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const ack = async (id) => {
    try {
      await api.post(`/api/v1/policies/policies/${id}/acknowledge/`);
      load();
      message.success('Acknowledged');
    } catch (e) {
      message.error('Failed to acknowledge');
    }
  };

  return (
    <Card title="My Policy Acknowledgements">
      <Tabs
        items={[
          {
            key: 'pending',
            label: 'Pending',
            children: (
              <Table
                dataSource={pending}
                rowKey="id"
                loading={loading}
                columns={[
                  { title: 'Code', dataIndex: 'code' },
                  { title: 'Title', dataIndex: 'title' },
                  { title: 'Version', dataIndex: 'version' },
                  { title: 'Category', dataIndex: 'category' },
                  {
                    title: 'Actions',
                    render: (_, r) => (
                      <Button size="small" type="primary" onClick={() => ack(r.id)}>Acknowledge</Button>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'acks',
            label: 'Acknowledged',
            children: (
              <Table
                dataSource={acks}
                rowKey="id"
                loading={loading}
                columns={[
                  { title: 'Policy', dataIndex: ['policy', 'title'], render: (_, r) => r.policy || r.policy_id || '-' },
                  { title: 'Version', dataIndex: 'version' },
                  { title: 'Date', dataIndex: 'acknowledged_at' },
                ]}
              />
            ),
          },
        ]}
      />
    </Card>
  );
};

export default MyAcknowledgements;

