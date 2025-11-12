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
  Drawer,
  Form,
  Select,
  InputNumber,
  Switch,
  message,
  Alert,
  DatePicker,
  Checkbox,
  Divider,
  Popconfirm,
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
import { useNavigate, Link } from 'react-router-dom';

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

const ROUNDING_OPTIONS = [
  { label: 'No Rounding', value: 'NO_ROUNDING' },
  { label: 'Round Up', value: 'ROUND_UP' },
  { label: 'Round Down', value: 'ROUND_DOWN' },
  { label: 'Round Nearest', value: 'ROUND_NEAREST' },
  { label: 'Truncate', value: 'TRUNCATE' },
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

const normalizeFallbackProduct = (product) => ({
  ...product,
  budgetLinked: false,
  budgetCode: product.sku,
  budgetName: product.name,
  baseUom: product.uom,
  baseStandardCost: 0,
  budgetItemId: null,
});

const ProductsList = () => {
  const navigate = useNavigate();
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [categoryDistribution, setCategoryDistribution] = useState(FALLBACK_CATEGORY_DISTRIBUTION);
  const [turnoverTrend, setTurnoverTrend] = useState(FALLBACK_TURNOVER);
  const [supplierDrawer, setSupplierDrawer] = useState({ visible: false, item: null });
  const [itemSuppliers, setItemSuppliers] = useState([]);
  const [supplierOptions, setSupplierOptions] = useState([]);
  const [supplierLoading, setSupplierLoading] = useState(false);
  const [supplierForm] = Form.useForm();
  const [fefoDrawer, setFefoDrawer] = useState({ visible: false, item: null });
  const [fefoConfigs, setFefoConfigs] = useState([]);
  const [warehouseOptions, setWarehouseOptions] = useState([]);
  const [fefoLoading, setFefoLoading] = useState(false);
  const [fefoForm] = Form.useForm();
  const [uomDrawer, setUomDrawer] = useState({ visible: false, item: null });
  const [uomConversions, setUomConversions] = useState([]);
  const [uomOptions, setUomOptions] = useState([]);
  const [uomLoading, setUomLoading] = useState(false);
  const [uomForm] = Form.useForm();

  useEffect(() => {
    loadProducts();
  }, [currentCompany]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const decoratedFallback = FALLBACK_PRODUCTS.map(normalizeFallbackProduct);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setProducts(decoratedFallback);
        setCategoryDistribution(FALLBACK_CATEGORY_DISTRIBUTION);
        setTurnoverTrend(FALLBACK_TURNOVER);
        return;
      }
      const response = await api.get('/api/v1/inventory/items/', {
        params: { ordering: 'code' },
      });
      const payload = response.data || {};
      const results = Array.isArray(payload.results) ? payload.results : Array.isArray(payload) ? payload : [];
      const normalized = results.map((record) => {
        const profile = record.operational_profile || {};
        const configs = Array.isArray(record.warehouse_configs) ? record.warehouse_configs : [];
        const globalConfig = configs.find((cfg) => !cfg.warehouse) || configs[0] || {};
        const budgetLinked = Boolean(record.budget_item);
        const budgetCode = record.budget_item_code || record.code;
        const budgetName = record.budget_item_name || record.name;
        const baseUom = record.budget_item_uom_code || record.uom_code || '';
        const baseStandardCost = Number(
          record.budget_item_standard_price ?? record.standard_cost ?? 0,
        );
        return {
          id: record.id,
          sku: budgetCode,
          code: record.code,
          name: record.name,
          budgetLinked,
          budgetCode,
          budgetName,
          baseUom,
          baseStandardCost,
          budgetItemId: record.budget_item,
          category: record.category_name || '',
          segment: profile.storage_class || 'A',
          uom: record.uom_code || '',
          purchaseUom: profile.purchase_uom_code || record.uom_code || '',
          salesUom: profile.sales_uom_code || record.uom_code || '',
          status: profile.requires_expiry_tracking ? 'Blocked' : 'Available',
          warehouse: globalConfig.warehouse_code || 'Global',
          stock_on_hand: Number(globalConfig.min_stock_level || 0),
          reorder_point: Number(globalConfig.reorder_point || 0),
          min_stock_level: Number(globalConfig.min_stock_level || 0),
          operationalFlags: {
            batch: profile.requires_batch_tracking,
            serial: profile.requires_serial_tracking,
            expiry: profile.requires_expiry_tracking,
            negative: profile.allow_negative_inventory,
          },
        };
      });
      setProducts(normalized);
      setCategoryDistribution(payload.category_distribution || FALLBACK_CATEGORY_DISTRIBUTION);
      setTurnoverTrend(payload.turnover_trend || FALLBACK_TURNOVER);
    } catch (error) {
      console.warn('Products fallback data used:', error?.message);
      setProducts(FALLBACK_PRODUCTS.map(normalizeFallbackProduct));
      setCategoryDistribution(FALLBACK_CATEGORY_DISTRIBUTION);
      setTurnoverTrend(FALLBACK_TURNOVER);
    } finally {
      setLoading(false);
    }
  };

  const buildItemQueryParams = (record) => {
    const params = {};
    if (record?.id) params.budget_item = record.id;
    if (record?.budgetItemId) params.budget_item = record.budgetItemId;
    return params;
  };

  const ensureUomOptions = async () => {
    if (uomOptions.length) return uomOptions;
    try {
      const response = await api.get('/api/v1/inventory/units-of-measure/', {
        params: { page_size: 500 },
      });
      const payload = response.data || {};
      const results = Array.isArray(payload.results)
        ? payload.results
        : Array.isArray(payload)
        ? payload
        : [];
      setUomOptions(results || []);
      return results || [];
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to load UoM list');
      return [];
    }
  };

  const refreshUomConversions = async (itemRecord) => {
    if (!itemRecord?.budgetItemId) return;
    try {
      setUomLoading(true);
      const params = { ...buildItemQueryParams(itemRecord), page_size: 200 };
      const response = await api.get('/api/v1/inventory/item-uom-conversions/', {
        params,
      });
      const payload = response.data || {};
      const rows = Array.isArray(payload.results)
        ? payload.results
        : Array.isArray(payload)
        ? payload
        : [];
      setUomConversions(rows || []);
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to load UoM conversions');
      setUomConversions([]);
    } finally {
      setUomLoading(false);
    }
  };

  const openUomDrawer = async (itemRecord) => {
    if (!itemRecord?.budgetItemId) {
      message.error('Budget master link is required to manage UoM conversions');
      return;
    }
    setUomDrawer({ visible: true, item: itemRecord });
    uomForm.resetFields();
    await ensureUomOptions();
    await refreshUomConversions(itemRecord);
  };

  const closeUomDrawer = () => {
    setUomDrawer({ visible: false, item: null });
    setUomConversions([]);
  };

  const handleUomCreate = async () => {
    if (!uomDrawer.budget_item) return;
    try {
      const values = await uomForm.validateFields();
      setUomLoading(true);
      const payload = {
        item: uomDrawer.budget_item.id,
        from_uom: values.from_uom,
        to_uom: values.to_uom,
        conversion_factor: values.conversion_factor,
        rounding_rule: values.rounding_rule || 'NO_ROUNDING',
        is_purchase_conversion: !!values.is_purchase_conversion,
        is_sales_conversion: !!values.is_sales_conversion,
        is_stock_conversion: !!values.is_stock_conversion,
        effective_date: values.effective_date ? values.effective_date.format('YYYY-MM-DD') : undefined,
        precedence: typeof values.precedence === 'number' ? values.precedence : 100,
      };
      if (uomDrawer.budget_item.budgetItemId) {
        payload.budget_item = uomDrawer.budget_item.budgetItemId;
      }
      await api.post('/api/v1/inventory/item-uom-conversions/', payload);
      message.success('Conversion saved');
      uomForm.resetFields();
      await refreshUomConversions(uomDrawer.budget_item);
    } catch (error) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Unable to save conversion');
    } finally {
      setUomLoading(false);
    }
  };

  const handleUomDelete = async (record) => {
    if (!record?.id) return;
    try {
      setUomLoading(true);
      await api.delete(`/api/v1/inventory/item-uom-conversions/${record.id}/`);
      message.success('Conversion removed');
      setUomLoading(false);
      if (uomDrawer.budget_item) {
        await refreshUomConversions(uomDrawer.budget_item);
      }
    } catch (error) {
      setUomLoading(false);
      message.error(error?.response?.data?.detail || 'Unable to remove conversion');
    }
  };

  const filteredProducts = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return (products || []).filter((product) => {
      const matchesTerm =
        !term ||
        product.name?.toLowerCase().includes(term) ||
        product.sku?.toLowerCase().includes(term) ||
        product.budgetName?.toLowerCase().includes(term) ||
        product.budgetCode?.toLowerCase().includes(term) ||
        product.category?.toLowerCase().includes(term);
      const matchesStatus =
        statusFilter === 'ALL' ||
        product.status === statusFilter ||
        (statusFilter === 'LOW' && product.status === 'Low Stock') ||
        (statusFilter === 'CRITICAL' && product.status === 'Critical');
      return matchesTerm && matchesStatus;
    });
  }, [products, searchTerm, statusFilter]);

  const masterSummary = useMemo(() => {
    const total = products.length;
    if (!total) return { total: 0, linked: 0, orphaned: 0 };
    const linked = products.filter((product) => product.budgetLinked).length;
    return { total, linked, orphaned: total - linked };
  }, [products]);

  const openSupplierDrawer = async (itemRecord) => {
    if (!itemRecord) return;
    setSupplierDrawer({ visible: true, item: itemRecord });
    supplierForm.resetFields();
    try {
      setSupplierLoading(true);
      if (!supplierOptions.length) {
        const supplierResponse = await api.get('/api/v1/procurement/suppliers/', {
          params: { page_size: 500 },
        });
        const supplierPayload = supplierResponse.data || {};
        const supplierList = Array.isArray(supplierPayload.results)
          ? supplierPayload.results
          : supplierPayload;
        setSupplierOptions(supplierList || []);
      }
      const linksResponse = await api.get('/api/v1/inventory/item-suppliers/', {
        params: buildItemQueryParams(itemRecord),
      });
      const linkPayload = linksResponse.data || {};
      const rows = Array.isArray(linkPayload.results) ? linkPayload.results : linkPayload;
      setItemSuppliers(rows || []);
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to load suppliers');
      setItemSuppliers([]);
    } finally {
      setSupplierLoading(false);
    }
  };

  const closeSupplierDrawer = () => {
    setSupplierDrawer({ visible: false, item: null });
    setItemSuppliers([]);
  };

  const handleSupplierCreate = async () => {
    if (!supplierDrawer.budget_item) return;
    try {
      const values = await supplierForm.validateFields();
      setSupplierLoading(true);
      const payload = {
        item: supplierDrawer.budget_item.id,
        supplier: values.supplier,
        supplier_item_code: values.supplier_item_code || '',
        supplier_pack_size: values.supplier_pack_size || 0,
        moq_qty: values.moq_qty || 0,
        multiple_qty: values.multiple_qty || 0,
        lead_time_days: values.lead_time_days || 0,
        lead_time_variability: values.lead_time_variability || 0,
        preferred_rank: values.preferred_rank || 1,
      };
      if (supplierDrawer.budget_item.budgetItemId) {
        payload.budget_item = supplierDrawer.budget_item.budgetItemId;
      }
      await api.post('/api/v1/inventory/item-suppliers/', payload);
      message.success('Supplier linked');
      supplierForm.resetFields();
      await openSupplierDrawer(supplierDrawer.budget_item);
    } catch (error) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Unable to save supplier link');
    } finally {
      setSupplierLoading(false);
    }
  };

  const handleSupplierStatusToggle = async (record) => {
    try {
      await api.patch(`/api/v1/inventory/item-suppliers/${record.id}/`, {
        is_active: !record.is_active,
      });
      message.success(`Supplier ${record.is_active ? 'disabled' : 'enabled'}`);
      if (supplierDrawer.budget_item) {
        await openSupplierDrawer(supplierDrawer.budget_item);
      }
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to update supplier');
    }
  };

  const openFefoDrawer = async (itemRecord) => {
    if (!itemRecord) return;
    setFefoDrawer({ visible: true, item: itemRecord });
    fefoForm.resetFields();
    try {
      setFefoLoading(true);
      if (!warehouseOptions.length) {
        const warehouseResponse = await api.get('/api/v1/inventory/warehouses/', {
          params: { page_size: 200 },
        });
        const warehousePayload = warehouseResponse.data || {};
        const warehouseList = Array.isArray(warehousePayload.results)
          ? warehousePayload.results
          : warehousePayload;
        setWarehouseOptions(warehouseList || []);
      }
      const configResponse = await api.get('/api/v1/inventory/item-fefo-configs/', {
        params: buildItemQueryParams(itemRecord),
      });
      const configPayload = configResponse.data || {};
      const rows = Array.isArray(configPayload.results) ? configPayload.results : configPayload;
      setFefoConfigs(rows || []);
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to load FEFO configs');
      setFefoConfigs([]);
    } finally {
      setFefoLoading(false);
    }
  };

  const closeFefoDrawer = () => {
    setFefoDrawer({ visible: false, item: null });
    setFefoConfigs([]);
  };

  const handleFefoCreate = async () => {
    if (!fefoDrawer.budget_item) return;
    try {
      const values = await fefoForm.validateFields();
      setFefoLoading(true);
      const payload = {
        item: fefoDrawer.budget_item.id,
        warehouse: values.warehouse || null,
        enforce_fefo: values.enforce_fefo || false,
        warn_days_before_expiry: values.warn_days_before_expiry || 0,
        block_issue_if_expired: values.block_issue_if_expired !== false,
        disposal_method: values.disposal_method || 'SCRAP',
        expiry_calculation_rule: values.expiry_calculation_rule || 'FIXED_DATE',
        shelf_life_days: values.shelf_life_days || 0,
      };
      if (fefoDrawer.budget_item.budgetItemId) {
        payload.budget_item = fefoDrawer.budget_item.budgetItemId;
      }
      await api.post('/api/v1/inventory/item-fefo-configs/', payload);
      message.success('FEFO configuration saved');
      fefoForm.resetFields();
      await openFefoDrawer(fefoDrawer.budget_item);
    } catch (error) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || 'Unable to save FEFO config');
    } finally {
      setFefoLoading(false);
    }
  };

  const handleFefoDelete = async (record) => {
    try {
      await api.delete(`/api/v1/inventory/item-fefo-configs/${record.id}/`);
      message.success('FEFO configuration removed');
      if (fefoDrawer.budget_item) {
        await openFefoDrawer(fefoDrawer.budget_item);
      }
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to delete config');
    }
  };

  const metrics = useMemo(() => {
    const totalSkus = filteredProducts.length;
    const lowStock = filteredProducts.filter((product) => product.status === 'Low Stock').length;
    const critical = filteredProducts.filter((product) => product.status === 'Critical').length;
    const blocked = filteredProducts.filter((product) => product.status === 'Blocked').length;
    return {
      totalSkus,
      lowStock,
      critical,
      blocked,
    };
  }, [filteredProducts]);

  const turnoverConfig = useMemo(() => {
    const safeData = (Array.isArray(turnoverTrend) ? turnoverTrend : []).map((product) => ({
      ...product,
      turnover: Number(product?.turnover) || 0,
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

  const supplierColumns = [
    {
      title: 'Supplier',
      dataIndex: 'supplier_name',
      key: 'supplier_name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.supplier_item_code || record.supplier_code}</Text>
        </Space>
      ),
    },
    {
      title: 'MOQ',
      dataIndex: 'moq_qty',
      key: 'moq_qty',
      render: (value) => (Number(value) || 0).toLocaleString(),
    },
    {
      title: 'Multiple',
      dataIndex: 'multiple_qty',
      key: 'multiple_qty',
      render: (value) => (Number(value) || 0).toLocaleString(),
    },
    {
      title: 'Lead Time (days)',
      dataIndex: 'lead_time_days',
      key: 'lead_time_days',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text>{value || 0}</Text>
          <Text type="secondary">± {record.lead_time_variability || 0}</Text>
        </Space>
      ),
    },
    {
      title: 'Preferred Rank',
      dataIndex: 'preferred_rank',
      key: 'preferred_rank',
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (value) => <Tag color={value ? 'green' : 'red'}>{value ? 'Active' : 'Inactive'}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button size="small" onClick={() => handleSupplierStatusToggle(record)}>
          {record.is_active ? 'Deactivate' : 'Activate'}
        </Button>
      ),
    },
  ];

  const fefoColumns = [
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_code',
      key: 'warehouse_code',
      render: (value) => value || 'Global',
    },
    {
      title: 'Enforce',
      dataIndex: 'enforce_fefo',
      key: 'enforce_fefo',
      render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? 'Yes' : 'No'}</Tag>,
    },
    {
      title: 'Warn (days)',
      dataIndex: 'warn_days_before_expiry',
      key: 'warn_days_before_expiry',
    },
    {
      title: 'Block Expired',
      dataIndex: 'block_issue_if_expired',
      key: 'block_issue_if_expired',
      render: (value) => <Tag color={value ? 'red' : 'blue'}>{value ? 'Block' : 'Allow'}</Tag>,
    },
    {
      title: 'Disposal',
      dataIndex: 'disposal_method',
      key: 'disposal_method',
    },
    {
      title: 'Expiry Rule',
      dataIndex: 'expiry_calculation_rule',
      key: 'expiry_calculation_rule',
    },
    {
      title: 'Shelf Life (days)',
      dataIndex: 'shelf_life_days',
      key: 'shelf_life_days',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button danger size="small" onClick={() => handleFefoDelete(record)}>
          Remove
        </Button>
      ),
    },
  ];

  const uomColumns = [
    {
      title: 'From → To',
      key: 'pair',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{`${record.from_uom_code || ''} → ${record.to_uom_code || ''}`}</Text>
          <Text type="secondary">
            {record.from_uom_name || ''} → {record.to_uom_name || ''}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Factor',
      dataIndex: 'conversion_factor',
      key: 'conversion_factor',
      render: (value) => Number(value || 0).toLocaleString(),
    },
    {
      title: 'Contexts',
      key: 'contexts',
      render: (_, record) => (
        <Space size={4}>
          {record.is_purchase_conversion ? <Tag color="geekblue">Purchase</Tag> : null}
          {record.is_sales_conversion ? <Tag color="purple">Sales</Tag> : null}
          {record.is_stock_conversion ? <Tag color="gold">Stock</Tag> : null}
          {!record.is_purchase_conversion &&
          !record.is_sales_conversion &&
          !record.is_stock_conversion ? (
            <Tag>Generic</Tag>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'Rounding',
      dataIndex: 'rounding_rule',
      key: 'rounding_rule',
      render: (value) => value?.replace(/_/g, ' ') || 'NO_ROUNDING',
    },
    {
      title: 'Effective',
      dataIndex: 'effective_date',
      key: 'effective_date',
    },
    {
      title: 'Precedence',
      dataIndex: 'precedence',
      key: 'precedence',
      align: 'right',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Popconfirm
          title="Remove conversion?"
          okText="Delete"
          okButtonProps={{ danger: true }}
          onConfirm={() => handleUomDelete(record)}
        >
          <Button danger size="small">
            Delete
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const categoryConfig = useMemo(() => {
    const safeData = (Array.isArray(categoryDistribution) ? categoryDistribution : []).map(
      (product) => ({
        ...product,
        value: Number(product?.value) || 0,
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
      title: 'Budget Code',
      dataIndex: 'budgetCode',
      key: 'budgetCode',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <BarcodeOutlined />
            <Link to={`/inventory/items/${record.id}`}>
              <Text strong>{record.budgetCode}</Text>
            </Link>
            <Tag color={record.budgetLinked ? 'blue' : 'red'}>
              {record.budgetLinked ? 'Budget Master' : 'Not Linked'}
            </Tag>
          </Space>
          {record.code && record.code !== record.budgetCode ? (
            <Text type="secondary">Operational code: {record.code}</Text>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'Product',
      dataIndex: 'budgetName',
      key: 'budgetName',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Link to={`/inventory/items/${record.id}`}>
            <Text strong>{record.budgetName}</Text>
          </Link>
          <Text type="secondary">{record.category}</Text>
          {record.name && record.name !== record.budgetName ? (
            <Text type="secondary">Inventory label: {record.name}</Text>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'UoM Alignment',
      dataIndex: 'uom',
      key: 'uom',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <Text strong>Base</Text>
            <Text>{record.baseUom || record.uom || '—'}</Text>
            {Number(record.baseStandardCost) > 0 && (
              <Tag color="geekblue">
                {Number(record.baseStandardCost).toLocaleString()} {currentCompany?.currency || ''}
              </Tag>
            )}
          </Space>
          <Text>Stock: {record.uom || '—'}</Text>
          <Text type="secondary">Purchase: {record.purchaseUom || '—'}</Text>
          <Text type="secondary">Sales: {record.salesUom || '—'}</Text>
        </Space>
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
      title: 'Warehouse Scope',
      dataIndex: 'warehouse',
      key: 'warehouse',
    },
    {
      title: 'Operational Controls',
      dataIndex: 'operationalFlags',
      key: 'operationalFlags',
      render: (flags = {}) => (
        <Space wrap>
          {flags.batch && <Tag color="blue">Batch</Tag>}
          {flags.serial && <Tag color="purple">Serial</Tag>}
          {flags.expiry && <Tag color="red">Expiry</Tag>}
          {flags.negative && <Tag color="orange">Neg Inv</Tag>}
          {!flags.batch && !flags.serial && !flags.expiry && !flags.negative && (
            <Tag color="default">Standard</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'UoM',
      key: 'uom',
      render: (_, record) => (
        <Button size="small" onClick={() => openUomDrawer(record)}>
          UoM
        </Button>
      ),
    },
    {
      title: 'Suppliers',
      key: 'suppliers',
      render: (_, record) => (
        <Button size="small" onClick={() => openSupplierDrawer(record)}>
          Manage
        </Button>
      ),
    },
    {
      title: 'FEFO',
      key: 'fefo',
      render: (_, record) => (
        <Button size="small" onClick={() => openFefoDrawer(record)}>
          Configure
        </Button>
      ),
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
            style={{ marginBottom: 16 }}
            title="Budget Item Master"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/budgets/item-codes')}>
                Open Item Codes
              </Button>
            }
          >
            <Space direction="vertical" size={4}>
              <Text strong>
                {masterSummary.linked} / {masterSummary.total || 0} items linked to Budget master
              </Text>
              {masterSummary.orphaned > 0 ? (
                <Tag color="red">{masterSummary.orphaned} items need linking</Tag>
              ) : (
                <Tag color="green">All operational items aligned</Tag>
              )}
              <Text type="secondary">
                Code, name, base UoM and standard cost stay in Budgeting. Configure warehouse settings, suppliers and FEFO rules here.
              </Text>
            </Space>
          </Card>
          <Card
            title="Product Catalogue"
            extra={
              <Space>
                <Input.Search
                  allowClear
                  placeholder="Search budget code, SKU, product, category"
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
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 12 }}
              message="Budget controls item master"
              description="Update code, name, base UoM and standard price from Budget » Item Codes. Inventory can only extend operational attributes."
            />
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
              renderItem={(product) => (
                <List.Item key={product.id}>
                  <Space>
                    <Badge color={segmentColorMap[product.segment]} />
                    <Space direction="vertical" size={0}>
                      <Text strong>{product.budgetName || product.name}</Text>
                      <Text type="secondary">
                        {product.budgetCode || product.sku} ·{' '}
                        {product.segment ? `Class ${product.segment}` : 'Unclassified'}
                      </Text>
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
      <Drawer
        width={540}
        title={
          uomDrawer.budget_item
            ? `UoM Conversions · ${uomDrawer.budget_item.budgetName || uomDrawer.budget_item.name} (${
                uomDrawer.budget_item.budgetCode || uomDrawer.budget_item.sku
              })`
            : 'UoM Conversions'
        }
        open={uomDrawer.visible}
        onClose={closeUomDrawer}
        destroyOnClose
      >
        {uomDrawer.budget_item && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message={`Master Item · ${uomDrawer.budget_item.budgetCode || uomDrawer.budget_item.sku}`}
            description="Define conversions between purchase, stock, and sales UoMs. Core UoM data stays in Budget Item Codes."
          />
        )}
        <Card
          title="Active Conversions"
          loading={uomLoading}
          bodyStyle={{ padding: 0 }}
          style={{ marginBottom: 16 }}
        >
          <Table
            dataSource={uomConversions}
            columns={uomColumns}
            rowKey="id"
            size="small"
            loading={uomLoading}
            pagination={false}
          />
        </Card>
        <Card title="Add Conversion" size="small">
          <Form layout="vertical" form={uomForm} onFinish={handleUomCreate}>
            <Form.Item
              name="from_uom"
              label="From UoM"
              rules={[{ required: true, message: 'Select the source UoM' }]}
            >
              <Select
                showSearch
                placeholder="Select source UoM"
                optionFilterProp="label"
                options={(uomOptions || []).map((option) => ({
                  label: `${option.code} · ${option.name}`,
                  value: option.id,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="to_uom"
              label="To UoM"
              rules={[{ required: true, message: 'Select the target UoM' }]}
            >
              <Select
                showSearch
                placeholder="Select target UoM"
                optionFilterProp="label"
                options={(uomOptions || []).map((option) => ({
                  label: `${option.code} · ${option.name}`,
                  value: option.id,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="conversion_factor"
              label="Conversion Factor"
              rules={[{ required: true, message: 'Enter conversion factor' }]}
            >
              <InputNumber min={0} step={0.000001} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="rounding_rule" label="Rounding Rule" initialValue="NO_ROUNDING">
              <Select options={ROUNDING_OPTIONS} />
            </Form.Item>
            <Form.Item name="effective_date" label="Effective Date">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="precedence" label="Precedence" initialValue={100}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Divider />
            <Form.Item name="is_purchase_conversion" valuePropName="checked">
              <Checkbox>Purchase Context</Checkbox>
            </Form.Item>
            <Form.Item name="is_sales_conversion" valuePropName="checked">
              <Checkbox>Sales Context</Checkbox>
            </Form.Item>
            <Form.Item name="is_stock_conversion" valuePropName="checked">
              <Checkbox>Stock Context</Checkbox>
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={uomLoading}>
              Save Conversion
            </Button>
          </Form>
        </Card>
      </Drawer>
      <Drawer
        width={520}
        title={
          supplierDrawer.budget_item
            ? `Suppliers · ${supplierDrawer.budget_item.budgetName || supplierDrawer.budget_item.name} (${supplierDrawer.budget_item.budgetCode || supplierDrawer.budget_item.sku})`
            : 'Suppliers'
        }
        open={supplierDrawer.visible}
        onClose={closeSupplierDrawer}
        destroyOnClose
      >
        {supplierDrawer.budget_item && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message={`Master Item · ${supplierDrawer.budget_item.budgetCode || supplierDrawer.budget_item.sku}`}
            description="Item code, name and base UoM are synchronized from Budget Item Codes. Link suppliers here without editing the core master."
          />
        )}
        <Card
          title="Linked Suppliers"
          loading={supplierLoading}
          bodyStyle={{ padding: 0 }}
          style={{ marginBottom: 16 }}
        >
          <Table
            dataSource={itemSuppliers}
            columns={supplierColumns}
            pagination={false}
            size="small"
            rowKey="id"
          />
        </Card>
        <Card title="Add Supplier" size="small">
          <Form layout="vertical" form={supplierForm} onFinish={handleSupplierCreate}>
            <Form.Item
              name="supplier"
              label="Supplier"
              rules={[{ required: true, message: 'Select a supplier' }]}
            >
              <Select
                placeholder="Choose supplier"
                showSearch
                optionFilterProp="label"
                options={(supplierOptions || []).map((option) => ({
                  label: `${option.name} (${option.code})`,
                  value: option.id,
                }))}
              />
            </Form.Item>
            <Form.Item name="supplier_item_code" label="Supplier Item Code">
              <Input placeholder="Supplier reference" />
            </Form.Item>
            <Form.Item name="supplier_pack_size" label="Pack Size">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="moq_qty" label="Minimum Order Quantity">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="multiple_qty" label="Order Multiple">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="lead_time_days" label="Lead Time (days)">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="lead_time_variability" label="Lead Time Variability (days)">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="preferred_rank" label="Preferred Rank" initialValue={1}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={supplierLoading}>
              Save Supplier
            </Button>
          </Form>
        </Card>
      </Drawer>
      <Drawer
        width={520}
        title={
          fefoDrawer.budget_item
            ? `FEFO · ${fefoDrawer.budget_item.budgetName || fefoDrawer.budget_item.name} (${fefoDrawer.budget_item.budgetCode || fefoDrawer.budget_item.sku})`
            : 'FEFO'
        }
        open={fefoDrawer.visible}
        onClose={closeFefoDrawer}
        destroyOnClose
      >
        {fefoDrawer.budget_item && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message={`Master Item · ${fefoDrawer.budget_item.budgetCode || fefoDrawer.budget_item.sku}`}
            description="FEFO routing is an operational control. Update base attributes from Budget » Item Codes if needed."
          />
        )}
        <Card
          title="Configurations"
          loading={fefoLoading}
          bodyStyle={{ padding: 0 }}
          style={{ marginBottom: 16 }}
        >
          <Table
            dataSource={fefoConfigs}
            columns={fefoColumns}
            pagination={false}
            rowKey="id"
            size="small"
          />
        </Card>
        <Card title="Add / Update FEFO" size="small">
          <Form layout="vertical" form={fefoForm} onFinish={handleFefoCreate}>
            <Form.Item name="warehouse" label="Warehouse">
              <Select
                allowClear
                placeholder="Global (optional)"
                options={(warehouseOptions || []).map((option) => ({
                  label: `${option.code} - ${option.name}`,
                  value: option.id,
                }))}
              />
            </Form.Item>
            <Form.Item name="enforce_fefo" label="Enforce FEFO" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="warn_days_before_expiry" label="Warn Days">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="block_issue_if_expired"
              label="Block Issue if Expired"
              initialValue
            >
              <Select
                options={[
                  { label: 'Block', value: true },
                  { label: 'Allow', value: false },
                ]}
              />
            </Form.Item>
            <Form.Item name="disposal_method" label="Disposal Method" initialValue="SCRAP">
              <Select
                options={[
                  { label: 'Scrap', value: 'SCRAP' },
                  { label: 'Donate', value: 'DONATE' },
                  { label: 'Return to Supplier', value: 'RETURN_TO_SUPPLIER' },
                  { label: 'Rework', value: 'REWORK' },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="expiry_calculation_rule"
              label="Expiry Calculation"
              initialValue="FIXED_DATE"
            >
              <Select
                options={[
                  { label: 'Fixed Date', value: 'FIXED_DATE' },
                  { label: 'Days from Manufacture', value: 'DAYS_FROM_MFG' },
                  { label: 'Days from Receipt', value: 'DAYS_FROM_RECEIPT' },
                  { label: 'Custom Formula', value: 'CUSTOM' },
                ]}
              />
            </Form.Item>
            <Form.Item name="shelf_life_days" label="Shelf Life (days)">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={fefoLoading}>
              Save FEFO Config
            </Button>
          </Form>
        </Card>
      </Drawer>
    </div>
  );
};

export default ProductsList;
