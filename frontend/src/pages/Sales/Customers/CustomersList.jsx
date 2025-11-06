import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Space,
  Segmented,
  Input,
  Tag,
  List,
  Typography,
  Badge,
  Statistic,
  Button,
  Modal,
  Form,
  Select,
  InputNumber,
  message,
} from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  ArrowUpOutlined,
  MailOutlined,
  CalendarOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Column, Pie } from '@ant-design/charts';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;

const FALLBACK_CUSTOMERS = [
  {
    id: 1,
    name: 'Acme Textiles',
    segment: 'Enterprise',
    industry: 'Garments',
    health: 'Growing',
    owner: 'Rahim Uddin',
    revenue: 6200000,
    last_contact: '2024-06-10',
    score: 82,
    location: 'Dhaka',
  },
  {
    id: 2,
    name: 'Northwind Apparel',
    segment: 'Mid-Market',
    industry: 'Retail',
    health: 'At Risk',
    owner: 'Sara Karim',
    revenue: 2800000,
    last_contact: '2024-06-04',
    score: 58,
    location: 'Chattogram',
  },
  {
    id: 3,
    name: 'Dakota Fashion',
    segment: 'Enterprise',
    industry: 'Export',
    health: 'Stable',
    owner: 'Lamia Hasan',
    revenue: 4500000,
    last_contact: '2024-06-11',
    score: 74,
    location: 'Dhaka',
  },
  {
    id: 4,
    name: 'Pixel Export',
    segment: 'SMB',
    industry: 'Ecommerce',
    health: 'Growing',
    owner: 'Sajid Khan',
    revenue: 1800000,
    last_contact: '2024-06-08',
    score: 68,
    location: 'Khulna',
  },
  {
    id: 5,
    name: 'Lotus Garments',
    segment: 'Mid-Market',
    industry: 'Manufacturing',
    health: 'Dormant',
    owner: 'Rahim Uddin',
    revenue: 1320000,
    last_contact: '2024-05-24',
    score: 45,
    location: 'Narayanganj',
  },
];

const FALLBACK_SEGMENT_DISTRIBUTION = [
  { segment: 'Enterprise', value: 38 },
  { segment: 'Mid-Market', value: 34 },
  { segment: 'SMB', value: 28 },
];

const FALLBACK_REVENUE_TREND = [
  { month: 'Jan', revenue: 3.2 },
  { month: 'Feb', revenue: 3.5 },
  { month: 'Mar', revenue: 3.9 },
  { month: 'Apr', revenue: 4.1 },
  { month: 'May', revenue: 4.5 },
  { month: 'Jun', revenue: 4.8 },
];

const healthColor = {
  Growing: 'green',
  Stable: 'blue',
  'At Risk': 'volcano',
  Dormant: 'red',
};

