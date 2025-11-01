import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, DatePicker, Input, InputNumber, message, Space } from 'antd';
import { PlusOutlined, CheckCircleOutlined, CloseCircleOutlined, DollarOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const AdvancesLoansManagement = () => {
  const [myAdvances, setMyAdvances] = useState([]);
  const [myLoans, setMyLoans] = useState([]);
  const [teamAdvances, setTeamAdvances] = useState([]);
  const [teamLoans, setTeamLoans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isAdvanceModalVisible, setIsAdvanceModalVisible] = useState(false);
  const [isLoanModalVisible, setIsLoanModalVisible] = useState(false);
  const [advanceForm] = Form.useForm();
  const [loanForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [myAdvancesRes, myLoansRes, teamAdvancesRes, teamLoansRes] = await Promise.all([
        api.get('/api/v1/hr/salary-advances/'),
        api.get('/api/v1/hr/employee-loans/'),
        api.get('/api/v1/hr/salary-advances/?team=true'), // Assuming a team filter
        api.get('/api/v1/hr/employee-loans/?team=true'), // Assuming a team filter
      ]);
      setMyAdvances(myAdvancesRes.data);
      setMyLoans(myLoansRes.data);
      setTeamAdvances(teamAdvancesRes.data);
      setTeamLoans(teamLoansRes.data);
    } catch (error) {
      message.error('Failed to load advances and loans data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const showAdvanceModal = () => setIsAdvanceModalVisible(true);
  const handleAdvanceCancel = () => {
    setIsAdvanceModalVisible(false);
    advanceForm.resetFields();
  };

  const showLoanModal = () => setIsLoanModalVisible(true);
  const handleLoanCancel = () => {
    setIsLoanModalVisible(false);
    loanForm.resetFields();
  };

  const handleAdvanceSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/salary-advances/', values);
      message.success('Salary advance request submitted successfully!');
      handleAdvanceCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to submit salary advance request.');
    }
  };

  const handleLoanSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/employee-loans/', values);
      message.success('Employee loan request submitted successfully!');
      handleLoanCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to submit employee loan request.');
    }
  };

  const getStatusTag = (status) => {
    switch (status) {
      case 'REQUESTED':
      case 'PENDING': return <Tag color="gold">{status}</Tag>;
      case 'APPROVED':
      case 'ACTIVE':
      case 'DISBURSED': return <Tag color="green">{status}</Tag>;
      case 'REJECTED':
      case 'CLOSED':
      case 'RECOVERED': return <Tag color="blue">{status}</Tag>;
      default: return <Tag>{status}</Tag>;
    }
  };

  const myAdvancesColumns = [
    { title: 'Request Date', dataIndex: 'request_date', key: 'request_date' },
    { title: 'Amount', dataIndex: 'amount', key: 'amount' },
    { title: 'Reason', dataIndex: 'reason', key: 'reason' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
  ];

  const myLoansColumns = [
    { title: 'Loan Type', dataIndex: 'loan_type', key: 'loan_type' },
    { title: 'Principal', dataIndex: 'principal_amount', key: 'principal_amount' },
    { title: 'Installment', dataIndex: 'installment_amount', key: 'installment_amount' },
    { title: 'Total Installments', dataIndex: 'total_installments', key: 'total_installments' },
    { title: 'Paid Installments', dataIndex: 'paid_installments', key: 'paid_installments' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
  ];

  const teamAdvancesColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Request Date', dataIndex: 'request_date', key: 'request_date' },
    { title: 'Amount', dataIndex: 'amount', key: 'amount' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Action', key: 'action', render: (_, record) => (
        record.status === 'REQUESTED' && (
          <Space>
            <Button icon={<CheckCircleOutlined />} type="primary" size="small" onClick={() => message.info('Implement approve advance')}>Approve</Button>
            <Button icon={<CloseCircleOutlined />} type="primary" danger size="small" onClick={() => message.info('Implement reject advance')}>Reject</Button>
          </Space>
        )
      ),
    },
  ];

  const teamLoansColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Loan Type', dataIndex: 'loan_type', key: 'loan_type' },
    { title: 'Principal', dataIndex: 'principal_amount', key: 'principal_amount' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Action', key: 'action', render: (_, record) => (
        record.status === 'REQUESTED' && (
          <Space>
            <Button icon={<CheckCircleOutlined />} type="primary" size="small" onClick={() => message.info('Implement approve loan')}>Approve</Button>
            <Button icon={<CloseCircleOutlined />} type="primary" danger size="small" onClick={() => message.info('Implement reject loan')}>Reject</Button>
          </Space>
        )
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Employee Advances & Loans</Title>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="My Advances" key="1">
            <Button type="primary" icon={<PlusOutlined />} onClick={showAdvanceModal} style={{ marginBottom: 16 }}>
              Request Advance
            </Button>
            <Table columns={myAdvancesColumns} dataSource={myAdvances} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="My Loans" key="2">
            <Button type="primary" icon={<PlusOutlined />} onClick={showLoanModal} style={{ marginBottom: 16 }}>
              Request Loan
            </Button>
            <Table columns={myLoansColumns} dataSource={myLoans} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Team Advances" key="3">
            <Table columns={teamAdvancesColumns} dataSource={teamAdvances} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Team Loans" key="4">
            <Table columns={teamLoansColumns} dataSource={teamLoans} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      {/* Salary Advance Modal */}
      <Modal title="Request Salary Advance" visible={isAdvanceModalVisible} onCancel={handleAdvanceCancel} footer={null}>
        <Form form={advanceForm} layout="vertical" onFinish={handleAdvanceSubmit}>
          <Form.Item name="amount" label="Amount" rules={[{ required: true, message: 'Please enter amount' }]}>
            <InputNumber min={1} style={{ width: '100%' }} formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(/\$\s?|(,*)/g, '')} />
          </Form.Item>
          <Form.Item name="reason" label="Reason" rules={[{ required: true, message: 'Please enter reason' }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="request_date" label="Request Date" rules={[{ required: true, message: 'Please select date' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Submit Request</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Employee Loan Modal */}
      <Modal title="Request Employee Loan" visible={isLoanModalVisible} onCancel={handleLoanCancel} footer={null}>
        <Form form={loanForm} layout="vertical" onFinish={handleLoanSubmit}>
          <Form.Item name="loan_type" label="Loan Type" rules={[{ required: true, message: 'Please enter loan type' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="principal_amount" label="Principal Amount" rules={[{ required: true, message: 'Please enter principal amount' }]}>
            <InputNumber min={1} style={{ width: '100%' }} formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(/\$\s?|(,*)/g, '')} />
          </Form.Item>
          <Form.Item name="interest_rate" label="Interest Rate (%)" rules={[{ required: true, message: 'Please enter interest rate' }]}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="disbursement_date" label="Disbursement Date" rules={[{ required: true, message: 'Please select disbursement date' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="total_installments" label="Total Installments" rules={[{ required: true, message: 'Please enter total installments' }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="installment_amount" label="Installment Amount" rules={[{ required: true, message: 'Please enter installment amount' }]}>
            <InputNumber min={1} style={{ width: '100%' }} formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(/\$\s?|(,*)/g, '')} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Submit Request</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default AdvancesLoansManagement;
