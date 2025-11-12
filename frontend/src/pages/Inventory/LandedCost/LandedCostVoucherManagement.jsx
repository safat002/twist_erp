import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  DatePicker,
  InputNumber,
  Select,
  message,
  Drawer,
  Descriptions,
  Steps,
  Row,
  Col,
  Statistic,
  Divider,
  Popconfirm,
  Alert,
  Checkbox,
  Typography,
  Tooltip,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SendOutlined,
  CheckOutlined,
  DollarOutlined,
  FileTextOutlined,
  SyncOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import landedCostVoucherService from '../../../services/landedCostVoucher';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;
const { Step } = Steps;
const { TextArea } = Input;
const { Option } = Select;

const LandedCostVoucherManagement = () => {
  const { company } = useCompany();
  const [loading, setLoading] = useState(false);
  const [vouchers, setVouchers] = useState([]);
  const [selectedVoucher, setSelectedVoucher] = useState(null);
  const [viewDrawerVisible, setViewDrawerVisible] = useState(false);
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [allocationModalVisible, setAllocationModalVisible] = useState(false);
  const [allocations, setAllocations] = useState([]);
  const [allocationPlan, setAllocationPlan] = useState(null);
  const [goodsReceipts, setGoodsReceipts] = useState([]);
  const [selectedGRNs, setSelectedGRNs] = useState([]);
  const [apportionmentMethod, setApportionmentMethod] = useState('BY_VALUE');
  const [form] = Form.useForm();
  const [allocationForm] = Form.useForm();

  useEffect(() => {
    loadVouchers();
    loadGoodsReceipts();
  }, [company]);

  const loadVouchers = async () => {
    setLoading(true);
    try {
      const response = await landedCostVoucherService.fetchLandedCostVouchers();
      setVouchers(response.data.results || response.data || []);
    } catch (error) {
      message.error('Failed to load vouchers');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadGoodsReceipts = async () => {
    try {
      // Fetch GRNs - adjust API endpoint as needed
      const response = await fetch('/api/v1/inventory/goods-receipts/');
      const data = await response.json();
      setGoodsReceipts(data.results || data || []);
    } catch (error) {
      console.error('Failed to load goods receipts:', error);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setSelectedVoucher(null);
    setFormModalVisible(true);
  };

  const handleEdit = (record) => {
    if (!landedCostVoucherService.canEditVoucher(record)) {
      message.warning('This voucher cannot be edited in its current status');
      return;
    }
    setSelectedVoucher(record);
    form.setFieldsValue({
      ...record,
      voucher_date: dayjs(record.voucher_date),
      invoice_date: record.invoice_date ? dayjs(record.invoice_date) : null,
    });
    setFormModalVisible(true);
  };

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const data = {
        ...values,
        voucher_date: values.voucher_date.format('YYYY-MM-DD'),
        invoice_date: values.invoice_date ? values.invoice_date.format('YYYY-MM-DD') : null,
        company: company.id,
      };

      if (selectedVoucher) {
        await landedCostVoucherService.updateLandedCostVoucher(selectedVoucher.id, data);
        message.success('Voucher updated successfully');
      } else {
        await landedCostVoucherService.createLandedCostVoucher(data);
        message.success('Voucher created successfully');
      }

      setFormModalVisible(false);
      loadVouchers();
    } catch (error) {
      message.error('Failed to save voucher');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForApproval = async (voucher) => {
    try {
      await landedCostVoucherService.submitVoucher(voucher.id);
      message.success('Voucher submitted for approval');
      loadVouchers();
    } catch (error) {
      message.error('Failed to submit voucher');
    }
  };

  const handleApprove = async (voucher) => {
    try {
      await landedCostVoucherService.approveVoucher(voucher.id);
      message.success('Voucher approved');
      loadVouchers();
    } catch (error) {
      message.error('Failed to approve voucher');
    }
  };

  const handleOpenAllocation = async (voucher) => {
    setSelectedVoucher(voucher);
    setSelectedGRNs([]);
    setAllocationPlan(null);
    setAllocationModalVisible(true);
  };

  const handleGenerateAllocationPlan = async () => {
    if (selectedGRNs.length === 0) {
      message.warning('Please select at least one GRN');
      return;
    }

    setLoading(true);
    try {
      const response = await landedCostVoucherService.generateAllocationPlan(
        selectedVoucher.id,
        selectedGRNs,
        apportionmentMethod
      );
      setAllocationPlan(response.data.allocation_plan);
      message.success('Allocation plan generated');
    } catch (error) {
      message.error('Failed to generate allocation plan');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleAllocate = async () => {
    if (!allocationPlan || allocationPlan.length === 0) {
      message.warning('Please generate an allocation plan first');
      return;
    }

    setLoading(true);
    try {
      await landedCostVoucherService.allocateVoucher(selectedVoucher.id, allocationPlan);
      message.success('Voucher allocated to cost layers');
      setAllocationModalVisible(false);
      loadVouchers();
    } catch (error) {
      message.error('Failed to allocate voucher');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handlePostToGL = async (voucher) => {
    try {
      await landedCostVoucherService.postVoucherToGL(voucher.id);
      message.success('Voucher posted to GL');
      loadVouchers();
    } catch (error) {
      message.error('Failed to post to GL');
    }
  };

  const handleView = async (voucher) => {
    setSelectedVoucher(voucher);
    setLoading(true);
    try {
      const response = await landedCostVoucherService.fetchAllocations(voucher.id);
      setAllocations(response.data.results || response.data || []);
      setViewDrawerVisible(true);
    } catch (error) {
      message.error('Failed to load voucher details');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (voucher) => {
    Modal.confirm({
      title: 'Cancel Voucher',
      content: 'Are you sure you want to cancel this voucher? This action cannot be undone.',
      onOk: async () => {
        try {
          await landedCostVoucherService.cancelVoucher(voucher.id, 'Cancelled by user');
          message.success('Voucher cancelled');
          loadVouchers();
        } catch (error) {
          message.error('Failed to cancel voucher');
        }
      },
    });
  };

  const getStatusColor = (status) => {
    const colors = {
      DRAFT: 'default',
      SUBMITTED: 'processing',
      APPROVED: 'success',
      ALLOCATED: 'purple',
      POSTED: 'blue',
      CANCELLED: 'error',
    };
    return colors[status] || 'default';
  };

  const getCurrentStep = (status) => {
    const steps = {
      DRAFT: 0,
      SUBMITTED: 1,
      APPROVED: 2,
      ALLOCATED: 3,
      POSTED: 4,
      CANCELLED: -1,
    };
    return steps[status] || 0;
  };

  const columns = [
    {
      title: 'Voucher #',
      dataIndex: 'voucher_number',
      key: 'voucher_number',
      fixed: 'left',
      width: 150,
    },
    {
      title: 'Date',
      dataIndex: 'voucher_date',
      key: 'voucher_date',
      width: 120,
      render: (text) => dayjs(text).format('MMM DD, YYYY'),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Total Cost',
      dataIndex: 'total_cost',
      key: 'total_cost',
      width: 130,
      render: (value, record) => landedCostVoucherService.formatAmount(value, record.currency),
    },
    {
      title: 'Allocated',
      dataIndex: 'allocated_cost',
      key: 'allocated_cost',
      width: 130,
      render: (value, record) => landedCostVoucherService.formatAmount(value, record.currency),
    },
    {
      title: 'Unallocated',
      key: 'unallocated',
      width: 130,
      render: (_, record) => {
        const unallocated = landedCostVoucherService.calculateUnallocated(record);
        return landedCostVoucherService.formatAmount(unallocated, record.currency);
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {landedCostVoucherService.getStatusLabel(status)}
        </Tag>
      ),
    },
    {
      title: 'GL Posted',
      dataIndex: 'posted_to_gl',
      key: 'posted_to_gl',
      width: 100,
      render: (posted) => posted ? <CheckOutlined style={{ color: '#52c41a' }} /> : null,
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 220,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleView(record)}
            />
          </Tooltip>
          {landedCostVoucherService.canEditVoucher(record) && (
            <Tooltip title="Edit">
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              />
            </Tooltip>
          )}
          {landedCostVoucherService.canSubmitVoucher(record) && (
            <Tooltip title="Submit">
              <Button
                type="link"
                size="small"
                icon={<SendOutlined />}
                onClick={() => handleSubmitForApproval(record)}
              />
            </Tooltip>
          )}
          {landedCostVoucherService.canApproveVoucher(record) && (
            <Tooltip title="Approve">
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
              />
            </Tooltip>
          )}
          {landedCostVoucherService.canAllocateVoucher(record) && (
            <Tooltip title="Allocate">
              <Button
                type="link"
                size="small"
                icon={<SyncOutlined />}
                onClick={() => handleOpenAllocation(record)}
              />
            </Tooltip>
          )}
          {landedCostVoucherService.canPostToGL(record) && (
            <Tooltip title="Post to GL">
              <Button
                type="link"
                size="small"
                icon={<DollarOutlined />}
                onClick={() => handlePostToGL(record)}
              />
            </Tooltip>
          )}
          {record.status === 'DRAFT' && (
            <Tooltip title="Cancel">
              <Button
                type="link"
                size="small"
                danger
                icon={<CloseOutlined />}
                onClick={() => handleCancel(record)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  const allocationPlanColumns = [
    {
      title: 'GRN',
      dataIndex: 'goods_receipt_number',
      key: 'goods_receipt_number',
      render: (_, record) => {
        const grn = goodsReceipts.find(g => g.id === record.goods_receipt_id);
        return grn?.grn_number || 'N/A';
      },
    },
    {
      title: 'Product',
      key: 'product',
      render: (_, record) => {
        // You may need to fetch product details
        return `Product ID: ${record.product_id}`;
      },
    },
    {
      title: 'Allocated Amount',
      dataIndex: 'allocated_amount',
      key: 'allocated_amount',
      render: (value) => landedCostVoucherService.formatAmount(value),
    },
    {
      title: 'Allocation %',
      dataIndex: 'allocation_percentage',
      key: 'allocation_percentage',
      render: (value) => `${parseFloat(value).toFixed(2)}%`,
    },
    {
      title: 'Basis Value',
      dataIndex: 'basis_value',
      key: 'basis_value',
      render: (value) => landedCostVoucherService.formatAmount(value),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4}>Landed Cost Vouchers</Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            New Voucher
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={vouchers}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} vouchers`,
          }}
        />
      </Card>

      {/* Create/Edit Form Modal */}
      <Modal
        title={selectedVoucher ? 'Edit Voucher' : 'Create New Voucher'}
        open={formModalVisible}
        onCancel={() => setFormModalVisible(false)}
        width={700}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="voucher_date"
                label="Voucher Date"
                rules={[{ required: true, message: 'Please select voucher date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="total_cost"
                label="Total Cost"
                rules={[{ required: true, message: 'Please enter total cost' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  precision={2}
                  formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => value.replace(/\$\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: 'Please enter description' }]}
          >
            <TextArea rows={3} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="currency" label="Currency" initialValue="USD">
                <Select>
                  <Option value="USD">USD</Option>
                  <Option value="EUR">EUR</Option>
                  <Option value="BDT">BDT</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="invoice_number" label="Invoice Number">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="invoice_date" label="Invoice Date">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="supplier_id" label="Supplier ID">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="notes" label="Notes">
            <TextArea rows={2} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {selectedVoucher ? 'Update' : 'Create'}
              </Button>
              <Button onClick={() => setFormModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Allocation Modal */}
      <Modal
        title="Allocate Voucher to Cost Layers"
        open={allocationModalVisible}
        onCancel={() => setAllocationModalVisible(false)}
        width={900}
        footer={null}
      >
        {selectedVoucher && (
          <>
            <Alert
              message={`Total Cost: ${landedCostVoucherService.formatAmount(selectedVoucher.total_cost, selectedVoucher.currency)}`}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Steps current={allocationPlan ? 1 : 0} style={{ marginBottom: 24 }}>
              <Step title="Select GRNs" description="Choose receipts to allocate to" />
              <Step title="Preview Plan" description="Review allocation distribution" />
              <Step title="Confirm" description="Apply to cost layers" />
            </Steps>

            {!allocationPlan ? (
              <>
                <Divider>Step 1: Select Goods Receipts</Divider>
                <Form.Item label="Apportionment Method">
                  <Select
                    value={apportionmentMethod}
                    onChange={setApportionmentMethod}
                    style={{ width: 300 }}
                  >
                    <Option value="BY_VALUE">By Value</Option>
                    <Option value="BY_QUANTITY">By Quantity</Option>
                    <Option value="EQUAL">Equal Distribution</Option>
                  </Select>
                </Form.Item>

                <Form.Item label="Select GRNs">
                  <Checkbox.Group
                    options={goodsReceipts.map(grn => ({
                      label: `${grn.grn_number} - ${dayjs(grn.receipt_date).format('MMM DD, YYYY')}`,
                      value: grn.id,
                    }))}
                    value={selectedGRNs}
                    onChange={setSelectedGRNs}
                  />
                </Form.Item>

                <Button
                  type="primary"
                  onClick={handleGenerateAllocationPlan}
                  loading={loading}
                  disabled={selectedGRNs.length === 0}
                >
                  Generate Allocation Plan
                </Button>
              </>
            ) : (
              <>
                <Divider>Step 2: Review Allocation Plan</Divider>
                <Table
                  columns={allocationPlanColumns}
                  dataSource={allocationPlan}
                  rowKey={(record) => `${record.goods_receipt_id}-${record.product_id}`}
                  pagination={false}
                  size="small"
                  style={{ marginBottom: 16 }}
                />

                <Space>
                  <Button type="primary" onClick={handleAllocate} loading={loading}>
                    Confirm & Allocate
                  </Button>
                  <Button onClick={() => setAllocationPlan(null)}>
                    Back
                  </Button>
                  <Button onClick={() => setAllocationModalVisible(false)}>
                    Cancel
                  </Button>
                </Space>
              </>
            )}
          </>
        )}
      </Modal>

      {/* View Details Drawer */}
      <Drawer
        title="Voucher Details"
        placement="right"
        width={720}
        onClose={() => setViewDrawerVisible(false)}
        open={viewDrawerVisible}
      >
        {selectedVoucher && (
          <>
            <Steps current={getCurrentStep(selectedVoucher.status)} size="small" style={{ marginBottom: 24 }}>
              <Step title="Draft" />
              <Step title="Submitted" />
              <Step title="Approved" />
              <Step title="Allocated" />
              <Step title="Posted to GL" />
            </Steps>

            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Voucher Number" span={2}>
                {selectedVoucher.voucher_number}
              </Descriptions.Item>
              <Descriptions.Item label="Date">
                {dayjs(selectedVoucher.voucher_date).format('MMM DD, YYYY')}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={getStatusColor(selectedVoucher.status)}>
                  {landedCostVoucherService.getStatusLabel(selectedVoucher.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Total Cost" span={2}>
                {landedCostVoucherService.formatAmount(selectedVoucher.total_cost, selectedVoucher.currency)}
              </Descriptions.Item>
              <Descriptions.Item label="Allocated">
                {landedCostVoucherService.formatAmount(selectedVoucher.allocated_cost, selectedVoucher.currency)}
              </Descriptions.Item>
              <Descriptions.Item label="Unallocated">
                {landedCostVoucherService.formatAmount(
                  landedCostVoucherService.calculateUnallocated(selectedVoucher),
                  selectedVoucher.currency
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Description" span={2}>
                {selectedVoucher.description}
              </Descriptions.Item>
              {selectedVoucher.invoice_number && (
                <Descriptions.Item label="Invoice #" span={2}>
                  {selectedVoucher.invoice_number}
                </Descriptions.Item>
              )}
              {selectedVoucher.posted_to_gl && (
                <Descriptions.Item label="GL Journal Entry" span={2}>
                  JE #{selectedVoucher.je_id} - Posted on {dayjs(selectedVoucher.gl_posted_date).format('MMM DD, YYYY')}
                </Descriptions.Item>
              )}
            </Descriptions>

            {allocations.length > 0 && (
              <>
                <Divider>Cost Layer Allocations</Divider>
                <Table
                  dataSource={allocations}
                  rowKey="id"
                  size="small"
                  pagination={false}
                  columns={[
                    {
                      title: 'GRN',
                      dataIndex: 'goods_receipt_number',
                      key: 'goods_receipt_number',
                    },
                    {
                      title: 'Product',
                      dataIndex: 'product_name',
                      key: 'product_name',
                    },
                    {
                      title: 'Allocated',
                      dataIndex: 'allocated_amount',
                      key: 'allocated_amount',
                      render: (value) => landedCostVoucherService.formatAmount(value),
                    },
                    {
                      title: 'To Inventory',
                      dataIndex: 'to_inventory',
                      key: 'to_inventory',
                      render: (value) => landedCostVoucherService.formatAmount(value),
                    },
                    {
                      title: 'To COGS',
                      dataIndex: 'to_cogs',
                      key: 'to_cogs',
                      render: (value) => landedCostVoucherService.formatAmount(value),
                    },
                  ]}
                />
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default LandedCostVoucherManagement;
