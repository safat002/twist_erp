import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Divider,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  message,
} from 'antd';
import {
  BankOutlined,
  DollarOutlined,
  PlusOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import api from '../../../services/api';
import {
  createPayment,
  fetchAccounts,
  fetchInvoices,
  fetchPayments,
  postPayment,
} from '../../../services/finance';

const PAYMENT_TYPES = [
  { label: 'Customer Receipt', value: 'RECEIPT' },
  { label: 'Supplier Payment', value: 'PAYMENT' },
];

const PAYMENT_METHODS = [
  { label: 'Cash', value: 'CASH' },
  { label: 'Bank Transfer', value: 'BANK' },
  { label: 'Cheque', value: 'CHEQUE' },
  { label: 'Card', value: 'CARD' },
  { label: 'Mobile Payment', value: 'MOBILE' },
];

const PaymentsList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [payments, setPayments] = useState([]);
  const [summary, setSummary] = useState({});
  const [accounts, setAccounts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [openInvoices, setOpenInvoices] = useState([]);
  const [filterType, setFilterType] = useState('ALL');
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const loadLookups = async () => {
    try {
      const [{ data: accountData }, { data: customerData }, { data: supplierData }] = await Promise.all([
        fetchAccounts(),
        api.get('/api/v1/sales/customers/'),
        api.get('/api/v1/procurement/suppliers/'),
      ]);
      setAccounts(Array.isArray(accountData?.results) ? accountData.results : []);
      setCustomers(Array.isArray(customerData?.results) ? customerData.results : []);
      setSuppliers(Array.isArray(supplierData?.results) ? supplierData.results : []);
    } catch (error) {
      console.warn('Failed to load payment lookups', error?.message);
      message.error('Unable to load customers or suppliers.');
    }
  };

  const loadInvoices = async () => {
    try {
      const { data } = await fetchInvoices();
      const list = Array.isArray(data?.results) ? data.results : [];
      setOpenInvoices(list.filter((invoice) => Number(invoice.balance_due || 0) > 0));
    } catch (error) {
      console.warn('Failed to load invoices for allocations', error?.message);
    }
  };

  const loadPayments = async (params = {}) => {
    try {
      setLoading(true);
      const { data } = await fetchPayments(params);
      setPayments(Array.isArray(data?.results) ? data.results : []);
      setSummary(data?.summary || {});
    } catch (error) {
      console.warn('Failed to load payments', error?.message);
      message.error('Unable to load payments.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentCompany?.id) {
      loadLookups();
      loadInvoices();
      loadPayments();
    }
  }, [currentCompany?.id]);

  useEffect(() => {
    if (!currentCompany?.id) return;
    if (filterType === 'ALL') {
      loadPayments();
    } else {
      loadPayments({ type: filterType });
    }
  }, [filterType]);

  const bankAccounts = useMemo(
    () =>
      accounts
        .filter((account) => account.is_bank_account)
        .map((account) => ({ value: account.id, label: `${account.code} · ${account.name}` })),
    [accounts],
  );

  const customerOptions = useMemo(
    () => customers.map((customer) => ({ value: customer.id, label: customer.name })),
    [customers],
  );

  const supplierOptions = useMemo(
    () => suppliers.map((supplier) => ({ value: supplier.id, label: supplier.name })),
    [suppliers],
  );

  const invoiceOptions = useMemo(
    () =>
      openInvoices.map((invoice) => ({
        value: invoice.id,
        label: `${invoice.invoice_number || 'Draft'} · ${invoice.invoice_type} · Due ${dayjs(
          invoice.due_date,
        ).format('YYYY-MM-DD')} · Balance ${invoice.balance_due}`,
        invoice,
      })),
    [openInvoices],
  );

  const handleCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      payment_type: 'RECEIPT',
      payment_method: 'BANK',
      payment_date: dayjs(),
      allocations: [],
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    const payload = {
      ...values,
      payment_date: values.payment_date.format('YYYY-MM-DD'),
      partner_type: values.payment_type === 'RECEIPT' ? 'customer' : 'supplier',
      allocations: (values.allocations || []).map((allocation) => ({
        invoice: allocation.invoice,
        allocated_amount: allocation.allocated_amount,
      })),
      currency: currentCompany?.currency_code || 'BDT',
    };
    try {
      await createPayment(payload);
      message.success('Payment recorded.');
      setModalVisible(false);
      loadPayments(filterType === 'ALL' ? {} : { type: filterType });
      loadInvoices();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to record payment.');
    }
  };

  const handlePost = async (payment) => {
    try {
      await postPayment(payment.id);
      message.success('Payment posted successfully.');
      loadPayments(filterType === 'ALL' ? {} : { type: filterType });
      loadInvoices();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to post payment.');
    }
  };

  const partnerName = (record) => {
    if (record.payment_type === 'RECEIPT') {
      return customers.find((customer) => customer.id === record.partner_id)?.name || '—';
    }
    return suppliers.find((supplier) => supplier.id === record.partner_id)?.name || '—';
  };

  const columns = [
    {
      title: 'Payment #',
      dataIndex: 'payment_number',
      key: 'payment_number',
      render: (value) => value || 'Draft',
    },
    {
      title: 'Type',
      dataIndex: 'payment_type',
      key: 'type',
      render: (type) => (
        <Tag color={type === 'RECEIPT' ? 'green' : 'volcano'}>
          {type === 'RECEIPT' ? 'Receipt' : 'Payment'}
        </Tag>
      ),
    },
    {
      title: 'Partner',
      key: 'partner',
      render: (_, record) => partnerName(record),
    },
    {
      title: 'Date',
      dataIndex: 'payment_date',
      key: 'date',
      render: (value) => dayjs(value).format('YYYY-MM-DD'),
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right',
      render: (value) => (Number(value || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      title: 'Method',
      dataIndex: 'payment_method',
      key: 'method',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'POSTED' ? 'green' : 'default'}>{status}</Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) =>
        record.status === 'POSTED' ? (
          <Tag color="green">Posted</Tag>
        ) : (
          <Button type="link" onClick={() => handlePost(record)}>
            Post
          </Button>
        ),
    },
  ];

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <BankOutlined style={{ fontSize: 24 }} />
          <span style={{ fontSize: 18, fontWeight: 600 }}>Cash & Bank Movements</span>
        </Space>
        <Space>
          <Select
            value={filterType}
            onChange={setFilterType}
            options={[
              { label: 'All', value: 'ALL' },
              { label: 'Receipts', value: 'RECEIPT' },
              { label: 'Payments', value: 'PAYMENT' },
            ]}
            style={{ width: 160 }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => loadPayments(filterType === 'ALL' ? {} : { type: filterType })}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            New Entry
          </Button>
        </Space>
      </Space>

      <Space style={{ marginBottom: 16 }}>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Receipts" value={summary?.receipts || 0} precision={2} prefix={<DollarOutlined />} />
        </Card>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Disbursements" value={summary?.disbursements || 0} precision={2} prefix={<DollarOutlined />} />
        </Card>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Entries" value={summary?.count || 0} />
        </Card>
      </Space>

      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          dataSource={payments}
          loading={loading}
          columns={columns}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      <Modal
        title="Record Payment"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={720}
        onOk={() => form.submit()}
      >
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item
            name="payment_type"
            label="Transaction Type"
            rules={[{ required: true, message: 'Select transaction type' }]}
          >
            <Select options={PAYMENT_TYPES} />
          </Form.Item>
          <Space size="large" style={{ width: '100%' }}>
            <Form.Item
              name="payment_date"
              label="Payment Date"
              style={{ flex: 1 }}
              rules={[{ required: true, message: 'Select payment date' }]}
            >
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="payment_method"
              label="Method"
              style={{ flex: 1 }}
              rules={[{ required: true, message: 'Select payment method' }]}
            >
              <Select options={PAYMENT_METHODS} />
            </Form.Item>
          </Space>
          <Form.Item
            name="bank_account"
            label="Cash/Bank Account"
            rules={[{ required: true, message: 'Select cash/bank account' }]}
          >
            <Select options={bankAccounts} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item
            name="amount"
            label="Amount"
            rules={[{ required: true, message: 'Enter amount' }]}
          >
            <Input type="number" min="0" step="0.01" />
          </Form.Item>
          <Form.Item
            shouldUpdate
            noStyle
          >
            {({ getFieldValue }) => {
              const type = getFieldValue('payment_type') || 'RECEIPT';
              return (
                <Form.Item
                  name="partner_id"
                  label={type === 'RECEIPT' ? 'Customer' : 'Supplier'}
                  rules={[{ required: true, message: 'Select partner' }]}
                >
                  <Select
                    options={type === 'RECEIPT' ? customerOptions : supplierOptions}
                    showSearch
                    optionFilterProp="label"
                  />
                </Form.Item>
              );
            }}
          </Form.Item>
          <Form.Item name="reference" label="Reference">
            <Input placeholder="Optional reference" />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={2} placeholder="Internal notes" />
          </Form.Item>

          <Divider orientation="left">Apply against invoices</Divider>
          <Form.List name="allocations">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...field }) => (
                  <Space key={key} align="baseline" style={{ display: 'flex', marginBottom: 12 }}>
                    <Form.Item
                      {...field}
                      name={[name, 'invoice']}
                      rules={[{ required: true, message: 'Select invoice' }]}
                    >
                      <Select
                        placeholder="Invoice"
                        showSearch
                        optionFilterProp="label"
                        options={invoiceOptions}
                        style={{ width: 300 }}
                      />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[name, 'allocated_amount']}
                      rules={[{ required: true, message: 'Enter amount' }]}
                    >
                      <Input type="number" step="0.01" placeholder="Amount" style={{ width: 140 }} />
                    </Form.Item>
                    <Button type="link" danger onClick={() => remove(name)}>
                      Remove
                    </Button>
                  </Space>
                ))}
                <Button type="dashed" icon={<PlusOutlined />} block onClick={() => add()}>
                  Add Allocation
                </Button>
              </>
            )}
          </Form.List>
          <Divider orientation="left">
            <ThunderboltOutlined /> Automation
          </Divider>
          <p style={{ color: '#888' }}>
            Posted payments automatically reduce the balance on linked invoices and update cash
            ledgers.
          </p>
        </Form>
      </Modal>
    </div>
  );
};

export default PaymentsList;
