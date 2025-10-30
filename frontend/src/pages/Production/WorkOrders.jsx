import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  message,
} from 'antd';
import { PlayCircleOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../../services/api';
import {
  completeWorkOrder,
  createWorkOrder,
  fetchBOMs,
  fetchWorkOrders,
  issueMaterials,
  recordProductionReceipt,
  releaseWorkOrder,
  startWorkOrder,
} from '../../services/production';

const WorkOrders = () => {
  const [loading, setLoading] = useState(false);
  const [workOrders, setWorkOrders] = useState([]);
  const [boms, setBoms] = useState([]);
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [issueModalVisible, setIssueModalVisible] = useState(false);
  const [receiptModalVisible, setReceiptModalVisible] = useState(false);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState(null);
  const [form] = Form.useForm();
  const [issueForm] = Form.useForm();
  const [receiptForm] = Form.useForm();

  const loadLookups = async () => {
    try {
      const [{ data: productData }, { data: warehouseData }, { data: bomData }] = await Promise.all([
        api.get('/api/v1/inventory/products/', { params: { is_active: true, limit: 200 } }),
        api.get('/api/v1/inventory/warehouses/', { params: { limit: 200 } }),
        fetchBOMs({ limit: 200 }),
      ]);
      setProducts(Array.isArray(productData?.results) ? productData.results : []);
      setWarehouses(Array.isArray(warehouseData?.results) ? warehouseData.results : []);
      setBoms(Array.isArray(bomData?.results) ? bomData.results : []);
    } catch (error) {
      console.warn('Failed to load work order lookups', error?.message);
      message.error('Unable to load BOMs or master data.');
    }
  };

  const loadWorkOrders = async () => {
    try {
      setLoading(true);
      const { data } = await fetchWorkOrders();
      setWorkOrders(Array.isArray(data?.results) ? data.results : []);
    } catch (error) {
      console.warn('Failed to load work orders', error?.message);
      message.error('Unable to load work orders.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLookups();
    loadWorkOrders();
  }, []);

  const productOptions = useMemo(
    () => products.map((product) => ({ value: product.id, label: `${product.code} - ${product.name}` })),
    [products],
  );

  const warehouseOptions = useMemo(
    () => warehouses.map((warehouse) => ({ value: warehouse.id, label: `${warehouse.code} - ${warehouse.name}` })),
    [warehouses],
  );

  const bomOptions = useMemo(
    () => boms.map((bom) => ({ value: bom.id, label: `${bom.code} - ${bom.name || ''}` })),
    [boms],
  );

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      scheduled_start: dayjs(),
      scheduled_end: dayjs().add(2, 'day'),
      priority: 'NORMAL',
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    const payload = {
      ...values,
      scheduled_start: values.scheduled_start?.format('YYYY-MM-DD'),
      scheduled_end: values.scheduled_end?.format('YYYY-MM-DD'),
    };
    try {
      await createWorkOrder(payload);
      message.success('Work order created.');
      setModalVisible(false);
      loadWorkOrders();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to create work order.');
    }
  };

  const handleRelease = async (record) => {
    try {
      await releaseWorkOrder(record.id);
      message.success('Work order released.');
      loadWorkOrders();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to release work order.');
    }
  };

  const handleStart = async (record) => {
    try {
      await startWorkOrder(record.id);
      message.success('Work order started.');
      loadWorkOrders();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to start work order.');
    }
  };

  const handleComplete = async (record) => {
    Modal.confirm({
      title: `Complete ${record.number}?`,
      content: 'Confirm quantity completed to close the work order.',
      onOk: async () => {
        try {
          await completeWorkOrder(record.id, { quantity_completed: record.quantity_planned });
          message.success('Work order completed.');
          loadWorkOrders();
        } catch (error) {
          message.error(error?.response?.data?.detail || 'Unable to complete work order.');
        }
      },
    });
  };

  const openIssueModal = (record) => {
    setSelectedWorkOrder(record);
    issueForm.resetFields();
    issueForm.setFieldsValue({
      issue_date: dayjs(),
      lines: (record.components || []).map((component) => ({
        component: component.id,
        quantity: component.remaining_quantity,
        warehouse: component.preferred_warehouse,
      })),
    });
    setIssueModalVisible(true);
  };

  const handleIssueSubmit = async (values) => {
    try {
      await issueMaterials(selectedWorkOrder.id, {
        issue_date: values.issue_date?.format('YYYY-MM-DD'),
        lines: values.lines,
      });
      message.success('Material issue recorded.');
      setIssueModalVisible(false);
      loadWorkOrders();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to issue materials.');
    }
  };

  const openReceiptModal = (record) => {
    setSelectedWorkOrder(record);
    receiptForm.resetFields();
    receiptForm.setFieldsValue({
      receipt_date: dayjs(),
      quantity_good: record.quantity_planned,
      quantity_scrap: 0,
    });
    setReceiptModalVisible(true);
  };

  const handleReceiptSubmit = async (values) => {
    try {
      await recordProductionReceipt(selectedWorkOrder.id, {
        receipt_date: values.receipt_date?.format('YYYY-MM-DD'),
        quantity_good: values.quantity_good,
        quantity_scrap: values.quantity_scrap,
        notes: values.notes,
      });
      message.success('Production receipt recorded.');
      setReceiptModalVisible(false);
      loadWorkOrders();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to record receipt.');
    }
  };

  const columns = [
    {
      title: 'Number',
      dataIndex: 'number',
      key: 'number',
    },
    {
      title: 'Product',
      dataIndex: 'product',
      key: 'product',
      render: (value) => {
        const product = products.find((item) => item.id === value);
        return product ? `${product.code} - ${product.name}` : value;
      },
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity_planned',
      key: 'quantity',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag
          color={
            status === 'COMPLETED'
              ? 'green'
              : status === 'IN_PROGRESS'
                ? 'blue'
                : status === 'RELEASED'
                  ? 'purple'
                  : 'default'
          }
        >
          {status}
        </Tag>
      ),
    },
    {
      title: 'Planned Window',
      key: 'window',
      render: (_, record) => (
        <span>
          {record.scheduled_start || 'TBD'} → {record.scheduled_end || 'TBD'}
        </span>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space wrap>
          {record.status === 'PLANNED' && (
            <Button type="link" onClick={() => handleRelease(record)}>
              Release
            </Button>
          )}
          {record.status === 'RELEASED' && (
            <Button icon={<PlayCircleOutlined />} type="link" onClick={() => handleStart(record)}>
              Start
            </Button>
          )}
          {record.status === 'IN_PROGRESS' && (
            <Button type="link" onClick={() => handleComplete(record)}>
              Complete
            </Button>
          )}
          <Button type="link" onClick={() => openIssueModal(record)}>
            Issue Materials
          </Button>
          <Button type="link" onClick={() => openReceiptModal(record)}>
            Record Receipt
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ justifyContent: 'space-between', width: '100%', marginBottom: 16 }}>
        <Space>
          <ThunderboltOutlined style={{ fontSize: 24 }} />
          <span style={{ fontSize: 18, fontWeight: 600 }}>Work Orders</span>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          New Work Order
        </Button>
      </Space>
      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          dataSource={workOrders}
          loading={loading}
          columns={columns}
          expandable={{ expandedRowRender: (record) => (
            <Table
              dataSource={record.components || []}
              columns={[
                {
                  title: 'Component',
                  dataIndex: ['component_detail', 'code'],
                  key: 'component',
                  render: (_, item) => `${item.component_detail?.code || ''} - ${item.component_detail?.name || ''}`,
                },
                { title: 'Required', dataIndex: 'required_quantity', key: 'req' },
                { title: 'Issued', dataIndex: 'issued_quantity', key: 'issued' },
                { title: 'Remaining', dataIndex: 'remaining_quantity', key: 'remaining' },
              ]}
              pagination={false}
              rowKey="id"
              size="small"
            />
          )}}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      <Modal
        title="Create Work Order"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={720}
        onOk={() => form.submit()}
      >
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item name="product" label="Product" rules={[{ required: true, message: 'Select product' }]}> 
            <Select showSearch optionFilterProp="label" options={productOptions} />
          </Form.Item>
          <Form.Item name="bom" label="Bill of Material" rules={[{ required: true, message: 'Select BOM' }]}> 
            <Select showSearch optionFilterProp="label" options={bomOptions} />
          </Form.Item>
          <Form.Item name="quantity_planned" label="Planned Quantity" rules={[{ required: true, message: 'Enter quantity' }]}> 
            <Input type="number" min="0" step="0.01" />
          </Form.Item>
          <Space size="large" style={{ width: '100%' }}>
            <Form.Item name="scheduled_start" label="Scheduled Start" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="scheduled_end" label="Scheduled End" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Space size="large" style={{ width: '100%' }}>
            <Form.Item name="priority" label="Priority" style={{ flex: 1 }}>
              <Select
                options=[
                  { label: 'Low', value: 'LOW' },
                  { label: 'Normal', value: 'NORMAL' },
                  { label: 'High', value: 'HIGH' },
                  { label: 'Critical', value: 'CRITICAL' },
                ]
              />
            </Form.Item>
            <Form.Item name="warehouse" label="Production Warehouse" style={{ flex: 1 }}>
              <Select showSearch optionFilterProp="label" options={warehouseOptions} />
            </Form.Item>
          </Space>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} placeholder="Optional instructions" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={selectedWorkOrder ? `Issue Materials · ${selectedWorkOrder.number}` : 'Issue Materials'}
        open={issueModalVisible}
        onCancel={() => setIssueModalVisible(false)}
        destroyOnClose
        width={720}
        onOk={() => issueForm.submit()}
      >
        <Form layout="vertical" form={issueForm} onFinish={handleIssueSubmit}>
          <Form.Item name="issue_date" label="Issue Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...field }) => (
                  <Space key={key} align="baseline" wrap style={{ display: 'flex', marginBottom: 12 }}>
                    <Form.Item {...field} name={[name, 'component']} rules={[{ required: true, message: 'Component required' }]}> 
                      <Select
                        showSearch
                        placeholder="Component"
                        optionFilterProp="label"
                        options={(selectedWorkOrder?.components || []).map((component) => ({
                          value: component.id,
                          label: `${component.component_detail?.code || ''} - ${component.component_detail?.name || ''}`,
                        }))}
                        style={{ width: 260 }}
                      />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'quantity']} rules={[{ required: true, message: 'Enter quantity' }]}> 
                      <Input type="number" step="0.01" placeholder="Quantity" style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'warehouse']}>
                      <Select placeholder="Warehouse" options={warehouseOptions} style={{ width: 160 }} allowClear />
                    </Form.Item>
                    <Button type="link" danger onClick={() => remove(name)}>
                      Remove
                    </Button>
                  </Space>
                ))}
                <Button type="dashed" block icon={<PlusOutlined />} onClick={() => add()}>
                  Add Component
                </Button>
              </>
            )}
          </Form.List>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={2} placeholder="Optional notes" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={selectedWorkOrder ? `Record Receipt · ${selectedWorkOrder.number}` : 'Record Receipt'}
        open={receiptModalVisible}
        onCancel={() => setReceiptModalVisible(false)}
        destroyOnClose
        width={520}
        onOk={() => receiptForm.submit()}
      >
        <Form layout="vertical" form={receiptForm} onFinish={handleReceiptSubmit}>
          <Form.Item name="receipt_date" label="Receipt Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="quantity_good" label="Good Quantity" rules={[{ required: true, message: 'Enter good quantity' }]}>
            <Input type="number" step="0.01" />
          </Form.Item>
          <Form.Item name="quantity_scrap" label="Scrap Quantity">
            <Input type="number" step="0.01" />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={2} placeholder="Optional notes" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WorkOrders;
