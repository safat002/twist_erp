import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, DatePicker, Select, Switch, Upload, Space, Tag, Drawer } from 'antd';
import { App as AntApp } from 'antd';
import { PlusOutlined, UploadOutlined, CheckCircleTwoTone } from '@ant-design/icons';
import api from '../../services/api';

const fallbackCategoryOptions = [
  { label: 'HR', value: 'hr' },
  { label: 'Finance', value: 'finance' },
  { label: 'Operations', value: 'operations' },
  { label: 'Quality', value: 'quality' },
  { label: 'Compliance', value: 'compliance' },
  { label: 'Safety', value: 'safety' },
  { label: 'IT', value: 'it' },
];

const PoliciesList = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const { message } = AntApp.useApp();
  const [categories, setCategories] = useState([]);
  const [categoriesRaw, setCategoriesRaw] = useState([]);
  const [viewOpen, setViewOpen] = useState(false);
  const [viewRecord, setViewRecord] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const [polRes, catRes] = await Promise.all([
        api.get('/api/v1/policies/policies/'),
        api.get('/api/v1/policies/categories/').catch(() => ({ data: [] })),
      ]);
      const list = Array.isArray(polRes.data) ? polRes.data : polRes.data?.results || [];
      setData(list);
      const cats = Array.isArray(catRes.data) ? catRes.data : catRes.data?.results || [];
      setCategoriesRaw(cats);
      setCategories(cats.map((c) => ({ label: c.name, value: c.code })));
    } catch (e) {
      message.error('Failed to load policies');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const fd = new FormData();
      fd.append('title', values.title);
      fd.append('category', values.category);
      const selected = categoriesRaw.find((c) => c.code === values.category);
      if (selected) fd.append('category_ref', selected.id);
      if (values.effective_date) fd.append('effective_date', values.effective_date.format('YYYY-MM-DD'));
      if (values.expiry_date) fd.append('expiry_date', values.expiry_date.format('YYYY-MM-DD'));
      fd.append('requires_acknowledgement', values.requires_acknowledgement ? 'true' : 'false');
      if (values.description) fd.append('description', values.description);
      if (values.content) fd.append('content', values.content);
      if (values.file && values.file.file) fd.append('file', values.file.file);
      if (Array.isArray(values.compliance_links)) fd.append('compliance_links', JSON.stringify(values.compliance_links));
      await api.post('/api/v1/policies/policies/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      message.success('Policy created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail || 'Could not create policy');
    } finally {
      setSaving(false);
    }
  };

  const ack = async (id) => {
    try {
      await api.post(`/api/v1/policies/policies/${id}/acknowledge/`);
      message.success('Acknowledged');
      load();
    } catch (e) {
      message.error('Failed to acknowledge');
    }
  };

  const publish = async (id) => {
    try {
      await api.post(`/api/v1/policies/policies/${id}/publish/`);
      message.success('Published');
      load();
    } catch (e) {
      message.error('Failed to publish');
    }
  };

  const view = (record) => {
    setViewRecord(record);
    setViewOpen(true);
  };

  const showHistory = async (id) => {
    try {
      const { data } = await api.get(`/api/v1/policies/policies/${id}/versions/`);
      const list = Array.isArray(data) ? data : data?.results || [];
      setHistory(list);
      setHistoryOpen(true);
    } catch (e) {
      message.error('Failed to load history');
    }
  };

  const columns = useMemo(
    () => [
      { title: 'Code', dataIndex: 'code', key: 'code' },
      { title: 'Title', dataIndex: 'title', key: 'title' },
      { title: 'Category', dataIndex: 'category', key: 'category', render: (v) => <Tag>{v}</Tag> },
      { title: 'Version', dataIndex: 'version', key: 'version' },
      { title: 'Status', dataIndex: 'status', key: 'status', render: (v) => <Tag color={v === 'active' ? 'green' : v === 'draft' ? 'gold' : 'default'}>{v.toUpperCase()}</Tag> },
      { title: 'Effective', dataIndex: 'effective_date', key: 'effective_date' },
      { title: 'Expiry', dataIndex: 'expiry_date', key: 'expiry_date' },
      {
        title: 'Ack Required',
        dataIndex: 'requires_acknowledgement',
        key: 'requires_acknowledgement',
        render: (v) => (v ? <CheckCircleTwoTone twoToneColor="#52c41a" /> : ''),
      },
      {
        title: 'Actions',
        key: 'actions',
        render: (_, record) => (
          <Space>
            <Button size="small" onClick={() => view(record)}>View</Button>
            <Button size="small" onClick={() => showHistory(record.id)}>History</Button>
            {record.status !== 'active' && (
              <Button size="small" onClick={() => publish(record.id)}>Publish</Button>
            )}
            {record.requires_acknowledgement && !record.acknowledged && record.status === 'active' && (
              <Button size="small" type="primary" onClick={() => ack(record.id)}>Acknowledge</Button>
            )}
          </Space>
        ),
      },
    ],
    [],
  );

  return (
    <Card
      title="Policies & SOPs"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>New Policy</Button>}
    >
      <Table columns={columns} dataSource={data} loading={loading} rowKey="id" pagination={{ pageSize: 10 }} />

      <Modal title="Create Policy" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} confirmLoading={saving} okText="Create">
        <Form layout="vertical" form={form} initialValues={{ category: 'operations', requires_acknowledgement: false }}>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="Category" rules={[{ required: true }]}>
            <Select options={categories.length ? categories : fallbackCategoryOptions} />
          </Form.Item>
          <Form.Item name="effective_date" label="Effective Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="expiry_date" label="Expiry Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="requires_acknowledgement" label="Require Acknowledgement" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.List name="compliance_links">
            {(fields, { add, remove }) => (
              <Card size="small" title="Compliance Links" extra={<Button size="small" onClick={() => add()}>Add</Button>} style={{ marginBottom: 12 }}>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item {...restField} name={[name, 'label']} rules={[{ required: true }]}>
                      <Input placeholder="Label" />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'url']} rules={[{ type: 'url', required: true }]}>
                      <Input placeholder="https://..." />
                    </Form.Item>
                    <Button danger onClick={() => remove(name)}>Remove</Button>
                  </Space>
                ))}
              </Card>
            )}
          </Form.List>
          <Form.Item name="file" label="Upload File">
            <Upload beforeUpload={() => false} maxCount={1}>
              <Button icon={<UploadOutlined />}>Select File</Button>
            </Upload>
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="content" label="Content">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title={viewRecord?.title || 'Policy'} open={viewOpen} onClose={() => setViewOpen(false)} width={720} destroyOnClose>
        {viewRecord?.file ? (
          <iframe title="policy-file" src={viewRecord.file} style={{ width: '100%', height: '80vh', border: 0 }} />
        ) : (
          <Card size="small" title={`Code ${viewRecord?.code} · Version ${viewRecord?.version}`}>
            <p><strong>Description:</strong> {viewRecord?.description || '-'}</p>
            <div style={{ whiteSpace: 'pre-wrap' }}>{viewRecord?.content || 'No content'}</div>
          </Card>
        )}
      </Drawer>

      <Modal title="Version History" open={historyOpen} onCancel={() => setHistoryOpen(false)} footer={null} width={800}>
        <Table
          dataSource={history}
          rowKey="id"
          size="small"
          columns={[
            { title: 'Version', dataIndex: 'version' },
            { title: 'Status', dataIndex: 'status' },
            { title: 'Published', dataIndex: 'published_at' },
            { title: 'Effective', dataIndex: 'effective_date' },
          ]}
          pagination={false}
        />
      </Modal>
    </Card>
  );
};

export default PoliciesList;
