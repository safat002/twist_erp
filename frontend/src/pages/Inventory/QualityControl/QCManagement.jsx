import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  Upload,
  message,
  Drawer,
  Descriptions,
  Space,
  Statistic,
  Row,
  Col,
  Progress,
  Badge,
  Popconfirm,
  Alert,
  Empty,
  Spin,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  UploadOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  CheckOutlined,
  StopOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import qcService from '../../../services/qc';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;
const { Option } = Select;

const QCManagement = () => {
  const { company } = useCompany();
  const [activeTab, setActiveTab] = useState('inspections');
  const [loading, setLoading] = useState(false);

  // Inspections State
  const [inspections, setInspections] = useState([]);
  const [pendingGRNs, setPendingGRNs] = useState([]);
  const [checkpoints, setCheckpoints] = useState([]);
  const [inspectionModalVisible, setInspectionModalVisible] = useState(false);
  const [inspectionForm] = Form.useForm();

  // Stock Holds State
  const [holds, setHolds] = useState([]);
  const [holdModalVisible, setHoldModalVisible] = useState(false);
  const [releaseModalVisible, setReleaseModalVisible] = useState(false);
  const [selectedHold, setSelectedHold] = useState(null);
  const [holdForm] = Form.useForm();
  const [releaseForm] = Form.useForm();

  // Batch Lots State
  const [batches, setBatches] = useState([]);
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [batchForm] = Form.useForm();

  // Statistics
  const [statistics, setStatistics] = useState(null);

  useEffect(() => {
    if (company) {
      loadData();
    }
  }, [company, activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'inspections') {
        await Promise.all([
          loadInspections(),
          loadPendingGRNs(),
          loadCheckpoints(),
          loadStatistics(),
        ]);
      } else if (activeTab === 'holds') {
        await loadHolds();
      } else if (activeTab === 'batches') {
        await loadBatches();
      }
    } catch (error) {
      message.error('Failed to load data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadInspections = async () => {
    const response = await qcService.getQCResults();
    setInspections(response.data.results || response.data);
  };

  const loadPendingGRNs = async () => {
    const response = await qcService.getPendingInspections();
    setPendingGRNs(response.data);
  };

  const loadCheckpoints = async () => {
    const response = await qcService.getQCCheckpoints({ active_only: true });
    setCheckpoints(response.data.results || response.data);
  };

  const loadHolds = async () => {
    const response = await qcService.getStockHolds();
    setHolds(response.data.results || response.data);
  };

  const loadBatches = async () => {
    const response = await qcService.getBatchLots({ with_stock: true });
    setBatches(response.data.results || response.data);
  };

  const loadStatistics = async () => {
    const response = await qcService.getQCStatistics();
    setStatistics(response.data);
  };

  // ============================================================================
  // QC INSPECTION HANDLERS
  // ============================================================================

  const handleCreateInspection = () => {
    inspectionForm.resetFields();
    setInspectionModalVisible(true);
  };

  const handleInspectionSubmit = async () => {
    try {
      const values = await inspectionForm.validateFields();

      const formData = new FormData();
      Object.keys(values).forEach(key => {
        if (values[key] !== undefined && values[key] !== null) {
          if (key === 'inspected_date') {
            formData.append(key, values[key].format('YYYY-MM-DD'));
          } else if (key === 'attachment' && values[key]?.fileList?.length > 0) {
            formData.append(key, values[key].fileList[0].originFileObj);
          } else {
            formData.append(key, values[key]);
          }
        }
      });

      await qcService.createQCResult(formData);
      message.success('QC inspection recorded successfully');
      setInspectionModalVisible(false);
      loadData();
    } catch (error) {
      message.error('Failed to record inspection');
      console.error(error);
    }
  };

  // ============================================================================
  // STOCK HOLD HANDLERS
  // ============================================================================

  const handleReleaseHold = (hold) => {
    setSelectedHold(hold);
    releaseForm.resetFields();
    setReleaseModalVisible(true);
  };

  const handleReleaseSubmit = async () => {
    try {
      const values = await releaseForm.validateFields();
      await qcService.releaseStockHold(selectedHold.id, values);
      message.success('Stock hold released successfully');
      setReleaseModalVisible(false);
      loadHolds();
    } catch (error) {
      message.error('Failed to release hold');
      console.error(error);
    }
  };

  // ============================================================================
  // BATCH LOT HANDLERS
  // ============================================================================

  const handleDisposeBatch = async (batchId) => {
    try {
      await qcService.disposeBatchLot(batchId, {
        disposal_method: 'SCRAP',
        notes: 'Expired batch disposed',
      });
      message.success('Batch disposed successfully');
      loadBatches();
    } catch (error) {
      message.error('Failed to dispose batch');
      console.error(error);
    }
  };

  // ============================================================================
  // TABLE COLUMNS
  // ============================================================================

  const inspectionColumns = [
    {
      title: 'QC ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'GRN',
      dataIndex: 'grn_number',
      key: 'grn_number',
    },
    {
      title: 'Checkpoint',
      dataIndex: 'checkpoint_name',
      key: 'checkpoint_name',
    },
    {
      title: 'Date',
      dataIndex: 'inspected_date',
      key: 'inspected_date',
      render: (date) => dayjs(date).format('MMM DD, YYYY'),
    },
    {
      title: 'Inspected',
      dataIndex: 'qty_inspected',
      key: 'qty_inspected',
      align: 'right',
    },
    {
      title: 'Accepted',
      dataIndex: 'qty_accepted',
      key: 'qty_accepted',
      align: 'right',
      render: (qty) => <Text type="success">{qty}</Text>,
    },
    {
      title: 'Rejected',
      dataIndex: 'qty_rejected',
      key: 'qty_rejected',
      align: 'right',
      render: (qty) => qty > 0 ? <Text type="danger">{qty}</Text> : qty,
    },
    {
      title: 'Reject %',
      dataIndex: 'rejection_percentage',
      key: 'rejection_percentage',
      align: 'right',
      render: (pct) => {
        const color = pct > 5 ? 'red' : pct > 0 ? 'orange' : 'green';
        return <Text style={{ color }}>{pct?.toFixed(1)}%</Text>;
      },
    },
    {
      title: 'Status',
      dataIndex: 'qc_status',
      key: 'qc_status',
      render: (status) => (
        <Tag color={qcService.QC_STATUS_COLORS[status]}>
          {qcService.QC_STATUS_LABELS[status]}
        </Tag>
      ),
    },
    {
      title: 'Hold Created',
      dataIndex: 'hold_created',
      key: 'hold_created',
      render: (created) => created ? <CheckCircleOutlined style={{ color: 'orange' }} /> : null,
    },
  ];

  const holdColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: 'Item',
      dataIndex: 'budget_item_code',
      key: 'budget_item_code',
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_code',
      key: 'warehouse_code',
    },
    {
      title: 'Type',
      dataIndex: 'hold_type',
      key: 'hold_type',
      render: (type) => qcService.HOLD_TYPE_LABELS[type],
    },
    {
      title: 'Qty Held',
      dataIndex: 'qty_held',
      key: 'qty_held',
      align: 'right',
    },
    {
      title: 'Hold Date',
      dataIndex: 'hold_date',
      key: 'hold_date',
      render: (date) => dayjs(date).format('MMM DD, YYYY'),
    },
    {
      title: 'Expected Release',
      dataIndex: 'expected_release_date',
      key: 'expected_release_date',
      render: (date) => date ? dayjs(date).format('MMM DD, YYYY') : '—',
    },
    {
      title: 'Days Held',
      dataIndex: 'days_held',
      key: 'days_held',
      align: 'right',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => (
        <Badge
          status={qcService.HOLD_STATUS_COLORS[status]}
          text={qcService.HOLD_STATUS_LABELS[status]}
        />
      ),
    },
    {
      title: 'Overdue',
      key: 'is_overdue',
      render: (_, record) => {
        if (record.is_overdue) {
          return <Tag color="red" icon={<WarningOutlined />}>OVERDUE</Tag>;
        }
        return null;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'ACTIVE' && (
            <Button
              size="small"
              type="primary"
              onClick={() => handleReleaseHold(record)}
            >
              Release
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const batchColumns = [
    {
      title: 'Batch Code',
      dataIndex: 'internal_batch_code',
      key: 'internal_batch_code',
    },
    {
      title: 'Item',
      dataIndex: 'budget_item_code',
      key: 'budget_item_code',
    },
    {
      title: 'GRN',
      dataIndex: 'grn_number',
      key: 'grn_number',
    },
    {
      title: 'Received',
      dataIndex: 'received_date',
      key: 'received_date',
      render: (date) => dayjs(date).format('MMM DD, YYYY'),
    },
    {
      title: 'Expiry',
      dataIndex: 'exp_date',
      key: 'exp_date',
      render: (date) => date ? dayjs(date).format('MMM DD, YYYY') : '—',
    },
    {
      title: 'Days to Expiry',
      dataIndex: 'days_until_expiry',
      key: 'days_until_expiry',
      render: (days) => {
        if (days === null) return '—';
        const color = qcService.getExpiryColor(days);
        const status = qcService.getExpiryStatus(days);
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: 'Current Qty',
      dataIndex: 'current_qty',
      key: 'current_qty',
      align: 'right',
    },
    {
      title: 'Utilization',
      dataIndex: 'utilization_pct',
      key: 'utilization_pct',
      render: (pct) => (
        <Progress
          percent={pct}
          size="small"
          status={pct === 100 ? 'success' : 'active'}
        />
      ),
    },
    {
      title: 'Status',
      dataIndex: 'hold_status',
      key: 'hold_status',
      render: (status) => (
        <Badge
          status={qcService.BATCH_STATUS_COLORS[status]}
          text={qcService.BATCH_STATUS_LABELS[status]}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.is_expired && record.current_qty > 0 && (
            <Popconfirm
              title="Dispose this expired batch?"
              onConfirm={() => handleDisposeBatch(record.id)}
            >
              <Button size="small" danger icon={<StopOutlined />}>
                Dispose
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>Quality Control & Compliance</Title>

      {/* Statistics Row */}
      {statistics && activeTab === 'inspections' && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Inspections"
                value={statistics.total_inspections}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Pass Rate"
                value={statistics.pass_rate}
                precision={1}
                suffix="%"
                valueStyle={{ color: statistics.pass_rate >= 95 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Avg Rejection %"
                value={statistics.avg_rejection_pct}
                precision={1}
                suffix="%"
                valueStyle={{ color: statistics.avg_rejection_pct <= 5 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Pending GRNs"
                value={pendingGRNs.length}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: pendingGRNs.length > 0 ? '#faad14' : '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="QC Inspections" key="inspections">
            {pendingGRNs.length > 0 && (
              <Alert
                message={`${pendingGRNs.length} GRN(s) pending inspection`}
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                style={{ marginBottom: 16 }}
                action={
                  <Button
                    size="small"
                    type="primary"
                    onClick={handleCreateInspection}
                  >
                    Inspect Now
                  </Button>
                }
              />
            )}

            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateInspection}
              style={{ marginBottom: 16 }}
            >
              Record Inspection
            </Button>

            <Table
              dataSource={inspections}
              columns={inspectionColumns}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>

          <TabPane tab={<Badge count={holds.filter(h => h.status === 'ACTIVE').length} offset={[10, 0]}>Stock Holds</Badge>} key="holds">
            <Table
              dataSource={holds}
              columns={holdColumns}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>

          <TabPane tab="Batch Lots" key="batches">
            <Table
              dataSource={batches}
              columns={batchColumns}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* QC Inspection Modal */}
      <Modal
        title="Record QC Inspection"
        open={inspectionModalVisible}
        onOk={handleInspectionSubmit}
        onCancel={() => setInspectionModalVisible(false)}
        width={700}
      >
        <Form form={inspectionForm} layout="vertical">
          <Form.Item name="grn" label="GRN" rules={[{ required: true }]}>
            <Select placeholder="Select GRN">
              {pendingGRNs.map(grn => (
                <Option key={grn.id} value={grn.id}>
                  {grn.grn_number} - {grn.warehouse_name} ({dayjs(grn.receipt_date).format('MMM DD, YYYY')})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="checkpoint" label="Checkpoint" rules={[{ required: true }]}>
            <Select placeholder="Select Checkpoint">
              {checkpoints.map(cp => (
                <Option key={cp.id} value={cp.id}>
                  {cp.checkpoint_name} (Threshold: {cp.acceptance_threshold}%)
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="qty_inspected" label="Qty Inspected" rules={[{ required: true }]}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="qty_accepted" label="Qty Accepted" rules={[{ required: true }]}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="qty_rejected" label="Qty Rejected" rules={[{ required: true }]}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="rejection_reason" label="Rejection Reason">
            <Select placeholder="Select reason">
              {Object.entries(qcService.REJECTION_REASON_LABELS).map(([key, label]) => (
                <Option key={key} value={key}>{label}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="notes" label="Notes">
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item name="attachment" label="Attachment (COA, Photos)">
            <Upload maxCount={1}>
              <Button icon={<UploadOutlined />}>Upload File</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>

      {/* Release Hold Modal */}
      <Modal
        title="Release Stock Hold"
        open={releaseModalVisible}
        onOk={handleReleaseSubmit}
        onCancel={() => setReleaseModalVisible(false)}
      >
        <Form form={releaseForm} layout="vertical">
          <Form.Item name="disposition" label="Disposition" rules={[{ required: true }]}>
            <Select placeholder="Select disposition">
              {Object.entries(qcService.DISPOSITION_LABELS).map(([key, label]) => (
                <Option key={key} value={key}>{label}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="notes" label="Release Notes">
            <TextArea rows={3} placeholder="Enter release notes..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default QCManagement;
