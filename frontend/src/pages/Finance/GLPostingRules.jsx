import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Form,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { useCompany } from '../../contexts/CompanyContext';
import {
  fetchAccounts,
  fetchInventoryPostingRules,
  createInventoryPostingRule,
  updateInventoryPostingRule,
  deleteInventoryPostingRule,
} from '../../services/finance';
import api from '../../services/api';

const { Text } = Typography;

const TRANSACTION_OPTIONS = [
  { label: 'Receipt', value: 'RECEIPT' },
  { label: 'Issue', value: 'ISSUE' },
  { label: 'Transfer Out', value: 'TRANSFER_OUT' },
  { label: 'Transfer In', value: 'TRANSFER_IN' },
  { label: 'Adjustment', value: 'ADJUSTMENT' },
  { label: 'Scrap', value: 'SCRAP' },
];

const WAREHOUSE_TYPES = [
  { label: 'Any', value: '' },
  { label: 'Main', value: 'MAIN' },
  { label: 'Transit', value: 'TRANSIT' },
  { label: 'Retail', value: 'RETAIL' },
  { label: 'Virtual', value: 'VIRTUAL' },
];

const GLPostingRules = () => {
  const { currentCompany } = useCompany();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [budgetItems, setBudgetItems] = useState([]);
  const [inventoryItems, setInventoryItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [form] = Form.useForm();

  useEffect(() => {
    if (!currentCompany?.id) return;
    loadRules();
    loadReferences();
  }, [currentCompany?.id]);

  const filterOption = (input, option) =>
    ((option?.label || '') + '').toLowerCase().includes((input || '').toLowerCase());

  const loadRules = async () => {
    try {
      setLoading(true);
      const { data } = await fetchInventoryPostingRules();
      setRules(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load GL rules', error);
      setRules([]);
      message.error('Unable to load GL posting rules.');
    } finally {
      setLoading(false);
    }
  };

  const extractList = (payload) => {
    if (!payload) return [];
    if (Array.isArray(payload)) {
      return payload;
    }
    if (Array.isArray(payload.results)) {
      return payload.results;
    }
    return [];
  };

  const loadReferences = async () => {
    try {
      const [
        accountsRes,
        warehousesRes,
        budgetItemsRes,
        categoriesRes,
        itemsRes,
      ] = await Promise.all([
        fetchAccounts({ limit: 500 }),
        api.get('/api/v1/inventory/warehouses/'),
        api.get('/api/v1/budgets/item-codes/'),
        api.get('/api/v1/inventory/product-categories/'),
        api.get('/api/v1/inventory/items/?limit=200'),
      ]);
      setAccounts(extractList(accountsRes?.data));
      setWarehouses(extractList(warehousesRes?.data));
      setBudgetItems(extractList(budgetItemsRes?.data));
      setCategories(extractList(categoriesRes?.data));
      setInventoryItems(extractList(itemsRes?.data));
    } catch (error) {
      console.error('Failed to load GL references', error);
    }
  };

  const openForm = (rule) => {
    setEditingRule(rule || null);
    if (rule) {
      form.setFieldsValue({
        ...rule,
        budget_item: rule.budget_item,
        item: rule.item,
      });
    } else {
      form.resetFields();
      form.setFieldsValue({ is_active: true, priority: 100 });
    }
    setModalVisible(true);
  };

  const closeForm = () => {
    setModalVisible(false);
    setEditingRule(null);
  };

  const handleSubmit = async (values) => {
    setModalLoading(true);
    try {
      if (editingRule) {
        await updateInventoryPostingRule(editingRule.id, values);
        message.success('GL posting rule updated.');
      } else {
        await createInventoryPostingRule(values);
        message.success('GL posting rule created.');
      }
      closeForm();
      loadRules();
    } catch (error) {
      console.error('Failed to save GL posting rule', error);
      message.error(error?.response?.data?.detail || 'Unable to save GL posting rule.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleDelete = (rule) => {
    Modal.confirm({
      title: 'Delete GL Posting Rule',
      content: 'This action cannot be undone. Are you sure?',
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteInventoryPostingRule(rule.id);
          message.success('Rule deleted.');
          loadRules();
        } catch (error) {
          console.error('Failed to delete rule', error);
          message.error('Unable to delete rule.');
        }
      },
    });
  };

  const categoryOptions = useMemo(
    () =>
      categories.map((cat) => ({
        label: `${cat.code || cat.name}`,
        value: cat.id,
      })),
    [categories],
  );

  const ruleColumns = [
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
    },
    {
      title: 'Transaction',
      dataIndex: 'transaction_type',
      key: 'transaction_type',
      render: (value) => value || 'Any',
    },
    {
      title: 'Budget Item',
      dataIndex: 'budget_item_code',
      key: 'budget_item_code',
      render: (value) => value || '-',
    },
    {
      title: 'Inventory Item',
      dataIndex: 'item_code',
      key: 'item_code',
      render: (value) => value || '-',
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (_, record) => record.category_code || '-',
    },
    {
      title: 'Sub-category',
      dataIndex: 'sub_category',
      key: 'sub_category',
      render: (_, record) => record.sub_category_code || '-',
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_code',
      key: 'warehouse_code',
      render: (value) => value || 'Any',
    },
    {
      title: 'Warehouse Type',
      dataIndex: 'warehouse_type',
      key: 'warehouse_type',
      render: (value) => value || 'Any',
    },
    {
      title: 'Inventory Account',
      dataIndex: 'inventory_account_code',
      key: 'inventory_account_code',
    },
    {
      title: 'COGS Account',
      dataIndex: 'cogs_account_code',
      key: 'cogs_account_code',
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (value) => (
        <Tag color={value ? 'green' : 'default'}>{value ? 'Active' : 'Inactive'}</Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} type="link" onClick={() => openForm(record)}>
            Edit
          </Button>
          <Button
            icon={<DeleteOutlined />}
            type="link"
            danger
            onClick={() => handleDelete(record)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space align="center" style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <Text strong style={{ fontSize: 20 }}>
          GL Posting Rules
        </Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openForm()}>
          New Rule
        </Button>
      </Space>
      <Card bordered={false}>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={rules}
          columns={ruleColumns}
          pagination={{ pageSize: 12 }}
        />
      </Card>

      <Modal
        title={editingRule ? 'Edit GL Posting Rule' : 'New GL Posting Rule'}
        open={modalVisible}
        onCancel={closeForm}
        onOk={() => form.submit()}
        confirmLoading={modalLoading}
        destroyOnClose
        okText="Save"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ is_active: true, priority: 100 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="Priority" name="priority">
                <InputNumber min={1} max={999} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Transaction Type" name="transaction_type">
                <Select options={[{ label: 'Any', value: '' }, ...TRANSACTION_OPTIONS]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="budget_item" label="Budget Item">
            <Select
              showSearch
              allowClear
              placeholder="Budget Item"
              options={budgetItems.map((item) => ({
                label: `${item.code || ''} ${item.name || ''}`.trim(),
                value: item.id,
              }))}
              filterOption={filterOption}
            />
          </Form.Item>
          <Form.Item name="item" label="Inventory Item">
            <Select
              showSearch
              allowClear
              placeholder="Inventory Item"
              options={inventoryItems.map((item) => ({
                label: `${item.code || ''} ${item.name || ''}`.trim(),
                value: item.id,
              }))}
              filterOption={filterOption}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="Category">
                <Select options={[{ label: 'Any', value: null }, ...categoryOptions]} allowClear />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="sub_category" label="Sub-category">
                <Select options={[{ label: 'Any', value: null }, ...categoryOptions]} allowClear />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="warehouse" label="Warehouse">
                <Select
                  allowClear
                  placeholder="Warehouse"
                  options={warehouses.map((wh) => ({
                    label: `${wh.code || ''} ${wh.name || ''}`.trim(),
                    value: wh.id,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="warehouse_type" label="Warehouse Type">
                <Select options={WAREHOUSE_TYPES} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="inventory_account" label="Inventory Account" rules={[{ required: true }]}>
            <Select
              showSearch
              options={accounts.map((acct) => ({
                label: `${acct.code || ''} ${acct.name || ''}`.trim(),
                value: acct.id,
              }))}
              filterOption={filterOption}
            />
          </Form.Item>
          <Form.Item name="cogs_account" label="COGS Account">
            <Select
              showSearch
              allowClear
              options={accounts.map((acct) => ({
                label: `${acct.code || ''} ${acct.name || ''}`.trim(),
                value: acct.id,
              }))}
              filterOption={filterOption}
            />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch checkedChildren="Active" unCheckedChildren="Inactive" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default GLPostingRules;
