import React, { useEffect, useState, useMemo } from 'react';
import { Card, Table, Button, Modal, Form, Input, Switch, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../../services/api';

const Uoms = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/v1/budgets/uoms/');
      const list = Array.isArray(data) ? data : data?.results || [];
      setData(list);
    } catch (e) {
      message.error('Failed to load UoMs');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const columns = useMemo(
    () => [
      { title: 'Code', dataIndex: 'code', key: 'code' },
      { title: 'Name', dataIndex: 'name', key: 'name' },
      { title: 'Short', dataIndex: 'short_name', key: 'short_name' },
      { title: 'Active', dataIndex: 'is_active', key: 'is_active', render: (v) => (v ? 'Yes' : 'No') },
    ],
    [],
  );

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await api.post('/api/v1/budgets/uoms/', {
        code: values.code,
        name: values.name,
        short_name: values.short_name || '',
        is_active: values.is_active ?? true,
      });
      message.success('UoM created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Could not create UoM');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card
      title="Units of Measure"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          New UoM
        </Button>
      }
    >
      <Table columns={columns} dataSource={data} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />

      <Modal title="Create UoM" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} confirmLoading={saving} okText="Create">
        <Form layout="vertical" form={form} initialValues={{ is_active: true }}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input placeholder="e.g., PCS, KG, M" />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Pieces, Kilogram, Meter" />
          </Form.Item>
          <Form.Item name="short_name" label="Short Name">
            <Input placeholder="e.g., pc, kg, m" />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default Uoms;
