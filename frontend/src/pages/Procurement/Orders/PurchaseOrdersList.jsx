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
} from 'antd';
import {
  ShoppingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  FieldTimeOutlined,
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
      po.request_type_display || firstLine.item_name || firstLine.budget_line_name || po.category || '�';
    const amount = Number(po.total_amount ?? po.amount ?? 0);
    const currency = po.currency || 'USD';
    const statusKeyRaw = (po.status || po.status_key || '').toString().toLowerCase();
    const statusDisplay = po.status_display || po.status || po.statusLabel || '�';
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
      requester: po.cost_center_name || po.requester || '�',
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
      return { color: 'default', label: status || '�' };
  }
};

const PurchaseOrdersList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState(normalizePurchaseOrders(FALLBACK_POS));
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateRange, setDateRange] = useState([dayjs().startOf('month'), dayjs().endOf('month')]);
  const [spendTrend, setSpendTrend] = useState(FALLBACK_SPEND_TREND);

  useEffect(() => {
    loadOrders();
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
        value && value !== '�' ? <Tag color="blue">{value}</Tag> : <Text type="secondary">�</Text>,
    },
    {
      title: 'Requester',
      dataIndex: 'requester',
      key: 'requester',
      render: (value) => value || '�',
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
      render: (value) => (value ? dayjs(value).format('MMM D, YYYY') : '�'),
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
          <Card>
            <Statistic
              title="Total PO Value"
              value={Number(metrics.total || 0).toLocaleString()}
              prefix={<ShoppingOutlined style={{ color: '#1890ff' }} />}
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
    </div>
  );
};

export default PurchaseOrdersList;
