import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Segmented,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  StopOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import qcService, {
  HOLD_TYPE_LABELS,
  HOLD_STATUS_LABELS,
  HOLD_STATUS_COLORS,
  HOLD_TYPES,
  DISPOSITION_LABELS,
  DISPOSITIONS,
} from '../../../services/qc';
import api from '../../../services/api';

const { Title, Text } = Typography;

const statusFilters = [
  { label: 'Active', value: 'ACTIVE' },
  { label: 'Released', value: 'RELEASED' },
  { label: 'Scrapped', value: 'SCRAPPED' },
  { label: 'All', value: 'ALL' },
];

const asArray = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.results)) return payload.results;
  if (payload.data) {
    if (Array.isArray(payload.data)) return payload.data;
    if (Array.isArray(payload.data.results)) return payload.data.results;
  }
  return [];
};

const StockHoldManagement = () => {
  const companyContext = useCompany();
  const activeCompany = companyContext?.currentCompany || companyContext?.company;
  const [holds, setHolds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ACTIVE');
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createForm] = Form.useForm();
  const [releaseModal, setReleaseModal] = useState({ visible: false, record: null, loading: false });
  const [releaseForm] = Form.useForm();
  const [detailDrawer, setDetailDrawer] = useState({ visible: false, record: null });
  const [warehouses, setWarehouses] = useState([]);
  const [items, setItems] = useState([]);
  const [batches, setBatches] = useState([]);
  const [referenceLoading, setReferenceLoading] = useState(false);

  const warehouseOptions = useMemo(
    () =>
      (warehouses || []).map((wh) => ({
        value: wh.id,
        label: `${wh.code || ''} ${wh.name || ''}`.trim(),
      })),
    [warehouses]
  );

  const itemOptions = useMemo(
    () =>
      (items || []).map((item) => ({
        value: item.id,
        label: `${item.code || item.sku || ''} ${item.name || ''}`.trim(),
      })),
    [items]
  );

  const batchOptions = useMemo(
    () =>
      (batches || []).map((batch) => ({
        value: batch.id,
        label:
          batch.internal_batch_code ||
          batch.supplier_lot_number ||
          `Batch ${batch.id}`,
      })),
    [batches]
  );

  const holdTypeOptions = useMemo(
    () =>
      Object.keys(HOLD_TYPES).map((value) => ({
        value,
        label: HOLD_TYPE_LABELS[value] || value,
      })),
    []
  );

  const loadReferences = useCallback(async () => {
    if (!activeCompany?.id) return;
    setReferenceLoading(true);
    try {
      const [warehouseRes, itemRes, batchRes] = await Promise.all([
        api.get('/api/v1/inventory/warehouses/', { params: { limit: 500 } }),
        api.get('/api/v1/inventory/items/', { params: { limit: 500 } }),
        qcService.getBatchLots({ limit: 500 }),
      ]);
      setWarehouses(asArray(warehouseRes.data));
      setItems(asArray(itemRes.data));
      setBatches(asArray(batchRes.data));
    } catch (error) {
      message.error('Unable to load reference data for stock holds.');
    } finally {
      setReferenceLoading(false);
    }
  }, [activeCompany?.id]);

  const loadHolds = useCallback(async () => {
    if (!activeCompany?.id) return;
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'ALL') {
        params.status = statusFilter;
      }
      const response = await qcService.getStockHolds(params);
      setHolds(asArray(response.data));
    } catch (error) {
      message.error('Failed to load stock holds.');
    } finally {
      setLoading(false);
    }
  }, [activeCompany?.id, statusFilter]);

  useEffect(() => {
    loadHolds();
  }, [loadHolds]);

  useEffect(() => {
    loadReferences();
  }, [loadReferences]);

  const openCreateModal = () => {
    createForm.resetFields();
    createForm.setFieldsValue({
      hold_type: 'QC_INSPECTION',
      hold_date: dayjs(),
      expected_release_date: dayjs().add(2, 'day'),
      qty_held: 1,
    });
    setCreateModalVisible(true);
  };

  const handleCreateHold = async () => {
    try {
      const values = await createForm.validateFields();
      const payload = {
        hold_type: values.hold_type,
        warehouse: values.warehouse,
        item: values.budget_item || null,
        batch_lot: values.batch_lot || null,
        qty_held: Number(values.qty_held || 0),
        hold_reason: values.hold_reason,
        hold_date: values.hold_date
          ? values.hold_date.format('YYYY-MM-DD')
          : dayjs().format('YYYY-MM-DD'),
        expected_release_date: values.expected_release_date
          ? values.expected_release_date.format('YYYY-MM-DD')
          : null,
      };
      setCreateSubmitting(true);
      await qcService.createStockHold(payload);
      message.success('Stock hold created.');
      setCreateModalVisible(false);
      createForm.resetFields();
      loadHolds();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error?.response?.data?.detail || 'Unable to create stock hold.');
      }
    } finally {
      setCreateSubmitting(false);
    }
  };

  const openReleaseModal = (record) => {
    releaseForm.resetFields();
    releaseForm.setFieldsValue({
      disposition: 'TO_WAREHOUSE',
      release_date: dayjs(),
    });
    setReleaseModal({ visible: true, record, loading: false });
  };

  const handleReleaseHold = async () => {
    if (!releaseModal.record) return;
    try {
      const values = await releaseForm.validateFields();
      setReleaseModal((prev) => ({ ...prev, loading: true }));
      await qcService.releaseStockHold(releaseModal.record.id, {
        disposition: values.disposition,
        release_date: values.release_date
          ? values.release_date.format('YYYY-MM-DD')
          : undefined,
      });
      message.success('Stock hold released.');
      releaseForm.resetFields();
      setReleaseModal({ visible: false, record: null, loading: false });
      loadHolds();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error?.response?.data?.detail || 'Unable to release hold.');
        setReleaseModal((prev) => ({ ...prev, loading: false }));
      }
    }
  };

  const handleDeleteHold = (record) => {
    Modal.confirm({
      title: `Delete hold #${record.id}?`,
      okText: 'Delete',
      okType: 'danger',
      icon: <WarningOutlined />,
      onOk: async () => {
        try {
          await qcService.deleteStockHold(record.id);
          message.success('Stock hold deleted.');
          loadHolds();
        } catch (error) {
          message.error(error?.response?.data?.detail || 'Unable to delete hold.');
        }
      },
    });
  };

  const columns = [
    {
      title: 'Hold #',
      dataIndex: 'id',
      key: 'id',
      width: 90,
      render: (value) => <Text strong>#{value}</Text>,
    },
    {
      title: 'Item / Batch',
      key: 'budget_item',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.budget_item_code || record.budget_item_code || 'Unlinked Item'}</Text>
          <Text type="secondary">{record.batch_code || record.batch_lot_label || 'No batch'}</Text>
        </Space>
      ),
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_name',
      key: 'warehouse',
    },
    {
      title: 'Quantity',
      dataIndex: 'qty_held',
      key: 'qty_held',
      render: (value) => `${Number(value || 0).toLocaleString()} units`,
    },
    {
      title: 'Hold Type',
      dataIndex: 'hold_type',
      key: 'hold_type',
      render: (value) => HOLD_TYPE_LABELS[value] || value,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value, record) => {
        const colorKey = value?.toUpperCase();
        return (
          <Tag color={HOLD_STATUS_COLORS[colorKey] || 'default'}>
            {HOLD_STATUS_LABELS[value] || value}
            {record.escalation_flag ? (
              <WarningOutlined style={{ marginLeft: 4, color: '#faad14' }} />
            ) : null}
          </Tag>
        );
      },
    },
    {
      title: 'Hold Date',
      dataIndex: 'hold_date',
      key: 'hold_date',
      render: (value) => (value ? dayjs(value).format('MMM D, YYYY') : '-'),
    },
    {
      title: 'Expected Release',
      dataIndex: 'expected_release_date',
      key: 'expected_release_date',
      render: (value) => (value ? dayjs(value).format('MMM D, YYYY') : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="View details">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => setDetailDrawer({ visible: true, record })}
            />
          </Tooltip>
          {record.status === 'ACTIVE' && (
            <Tooltip title="Release hold">
              <Button
                size="small"
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => openReleaseModal(record)}
              />
            </Tooltip>
          )}
          {record.status !== 'RELEASED' && (
            <Tooltip title="Delete hold">
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => handleDeleteHold(record)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  const activeBadgeCount = holds.filter((hold) => hold.status === 'ACTIVE').length;

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={2}>Stock Holds</Title>
          <Text type="secondary">
            Place stock on hold outside of goods receipts and manage release workflows centrally.
          </Text>
        </Col>
        <Col>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadHolds}>
              Refresh
            </Button>
            <Badge count={activeBadgeCount} offset={[6, 0]}>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
                New Hold
              </Button>
            </Badge>
          </Space>
        </Col>
      </Row>

      <Card>
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
          <Segmented
            options={statusFilters}
            value={statusFilter}
            onChange={setStatusFilter}
          />
        </Space>
        <Table
          columns={columns}
          dataSource={holds}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      <Modal
        title="Create Stock Hold"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={handleCreateHold}
        confirmLoading={createSubmitting}
        width={720}
      >
        <Form form={createForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="hold_type"
                label="Hold Type"
                rules={[{ required: true, message: 'Select hold type' }]}
              >
                <Select options={holdTypeOptions} placeholder="Select hold type" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="warehouse"
                label="Warehouse"
                rules={[{ required: true, message: 'Select warehouse' }]}
              >
                <Select
                  options={warehouseOptions}
                  showSearch
                  optionFilterProp="label"
                  placeholder="Select warehouse"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="budget_item" label="Item">
                <Select
                  options={itemOptions}
                  showSearch
                  optionFilterProp="label"
                  placeholder="Select item (optional)"
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="batch_lot" label="Batch / Lot">
                <Select
                  options={batchOptions}
                  showSearch
                  optionFilterProp="label"
                  placeholder="Select batch (optional)"
                  allowClear
                  loading={referenceLoading}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="qty_held"
                label="Quantity Held"
                rules={[{ required: true, message: 'Enter quantity' }]}
              >
                <InputNumber min={0.001} precision={3} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="hold_date"
                label="Hold Date"
                rules={[{ required: true, message: 'Select hold date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="expected_release_date" label="Expected Release">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="hold_reason"
            label="Hold Reason"
            rules={[{ required: true, message: 'Provide a reason' }]}
          >
            <Input.TextArea rows={3} placeholder="Describe why the stock is being held" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Release Hold #${releaseModal.record?.id || ''}`}
        open={releaseModal.visible}
        onCancel={() => {
          releaseForm.resetFields();
          setReleaseModal({ visible: false, record: null, loading: false });
        }}
        onOk={handleReleaseHold}
        confirmLoading={releaseModal.loading}
      >
        <Form form={releaseForm} layout="vertical">
          <Form.Item
            name="disposition"
            label="Disposition"
            rules={[{ required: true, message: 'Select disposition' }]}
          >
            <Select
              options={Object.keys(DISPOSITIONS).map((value) => ({
                value,
                label: DISPOSITION_LABELS[value] || value,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="release_date"
            label="Release Date"
            rules={[{ required: true, message: 'Select release date' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={detailDrawer.record ? `Hold #${detailDrawer.record.id}` : 'Stock Hold Detail'}
        open={detailDrawer.visible}
        width={520}
        onClose={() => setDetailDrawer({ visible: false, record: null })}
      >
        {detailDrawer.record ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="Item">
              {detailDrawer.record.budget_item_code || detailDrawer.record.budget_item_code || 'Unlinked'}
            </Descriptions.Item>
            <Descriptions.Item label="Warehouse">
              {detailDrawer.record.warehouse_name}
            </Descriptions.Item>
            <Descriptions.Item label="Hold Type">
              {HOLD_TYPE_LABELS[detailDrawer.record.hold_type] || detailDrawer.record.hold_type}
            </Descriptions.Item>
            <Descriptions.Item label="Quantity">
              {Number(detailDrawer.record.qty_held || 0).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="Hold Reason">
              {detailDrawer.record.hold_reason}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={HOLD_STATUS_COLORS[detailDrawer.record.status?.toUpperCase()] || 'default'}>
                {HOLD_STATUS_LABELS[detailDrawer.record.status] || detailDrawer.record.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Hold Date">
              {detailDrawer.record.hold_date
                ? dayjs(detailDrawer.record.hold_date).format('MMM D, YYYY')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Expected Release">
              {detailDrawer.record.expected_release_date
                ? dayjs(detailDrawer.record.expected_release_date).format('MMM D, YYYY')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="QC Result">
              {detailDrawer.record.qc_pass_result || 'Pending'}
            </Descriptions.Item>
            <Descriptions.Item label="Notes">
              {detailDrawer.record.qc_notes || 'None'}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">Select a hold to see more details.</Text>
        )}
      </Drawer>
    </div>
  );
};

export default StockHoldManagement;
