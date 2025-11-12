import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Space,
  Typography,
  Tag,
  Card,
  Descriptions,
  Tabs,
  Table,
  List,
  Badge,
  Divider,
  Spin,
  message,
  Drawer,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  Row,
  Col,
  DatePicker,
  Popconfirm,
} from 'antd';
import { ArrowLeftOutlined, EditOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import api from '../../../services/api';

const { Title, Text } = Typography;

const HAZMAT_OPTIONS = [
  { label: 'None', value: '' },
  { label: 'Danger', value: 'DANGER' },
  { label: 'Warning', value: 'WARNING' },
  { label: 'Caution', value: 'CAUTION' },
];

const STORAGE_OPTIONS = [
  { label: 'Dry', value: 'DRY' },
  { label: 'Frozen', value: 'FROZEN' },
  { label: 'Climate Controlled', value: 'CLIMATE' },
  { label: 'Hazardous Material', value: 'HAZMAT' },
  { label: 'Outdoor', value: 'OUTDOOR' },
];

const MovementHistoryTable = ({ events, loading, filters = {}, onChange = () => {} }) => {
  const columns = [
    {
      title: 'Timestamp',
      dataIndex: 'event_timestamp',
      key: 'event_timestamp',
      render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Event',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: 'Qty',
      dataIndex: 'qty_change',
      key: 'qty_change',
      render: (value, record) => `${Number(value || 0).toLocaleString()} ${record.stock_uom?.code || ''}`,
    },
    {
      title: 'Warehouse',
      dataIndex: ['warehouse', 'code'],
      key: 'warehouse',
    },
    {
      title: 'Reference',
      key: 'reference',
      render: (_, record) =>
        `${record.reference_document_type || ''} ${record.reference_document_id || ''}`.trim(),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Space wrap>
        <Select
          placeholder="Event Type"
          allowClear
          style={{ width: 180 }}
          value={filters.event_type}
          onChange={(value) => onChange({ ...filters, event_type: value })}
          options={[
            { label: 'Receipt', value: 'RECEIPT' },
            { label: 'Issue', value: 'ISSUE' },
            { label: 'Transfer Out', value: 'TRANSFER_OUT' },
            { label: 'Transfer In', value: 'TRANSFER_IN' },
            { label: 'Adjustment', value: 'ADJUSTMENT' },
          ]}
        />
        <DatePicker.RangePicker
          value={filters.range}
          onChange={(range) => onChange({ ...filters, range })}
        />
        <Button onClick={() => onChange({ event_type: undefined, range: undefined })}>Clear Filters</Button>
      </Space>
      <Table
        dataSource={events}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        size="small"
      />
    </Space>
  );
};

const ItemDetail = () => {
  const { itemId } = useParams();
  const navigate = useNavigate();

  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [suppliers, setSuppliers] = useState([]);
  const [warehouseConfigs, setWarehouseConfigs] = useState([]);
  const [movementEvents, setMovementEvents] = useState([]);
  const [movementLoading, setMovementLoading] = useState(false);
  const [movementFilters, setMovementFilters] = useState({ event_type: undefined, range: undefined });

  const [profileDrawer, setProfileDrawer] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileForm] = Form.useForm();

  const loadItem = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/api/v1/inventory/items/${itemId}/`);
      setItem(data);
      setWarehouseConfigs(data.warehouse_configs || []);
      profileForm.setFieldsValue({
        ...data.operational_profile,
      });
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to load item');
    } finally {
      setLoading(false);
    }
  };

  const fetchSuppliers = async () => {
    try {
      const { data } = await api.get('/api/v1/inventory/item-suppliers/', {
        params: { item: itemId },
      });
      const results = Array.isArray(data?.results) ? data.results : data;
      setSuppliers(results || []);
    } catch (error) {
      setSuppliers([]);
    }
  };

  const fetchMovementEvents = async (nextFilters = movementFilters) => {
    try {
      setMovementLoading(true);
      const params = { item: itemId, page_size: 50 };
      if (nextFilters.event_type) params.event_type = nextFilters.event_type;
      if (nextFilters.range) {
        params.date_from = nextFilters.range[0]?.format('YYYY-MM-DD');
        params.date_to = nextFilters.range[1]?.format('YYYY-MM-DD');
      }
      const { data } = await api.get('/api/v1/inventory/movement-events/', { params });
      const results = Array.isArray(data?.results) ? data.results : data;
      setMovementEvents(results || []);
    } catch (error) {
      setMovementEvents([]);
    } finally {
      setMovementLoading(false);
    }
  };

  const fetchInTransit = async () => {
    try {
      setInTransitLoading(true);
      const { data } = await api.get('/api/v1/inventory/in-transit-lines/', {
        params: { item: itemId },
      });
      const results = Array.isArray(data?.results) ? data.results : data;
      setInTransit(results || []);
    } catch (error) {
      setInTransit([]);
    } finally {
      setInTransitLoading(false);
    }
  };

  const ensureWarehouseOptions = async () => {
    if (warehouseOptions.length) return warehouseOptions;
    try {
      const { data } = await api.get('/api/v1/inventory/warehouses/', { params: { page_size: 200 } });
      const results = Array.isArray(data?.results) ? data.results : data;
      setWarehouseOptions(results || []);
      return results || [];
    } catch (error) {
      message.error('Unable to load warehouse list');
      return [];
    }
  };

  const openWarehouseDrawer = async (record = null) => {
    await ensureWarehouseOptions();
    setWarehouseDrawer({ visible: true, record });
    if (record) {
      warehouseForm.setFieldsValue({
        warehouse: record.warehouse?.id || null,
        pack_size_qty: record.pack_size_qty,
        min_stock_level: record.min_stock_level,
        max_stock_level: record.max_stock_level,
        reorder_point: record.reorder_point,
        economic_order_qty: record.economic_order_qty,
        lead_time_days: record.lead_time_days,
        service_level_pct: record.service_level_pct,
      });
    } else {
      warehouseForm.resetFields();
    }
  };

  const closeWarehouseDrawer = () => {
    setWarehouseDrawer({ visible: false, record: null });
    warehouseForm.resetFields();
  };

  const handleWarehouseSave = async () => {
    try {
      const values = await warehouseForm.validateFields();
      setWarehouseSaving(true);
      const payload = {
        ...values,
        item: item.id,
        budget_item: item.budget_item,
        warehouse: values.warehouse || null,
      };
      if (warehouseDrawer.record?.id) {
        await api.patch(`/api/v1/inventory/item-warehouse-configs/${warehouseDrawer.record.id}/`, payload);
      } else {
        await api.post('/api/v1/inventory/item-warehouse-configs/', payload);
      }
      message.success('Warehouse configuration saved');
      closeWarehouseDrawer();
      await loadItem();
    } catch (error) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Unable to save configuration');
    } finally {
      setWarehouseSaving(false);
    }
  };

  const handleWarehouseDelete = async (record) => {
    if (!record?.id) return;
    try {
      await api.delete(`/api/v1/inventory/item-warehouse-configs/${record.id}/`);
      message.success('Configuration deleted');
      await loadItem();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to delete configuration');
    }
  };

  useEffect(() => {
    if (!itemId) return;
    loadItem();
    fetchSuppliers();
    fetchMovementEvents();
    fetchInTransit();
  }, [itemId]);

  const masterInfo = useMemo(() => {
    if (!item) return [];
    return [
      { label: 'Code', value: item.budget_item_code || item.code },
      { label: 'Name', value: item.budget_item_name || item.name },
      { label: 'Category', value: item.category_name || '—' },
      { label: 'Item Type', value: item.budget_item_type || '—' },
      { label: 'Base UoM', value: item.budget_item_uom_code || item.uom_code || '—' },
      {
        label: 'Standard Cost',
        value: item.budget_item_standard_price
          ? Number(item.budget_item_standard_price).toLocaleString()
          : '—',
      },
      { label: 'Company', value: item.company?.name || '—' },
    ];
  }, [item]);

  const operationalProfile = item?.operational_profile || {};

  const handleProfileSave = async () => {
    try {
      const values = await profileForm.validateFields();
      setProfileSaving(true);
      const payload = {
        ...values,
        item: item.id,
        budget_item: item.budget_item,
        requires_batch_tracking: !!values.requires_batch_tracking,
        requires_serial_tracking: !!values.requires_serial_tracking,
        requires_expiry_tracking: !!values.requires_expiry_tracking,
        allow_negative_inventory: !!values.allow_negative_inventory,
      };
      if (operationalProfile?.id) {
        await api.patch(`/api/v1/inventory/item-operational-profiles/${operationalProfile.id}/`, payload);
      } else {
        await api.post('/api/v1/inventory/item-operational-profiles/', payload);
      }
      message.success('Operational profile saved');
      setProfileDrawer(false);
      await loadItem();
    } catch (error) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Unable to save operational profile');
    } finally {
      setProfileSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <Spin />
      </div>
    );
  }

  if (!item) {
    return (
      <div style={{ padding: 24 }}>
        <Space direction="vertical">
          <Text type="secondary">Item not found.</Text>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            Back
          </Button>
        </Space>
      </div>
    );
  }

  return (
    <div style={{ padding: 8 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          Back
        </Button>
        <Title level={3} style={{ margin: 0 }}>
          {item.budget_item_name || item.name}
        </Title>
        <Tag color="blue">{item.budget_item_code || item.code}</Tag>
        {item.budget_item ? <Tag color="green">Budget Master Linked</Tag> : <Tag color="red">Legacy Item</Tag>}
      </Space>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Master Data">
            <Descriptions bordered column={1} size="small">
              {masterInfo.map((entry) => (
                <Descriptions.Item label={entry.label} key={entry.label}>
                  {entry.value || '—'}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card
            title="Operational Flags"
            extra={
              <Button icon={<EditOutlined />} onClick={() => setProfileDrawer(true)}>
                Edit Profile
              </Button>
            }
          >
            <List
              dataSource={[
                { name: 'Batch Tracking', value: operationalProfile.requires_batch_tracking },
                { name: 'Serial Tracking', value: operationalProfile.requires_serial_tracking },
                { name: 'Expiry Tracking', value: operationalProfile.requires_expiry_tracking },
                { name: 'Negative Inventory', value: operationalProfile.allow_negative_inventory },
              ]}
              renderItem={(itemFlag) => (
                <List.Item>
                  <Text>{itemFlag.name}</Text>
                  {itemFlag.value ? <Badge status="success" text="Enabled" /> : <Badge status="default" text="Disabled" />}
                </List.Item>
              )}
            />
            <Divider />
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Hazmat Class">{operationalProfile.hazmat_class || '—'}</Descriptions.Item>
              <Descriptions.Item label="Storage Class">{operationalProfile.storage_class || '—'}</Descriptions.Item>
              <Descriptions.Item label="Barcode">{operationalProfile.barcode || '—'}</Descriptions.Item>
              <Descriptions.Item label="QR Code">{operationalProfile.qr_code || '—'}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="overview"
        style={{ marginTop: 16 }}
        items={[
          {
            key: 'overview',
            label: 'Overview',
            children: (
              <Card>
                <Descriptions title="Global Warehouse Settings" column={2}>
                  <Descriptions.Item label="Min Stock">{item.min_stock_level || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Max Stock">{item.max_stock_level || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Reorder Qty">{item.reorder_quantity || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Lead Time (days)">{item.lead_time_days || '—'}</Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: 'warehouses',
            label: 'Warehouse Configs',
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button type="primary" onClick={() => openWarehouseDrawer(null)} style={{ alignSelf: 'flex-end' }}>
                  Add Configuration
                </Button>
                <Table
                  dataSource={warehouseConfigs}
                  rowKey="id"
                  pagination={false}
                  columns={[
                    {
                      title: 'Scope',
                      render: (_, record) =>
                        record.warehouse
                          ? `${record.warehouse.code} · ${record.warehouse.name}`
                          : 'Global',
                    },
                    {
                      title: 'Min / Max',
                      render: (_, record) =>
                        `${Number(record.min_stock_level || 0)} / ${Number(record.max_stock_level || 0)}`,
                    },
                    {
                      title: 'Reorder / EOQ',
                      render: (_, record) =>
                        `${Number(record.reorder_point || 0)} / ${Number(record.economic_order_qty || 0)}`,
                    },
                    {
                      title: 'Lead Time (days)',
                      dataIndex: 'lead_time_days',
                    },
                    {
                      title: 'Service Level (%)',
                      dataIndex: 'service_level_pct',
                    },
                    {
                      title: 'Actions',
                      render: (_, record) => (
                        <Space>
                          <Button size="small" onClick={() => openWarehouseDrawer(record)}>
                            Edit
                          </Button>
                          {record.id && (
                            <Popconfirm
                              title="Remove configuration?"
                              okText="Delete"
                              okButtonProps={{ danger: true }}
                              onConfirm={() => handleWarehouseDelete(record)}
                            >
                              <Button danger size="small">Delete</Button>
                            </Popconfirm>
                          )}
                        </Space>
                      ),
                    },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: 'suppliers',
            label: 'Suppliers',
            children: (
              <Table
                dataSource={suppliers}
                rowKey="id"
                pagination={false}
                columns={[
                  {
                    title: 'Supplier',
                    dataIndex: ['supplier', 'name'],
                  },
                  {
                    title: 'Supplier Item Code',
                    dataIndex: 'supplier_item_code',
                  },
                  {
                    title: 'MOQ',
                    dataIndex: 'moq_qty',
                    render: (value) => Number(value || 0).toLocaleString(),
                  },
                  {
                    title: 'Multiple',
                    dataIndex: 'multiple_qty',
                    render: (value) => Number(value || 0).toLocaleString(),
                  },
                  {
                    title: 'Lead Time (days)',
                    dataIndex: 'lead_time_days',
                  },
                  {
                    title: 'Preferred Rank',
                    dataIndex: 'preferred_rank',
                  },
                  {
                    title: 'Status',
                    dataIndex: 'is_active',
                    render: (value) => (value ? <Tag color="green">Active</Tag> : <Tag color="red">Inactive</Tag>),
                  },
                ]}
              />
            ),
          },
          {
            key: 'uom',
            label: 'UoM Conversions',
            children: (
              <Table
                dataSource={item.uom_conversions || []}
                rowKey="id"
                pagination={false}
                columns={[
                  {
                    title: 'From → To',
                    render: (_, record) => `${record.from_uom_code || ''} → ${record.to_uom_code || ''}`,
                  },
                  {
                    title: 'Factor',
                    dataIndex: 'conversion_factor',
                    render: (value) => Number(value || 0).toLocaleString(),
                  },
                  {
                    title: 'Contexts',
                    render: (_, record) => (
                      <Space>
                        {record.is_purchase_conversion && <Tag color="geekblue">Purchase</Tag>}
                        {record.is_sales_conversion && <Tag color="purple">Sales</Tag>}
                        {record.is_stock_conversion && <Tag color="gold">Stock</Tag>}
                        {!record.is_purchase_conversion &&
                          !record.is_sales_conversion &&
                          !record.is_stock_conversion && <Tag>Generic</Tag>}
                      </Space>
                    ),
                  },
                  {
                    title: 'Effective Date',
                    dataIndex: 'effective_date',
                  },
                  {
                    title: 'Rounding',
                    dataIndex: 'rounding_rule',
                  },
                ]}
              />
            ),
          },
          {
            key: 'movements',
            label: 'Movement History',
            children: (
              <MovementHistoryTable
                events={movementEvents}
                loading={movementLoading}
                filters={movementFilters}
                onChange={(nextFilters) => {
                  setMovementFilters(nextFilters);
                  fetchMovementEvents(nextFilters);
                }}
              />
            ),
          },
          {
            key: 'intransit',
            label: 'In Transit',
            children: (
              <Table
                dataSource={inTransit}
                loading={inTransitLoading}
                rowKey="id"
                pagination={false}
                columns={[
                  {
                    title: 'From → To',
                    render: (_, record) =>
                      `${record.from_warehouse_code || ''} → ${record.to_warehouse_code || ''}`,
                  },
                  {
                    title: 'Qty',
                    dataIndex: 'quantity',
                    render: (value) => Number(value || 0).toLocaleString(),
                  },
                  {
                    title: 'Rate',
                    dataIndex: 'rate',
                    render: (value) => Number(value || 0).toLocaleString(),
                  },
                  {
                    title: 'Created',
                    dataIndex: 'created_at',
                    render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm'),
                  },
                  {
                    title: 'Movement',
                    render: (_, record) => record.movement_number || record.movement,
                  },
                ]}
              />
            ),
          },
        ]}
      />

      <Drawer
        open={profileDrawer}
        title="Operational Profile"
        onClose={() => setProfileDrawer(false)}
        width={520}
        destroyOnClose
        extra={
          <Button type="primary" onClick={handleProfileSave} loading={profileSaving}>
            Save
          </Button>
        }
      >
        <Form layout="vertical" form={profileForm}>
          <Form.Item name="barcode" label="Barcode">
            <Input />
          </Form.Item>
          <Form.Item name="qr_code" label="QR Code">
            <Input />
          </Form.Item>
          <Form.Item name="hazmat_signal_word" label="Hazmat Signal Word">
            <Select options={HAZMAT_OPTIONS} allowClear />
          </Form.Item>
          <Form.Item name="storage_class" label="Storage Class">
            <Select options={STORAGE_OPTIONS} allowClear />
          </Form.Item>
          <Form.Item name="hazmat_class" label="Hazmat Class">
            <Input />
          </Form.Item>
          <Form.Item name="handling_instructions" label="Handling Instructions">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="requires_batch_tracking" valuePropName="checked">
            <Switch>Batch Tracking</Switch>
          </Form.Item>
          <Form.Item name="requires_serial_tracking" valuePropName="checked">
            <Switch>Serial Tracking</Switch>
          </Form.Item>
          <Form.Item name="requires_expiry_tracking" valuePropName="checked">
            <Switch>Expiry Tracking</Switch>
          </Form.Item>
          <Form.Item name="allow_negative_inventory" valuePropName="checked">
            <Switch>Allow Negative Inventory</Switch>
          </Form.Item>
          <Form.Item name="expiry_warning_days" label="Expiry Warning (days)">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Drawer>
      <Drawer
        open={warehouseDrawer.visible}
        title={warehouseDrawer.record ? 'Edit Warehouse Config' : 'Add Warehouse Config'}
        onClose={closeWarehouseDrawer}
        width={520}
        destroyOnClose
        extra={
          <Button type="primary" onClick={handleWarehouseSave} loading={warehouseSaving}>
            Save
          </Button>
        }
      >
        <Form layout="vertical" form={warehouseForm}>
          <Form.Item name="warehouse" label="Warehouse" tooltip="Leave blank for global settings">
            <Select
              allowClear
              placeholder="Global"
              options={(warehouseOptions || []).map((option) => ({
                label: `${option.code} · ${option.name}`,
                value: option.id,
              }))}
            />
          </Form.Item>
          <Form.Item name="pack_size_qty" label="Pack Size Qty">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="min_stock_level" label="Min Stock Level">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_stock_level" label="Max Stock Level">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="reorder_point" label="Reorder Point">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="economic_order_qty" label="Economic Order Quantity">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="lead_time_days" label="Lead Time (days)">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="service_level_pct" label="Service Level (%)">
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
};

export default ItemDetail;
