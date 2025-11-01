import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, Input, Select, DatePicker, InputNumber, message, Space } from 'antd';
import { PlusOutlined, EditOutlined, UserDeleteOutlined, FileTextOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const ExitManagement = () => {
  const [employeeExits, setEmployeeExits] = useState([]);
  const [disciplinaryActions, setDisciplinaryActions] = useState([]);
  const [clearanceChecklists, setClearanceChecklists] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isExitModalVisible, setIsExitModalVisible] = useState(false);
  const [isDisciplinaryModalVisible, setIsDisciplinaryModalVisible] = useState(false);
  const [isClearanceChecklistModalVisible, setIsClearanceChecklistModalVisible] = useState(false);

  const [exitForm] = Form.useForm();
  const [disciplinaryForm] = Form.useForm();
  const [clearanceChecklistForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [exitsRes, disciplinaryRes, checklistsRes] = await Promise.all([
        api.get('/api/v1/hr/employee-exits/'),
        api.get('/api/v1/hr/disciplinary-actions/'),
        api.get('/api/v1/hr/clearance-checklists/'),
      ]);
      setEmployeeExits(exitsRes.data);
      setDisciplinaryActions(disciplinaryRes.data);
      setClearanceChecklists(checklistsRes.data);
    } catch (error) {
      message.error('Failed to load exit and disciplinary data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Employee Exit Handlers
  const showExitModal = () => setIsExitModalVisible(true);
  const handleExitCancel = () => {
    setIsExitModalVisible(false);
    exitForm.resetFields();
  };
  const handleExitSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/employee-exits/', values);
      message.success('Employee exit record created successfully!');
      handleExitCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to create employee exit record.');
    }
  };

  // Disciplinary Action Handlers
  const showDisciplinaryModal = () => setIsDisciplinaryModalVisible(true);
  const handleDisciplinaryCancel = () => {
    setIsDisciplinaryModalVisible(false);
    disciplinaryForm.resetFields();
  };
  const handleDisciplinarySubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/disciplinary-actions/', values);
      message.success('Disciplinary action recorded successfully!');
      handleDisciplinaryCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to record disciplinary action.');
    }
  };

  // Clearance Checklist Handlers
  const showClearanceChecklistModal = () => setIsClearanceChecklistModalVisible(true);
  const handleClearanceChecklistCancel = () => {
    setIsClearanceChecklistModalVisible(false);
    clearanceChecklistForm.resetFields();
  };
  const handleClearanceChecklistSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/clearance-checklists/', values);
      message.success('Clearance checklist item added successfully!');
      handleClearanceChecklistCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to add clearance checklist item.');
    }
  };

  const getStatusTag = (status) => {
    let color;
    switch (status) {
      case 'INITIATED':
      case 'DRAFT': return 'blue';
      case 'NOTICE_PERIOD':
      case 'SUBMITTED': return 'gold';
      case 'CLEARANCE':
      case 'APPROVED': return 'cyan';
      case 'COMPLETED':
      case 'PAID': return 'green';
      case 'TERMINATION':
      case 'REJECTED': return 'red';
      default: return 'default';
    }
    return <Tag color={color}>{status}</Tag>;
  };

  const employeeExitsColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Exit Reason', dataIndex: 'exit_reason', key: 'exit_reason' },
    { title: 'Last Working Date', dataIndex: 'last_working_date', key: 'last_working_date' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Initiated By', dataIndex: 'initiated_by_name', key: 'initiated_by_name' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} size="small">View Details</Button>
          <Button icon={<FileTextOutlined />} size="small">Exit Interview</Button>
        </Space>
      ),
    },
  ];

  const disciplinaryActionsColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Action Type', dataIndex: 'action_type', key: 'action_type' },
    { title: 'Violation Date', dataIndex: 'violation_date', key: 'violation_date' },
    { title: 'Action Date', dataIndex: 'action_date', key: 'action_date' },
    { title: 'Issued By', dataIndex: 'issued_by_name', key: 'issued_by_name' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">View Details</Button>
      ),
    },
  ];

  const clearanceChecklistsColumns = [
    { title: 'Title', dataIndex: 'title', key: 'title' },
    { title: 'Responsible Dept.', dataIndex: 'responsible_department', key: 'responsible_department' }, // TODO: Resolve department name
    { title: 'Mandatory', dataIndex: 'is_mandatory', key: 'is_mandatory', render: (text) => (text ? <Tag color="green">Yes</Tag> : <Tag>No</Tag>) },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Disciplinary & Exit Management</Title>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="Employee Exits" key="1">
            <Button type="primary" icon={<UserDeleteOutlined />} onClick={showExitModal} style={{ marginBottom: 16 }}>
              Initiate Employee Exit
            </Button>
            <Table columns={employeeExitsColumns} dataSource={employeeExits} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Disciplinary Actions" key="2">
            <Button type="primary" icon={<PlusOutlined />} onClick={showDisciplinaryModal} style={{ marginBottom: 16 }}>
              Record Disciplinary Action
            </Button>
            <Table columns={disciplinaryActionsColumns} dataSource={disciplinaryActions} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Clearance Checklists" key="3">
            <Button type="primary" icon={<PlusOutlined />} onClick={showClearanceChecklistModal} style={{ marginBottom: 16 }}>
              Add Clearance Item
            </Button>
            <Table columns={clearanceChecklistsColumns} dataSource={clearanceChecklists} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      {/* Employee Exit Modal */}
      <Modal title="Initiate Employee Exit" visible={isExitModalVisible} onCancel={handleExitCancel} footer={null}>
        <Form form={exitForm} layout="vertical" onFinish={handleExitSubmit}>
          <Form.Item name="employee" label="Employee" rules={[{ required: true }]}> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="exit_reason" label="Exit Reason" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="RESIGNATION">Resignation</Select.Option>
              <Select.Option value="TERMINATION">Termination</Select.Option>
              <Select.Option value="RETIREMENT">Retirement</Select.Option>
              <Select.Option value="CONTRACT_END">Contract End</Select.Option>
              <Select.Option value="MUTUAL">Mutual Separation</Select.Option>
              <Select.Option value="OTHER">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="last_working_date" label="Last Working Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="rehire_eligible" valuePropName="checked">
            <Checkbox>Eligible for Rehire</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Initiate Exit</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Disciplinary Action Modal */}
      <Modal title="Record Disciplinary Action" visible={isDisciplinaryModalVisible} onCancel={handleDisciplinaryCancel} footer={null}>
        <Form form={disciplinaryForm} layout="vertical" onFinish={handleDisciplinarySubmit}>
          <Form.Item name="employee" label="Employee" rules={[{ required: true }]}> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="action_type" label="Action Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="VERBAL_WARNING">Verbal Warning</Select.Option>
              <Select.Option value="WRITTEN_WARNING">Written Warning</Select.Option>
              <Select.Option value="FINAL_WARNING">Final Warning</Select.Option>
              <Select.Option value="SUSPENSION">Suspension</Select.Option>
              <Select.Option value="TERMINATION">Termination</Select.Option>
              <Select.Option value="OTHER">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="violation_date" label="Violation Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="action_date" label="Action Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label="Description" rules={[{ required: true }]}>
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Record Action</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Clearance Checklist Modal */}
      <Modal title="Add Clearance Checklist Item" visible={isClearanceChecklistModalVisible} onCancel={handleClearanceChecklistCancel} footer={null}>
        <Form form={clearanceChecklistForm} layout="vertical" onFinish={handleClearanceChecklistSubmit}>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="responsible_department" label="Responsible Department"> {/* TODO: Replace with Select for Departments */}
            <Input />
          </Form.Item>
          <Form.Item name="is_mandatory" valuePropName="checked">
            <Checkbox>Is Mandatory</Checkbox>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Add Item</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ExitManagement;
