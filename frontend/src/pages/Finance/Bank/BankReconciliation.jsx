import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, DatePicker, Form, Input, Select, Space, Table, Tag, message } from 'antd';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import { fetchAccounts } from '../../../services/finance';
import { fetchBankStatements, createBankStatement, matchStatementLine } from '../../../services/finance';

const STATUS_COLORS = { IMPORTED: 'blue', PARTIAL: 'orange', RECONCILED: 'green' };

const BankReconciliation = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [statements, setStatements] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [form] = Form.useForm();

  const bankAccounts = useMemo(
    () => accounts.filter((a) => a.is_bank_account).map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` })),
    [accounts]
  );

  const load = async () => {
    try {
      setLoading(true);
      const [{ data: acc }, { data: stmts }] = await Promise.all([fetchAccounts(), fetchBankStatements()]);
      setAccounts(Array.isArray(acc?.results) ? acc.results : []);
      setStatements(Array.isArray(stmts?.results) ? stmts.results : stmts);
    } catch (err) {
      message.error('Unable to load bank statements');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (currentCompany?.id) load(); }, [currentCompany?.id]);

  const columns = [
    { title: 'Account', dataIndex: ['bank_account'], key: 'account', render: (_, r) => r.bank_account },
    { title: 'Date', dataIndex: 'statement_date', key: 'date' },
    { title: 'Opening', dataIndex: 'opening_balance', key: 'opening', align: 'right' },
    { title: 'Closing', dataIndex: 'closing_balance', key: 'closing', align: 'right' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
  ];

  const handleCreate = async (values) => {
    try {
      const payload = {
        bank_account: values.bank_account,
        statement_date: values.statement_date.format('YYYY-MM-DD'),
        opening_balance: values.opening_balance,
        closing_balance: values.opening_balance,
        currency: values.currency || 'BDT',
        imported_filename: values.imported_filename || '',
      };
      await createBankStatement(payload);
      message.success('Statement created');
      form.resetFields();
      load();
    } catch (err) {
      message.error('Failed to create statement');
    }
  };

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>Bank Reconciliation</span>
      </Space>
      <Card style={{ marginBottom: 16 }}>
        <Form layout="inline" form={form} onFinish={handleCreate}>
          <Form.Item name="bank_account" label="Bank Account" rules={[{ required: true }]}>
            <Select options={bankAccounts} showSearch optionFilterProp="label" style={{ width: 260 }} />
          </Form.Item>
          <Form.Item name="statement_date" label="Statement Date" rules={[{ required: true }]}> 
            <DatePicker style={{ width: 180 }} />
          </Form.Item>
          <Form.Item name="opening_balance" label="Opening" rules={[{ required: true }]}> 
            <Input type="number" step="0.01" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="currency" label="Currency" initialValue="BDT"> 
            <Input style={{ width: 100 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Create</Button>
          </Form.Item>
        </Form>
      </Card>
      <Card>
        <Table rowKey="id" loading={loading} dataSource={statements} columns={columns} pagination={{ pageSize: 12 }} />
      </Card>
    </div>
  );
};

export default BankReconciliation;

