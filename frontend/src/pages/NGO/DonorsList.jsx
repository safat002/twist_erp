import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input } from 'antd';
import { App as AntApp } from 'antd';
import api from '../../services/api';
import usePermissions from '../../hooks/usePermissions';

const DonorsList = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { can } = usePermissions();
  const { message } = AntApp.useApp();

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/v1/ngo/donors/');
      setData(Array.isArray(res.data) ? res.data : res.data?.results || []);
    } catch (e) {
      message.error('Failed to load donors');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const columns = useMemo(() => ([
    { title: 'Code', dataIndex: 'code' },
    { title: 'Name', dataIndex: 'name' },
    { title: 'Email', dataIndex: 'email' },
    { title: 'Phone', dataIndex: 'phone' },
    { title: 'Website', dataIndex: 'website' },
  ]), []);

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.post('/api/v1/ngo/donors/', {
        name: v.name,
        email: v.email,
        phone: v.phone,
        website: v.website,
        address: v.address,
      });
      setOpen(false);
      form.resetFields();
      load();
      message.success('Donor created');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to create donor');
    }
  };

  return (
    <Card title="Donors" extra={can('ngo.create_program') ? <Button type="primary" onClick={() => setOpen(true)}>New Donor</Button> : null}>
      <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />
      <Modal title="Create Donor" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} okText="Create">
        <Form layout="vertical" form={form}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="email" label="Email"><Input /></Form.Item>
          <Form.Item name="phone" label="Phone"><Input /></Form.Item>
          <Form.Item name="website" label="Website"><Input /></Form.Item>
          <Form.Item name="address" label="Address"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default DonorsList;
