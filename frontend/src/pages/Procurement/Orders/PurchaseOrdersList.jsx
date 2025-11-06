import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Space,
  Segmented,
  DatePicker,
  Tag,
  Statistic,
  Typography,
  List,
  Drawer,
  Select,
  Button,
  message,
  Form,
  InputNumber,
  Input,
} from 'antd';
import {
  ShoppingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  FieldTimeOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

const STATUS_FILTERS = [
  { label: 'All', value: 'ALL' },
  { label: 'Awaiting Approval', value: 'pending_approval' },
  { label: 'Approved', value: 'approved' },
  { label: 'Issued', value: 'issued' },
  { label: 'Partially Received', value: 'partially_received' },
  { label: 'Received', value: 'received' },
];

const FALLBACK_POS = [
  {
    id: 1,
    po_number: 'PO-2024-0401',
    supplier: 'Dhaka Cotton Mills',
    category: 'Raw Material',
    amount: 820000,
    currency: 'BDT',
    status: 'Approved',
    status_key: 'approved',
    expected_date: '2024-06-20',
    requester: 'Production',
  },
  {
    id: 2,
    po_number: 'PO-2024-0402',
    supplier: 'ColorSync Ltd.',
    category: 'Chemicals',
    amount: 210000,
    currency: 'BDT',
    status: 'Awaiting Approval',
    status_key: 'pending_approval',
    expected_date: '2024-06-18',
    requester: 'Print Unit',
  },
  {
    id: 3,
    po_number: 'PO-2024-0403',
    supplier: 'Rapid Box Solutions',
    category: 'Packaging',
    amount: 165000,
    currency: 'BDT',
    status: 'Issued',
    status_key: 'issued',
    expected_date: '2024-06-22',
    requester: 'Logistics',
  },
  {
    id: 4,
    po_number: 'PO-2024-0404',
    supplier: 'LogiTrans Express',
    category: 'Logistics',
    amount: 98000,
    currency: 'BDT',
    status: 'Received',
    status_key: 'received',
    expected_date: '2024-06-12',
    requester: 'Fulfilment',
  },
];

const FALLBACK_SPEND_TREND = [
  { week: 'Week 1', amount: 1.3 },
  { week: 'Week 2', amount: 1.1 },
  { week: 'Week 3', amount: 1.6 },
  { week: 'Week 4', amount: 1.4 },
];

const normalizePurchaseOrders = (records = []) =>
  (Array.isArray(records) ? records : []).map((po) => {
    const lines = Array.isArray(po.lines) ? po.lines : [];
    const firstLine = lines[0] || {};
    const category =
      po.request_type_display || firstLine.item_name || firstLine.budget_line_name || po.category || '-';
    const amount = Number(po.total_amount ?? po.amount ?? 0);
    const currency = po.currency || 'USD';
    const statusKeyRaw = (po.status || po.status_key || '').toString().toLowerCase();
    const statusDisplay = po.status_display || po.status || po.statusLabel || '-';
    const status_key = statusKeyRaw || statusDisplay.toString().toLowerCase();
    const expectedDate = po.expected_delivery_date || po.order_date || po.expected_date || null;

    return {
      id: po.id ?? po.po_number ?? Math.random().toString(36).slice(2),
      po_number: po.order_number || po.po_number,
      supplier: po.supplier_name || po.supplier || `Supplier #${po.supplier}`,
      category,
      amount,
      currency,
      status: statusDisplay,
      status_key: status_key || 'unknown',
      expected_date: expectedDate,
      requester: po.cost_center_name || po.requester || '-',
    };
  });

const getStatusTagProps = (status) => {
  const normalized = (status || '').toLowerCase();
  switch (normalized) {
    case 'approved':
      return { color: 'green', label: 'Approved' };
    case 'awaiting approval':
    case 'pending approval':
      return { color: 'orange', label: 'Awaiting Approval' };
    case 'issued':
      return { color: 'purple', label: 'Issued' };
    case 'partially received':
      return { color: 'magenta', label: 'Partially Received' };
    case 'received':
      return { color: 'blue', label: 'Received' };
    case 'cancelled':
      return { color: 'red', label: 'Cancelled' };
    default:
      return { color: 'default', label: status || '-' };
  }
};

const PurchaseOrdersList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState(normalizePurchaseOrders(FALLBACK_POS));
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateRange, setDateRange] = useState([dayjs().startOf('month'), dayjs().endOf('month')]);
  const [spendTrend, setSpendTrend] = useState(FALLBACK_SPEND_TREND);
  const [pendingCount, setPendingCount] = useState(0);
  const [pendingOpen, setPendingOpen] = useState(false);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingList, setPendingList] = useState([]);
  const [selectedPR, setSelectedPR] = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const [supplierId, setSupplierId] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm] = Form.useForm();
  const [createCcOptions, setCreateCcOptions] = useState([]);
  const [createBudgetLines, setCreateBudgetLines] = useState([]);

  useEffect(() => {
    loadOrders();
    loadPendingRequisitions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCompany, statusFilter, dateRange]);

  const loadOrders = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setOrders(normalizePurchaseOrders(FALLBACK_POS));
        setSpendTrend(FALLBACK_SPEND_TREND);
        return;
      }

      const response = await api.get('/api/v1/procurement/purchase-orders/', {
        params: {
          status: statusFilter === 'ALL' ? undefined : statusFilter,
          date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
          date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
        },
      });
      const payload = response.data || {};
      const normalized = normalizePurchaseOrders(payload.results || []);
      setOrders(normalized);
      if (Array.isArray(payload.spend_trend)) {
        setSpendTrend(payload.spend_trend);
      }
    } catch (error) {
      console.warn('Purchase orders fallback data used:', error?.message);
      setOrders(normalizePurchaseOrders(FALLBACK_POS));
      setSpendTrend(FALLBACK_SPEND_TREND);
    } finally {
      setLoading(false);
    }
  };

  const loadPendingRequisitions = async () => {
    try {
      const { data } = await api.get('/api/v1/procurement/purchase-requisitions/', { params: { status: 'submitted' } });
      const results = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      setPendingCount(results.length);
      setPendingList(results);
    } catch (e) {
      setPendingCount(0);
      setPendingList([]);
    }
  };

  const loadSuppliers = async () => {
    try {
      const { data } = await api.get('/api/v1/procurement/suppliers/');
      const results = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      setSuppliers(results.map((s) => ({ value: s.id, label: `${s.code || ''} ${s.name}`.trim() })));
    } catch (e) {
      setSuppliers([]);
    }
  };

  const openPendingDrawer = async () => {
    setPendingOpen(true);
    await loadSuppliers();
  };

  const openCreateDrawer = async () => {
    setCreateOpen(true);
    await loadSuppliers();
    try {
      const { data } = await api.get('/api/v1/budgets/cost-centers/');
      const list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      setCreateCcOptions(list.map((cc) => ({ value: cc.id, label: `${cc.code || ''} ${cc.name}` })));
    } catch (e) {
      setCreateCcOptions([]);
    }
  };

  const loadCreateBudgetLines = async (costCenterId) => {
    if (!costCenterId) { setCreateBudgetLines([]); return; }
    try {
      const { data } = await api.get('/api/v1/budgets/lines/', { params: { cost_center: costCenterId } });
      const list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      setCreateBudgetLines(list.map((bl) => ({ value: bl.id, label: `${bl.item_code || ''} ${bl.item_name || ''}`.trim() })));
    } catch (e) {
      setCreateBudgetLines([]);
    }
  };

  const generatePOFromSelected = async () => {
    if (!selectedPR || !supplierId) {
      message.warning('Select a requisition and supplier first');
      return;
    }
    try {
      setPendingLoading(true);
      await api.post(`/api/v1/procurement/purchase-requisitions/${selectedPR.id}/generate-po/`, {
        supplier_id: supplierId,
        expected_delivery_date: selectedPR.required_by,
      });
      message.success('Purchase Order generated from requisition');
      setSupplierId(null);
      setSelectedPR(null);
      await loadOrders();
      await loadPendingRequisitions();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to generate PO');
    } finally {
      setPendingLoading(false);
    }
  };

  const filteredOrders = useMemo(() => {
    if (statusFilter === 'ALL') {
      return orders;
    }
    return orders.filter((order) => order.status_key === statusFilter);
  }, [orders, statusFilter]);

  const metrics = useMemo(() => {
    return filteredOrders.reduce(
      (acc, order) => {
        acc.total += order.amount || 0;
        if (order.status_key === 'approved') acc.approved += 1;
        if (order.status_key === 'pending_approval') acc.awaiting += 1;
        if (order.status_key === 'received') acc.received += 1;
        return acc;
      },
      { total: 0, approved: 0, awaiting: 0, received: 0 },
    );
  }, [filteredOrders]);

  const spendConfig = useMemo(() => {
    const safeData = (Array.isArray(spendTrend) ? spendTrend : []).map((order) => ({
      ...order,
      amount: Number(order?.amount) || 0,
    }));
    return {
      data: safeData,
      xField: 'week',
      yField: 'amount',
      color: '#fa8c16',
      columnStyle: { radius: [8, 8, 0, 0] },
      tooltip: {
        formatter: (datum) => ({
          name: 'PO Value',
          value: `${datum.amount}M BDT`,
        }),
      },
    };
  }, [spendTrend]);

  const columns = [
    {
      title: 'PO',
      dataIndex: 'po_number',
      key: 'po_number',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.supplier}</Text>
        </Space>
      ),
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (value) =>
        value && value !== '-' ? <Tag color="blue">{value}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: 'Requester',
      dataIndex: 'requester',
      key: 'requester',
      render: (value) => value || '-',
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right',
      render: (value, record) => `${record.currency || 'BDT'} ${(Number(value) || 0).toLocaleString()}`,
    },
    {
      title: 'Expected Delivery',
      dataIndex: 'expected_date',
      key: 'expected_date',
      render: (value) => (value ? dayjs(value).format('MMM D, YYYY') : '-'),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => {
        const { color, label } = getStatusTagProps(value);
        return <Tag color={color}>{label}</Tag>;
      },
    },
  ];

  return (
    <div>
      <Title level={2}>Purchase Orders</Title>
      <Text type="secondary">
        Track PO status, spend cadence, and approval cycles to keep procurement aligned with the ERP blueprint.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} xl={6}>
          <Card onClick={openPendingDrawer} hoverable>
            <Statistic
              title="Pending Requisitions"
              value={pendingCount}
              prefix={<ExclamationCircleOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Approved"
              value={metrics.approved}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Awaiting Approval"
              value={metrics.awaiting}
              prefix={<ExclamationCircleOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Received"
              value={metrics.received}
              prefix={<FieldTimeOutlined style={{ color: '#13c2c2' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        <Col xs={24} xl={16}>
          <Card
            title="Purchase Order Register"
            extra={
              <Space>
                <Segmented
                  options={STATUS_FILTERS}
                  value={statusFilter}
                  onChange={(value) => setStatusFilter(value)}
                />
                <RangePicker value={dateRange} onChange={(range) => setDateRange(range)} />
                <Button type="primary" onClick={openCreateDrawer}>Create PO</Button>
              </Space>
            }
            loading={loading}
          >
            <Table dataSource={filteredOrders} columns={columns} rowKey="id" pagination={{ pageSize: 10 }} />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Weekly Spend Trend" style={{ marginBottom: 16 }} loading={loading}>
            <Column {...spendConfig} height={220} />
          </Card>
          <Card title="Approver Checklist">
            <List
              dataSource={[
                { id: 'check-1', title: 'Budget alignment', detail: 'COO sign-off required' },
                { id: 'check-2', title: 'Compliance check', detail: 'All documents uploaded' },
                { id: 'check-3', title: 'Payment schedule', detail: 'Finance review pending' },
              ]}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0}>
                    <Text strong>{item.title}</Text>
                    <Text type="secondary">{item.detail}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Drawer
        title="Pending Purchase Requisitions"
        open={pendingOpen}
        width={860}
        onClose={() => { setPendingOpen(false); setSelectedPR(null); setSupplierId(null); }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Space align="center" wrap>
            <Select
              placeholder="Select supplier"
              style={{ minWidth: 260 }}
              options={suppliers}
              value={supplierId}
              onChange={setSupplierId}
            />
            <Button type="primary" onClick={generatePOFromSelected} loading={pendingLoading} disabled={!selectedPR || !supplierId}>
              Generate PO
            </Button>
          </Space>
          <Table
            rowKey="id"
            dataSource={pendingList}
            loading={pendingLoading}
            rowSelection={{
              type: 'radio',
              selectedRowKeys: selectedPR ? [selectedPR.id] : [],
              onChange: (keys, rows) => setSelectedPR(rows[0] || null),
            }}
            columns={[
              { title: 'PR No', dataIndex: 'requisition_number', key: 'requisition_number' },
              { title: 'Priority', dataIndex: 'priority', key: 'priority', render: (v) => <Tag>{String(v || '').toUpperCase()}</Tag> },
              { title: 'Required By', dataIndex: 'required_by', key: 'required_by', render: (v) => (v ? dayjs(v).format('YYYY-MM-DD') : '-') },
              { title: 'Justification', dataIndex: 'justification', key: 'justification', ellipsis: true },
            ]}
            expandable={{
              expandedRowRender: (record) => (
                <Table
                  size="small"
                  pagination={false}
                  rowKey={(r) => r.id}
                  dataSource={record.lines || []}
                  columns={[
                    { title: '#', dataIndex: 'line_number', key: 'line_number', width: 60 },
                    { title: 'Item', dataIndex: 'budget_line_name', key: 'budget_line_name' },
                    { title: 'Qty', dataIndex: 'quantity', key: 'quantity', width: 100 },
                    { title: 'UoM', dataIndex: 'uom', key: 'uom', width: 100 },
                    { title: 'Est. Unit Cost', dataIndex: 'estimated_unit_cost', key: 'estimated_unit_cost', width: 140 },
                    { title: 'Needed By', dataIndex: 'needed_by', key: 'needed_by', width: 140, render: (v) => (v ? dayjs(v).format('YYYY-MM-DD') : '-') },
                  ]}
                />
              ),
            }}
          />
        </Space>
      </Drawer>

      <Drawer
        title="Create Purchase Order"
        open={createOpen}
        width={960}
        styles={{ body: { overflowX: 'auto' } }}
        onClose={() => { setCreateOpen(false); createForm.resetFields(); }}
        destroyOnClose
      >
        <Form layout="vertical" form={createForm} onFinish={async (values) => {
          try {
            setCreateLoading(true);
            const payload = {
              supplier: values.supplier,
              cost_center: values.cost_center || null,
              currency: values.currency || 'USD',
              expected_delivery_date: values.expected_delivery_date ? values.expected_delivery_date.format('YYYY-MM-DD') : null,
              lines: (values.lines || []).map((ln, idx) => ({
                line_number: idx + 1,
                requisition_line: null,
                budget_line: ln.budget_line,
                product: null,
                description: ln.description || '',
                quantity: Number(ln.quantity) || 0,
                expected_delivery_date: ln.needed_by || values.expected_delivery_date || null,
                unit_price: Number(ln.unit_price) || 0,
                tax_rate: Number(ln.tax_rate) || 0,
              })),
            };
            await api.post('/api/v1/procurement/purchase-orders/', payload);
            message.success('Purchase Order created');
            setCreateOpen(false);
            createForm.resetFields();
            await loadOrders();
          } catch (e) {
            message.error(e?.response?.data?.detail || 'Failed to create PO');
          } finally {
            setCreateLoading(false);
          }
        }}>
          <Space size={16} style={{ display: 'flex', marginBottom: 8 }} wrap>
            <Form.Item name="supplier" label="Supplier" rules={[{ required: true }]}>
              <Select
                showSearch
                placeholder="Select supplier"
                options={suppliers}
                filterOption={(input, option) => (option?.label || '').toLowerCase().includes(input.toLowerCase())}
                style={{ minWidth: 300 }}
              />
            </Form.Item>
            <Form.Item name="cost_center" label="Cost Center">
              <Select
                showSearch
                placeholder="Optional cost center"
                options={createCcOptions}
                onChange={(val) => loadCreateBudgetLines(val)}
                filterOption={(input, option) => (option?.label || '').toLowerCase().includes(input.toLowerCase())}
                style={{ minWidth: 260 }}
              />
            </Form.Item>
            <Form.Item name="currency" label="Currency" initialValue="USD">
              <Select options={[{ value: 'USD', label: 'USD' }, { value: 'BDT', label: 'BDT' }]} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="expected_delivery_date" label="Expected Delivery" rules={[{ required: true }]}>
              <DatePicker />
            </Form.Item>
          </Space>

          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <Card title="Lines" size="small" extra={<Button onClick={() => add()}>Add Line</Button>}>
                {fields.map(({ key, name, ...restField }) => (
                  <div key={key} style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, 1fr) 240px 120px 120px 120px auto', columnGap: 8, alignItems: 'end', marginBottom: 8 }}>
                    <Form.Item {...restField} name={[name, 'budget_line']} label="Budget Line" rules={[{ required: true }]}>
                      <Select
                        showSearch
                        placeholder="Select budget line"
                        options={createBudgetLines}
                        filterOption={(input, option) => (option?.label || '').toLowerCase().includes(input.toLowerCase())}
                      />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'description']} label="Description">
                      <Input placeholder="Item / service description" />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'quantity']} label="Qty" rules={[{ required: true }]}>
                      <InputNumber min={0.001} step={1} style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'unit_price']} label="Unit Price" rules={[{ required: true }]}>
                      <InputNumber min={0} step={0.01} style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'tax_rate']} label="Tax %">
                      <InputNumber min={0} step={0.01} style={{ width: 120 }} />
                    </Form.Item>
                    <Button
                      aria-label="Remove line"
                      type="text"
                      danger
                      shape="circle"
                      icon={<CloseOutlined />}
                      onClick={() => remove(name)}
                    />
                  </div>
                ))}
              </Card>
            )}
          </Form.List>

          <Space style={{ marginTop: 12 }}>
            <Button onClick={() => { setCreateOpen(false); createForm.resetFields(); }}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={createLoading}>Create</Button>
          </Space>
        </Form>
      </Drawer>
    </div>
  );
};

export default PurchaseOrdersList;
