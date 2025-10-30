import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Button,
  Space,
  Segmented,
  Input,
  Tag,
  Statistic,
  List,
  Typography,
  Tooltip,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  BarcodeOutlined,
  ShopOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  AlertOutlined,
} from '@ant-design/icons';
import { Area, Rose } from '@ant-design/charts';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;

const FALLBACK_PRODUCTS = [
  {
    id: 'SKU-1001',
    sku: 'FAB-ROLL-60',
    name: 'Cotton Fabric Roll 60 GSM',
    category: 'Raw Material',
    segment: 'A',
    uom: 'Roll',
    stock_on_hand: 420,
    reorder_point: 350,
    status: 'Available',
    warehouse: 'HQ Distribution',
    supplier: 'Dhaka Cotton Mills',
    last_movement: '2024-06-10',
  },
  {
    id: 'SKU-1002',
    sku: 'DYE-NVY',
    name: 'Reactive Dye Navy Blue 5kg',
    category: 'Chemicals',
    segment: 'B',
    uom: 'Bucket',
    stock_on_hand: 28,
    reorder_point: 40,
    status: 'Low Stock',
    warehouse: 'Print Unit Store',
    supplier: 'ColorSync Ltd.',
    last_movement: '2024-06-12',
  },
  {
    id: 'SKU-1003',
    sku: 'BTN-PLASTIC',
    name: 'Shirt Buttons (Pack of 500)',
    category: 'Accessories',
    segment: 'A',
    uom: 'Pack',
    stock_on_hand: 980,
    reorder_point: 600,
    status: 'Available',
    warehouse: 'HQ Distribution',
    supplier: 'Accessories Hub',
    last_movement: '2024-06-09',
  },
  {
    id: 'SKU-1004',
    sku: 'ZIP-NYLON',
    name: 'Nylon Zipper 18"',
    category: 'Accessories',
    segment: 'C',
    uom: 'Piece',
    stock_on_hand: 210,
    reorder_point: 400,
    status: 'Critical',
    warehouse: 'EU Hub',
    supplier: 'Global Trims',
    last_movement: '2024-06-07',
  },
  {
    id: 'SKU-1005',
    sku: 'BOX-EXP',
    name: 'Export Carton Box',
    category: 'Packaging',
    segment: 'B',
    uom: 'Piece',
    stock_on_hand: 1250,
    reorder_point: 800,
    status: 'Available',
    warehouse: 'Fulfilment Centre',
    supplier: 'Rapid Box Solutions',
    last_movement: '2024-06-11',
  },
];

const FALLBACK_CATEGORY_DISTRIBUTION = [
  { category: 'Raw Material', value: 34 },
  { category: 'Accessories', value: 28 },
  { category: 'Chemicals', value: 12 },
  { category: 'Packaging', value: 18 },
  { category: 'Finished Goods', value: 8 },
];

const FALLBACK_TURNOVER = [
  { month: 'Jan', turnover: 4.2 },
  { month: 'Feb', turnover: 4.5 },
  { month: 'Mar', turnover: 4.8 },
  { month: 'Apr', turnover: 5.1 },
  { month: 'May', turnover: 5.3 },
  { month: 'Jun', turnover: 5.7 },
];

const statusColorMap = {
  Available: 'green',
  'Low Stock': 'gold',
  Critical: 'red',
  Blocked: 'volcano',
};

const segmentColorMap = {
  A: '#722ed1',
  B: '#13c2c2',
  C: '#faad14',
};

