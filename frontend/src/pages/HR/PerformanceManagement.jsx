import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, Input, Select, DatePicker, InputNumber, message, Space } from 'antd';
import { PlusOutlined, EditOutlined, CheckCircleOutlined, TrophyOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const PerformanceManagement = () => {
  const [reviewCycles, setReviewCycles] = useState([]);
  const [goals, setGoals] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [competencies, setCompetencies] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isCycleModalVisible, setIsCycleModalVisible] = useState(false);
  const [isGoalModalVisible, setIsGoalModalVisible] = useState(false);
  const [isReviewModalVisible, setIsReviewModalVisible] = useState(false);
  const [isCompetencyModalVisible, setIsCompetencyModalVisible] = useState(false);

  const [cycleForm] = Form.useForm();
  const [goalForm] = Form.useForm();
  const [reviewForm] = Form.useForm();
  const [competencyForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cyclesRes, goalsRes, reviewsRes, competenciesRes] = await Promise.all([
        api.get('/api/v1/hr/performance-review-cycles/'),
        api.get('/api/v1/hr/performance-goals/'),
        api.get('/api/v1/hr/performance-reviews/'),
        api.get('/api/v1/hr/competencies/'),
      ]);
      setReviewCycles(cyclesRes.data);
      setGoals(goalsRes.data);
      setReviews(reviewsRes.data);
      setCompetencies(competenciesRes.data);
    } catch (error) {
      message.error('Failed to load performance data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Review Cycle Handlers
  const showCycleModal = () => setIsCycleModalVisible(true);
  const handleCycleCancel = () => {
    setIsCycleModalVisible(false);
    cycleForm.resetFields();
  };
  const handleCycleSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/performance-review-cycles/', values);
      message.success('Review cycle created successfully!');
      handleCycleCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to create review cycle.');
    }
  };

  // Performance Goal Handlers
  const showGoalModal = () => setIsGoalModalVisible(true);
  const handleGoalCancel = () => {
    setIsGoalModalVisible(false);
    goalForm.resetFields();
  };
  const handleGoalSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/performance-goals/', values);
      message.success('Performance goal created successfully!');
      handleGoalCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to create performance goal.');
    }
  };

  // Competency Handlers
  const showCompetencyModal = () => setIsCompetencyModalVisible(true);
  const handleCompetencyCancel = () => {
    setIsCompetencyModalVisible(false);
    competencyForm.resetFields();
  };
  const handleCompetencySubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/competencies/', values);
      message.success('Competency created successfully!');
      handleCompetencyCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to create competency.');
    }
  };

  // Performance Review Handlers
  const showReviewModal = () => setIsReviewModalVisible(true);
  const handleReviewCancel = () => {
    setIsReviewModalVisible(false);
    reviewForm.resetFields();
  };
  const handleReviewSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/performance-reviews/', values);
      message.success('Performance review created successfully!');
      handleReviewCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to create performance review.');
    }
  };

  const getStatusTag = (status) => {
    let color;
    switch (status) {
      case 'DRAFT': color = 'default'; break;
      case 'NOT_STARTED': color = 'default'; break;
      case 'IN_PROGRESS': color = 'blue'; break;
      case 'SUBMITTED': color = 'gold'; break;
      case 'APPROVED':
      case 'COMPLETED':
      case 'ACHIEVED': color = 'green'; break;
      case 'REJECTED':
      case 'NOT_ACHIEVED': color = 'red'; break;
      default: color = 'default';
    }
    return <Tag color={color}>{status}</Tag>;
  };

  const reviewCyclesColumns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Year', dataIndex: 'year', key: 'year' },
    { title: 'Start Date', dataIndex: 'start_date', key: 'start_date' },
    { title: 'End Date', dataIndex: 'end_date', key: 'end_date' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  const goalsColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Review Cycle', dataIndex: 'review_cycle_name', key: 'review_cycle_name' },
    { title: 'Title', dataIndex: 'title', key: 'title' },
    { title: 'Category', dataIndex: 'category', key: 'category' },
    { title: 'Due Date', dataIndex: 'due_date', key: 'due_date' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  const reviewsColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Review Cycle', dataIndex: 'review_cycle_name', key: 'review_cycle_name' },
    { title: 'Reviewer', dataIndex: 'reviewer_name', key: 'reviewer_name' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: getStatusTag },
    { title: 'Final Rating', dataIndex: 'final_rating', key: 'final_rating' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  const competenciesColumns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Type', dataIndex: 'competency_type', key: 'competency_type' },
    { title: 'Description', dataIndex: 'description', key: 'description' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Performance & Appraisal Management</Title>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="Review Cycles" key="1">
            <Button type="primary" icon={<PlusOutlined />} onClick={showCycleModal} style={{ marginBottom: 16 }}>
              Create Review Cycle
            </Button>
            <Table columns={reviewCyclesColumns} dataSource={reviewCycles} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Goals" key="2">
            <Button type="primary" icon={<PlusOutlined />} onClick={showGoalModal} style={{ marginBottom: 16 }}>
              Create Goal
            </Button>
            <Table columns={goalsColumns} dataSource={goals} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Reviews" key="3">
            <Button type="primary" icon={<PlusOutlined />} onClick={showReviewModal} style={{ marginBottom: 16 }}>
              Create Review
            </Button>
            <Table columns={reviewsColumns} dataSource={reviews} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Competencies" key="4">
            <Button type="primary" icon={<PlusOutlined />} onClick={showCompetencyModal} style={{ marginBottom: 16 }}>
              Create Competency
            </Button>
            <Table columns={competenciesColumns} dataSource={competencies} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      {/* Review Cycle Modal */}
      <Modal title="Create Review Cycle" visible={isCycleModalVisible} onCancel={handleCycleCancel} footer={null}>
        <Form form={cycleForm} layout="vertical" onFinish={handleCycleSubmit}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="year" label="Year" rules={[{ required: true }]}>
            <InputNumber min={2000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="start_date" label="Start Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="end_date" label="End Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Create Cycle</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Performance Goal Modal */}
      <Modal title="Create Performance Goal" visible={isGoalModalVisible} onCancel={handleGoalCancel} footer={null}>
        <Form form={goalForm} layout="vertical" onFinish={handleGoalSubmit}>
          <Form.Item name="employee" label="Employee" rules={[{ required: true }]}> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="review_cycle" label="Review Cycle" rules={[{ required: true }]}>
            <Select options={reviewCycles.map(cycle => ({ label: cycle.name, value: cycle.id }))} />
          </Form.Item>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description" rules={[{ required: true }]}>
            <TextArea rows={2} />
          </Form.Item>
          <Form.Item name="category" label="Category" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="BUSINESS">Business Result</Select.Option>
              <Select.Option value="COMPETENCY">Competency Development</Select.Option>
              <Select.Option value="PROJECT">Project Delivery</Select.Option>
              <Select.Option value="OTHER">Other</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="due_date" label="Due Date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Create Goal</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Performance Review Modal */}
      <Modal title="Create Performance Review" visible={isReviewModalVisible} onCancel={handleReviewCancel} footer={null}>
        <Form form={reviewForm} layout="vertical" onFinish={handleReviewSubmit}>
          <Form.Item name="employee" label="Employee" rules={[{ required: true }]}> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="review_cycle" label="Review Cycle" rules={[{ required: true }]}>
            <Select options={reviewCycles.map(cycle => ({ label: cycle.name, value: cycle.id }))} />
          </Form.Item>
          <Form.Item name="reviewer" label="Reviewer"> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="status" label="Status" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="DRAFT">Draft</Select.Option>
              <Select.Option value="SELF_ASSESSMENT">Self Assessment</Select.Option>
              <Select.Option value="MANAGER_REVIEW">Manager Review</Select.Option>
              <Select.Option value="CALIBRATION">Calibration</Select.Option>
              <Select.Option value="COMPLETED">Completed</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Create Review</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Competency Modal */}
      <Modal title="Create Competency" visible={isCompetencyModalVisible} onCancel={handleCompetencyCancel} footer={null}>
        <Form form={competencyForm} layout="vertical" onFinish={handleCompetencySubmit}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <TextArea rows={2} />
          </Form.Item>
          <Form.Item name="competency_type" label="Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="TECHNICAL">Technical</Select.Option>
              <Select.Option value="BEHAVIORAL">Behavioral</Select.Option>
              <Select.Option value="LEADERSHIP">Leadership</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Create Competency</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default PerformanceManagement;
