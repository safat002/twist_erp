import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Upload,
  InputNumber,
  message,
  Row,
  Col,
  Divider,
  Typography,
  Descriptions,
  Alert,
  Popconfirm,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckOutlined,
  UploadOutlined,
  InboxOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
  BarcodeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import * as procurementService from '../../../services/procurement';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

const GoodsReceiptManagement = () => {
  const { currentCompany } = useCompany();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [grns, setGrns] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [editingGRN, setEditingGRN] = useState(null);
  const [selectedGRN, setSelectedGRN] = useState(null);
  const [selectedPO, setSelectedPO] = useState(null);

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
        status: 'ISSUED', // Only issued POs can be received
      });
      const data = response.data?.results || response.data || [];
      setPurchaseOrders(data);
    } catch (error) {
      message.error('Failed to load purchase orders');
      console.error(error);
    }
  }, [currentCompany]);

  useEffect(() => {
    fetchGRNs();
    fetchPurchaseOrders();
  }, [fetchGRNs, fetchPurchaseOrders]);

  // Handle PO selection - load PO details
  const handlePOSelect = async (poId) => {
    try {
      const response = await procurementService.getPurchaseOrder(poId);
      const po = response.data;
      setSelectedPO(po);

      // Initialize form lines with PO line items
      const lines = po.lines?.map((line, index) => ({
        key: index,
        purchase_order_line: line.id,
        item: line.budget_item || line.budget_item,
        item_code: line.budget_item_code || line.budget_item_code,
        item_name: line.budget_item_name || line.description,
        ordered_quantity: line.quantity,
        quantity_received: 0,
        batch_no: '',
        expiry_date: null,
        serial_numbers: [],
        manufacturer_batch_no: '',
        certificate_of_analysis: null,
        is_serialized: line.budget_item?.is_serialized || false,
        is_batch_tracked: line.budget_item?.is_batch_tracked || false,
      })) || [];

      form.setFieldsValue({ lines });
    } catch (error) {
      message.error('Failed to load purchase order details');
      console.error(error);
    }
  };

  // Open create modal
  const handleCreate = () => {
    setEditingGRN(null);
    setSelectedPO(null);
    form.resetFields();
    form.setFieldsValue({
      receipt_date: dayjs(),
      status: 'DRAFT',
    });
    setModalVisible(true);
  };

  // Open edit modal
  const handleEdit = async (grn) => {
    try {
      const response = await procurementService.getGoodsReceipt(grn.id);
      const fullGRN = response.data;
      setEditingGRN(fullGRN);

      // Load PO details
      const poResponse = await procurementService.getPurchaseOrder(fullGRN.purchase_order);
      setSelectedPO(poResponse.data);

      form.setFieldsValue({
        purchase_order: fullGRN.purchase_order,
        receipt_date: dayjs(fullGRN.receipt_date),
        notes: fullGRN.notes,
        lines: fullGRN.lines?.map((line, index) => ({
          ...line,
          key: index,
          expiry_date: line.expiry_date ? dayjs(line.expiry_date) : null,
        })),
      });
      setModalVisible(true);
    } catch (error) {
      message.error('Failed to load goods receipt');
      console.error(error);
    }
  };

  // View details
  const handleView = async (grn) => {
    try {
      const response = await procurementService.getGoodsReceipt(grn.id);
      setSelectedGRN(response.data);
      setDetailModalVisible(true);
    } catch (error) {
      message.error('Failed to load goods receipt details');
      console.error(error);
    }
  };

  // Delete GRN
  const handleDelete = async (id) => {
    try {
      await procurementService.deleteGoodsReceipt(id);
      message.success('Goods receipt deleted successfully');
      fetchGRNs();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to delete goods receipt');
    }
  };

  // Post GRN (triggers stock movement)
  const handlePost = async (id) => {
    try {
      await procurementService.postGoodsReceipt(id);
      message.success('Goods receipt posted successfully! Stock has been updated.');
      fetchGRNs();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to post goods receipt');
    }
  };

  // Submit form
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Prepare data
      const data = {
        company: currentCompany.id,
        purchase_order: values.purchase_order,
        supplier: selectedPO?.supplier,
        receipt_date: values.receipt_date.format('YYYY-MM-DD'),
        notes: values.notes || '',
        status: values.status || 'DRAFT',
        lines: values.lines?.map(line => ({
          purchase_order_line: line.purchase_order_line,
          item: line.budget_item,
          quantity_received: line.quantity_received,
          batch_no: line.batch_no || '',
          expiry_date: line.expiry_date ? line.expiry_date.format('YYYY-MM-DD') : null,
          serial_numbers: line.serial_numbers || [],
          manufacturer_batch_no: line.manufacturer_batch_no || '',
          certificate_of_analysis: line.certificate_of_analysis || null,
        })),
      };

      if (editingGRN) {
        await procurementService.updateGoodsReceipt(editingGRN.id, data);
        message.success('Goods receipt updated successfully');
      } else {
        await procurementService.createGoodsReceipt(data);
        message.success('Goods receipt created successfully');
      }

      setModalVisible(false);
      form.resetFields();
      fetchGRNs();
    } catch (error) {
      if (error.errorFields) {
        message.error('Please fill in all required fields');
      } else {
        message.error(error.response?.data?.detail || 'Failed to save goods receipt');
      }
      console.error(error);
    }
  };

  // Columns for GRN list
  const columns = [
    {
      title: 'GRN Number',
      dataIndex: 'receipt_number',
      key: 'receipt_number',
      fixed: 'left',
      width: 140,
    },
    {
      title: 'Date',
      dataIndex: 'receipt_date',
      key: 'receipt_date',
      width: 120,
      render: (date) => date ? dayjs(date).format('DD MMM YYYY') : '-',
    },
    {
      title: 'PO Number',
      dataIndex: 'purchase_order_number',
      key: 'purchase_order_number',
      width: 140,
    },
    {
      title: 'Supplier',
      dataIndex: 'supplier_name',
      key: 'supplier_name',
      width: 200,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Tag color={procurementService.getGRNStatusColor(status)}>
          {procurementService.getGRNStatusLabel(status)}
        </Tag>
      ),
    },
    {
      title: 'QC Status',
      dataIndex: 'quality_status',
      key: 'quality_status',
      width: 120,
      render: (status) => status ? (
        <Tag
          color={procurementService.getQualityStatusColor(status)}
          icon={status === 'pending' ? <WarningOutlined /> : status === 'passed' ? <CheckOutlined /> : null}
        >
          {procurementService.getQualityStatusLabel(status)}
        </Tag>
      ) : <Tag>N/A</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
            size="small"
          >
            View
          </Button>
          {record.status === 'DRAFT' && (
            <>
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
                size="small"
              />
              <Popconfirm
                title="Are you sure you want to post this GRN?"
                description="This will update stock levels and cannot be undone."
                onConfirm={() => handlePost(record.id)}
                okText="Yes, Post"
                cancelText="Cancel"
              >
                <Button type="primary" size="small" icon={<CheckOutlined />}>
                  Post
                </Button>
              </Popconfirm>
              <Popconfirm
                title="Delete this GRN?"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button
                  danger
                  type="link"
                  icon={<DeleteOutlined />}
                  size="small"
                />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  // Line items form component
  const LineItemsForm = () => {
    const lines = Form.useWatch('lines', form) || [];

    return (
      <div>
        <Table
          dataSource={lines}
          pagination={false}
          size="small"
          scroll={{ x: 1200 }}
          columns={[
            {
              title: 'Item Code',
              dataIndex: 'item_code',
              width: 120,
              fixed: 'left',
            },
            {
              title: 'Item Name',
              dataIndex: 'item_name',
              width: 200,
            },
            {
              title: 'Ordered Qty',
              dataIndex: 'ordered_quantity',
              width: 100,
              render: (qty) => qty?.toFixed(2) || '0',
            },
            {
              title: 'Received Qty *',
              key: 'quantity_received',
              width: 120,
              render: (_, record, index) => (
                <Form.Item
                  name={['lines', index, 'quantity_received']}
                  rules={[{ required: true, message: 'Required' }]}
                  style={{ margin: 0 }}
                >
                  <InputNumber
                    min={0}
                    max={record.ordered_quantity}
                    style={{ width: '100%' }}
                    placeholder="0"
                  />
                </Form.Item>
              ),
            },
            {
              title: 'Batch Number',
              key: 'batch_no',
              width: 140,
              render: (_, record, index) => record.is_batch_tracked ? (
                <Form.Item
                  name={['lines', index, 'batch_no']}
                  rules={[{ required: record.is_batch_tracked, message: 'Required for batch-tracked items' }]}
                  style={{ margin: 0 }}
                >
                  <Input placeholder="BATCH-001" />
                </Form.Item>
              ) : <Text type="secondary">N/A</Text>,
            },
            {
              title: 'Expiry Date',
              key: 'expiry_date',
              width: 140,
              render: (_, record, index) => record.is_batch_tracked ? (
                <Form.Item
                  name={['lines', index, 'expiry_date']}
                  style={{ margin: 0 }}
                >
                  <DatePicker style={{ width: '100%' }} format="DD MMM YYYY" />
                </Form.Item>
              ) : <Text type="secondary">N/A</Text>,
            },
            {
              title: 'Mfg Batch No',
              key: 'manufacturer_batch_no',
              width: 140,
              render: (_, record, index) => record.is_batch_tracked ? (
                <Form.Item
                  name={['lines', index, 'manufacturer_batch_no']}
                  style={{ margin: 0 }}
                >
                  <Input placeholder="MFG-XYZ-123" />
                </Form.Item>
              ) : <Text type="secondary">N/A</Text>,
            },
            {
              title: 'Serial Numbers',
              key: 'serial_numbers',
              width: 220,
              render: (_, record, index) => (
                <Form.Item
                  name={['lines', index, 'serial_numbers']}
                  rules={
                    record.is_serialized
                      ? [
                          {
                            validator: (_, value) => {
                              const qty = form.getFieldValue(['lines', index, 'quantity_received']);
                              if (value && value.length !== parseInt(qty || 0, 10)) {
                                return Promise.reject(`Must provide ${qty} serial numbers`);
                              }
                              return Promise.resolve();
                            },
                          },
                        ]
                      : []
                  }
                  style={{ margin: 0 }}
                >
                  <Select
                    mode="tags"
                    placeholder={
                      record.is_serialized ? 'Enter required serial numbers' : 'Optional serial list'
                    }
                    tokenSeparators={[',', ' ', ';']}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              ),
            },
          ]}
        />
      </div>
    );
  };

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={2}>Goods Receipts (GRN)</Title>
          <Text type="secondary">
            Receive goods from purchase orders, capture batch/serial numbers, and trigger QC inspections
          </Text>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            Create GRN
          </Button>
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={grns}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} goods receipts`,
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingGRN ? 'Edit Goods Receipt' : 'Create Goods Receipt'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        onOk={handleSubmit}
        width={1400}
        okText={editingGRN ? 'Update' : 'Create'}
        cancelText="Cancel"
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="purchase_order"
                label="Purchase Order"
                rules={[{ required: true, message: 'Please select a purchase order' }]}
              >
                <Select
                  placeholder="Select PO"
                  onChange={handlePOSelect}
                  disabled={!!editingGRN}
                  showSearch
                  filterOption={(input, option) =>
                    option.children.toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {purchaseOrders.map(po => (
                    <Select.Option key={po.id} value={po.id}>
                      {po.order_number} - {po.supplier_name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="receipt_date"
                label="Receipt Date"
                rules={[{ required: true, message: 'Please select receipt date' }]}
              >
                <DatePicker style={{ width: '100%' }} format="DD MMM YYYY" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="notes" label="Notes">
            <TextArea rows={2} placeholder="Any remarks about this receipt..." />
          </Form.Item>

          {selectedPO && (
            <>
              <Divider orientation="left">
                <Space>
                  <InboxOutlined />
                  Receipt Line Items
                </Space>
              </Divider>

              <Alert
                message="Batch & Serial Number Tracking"
                description="Batch numbers and expiry dates are required for batch-tracked items. Serial numbers must match the received quantity for serialized items."
                type="info"
                showIcon
                icon={<BarcodeOutlined />}
                style={{ marginBottom: 16 }}
              />

              <LineItemsForm />
            </>
          )}
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title={`Goods Receipt: ${selectedGRN?.receipt_number}`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Close
          </Button>,
          selectedGRN?.quality_status === 'pending' && (
            <Button
              key="qc"
              type="primary"
              icon={<SafetyCertificateOutlined />}
              onClick={() => {
                setDetailModalVisible(false);
                // Navigate to QC page with GRN pre-selected
                window.location.href = `/inventory/quality-control?grn=${selectedGRN.id}`;
              }}
            >
              Perform QC Inspection
            </Button>
          ),
        ]}
        width={1000}
      >
        {selectedGRN && (
          <div>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="GRN Number">{selectedGRN.receipt_number}</Descriptions.Item>
              <Descriptions.Item label="Date">{dayjs(selectedGRN.receipt_date).format('DD MMM YYYY')}</Descriptions.Item>
              <Descriptions.Item label="PO Number">{selectedGRN.purchase_order_number}</Descriptions.Item>
              <Descriptions.Item label="Supplier">{selectedGRN.supplier_name}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={procurementService.getGRNStatusColor(selectedGRN.status)}>
                  {procurementService.getGRNStatusLabel(selectedGRN.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="QC Status">
                <Tag color={procurementService.getQualityStatusColor(selectedGRN.quality_status)}>
                  {procurementService.getQualityStatusLabel(selectedGRN.quality_status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Notes" span={2}>{selectedGRN.notes || 'N/A'}</Descriptions.Item>
            </Descriptions>

            {selectedGRN.quality_status === 'pending' && (
              <Alert
                message="QC Inspection Required"
                description="This GRN has been marked for quality control inspection. Stock is currently in QUARANTINE status."
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                style={{ marginTop: 16 }}
              />
            )}

            <Divider>Receipt Lines</Divider>
            <Table
              dataSource={selectedGRN.lines}
              pagination={false}
              size="small"
              columns={[
                { title: 'Item Code', dataIndex: 'item_code', width: 120 },
                { title: 'Item Name', dataIndex: 'item_name', width: 200 },
                { title: 'Qty Received', dataIndex: 'quantity_received', width: 100, render: (qty) => qty?.toFixed(2) },
                { title: 'Batch No', dataIndex: 'batch_no', width: 120, render: (val) => val || '-' },
                {
                  title: 'Expiry Date',
                  dataIndex: 'expiry_date',
                  width: 120,
                  render: (date) => date ? dayjs(date).format('DD MMM YYYY') : '-'
                },
                {
                  title: 'Serial Numbers',
                  dataIndex: 'serial_numbers',
                  render: (serials) => serials?.length > 0 ? (
                    <Space wrap>
                      {serials.map((sn, idx) => <Tag key={idx}>{sn}</Tag>)}
                    </Space>
                  ) : '-'
                },
              ]}
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default GoodsReceiptManagement;
