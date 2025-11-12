import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Space,
  Segmented,
  DatePicker,
  Tag,
  Timeline,
  Typography,
  List,
  Badge,
  Tooltip,
  Button,
  Divider,
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Modal,
  Spin,
  message,
} from 'antd';
import {
  SwapRightOutlined,
  TruckOutlined,
  ExclamationCircleOutlined,
  DeploymentUnitOutlined,
  FieldTimeOutlined,
  EyeOutlined,
  PlusOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import dayjs from 'dayjs';
import api from '../../../services/api';
import {
  fetchStockMovements,
  previewStockMovement,
  createStockMovement,
  createStockMovementLine,
  confirmStockMovementReceipt,
} from '../../../services/inventory';
import { useCompany } from '../../../contexts/CompanyContext';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

const FALLBACK_MOVEMENTS = [
  {
    id: 'MOVE-1001',
    reference: 'GRN-4581',
    type: 'Inbound',
    sku: 'FAB-ROLL-60',
    name: 'Cotton Fabric Roll 60 GSM',
    quantity: 120,
    uom: 'Roll',
    from: 'Supplier: Dhaka Cotton Mills',
    to: 'HQ Distribution',
    status: 'Received',
    timestamp: '2024-06-12 08:45',
    owner: 'Receiving Team',
  },
  {
    id: 'MOVE-1002',
    reference: 'ISS-7732',
    type: 'Outbound',
    sku: 'ZIP-NYLON',
    name: 'Nylon Zipper 18"',
    quantity: 400,
    uom: 'Piece',
    from: 'HQ Distribution',
    to: 'Production Line 3',
    status: 'Staged',
    timestamp: '2024-06-12 09:30',
    owner: 'Kitting Team',
  },
  {
    id: 'MOVE-1003',
    reference: 'TRF-2201',
    type: 'Transfer',
    sku: 'BOX-EXP',
    name: 'Export Carton Box',
    quantity: 600,
    uom: 'Piece',
    from: 'HQ Distribution',
    to: 'Fulfilment Centre',
    status: 'In Transit',
    timestamp: '2024-06-12 11:05',
    owner: 'Logistics',
  },
  {
    id: 'MOVE-1004',
    reference: 'RET-087',
    type: 'Return',
    sku: 'DYE-NVY',
    name: 'Reactive Dye Navy Blue 5kg',
    quantity: 10,
    uom: 'Bucket',
    from: 'Production Line 1',
    to: 'Print Unit Store',
    status: 'Quality Hold',
    timestamp: '2024-06-11 16:40',
    owner: 'QA Team',
  },
];

const FALLBACK_ACTIVITY = [
  { hour: '08:00', inbound: 28, outbound: 21, transfers: 4 },
  { hour: '10:00', inbound: 35, outbound: 33, transfers: 6 },
  { hour: '12:00', inbound: 26, outbound: 30, transfers: 5 },
  { hour: '14:00', inbound: 32, outbound: 28, transfers: 8 },
  { hour: '16:00', inbound: 24, outbound: 26, transfers: 7 },
];

const FALLBACK_TIMELINE = [
  {
    time: '07:45',
    title: 'Dock Door 3 opened for inbound truck',
    type: 'inbound',
  },
  {
    time: '09:10',
    title: 'Wave #27 picking started',
    type: 'outbound',
  },
  {
    time: '11:30',
    title: 'Inter-warehouse transfer scheduled',
    type: 'transfer',
  },
  {
    time: '13:20',
    title: 'Return inspection flagged discrepancy',
    type: 'exception',
  },
  {
    time: '15:00',
    title: 'Courier dispatch for ecommerce orders',
    type: 'outbound',
  },
];

const statusColorMap = {
  RECEIVED: 'green',
  STAGED: 'processing',
  IN_TRANSIT: 'blue',
  'IN TRANSIT': 'blue',
  QUALITY_HOLD: 'volcano',
  'QUALITY HOLD': 'volcano',
  COMPLETED: 'green',
  DRAFT: 'default',
  SUBMITTED: 'blue',
};

const asArray = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.results)) return payload.results;
  if (payload.data) {
    if (Array.isArray(payload.data)) return payload.data;
    if (Array.isArray(payload.data.results)) return payload.data.results;
  }
  return [];
};

