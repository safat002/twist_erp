import React, { useEffect, useState } from 'react';
import { Button, Card, Form, Input, Select, Space, Table, Tag, DatePicker, message } from 'antd';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import {
  fetchPeriods,
  createPeriod,
  closePeriod,
  openPeriod,
  lockPeriod,
  unlockPeriod,
} from '../../../services/finance';

const STATUS_COLORS = { OPEN: 'green', CLOSED: 'red', LOCKED: 'blue' };

const PeriodsList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [periods, setPeriods] = useState([]);
  const [form] = Form.useForm();

  const load = async () => {
    try {
      setLoading(true);
      const { data } = await fetchPeriods();
      setPeriods(Array.isArray(data?.results) ? data.results : data);
    } catch (err) {
      message.error('Unable to load fiscal periods');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentCompany?.id) load();
  }, [currentCompany?.id]);

  const columns = [
    { title: 'Period', dataIndex: 'period', key: 'period' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={STATUS_COLORS[status] || 'default'}>{status}</Tag>,
    },
    { title: 'Locked By', dataIndex: 'locked_by', key: 'locked_by', render: (v) => (v ? v : '-') },
    { title: 'Locked At', dataIndex: 'locked_at', key: 'locked_at', render: (v) => (v ? v : '-') },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={async () => { await openPeriod(record.id); message.success('Opened'); load(); }}>Open</Button>
          <Button size="small" onClick={async () => { await closePeriod(record.id); message.success('Closed'); load(); }}>Close</Button>
          <Button size="small" onClick={async () => { await lockPeriod(record.id); message.success('Locked'); load(); }}>Lock</Button>
          <Button size="small" onClick={async () => { await unlockPeriod(record.id); message.success('Unlocked'); load(); }}>Unlock</Button>
        </Space>
      ),
    },
  ];

  const handleCreate = async (values) => {
    try {
      const period = values.period.format('YYYY-MM');
      await createPeriod({ period, status: values.status });
      message.success('Fiscal period created');
      form.resetFields();
      load();
    } catch (err) {
      message.error('Failed to create period');
    }
  };

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>Fiscal Periods</span>
      </Space>
      <Card style={{ marginBottom: 16 }}>
        <Form layout="inline" form={form} onFinish={handleCreate}>
          <Form.Item name="period" label="Period" rules={[{ required: true }]}> 
            <DatePicker picker="month" />
          </Form.Item>
          <Form.Item name="status" label="Status" initialValue="OPEN">
            <Select options={[{ value: 'OPEN' }, { value: 'CLOSED' }, { value: 'LOCKED' }]} style={{ width: 160 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Create</Button>
          </Form.Item>
        </Form>
      </Card>
      <Card>
        <Table rowKey="id" loading={loading} dataSource={periods} columns={columns} pagination={{ pageSize: 12 }} />
      </Card>
    </div>
  );
};

export default PeriodsList;

