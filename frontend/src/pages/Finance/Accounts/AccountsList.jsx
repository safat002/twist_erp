import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
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
  ApartmentOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useCompany } from '../../../contexts/CompanyContext';
import {
  createAccount,
  deleteAccount,
  fetchAccounts,
  updateAccount,
} from '../../../services/finance';

const ACCOUNT_TYPES = [
  { label: 'Asset', value: 'ASSET' },
  { label: 'Liability', value: 'LIABILITY' },
  { label: 'Equity', value: 'EQUITY' },
  { label: 'Revenue', value: 'REVENUE' },
  { label: 'Expense', value: 'EXPENSE' },
];

const AccountsList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [summary, setSummary] = useState({ total: 0, balances: {} });
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [form] = Form.useForm();

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const { data } = await fetchAccounts();
      setAccounts(Array.isArray(data?.results) ? data.results : []);
      if (data?.summary) {
        setSummary(data.summary);
      }
    } catch (error) {
      console.warn('Failed to load accounts', error?.message);
      message.error('Unable to load chart of accounts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentCompany?.id) {
      loadAccounts();
    }
  }, [currentCompany?.id]);

  const openCreateModal = () => {
    setEditingAccount(null);
    form.resetFields();
    setModalVisible(true);
  };

  const openEditModal = (record) => {
    setEditingAccount(record);
    form.setFieldsValue({
      code: record.code,
      name: record.name,
      account_type: record.account_type,
      currency: record.currency,
      parent_account: record.parent_account,
      allow_direct_posting: record.allow_direct_posting,
      is_active: record.is_active,
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    try {
      if (editingAccount) {
        await updateAccount(editingAccount.id, values);
        message.success('Account updated successfully.');
      } else {
        await createAccount(values);
        message.success('Account created successfully.');
      }
      setModalVisible(false);
      loadAccounts();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to save account.');
    }
  };

  const handleDelete = (record) => {
    Modal.confirm({
      title: `Delete ${record.code}?`,
      content: 'This action cannot be undone and is only allowed for unused accounts.',
      okType: 'danger',
      okText: 'Delete',
      onOk: async () => {
        try {
          await deleteAccount(record.id);
          message.success('Account deleted.');
          loadAccounts();
        } catch (error) {
          message.error(error?.response?.data?.detail || 'Unable to delete account.');
        }
      },
    });
  };

  const columns = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
      width: 120,
      sorter: (a, b) => a.code.localeCompare(b.code),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name) => <span>{name}</span>,
    },
    {
      title: 'Type',
      dataIndex: 'account_type',
      key: 'account_type',
      width: 130,
      render: (type) => <Tag color="blue">{type}</Tag>,
      filters: ACCOUNT_TYPES.map((item) => ({ text: item.label, value: item.value })),
      onFilter: (value, record) => record.account_type === value,
    },
    {
      title: 'Parent',
      dataIndex: 'parent_account_display',
      key: 'parent_account',
      width: 200,
      render: (parent) => (parent ? `${parent.code} · ${parent.name}` : '—'),
    },
    {
      title: 'Balance',
      dataIndex: 'current_balance',
      key: 'balance',
      width: 140,
      align: 'right',
      render: (value) => (Number(value || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      title: 'Active',
      dataIndex: 'is_active',
      key: 'active',
      width: 100,
      render: (active) => <Tag color={active ? 'green' : 'red'}>{active ? 'Yes' : 'No'}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 140,
      render: (_, record) => (
        <Space size="middle">
          <Button icon={<EditOutlined />} type="text" onClick={() => openEditModal(record)} />
          <Button
            icon={<DeleteOutlined />}
            type="text"
            danger
            onClick={() => handleDelete(record)}
          />
        </Space>
      ),
    },
  ];

  const parentOptions = useMemo(
    () =>
      accounts.map((account) => ({
        value: account.id,
        label: `${account.code} · ${account.name}`,
      })),
    [accounts],
  );

  return (
    <div>
      <Space align="center" style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <ApartmentOutlined style={{ fontSize: 24 }} />
          <span style={{ fontSize: 18, fontWeight: 600 }}>Chart of Accounts</span>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadAccounts} disabled={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            New Account
          </Button>
        </Space>
      </Space>

      <Space style={{ marginBottom: 16 }}>
        <Card bordered={false} style={{ minWidth: 200 }}>
          <Statistic title="Total Accounts" value={summary?.total || 0} />
        </Card>
        <Card bordered={false} style={{ minWidth: 200 }}>
          <Statistic
            title="Total Assets"
            value={summary?.balances?.ASSET || 0}
            precision={2}
          />
        </Card>
        <Card bordered={false} style={{ minWidth: 200 }}>
          <Statistic
            title="Total Liabilities"
            value={summary?.balances?.LIABILITY || 0}
            precision={2}
          />
        </Card>
      </Space>

      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={accounts}
          columns={columns}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingAccount ? 'Edit Account' : 'Create Account'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="code"
            label="Account Code"
            rules={[{ required: true, message: 'Please enter account code' }]}
          >
            <Input placeholder="e.g. 1100" />
          </Form.Item>
          <Form.Item
            name="name"
            label="Account Name"
            rules={[{ required: true, message: 'Please enter account name' }]}
          >
            <Input placeholder="e.g. Accounts Receivable" />
          </Form.Item>
          <Form.Item
            name="account_type"
            label="Account Type"
            rules={[{ required: true, message: 'Select an account type' }]}
          >
            <Select options={ACCOUNT_TYPES} />
          </Form.Item>
          <Form.Item name="currency" label="Currency" initialValue="BDT">
            <Input placeholder="BDT" />
          </Form.Item>
          <Form.Item name="parent_account" label="Parent Account">
            <Select options={parentOptions} allowClear showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="allow_direct_posting" label="Allow Direct Posting" initialValue>
            <Select
              options={[
                { label: 'Yes', value: true },
                { label: 'No', value: false },
              ]}
            />
          </Form.Item>
          <Form.Item name="is_active" label="Active" initialValue>
            <Select
              options={[
                { label: 'Active', value: true },
                { label: 'Inactive', value: false },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AccountsList;
