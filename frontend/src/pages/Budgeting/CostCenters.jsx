import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Switch, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../../services/api';

const CostCenters = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/v1/budgets/cost-centers/');
      const list = Array.isArray(data) ? data : data?.results || [];
      setData(list);
    } catch (e) {
      message.error('Failed to load cost centers');
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
      { title: 'Type', dataIndex: 'cost_center_type', key: 'cost_center_type' },
      { title: 'Active', dataIndex: 'is_active', key: 'is_active', render: (v) => (v ? 'Yes' : 'No') },
    ],
    [],
  );

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await api.post('/api/v1/budgets/cost-centers/', {
        code: values.code,
        name: values.name,
        cost_center_type: values.cost_center_type || 'department',
        description: values.description || '',
        default_currency: values.default_currency || 'BDT',
        is_active: values.is_active ?? true,
      });
      message.success('Cost center created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      if (e?.errorFields) return;
      const detail = e?.response?.data?.detail || 'Could not create cost center';
      message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card
      title="Cost Centers"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          New Cost Center
        </Button>
      }
    >
      <Table columns={columns} dataSource={data} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />

      <Modal title="Create Cost Center" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} confirmLoading={saving} okText="Create">
        <Form layout="vertical" form={form} initialValues={{ cost_center_type: 'department', is_active: true }}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input placeholder="Unique code" />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="cost_center_type" label="Type">
            <Select
              options={[
                { value: 'department', label: 'Department' },
                { value: 'branch', label: 'Branch' },
                { value: 'program', label: 'Program / Grant' },
                { value: 'project', label: 'Project' },
                { value: 'production_line', label: 'Production Line' },
              ]}
            />
          </Form.Item>
          <Form.Item name="default_currency" label="Default Currency">
            <Input placeholder="e.g., BDT" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default CostCenters;

