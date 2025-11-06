import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import valuationService from '../../../services/valuation';
import api from '../../../services/api';

const { Title, Text } = Typography;

const ValuationSettings = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [methods, setMethods] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingMethod, setEditingMethod] = useState(null);

  // Filters
  const [productFilter, setProductFilter] = useState(null);
  const [warehouseFilter, setWarehouseFilter] = useState(null);
  const [methodFilter, setMethodFilter] = useState(null);
  const [activeOnlyFilter, setActiveOnlyFilter] = useState(false);

  const [form] = Form.useForm();

  // Load data on mount and company change
  useEffect(() => {
    if (currentCompany) {
      loadData();
    }
  }, [currentCompany]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [methodsRes, productsRes, warehousesRes] = await Promise.all([
        valuationService.getValuationMethods(),
        api.get('/api/v1/inventory/products/'),
        api.get('/api/v1/inventory/warehouses/'),
      ]);

      setMethods(methodsRes?.results || methodsRes || []);
      setProducts(productsRes.data?.results || productsRes.data || []);
      setWarehouses(warehousesRes.data?.results || warehousesRes.data || []);
    } catch (error) {
      console.error('Failed to load valuation settings:', error);
      message.error(error?.response?.data?.detail || 'Failed to load valuation settings');
    } finally {
      setLoading(false);
    }
  };

  // Filtered methods based on active filters
  const filteredMethods = useMemo(() => {
    return (methods || []).filter((method) => {
      if (productFilter && method.product !== productFilter) return false;
      if (warehouseFilter && method.warehouse !== warehouseFilter) return false;
      if (methodFilter && method.valuation_method !== methodFilter) return false;
      if (activeOnlyFilter && !method.is_active) return false;
      return true;
    });
  }, [methods, productFilter, warehouseFilter, methodFilter, activeOnlyFilter]);

  // Calculate statistics
  const statistics = useMemo(() => {
    const total = methods.length;
    const active = methods.filter((m) => m.is_active).length;
    const methodCounts = {
      FIFO: methods.filter((m) => m.valuation_method === 'FIFO').length,
      LIFO: methods.filter((m) => m.valuation_method === 'LIFO').length,
      WEIGHTED_AVG: methods.filter((m) => m.valuation_method === 'WEIGHTED_AVG').length,
      STANDARD: methods.filter((m) => m.valuation_method === 'STANDARD').length,
    };

    return { total, active, ...methodCounts };
  }, [methods]);

  const handleCreate = () => {
    setEditingMethod(null);
    form.resetFields();
    form.setFieldsValue({
      valuation_method: 'FIFO',
      avg_period: 'PERPETUAL',
      allow_negative_inventory: false,
      prevent_cost_below_zero: true,
      effective_date: dayjs(),
      is_active: true,
    });
    setModalOpen(true);
  };

  const handleEdit = (record) => {
    setEditingMethod(record);
    form.setFieldsValue({
      ...record,
      effective_date: record.effective_date ? dayjs(record.effective_date) : dayjs(),
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        effective_date: values.effective_date ? values.effective_date.format('YYYY-MM-DD') : undefined,
      };

      if (editingMethod) {
        await valuationService.updateValuationMethod(editingMethod.id, payload);
        message.success('Valuation method updated successfully');
      } else {
        await valuationService.createValuationMethod(payload);
        message.success('Valuation method created successfully');
      }

      setModalOpen(false);
      form.resetFields();
      setEditingMethod(null);
      loadData();
    } catch (error) {
      if (error?.errorFields) {
        return; // Form validation error
      }
      message.error(error?.response?.data?.detail || 'Failed to save valuation method');
    }
  };

  const handleDelete = async (id) => {
    Modal.confirm({
      title: 'Delete Valuation Method',
      content: 'Are you sure you want to delete this valuation method? This action cannot be undone.',
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await valuationService.deleteValuationMethod(id);
          message.success('Valuation method deleted successfully');
          loadData();
        } catch (error) {
          message.error(error?.response?.data?.detail || 'Failed to delete valuation method');
        }
      },
    });
  };

  const handleToggleActive = async (record) => {
    try {
      await valuationService.patchValuationMethod(record.id, {
        is_active: !record.is_active,
      });
      message.success(`Valuation method ${!record.is_active ? 'activated' : 'deactivated'}`);
      loadData();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Failed to toggle status');
    }
  };

  const columns = [
    {
      title: 'Product',
      key: 'product',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.product_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.product_code}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Warehouse',
      key: 'warehouse',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.warehouse_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.warehouse_code}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Method',
      dataIndex: 'valuation_method',
      key: 'valuation_method',
      render: (value, record) => (
        <Tag
          color={valuationService.getMethodColor(value)}
          style={{
            fontSize: 12,
            fontWeight: 500,
            padding: '4px 10px',
          }}
        >
          {record.valuation_method_display}
        </Tag>
      ),
    },
    {
      title: 'Average Period',
      dataIndex: 'avg_period_display',
      key: 'avg_period',
      render: (value) => value || <Text type="secondary">N/A</Text>,
    },
    {
      title: 'Effective Date',
      dataIndex: 'effective_date',
      key: 'effective_date',
      render: (value) => value || <Text type="secondary">Not set</Text>,
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => (
        <Space>
          <Badge
            status={record.is_active ? 'success' : 'default'}
            text={record.is_active ? 'Active' : 'Inactive'}
          />
          {record.allow_negative_inventory && (
            <Tag color="orange" icon={<WarningOutlined />}>
              Neg. Inv
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Edit
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => handleToggleActive(record)}
          >
            {record.is_active ? 'Deactivate' : 'Activate'}
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  const selectedMethod = Form.useWatch('valuation_method', form);
  const showAvgPeriod = selectedMethod === 'WEIGHTED_AVG';

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ marginBottom: 0 }}>
            Valuation Settings
          </Title>
          <Text type="secondary">
            Configure inventory valuation methods per product and warehouse
          </Text>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            New Valuation Method
          </Button>
        </Col>
      </Row>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Configurations"
              value={statistics.total}
              prefix={<SettingOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Methods"
              value={statistics.active}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="FIFO Methods"
              value={statistics.FIFO}
              valueStyle={{ color: '#17a2b8' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Weighted Avg"
              value={statistics.WEIGHTED_AVG}
              valueStyle={{ color: '#28a745' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={6}>
            <Select
              allowClear
              showSearch
              placeholder="Filter by Product"
              style={{ width: '100%' }}
              value={productFilter}
              onChange={setProductFilter}
              options={products.map((p) => ({
                value: p.id,
                label: `${p.code} - ${p.name}`,
              }))}
              filterOption={(input, option) =>
                option.label.toLowerCase().includes(input.toLowerCase())
              }
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              allowClear
              showSearch
              placeholder="Filter by Warehouse"
              style={{ width: '100%' }}
              value={warehouseFilter}
              onChange={setWarehouseFilter}
              options={warehouses.map((w) => ({
                value: w.id,
                label: `${w.code} - ${w.name}`,
              }))}
              filterOption={(input, option) =>
                option.label.toLowerCase().includes(input.toLowerCase())
              }
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              allowClear
              placeholder="Filter by Method"
              style={{ width: '100%' }}
              value={methodFilter}
              onChange={setMethodFilter}
              options={valuationService.getValuationMethodChoices().map((choice) => ({
                value: choice.value,
                label: choice.label,
              }))}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Space>
              <Switch checked={activeOnlyFilter} onChange={setActiveOnlyFilter} />
              <Text>Active Only</Text>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Main Table */}
      <Card>
        {filteredMethods.length === 0 && !loading ? (
          <Alert
            type="info"
            showIcon
            message="No Valuation Methods Configured"
            description="Get started by creating a valuation method for your products and warehouses. Default FIFO method will be used for items without explicit configuration."
            action={
              <Button type="primary" size="small" onClick={handleCreate}>
                Create Method
              </Button>
            }
          />
        ) : (
          <Table
            dataSource={filteredMethods}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 15 }}
          />
        )}
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingMethod ? 'Edit Valuation Method' : 'New Valuation Method'}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
          setEditingMethod(null);
        }}
        onOk={handleSave}
        okText="Save"
        destroyOnClose
        width={700}
      >
        <Form layout="vertical" form={form}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Product"
                name="product"
                rules={[{ required: true, message: 'Please select a product' }]}
              >
                <Select
                  showSearch
                  placeholder="Select product"
                  options={products.map((p) => ({
                    value: p.id,
                    label: `${p.code} - ${p.name}`,
                  }))}
                  filterOption={(input, option) =>
                    option.label.toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Warehouse"
                name="warehouse"
                rules={[{ required: true, message: 'Please select a warehouse' }]}
              >
                <Select
                  showSearch
                  placeholder="Select warehouse"
                  options={warehouses.map((w) => ({
                    value: w.id,
                    label: `${w.code} - ${w.name}`,
                  }))}
                  filterOption={(input, option) =>
                    option.label.toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Valuation Method"
                name="valuation_method"
                rules={[{ required: true, message: 'Please select a method' }]}
              >
                <Select
                  placeholder="Select method"
                  options={valuationService.getValuationMethodChoices()}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              {showAvgPeriod && (
                <Form.Item label="Average Period" name="avg_period">
                  <Select
                    placeholder="Select period"
                    options={valuationService.getAveragePeriodChoices()}
                  />
                </Form.Item>
              )}
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Effective Date"
                name="effective_date"
                rules={[{ required: true, message: 'Please select effective date' }]}
              >
                <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Status" name="is_active" valuePropName="checked">
                <Switch checkedChildren="Active" unCheckedChildren="Inactive" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Allow Negative Inventory"
                name="allow_negative_inventory"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Permit stock to go negative during shortages
              </Text>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Prevent Cost Below Zero"
                name="prevent_cost_below_zero"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Ensure cost values never drop below zero
              </Text>
            </Col>
          </Row>

          <Alert
            type="info"
            showIcon
            message="Important"
            description="Changes to valuation methods may require approval and can trigger inventory revaluation. Ensure you have proper authorization before making changes."
            style={{ marginTop: 16 }}
          />
        </Form>
      </Modal>
    </div>
  );
};

export default ValuationSettings;
