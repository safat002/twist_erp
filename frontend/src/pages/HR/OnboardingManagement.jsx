import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, Input, Select, DatePicker, message, Space, Checkbox, Timeline } from 'antd';
import { PlusOutlined, EditOutlined, CheckCircleOutlined, UserOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const OnboardingManagement = () => {
  const [checklistItems, setChecklistItems] = useState([]);
  const [employeeOnboardingRecords, setEmployeeOnboardingRecords] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isChecklistItemModalVisible, setIsChecklistItemModalVisible] = useState(false);
  const [isEmployeeOnboardingModalVisible, setIsEmployeeOnboardingModalVisible] = useState(false);

  const [checklistItemForm] = Form.useForm();
  const [employeeOnboardingForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [checklistRes, onboardingRes] = await Promise.all([
        api.get('/api/v1/hr/onboarding-checklist-items/'),
        api.get('/api/v1/hr/employee-onboarding/'),
      ]);
      setChecklistItems(checklistRes.data);
      setEmployeeOnboardingRecords(onboardingRes.data);
    } catch (error) {
      message.error('Failed to load onboarding data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Checklist Item Handlers
  const showChecklistItemModal = () => setIsChecklistItemModalVisible(true);
  const handleChecklistItemCancel = () => {
    setIsChecklistItemModalVisible(false);
    checklistItemForm.resetFields();
  };
  const handleChecklistItemSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/onboarding-checklist-items/', values);
      message.success('Checklist item added successfully!');
      handleChecklistItemCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to add checklist item.');
    }
  };

  // Employee Onboarding Handlers
  const showEmployeeOnboardingModal = () => setIsEmployeeOnboardingModalVisible(true);
  const handleEmployeeOnboardingCancel = () => {
    setIsEmployeeOnboardingModalVisible(false);
    employeeOnboardingForm.resetFields();
  };
  const handleEmployeeOnboardingSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/employee-onboarding/', values);
      message.success('Employee onboarding record created successfully!');
      handleEmployeeOnboardingCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to create employee onboarding record.');
    }
  };

  const handleTaskComplete = async (taskId) => {
    try {
      await api.post(`/api/v1/hr/onboarding-tasks/${taskId}/complete/`);
      message.success('Task marked as complete!');
      fetchData();
    } catch (error) {
      message.error('Failed to complete task.');
    }
  };

  const checklistItemsColumns = [
    { title: 'Title', dataIndex: 'title', key: 'title' },
    { title: 'Category', dataIndex: 'category', key: 'category' },
    { title: 'Responsible Dept.', dataIndex: 'responsible_department', key: 'responsible_department' }, // TODO: Resolve department name
    { title: 'Due Days (from joining)', dataIndex: 'due_days_from_joining', key: 'due_days_from_joining' },
    { title: 'Mandatory', dataIndex: 'is_mandatory', key: 'is_mandatory', render: (text) => (text ? <Tag color="green">Yes</Tag> : <Tag>No</Tag>) },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  const employeeOnboardingColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (text) => <Tag color={text === 'COMPLETED' ? 'green' : 'blue'}>{text}</Tag> },
    { title: 'Buddy', dataIndex: 'buddy_name', key: 'buddy_name' },
    { title: 'Probation End', dataIndex: 'probation_end_date', key: 'probation_end_date' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} size="small">View/Edit</Button>
          <Button icon={<CheckCircleOutlined />} size="small">Mark Complete</Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Onboarding Management</Title>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="Checklist Items" key="1">
            <Button type="primary" icon={<PlusOutlined />} onClick={showChecklistItemModal} style={{ marginBottom: 16 }}>
              Add Checklist Item
            </Button>
            <Table columns={checklistItemsColumns} dataSource={checklistItems} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Employee Onboarding" key="2">
            <Button type="primary" icon={<PlusOutlined />} onClick={showEmployeeOnboardingModal} style={{ marginBottom: 16 }}>
              Create Onboarding Record
            </Button>
            <Table columns={employeeOnboardingColumns} dataSource={employeeOnboardingRecords} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      {/* Checklist Item Modal */}
      <Modal title="Add Onboarding Checklist Item" visible={isChecklistItemModalVisible} onCancel={handleChecklistItemCancel} footer={null}>
        <Form form={checklistItemForm} layout="vertical" onFinish={handleChecklistItemSubmit}>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <TextArea rows={2} />
          </Form.Item>
          <Form.Item name="category" label="Category" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="DOCUMENTATION">Documentation</Select.Option>
              <Select.Option value="IT_SETUP">IT Setup</Select.Option>
              <Select.Option value="HR_ORIENTATION">HR Orientation</Select.Option>
              <Select.Option value="TRAINING">Training</Select.Option>
              <Select.Option value="INTRODUCTION">Team Introduction</Select.Option>
              <Select.Option value="OTHER">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="responsible_department" label="Responsible Department"> {/* TODO: Replace with Select for Departments */}
            <Input />
          </Form.Item>
          <Form.Item name="due_days_from_joining" label="Due Days (from joining)" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_mandatory" valuePropName="checked">
            <Checkbox>Is Mandatory</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Add Item</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Employee Onboarding Modal */}
      <Modal title="Create Employee Onboarding Record" visible={isEmployeeOnboardingModalVisible} onCancel={handleEmployeeOnboardingCancel} footer={null}>
        <Form form={employeeOnboardingForm} layout="vertical" onFinish={handleEmployeeOnboardingSubmit}>
          <Form.Item name="employee" label="Employee" rules={[{ required: true }]}> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="buddy" label="Buddy"> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="probation_end_date" label="Probation End Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Create Record</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default OnboardingManagement;
