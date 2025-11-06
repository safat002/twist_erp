import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, InputNumber } from 'antd';
import { App as AntApp } from 'antd';
import api from '../../services/api';
import usePermissions from '../../hooks/usePermissions';

const BorrowersList = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { can } = usePermissions();
  const { message } = AntApp.useApp();

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/v1/microfinance/borrowers/');
      setData(Array.isArray(res.data) ? res.data : res.data?.results || []);
    } catch (e) {
      message.error('Failed to load borrowers');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const columns = useMemo(() => ([
    { title: 'Code', dataIndex: 'code' },
    { title: 'Name', dataIndex: 'name' },
    { title: 'Mobile', dataIndex: 'mobile' },
    { title: 'Group', dataIndex: 'group_name' },
  ]), []);

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.post('/api/v1/microfinance/borrowers/', {
        name: v.name,
        mobile: v.mobile,
        nid: v.nid,
        address: v.address,
        group_name: v.group_name,
      });
      setOpen(false);
      form.resetFields();
      load();
      message.success('Borrower created');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to create borrower');
    }
  };

  return (
    <Card title="Borrowers" extra={can('microfinance.create_loan') ? <Button type="primary" onClick={() => setOpen(true)}>New Borrower</Button> : null}>
      <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />

      <Modal title="Create Borrower" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} okText="Create">
        <Form layout="vertical" form={form}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}> <Input /> </Form.Item>
          <Form.Item name="mobile" label="Mobile"> <Input /> </Form.Item>
          <Form.Item name="nid" label="NID"> <Input /> </Form.Item>
          <Form.Item name="group_name" label="Group"> <Input /> </Form.Item>
          <Form.Item name="address" label="Address"> <Input.TextArea rows={2} /> </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default BorrowersList;
