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
  CheckCircleOutlined,
  SyncOutlined,
  DollarOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

const FALLBACK_ORDERS = [
  {
    id: 1,
    order_number: 'SO-2024-0012',
    customer: 'Acme Textiles',
    value: 920000,
    currency: 'BDT',
    status: 'Closed Won',
    expected_close: '2024-06-05',
    owner: 'Rahim Uddin',
    stage: 'Closed',
  },
  {
    id: 2,
    order_number: 'SO-2024-0013',
    customer: 'Northwind Apparel',
    value: 680000,
    currency: 'BDT',
    status: 'Signed',
    expected_close: '2024-06-18',
    owner: 'Sara Karim',
    stage: 'Negotiation',
  },
  {
    id: 3,
    order_number: 'SO-2024-0014',
    customer: 'Dakota Fashion',
    value: 1380000,
    currency: 'BDT',
    status: 'Proposal Sent',
    expected_close: '2024-06-22',
    owner: 'Lamia Hasan',
    stage: 'Proposal',
  },
  {
    id: 4,
    order_number: 'SO-2024-0015',
    customer: 'Pixel Export',
    value: 450000,
    currency: 'BDT',
    status: 'In Review',
    expected_close: '2024-06-19',
    owner: 'Sajid Khan',
    stage: 'Qualification',
  },
];

const FALLBACK_BOOKINGS = [
  { month: 'Jan', amount: 2.1 },
  { month: 'Feb', amount: 2.5 },
  { month: 'Mar', amount: 2.8 },
  { month: 'Apr', amount: 3.2 },
  { month: 'May', amount: 3.5 },
  { month: 'Jun', amount: 3.9 },
];

const SalesOrdersList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateRange, setDateRange] = useState([dayjs().startOf('month'), dayjs().endOf('month')]);
  const [bookings, setBookings] = useState(FALLBACK_BOOKINGS);

  useEffect(() => {
    loadOrders();
  }, [currentCompany, statusFilter, dateRange]);

  const loadOrders = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setOrders(FALLBACK_ORDERS);
        setBookings(FALLBACK_BOOKINGS);
        return;
      }
      const response = await api.get('/api/v1/sales/orders/', {
        params: {
          status: statusFilter === 'ALL' ? undefined : statusFilter,
          date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
          date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
        },
      });
      const payload = response.data || {};
      const results = Array.isArray(payload.results) ? payload.results : [];
      setOrders(results);
      if (Array.isArray(payload.bookings_trend)) {
        setBookings(payload.bookings_trend);
      }
    } catch (error) {
      console.warn('Sales orders fallback data used:', error?.message);
      setOrders(FALLBACK_ORDERS);
      setBookings(FALLBACK_BOOKINGS);
    } finally {
      setLoading(false);
    }
  };

  const filteredOrders = useMemo(() => {
    if (statusFilter === 'ALL') {
      return orders;
    }
    return (orders || []).filter((order) => order.status === statusFilter);
  }, [orders, statusFilter]);

  const metrics = useMemo(() => {
    const total = filteredOrders.reduce((sum, order) => sum + (Number(order.value) || 0), 0);
    const signed = filteredOrders.filter((order) => order.status === 'Signed').length;
    const closed = filteredOrders.filter((order) => order.status === 'Closed Won').length;
    const inReview = filteredOrders.filter((order) => order.status === 'In Review').length;
    return {
      total,
      signed,
      closed,
      inReview,
    };
  }, [filteredOrders]);

  const bookingsConfig = useMemo(() => {
    const safeData = (Array.isArray(bookings) ? bookings : []).map((item) => ({
      ...item,
      amount: Number(item?.amount) || 0,
    }));
    return {
      data: safeData,
      xField: 'month',
      yField: 'amount',
      smooth: true,
      color: '#722ed1',
      yAxis: {
        label: {
          formatter: (value) => `${value}M BDT`,
        },
      },
      tooltip: {
        formatter: (datum) => ({
          name: 'Bookings',
          value: `${datum.amount}M BDT`,
        }),
      },
    };
  }, [bookings]);

  const columns = [
    {
      title: 'Order',
      dataIndex: 'order_number',
      key: 'order_number',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.customer}</Text>
        </Space>
      ),
    },
    {
      title: 'Stage',
      dataIndex: 'stage',
      key: 'stage',
      render: (value) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: 'Owner',
      dataIndex: 'owner',
      key: 'owner',
    },
    {
      title: 'Order Value',
      dataIndex: 'value',
      key: 'value',
      align: 'right',
      render: (value, record) =>
        `${record.currency || 'BDT'} ${(Number(value) || 0).toLocaleString()}`,
    },
    {
      title: 'Expected Close',
      dataIndex: 'expected_close',
      key: 'expected_close',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => {
        if (value === 'Closed Won') {
          return <Tag color="green">{value}</Tag>;
        }
        if (value === 'Signed') {
          return <Tag color="blue">{value}</Tag>;
        }
        if (value === 'In Review') {
          return <Tag color="orange">{value}</Tag>;
        }
        return <Tag color="purple">{value}</Tag>;
      },
    },
  ];

  return (
    <div>
      <Title level={2}>Sales Orders</Title>
      <Text type="secondary">
        Track bookings, committed revenue, and order statuses to maintain the Twist ERP sales
        cadence.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} xl={3}>
          <Card>
            <Statistic
              title="Total Value"
              value={metrics.total}
              prefix={<DollarOutlined style={{ color: '#1890ff' }} />}
              precision={0}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={3}>
          <Card>
            <Statistic
              title="Closed Won"
              value={metrics.closed}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={3}>
          <Card>
            <Statistic
              title="Signed"
              value={metrics.signed}
              prefix={<SyncOutlined spin style={{ color: '#13c2c2' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={3}>
          <Card>
            <Statistic
              title="In Review"
              value={metrics.inReview}
              prefix={<ExclamationCircleOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        <Col xs={24} xl={16}>
          <Card
            title="Order Register"
            extra={
              <Space>
                <Segmented
                  options={['ALL', 'Signed', 'Closed Won', 'In Review', 'Proposal Sent']}
                  value={statusFilter}
                  onChange={setStatusFilter}
                />
                <RangePicker value={dateRange} onChange={setDateRange} />
              </Space>
            }
            loading={loading}
          >
            <Table
              dataSource={filteredOrders}
              columns={columns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Bookings Trend" style={{ marginBottom: 16 }} loading={loading}>
            <Column {...bookingsConfig} height={220} />
          </Card>
          <Card title="Key Order Actions">
            <List
              dataSource={[
                { id: 'action-1', title: 'Finalize SOW with Northwind Apparel', due: 'Today' },
                { id: 'action-2', title: 'Legal review for Dakota Fashion', due: 'Tomorrow' },
                { id: 'action-3', title: 'Collect reference for Pixel Export', due: 'This week' },
              ]}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0}>
                    <Text strong>{item.title}</Text>
                    <Text type="secondary">Due: {item.due}</Text>
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

export default SalesOrdersList;
