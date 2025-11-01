import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, Input, Select, DatePicker, message, Space } from 'antd';
import { PlusOutlined, EditOutlined, UserAddOutlined, CalendarOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const RecruitmentManagement = () => {
  const [jobRequisitions, setJobRequisitions] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isReqModalVisible, setIsReqModalVisible] = useState(false);
  const [isCandidateModalVisible, setIsCandidateModalVisible] = useState(false);
  const [isInterviewModalVisible, setIsInterviewModalVisible] = useState(false);

  const [reqForm] = Form.useForm();
  const [candidateForm] = Form.useForm();
  const [interviewForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [reqsRes, candidatesRes, interviewsRes] = await Promise.all([
        api.get('/api/v1/hr/job-requisitions/'),
        api.get('/api/v1/hr/candidates/'),
        api.get('/api/v1/hr/interviews/'),
      ]);
      setJobRequisitions(reqsRes.data);
      setCandidates(candidatesRes.data);
      setInterviews(interviewsRes.data);
    } catch (error) {
      message.error('Failed to load recruitment data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Job Requisition Handlers
  const showReqModal = () => setIsReqModalVisible(true);
  const handleReqCancel = () => {
    setIsReqModalVisible(false);
    reqForm.resetFields();
  };
  const handleReqSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/job-requisitions/', values);
      message.success('Job requisition submitted successfully!');
      handleReqCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to submit job requisition.');
    }
  };

  // Candidate Handlers
  const showCandidateModal = () => setIsCandidateModalVisible(true);
  const handleCandidateCancel = () => {
    setIsCandidateModalVisible(false);
    candidateForm.resetFields();
  };
  const handleCandidateSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/candidates/', values);
      message.success('Candidate added successfully!');
      handleCandidateCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to add candidate.');
    }
  };

  // Interview Handlers
  const showInterviewModal = () => setIsInterviewModalVisible(true);
  const handleInterviewCancel = () => {
    setIsInterviewModalVisible(false);
    interviewForm.resetFields();
  };
  const handleInterviewSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/interviews/', values);
      message.success('Interview scheduled successfully!');
      handleInterviewCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to schedule interview.');
    }
  };

  const getStatusTag = (status) => {
    let color;
    switch (status) {
      case 'DRAFT': color = 'default'; break;
      case 'SUBMITTED': color = 'blue'; break;
      case 'APPROVED':
      case 'HIRED':
      case 'COMPLETED': color = 'green'; break;
      case 'REJECTED':
      case 'CANCELLED':
      case 'WITHDRAWN': color = 'red'; break;
      case 'SCREENING':
      case 'INTERVIEW':
      case 'OFFER': color = 'gold'; break;
      default: color = 'default';
    }
    return <Tag color={color}>{status}</Tag>;
  };

  const jobRequisitionsColumns = [
    { title: 'Req No.', dataIndex: 'requisition_number', key: 'requisition_number' },
    { title: 'Job Title', dataIndex: 'job_title', key: 'job_title' },
    { title: 'Department', dataIndex: 'department_name', key: 'department_name' },
    { title: 'Positions', dataIndex: 'number_of_positions', key: 'number_of_positions' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Requested By', dataIndex: 'requested_by_name', key: 'requested_by_name' },
    { title: 'Target Start', dataIndex: 'target_start_date', key: 'target_start_date' },
    { title: 'Budget', dataIndex: 'budget_allocated', key: 'budget_allocated' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} size="small">Edit</Button>
          <Button icon={<UserAddOutlined />} size="small">Add Candidate</Button>
        </Space>
      ),
    },
  ];

  const candidatesColumns = [
    { title: 'Name', dataIndex: 'full_name', key: 'full_name' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Phone', dataIndex: 'phone', key: 'phone' },
    { title: 'Job Requisition', dataIndex: 'job_requisition_title', key: 'job_requisition_title' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} size="small">Edit</Button>
          <Button icon={<CalendarOutlined />} size="small">Schedule Interview</Button>
        </Space>
      ),
    },
  ];

  const interviewsColumns = [
    { title: 'Candidate', dataIndex: 'candidate_name', key: 'candidate_name' },
    { title: 'Type', dataIndex: 'interview_type', key: 'interview_type' },
    { title: 'Scheduled Date', dataIndex: 'scheduled_date', key: 'scheduled_date' },
    { title: 'Interviewer', dataIndex: 'interviewer_name', key: 'interviewer_name' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} size="small">Edit</Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Recruitment Management</Title>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="Job Requisitions" key="1">
            <Button type="primary" icon={<PlusOutlined />} onClick={showReqModal} style={{ marginBottom: 16 }}>
              Create Job Requisition
            </Button>
            <Table columns={jobRequisitionsColumns} dataSource={jobRequisitions} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Candidates" key="2">
            <Button type="primary" icon={<UserAddOutlined />} onClick={showCandidateModal} style={{ marginBottom: 16 }}>
              Add Candidate
            </Button>
            <Table columns={candidatesColumns} dataSource={candidates} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Interviews" key="3">
            <Table columns={interviewsColumns} dataSource={interviews} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      {/* Job Requisition Modal */}
      <Modal title="Create Job Requisition" visible={isReqModalVisible} onCancel={handleReqCancel} footer={null}>
        <Form form={reqForm} layout="vertical" onFinish={handleReqSubmit}>
          <Form.Item name="job_title" label="Job Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department" label="Department" rules={[{ required: true }]}>
            <Input /> {/* TODO: Replace with Select for Departments */}
          </Form.Item>
          <Form.Item name="number_of_positions" label="Number of Positions" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="justification" label="Justification" rules={[{ required: true }]}>
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item name="target_start_date" label="Target Start Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Submit Requisition</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Candidate Modal */}
      <Modal title="Add Candidate" visible={isCandidateModalVisible} onCancel={handleCandidateCancel} footer={null}>
        <Form form={candidateForm} layout="vertical" onFinish={handleCandidateSubmit}>
          <Form.Item name="first_name" label="First Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="last_name" label="Last Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="Phone">
            <Input />
          </Form.Item>
          <Form.Item name="job_requisition" label="Job Requisition" rules={[{ required: true }]}>
            <Select options={jobRequisitions.map(req => ({ label: req.job_title, value: req.id }))} />
          </Form.Item>
          <Form.Item name="status" label="Status">
            <Select defaultValue="NEW">
              <Select.Option value="NEW">New</Select.Option>
              <Select.Option value="SCREENING">Screening</Select.Option>
              <Select.Option value="INTERVIEW">Interview</Select.Option>
              <Select.Option value="OFFER">Offer</Select.Option>
              <Select.Option value="HIRED">Hired</Select.Option>
              <Select.Option value="REJECTED">Rejected</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Add Candidate</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Interview Modal */}
      <Modal title="Schedule Interview" visible={isInterviewModalVisible} onCancel={handleInterviewCancel} footer={null}>
        <Form form={interviewForm} layout="vertical" onFinish={handleInterviewSubmit}>
          <Form.Item name="candidate" label="Candidate" rules={[{ required: true }]}>
            <Select options={candidates.map(cand => ({ label: cand.full_name, value: cand.id }))} />
          </Form.Item>
          <Form.Item name="interview_type" label="Interview Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="PHONE">Phone Screening</Select.Option>
              <Select.Option value="VIDEO">Video Interview</Select.Option>
              <Select.Option value="ONSITE">Onsite Interview</Select.Option>
              <Select.Option value="TECHNICAL">Technical Assessment</Select.Option>
              <Select.Option value="HR">HR Round</Select.Option>
              <Select.Option value="PANEL">Panel Interview</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="scheduled_date" label="Scheduled Date" rules={[{ required: true }]}>
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="interviewer" label="Interviewer" rules={[{ required: true }]}>
            <Input /> {/* TODO: Replace with Select for Employees */}
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Schedule Interview</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default RecruitmentManagement;
