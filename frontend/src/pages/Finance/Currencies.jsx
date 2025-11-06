import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined, StarOutlined, StarFilled, DeleteOutlined } from '@ant-design/icons';
import { fetchCurrencies, createCurrency, updateCurrency, deleteCurrency, setBaseCurrency, fetchCurrencyChoices } from '../../services/finance';

const Currencies = () => {
  const [loading, setLoading] = useState(false);
  const [currencies, setCurrencies] = useState([]);
  const [choices, setChoices] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const load = async () => {
    try {
      setLoading(true);
      const [{ data: curData }, { data: choicesData }] = await Promise.all([
        fetchCurrencies(),
        fetchCurrencyChoices(),
      ]);
      setCurrencies(Array.isArray(curData) ? curData : curData?.results || []);
      const list = Array.isArray(choicesData?.results) ? choicesData.results : [];
      setChoices(list);
    } catch (e) {
      message.error('Failed to load currencies');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const showCreate = () => {
    setEditing(null);
    form.resetFields();
    setIsModalOpen(true);
  };

  const showEdit = (record) => {
    setEditing(record);
    form.setFieldsValue(record);
    setIsModalOpen(true);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
    setEditing(null);
    form.resetFields();
  };

  const handleSubmit = async (values) => {
    try {
      if (editing) {
        await updateCurrency(editing.id, values);
        message.success('Currency updated');
      } else {
        await createCurrency(values);
        message.success('Currency added');
      }
      handleCancel();
      load();
    } catch (e) {
      message.error('Save failed');
    }
  };

  const handleDelete = async (record) => {
    try {
      await deleteCurrency(record.id);
      message.success('Currency deleted');
      load();
    } catch (e) {
      message.error('Delete failed');
    }
  };

  const handleSetBase = async (record) => {
    try {
      await setBaseCurrency(record.code);
      message.success(`${record.code} is now base currency`);
      load();
    } catch (e) {
      message.error('Failed to set base currency');
    }
  };

  const codeOptions = useMemo(
    () => choices.map((c) => ({ value: c.code, label: `${c.code} — ${c.name}` })),
    [choices],
  );

  const columns = [
    { title: 'Code', dataIndex: 'code', key: 'code' },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Symbol', dataIndex: 'symbol', key: 'symbol' },
    { title: 'Decimals', dataIndex: 'decimal_places', key: 'decimal_places', width: 100 },
    {
      title: 'Base', dataIndex: 'is_base_currency', key: 'is_base_currency', width: 100, align: 'center',
      render: (val, record) => val ? <Tag color="gold">Base</Tag> : (
        <Button type="link" icon={<StarOutlined />} onClick={() => handleSetBase(record)}>Set Base</Button>
      ),
    },
    {
      title: 'Active', dataIndex: 'is_active', key: 'is_active', width: 100, align: 'center',
      render: (val) => <Tag color={val ? 'green' : 'default'}>{val ? 'Yes' : 'No'}</Tag>,
    },
    {
      title: 'Actions', key: 'actions', width: 180,
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => showEdit(record)}>Edit</Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>Delete</Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={showCreate}>Add Currency</Button>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={load}>Refresh</Button>
      </Space>
      <Card>
        <Table
          dataSource={currencies}
          columns={columns}
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editing ? 'Edit Currency' : 'Add Currency'}
        open={isModalOpen}
        onCancel={handleCancel}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="code" label="Code" rules={[{ required: true, message: 'Select a code' }]}> 
            <Select showSearch options={codeOptions} placeholder="Select ISO code" />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true, message: 'Enter name' }]}> 
            <Input placeholder="e.g., US Dollar" />
          </Form.Item>
          <Form.Item name="symbol" label="Symbol"> 
            <Input placeholder="$" />
          </Form.Item>
          <Form.Item name="decimal_places" label="Decimal Places" initialValue={2}> 
            <Select options={[{value:0,label:'0'},{value:2,label:'2'},{value:3,label:'3'},{value:4,label:'4'}]} />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked" initialValue>
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">Save</Button>
              <Button onClick={handleCancel}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default Currencies;

