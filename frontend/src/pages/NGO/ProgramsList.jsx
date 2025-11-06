import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, DatePicker, InputNumber } from 'antd';
import { App as AntApp } from 'antd';
import api from '../../services/api';
import usePermissions from '../../hooks/usePermissions';

const ProgramsList = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [donors, setDonors] = useState([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { can } = usePermissions();
  const { message } = AntApp.useApp();

  const load = async () => {
    setLoading(true);
    try {
      const [prog, dnr] = await Promise.all([
        api.get('/api/v1/ngo/programs/'),
        api.get('/api/v1/ngo/donors/'),
      ]);
      setData(Array.isArray(prog.data) ? prog.data : prog.data?.results || []);
      const donorsList = Array.isArray(dnr.data) ? dnr.data : dnr.data?.results || [];
      setDonors(donorsList.map((d) => ({ value: d.id, label: `${d.code} - ${d.name}` })));
    } catch (e) {
      message.error('Failed to load programs');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const columns = useMemo(() => ([
    { title: 'Code', dataIndex: 'code' },
    { title: 'Title', dataIndex: 'title' },
    { title: 'Donor', dataIndex: 'donor_name' },
    { title: 'Budget', dataIndex: 'total_budget' },
    { title: 'Status', dataIndex: 'status' },
  ]), []);

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.post('/api/v1/ngo/programs/', {
        donor: v.donor,
        title: v.title,
        total_budget: v.total_budget,
        currency: v.currency || 'USD',
        start_date: v.start_date?.format('YYYY-MM-DD'),
        end_date: v.end_date?.format('YYYY-MM-DD'),
      });
      message.success('Program created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to create program');
    }
  };

  return (
    <Card title="Programs" extra={can('ngo.create_program') ? <Button type="primary" onClick={() => setOpen(true)}>New Program</Button> : null}>
      <Table dataSource={data} rowKey="id" columns={columns} loading={loading} />
      <Modal title="Create Program" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} okText="Create">
        <Form layout="vertical" form={form}>
          <Form.Item name="donor" label="Donor" rules={[{ required: true }]}>
            <Select options={donors} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="total_budget" label="Total Budget" rules={[{ required: true }]}> 
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
          <Form.Item name="currency" label="Currency">
            <Input placeholder="USD" />
          </Form.Item>
          <Form.Item name="start_date" label="Start Date"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="end_date" label="End Date"><DatePicker style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ProgramsList;
