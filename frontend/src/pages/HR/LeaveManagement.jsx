import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, DatePicker, Input, message, Space } from 'antd';
import { PlusOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { RangePicker } = DatePicker;

const LeaveManagement = () => {
  const [myRequests, setMyRequests] = useState([]);
  const [teamRequests, setTeamRequests] = useState([]);
  const [balances, setBalances] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [requestsRes, teamRes, balancesRes, typesRes] = await Promise.all([
        api.get('/api/v1/hr/leave-requests/'),
        api.get('/api/v1/hr/leave-requests/team_requests/'),
        api.get('/api/v1/hr/leave-balances/'),
        api.get('/api/v1/hr/leave-types/'),
      ]);
      setMyRequests(requestsRes.data);
      setTeamRequests(teamRes.data);
      setBalances(balancesRes.data);
      setLeaveTypes(typesRes.data);
    } catch (error) {
      message.error('Failed to load leave data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const showModal = () => {
    setIsModalVisible(true);
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    form.resetFields();
  };

  const handleFormSubmit = async (values) => {
    const [start_date, end_date] = values.dateRange;
    const payload = {
      leave_type: values.leave_type,
      start_date: start_date.format('YYYY-MM-DD'),
      end_date: end_date.format('YYYY-MM-DD'),
      reason: values.reason,
    };

    try {
      await api.post('/api/v1/hr/leave-requests/', payload);
      message.success('Leave request submitted successfully!');
      handleCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to submit leave request.');
    }
  };

  const handleApprove = async (id) => {
    try {
      await api.post(`/api/v1/hr/leave-requests/${id}/approve/`);
      message.success('Leave request approved.');
      fetchData();
    } catch (error) {
      message.error('Failed to approve request.');
    }
  };

  const handleReject = async (id) => {
    try {
      await api.post(`/api/v1/hr/leave-requests/${id}/reject/`);
      message.success('Leave request rejected.');
      fetchData();
    } catch (error) {
      message.error('Failed to reject request.');
    }
  };

  const getStatusTag = (status) => {
    switch (status) {
      case 'PENDING': return <Tag color="gold">Pending</Tag>;
      case 'APPROVED': return <Tag color="green">Approved</Tag>;
      case 'REJECTED': return <Tag color="red">Rejected</Tag>;
      default: return <Tag>{status}</Tag>;
    }
  };

  const myRequestsColumns = [
    { title: 'Leave Type', dataIndex: 'leave_type_name', key: 'leave_type' },
    { title: 'Start Date', dataIndex: 'start_date', key: 'start_date' },
    { title: 'End Date', dataIndex: 'end_date', key: 'end_date' },
    { title: 'Reason', dataIndex: 'reason', key: 'reason' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
  ];

  const teamRequestsColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee' },
    { title: 'Leave Type', dataIndex: 'leave_type_name', key: 'leave_type' },
    { title: 'Dates', key: 'dates', render: (_, record) => `${record.start_date} to ${record.end_date}` },
    { title: 'Reason', dataIndex: 'reason', key: 'reason' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    {
      title: 'Action',
      key: 'action',
      render: (_, record) => (
        record.status === 'PENDING' && (
          <Space>
            <Button icon={<CheckCircleOutlined />} type="primary" size="small" onClick={() => handleApprove(record.id)}>Approve</Button>
            <Button icon={<CloseCircleOutlined />} type="primary" danger size="small" onClick={() => handleReject(record.id)}>Reject</Button>
          </Space>
        )
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Leave & Holiday Management</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {balances.map(balance => (
          <Col key={balance.id} xs={24} sm={12} md={8} lg={6}>
            <Card>
              <Text strong>{balance.leave_type_name}</Text>
              <Title level={3}>{balance.balance} <Text style={{fontSize: '1rem'}}>Days</Text></Title>
            </Card>
          </Col>
        ))}
      </Row>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="My Requests" key="1">
            <Button type="primary" icon={<PlusOutlined />} onClick={showModal} style={{ marginBottom: 16 }}>
              Request Leave
            </Button>
            <Table columns={myRequestsColumns} dataSource={myRequests} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Team Requests" key="2">
            <Table columns={teamRequestsColumns} dataSource={teamRequests} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      <Modal title="Request New Leave" visible={isModalVisible} onCancel={handleCancel} footer={null}>
        <Form form={form} layout="vertical" onFinish={handleFormSubmit}>
          <Form.Item name="leave_type" label="Leave Type" rules={[{ required: true }]}>
            <Select options={leaveTypes.map(lt => ({ label: lt.name, value: lt.id }))} />
          </Form.Item>
          <Form.Item name="dateRange" label="Dates" rules={[{ required: true }]}>
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="reason" label="Reason" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Submit Request</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default LeaveManagement;
