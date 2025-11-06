import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Divider,
  Drawer,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import {
  DownloadOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  ReloadOutlined,
  DollarOutlined,
  InboxOutlined,
  ShopOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { Column, Pie } from '@ant-design/charts';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import valuationService from '../../../services/valuation';
import api from '../../../services/api';

const { Title, Text } = Typography;

const ValuationReport = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Filters
  const [productFilter, setProductFilter] = useState(null);
  const [warehouseFilter, setWarehouseFilter] = useState(null);
  const [methodFilter, setMethodFilter] = useState(null);
  const [asOfDate, setAsOfDate] = useState(dayjs());

  useEffect(() => {
    if (currentCompany) {
      loadMasterData();
    }
  }, [currentCompany]);

  const loadMasterData = async () => {
    try {
      const [productsRes, warehousesRes] = await Promise.all([
        api.get('/api/v1/inventory/products/'),
        api.get('/api/v1/inventory/warehouses/'),
      ]);

      setProducts(productsRes.data?.results || productsRes.data || []);
      setWarehouses(warehousesRes.data?.results || warehousesRes.data || []);
    } catch (error) {
      console.error('Failed to load master data:', error);
    }
  };

  const loadReport = useCallback(async () => {
    setLoading(true);
    try {
      const filters = {};
      if (productFilter) filters.product_id = productFilter;
      if (warehouseFilter) filters.warehouse_id = warehouseFilter;
      if (methodFilter) filters.method = methodFilter;

      const report = await valuationService.getValuationReport(filters);
      setReportData(report);
    } catch (error) {
      console.error('Failed to load valuation report:', error);
      message.error(error?.response?.data?.detail || 'Failed to load valuation report');
      setReportData(null);
    } finally {
      setLoading(false);
    }
  }, [productFilter, warehouseFilter, methodFilter]);

  useEffect(() => {
    if (currentCompany) {
      loadReport();
    }
  }, [productFilter, warehouseFilter, methodFilter, currentCompany, loadReport]);

  const handleViewDetails = (record) => {
    setSelectedItem(record);
    setDrawerOpen(true);
  };

  const handleExport = (format) => {
    message.info(`Export to ${format.toUpperCase()} - Feature coming soon!`);
    // TODO: Implement export functionality
  };

  // Calculate statistics
  const statistics = useMemo(() => {
    if (!reportData || !reportData.items) {
      return {
        totalItems: 0,
        totalValue: 0,
        totalQty: 0,
        avgValue: 0,
      };
    }

    const items = reportData.items;
    const totalItems = items.length;
    const totalValue = items.reduce((sum, item) => sum + parseFloat(item.total_value || 0), 0);
    const totalQty = items.reduce((sum, item) => sum + parseFloat(item.qty_on_hand || 0), 0);
    const avgValue = totalItems > 0 ? totalValue / totalItems : 0;

    return {
      totalItems,
      totalValue,
      totalQty,
      avgValue,
    };
  }, [reportData]);

  // Prepare chart data
  const warehouseChartData = useMemo(() => {
    if (!reportData || !reportData.items) return [];

    const warehouseMap = {};
    reportData.items.forEach((item) => {
      const warehouse = item.warehouse_name || 'Unknown';
      if (!warehouseMap[warehouse]) {
        warehouseMap[warehouse] = 0;
      }
      warehouseMap[warehouse] += parseFloat(item.total_value || 0);
    });

    return Object.entries(warehouseMap).map(([warehouse, value]) => ({
      warehouse,
      value,
    }));
  }, [reportData]);

  const methodChartData = useMemo(() => {
    if (!reportData || !reportData.items) return [];

    const methodMap = {};
    reportData.items.forEach((item) => {
      const method = item.valuation_method || 'FIFO';
      if (!methodMap[method]) {
        methodMap[method] = 0;
      }
      methodMap[method] += parseFloat(item.total_value || 0);
    });

    return Object.entries(methodMap).map(([method, value]) => ({
      method,
      value,
    }));
  }, [reportData]);

  const warehouseChartConfig = {
    data: warehouseChartData,
    xField: 'warehouse',
    yField: 'value',
    label: {
      position: 'top',
      formatter: (datum) => valuationService.formatCurrency(datum.value),
    },
    xAxis: {
      label: {
        autoRotate: true,
      },
    },
    yAxis: {
      label: {
        formatter: (value) => `${(value / 1000).toFixed(0)}K`,
      },
    },
  };

  const methodChartConfig = {
    data: methodChartData,
    angleField: 'value',
    colorField: 'method',
    radius: 0.8,
    innerRadius: 0.6,
    label: {
      type: 'outer',
      content: '{name} {percentage}',
    },
    interactions: [{ type: 'element-active' }],
    legend: {
      position: 'bottom',
    },
  };

  const columns = [
    {
      title: 'Product',
      key: 'product',
      fixed: 'left',
      width: 250,
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
      width: 180,
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
      width: 150,
      render: (value) => (
        <Tag
          color={valuationService.getMethodColor(value || 'FIFO')}
          style={{ fontWeight: 500 }}
        >
          {value || 'FIFO'}
        </Tag>
      ),
    },
    {
      title: 'Qty on Hand',
      dataIndex: 'qty_on_hand',
      key: 'qty_on_hand',
      align: 'right',
      width: 120,
      render: (value) => parseFloat(value || 0).toLocaleString(),
    },
    {
      title: 'Unit Cost',
      dataIndex: 'unit_cost',
      key: 'unit_cost',
      align: 'right',
      width: 120,
      render: (value) => valuationService.formatCurrency(value || 0),
    },
    {
      title: 'Total Value',
      dataIndex: 'total_value',
      key: 'total_value',
      align: 'right',
      width: 150,
      render: (value) => (
        <Text strong>{valuationService.formatCurrency(value || 0)}</Text>
      ),
    },
    {
      title: 'Open Layers',
      dataIndex: 'open_layers',
      key: 'open_layers',
      align: 'center',
      width: 100,
      render: (value) => <Tag color="blue">{value || 0}</Tag>,
    },
    {
      title: 'Last Movement',
      dataIndex: 'last_movement_date',
      key: 'last_movement_date',
      width: 150,
      render: (value) => (value ? dayjs(value).format('YYYY-MM-DD') : 'N/A'),
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => handleViewDetails(record)}
        >
          Details
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ marginBottom: 0 }}>
            Inventory Valuation Report
          </Title>
          <Text type="secondary">
            Comprehensive inventory valuation across products and warehouses
          </Text>
        </Col>
        <Col>
          <Space>
            <Tooltip title="Export to Excel">
              <Button
                icon={<FileExcelOutlined />}
                onClick={() => handleExport('excel')}
              >
                Excel
              </Button>
            </Tooltip>
            <Tooltip title="Export to PDF">
              <Button
                icon={<FilePdfOutlined />}
                onClick={() => handleExport('pdf')}
              >
                PDF
              </Button>
            </Tooltip>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={loadReport}
              loading={loading}
            >
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Items"
              value={statistics.totalItems}
              prefix={<InboxOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Inventory Value"
              value={statistics.totalValue}
              precision={2}
              prefix={<DollarOutlined style={{ color: '#52c41a' }} />}
              suffix={currentCompany?.currency_code || ''}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Quantity"
              value={statistics.totalQty}
              precision={2}
              prefix={<ShopOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Avg Value per Item"
              value={statistics.avgValue}
              precision={2}
              prefix={<BarChartOutlined style={{ color: '#faad14' }} />}
              suffix={currentCompany?.currency_code || ''}
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
            <DatePicker
              placeholder="As of Date"
              style={{ width: '100%' }}
              value={asOfDate}
              onChange={setAsOfDate}
              format="YYYY-MM-DD"
            />
          </Col>
        </Row>
      </Card>

      {/* Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="Valuation by Warehouse" loading={loading}>
            {warehouseChartData.length > 0 ? (
              <Column {...warehouseChartConfig} height={300} />
            ) : (
              <Alert type="info" message="No data available" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Valuation by Method" loading={loading}>
            {methodChartData.length > 0 ? (
              <Pie {...methodChartConfig} height={300} />
            ) : (
              <Alert type="info" message="No data available" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Main Table */}
      <Card title="Detailed Valuation Report">
        {reportData && reportData.items && reportData.items.length > 0 ? (
          <>
            <Table
              dataSource={reportData.items}
              columns={columns}
              rowKey={(record) => `${record.product}-${record.warehouse}`}
              loading={loading}
              pagination={{ pageSize: 20 }}
              scroll={{ x: 1600 }}
              summary={(pageData) => {
                const totalValue = pageData.reduce(
                  (sum, record) => sum + parseFloat(record.total_value || 0),
                  0
                );
                const totalQty = pageData.reduce(
                  (sum, record) => sum + parseFloat(record.qty_on_hand || 0),
                  0
                );

                return (
                  <Table.Summary fixed>
                    <Table.Summary.Row>
                      <Table.Summary.Cell index={0} colSpan={3}>
                        <Text strong>Page Total</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={3} align="right">
                        <Text strong>{totalQty.toLocaleString()}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={4} />
                      <Table.Summary.Cell index={5} align="right">
                        <Text strong>{valuationService.formatCurrency(totalValue)}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={6} colSpan={3} />
                    </Table.Summary.Row>
                  </Table.Summary>
                );
              }}
            />
            <Divider />
            <Row justify="end">
              <Col>
                <Space direction="vertical" size="small" style={{ textAlign: 'right' }}>
                  <Text type="secondary">Report Generated: {dayjs().format('YYYY-MM-DD HH:mm')}</Text>
                  {reportData.total_value && (
                    <Title level={4} style={{ margin: 0 }}>
                      Grand Total: {valuationService.formatCurrency(reportData.total_value)}
                    </Title>
                  )}
                </Space>
              </Col>
            </Row>
          </>
        ) : (
          <Alert
            type="info"
            showIcon
            message="No Data Available"
            description="Adjust filters or check that inventory data exists in the system."
          />
        )}
      </Card>

      {/* Details Drawer */}
      <Drawer
        title="Item Valuation Details"
        placement="right"
        width={600}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedItem(null);
        }}
      >
        {selectedItem && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Card>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Product">
                  <Text strong>{selectedItem.product_name}</Text>
                  <br />
                  <Text type="secondary">{selectedItem.product_code}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Warehouse">
                  <Text strong>{selectedItem.warehouse_name}</Text>
                  <br />
                  <Text type="secondary">{selectedItem.warehouse_code}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Valuation Method">
                  <Tag
                    color={valuationService.getMethodColor(selectedItem.valuation_method || 'FIFO')}
                  >
                    {selectedItem.valuation_method || 'FIFO'}
                  </Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Valuation Summary">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Quantity on Hand">
                  {parseFloat(selectedItem.qty_on_hand || 0).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="Unit Cost">
                  {valuationService.formatCurrency(selectedItem.unit_cost || 0)}
                </Descriptions.Item>
                <Descriptions.Item label="Total Value">
                  <Text strong style={{ fontSize: 16 }}>
                    {valuationService.formatCurrency(selectedItem.total_value || 0)}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="Open Cost Layers">
                  <Tag color="blue">{selectedItem.open_layers || 0} layers</Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Movement History">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Last Movement">
                  {selectedItem.last_movement_date
                    ? dayjs(selectedItem.last_movement_date).format('YYYY-MM-DD HH:mm')
                    : 'No movements'}
                </Descriptions.Item>
                <Descriptions.Item label="Last Movement Type">
                  {selectedItem.last_movement_type || 'N/A'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Space>
              <Button
                type="primary"
                onClick={async () => {
                  try {
                    const currentCost = await valuationService.getCurrentCost(
                      selectedItem.product,
                      selectedItem.warehouse
                    );
                    Modal.info({
                      title: 'Current Cost Information',
                      content: (
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="Current Cost">
                            {valuationService.formatCurrency(currentCost.current_cost || 0)}
                          </Descriptions.Item>
                          <Descriptions.Item label="Method Used">
                            {currentCost.method_used || 'FIFO'}
                          </Descriptions.Item>
                          <Descriptions.Item label="As of">
                            {dayjs().format('YYYY-MM-DD HH:mm')}
                          </Descriptions.Item>
                        </Descriptions>
                      ),
                    });
                  } catch (error) {
                    message.error('Failed to fetch current cost');
                  }
                }}
              >
                Get Current Cost
              </Button>
              <Button
                onClick={() => {
                  // Navigate to cost layers view with filters
                  message.info('Navigate to Cost Layers view - Feature coming soon!');
                }}
              >
                View Cost Layers
              </Button>
            </Space>
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default ValuationReport;
