import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, InputNumber } from 'antd';
import { App as AntApp } from 'antd';
import api from '../../services/api';
import usePermissions from '../../hooks/usePermissions';

const ProductsList = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState(null);
  const { can } = usePermissions();
  const { message } = AntApp.useApp();
  const [accounts, setAccounts] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const [res, acc] = await Promise.all([
        api.get('/api/v1/microfinance/products/'),
        api.get('/api/v1/finance/accounts/', { params: { limit: 200 } }).catch(() => ({ data: { results: [] } })),
      ]);
      setData(Array.isArray(res.data) ? res.data : res.data?.results || []);
      const accList = Array.isArray(acc.data) ? acc.data : acc.data?.results || [];
      setAccounts(accList.map((a) => ({ value: a.id, label: `${a.code} - ${a.name}` })));
    } catch (e) {
      message.error('Failed to load products');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const columns = useMemo(() => ([
    { title: 'Code', dataIndex: 'code' },
    { title: 'Name', dataIndex: 'name' },
    { title: 'Annual Rate', dataIndex: 'interest_rate_annual' },
    { title: 'Term (months)', dataIndex: 'term_months' },
    { title: 'Frequency', dataIndex: 'repayment_frequency' },
    {
      title: 'Actions', key: 'actions', render: (_, r) => (
        can('microfinance.update_loan') ? <Button size="small" onClick={() => openEdit(r)}>Edit</Button> : null
      ),
    },
  ]), [can]);

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.post('/api/v1/microfinance/products/', {
        name: v.name,
        interest_rate_annual: v.interest_rate_annual,
        term_months: v.term_months,
        repayment_frequency: v.repayment_frequency,
        portfolio_account: v.portfolio_account,
        interest_income_account: v.interest_income_account,
        cash_account: v.cash_account,
      });
      setOpen(false);
      form.resetFields();
      load();
      message.success('Product created');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to create product');
    }
  };

  const openEdit = (record) => {
    setEditRecord(record);
    editForm.setFieldsValue({
      name: record.name,
      interest_rate_annual: record.interest_rate_annual,
      term_months: record.term_months,
      repayment_frequency: record.repayment_frequency,
      portfolio_account: record.portfolio_account || null,
      interest_income_account: record.interest_income_account || null,
      cash_account: record.cash_account || null,
    });
    setEditOpen(true);
  };

  const handleUpdate = async () => {
    try {
      const v = await editForm.validateFields();
      await api.patch(`/api/v1/microfinance/products/${editRecord.id}/`, {
        name: v.name,
        interest_rate_annual: v.interest_rate_annual,
        term_months: v.term_months,
        repayment_frequency: v.repayment_frequency,
        portfolio_account: v.portfolio_account,
        interest_income_account: v.interest_income_account,
        cash_account: v.cash_account,
      });
      setEditOpen(false);
      setEditRecord(null);
      load();
      message.success('Product updated');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to update product');
    }
  };

  return (
    <Card title="Loan Products" extra={can('microfinance.create_loan') ? <Button type="primary" onClick={() => setOpen(true)}>New Product</Button> : null}>
      <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />
      <Modal title="Create Product" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} okText="Create">
        <Form layout="vertical" form={form} initialValues={{ repayment_frequency: 'monthly' }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}> <Input /> </Form.Item>
          <Form.Item name="interest_rate_annual" label="Annual Rate" rules={[{ required: true }]}> <InputNumber min={0} max={1} step={0.001} style={{ width: '100%' }} /> </Form.Item>
          <Form.Item name="term_months" label="Term (months)" rules={[{ required: true }]}> <InputNumber min={1} style={{ width: '100%' }} /> </Form.Item>
          <Form.Item name="repayment_frequency" label="Frequency" rules={[{ required: true }]}> 
            <Select options={[{value:'weekly',label:'Weekly'},{value:'biweekly',label:'Bi-Weekly'},{value:'monthly',label:'Monthly'}]} />
          </Form.Item>
          <Form.Item name="portfolio_account" label="Portfolio (Receivable) Account" rules={[{ required: true }]}>
            <Select options={accounts} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="interest_income_account" label="Interest Income Account" rules={[{ required: true }]}>
            <Select options={accounts} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="cash_account" label="Cash/Bank Account" rules={[{ required: true }]}>
            <Select options={accounts} showSearch optionFilterProp="label" />
          </Form.Item>
        </Form>
      </Modal>
      <Modal title={`Edit Product ${editRecord?.code || ''}`} open={editOpen} onCancel={() => setEditOpen(false)} onOk={handleUpdate} okText="Update">
        <Form layout="vertical" form={editForm}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}> <Input /> </Form.Item>
          <Form.Item name="interest_rate_annual" label="Annual Rate" rules={[{ required: true }]}> <InputNumber min={0} max={1} step={0.001} style={{ width: '100%' }} /> </Form.Item>
          <Form.Item name="term_months" label="Term (months)" rules={[{ required: true }]}> <InputNumber min={1} style={{ width: '100%' }} /> </Form.Item>
          <Form.Item name="repayment_frequency" label="Frequency" rules={[{ required: true }]}> 
            <Select options={[{value:'weekly',label:'Weekly'},{value:'biweekly',label:'Bi-Weekly'},{value:'monthly',label:'Monthly'}]} />
          </Form.Item>
          <Form.Item name="portfolio_account" label="Portfolio (Receivable) Account" rules={[{ required: true }]}>
            <Select options={accounts} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="interest_income_account" label="Interest Income Account" rules={[{ required: true }]}>
            <Select options={accounts} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="cash_account" label="Cash/Bank Account" rules={[{ required: true }]}>
            <Select options={accounts} showSearch optionFilterProp="label" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ProductsList;
