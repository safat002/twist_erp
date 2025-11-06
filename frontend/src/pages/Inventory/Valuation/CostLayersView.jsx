import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Progress,
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
  EyeOutlined,
  InfoCircleOutlined,
  ClusterOutlined,
  LockOutlined,
  UnlockOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import valuationService from '../../../services/valuation';
import api from '../../../services/api';

const { Title, Text } = Typography;

const CostLayersView = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [layers, setLayers] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [selectedLayer, setSelectedLayer] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);
  const [summaryData, setSummaryData] = useState(null);

  // Filters
  const [productFilter, setProductFilter] = useState(null);
  const [warehouseFilter, setWarehouseFilter] = useState(null);
  const [batchFilter, setBatchFilter] = useState('');
  const [openOnlyFilter, setOpenOnlyFilter] = useState(true);

  useEffect(() => {
    if (currentCompany) {
      loadData();
    }
  }, [currentCompany]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [productsRes, warehousesRes] = await Promise.all([
        api.get('/api/v1/inventory/products/'),
        api.get('/api/v1/inventory/warehouses/'),
      ]);

      setProducts(productsRes.data?.results || productsRes.data || []);
      setWarehouses(warehousesRes.data?.results || warehousesRes.data || []);

      // Load layers with filters
      await loadLayers();
    } catch (error) {
      console.error('Failed to load data:', error);
      message.error(error?.response?.data?.detail || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadLayers = useCallback(async () => {
    try {
      const filters = {};
      if (productFilter) filters.product = productFilter;
      if (warehouseFilter) filters.warehouse = warehouseFilter;
      if (openOnlyFilter) filters.open_only = true;
      if (batchFilter) filters.batch_no = batchFilter;

      const layersRes = await valuationService.getCostLayers(filters);
      setLayers(layersRes?.results || layersRes || []);
    } catch (error) {
      console.error('Failed to load cost layers:', error);
      message.error(error?.response?.data?.detail || 'Failed to load cost layers');
    }
  }, [productFilter, warehouseFilter, openOnlyFilter, batchFilter]);

  useEffect(() => {
    if (currentCompany) {
      loadLayers();
    }
  }, [productFilter, warehouseFilter, openOnlyFilter, batchFilter, currentCompany, loadLayers]);

  const handleViewDetails = (record) => {
    setSelectedLayer(record);
    setDrawerOpen(true);
  };

  const handleViewSummary = async (productId, warehouseId) => {
    try {
      const summary = await valuationService.getCostLayerSummary(productId, warehouseId);
      setSummaryData(summary);
      setSummaryModalOpen(true);
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Failed to load summary');
    }
  };

  // Calculate statistics
  const statistics = useMemo(() => {
    const total = layers.length;
    const open = layers.filter((l) => !l.is_closed).length;
    const closed = layers.filter((l) => l.is_closed).length;
    const totalValue = layers.reduce((sum, l) => sum + parseFloat(l.cost_remaining || 0), 0);
    const totalQty = layers.reduce((sum, l) => sum + parseFloat(l.qty_remaining || 0), 0);

    return {
      total,
      open,
      closed,
      totalValue,
      totalQty,
    };
  }, [layers]);

  const getStatusColor = (percentConsumed) => {
    if (percentConsumed >= 100) return 'exception';
    if (percentConsumed >= 90) return 'normal';
    if (percentConsumed >= 50) return 'active';
    return 'success';
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
      title: 'Receipt Date',
      dataIndex: 'receipt_date',
      key: 'receipt_date',
      render: (value) => (value ? dayjs(value).format('YYYY-MM-DD HH:mm') : 'N/A'),
    },
    {
      title: 'FIFO Seq',
      dataIndex: 'fifo_sequence',
      key: 'fifo_sequence',
      align: 'center',
      render: (value) => (
        <Tag color="blue" style={{ fontFamily: 'monospace' }}>
          #{value}
        </Tag>
      ),
    },
    {
      title: 'Quantity',
      key: 'quantity',
      align: 'right',
      render: (_, record) => (
        <Space direction="vertical" size={0} style={{ textAlign: 'right' }}>
          <Text>
            {parseFloat(record.qty_remaining || 0).toLocaleString()} /{' '}
            {parseFloat(record.qty_received || 0).toLocaleString()}
          </Text>
          <Progress
            percent={parseFloat(record.percentage_consumed || 0).toFixed(1)}
            size="small"
            status={getStatusColor(parseFloat(record.percentage_consumed || 0))}
            strokeWidth={6}
          />
        </Space>
      ),
    },
    {
      title: 'Cost/Unit',
      key: 'cost',
      align: 'right',
      render: (_, record) => (
        <Space direction="vertical" size={0} style={{ textAlign: 'right' }}>
          <Text strong>
            {valuationService.formatCurrency(record.effective_cost_per_unit || record.cost_per_unit)}
          </Text>
          {record.landed_cost_adjustment && parseFloat(record.landed_cost_adjustment) !== 0 && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              +{valuationService.formatCurrency(record.landed_cost_adjustment)} landed
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Remaining Value',
      dataIndex: 'cost_remaining',
      key: 'cost_remaining',
      align: 'right',
      render: (value) => (
        <Text strong>{valuationService.formatCurrency(value || 0)}</Text>
      ),
    },
    {
      title: 'Batch/Serial',
      key: 'batch',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.batch_no && <Tag color="purple">{record.batch_no}</Tag>}
          {record.serial_no && <Tag color="cyan">{record.serial_no}</Tag>}
          {!record.batch_no && !record.serial_no && <Text type="secondary">-</Text>}
        </Space>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => (
        <Space>
          <Badge
            status={record.is_closed ? 'default' : 'success'}
            text={record.is_closed ? 'Closed' : 'Open'}
          />
          {record.is_standard_cost && <Tag color="gold">Standard</Tag>}
          {record.immutable_after_post && <LockOutlined style={{ color: '#999' }} />}
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
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            Details
          </Button>
          <Button
            type="link"
            size="small"
            icon={<BarChartOutlined />}
            onClick={() => handleViewSummary(record.product, record.warehouse)}
          >
            Summary
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ marginBottom: 0 }}>
            Cost Layers
          </Title>
          <Text type="secondary">
            View and track inventory cost layers across products and warehouses
          </Text>
        </Col>
      </Row>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Layers"
              value={statistics.total}
              prefix={<ClusterOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Open Layers"
              value={statistics.open}
              prefix={<UnlockOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Remaining Quantity"
              value={statistics.totalQty.toFixed(2)}
              precision={2}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Value"
              value={statistics.totalValue.toFixed(2)}
              precision={2}
              prefix={currentCompany?.currency_symbol || '৳'}
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
            <Input
              allowClear
              placeholder="Filter by Batch Number"
              value={batchFilter}
              onChange={(e) => setBatchFilter(e.target.value)}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Space>
              <Switch checked={openOnlyFilter} onChange={setOpenOnlyFilter} />
              <Text>Open Only</Text>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Main Table */}
      <Card>
        {layers.length === 0 && !loading ? (
          <Alert
            type="info"
            showIcon
            message="No Cost Layers Found"
            description="Cost layers are created automatically when goods are received. Adjust filters or receive inventory to see cost layers."
          />
        ) : (
          <Table
            dataSource={layers}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 20 }}
            scroll={{ x: 1400 }}
          />
        )}
      </Card>

      {/* Details Drawer */}
      <Drawer
        title="Cost Layer Details"
        placement="right"
        width={600}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedLayer(null);
        }}
      >
        {selectedLayer && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Card>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Product">
                  <Text strong>{selectedLayer.product_name}</Text>
                  <br />
                  <Text type="secondary">{selectedLayer.product_code}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Warehouse">
                  <Text strong>{selectedLayer.warehouse_name}</Text>
                  <br />
                  <Text type="secondary">{selectedLayer.warehouse_code}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Receipt Date">
                  {dayjs(selectedLayer.receipt_date).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
                <Descriptions.Item label="FIFO Sequence">
                  <Tag color="blue">#{selectedLayer.fifo_sequence}</Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Quantity Details">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Quantity Received">
                  {parseFloat(selectedLayer.qty_received || 0).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="Quantity Remaining">
                  {parseFloat(selectedLayer.qty_remaining || 0).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="Quantity Consumed">
                  {(
                    parseFloat(selectedLayer.qty_received || 0) -
                    parseFloat(selectedLayer.qty_remaining || 0)
                  ).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="Consumption %">
                  <Progress
                    percent={parseFloat(selectedLayer.percentage_consumed || 0).toFixed(1)}
                    status={getStatusColor(parseFloat(selectedLayer.percentage_consumed || 0))}
                  />
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Cost Details">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Base Cost/Unit">
                  {valuationService.formatCurrency(selectedLayer.cost_per_unit)}
                </Descriptions.Item>
                <Descriptions.Item label="Landed Cost Adjustment">
                  {valuationService.formatCurrency(selectedLayer.landed_cost_adjustment || 0)}
                </Descriptions.Item>
                <Descriptions.Item label="Effective Cost/Unit">
                  <Text strong>
                    {valuationService.formatCurrency(
                      selectedLayer.effective_cost_per_unit || selectedLayer.cost_per_unit
                    )}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="Total Cost">
                  {valuationService.formatCurrency(selectedLayer.total_cost)}
                </Descriptions.Item>
                <Descriptions.Item label="Cost Remaining">
                  <Text strong>
                    {valuationService.formatCurrency(selectedLayer.cost_remaining)}
                  </Text>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Additional Information">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Batch Number">
                  {selectedLayer.batch_no || <Text type="secondary">Not specified</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="Serial Number">
                  {selectedLayer.serial_no || <Text type="secondary">Not specified</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="Source Document">
                  {selectedLayer.source_document_type} #{selectedLayer.source_document_id}
                </Descriptions.Item>
                <Descriptions.Item label="Standard Cost Layer">
                  {selectedLayer.is_standard_cost ? 'Yes' : 'No'}
                </Descriptions.Item>
                <Descriptions.Item label="Immutable After Post">
                  {selectedLayer.immutable_after_post ? 'Yes' : 'No'}
                </Descriptions.Item>
                <Descriptions.Item label="Layer Status">
                  <Badge
                    status={selectedLayer.is_closed ? 'default' : 'success'}
                    text={selectedLayer.is_closed ? 'Closed' : 'Open'}
                  />
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {selectedLayer.adjustment_reason && (
              <Card title="Adjustment History">
                <Alert
                  type="info"
                  showIcon
                  icon={<InfoCircleOutlined />}
                  message={`Adjusted on ${dayjs(selectedLayer.adjustment_date).format('YYYY-MM-DD')}`}
                  description={selectedLayer.adjustment_reason}
                />
              </Card>
            )}
          </Space>
        )}
      </Drawer>

      {/* Summary Modal */}
      <Modal
        title="Inventory Value Summary"
        open={summaryModalOpen}
        onCancel={() => {
          setSummaryModalOpen(false);
          setSummaryData(null);
        }}
        footer={[
          <Button key="close" onClick={() => setSummaryModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={700}
      >
        {summaryData && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Total Inventory Value"
                  value={summaryData.inventory_value || 0}
                  precision={2}
                  prefix={currentCompany?.currency_symbol || '৳'}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Open Layers"
                  value={summaryData.open_layers?.length || 0}
                />
              </Col>
            </Row>

            {summaryData.open_layers && summaryData.open_layers.length > 0 && (
              <Card title="Open Cost Layers" size="small">
                <Table
                  dataSource={summaryData.open_layers}
                  columns={[
                    {
                      title: 'FIFO #',
                      dataIndex: 'fifo_sequence',
                      key: 'fifo_sequence',
                      render: (value) => <Tag color="blue">#{value}</Tag>,
                    },
                    {
                      title: 'Qty Remaining',
                      dataIndex: 'qty_remaining',
                      key: 'qty_remaining',
                      render: (value) => parseFloat(value || 0).toLocaleString(),
                    },
                    {
                      title: 'Cost/Unit',
                      dataIndex: 'cost_per_unit',
                      key: 'cost_per_unit',
                      render: (value) => valuationService.formatCurrency(value),
                    },
                    {
                      title: 'Value',
                      dataIndex: 'cost_remaining',
                      key: 'cost_remaining',
                      render: (value) => valuationService.formatCurrency(value),
                    },
                  ]}
                  pagination={false}
                  size="small"
                />
              </Card>
            )}
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default CostLayersView;
