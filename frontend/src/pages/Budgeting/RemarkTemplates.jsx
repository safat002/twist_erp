import React, { useCallback, useEffect, useState } from 'react';
import { Button, Card, Form, Input, Modal, Space, Table, Tag, message } from 'antd';
import { fetchRemarkTemplates, createRemarkTemplate, updateRemarkTemplate, deleteRemarkTemplate } from '../../services/budget';

const RemarkTemplates = () => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await fetchRemarkTemplates();
      setRows(data?.results || data || []);
    } catch (e) {
      message.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const columns = [
    { title: 'Name', dataIndex: 'name' },
    { title: 'Type', dataIndex: 'template_type', render: (v) => <Tag>{v || 'custom'}</Tag> },
    { title: 'Usage', dataIndex: 'usage_count' },
    { title: 'Shared', dataIndex: 'is_shared', render: (v) => (v ? <Tag color="green">Shared</Tag> : <Tag>Private</Tag>) },
    {
      title: 'Actions',
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => { form.resetFields(); form.setFieldsValue(r); setOpen(true); }}>Edit</Button>
          <Button size="small" danger onClick={async () => { try { await deleteRemarkTemplate(r.id); message.success('Deleted'); load(); } catch (e) { message.error('Failed'); } }}>Delete</Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <h3 style={{ margin: 0 }}>Remark Templates</h3>
        <Button type="primary" onClick={() => { form.resetFields(); form.setFieldsValue({ is_shared: true }); setOpen(true); }}>New Template</Button>
      </Space>
      <Card>
        <Table rowKey="id" loading={loading} dataSource={rows} columns={columns} />
      </Card>
      <Modal
        title={form.getFieldValue('id') ? 'Edit Template' : 'New Template'}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={async () => {
          try {
            const v = await form.validateFields();
            const payload = { name: v.name, template_text: v.template_text, is_shared: !!v.is_shared };
            if (v.id) await updateRemarkTemplate(v.id, payload); else await createRemarkTemplate(payload);
            setOpen(false);
            message.success('Saved');
            load();
          } catch (e) {
            if (e?.errorFields) return; message.error('Failed to save');
          }
        }}
      >
        <Form layout="vertical" form={form}>
          <Form.Item name="id" hidden><Input type="hidden" /></Form.Item>
          <Form.Item label="Name" name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Text" name="template_text" rules={[{ required: true }]}><Input.TextArea rows={4} /></Form.Item>
          <Form.Item name="is_shared" valuePropName="checked" initialValue={true} label="Shared"><Input type="checkbox" /></Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

export default RemarkTemplates;