const StockMovements = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [movements, setMovements] = useState([]);
  const [movementFilter, setMovementFilter] = useState('ALL');
  const [activity, setActivity] = useState(FALLBACK_ACTIVITY);
  const [timelineEvents, setTimelineEvents] = useState(FALLBACK_TIMELINE);
  const [dateFilter, setDateFilter] = useState([dayjs().startOf('day'), dayjs().endOf('day')]);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [movementDrawerOpen, setMovementDrawerOpen] = useState(false);
  const [movementSaving, setMovementSaving] = useState(false);
  const [movementForm] = Form.useForm();
  const [referenceLoading, setReferenceLoading] = useState(false);
  const [warehouses, setWarehouses] = useState([]);
  const [items, setItems] = useState([]);
  const [confirmModal, setConfirmModal] = useState({ visible: false, record: null, loading: false });
  const [confirmForm] = Form.useForm();
  const movementStatusOptions = useMemo(
    () => [
      { label: 'Draft', value: 'DRAFT' },
      { label: 'Submitted', value: 'SUBMITTED' },
      { label: 'In Transit', value: 'IN_TRANSIT' },
      { label: 'Completed', value: 'COMPLETED' },
    ],
    []
  );

  const movementTypeOptions = useMemo(
    () => [
      { label: 'Transfer', value: 'TRANSFER' },
      { label: 'Receipt', value: 'RECEIPT' },
      { label: 'Issue', value: 'ISSUE' },
      { label: 'Adjustment', value: 'ADJUSTMENT' },
    ],
    []
  );

  const warehouseOptions = useMemo(
    () =>
      (warehouses || []).map((wh) => ({
        value: wh.id,
        label: `${wh.code || ''} ${wh.name || ''}`.trim(),
      })),
    [warehouses]
  );

  const itemOptions = useMemo(
    () =>
      (items || []).map((item) => ({
        value: item.id,
        label: `${item.code || item.sku || ''} ${item.name || ''}`.trim(),
      })),
    [items]
  );

  const itemsById = useMemo(
    () =>
      (items || []).reduce((acc, item) => {
        acc[item.id] = item;
        return acc;
      }, {}),
    [items]
  );

  const getDefaultRate = useCallback(
    (itemId) => {
      const item = itemsById[itemId];
      return Number(item?.valuation_rate ?? item?.standard_cost ?? item?.last_purchase_rate ?? 0) || 0;
    },
    [itemsById]
  );

  const isInTransitStatus = useCallback((status) => {
    if (!status) return false;
    const normalized = status.toString().replace(/\s+/g, '_').toUpperCase();
    return normalized === 'IN_TRANSIT';
  }, []);

  const openMovementDrawer = () => {
    movementForm.resetFields();
    movementForm.setFieldsValue({
      movement_type: 'TRANSFER',
      status: 'IN_TRANSIT',
      movement_date: dayjs(),
      lines: [{ quantity: 1 }],
    });
    setMovementDrawerOpen(true);
  };

  const closeMovementDrawer = () => {
    setMovementDrawerOpen(false);
    movementForm.resetFields();
  };

  const updateLineAtIndex = (index, updates) => {
    const currentLines = [...(movementForm.getFieldValue('lines') || [])];
    currentLines[index] = { ...(currentLines[index] || {}), ...updates };
    movementForm.setFieldsValue({ lines: currentLines });
  };

  const handleLineItemChange = (value, index) => {
    const selected = itemsById[value] || {};
    updateLineAtIndex(index, {
      item: value,
      uom: selected.stock_uom || selected.uom || selected.base_uom || '',
      rate: getDefaultRate(value),
    });
  };

  const handleCreateMovement = async () => {
    try {
      const values = await movementForm.validateFields();
      const lines = (values.lines || [])
        .map((line) => ({
          item: line.budget_item,
          quantity: Number(line.quantity || 0),
          rate: Number(line.rate ?? getDefaultRate(line.budget_item)),
          batch_no: line.batch_no || '',
          serial_numbers: line.serial_numbers || [],
          uom: line.uom,
        }))
        .filter((line) => line.budget_item && line.quantity > 0);

      if (!lines.length) {
        message.warning('Add at least one line item.');
        return;
      }

      const headerPayload = {
        movement_type: values.movement_type,
        movement_date: values.movement_date
          ? values.movement_date.format('YYYY-MM-DD')
          : dayjs().format('YYYY-MM-DD'),
        from_warehouse: values.from_warehouse || null,
        to_warehouse: values.to_warehouse,
        reference: values.reference || '',
        notes: values.notes || '',
        status:
          values.status ||
          (values.movement_type === 'TRANSFER' ? 'IN_TRANSIT' : 'DRAFT'),
      };

      setMovementSaving(true);
      const movementResponse = await createStockMovement(headerPayload);
      const createdMovement = movementResponse.data || movementResponse;
      const movementId = createdMovement.id;

      try {
        for (let index = 0; index < lines.length; index += 1) {
          const line = lines[index];
          await createStockMovementLine({
            movement: movementId,
            line_number: index + 1,
            item: line.budget_item,
            quantity: line.quantity,
            entered_quantity: line.quantity,
            rate: line.rate,
            batch_no: line.batch_no,
            serial_no: Array.isArray(line.serial_numbers)
              ? line.serial_numbers.join(', ')
              : line.serial_numbers || '',
          });
        }
      } catch (lineError) {
        await api.delete(`/api/v1/inventory/stock-movements/${movementId}/`).catch(() => {});
        throw lineError;
      }

      message.success('Stock movement created.');
      closeMovementDrawer();
      await loadMovements();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error?.response?.data?.detail || 'Unable to create stock movement.');
      }
    } finally {
      setMovementSaving(false);
    }
  };

  const openConfirmModal = (record) => {
    confirmForm.resetFields();
    confirmForm.setFieldsValue({ receipt_date: dayjs() });
    setConfirmModal({ visible: true, record, loading: false });
  };

  const handleConfirmReceipt = async () => {
    if (!confirmModal.record) return;
    try {
      const values = await confirmForm.validateFields();
      setConfirmModal((prev) => ({ ...prev, loading: true }));
      await confirmStockMovementReceipt(confirmModal.record.id, {
        receipt_date: values.receipt_date
          ? values.receipt_date.format('YYYY-MM-DD')
          : undefined,
      });
      message.success('Transfer receipt confirmed.');
      confirmForm.resetFields();
      setConfirmModal({ visible: false, record: null, loading: false });
      await loadMovements();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error?.response?.data?.detail || 'Unable to confirm receipt.');
        setConfirmModal((prev) => ({ ...prev, loading: false }));
      }
    }
  };

  const closeConfirmModal = () => {
    confirmForm.resetFields();
    setConfirmModal({ visible: false, record: null, loading: false });
  };

  useEffect(() => {
    loadMovements();
  }, [currentCompany, movementFilter, dateFilter]);

  const loadMovements = async () => {
    try {
        setLoading(true);
        if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
          setMovements(FALLBACK_MOVEMENTS);
          setActivity(FALLBACK_ACTIVITY);
          setTimelineEvents(FALLBACK_TIMELINE);
          return;
        }
      const response = await fetchStockMovements({
        params: {
          type: movementFilter === 'ALL' ? undefined : movementFilter,
          date_from: dateFilter?.[0]?.format('YYYY-MM-DD'),
          date_to: dateFilter?.[1]?.format('YYYY-MM-DD'),
        },
      });
        const payload = response.data || {};
        const results = Array.isArray(payload.results) ? payload.results : [];
        setMovements(results);
      if (Array.isArray(payload.activity)) {
        setActivity(payload.activity);
      }
      if (Array.isArray(payload.timeline)) {
        setTimelineEvents(payload.timeline);
      }
    } catch (error) {
      console.warn('Stock movements fallback data used:', error?.message);
      setMovements(FALLBACK_MOVEMENTS);
      setActivity(FALLBACK_ACTIVITY);
      setTimelineEvents(FALLBACK_TIMELINE);
    } finally {
      setLoading(false);
    }
  };

  const loadReferenceData = useCallback(async () => {
    if (!currentCompany?.id) return;
    setReferenceLoading(true);
    try {
      const [warehouseRes, itemRes] = await Promise.all([
        api.get('/api/v1/inventory/warehouses/', { params: { limit: 500 } }),
        api.get('/api/v1/inventory/items/', { params: { limit: 500 } }),
      ]);
      setWarehouses(asArray(warehouseRes.data));
      setItems(asArray(itemRes.data));
    } catch (error) {
      message.error('Unable to load reference data for stock movements.');
    } finally {
      setReferenceLoading(false);
    }
  }, [currentCompany?.id]);

  useEffect(() => {
    loadReferenceData();
  }, [loadReferenceData]);

  const handlePreview = async (movement) => {
    setPreviewVisible(true);
    setPreviewData(null);
    setPreviewLoading(true);
    try {
      const { data } = await previewStockMovement(movement.id);
      setPreviewData(data);
    } catch (err) {
      console.error('Failed to fetch GL preview', err);
      message.error('Unable to fetch GL preview right now.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const filteredMovements = useMemo(() => {
    if (movementFilter === 'ALL') {
      return movements;
    }
    return (movements || []).filter((movement) => movement.type === movementFilter);
  }, [movements, movementFilter]);

  const activityConfig = useMemo(() => {
    const safeData = (Array.isArray(activity) ? activity : []).reduce((acc, item) => {
      acc.push({ hour: item.hour, type: 'Inbound', value: Number(item?.inbound) || 0 });
      acc.push({ hour: item.hour, type: 'Outbound', value: Number(item?.outbound) || 0 });
      acc.push({ hour: item.hour, type: 'Transfer', value: Number(item?.transfers) || 0 });
      return acc;
    }, []);
    return {
      data: safeData,
      xField: 'hour',
      yField: 'value',
      seriesField: 'type',
      isGroup: true,
      color: ({ type }) => {
        if (type === 'Inbound') return '#52c41a';
        if (type === 'Outbound') return '#1890ff';
        return '#faad14';
      },
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${Number(datum.value).toLocaleString()} picks`,
        }),
      },
    };
  }, [activity]);

  const columns = [
    {
      title: 'Reference',
      dataIndex: 'reference',
      key: 'reference',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.id}</Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (value) => (
        <Tag color={value === 'Inbound' ? 'green' : value === 'Outbound' ? 'blue' : value === 'Transfer' ? 'purple' : 'gold'}>
          {value}
        </Tag>
      ),
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.name}</Text>
        </Space>
      ),
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right',
      render: (value, record) => `${Number(value || 0).toLocaleString()} ${record.uom || ''}`,
    },
    {
      title: 'From -> To',
      key: 'route',
      render: (_, record) => (
        <Space>
          <SwapRightOutlined />
          <Text>{record.from}</Text>
          <Text type="secondary">&rarr;</Text>
          <Text>{record.to}</Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => {
        const label = value || 'N/A';
        const colorKey = label.toString().replace(/\s+/g, '_').toUpperCase();
        return <Tag color={statusColorMap[colorKey] || 'default'}>{label}</Tag>;
      },
    },
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
    },
    {
      title: 'Owner',
      dataIndex: 'owner',
      key: 'owner',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="GL Preview">
            <Button size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record)}>
              Preview
            </Button>
          </Tooltip>
          {isInTransitStatus(record.status) && (
            <Tooltip title="Confirm Receipt">
              <Button
                size="small"
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => openConfirmModal(record)}
              >
                Confirm
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  const timelineColor = (type) => {
    if (type === 'inbound') return 'green';
    if (type === 'outbound') return 'blue';
    if (type === 'transfer') return 'purple';
    return 'red';
  };

  return (
    <div>
      <Title level={2}>Stock Movements</Title>
      <Text type="secondary">
        Track inbound, outbound, transfers, and exceptions to keep material flow aligned with the
        Twist ERP inventory playbook.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={8}>
          <Card>
            <Space direction="vertical" size="middle">
              <Segmented
                options={['ALL', 'Inbound', 'Outbound', 'Transfer', 'Return']}
                value={movementFilter}
                onChange={setMovementFilter}
              />
              <RangePicker
                allowClear
                value={dateFilter}
                onChange={(value) => setDateFilter(value)}
              />
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={16}>
          <Card title="Hourly Activity Mix">
            <Column {...activityConfig} height={240} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={16}>
          <Card
            title="Movement Register"
            loading={loading}
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={openMovementDrawer}>
                Create Movement
              </Button>
            }
          >
            <Table
              dataSource={filteredMovements}
              columns={columns}
              rowKey="id"
              pagination={{ pageSize: 15 }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Live Timeline" style={{ marginBottom: 16 }}>
            <Timeline
              mode="left"
              items={timelineEvents.map((event) => ({
                color: timelineColor(event.type),
                label: <Text strong>{event.time}</Text>,
                children: (
                  <Space>
                    {event.type === 'inbound' && <TruckOutlined style={{ color: '#52c41a' }} />}
                    {event.type === 'outbound' && <DeploymentUnitOutlined style={{ color: '#1890ff' }} />}
                    {event.type === 'transfer' && <FieldTimeOutlined style={{ color: '#722ed1' }} />}
                    {event.type === 'exception' && <ExclamationCircleOutlined style={{ color: '#f5222d' }} />}
                    <Text>{event.title}</Text>
                  </Space>
                ),
              }))}
            />
          </Card>
          <Card title="Exception Queue">
            <List
              dataSource={filteredMovements.filter((item) => item.status === 'Quality Hold')}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space>
                    <Badge status="error" />
                    <Space direction="vertical" size={0}>
                      <Text strong>{item.reference}</Text>
                      <Text type="secondary">{item.sku} - {item.timestamp}</Text>
                    </Space>
                  </Space>
                </List.Item>
              )}
              locale={{ emptyText: 'No quality holds right now.' }}
            />
          </Card>
        </Col>
      </Row>

      <Drawer
        title="Create Stock Movement"
        width={880}
        open={movementDrawerOpen}
        onClose={closeMovementDrawer}
        destroyOnClose
        extra={
          <Space>
            <Button onClick={closeMovementDrawer}>Cancel</Button>
            <Button type="primary" loading={movementSaving} onClick={handleCreateMovement}>
              Save Movement
            </Button>
          </Space>
        }
      >
        <Spin spinning={referenceLoading}>
          <Form form={movementForm} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="movement_type"
                label="Movement Type"
                rules={[{ required: true, message: 'Select movement type' }]}
              >
                <Select options={movementTypeOptions} placeholder="Select type" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="movement_date"
                label="Movement Date"
                rules={[{ required: true, message: 'Select date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="status" label="Status">
                <Select options={movementStatusOptions} placeholder="Select status" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="from_warehouse"
                label="From Warehouse"
              >
                <Select
                  options={warehouseOptions}
                  placeholder="Source warehouse"
                  optionFilterProp="label"
                  showSearch
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="to_warehouse"
                label="To Warehouse"
                rules={[{ required: true, message: 'Destination warehouse required' }]}
              >
                <Select
                  options={warehouseOptions}
                  placeholder="Destination warehouse"
                  optionFilterProp="label"
                  showSearch
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="reference" label="Reference">
                <Input placeholder="Optional reference" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="notes" label="Notes">
                <Input placeholder="Optional notes" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">Movement Lines</Divider>
          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field, index) => (
                  <Card
                    key={field.key}
                    size="small"
                    style={{ marginBottom: 16 }}
                    title={`Line ${index + 1}`}
                    extra={
                      fields.length > 1 ? (
                        <Button danger type="text" onClick={() => remove(field.name)}>
                          Remove
                        </Button>
                      ) : null
                    }
                  >
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name={[field.name, 'budget_item']}
                          label="Item"
                          rules={[{ required: true, message: 'Select an item' }]}
                        >
                          <Select
                            options={itemOptions}
                            showSearch
                            optionFilterProp="label"
                            placeholder="Search item"
                            onChange={(value) => handleLineItemChange(value, index)}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item
                          name={[field.name, 'quantity']}
                          label="Quantity"
                          rules={[{ required: true, message: 'Quantity required' }]}
                        >
                          <InputNumber min={0.001} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item name={[field.name, 'uom']} label="UOM">
                          <Input disabled placeholder="Auto" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={6}>
                        <Form.Item
                          name={[field.name, 'rate']}
                          label="Rate"
                          rules={[{ required: true, message: 'Rate required' }]}
                        >
                          <InputNumber min={0} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item name={[field.name, 'batch_no']} label="Batch / Lot">
                          <Input placeholder="Optional batch" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name={[field.name, 'serial_numbers']} label="Serial Numbers">
                          <Select mode="tags" placeholder="SN001, SN002" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item name={[field.name, 'notes']} label="Line Notes">
                      <Input placeholder="Optional notes" />
                    </Form.Item>
                  </Card>
                ))}
                <Button
                  block
                  type="dashed"
                  icon={<PlusOutlined />}
                  onClick={() => add({ quantity: 1 })}
                >
                  Add Line
                </Button>
              </>
            )}
          </Form.List>
        </Form>
        </Spin>
      </Drawer>

      <Drawer
        open={previewVisible}
        title={previewData ? `${previewData.movement_type || 'Movement'} GL Preview` : 'GL Preview'}
        width={640}
        onClose={() => setPreviewVisible(false)}
        footer={null}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text type="secondary">
            Movement ID: {previewData?.movement_id || '-'}
          </Text>
          {previewData?.warnings?.length ? (
            <Card size="small" type="inner" bordered style={{ background: '#fff7e6' }}>
              <Text strong>Warnings</Text>
              <List
                size="small"
                dataSource={previewData.warnings}
                renderItem={(warning) => (
                  <List.Item>
                    <Text type="warning">{warning}</Text>
                  </List.Item>
                )}
              />
            </Card>
          ) : null}
          <Table
            columns={[
              {
                title: 'Account',
                dataIndex: 'account_name',
                key: 'account_name',
                render: (_, record) => `${record.account_code || ''} ${record.account_name || ''}`.trim(),
              },
              {
                title: 'Debit',
                dataIndex: 'debit',
                key: 'debit',
                align: 'right',
                render: (value) => Number(value || 0).toLocaleString(),
              },
              {
                title: 'Credit',
                dataIndex: 'credit',
                key: 'credit',
                align: 'right',
                render: (value) => Number(value || 0).toLocaleString(),
              },
              {
                title: 'Description',
                dataIndex: 'description',
                key: 'description',
              },
            ]}
            dataSource={previewData?.entries || []}
            rowKey={(record) => `${record.account_id}-${record.description}-${record.debit}-${record.credit}`}
            pagination={false}
            loading={previewLoading}
            size="small"
          />
        </Space>
      </Drawer>

      <Modal
        title="Confirm Transfer Receipt"
        open={confirmModal.visible}
        onCancel={closeConfirmModal}
        onOk={handleConfirmReceipt}
        confirmLoading={confirmModal.loading}
        destroyOnClose
      >
        <Form form={confirmForm} layout="vertical">
          <Form.Item
            name="receipt_date"
            label="Receipt Date"
            rules={[{ required: true, message: 'Receipt date is required' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default StockMovements;
