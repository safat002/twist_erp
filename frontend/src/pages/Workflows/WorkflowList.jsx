import React, { useEffect, useMemo, useState } from 'react';
import { Card, Row, Col, Table, Space, Button, Tag, Typography, message, Modal, Form, Input } from 'antd';
import { PlusOutlined, CheckCircleOutlined, ArrowRightOutlined } from '@ant-design/icons';
import workflowService from '../../services/workflows';
import { useCompany } from '../../contexts/CompanyContext';

const { Title, Text } = Typography;

export default function WorkflowList() {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [instances, setInstances] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();

  const loadAll = async () => {
    setLoading(true);
    try {
      const [tpls, insts] = await Promise.all([
        workflowService.listTemplates(),
        workflowService.listInstances(),
      ]);
      setTemplates(tpls);
      setInstances(insts);
    } catch (err) {
      console.error(err);
      message.error('Failed to load workflows');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentCompany) loadAll();
  }, [currentCompany]);

  const templateColumns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Scope', dataIndex: 'scope_type', key: 'scope_type', render: v => <Tag color='blue'>{v}</Tag> },
    { title: 'Status', dataIndex: 'status', key: 'status', render: v => <Tag color={v === 'active' ? 'green' : 'default'}>{v}</Tag> },
    { title: 'Version', dataIndex: 'version', key: 'version', width: 100 },
  ];

  const instanceColumns = [
    { title: 'Template', dataIndex: ['template', 'name'], key: 'template' },
    { title: 'State', dataIndex: 'state', key: 'state', render: v => <Tag color={v === 'approved' ? 'green' : 'orange'}>{v}</Tag> },
    { title: 'Updated', dataIndex: 'updated_at', key: 'updated_at' },
    { title: 'Actions', key: 'actions', render: (_, record) => (
      <Space>
        <Button size='small' icon={<ArrowRightOutlined />} onClick={() => doTransition(record, 'submitted')} disabled={loading}>Submit</Button>
        <Button size='small' icon={<CheckCircleOutlined />} onClick={() => doApprove(record)} type='primary' disabled={loading}>Approve</Button>
      </Space>
    ) },
  ];

  const doTransition = async (instance, to) => {
    try {
      await workflowService.transitionInstance(instance.id, to);
      message.success('State updated');
      loadAll();
    } catch (err) {
      console.error(err);
      message.error('Failed to transition');
    }
  };

  const doApprove = async (instance) => {
    try {
      await workflowService.approveInstance(instance.id);
      message.success('Approved');
      loadAll();
    } catch (err) {
      console.error(err);
      message.error('Failed to approve');
    }
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await workflowService.createInstance({ template: values.template_id, state: values.state || 'draft', context: {} });
      setCreateOpen(false);
      form.resetFields();
      loadAll();
      message.success('Instance created');
    } catch (err) {
      if (err?.errorFields) return; // form errors
      console.error(err);
      message.error('Failed to create instance');
    }
  };

  return (
    <div>
      <Row justify='space-between' align='middle' style={{ marginBottom: 16 }}>
        <Col>
          <Title level={2} style={{ marginBottom: 0 }}>Workflow Studio</Title>
          <Text type='secondary'>Templates and Instances</Text>
        </Col>
        <Col>
          <Space>
            <Button icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>New Instance</Button>
          </Space>
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title='Templates' loading={loading}>
            <Table columns={templateColumns} dataSource={templates} rowKey='id' size='small' pagination={{ pageSize: 5 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title='Instances' loading={loading}>
            <Table columns={instanceColumns} dataSource={instances} rowKey='id' size='small' pagination={{ pageSize: 5 }} />
          </Card>
        </Col>
      </Row>

      <Modal open={createOpen} title='Create Workflow Instance' onOk={handleCreate} onCancel={() => setCreateOpen(false)} okText='Create'>
        <Form form={form} layout='vertical'>
          <Form.Item name='template_id' label='Template' rules={[{ required: true, message: 'Select a template' }]}>
            <Input placeholder='Enter Template ID' />
          </Form.Item>
          <Form.Item name='state' label='Initial State' initialValue='draft'>
            <Input placeholder='draft / submitted / approved' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
