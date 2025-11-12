import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Drawer,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  message,
  Typography,
  Popconfirm,
  Tooltip,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckOutlined,
  InboxOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
  ExportOutlined,
  ImportOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import * as procurementService from '../../../services/procurement';
import api from '../../../services/api';
import {
  InventoryLayout,
  SmartFilters,
  InventoryStats,
  WorkflowBoard,
  ViewToggle,
} from '../../../components/Inventory';
import WarehouseWarningDialog from '../../../components/Inventory/WarehouseWarningDialog';
import { useWarehouseValidation } from '../../../services/warehouseValidation';

const { Text } = Typography;

const GoodsReceiptManagementNew = () => {
  const { currentCompany } = useCompany();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [grns, setGrns] = useState([]);
  const [filteredGRNs, setFilteredGRNs] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingGRN, setEditingGRN] = useState(null);
  const [viewMode, setViewMode] = useState('table');
  const [filters, setFilters] = useState({});
  const [savedFilters, setSavedFilters] = useState([]);

  // Warehouse validation state
  const [selectedPO, setSelectedPO] = useState(null);
  const [poLineItems, setPOLineItems] = useState([]);
  const [warningDialogVisible, setWarningDialogVisible] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [pendingWarehouse, setPendingWarehouse] = useState(null);
  const [supervisors, setSupervisors] = useState([]);
  const warehouseValidation = useWarehouseValidation();

  // Fetch GRNs
  const fetchGRNs = useCallback(async () => {
    if (!currentCompany?.id) return;
    try {
      setLoading(true);
      const response = await procurementService.getGoodsReceipts({
        company: currentCompany.id,
      });
      const data = response.data?.results || response.data || [];
      setGrns(data);
      setFilteredGRNs(data);
    } catch (error) {
      message.error('Failed to load goods receipts');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [currentCompany]);

  // Fetch Purchase Orders
  const fetchPurchaseOrders = useCallback(async () => {
    if (!currentCompany?.id) return;
    try {
      const response = await procurementService.getPurchaseOrders({
        company: currentCompany.id,
        status: 'ISSUED',
      });
      const data = response.data?.results || response.data || [];
      setPurchaseOrders(data);
    } catch (error) {
      message.error('Failed to load purchase orders');
    }
  }, [currentCompany]);

  // Fetch Warehouses
  const fetchWarehouses = useCallback(async () => {
    if (!currentCompany?.id) return;
    try {
      const response = await api.get('/api/v1/inventory/warehouses/', {
        params: { company: currentCompany.id },
      });
      const data = response.data?.results || response.data || [];
      console.log('Fetched warehouses:', data);
      setWarehouses(data);
    } catch (error) {
      console.error('Failed to load warehouses:', error);
      message.error('Failed to load warehouses');
    }
  }, [currentCompany]);

  // Fetch Supervisors for approval
  const fetchSupervisors = useCallback(async () => {
    try {
      // Fetch users with supervisor/manager role
      const response = await api.get('/api/v1/users/', {
        params: { role: 'supervisor' } // Adjust based on your user API
      });
      const data = response.data?.results || response.data || [];
      setSupervisors(data);
    } catch (error) {
      console.error('Failed to load supervisors:', error);
      // Non-critical, don't show error to user
    }
  }, []);

  // Fetch PO details including line items
  const fetchPODetails = useCallback(async (poId) => {
    try {
      const response = await procurementService.getPurchaseOrderDetail(poId);
      const po = response.data;
      setSelectedPO(po);
      // Extract line items with budget_item information
      const lineItems = po.lines || [];
      setPOLineItems(lineItems);
      return lineItems;
    } catch (error) {
      console.error('Failed to load PO details:', error);
      message.error('Failed to load purchase order details');
      return [];
    }
  }, []);

  // Handle PO selection
  const handlePOChange = async (poId) => {
    if (poId) {
      await fetchPODetails(poId);
    } else {
      setSelectedPO(null);
      setPOLineItems([]);
    }
  };

  // Validate warehouse selection
  const validateWarehouseForPO = async (warehouseId) => {
    if (!poLineItems || poLineItems.length === 0) {
      return null;
    }

    // Validate against the first item in PO (or aggregate validations)
    // For simplicity, we check the first line item
    // In production, you might want to check all items and show the highest warning level
    const firstItem = poLineItems[0];
    if (!firstItem?.budget_item_id) {
      return null;
    }

    try {
      const validation = await warehouseValidation.validate(
        firstItem.budget_item_id,
        warehouseId
      );
      return validation;
    } catch (error) {
      console.error('Warehouse validation error:', error);
      return null;
    }
  };

  // Handle warehouse change with validation
  const handleWarehouseChange = async (warehouseId) => {
    if (!warehouseId) {
      form.setFieldValue('warehouse', null);
      return;
    }

    const validation = await validateWarehouseForPO(warehouseId);

    if (validation && !validation.is_valid && (validation.requires_reason || validation.requires_approval)) {
      // Show warning dialog
      setPendingWarehouse(warehouseId);
      setValidationResult(validation);
      setWarningDialogVisible(true);
      // Don't set the warehouse yet - wait for user confirmation
      form.setFieldValue('warehouse', null);
    } else {
      // Valid or INFO level - proceed
      form.setFieldValue('warehouse', warehouseId);
    }
  };

  // Handle warehouse override confirmation
  const handleWarehouseOverrideConfirm = async (reason, approvedById) => {
    try {
      // Log the override (this will happen after GRN is created)
      // For now, just proceed with the warehouse selection
      form.setFieldValue('warehouse', pendingWarehouse);

      // Store override info in form for later logging
      form.setFieldValue('_warehouse_override', {
        reason,
        approvedById,
        validation: validationResult
      });

      setWarningDialogVisible(false);
      message.success('Warehouse selection confirmed. Override will be logged on save.');
    } catch (error) {
      message.error('Failed to confirm warehouse override');
      console.error(error);
    }
  };

  // Handle use suggested warehouse
  const handleUseSuggestedWarehouse = (suggestedWarehouse) => {
    if (suggestedWarehouse) {
      form.setFieldValue('warehouse', suggestedWarehouse.id);
      setWarningDialogVisible(false);
      message.success(`Warehouse changed to ${suggestedWarehouse.code}`);
    }
  };

  // Handle warning dialog cancel
  const handleWarningDialogCancel = () => {
    setWarningDialogVisible(false);
    setPendingWarehouse(null);
    setValidationResult(null);
  };

  useEffect(() => {
    fetchGRNs();
    fetchPurchaseOrders();
    fetchWarehouses();
    fetchSupervisors();
  }, [fetchGRNs, fetchPurchaseOrders, fetchWarehouses, fetchSupervisors]);

  // Calculate stats
  const stats = useMemo(() => {
    const totalGRNs = grns.length;
    const pendingQC = grns.filter((g) => g.status === 'PENDING_QC').length;
    const approved = grns.filter((g) => g.status === 'APPROVED').length;
    const onHold = grns.filter((g) => g.status === 'ON_HOLD').length;
    const todayGRNs = grns.filter((g) =>
      dayjs(g.receipt_date).isSame(dayjs(), 'day')
    ).length;

    return [
      {
        key: 'total',
        title: 'Total GRNs',
        value: totalGRNs,
        icon: <InboxOutlined />,
        iconColor: '#1890ff',
        trend: 5,
        trendLabel: 'vs last month',
        onClick: () => handleFilterChange({}),
      },
      {
        key: 'pending_qc',
        title: 'Pending QC',
        value: pendingQC,
        icon: <SafetyCertificateOutlined />,
        iconColor: '#faad14',
        status: pendingQC > 10 ? 'warning' : 'normal',
        onClick: () => handleFilterChange({ status: 'PENDING_QC' }),
        highlight: true,
        highlightColor: '#faad14',
      },
      {
        key: 'approved',
        title: 'Approved',
        value: approved,
        icon: <CheckOutlined />,
        iconColor: '#52c41a',
        status: 'success',
        trend: 8,
        onClick: () => handleFilterChange({ status: 'APPROVED' }),
      },
      {
        key: 'on_hold',
        title: 'On Hold',
        value: onHold,
        icon: <WarningOutlined />,
        iconColor: '#ff4d4f',
        status: onHold > 0 ? 'danger' : 'normal',
        onClick: () => handleFilterChange({ status: 'ON_HOLD' }),
        footer: `${todayGRNs} received today`,
      },
    ];
  }, [grns]);

  // Filter configuration
  const filterConfig = [
    {
      type: 'select',
      field: 'status',
      label: 'Status',
      options: [
        { label: 'Draft', value: 'DRAFT' },
        { label: 'Pending QC', value: 'PENDING_QC' },
        { label: 'Approved', value: 'APPROVED' },
        { label: 'On Hold', value: 'ON_HOLD' },
        { label: 'Posted', value: 'POSTED' },
      ],
    },
    {
      type: 'select',
      field: 'warehouse',
      label: 'Warehouse',
      options: warehouses.map((w) => ({ label: w.name, value: w.id })),
    },
    {
      type: 'daterange',
      field: 'date_range',
      label: 'Receipt Date',
    },
    {
      type: 'select',
      field: 'supplier',
      label: 'Supplier',
      options: [], // Would be populated from API
    },
  ];

  // Quick filters
  const quickFilters = [
    {
      label: 'Today',
      icon: <InboxOutlined />,
      color: 'blue',
      filter: { date: 'today' },
    },
    {
      label: 'Pending QC',
      icon: <SafetyCertificateOutlined />,
      color: 'orange',
      filter: { status: 'PENDING_QC' },
    },
    {
      label: 'On Hold',
      icon: <WarningOutlined />,
      color: 'red',
      filter: { status: 'ON_HOLD' },
    },
    {
      label: 'This Week',
      color: 'green',
      filter: { date: 'week' },
    },
  ];

  // Handle filter change
  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);

    // Apply filters
    let filtered = [...grns];

    if (newFilters.status) {
      filtered = filtered.filter((g) => g.status === newFilters.status);
    }

    if (newFilters.warehouse) {
      filtered = filtered.filter((g) => g.warehouse === newFilters.warehouse);
    }

    if (newFilters.search) {
      const searchLower = newFilters.search.toLowerCase();
      filtered = filtered.filter(
        (g) =>
          g.grn_number?.toLowerCase().includes(searchLower) ||
          g.po_number?.toLowerCase().includes(searchLower) ||
          g.supplier_name?.toLowerCase().includes(searchLower)
      );
    }

    if (newFilters.date === 'today') {
      filtered = filtered.filter((g) =>
        dayjs(g.receipt_date).isSame(dayjs(), 'day')
      );
    } else if (newFilters.date === 'week') {
      filtered = filtered.filter((g) =>
        dayjs(g.receipt_date).isSame(dayjs(), 'week')
      );
    }

    setFilteredGRNs(filtered);
  };

  // Handle save filter
  const handleSaveFilter = (filter) => {
    setSavedFilters([...savedFilters, { ...filter, id: Date.now() }]);
    // In real app, save to backend or localStorage
  };

  // Handle delete filter
  const handleDeleteFilter = (filterId) => {
    setSavedFilters(savedFilters.filter((f) => f.id !== filterId));
  };

  // Open drawer for create/edit
  const openDrawer = (grn = null) => {
    setEditingGRN(grn);
    if (grn) {
      form.setFieldsValue({
        ...grn,
        receipt_date: grn.receipt_date ? dayjs(grn.receipt_date) : dayjs(),
      });
    } else {
      form.resetFields();
      form.setFieldsValue({ receipt_date: dayjs() });
    }
    setDrawerVisible(true);
  };

  // Handle submit
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const payload = {
        ...values,
        receipt_date: values.receipt_date.format('YYYY-MM-DD'),
        company: currentCompany.id,
      };

      // Remove internal fields
      const warehouseOverride = values._warehouse_override;
      delete payload._warehouse_override;

      let grnResult;
      if (editingGRN) {
        grnResult = await procurementService.updateGoodsReceipt(editingGRN.id, payload);
        message.success('GRN updated successfully');
      } else {
        grnResult = await procurementService.createGoodsReceipt(payload);
        message.success('GRN created successfully');
      }

      // Log warehouse override if exists
      if (warehouseOverride && grnResult.data) {
        const grn = grnResult.data;
        try {
          await warehouseValidation.logOverride({
            transaction_type: 'GRN',
            transaction_id: grn.id,
            transaction_number: grn.grn_number || grn.receipt_number || '',
            budget_item_id: poLineItems[0]?.budget_item_id,
            suggested_warehouse_id: warehouseOverride.validation?.suggested_warehouse?.id,
            actual_warehouse_id: values.warehouse,
            warning_level: warehouseOverride.validation?.warning_level || 'WARNING',
            override_reason: warehouseOverride.reason,
            was_approved: !!warehouseOverride.approvedById,
            approved_by_id: warehouseOverride.approvedById
          });
          console.log('Warehouse override logged successfully');
        } catch (overrideError) {
          console.error('Failed to log warehouse override:', overrideError);
          // Don't fail the GRN creation if logging fails
        }
      }

      setDrawerVisible(false);
      fetchGRNs();
    } catch (error) {
      message.error('Failed to save GRN');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete
  const handleDelete = async (id) => {
    try {
      setLoading(true);
      await procurementService.deleteGoodsReceipt(id);
      message.success('GRN deleted successfully');
      fetchGRNs();
    } catch (error) {
      message.error('Failed to delete GRN');
    } finally {
      setLoading(false);
    }
  };

  // Get status tag
  const getStatusTag = (status) => {
    const statusConfig = {
      DRAFT: { color: 'default', text: 'Draft' },
      PENDING_QC: { color: 'orange', text: 'Pending QC' },
      APPROVED: { color: 'green', text: 'Approved' },
      ON_HOLD: { color: 'red', text: 'On Hold' },
      POSTED: { color: 'blue', text: 'Posted' },
    };
    const config = statusConfig[status] || statusConfig.DRAFT;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // Table columns
  const columns = [
    {
      title: 'GRN Number',
      dataIndex: 'grn_number',
      key: 'grn_number',
      fixed: 'left',
      width: 150,
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: 'PO Number',
      dataIndex: 'po_number',
      key: 'po_number',
      width: 130,
    },
    {
      title: 'Supplier',
      dataIndex: 'supplier_name',
      key: 'supplier_name',
      width: 200,
    },
    {
      title: 'Receipt Date',
      dataIndex: 'receipt_date',
      key: 'receipt_date',
      width: 120,
      render: (date) => dayjs(date).format('DD MMM YYYY'),
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_name',
      key: 'warehouse_name',
      width: 150,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => getStatusTag(status),
    },
    {
      title: 'Items',
      dataIndex: 'item_count',
      key: 'item_count',
      width: 80,
      align: 'center',
      render: (count) => <Badge count={count} showZero />,
    },
    {
      title: 'Total Value',
      dataIndex: 'total_value',
      key: 'total_value',
      width: 120,
      align: 'right',
      render: (value) => `৳${value?.toLocaleString() || '0'}`,
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="View">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => openDrawer(record)}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openDrawer(record)}
              disabled={record.status === 'POSTED'}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this GRN?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={record.status === 'POSTED'}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Workflow board configuration
  const workflowColumns = [
    {
      id: 'draft',
      title: 'Draft',
      description: 'Pending submission',
      itemIds: filteredGRNs.filter((g) => g.status === 'DRAFT').map((g) => g.id.toString()),
      headerColor: '#fafafa',
      badgeColor: '#d9d9d9',
      statusColor: '#8c8c8c',
    },
    {
      id: 'pending_qc',
      title: 'Pending QC',
      description: 'Awaiting quality inspection',
      itemIds: filteredGRNs.filter((g) => g.status === 'PENDING_QC').map((g) => g.id.toString()),
      headerColor: '#fff7e6',
      badgeColor: '#faad14',
      statusColor: '#faad14',
      info: 'QC must be completed within 24 hours',
    },
    {
      id: 'approved',
      title: 'Approved',
      description: 'QC passed, ready to post',
      itemIds: filteredGRNs.filter((g) => g.status === 'APPROVED').map((g) => g.id.toString()),
      headerColor: '#f6ffed',
      badgeColor: '#52c41a',
      statusColor: '#52c41a',
    },
    {
      id: 'posted',
      title: 'Posted',
      description: 'Stock updated',
      itemIds: filteredGRNs.filter((g) => g.status === 'POSTED').map((g) => g.id.toString()),
      headerColor: '#e6f7ff',
      badgeColor: '#1890ff',
      statusColor: '#1890ff',
    },
  ];

  const workflowItems = useMemo(() => {
    const items = {};
    filteredGRNs.forEach((grn) => {
      items[grn.id.toString()] = {
        id: grn.id.toString(),
        code: grn.grn_number,
        name: grn.supplier_name,
        description: `PO: ${grn.po_number}`,
        assignee: grn.created_by_name || 'Unassigned',
        dueDate: dayjs(grn.receipt_date).format('DD MMM'),
        count: grn.item_count,
        tags: [grn.warehouse_name],
      };
    });
    return items;
  }, [filteredGRNs]);

  const handleWorkflowDragEnd = (result) => {
    // Handle status change via drag and drop
    console.log('Drag result:', result);
    // In real app, update status via API
  };

  return (
    <InventoryLayout
      title="Goods Receipts (GRN)"
      icon={<InboxOutlined />}
      subtitle="Receive and manage incoming inventory from suppliers"
      breadcrumb={[
        { label: 'Inventory', path: '/inventory' },
        { label: 'Inbound Operations' },
        { label: 'Goods Receipts' },
      ]}
      actions={[
        <Button key="refresh" icon={<ReloadOutlined />} onClick={fetchGRNs}>
          Refresh
        </Button>,
        <Button key="export" icon={<ExportOutlined />}>
          Export
        </Button>,
        <Button key="import" icon={<ImportOutlined />}>
          Import
        </Button>,
        <Button
          key="create"
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => openDrawer()}
        >
          New GRN
        </Button>,
      ]}
    >
      {/* Stats */}
      <InventoryStats stats={stats} loading={loading} />

      {/* Filters */}
      <SmartFilters
        filters={filterConfig}
        quickFilters={quickFilters}
        savedFilters={savedFilters}
        onFilterChange={handleFilterChange}
        onSaveFilter={handleSaveFilter}
        onDeleteFilter={handleDeleteFilter}
        searchPlaceholder="Search by GRN, PO, or supplier..."
      />

      {/* View Toggle */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <ViewToggle
          value={viewMode}
          onChange={setViewMode}
          views={['table', 'kanban']}
        />
      </div>

      {/* Content based on view mode */}
      {viewMode === 'table' ? (
        <Table
          columns={columns}
          dataSource={filteredGRNs}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1300 }}
          pagination={{
            total: filteredGRNs.length,
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} GRNs`,
          }}
        />
      ) : (
        <WorkflowBoard
          columns={workflowColumns}
          items={workflowItems}
          onDragEnd={handleWorkflowDragEnd}
          loading={loading}
        />
      )}

      {/* Create/Edit Drawer */}
      <Drawer
        title={editingGRN ? 'Edit GRN' : 'New GRN'}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={600}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerVisible(false)}>Cancel</Button>
            <Button type="primary" onClick={handleSubmit} loading={loading}>
              {editingGRN ? 'Update' : 'Create'}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="purchase_order"
            label="Purchase Order"
            rules={[{ required: true, message: 'Please select a PO' }]}
          >
            <Select
              placeholder="Select Purchase Order"
              showSearch
              optionFilterProp="children"
              onChange={handlePOChange}
              options={purchaseOrders.map((po) => ({
                label: `${po.po_number} - ${po.supplier_name}`,
                value: po.id,
              }))}
            />
          </Form.Item>

          <Form.Item
            name="receipt_date"
            label="Receipt Date"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="warehouse"
            label="Warehouse"
            rules={[{ required: true, message: 'Please select a warehouse' }]}
            extra={poLineItems.length > 0 && "Warehouse will be validated against purchase order items"}
          >
            <Select
              placeholder="Select Warehouse"
              showSearch
              optionFilterProp="label"
              notFoundContent={warehouses.length === 0 ? 'No warehouses available' : 'No match found'}
              onChange={handleWarehouseChange}
              options={warehouses.map((w) => ({
                label: `${w.code} - ${w.name}`,
                value: w.id,
              }))}
            />
          </Form.Item>

          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={4} placeholder="Additional notes..." />
          </Form.Item>
        </Form>
      </Drawer>

      {/* Warehouse Warning Dialog */}
      <WarehouseWarningDialog
        visible={warningDialogVisible}
        validation={validationResult}
        onConfirm={handleWarehouseOverrideConfirm}
        onCancel={handleWarningDialogCancel}
        onUseSuggested={handleUseSuggestedWarehouse}
        supervisors={supervisors}
      />
    </InventoryLayout>
  );
};

export default GoodsReceiptManagementNew;
