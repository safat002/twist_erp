import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, InputNumber, Select, DatePicker, Input, Space, Tag } from 'antd';
import { App as AntApp } from 'antd';
import api from '../../services/api';
import usePermissions from '../../hooks/usePermissions';

const LoansList = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [borrowers, setBorrowers] = useState([]);
  const [products, setProducts] = useState([]);
  const [open, setOpen] = useState(false);
  const [repayOpen, setRepayOpen] = useState(false);
  const [repayLoan, setRepayLoan] = useState(null);
  const [form] = Form.useForm();
  const [repayForm] = Form.useForm();
  const { can } = usePermissions();
  const { message } = AntApp.useApp();

  const load = async () => {
    setLoading(true);
    try {
      const [loans, brw, prod] = await Promise.all([
        api.get('/api/v1/microfinance/loans/'),
        api.get('/api/v1/microfinance/borrowers/'),
        api.get('/api/v1/microfinance/products/'),
      ]);
      setData(Array.isArray(loans.data) ? loans.data : loans.data?.results || []);
      const brws = Array.isArray(brw.data) ? brw.data : brw.data?.results || [];
      setBorrowers(brws.map((b) => ({ value: b.id, label: `${b.code} - ${b.name}` })));
      const prods = Array.isArray(prod.data) ? prod.data : prod.data?.results || [];
      setProducts(prods.map((p) => ({ value: p.id, label: `${p.code} - ${p.name}` })));
    } catch (e) {
      message.error('Failed to load loans');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const columns = useMemo(() => ([
    { title: 'Number', dataIndex: 'number' },
    { title: 'Borrower', dataIndex: 'borrower_name' },
    { title: 'Product', dataIndex: 'product_name' },
    { title: 'Principal', dataIndex: 'principal' },
    { title: 'Outstanding', dataIndex: 'outstanding_amount' },
    { title: 'Status', dataIndex: 'status', render: (v) => <Tag>{(v || '').toUpperCase()}</Tag> },
    {
      title: 'Actions', key: 'actions', render: (_, r) => (
        <Space>
          {['applied', 'approved'].includes(r.status) && can('microfinance.disburse_loan') && (
            <Button size="small" onClick={() => disburse(r.id)}>Disburse</Button>
          )}
          {['active', 'disbursed'].includes(r.status) && can('microfinance.record_repayment') && (
            <Button size="small" type="primary" onClick={() => openRepay(r)}>Repay</Button>
          )}
        </Space>
      ),
    },
  ]), []);

  const disburse = async (id) => {
    try {
      await api.post(`/api/v1/microfinance/loans/${id}/disburse/`);
      message.success('Loan disbursed');
      load();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to disburse');
    }
  };

  const openRepay = (loan) => {
    setRepayLoan(loan);
    setRepayOpen(true);
  };

  const handleRepay = async () => {
    try {
      const v = await repayForm.validateFields();
      await api.post('/api/v1/microfinance/repayments/', {
        loan: repayLoan.id,
        amount: v.amount,
        payment_date: v.payment_date?.format('YYYY-MM-DD'),
      });
      setRepayOpen(false);
      repayForm.resetFields();
      load();
      message.success('Repayment recorded');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to record repayment');
    }
  };

  const handleCreate = async () => {
    try {
      const v = await form.validateFields();
      await api.post('/api/v1/microfinance/loans/', {
        borrower: v.borrower,
        product: v.product,
        principal: v.principal,
        interest_rate_annual: v.interest_rate_annual,
        term_months: v.term_months,
        repayment_frequency: v.repayment_frequency,
      });
      setOpen(false);
      form.resetFields();
      load();
      message.success('Loan created');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to create loan');
    }
  };

  return (
    <Card title="Microfinance Loans" extra={can('microfinance.create_loan') ? <Button type="primary" onClick={() => setOpen(true)}>New Loan</Button> : null}>
      <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />

      <Modal title="Create Loan" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} okText="Create">
        <Form layout="vertical" form={form}>
          <Form.Item name="borrower" label="Borrower" rules={[{ required: true }]}> 
            <Select options={borrowers} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="product" label="Product" rules={[{ required: true }]}> 
            <Select options={products} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="principal" label="Principal" rules={[{ required: true }]}> 
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="interest_rate_annual" label="Interest Rate (annual)" rules={[{ required: true }]}> 
            <InputNumber min={0} max={1} step={0.001} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="term_months" label="Term (months)" rules={[{ required: true }]}> 
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="repayment_frequency" label="Frequency" rules={[{ required: true }]} initialValue="monthly"> 
            <Select options={[{value:'weekly',label:'Weekly'},{value:'biweekly',label:'Bi-Weekly'},{value:'monthly',label:'Monthly'}]} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="Record Repayment" open={repayOpen} onCancel={() => setRepayOpen(false)} onOk={handleRepay} okText="Record">
        <Form layout="vertical" form={repayForm}>
          <Form.Item label="Loan" >
            <Input value={repayLoan ? (repayLoan.number || `${repayLoan.borrower_name}`) : ''} disabled />
          </Form.Item>
          <Form.Item name="payment_date" label="Payment Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="amount" label="Amount" rules={[{ required: true }]}> 
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default LoansList;