const ProductsList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [categoryDistribution, setCategoryDistribution] = useState(FALLBACK_CATEGORY_DISTRIBUTION);
  const [turnoverTrend, setTurnoverTrend] = useState(FALLBACK_TURNOVER);

  useEffect(() => {
    loadProducts();
  }, [currentCompany]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setProducts(FALLBACK_PRODUCTS);
        setCategoryDistribution(FALLBACK_CATEGORY_DISTRIBUTION);
        setTurnoverTrend(FALLBACK_TURNOVER);
        return;
      }
      const response = await api.get('/api/v1/inventory/products/');
      const payload = response.data || {};
      const results = Array.isArray(payload.results) ? payload.results : [];
      setProducts(results);
      if (Array.isArray(payload.category_distribution)) {
        setCategoryDistribution(payload.category_distribution);
      }
      if (Array.isArray(payload.turnover_trend)) {
        setTurnoverTrend(payload.turnover_trend);
      }
    } catch (error) {
      console.warn('Products fallback data used:', error?.message);
      setProducts(FALLBACK_PRODUCTS);
      setCategoryDistribution(FALLBACK_CATEGORY_DISTRIBUTION);
      setTurnoverTrend(FALLBACK_TURNOVER);
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return (products || []).filter((product) => {
      const matchesTerm =
        !term ||
        product.name?.toLowerCase().includes(term) ||
        product.sku?.toLowerCase().includes(term) ||
        product.category?.toLowerCase().includes(term);
      const matchesStatus =
        statusFilter === 'ALL' ||
        product.status === statusFilter ||
        (statusFilter === 'LOW' && product.status === 'Low Stock') ||
        (statusFilter === 'CRITICAL' && product.status === 'Critical');
      return matchesTerm && matchesStatus;
    });
  }, [products, searchTerm, statusFilter]);

  const metrics = useMemo(() => {
    const totalSkus = filteredProducts.length;
    const lowStock = filteredProducts.filter((item) => item.status === 'Low Stock').length;
    const critical = filteredProducts.filter((item) => item.status === 'Critical').length;
    const blocked = filteredProducts.filter((item) => item.status === 'Blocked').length;
    return {
      totalSkus,
      lowStock,
      critical,
      blocked,
    };
  }, [filteredProducts]);

  const turnoverConfig = useMemo(() => {
    const safeData = (Array.isArray(turnoverTrend) ? turnoverTrend : []).map((item) => ({
      ...item,
      turnover: Number(item?.turnover) || 0,
    }));
    return {
      data: safeData,
      xField: 'month',
      yField: 'turnover',
      smooth: true,
      color: '#1890ff',
      yAxis: {
        label: {
          formatter: (value) => `${value}x`,
        },
      },
      tooltip: {
        formatter: (datum) => ({
          name: 'Turnover',
          value: `${Number(datum.turnover).toFixed(1)}x`,
        }),
      },
    };
  }, [turnoverTrend]);

  const categoryConfig = useMemo(() => {
    const safeData = (Array.isArray(categoryDistribution) ? categoryDistribution : []).map(
      (item) => ({
        ...item,
        value: Number(item?.value) || 0,
      }),
    );
    return {
      data: safeData,
      xField: 'category',
      yField: 'value',
      seriesField: 'category',
      legend: { position: 'bottom' },
      colorField: ({ category }) => category,
      radius: 0.9,
      innerRadius: 0.5,
      tooltip: {
        formatter: (datum) => ({
          name: datum.category,
          value: `${datum.value}% of SKUs`,
        }),
      },
    };
  }, [categoryDistribution]);

  const columns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (value) => (
        <Space>
          <BarcodeOutlined />
          <Text strong>{value}</Text>
        </Space>
      ),
    },
    {
      title: 'Product',
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
      title: 'Segment',
      dataIndex: 'segment',
      key: 'segment',
      render: (value) => (
        <Tag color={segmentColorMap[value] || 'default'}>Class {value || '–'}</Tag>
      ),
    },
    {
      title: 'Stock',
      dataIndex: 'stock_on_hand',
      key: 'stock_on_hand',
      align: 'right',
      render: (value, record) => (
        <Space direction="vertical" size={0} style={{ textAlign: 'right' }}>
          <Text>{`${(Number(value) || 0).toLocaleString()} ${record.uom || ''}`}</Text>
          <Text type="secondary">Reorder @ {(Number(record.reorder_point) || 0).toLocaleString()}</Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => (
        <Tag color={statusColorMap[value] || 'default'}>{value || 'N/A'}</Tag>
      ),
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse',
      key: 'warehouse',
    },
    {
      title: 'Supplier',
      dataIndex: 'supplier',
      key: 'supplier',
    },
    {
      title: 'Last Movement',
      dataIndex: 'last_movement',
      key: 'last_movement',
    },
  ];

  return (
    <div>
      <Title level={2}>Products & SKUs</Title>
      <Text type="secondary">
        Monitor SKU health, ABC contribution, and fast movers to align with the Twist ERP
        inventory blueprint.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Active SKUs"
              value={metrics.totalSkus}
              prefix={<ShopOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Low Stock"
              value={metrics.lowStock}
              prefix={<WarningOutlined style={{ color: '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Critical Items"
              value={metrics.critical}
              prefix={<AlertOutlined style={{ color: '#f5222d' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Blocked / QC Hold"
              value={metrics.blocked}
              prefix={<ThunderboltOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        <Col xs={24} xl={16}>
          <Card
            title="Product Catalogue"
            extra={
              <Space>
                <Input.Search
                  allowClear
                  placeholder="Search SKU, product, category"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  style={{ width: 260 }}
                />
                <Segmented
                  options={[
                    { label: 'All', value: 'ALL' },
                    { label: 'Low Stock', value: 'LOW' },
                    { label: 'Critical', value: 'CRITICAL' },
                    { label: 'Available', value: 'Available' },
                  ]}
                  value={statusFilter}
                  onChange={setStatusFilter}
                />
                <Button type="primary" icon={<PlusOutlined />}>
                  New SKU
                </Button>
              </Space>
            }
          >
            <Table
              dataSource={filteredProducts}
              columns={columns}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 15 }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Turnover Trend" style={{ marginBottom: 16 }} loading={loading}>
            <Area {...turnoverConfig} height={220} />
          </Card>
          <Card title="Category Composition" style={{ marginBottom: 16 }} loading={loading}>
            <Rose {...categoryConfig} height={220} />
          </Card>
          <Card title="Fast Movers">
            <List
              dataSource={filteredProducts.slice(0, 5)}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space>
                    <Badge color={segmentColorMap[item.segment]} />
                    <Space direction="vertical" size={0}>
                      <Text strong>{item.name}</Text>
                      <Text type="secondary">
                        {item.sku} · {item.segment ? `Class ${item.segment}` : 'Unclassified'}
                      </Text>
                    </Space>
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

export default ProductsList;
