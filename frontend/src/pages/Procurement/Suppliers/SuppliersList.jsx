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
  Statistic,
  Typography,
  List,
} from 'antd';
import {
  SafetyCertificateOutlined,
  AlertOutlined,
  AuditOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;

const FALLBACK_SUPPLIERS = [
  {
    id: 1,
    name: 'Dhaka Cotton Mills',
    category: 'Raw Material',
    spend: 4200000,
    on_time: 94,
    quality: 96,
    risk: 'Low',
    last_po: '2024-06-10',
    account_manager: 'Azim Rahman',
  },
  {
    id: 2,
    name: 'ColorSync Ltd.',
    category: 'Chemicals',
    spend: 1650000,
    on_time: 88,
    quality: 91,
    risk: 'Medium',
    last_po: '2024-06-08',
    account_manager: 'Shaila Binte',
  },
  {
    id: 3,
    name: 'Rapid Box Solutions',
    category: 'Packaging',
    spend: 1280000,
    on_time: 91,
    quality: 95,
    risk: 'Low',
    last_po: '2024-06-11',
    account_manager: 'Farhan Hossain',
  },
  {
    id: 4,
    name: 'LogiTrans Express',
    category: 'Logistics',
    spend: 980000,
    on_time: 84,
    quality: 89,
    risk: 'High',
    last_po: '2024-06-06',
    account_manager: 'Marium Hasan',
  },
];

const FALLBACK_SPEND_TREND = [
  { month: 'Jan', spend: 3.2 },
  { month: 'Feb', spend: 3.5 },
  { month: 'Mar', spend: 3.7 },
  { month: 'Apr', spend: 4.1 },
  { month: 'May', spend: 4.3 },
  { month: 'Jun', spend: 4.6 },
];

const SuppliersList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [suppliers, setSuppliers] = useState([]);
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [spendTrend, setSpendTrend] = useState(FALLBACK_SPEND_TREND);

  useEffect(() => {
    loadSuppliers();
  }, [currentCompany]);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setSuppliers(FALLBACK_SUPPLIERS);
        setSpendTrend(FALLBACK_SPEND_TREND);
        return;
      }
      const response = await api.get('/api/v1/procurement/suppliers/');
      const payload = response.data || {};
      const results = Array.isArray(payload.results) ? payload.results : [];
      setSuppliers(results);
      if (Array.isArray(payload.spend_trend)) {
        setSpendTrend(payload.spend_trend);
      }
    } catch (error) {
      console.warn('Suppliers fallback data used:', error?.message);
      setSuppliers(FALLBACK_SUPPLIERS);
      setSpendTrend(FALLBACK_SPEND_TREND);
    } finally {
      setLoading(false);
    }
  };

  const filteredSuppliers = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return (suppliers || []).filter((supplier) => {
      const matchesCategory =
        categoryFilter === 'ALL' || supplier.category === categoryFilter;
      const matchesTerm =
        !term ||
        supplier.name?.toLowerCase().includes(term) ||
        supplier.category?.toLowerCase().includes(term) ||
        supplier.account_manager?.toLowerCase().includes(term);
      return matchesCategory && matchesTerm;
    });
  }, [suppliers, categoryFilter, searchTerm]);

  const metrics = useMemo(() => {
    const totalSpend = filteredSuppliers.reduce(
      (sum, supplier) => sum + (Number(supplier.spend) || 0),
      0,
    );
    const criticalSuppliers = filteredSuppliers.filter((supplier) => supplier.risk === 'High').length;
    const avgQuality =
      filteredSuppliers.reduce((sum, supplier) => sum + (Number(supplier.quality) || 0), 0) /
      (filteredSuppliers.length || 1);
    return {
      totalSpend,
      criticalSuppliers,
      avgQuality: Math.round(avgQuality),
      supplierCount: filteredSuppliers.length,
    };
  }, [filteredSuppliers]);

  const spendConfig = useMemo(() => {
    const safeData = (Array.isArray(spendTrend) ? spendTrend : []).map((item) => ({
      ...item,
      spend: Number(item?.spend) || 0,
    }));
    return {
      data: safeData,
      xField: 'month',
      yField: 'spend',
      smooth: true,
      color: '#13c2c2',
      yAxis: {
        label: {
          formatter: (value) => `${value}M BDT`,
        },
      },
      tooltip: {
        formatter: (datum) => ({
          name: 'Spend',
          value: `${datum.spend}M BDT`,
        }),
      },
    };
  }, [spendTrend]);

  const columns = [
    {
      title: 'Supplier',
      dataIndex: 'name',
      key: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.category}</Text>
        </Space>
      ),
    },
    {
      title: 'Spend (YTD)',
      dataIndex: 'spend',
      key: 'spend',
      align: 'right',
      render: (value) => `৳ ${(Number(value) || 0).toLocaleString()}`,
    },
    {
      title: 'On-Time Delivery',
      dataIndex: 'on_time',
      key: 'on_time',
      render: (value) => <Tag color={Number(value) >= 90 ? 'green' : 'orange'}>{value}%</Tag>,
    },
    {
      title: 'Quality Score',
      dataIndex: 'quality',
      key: 'quality',
      render: (value) => <Tag color={Number(value) >= 95 ? 'blue' : 'gold'}>{value}%</Tag>,
    },
    {
      title: 'Risk',
      dataIndex: 'risk',
      key: 'risk',
      render: (value) => (
        <Tag color={value === 'High' ? 'red' : value === 'Medium' ? 'orange' : 'green'}>{value}</Tag>
      ),
    },
    {
      title: 'Last PO',
      dataIndex: 'last_po',
      key: 'last_po',
    },
    {
      title: 'Account Manager',
      dataIndex: 'account_manager',
      key: 'account_manager',
    },
  ];

  return (
    <div>
      <Title level={2}>Suppliers</Title>
      <Text type="secondary">
        Monitor supplier performance, risk, and spend distribution to stay aligned with the Twist ERP
        sourcing strategy.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Total Active Suppliers"
              value={metrics.supplierCount}
              prefix={<SafetyCertificateOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Spend YTD"
              value={metrics.totalSpend}
              prefix={<DollarOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Avg Quality"
              value={metrics.avgQuality}
              suffix="%"
              prefix={<AuditOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="High Risk"
              value={metrics.criticalSuppliers}
              prefix={<AlertOutlined style={{ color: '#f5222d' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        <Col xs={24} xl={16}>
          <Card
            title="Supplier Directory"
            extra={
              <Space>
                <Input.Search
                  allowClear
                  placeholder="Search supplier, category, manager"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  style={{ width: 260 }}
                />
                <Segmented
                  options={['ALL', 'Raw Material', 'Chemicals', 'Packaging', 'Logistics']}
                  value={categoryFilter}
                  onChange={setCategoryFilter}
                />
              </Space>
            }
            loading={loading}
          >
            <Table
              dataSource={filteredSuppliers}
              columns={columns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Spend Trend" style={{ marginBottom: 16 }} loading={loading}>
            <Column {...spendConfig} height={220} />
          </Card>
          <Card title="Supplier Playbooks">
            <List
              dataSource={[
                {
                  id: 'play-1',
                  title: 'Diversify critical categories',
                  detail: 'Launch dual-sourcing for chemicals',
                },
                {
                  id: 'play-2',
                  title: 'Performance uplift program',
                  detail: 'Quarterly business review with logistics partners',
                },
                {
                  id: 'play-3',
                  title: 'Sustainability assessment',
                  detail: 'Initiate ESG scorecard for top 10 suppliers',
                },
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

export default SuppliersList;
