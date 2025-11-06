import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  message,
} from 'antd';
import { ClusterOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import api from '../../services/api';
import { createBOM, deleteBOM, fetchBOMs, updateBOM } from '../../services/production';

const BOMList = () => {
  const [loading, setLoading] = useState(false);
  const [boms, setBoms] = useState([]);
  const [products, setProducts] = useState([]);
  const [uoms, setUoms] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const loadLookups = async () => {
    try {
      const [{ data: productData }, { data: uomData }, { data: warehouseData }] = await Promise.all([
        api.get('/api/v1/inventory/products/', { params: { is_active: true, limit: 200 } }),
        api.get('/api/v1/inventory/units-of-measure/', { params: { limit: 200 } }).catch(() => ({ data: { results: [] } })),
        api.get('/api/v1/inventory/warehouses/', { params: { limit: 200 } }).catch(() => ({ data: { results: [] } })),
      ]);
      setProducts(Array.isArray(productData?.results) ? productData.results : []);
      setUoms(Array.isArray(uomData?.results) ? uomData.results : []);
      setWarehouses(Array.isArray(warehouseData?.results) ? warehouseData.results : []);
    } catch (error) {
      console.warn('Failed to load production lookups', error?.message);
      message.error('Unable to fetch product master data.');
    }
  };

  const loadBOMs = async () => {
    try {
      setLoading(true);
      const { data } = await fetchBOMs();
      setBoms(Array.isArray(data?.results) ? data.results : []);
    } catch (error) {
      console.warn('Failed to load BOMs', error?.message);
      message.error('Unable to load bills of material.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLookups();
    loadBOMs();
  }, []);

  const productOptions = useMemo(
    () => products.map((product) => ({ value: product.id, label: `${product.code} - ${product.name}` })),
    [products],
  );

  const uomOptions = useMemo(
    () => uoms.map((uom) => ({ value: uom.id, label: `${uom.short_name || uom.code}` })),
    [uoms],
  );

  const warehouseOptions = useMemo(
    () => warehouses.map((warehouse) => ({ value: warehouse.id, label: `${warehouse.code} - ${warehouse.name}` })),
    [warehouses],
  );

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({
      status: 'ACTIVE',
      components: [
        { component: undefined, quantity: 1, sequence: 1 },
      ],
    });
    setEditing(null);
    setModalVisible(true);
  };

  const openEdit = (record) => {
    setEditing(record);
    form.setFieldsValue({
      product: record.product,
      name: record.name,
      version: record.version,
      status: record.status,
      is_primary: record.is_primary,
      components: (record.components || []).map((component, index) => ({
        component: component.component,
        quantity: component.quantity,
        uom: component.uom,
        warehouse: component.warehouse,
        sequence: component.sequence || index + 1,
      })),
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    const payload = {
      ...values,
      components: (values.components || []).map((component, index) => ({
        ...component,
        sequence: component.sequence || index + 1,
      })),
    };
    try {
      if (editing) {
        await updateBOM(editing.id, payload);
        message.success('Bill of material updated.');
      } else {
        await createBOM(payload);
        message.success('Bill of material created.');
      }
      setModalVisible(false);
      loadBOMs();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to save BOM.');
    }
  };

  const handleDelete = (record) => {
    Modal.confirm({
      title: `Delete ${record.code}?`,
      content: 'Deleting a BOM cannot be undone.',
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteBOM(record.id);
          message.success('Bill of material deleted.');
          loadBOMs();
        } catch (error) {
          message.error(error?.response?.data?.detail || 'Unable to delete BOM.');
        }
      },
    });
  };

  const columns = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
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
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={status === 'ACTIVE' ? 'green' : status === 'ARCHIVED' ? 'red' : 'default'}>{status}</Tag>,
    },
    {
      title: 'Primary',
      dataIndex: 'is_primary',
      key: 'primary',
      render: (value) => <Tag color={value ? 'blue' : 'default'}>{value ? 'Yes' : 'No'}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openEdit(record)}>
            Edit
          </Button>
          <Button type="link" danger onClick={() => handleDelete(record)}>
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ justifyContent: 'space-between', width: '100%', marginBottom: 16 }}>
        <Space>
          <ClusterOutlined style={{ fontSize: 24 }} />
          <span style={{ fontSize: 18, fontWeight: 600 }}>Bills of Materials</span>
        </Space>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadBOMs} disabled={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            New BOM
          </Button>
        </Space>
      </Space>
      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          dataSource={boms}
          loading={loading}
          columns={columns}
          expandable={{ expandedRowRender: (record) => (
            <Table
              size="small"
              columns={[
                { title: 'Component', dataIndex: ['component_detail', 'code'], key: 'code', render: (_, row) => `${row.component_detail?.code || ''} - ${row.component_detail?.name || ''}` },
                { title: 'Quantity', dataIndex: 'quantity', key: 'quantity' },
                { title: 'UOM', dataIndex: 'uom', key: 'uom', render: (value) => uoms.find((uom) => uom.id === value)?.code || value },
                { title: 'Warehouse', dataIndex: 'warehouse', key: 'warehouse', render: (value) => warehouses.find((w) => w.id === value)?.code || '—' },
              ]}
              dataSource={record.components || []}
              pagination={false}
              rowKey="id"
            />
          )}}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      <Modal
        title={editing ? 'Edit Bill of Material' : 'Create Bill of Material'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={720}
        onOk={() => form.submit()}
      >
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item
            name="product"
            label="Finished Good"
            rules={[{ required: true, message: 'Select finished product' }]}
          >
            <Select showSearch optionFilterProp="label" options={productOptions} />
          </Form.Item>
          <Form.Item name="name" label="Name">
            <Input placeholder="Optional name" />
          </Form.Item>
          <Space size="large" style={{ width: '100%' }}>
            <Form.Item name="version" label="Version" style={{ flex: 1 }}>
              <Input placeholder="1.0" />
            </Form.Item>
            <Form.Item name="status" label="Status" style={{ flex: 1 }}>
              <Select
                options={[
                  { label: 'Draft', value: 'DRAFT' },
                  { label: 'Active', value: 'ACTIVE' },
                  { label: 'Archived', value: 'ARCHIVED' },
                ]}
              />
            </Form.Item>
            <Form.Item name="is_primary" label="Primary" style={{ flex: 1 }}>
              <Select options={[{ label: 'Yes', value: true }, { label: 'No', value: false }]} />
            </Form.Item>
          </Space>
          <Form.Item name="revision_notes" label="Revision Notes">
            <Input.TextArea rows={3} placeholder="Internal notes" />
          </Form.Item>

          <Form.List name="components">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...field }) => (
                  <Space key={key} align="baseline" wrap style={{ display: 'flex', marginBottom: 12 }}>
                    <Form.Item
                      {...field}
                      name={[name, 'component']}
                      rules={[{ required: true, message: 'Select component product' }]}
                    >
                      <Select
                        showSearch
                        placeholder="Component"
                        optionFilterProp="label"
                        options={productOptions}
                        style={{ width: 220 }}
                      />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'quantity']} rules={[{ required: true, message: 'Quantity required' }]}> 
                      <Input type="number" step="0.01" placeholder="Qty" style={{ width: 100 }} />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'uom']}>
                      <Select placeholder="UOM" options={uomOptions} style={{ width: 100 }} />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'warehouse']}>
                      <Select placeholder="Warehouse" options={warehouseOptions} style={{ width: 160 }} allowClear />
                    </Form.Item>
                    <Form.Item {...field} name={[name, 'scrap_percent']} initialValue={0}>
                      <Input type="number" step="0.01" placeholder="Scrap %" style={{ width: 100 }} />
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
        </Form>
      </Modal>
    </div>
  );
};

export default BOMList;