const CustomersList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [segmentFilter, setSegmentFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [segmentDistribution, setSegmentDistribution] = useState(FALLBACK_SEGMENT_DISTRIBUTION);
  const [revenueTrend, setRevenueTrend] = useState(FALLBACK_REVENUE_TREND);
  const [isCustomerModalOpen, setIsCustomerModalOpen] = useState(false);
  const [customerForm] = Form.useForm();
  const [accounts, setAccounts] = useState([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const customerTypeOptions = [
    { label: 'Local', value: 'local' },
    { label: 'Export', value: 'export' },
    { label: 'Intercompany', value: 'intercompany' },
  ];

  useEffect(() => {
    loadCustomers();
  }, [currentCompany]);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setCustomers(FALLBACK_CUSTOMERS);
        setSegmentDistribution(FALLBACK_SEGMENT_DISTRIBUTION);
        setRevenueTrend(FALLBACK_REVENUE_TREND);
        return;
      }
      const response = await api.get('/api/v1/sales/customers/');
      const payload = response.data;
      const results = Array.isArray(payload) ? payload : Array.isArray(payload?.results) ? payload.results : [];
      setCustomers(results);
      if (Array.isArray(payload.segment_distribution)) {
        setSegmentDistribution(payload.segment_distribution);
      }
      if (Array.isArray(payload.revenue_trend)) {
        setRevenueTrend(payload.revenue_trend);
      }
    } catch (error) {
      console.warn('Customers fallback data used:', error?.message);
      setCustomers(FALLBACK_CUSTOMERS);
      setSegmentDistribution(FALLBACK_SEGMENT_DISTRIBUTION);
      setRevenueTrend(FALLBACK_REVENUE_TREND);
    } finally {
      setLoading(false);
    }
  };

  const loadAccounts = async () => {
    try {
      setAccountsLoading(true);
      const res = await api.get('/api/v1/finance/accounts/');
      const data = Array.isArray(res.data) ? res.data : res.data?.results || [];
      setAccounts(data);
    } catch (err) {
      message.error('Unable to load accounts.');
    } finally {
      setAccountsLoading(false);
    }
  };

  const showCustomerModal = () => {
    setIsCustomerModalOpen(true);
    loadAccounts();
  };

  const handleCustomerCancel = () => {
    setIsCustomerModalOpen(false);
    customerForm.resetFields();
  };

  const handleCustomerSubmit = async (values) => {
    try {
      await api.post('/api/v1/sales/customers/', values);
      message.success('Customer added successfully');
      handleCustomerCancel();
      loadCustomers();
    } catch (err) {
      message.error(err?.response?.data?.detail || 'Failed to add customer');
    }
  };

  const filteredCustomers = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return (customers || []).filter((customer) => {
      const matchesSegment =
        segmentFilter === 'ALL' || customer.segment === segmentFilter || customer.segment === segmentFilter.toUpperCase();
      const matchesTerm =
        !term ||
        customer.name?.toLowerCase().includes(term) ||
        customer.industry?.toLowerCase().includes(term) ||
        customer.owner?.toLowerCase().includes(term);
      return matchesSegment && matchesTerm;
    });
  }, [customers, segmentFilter, searchTerm]);

  const metrics = useMemo(() => {
    const totalCustomers = filteredCustomers.length;
    const enterpriseCount = filteredCustomers.filter((item) => item.segment === 'Enterprise').length;
    const riskCount = filteredCustomers.filter((item) => item.health === 'At Risk').length;
    const avgScore =
      filteredCustomers.reduce((sum, item) => sum + (Number(item.score) || 0), 0) /
      (filteredCustomers.length || 1);
    return {
      totalCustomers,
      enterpriseCount,
      riskCount,
      avgScore: Math.round(avgScore),
    };
  }, [filteredCustomers]);

  const revenueConfig = useMemo(() => {
    const safeData = (Array.isArray(revenueTrend) ? revenueTrend : []).map((item) => ({
      ...item,
      revenue: Number(item?.revenue) || 0,
    }));
    return {
      data: safeData,
      xField: 'month',
      yField: 'revenue',
      smooth: true,
      color: '#1890ff',
      yAxis: {
        label: {
          formatter: (value) => `${value}M BDT`,
        },
      },
      tooltip: {
        formatter: (datum) => ({
          name: 'Revenue',
          value: `${datum.revenue}M BDT`,
        }),
      },
    };
  }, [revenueTrend]);

  const segmentConfig = useMemo(() => {
    const safeData = (Array.isArray(segmentDistribution) ? segmentDistribution : []).map(
      (item) => ({
        ...item,
        value: Number(item?.value) || 0,
      }),
    );
    const total = safeData.reduce((sum, d) => sum + (Number(d.value) || 0), 0);
    return {
      data: safeData,
      angleField: 'value',
      colorField: 'segment',
      radius: 0.8,
      label: {
        type: 'outer',
        formatter: (datum) => {
          const pct = total > 0 ? ((Number(datum.value) || 0) / total) * 100 : 0;
          return `${datum.segment}: ${pct.toFixed(1)}%`;
        },
      },
      tooltip: {
        formatter: (datum) => ({
          name: datum.segment,
          value: `${datum.value}% of customers`,
        }),
      },
    };
  }, [segmentDistribution]);

  const columns = [
    {
      title: 'Customer',
      dataIndex: 'name',
      key: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.industry}</Text>
        </Space>
      ),
    },
    {
      title: 'Segment',
      dataIndex: 'segment',
      key: 'segment',
      render: (value) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: 'Health',
      dataIndex: 'health',
      key: 'health',
      render: (value) => <Tag color={healthColor[value] || 'default'}>{value}</Tag>,
    },
    {
      title: 'Relationship Owner',
      dataIndex: 'owner',
      key: 'owner',
      render: (value) => (
        <Space>
          <UserOutlined />
          <span>{value}</span>
        </Space>
      ),
    },
    {
      title: 'Annual Revenue',
      dataIndex: 'revenue',
      key: 'revenue',
      align: 'right',
      render: (value) => `৳ ${(Number(value) || 0).toLocaleString()}`,
    },
    {
      title: 'Last Contact',
      dataIndex: 'last_contact',
      key: 'last_contact',
      render: (value) => (
        <Space>
          <CalendarOutlined />
          <span>{value}</span>
        </Space>
      ),
    },
    {
      title: 'Engagement Score',
      dataIndex: 'score',
      key: 'score',
      render: (value) => (
        <Badge
          count={value}
          style={{ backgroundColor: Number(value) >= 70 ? '#52c41a' : '#faad14' }}
        />
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Customers</Title>
      <Text type="secondary">
        Manage customer health, segmentation, and engagement to align with the Twist ERP customer
        success plan.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Active Customers"
              value={metrics.totalCustomers}
              prefix={<TeamOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Enterprise Accounts"
              value={metrics.enterpriseCount}
              prefix={<ArrowUpOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="At Risk"
              value={metrics.riskCount}
              prefix={<MailOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Avg Engagement Score"
              value={metrics.avgScore}
              suffix="/100"
              prefix={<UserOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        <Col xs={24} xl={16}>
          <Card
            title="Customer Directory"
            extra={
              <Space>
                <Input.Search
                  allowClear
                  placeholder="Search name, industry, owner"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  style={{ width: 260 }}
                />
                <Segmented
                  options={['ALL', 'Enterprise', 'Mid-Market', 'SMB']}
                  value={segmentFilter}
                  onChange={setSegmentFilter}
                />
                <Button type="primary" icon={<PlusOutlined />} onClick={showCustomerModal}>
                  Add Customer
                </Button>
              </Space>
            }
            loading={loading}
          >
            <Table
              dataSource={filteredCustomers}
              columns={columns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Revenue Trend" style={{ marginBottom: 16 }} loading={loading}>
            <Column {...revenueConfig} height={220} />
          </Card>
          <Card title="Segment Breakdown">
            <Pie {...segmentConfig} height={220} />
          </Card>
        </Col>
      </Row>

      <Modal
        title="Add New Customer"
        open={isCustomerModalOpen}
        onCancel={handleCustomerCancel}
        footer={null}
        destroyOnClose
      >
        <Form layout="vertical" form={customerForm} onFinish={handleCustomerSubmit} initialValues={{ payment_terms: 30, customer_type: 'local' }}>
          <Form.Item name="name" label="Customer Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>
          <Form.Item name="phone" label="Phone">
            <Input />
          </Form.Item>
          <Form.Item name="customer_type" label="Customer Type" rules={[{ required: true }]}>
            <Select options={customerTypeOptions} />
          </Form.Item>
          <Form.Item name="payment_terms" label="Payment Terms (days)">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="receivable_account" label="Receivable Account" rules={[{ required: true }]}> 
            <Select loading={accountsLoading} placeholder="Select receivable account" showSearch optionFilterProp="label">
              {(accounts || []).map((acc) => (
                <Select.Option key={acc.id} value={acc.id} label={`${acc.code} — ${acc.name}`}>
                  {acc.code} — {acc.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button onClick={handleCustomerCancel}>Cancel</Button>
              <Button type="primary" htmlType="submit">Create</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CustomersList;
