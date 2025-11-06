import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, InputNumber, Space, Switch, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../../services/api';

const ItemCodes = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [uoms, setUoms] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [codesRes, uomRes] = await Promise.all([
        api.get('/api/v1/budgets/item-codes/'),
        api.get('/api/v1/budgets/uoms/'),
      ]);
      const items = Array.isArray(codesRes.data) ? codesRes.data : codesRes.data?.results || [];
      const uomList = Array.isArray(uomRes.data) ? uomRes.data : uomRes.data?.results || [];
      setData(items);
      setUoms(uomList);
    } catch (e) {
      message.error('Failed to load item codes');
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
      { title: 'Category', dataIndex: 'category', key: 'category' },
      { title: 'UoM', dataIndex: 'uom_name', key: 'uom_name' },
      {
        title: 'Standard Price',
        dataIndex: 'standard_price',
        key: 'standard_price',
        render: (v) => Number(v || 0).toFixed(2),
      },
      {
        title: 'Active',
        dataIndex: 'is_active',
        key: 'is_active',
        render: (v) => (v ? 'Yes' : 'No'),
      },
    ],
    [],
  );

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await api.post('/api/v1/budgets/item-codes/', {
        code: values.code,
        name: values.name,
        category: values.category || '',
        uom: values.uom,
        standard_price: values.standard_price || 0,
        is_active: values.is_active ?? true,
      });
      message.success('Item code created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      if (e?.errorFields) return; // form errors
      const detail = e?.response?.data?.detail || 'Could not create item code';
      message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card
      title="Budget Item Codes"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          New Item Code
        </Button>
      }
    >
      <Table columns={columns} dataSource={data} loading={loading} rowKey="id" pagination={{ pageSize: 10 }} />

      <Modal title="Create Item Code" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} confirmLoading={saving} okText="Create">
        <Form layout="vertical" form={form} initialValues={{ is_active: true }}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input placeholder="Unique code" />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="Category">
            <Input />
          </Form.Item>
          <Form.Item name="uom" label="Unit of Measure" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={(uoms || []).map((u) => ({ value: u.id, label: `${u.short_name || u.code} - ${u.name}` }))}
            />
          </Form.Item>
          <Form.Item name="standard_price" label="Standard Price">
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ItemCodes;



