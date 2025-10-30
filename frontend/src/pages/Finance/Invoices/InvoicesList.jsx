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
  CheckCircleOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import api from '../../../services/api';
import {
  createInvoice,
  fetchAccounts,
  fetchInvoices,
  postInvoice,
} from '../../../services/finance';

const INVOICE_TYPE_OPTIONS = [
  { label: 'Sales Invoice (AR)', value: 'AR' },
  { label: 'Supplier Bill (AP)', value: 'AP' },
];

const InvoiceList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [invoices, setInvoices] = useState([]);
  const [summary, setSummary] = useState({});
  const [forecast, setForecast] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [filterType, setFilterType] = useState('AR');
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
      console.warn('Failed to load invoice lookups', error?.message);
      message.error('Unable to load customers or suppliers.');
    }
  };

  const loadInvoices = async (params = {}) => {
    try {
      setLoading(true);
      const { data } = await fetchInvoices(params);
      setInvoices(Array.isArray(data?.results) ? data.results : []);
      setSummary(data?.summary || {});
      setForecast(Array.isArray(data?.forecast) ? data.forecast : []);
    } catch (error) {
      console.warn('Failed to load invoices', error?.message);
      message.error('Unable to load invoices.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentCompany?.id) {
      loadLookups();
      loadInvoices({ type: filterType });
    }
  }, [currentCompany?.id]);

  useEffect(() => {
    if (currentCompany?.id) {
      loadInvoices({ type: filterType });
    }
  }, [filterType]);

  const customerOptions = useMemo(
    () => customers.map((customer) => ({ value: customer.id, label: customer.name })),
    [customers],
  );

  const supplierOptions = useMemo(
    () => suppliers.map((supplier) => ({ value: supplier.id, label: supplier.name })),
    [suppliers],
  );

  const revenueAccounts = useMemo(
    () =>
      accounts
        .filter((account) => account.account_type === 'REVENUE')
        .map((account) => ({ value: account.id, label: `${account.code} · ${account.name}` })),
    [accounts],
  );

  const expenseAccounts = useMemo(
    () =>
      accounts
        .filter((account) => account.account_type !== 'REVENUE')
        .map((account) => ({ value: account.id, label: `${account.code} · ${account.name}` })),
    [accounts],
  );

  const handleCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      invoice_type: filterType,
      invoice_date: dayjs(),
      due_date: dayjs().add(7, 'day'),
      lines: [
        { description: '', quantity: 1, unit_price: 0, tax_rate: 0, discount_percent: 0, account: undefined },
      ],
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    const payload = {
      ...values,
      invoice_date: values.invoice_date.format('YYYY-MM-DD'),
      due_date: values.due_date.format('YYYY-MM-DD'),
      partner_type: values.invoice_type === 'AR' ? 'customer' : 'supplier',
    };
    try {
      await createInvoice(payload);
      message.success('Invoice created.');
      setModalVisible(false);
      loadInvoices({ type: filterType });
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to create invoice.');
    }
  };

  const handlePost = async (invoice) => {
    try {
      await postInvoice(invoice.id);
      message.success('Invoice posted to ledger.');
      loadInvoices({ type: filterType });
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to post invoice.');
    }
  };

  const partnerName = (record) => {
    if (record.invoice_type === 'AR') {
      return customers.find((customer) => customer.id === record.partner_id)?.name || '—';
    }
    return suppliers.find((supplier) => supplier.id === record.partner_id)?.name || '—';
  };

  const columns = [
    {
      title: 'Invoice #',
      dataIndex: 'invoice_number',
      key: 'invoice_number',
      render: (value) => value || 'Pending',
    },
    {
      title: 'Type',
      dataIndex: 'invoice_type',
      key: 'type',
      render: (type) => <Tag color={type === 'AR' ? 'blue' : 'volcano'}>{type}</Tag>,
    },
    {
      title: 'Partner',
      key: 'partner',
      render: (_, record) => partnerName(record),
    },
    {
      title: 'Invoice Date',
      dataIndex: 'invoice_date',
      key: 'invoice_date',
      render: (value) => dayjs(value).format('YYYY-MM-DD'),
    },
    {
      title: 'Due Date',
      dataIndex: 'due_date',
      key: 'due_date',
      render: (value) => dayjs(value).format('YYYY-MM-DD'),
    },
    {
      title: 'Total',
      dataIndex: 'total_amount',
      key: 'total',
      align: 'right',
      render: (value) => (Number(value || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      title: 'Balance',
      dataIndex: 'balance_due',
      key: 'balance_due',
      align: 'right',
      render: (value) => (Number(value || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'PAID' ? 'green' : status === 'POSTED' ? 'blue' : 'default'}>
          {status}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) =>
        record.status === 'POSTED' || record.status === 'PAID' ? (
          <Tag icon={<CheckCircleOutlined />} color="green">
            Posted
          </Tag>
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
          <FileTextOutlined style={{ fontSize: 24 }} />
          <span style={{ fontSize: 18, fontWeight: 600 }}>Invoices & Bills</span>
        </Space>
        <Space>
          <Select
            value={filterType}
            onChange={setFilterType}
            options={INVOICE_TYPE_OPTIONS}
            style={{ width: 200 }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => loadInvoices({ type: filterType })}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            New Invoice
          </Button>
        </Space>
      </Space>

      <Space style={{ marginBottom: 16 }}>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic
            title="Total Outstanding"
            value={summary?.total_outstanding || 0}
            precision={2}
          />
        </Card>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Overdue" value={summary?.total_overdue || 0} precision={2} />
        </Card>
      </Space>

      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={invoices}
          columns={columns}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      {forecast.length ? (
        <Card title="Cash Flow Forecast" style={{ marginTop: 16 }}>
          <Table
            dataSource={forecast.map((item, index) => ({ key: index, ...item }))}
            columns={[
              { title: 'Month', dataIndex: 'month', key: 'month' },
              { title: 'Status', dataIndex: 'status', key: 'status' },
              {
                title: 'Amount',
                dataIndex: 'amount',
                key: 'amount',
                align: 'right',
                render: (value) => (Number(value || 0)).toLocaleString(),
              },
            ]}
            pagination={false}
            size="small"
          />
        </Card>
      ) : null}

      <Modal
        title="Create Invoice"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={800}
        onOk={() => form.submit()}
      >
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item
            name="invoice_type"
            label="Invoice Type"
            rules={[{ required: true, message: 'Select invoice type' }]}
          >
            <Select options={INVOICE_TYPE_OPTIONS} />
          </Form.Item>
          <Space style={{ width: '100%' }} size="large">
            <Form.Item
              name="invoice_date"
              label="Invoice Date"
              style={{ flex: 1 }}
              rules={[{ required: true, message: 'Select invoice date' }]}
            >
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="due_date"
              label="Due Date"
              style={{ flex: 1 }}
              rules={[{ required: true, message: 'Select due date' }]}
            >
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item
            shouldUpdate
            noStyle
          >
            {({ getFieldValue }) => {
              const type = getFieldValue('invoice_type') || 'AR';
              return (
                <Form.Item
                  name="partner_id"
                  label={type === 'AR' ? 'Customer' : 'Supplier'}
                  rules={[{ required: true, message: 'Select partner' }]}
                >
                  <Select
                    options={type === 'AR' ? customerOptions : supplierOptions}
                    showSearch
                    optionFilterProp="label"
                  />
                </Form.Item>
              );
            }}
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} placeholder="Optional notes" />
          </Form.Item>

          <Divider orientation="left">Lines</Divider>
          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...field }) => (
                  <Space key={key} align="baseline" style={{ display: 'flex', marginBottom: 16 }}>
                    <Form.Item
                      {...field}
                      name={[name, 'description']}
                      rules={[{ required: true, message: 'Enter description' }]}
                    >
                      <Input placeholder="Description" style={{ width: 220 }} />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'quantity']} initialValue={1}>
                      <Input placeholder="Qty" type="number" step="0.01" style={{ width: 80 }} />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'unit_price']} initialValue={0}>
                      <Input placeholder="Unit Price" type="number" step="0.01" style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'tax_rate']} initialValue={0}>
                      <Input placeholder="Tax %" type="number" step="0.01" style={{ width: 80 }} />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'discount_percent']} initialValue={0}>
                      <Input placeholder="Disc %" type="number" step="0.01" style={{ width: 80 }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[name, 'account']}
                      rules={[{ required: true, message: 'Select account' }]}
                    >
                      <Select
                        showSearch
                        placeholder="Account"
                        optionFilterProp="label"
                        style={{ width: 200 }}
                        options={(form.getFieldValue('invoice_type') === 'AP'
                          ? expenseAccounts
                          : revenueAccounts)}
                      />
                    </Form.Item>
                    {fields.length > 1 ? (
                      <Button type="link" danger onClick={() => remove(name)}>
                        Remove
                      </Button>
                    ) : null}
                  </Space>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add()}>
                  Add Line
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
};

export default InvoiceList;
