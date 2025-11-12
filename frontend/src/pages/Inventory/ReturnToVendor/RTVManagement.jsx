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
  Typography,
  Tooltip,
  Badge,
  Timeline,
  List,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SendOutlined,
  CheckOutlined,
  CloseOutlined,
  TruckOutlined,
  DollarOutlined,
  FileTextOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import rtvService from '../../../services/rtv';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;
const { Step } = Steps;
const { TextArea } = Input;
const { Option } = Select;

const RTVManagement = () => {
  const { company } = useCompany();
  const [loading, setLoading] = useState(false);
  const [rtvs, setRTVs] = useState([]);
  const [selectedRTV, setSelectedRTV] = useState(null);
  const [viewDrawerVisible, setViewDrawerVisible] = useState(false);
  const [formModalVisible, setFormModalVisible] = useState(false);
  const [lineModalVisible, setLineModalVisible] = useState(false);
  const [shippingModalVisible, setShippingModalVisible] = useState(false);
  const [completeModalVisible, setCompleteModalVisible] = useState(false);
  const [rtvLines, setRTVLines] = useState([]);
  const [goodsReceipts, setGoodsReceipts] = useState([]);
  const [products, setProducts] = useState([]);
  const [uoms, setUOMs] = useState([]);
  const [form] = Form.useForm();
  const [lineForm] = Form.useForm();
  const [shippingForm] = Form.useForm();
  const [completeForm] = Form.useForm();

  useEffect(() => {
    loadRTVs();
    loadGoodsReceipts();
    loadProducts();
    loadUOMs();
  }, [company]);

  const loadRTVs = async () => {
    setLoading(true);
    try {
      const response = await rtvService.fetchRTVs();
      setRTVs(response.data.results || response.data || []);
    } catch (error) {
      message.error('Failed to load RTVs');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadGoodsReceipts = async () => {
    try {
      const response = await fetch('/api/v1/inventory/goods-receipts/');
      const data = await response.json();
      setGoodsReceipts(data.results || data || []);
    } catch (error) {
      console.error('Failed to load goods receipts:', error);
    }
  };

  const loadProducts = async () => {
    try {
      const response = await fetch('/api/v1/inventory/products/');
      const data = await response.json();
      setProducts(data.results || data || []);
    } catch (error) {
      console.error('Failed to load products:', error);
    }
  };

  const loadUOMs = async () => {
    try {
      const response = await fetch('/api/v1/inventory/units-of-measure/');
      const data = await response.json();
      setUOMs(data.results || data || []);
    } catch (error) {
      console.error('Failed to load UOMs:', error);
    }
  };

  const handleCreate = () => {
    form.resetFields();
    setSelectedRTV(null);
    setFormModalVisible(true);
  };

  const handleEdit = (record) => {
    if (!rtvService.canEditRTV(record)) {
      message.warning('This RTV cannot be edited in its current status');
      return;
    }
    setSelectedRTV(record);
    form.setFieldsValue({
      ...record,
      rtv_date: dayjs(record.rtv_date),
    });
    setFormModalVisible(true);
  };

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const data = {
        ...values,
        rtv_date: values.rtv_date.format('YYYY-MM-DD'),
        company: company.id,
      };

      if (selectedRTV) {
        await rtvService.updateRTV(selectedRTV.id, data);
        message.success('RTV updated successfully');
      } else {
        await rtvService.createRTV(data);
        message.success('RTV created successfully');
      }

      setFormModalVisible(false);
      loadRTVs();
    } catch (error) {
      message.error('Failed to save RTV');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddLine = (rtv) => {
    setSelectedRTV(rtv);
    lineForm.resetFields();
    setLineModalVisible(true);
  };

  const handleSubmitLine = async (values) => {
    setLoading(true);
    try {
      await rtvService.createRTVLine({
        ...values,
        rtv: selectedRTV.id,
        company: company.id,
      });
      message.success('Line added successfully');
      setLineModalVisible(false);
      loadRTVs();
    } catch (error) {
      message.error('Failed to add line');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForApproval = async (rtv) => {
    try {
      await rtvService.submitRTV(rtv.id);
      message.success('RTV submitted for approval');
      loadRTVs();
    } catch (error) {
      message.error('Failed to submit RTV');
    }
  };

  const handleApprove = async (rtv) => {
    try {
      await rtvService.approveRTV(rtv.id);
      message.success('RTV approved and negative movement events created');
      loadRTVs();
    } catch (error) {
      message.error('Failed to approve RTV');
    }
  };

  const handleOpenShipping = (rtv) => {
    setSelectedRTV(rtv);
    shippingForm.setFieldsValue({
      pickup_date: dayjs(),
    });
    setShippingModalVisible(true);
  };

  const handleSubmitShipping = async (values) => {
    setLoading(true);
    try {
      await rtvService.updateShipping(selectedRTV.id, {
        ...values,
        pickup_date: values.pickup_date.format('YYYY-MM-DD'),
        expected_delivery_date: values.expected_delivery_date
          ? values.expected_delivery_date.format('YYYY-MM-DD')
          : null,
      });
      message.success('Shipping information updated');
      setShippingModalVisible(false);
      loadRTVs();
    } catch (error) {
      message.error('Failed to update shipping information');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenComplete = (rtv) => {
    setSelectedRTV(rtv);
    completeForm.resetFields();
    setCompleteModalVisible(true);
  };

  const handleComplete = async (values) => {
    setLoading(true);
    try {
      await rtvService.completeRTV(selectedRTV.id, {
        ...values,
        debit_note_date: values.debit_note_date
          ? values.debit_note_date.format('YYYY-MM-DD')
          : null,
        actual_delivery_date: values.actual_delivery_date
          ? values.actual_delivery_date.format('YYYY-MM-DD')
          : null,
      });
      message.success('RTV completed and budget reversed');
      setCompleteModalVisible(false);
      loadRTVs();
    } catch (error) {
      message.error('Failed to complete RTV');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleView = async (rtv) => {
    setSelectedRTV(rtv);
    setLoading(true);
    try {
      const response = await rtvService.fetchRTVLines(rtv.id);
      setRTVLines(response.data.results || response.data || []);
      setViewDrawerVisible(true);
    } catch (error) {
      message.error('Failed to load RTV details');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (rtv) => {
    Modal.confirm({
      title: 'Cancel RTV',
      content: 'Are you sure you want to cancel this RTV? This action cannot be undone.',
      onOk: async () => {
        try {
          await rtvService.cancelRTV(rtv.id, 'Cancelled by user');
          message.success('RTV cancelled');
          loadRTVs();
        } catch (error) {
          message.error('Failed to cancel RTV');
        }
      },
    });
  };

  const getStatusColor = (status) => {
    return rtvService.getStatusColor(status);
  };

  const getCurrentStep = (status) => {
    const steps = {
      DRAFT: 0,
      SUBMITTED: 1,
      APPROVED: 2,
      IN_TRANSIT: 3,
      COMPLETED: 4,
      CANCELLED: -1,
    };
    return steps[status] || 0;
  };

  const columns = [
    {
      title: 'RTV #',
      dataIndex: 'rtv_number',
      key: 'rtv_number',
      fixed: 'left',
      width: 150,
    },
    {
      title: 'Date',
      dataIndex: 'rtv_date',
      key: 'rtv_date',
      width: 120,
      render: (text) => dayjs(text).format('MMM DD, YYYY'),
    },
    {
      title: 'GRN',
      dataIndex: 'goods_receipt_number',
      key: 'goods_receipt_number',
      width: 150,
    },
    {
      title: 'Supplier',
      dataIndex: 'supplier_name',
      key: 'supplier_name',
      ellipsis: true,
    },
    {
      title: 'Reason',
      dataIndex: 'reason_display',
      key: 'reason_display',
      width: 150,
    },
    {
      title: 'Return Value',
      dataIndex: 'total_return_value',
      key: 'total_return_value',
      width: 130,
      render: (value) => rtvService.formatAmount(value),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {rtvService.getStatusLabel(status)}
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
      width: 280,
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
          {rtvService.canEditRTV(record) && (
            <>
              <Tooltip title="Edit">
                <Button
                  type="link"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}
                />
              </Tooltip>
              <Tooltip title="Add Line">
                <Button
                  type="link"
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => handleAddLine(record)}
                />
              </Tooltip>
            </>
          )}
          {rtvService.canSubmitRTV(record) && (
            <Tooltip title="Submit">
              <Button
                type="link"
                size="small"
                icon={<SendOutlined />}
                onClick={() => handleSubmitForApproval(record)}
              />
            </Tooltip>
          )}
          {rtvService.canApproveRTV(record) && (
            <Tooltip title="Approve">
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
              />
            </Tooltip>
          )}
          {record.status === 'APPROVED' && (
            <Tooltip title="Update Shipping">
              <Button
                type="link"
                size="small"
                icon={<TruckOutlined />}
                onClick={() => handleOpenShipping(record)}
              />
            </Tooltip>
          )}
          {rtvService.canCompleteRTV(record) && (
            <Tooltip title="Complete">
              <Button
                type="link"
                size="small"
                icon={<DollarOutlined />}
                onClick={() => handleOpenComplete(record)}
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

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4}>Return To Vendor (RTV)</Title>
          <Button
            type="primary"
            icon={<UndoOutlined />}
            onClick={handleCreate}
          >
            New Return
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={rtvs}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1600 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} returns`,
          }}
        />
      </Card>

      {/* Create/Edit Form Modal */}
      <Modal
        title={selectedRTV ? 'Edit RTV' : 'Create New Return To Vendor'}
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
                name="rtv_date"
                label="RTV Date"
                rules={[{ required: true, message: 'Please select RTV date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="goods_receipt"
                label="Goods Receipt"
                rules={[{ required: true, message: 'Please select GRN' }]}
              >
                <Select
                  showSearch
                  placeholder="Select GRN"
                  optionFilterProp="children"
                >
                  {goodsReceipts.map(grn => (
                    <Option key={grn.id} value={grn.id}>
                      {grn.grn_number} - {dayjs(grn.receipt_date).format('MMM DD, YYYY')}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="supplier_id"
                label="Supplier ID"
                rules={[{ required: true, message: 'Please enter supplier ID' }]}
              >
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="return_reason"
                label="Return Reason"
                rules={[{ required: true, message: 'Please select reason' }]}
              >
                <Select>
                  {Object.entries(rtvService.RETURN_REASON_LABELS).map(([key, label]) => (
                    <Option key={key} value={key}>{label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="refund_expected"
            label="Refund Expected"
            valuePropName="checked"
            initialValue={true}
          >
            <Select>
              <Option value={true}>Yes</Option>
              <Option value={false}>No</Option>
            </Select>
          </Form.Item>

          <Form.Item name="notes" label="Notes">
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                {selectedRTV ? 'Update' : 'Create'}
              </Button>
              <Button onClick={() => setFormModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Add Line Modal */}
      <Modal
        title="Add Return Line"
        open={lineModalVisible}
        onCancel={() => setLineModalVisible(false)}
        width={600}
        footer={null}
      >
        <Form
          form={lineForm}
          layout="vertical"
          onFinish={handleSubmitLine}
        >
          <Form.Item
            name="product"
            label="Product"
            rules={[{ required: true, message: 'Please select product' }]}
          >
            <Select
              showSearch
              placeholder="Select product"
              optionFilterProp="children"
            >
              {products.map(product => (
                <Option key={product.id} value={product.id}>
                  {product.code} - {product.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="quantity_to_return"
                label="Quantity"
                rules={[{ required: true, message: 'Please enter quantity' }]}
              >
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="uom"
                label="UOM"
                rules={[{ required: true, message: 'Please select UOM' }]}
              >
                <Select>
                  {uoms.map(uom => (
                    <Option key={uom.id} value={uom.id}>{uom.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="unit_cost"
            label="Unit Cost"
            rules={[{ required: true, message: 'Please enter unit cost' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={2}
              formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => value.replace(/\$\s?|(,*)/g, '')}
            />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} />
          </Form.Item>

          <Form.Item name="quality_notes" label="Quality Notes">
            <TextArea rows={2} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                Add Line
              </Button>
              <Button onClick={() => setLineModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Shipping Modal */}
      <Modal
        title="Update Shipping Information"
        open={shippingModalVisible}
        onCancel={() => setShippingModalVisible(false)}
        width={600}
        footer={null}
      >
        <Form
          form={shippingForm}
          layout="vertical"
          onFinish={handleSubmitShipping}
        >
          <Form.Item
            name="carrier"
            label="Carrier"
            rules={[{ required: true, message: 'Please enter carrier' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="tracking_number"
            label="Tracking Number"
            rules={[{ required: true, message: 'Please enter tracking number' }]}
          >
            <Input />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="pickup_date"
                label="Pickup Date"
                rules={[{ required: true, message: 'Please select pickup date' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="expected_delivery_date" label="Expected Delivery">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                Update Shipping
              </Button>
              <Button onClick={() => setShippingModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Complete Modal */}
      <Modal
        title="Complete RTV"
        open={completeModalVisible}
        onCancel={() => setCompleteModalVisible(false)}
        width={600}
        footer={null}
      >
        <Alert
          message="Completing this RTV will reverse budget usage and post to GL"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form
          form={completeForm}
          layout="vertical"
          onFinish={handleComplete}
        >
          <Form.Item name="refund_amount" label="Refund Amount">
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={2}
              formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => value.replace(/\$\s?|(,*)/g, '')}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="debit_note_number" label="Debit Note #">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="debit_note_date" label="Debit Note Date">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="actual_delivery_date" label="Actual Delivery Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                Complete RTV
              </Button>
              <Button onClick={() => setCompleteModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* View Details Drawer */}
      <Drawer
        title="RTV Details"
        placement="right"
        width={720}
        onClose={() => setViewDrawerVisible(false)}
        open={viewDrawerVisible}
      >
        {selectedRTV && (
          <>
            <Steps current={getCurrentStep(selectedRTV.status)} size="small" style={{ marginBottom: 24 }}>
              <Step title="Draft" />
              <Step title="Submitted" />
              <Step title="Approved" />
              <Step title="In Transit" />
              <Step title="Completed" />
            </Steps>

            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="RTV Number" span={2}>
                {selectedRTV.rtv_number}
              </Descriptions.Item>
              <Descriptions.Item label="Date">
                {dayjs(selectedRTV.rtv_date).format('MMM DD, YYYY')}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={getStatusColor(selectedRTV.status)}>
                  {rtvService.getStatusLabel(selectedRTV.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="GRN">
                {selectedRTV.goods_receipt_number}
              </Descriptions.Item>
              <Descriptions.Item label="Supplier">
                {selectedRTV.supplier_name}
              </Descriptions.Item>
              <Descriptions.Item label="Return Reason" span={2}>
                {selectedRTV.reason_display}
              </Descriptions.Item>
              <Descriptions.Item label="Total Return Value" span={2}>
                {rtvService.formatAmount(selectedRTV.total_return_value)}
              </Descriptions.Item>
              {selectedRTV.refund_amount && (
                <Descriptions.Item label="Refund Amount" span={2}>
                  {rtvService.formatAmount(selectedRTV.refund_amount)}
                </Descriptions.Item>
              )}
              {selectedRTV.carrier && (
                <>
                  <Descriptions.Item label="Carrier">
                    {selectedRTV.carrier}
                  </Descriptions.Item>
                  <Descriptions.Item label="Tracking #">
                    {selectedRTV.tracking_number}
                  </Descriptions.Item>
                </>
              )}
              {selectedRTV.posted_to_gl && (
                <Descriptions.Item label="GL Journal Entry" span={2}>
                  JE #{selectedRTV.je_id} - Posted on {dayjs(selectedRTV.gl_posted_date).format('MMM DD, YYYY')}
                </Descriptions.Item>
              )}
            </Descriptions>

            {rtvLines.length > 0 && (
              <>
                <Divider>Return Lines</Divider>
                <Table
                  dataSource={rtvLines}
                  rowKey="id"
                  size="small"
                  pagination={false}
                  columns={[
                    {
                      title: 'Product',
                      dataIndex: 'product_name',
                      key: 'product_name',
                    },
                    {
                      title: 'Quantity',
                      dataIndex: 'quantity_to_return',
                      key: 'quantity_to_return',
                      render: (qty, record) => `${qty} ${record.uom_name}`,
                    },
                    {
                      title: 'Unit Cost',
                      dataIndex: 'unit_cost',
                      key: 'unit_cost',
                      render: (value) => rtvService.formatAmount(value),
                    },
                    {
                      title: 'Line Total',
                      dataIndex: 'line_total',
                      key: 'line_total',
                      render: (value) => rtvService.formatAmount(value),
                    },
                    {
                      title: 'Budget Reversed',
                      dataIndex: 'budget_reversed',
                      key: 'budget_reversed',
                      render: (reversed) => reversed ? (
                        <CheckOutlined style={{ color: '#52c41a' }} />
                      ) : (
                        <CloseOutlined style={{ color: '#ff4d4f' }} />
                      ),
                    },
                  ]}
                />
              </>
            )}

            {selectedRTV.notes && (
              <>
                <Divider>Notes</Divider>
                <Text>{selectedRTV.notes}</Text>
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default RTVManagement;
