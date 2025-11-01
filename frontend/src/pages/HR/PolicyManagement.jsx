import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, Input, Select, DatePicker, message, Space, Checkbox } from 'antd';
import { PlusOutlined, EditOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const PolicyManagement = () => {
  const [policyDocuments, setPolicyDocuments] = useState([]);
  const [policyAcknowledgments, setPolicyAcknowledgments] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isPolicyDocModalVisible, setIsPolicyDocModalVisible] = useState(false);
  const [isPolicyAckModalVisible, setIsPolicyAckModalVisible] = useState(false);

  const [policyDocForm] = Form.useForm();
  const [policyAckForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [docsRes, acksRes] = await Promise.all([
        api.get('/api/v1/hr/policy-documents/'),
        api.get('/api/v1/hr/policy-acknowledgments/'),
      ]);
      setPolicyDocuments(docsRes.data);
      setPolicyAcknowledgments(acksRes.data);
    } catch (error) {
      message.error('Failed to load policy data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Policy Document Handlers
  const showPolicyDocModal = () => setIsPolicyDocModalVisible(true);
  const handlePolicyDocCancel = () => {
    setIsPolicyDocModalVisible(false);
    policyDocForm.resetFields();
  };
  const handlePolicyDocSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/policy-documents/', values);
      message.success('Policy document added successfully!');
      handlePolicyDocCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to add policy document.');
    }
  };

  // Policy Acknowledgment Handlers
  const showPolicyAckModal = () => setIsPolicyAckModalVisible(true);
  const handlePolicyAckCancel = () => {
    setIsPolicyAckModalVisible(false);
    policyAckForm.resetFields();
  };
  const handlePolicyAckSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/policy-acknowledgments/', values);
      message.success('Policy acknowledgment recorded successfully!');
      handlePolicyAckCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to record policy acknowledgment.');
    }
  };

  const policyDocumentsColumns = [
    { title: 'Title', dataIndex: 'title', key: 'title' },
    { title: 'Category', dataIndex: 'category', key: 'category' },
    { title: 'Version', dataIndex: 'version', key: 'version' },
    { title: 'Effective Date', dataIndex: 'effective_date', key: 'effective_date' },
    { title: 'Owner', dataIndex: 'owner_name', key: 'owner_name' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  const policyAcknowledgmentsColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Policy', dataIndex: 'policy_title', key: 'policy_title' },
    { title: 'Acknowledged At', dataIndex: 'acknowledged_at', key: 'acknowledged_at' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<FileTextOutlined />} size="small">View Details</Button>
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Policy Management & Acknowledgment</Title>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="Policy Documents" key="1">
            <Button type="primary" icon={<PlusOutlined />} onClick={showPolicyDocModal} style={{ marginBottom: 16 }}>
              Add Policy Document
            </Button>
            <Table columns={policyDocumentsColumns} dataSource={policyDocuments} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Policy Acknowledgments" key="2">
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={showPolicyAckModal} style={{ marginBottom: 16 }}>
              Record Acknowledgment
            </Button>
            <Table columns={policyAcknowledgmentsColumns} dataSource={policyAcknowledgments} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      {/* Policy Document Modal */}
      <Modal title="Add Policy Document" visible={isPolicyDocModalVisible} onCancel={handlePolicyDocCancel} footer={null}>
        <Form form={policyDocForm} layout="vertical" onFinish={handlePolicyDocSubmit}>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="policy_code" label="Policy Code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="Category" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="LEAVE">Leave Policy</Select.Option>
              <Select.Option value="ATTENDANCE">Attendance Policy</Select.Option>
              <Select.Option value="OVERTIME">Overtime Policy</Select.Option>
              <Select.Option value="WFH">Work from Home</Select.Option>
              <Select.Option value="CODE_OF_CONDUCT">Code of Conduct</Select.Option>
              <Select.Option value="OTHER">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="document_url" label="Document URL" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="effective_date" label="Effective Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="requires_acknowledgment" valuePropName="checked">
            <Checkbox>Requires Acknowledgment</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Add Policy</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Policy Acknowledgment Modal */}
      <Modal title="Record Policy Acknowledgment" visible={isPolicyAckModalVisible} onCancel={handlePolicyAckCancel} footer={null}>
        <Form form={policyAckForm} layout="vertical" onFinish={handlePolicyAckSubmit}>
          <Form.Item name="employee" label="Employee" rules={[{ required: true }]}> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="policy" label="Policy Document" rules={[{ required: true }]}>
            <Select options={policyDocuments.map(doc => ({ label: doc.title, value: doc.id }))} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Record Acknowledgment</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default PolicyManagement;
