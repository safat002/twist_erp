import React, { useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CalendarOutlined,
  PlusOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import PageHeader from '../../components/Common/PageHeader';
import api from '../../services/api';

const { Text } = Typography;

const STATUS_COLORS = {
  PLANNED: 'processing',
  IN_PROGRESS: 'blue',
  COMPLETED: 'green',
  OVERDUE: 'red',
};

const STATUS_OPTIONS = [
  { value: 'PLANNED', label: 'Planned' },
  { value: 'IN_PROGRESS', label: 'In progress' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'OVERDUE', label: 'Overdue' },
];

const PERIOD_OPTIONS = [
  { value: 'ALL', label: 'All tasks' },
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'overdue', label: 'Overdue' },
];

const AssetMaintenance = () => {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [summary, setSummary] = useState({ overdue: 0, this_month: 0, completed: 0, total: 0 });
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [periodFilter, setPeriodFilter] = useState('ALL');
  const [modalVisible, setModalVisible] = useState(false);
  const [assetOptions, setAssetOptions] = useState([]);
  const [form] = Form.useForm();

  useEffect(() => {
    loadMaintenance();
  }, [statusFilter, periodFilter]);

  useEffect(() => {
    loadSummary();
    loadAssets();
  }, []);

  const loadMaintenance = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'ALL') {
        params.status = statusFilter;
      }
      if (periodFilter !== 'ALL') {
        params.period = periodFilter;
      }
      const { data } = await api.get('/api/v1/assets/maintenance/', { params });
      setTasks(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load maintenance planner', error);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      const { data } = await api.get('/api/v1/assets/maintenance/summary/');
      setSummary(data || { overdue: 0, this_month: 0, completed: 0, total: 0 });
    } catch (error) {
      console.warn('Unable to load maintenance summary', error?.message);
      setSummary({ overdue: 0, this_month: 0, completed: 0, total: 0 });
    }
  };

  const loadAssets = async () => {
    try {
      const { data } = await api.get('/api/v1/assets/');
      const options = (Array.isArray(data) ? data : []).map((asset) => ({
        value: asset.id,
        label: `${asset.code} — ${asset.name}`,
      }));
      setAssetOptions(options);
    } catch (error) {
      console.warn('Unable to load assets for maintenance form', error?.message);
    }
  };

  const handleStatusChange = async (taskId, value) => {
    try {
      await api.patch(`/api/v1/assets/maintenance/${taskId}/`, { status: value });
      message.success('Maintenance status updated.');
      loadMaintenance();
      loadSummary();
    } catch (error) {
      console.error('Failed to update maintenance status', error);
      message.error('Could not update status.');
    }
  };

  const handleMarkComplete = async (taskId) => {
    try {
      await api.patch(`/api/v1/assets/maintenance/${taskId}/`, {
        status: 'COMPLETED',
        completed_at: dayjs().format('YYYY-MM-DD'),
      });
      message.success('Task marked as completed.');
      loadMaintenance();
      loadSummary();
    } catch (error) {
      console.error('Failed to complete task', error);
      message.error('Could not complete task.');
    }
  };

  const handleCreateTask = async () => {
    try {
      const values = await form.validateFields();
      await api.post('/api/v1/assets/maintenance/', {
        ...values,
        scheduled_date: values.scheduled_date.format('YYYY-MM-DD'),
        due_date: values.due_date.format('YYYY-MM-DD'),
      });
      message.success('Maintenance task scheduled.');
      setModalVisible(false);
      form.resetFields();
      loadMaintenance();
      loadSummary();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      console.error('Failed to create maintenance task', error);
      message.error('Could not create task.');
    }
  };

  const columns = useMemo(
    () => [
      {
        title: 'Asset',
        dataIndex: 'asset_code',
        key: 'asset_code',
        render: (value, record) => (
          <Space direction="vertical" size={0}>
            <Text strong>{value}</Text>
            <Text type="secondary">{record.asset_name}</Text>
          </Space>
        ),
      },
      {
        title: 'Task',
        dataIndex: 'title',
        key: 'title',
        render: (value, record) => (
          <Space direction="vertical" size={0}>
            <Text>{value}</Text>
            {record.maintenance_type ? (
              <Tag color="blue">{record.maintenance_type}</Tag>
            ) : null}
          </Space>
        ),
      },
      {
        title: 'Scheduled',
        dataIndex: 'scheduled_date',
        key: 'scheduled_date',
        render: (value) => (value ? dayjs(value).format('DD MMM YYYY') : '—'),
      },
      {
        title: 'Due',
        dataIndex: 'due_date',
        key: 'due_date',
        render: (value, record) => {
          const formatted = value ? dayjs(value).format('DD MMM YYYY') : '—';
          return record.is_overdue ? (
            <Badge status="error" text={formatted} />
          ) : (
            formatted
          );
        },
      },
      {
        title: 'Assigned To',
        dataIndex: 'assigned_to',
        key: 'assigned_to',
        render: (value) => value || '—',
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (value, record) => (
          <Select
            value={value}
            onChange={(next) => handleStatusChange(record.id, next)}
            options={STATUS_OPTIONS}
            size="small"
            style={{ minWidth: 150 }}
          />
        ),
      },
      {
        title: 'Actions',
        key: 'actions',
        render: (_, record) => (
          <Space>
            {record.status !== 'COMPLETED' ? (
              <Button
                type="link"
                icon={<CheckCircleOutlined />}
                onClick={() => handleMarkComplete(record.id)}
              >
                Complete
              </Button>
            ) : null}
          </Space>
        ),
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader
        title="Maintenance Planner"
        subtitle="Plan, monitor, and close preventive maintenance activities"
        extra={
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 180 }}
              options={[{ value: 'ALL', label: 'All statuses' }, ...STATUS_OPTIONS]}
            />
            <Select
              value={periodFilter}
              onChange={setPeriodFilter}
              style={{ width: 150 }}
              options={PERIOD_OPTIONS}
            />
            <Button icon={<ReloadOutlined />} onClick={loadMaintenance} loading={loading} />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
              Schedule Task
            </Button>
          </Space>
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          <Card>
            <Statistic
              title="Open Tasks"
              value={summary.total - summary.completed}
              prefix={<CalendarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="Due This Month" value={summary.this_month} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="Overdue" value={summary.overdue} valueStyle={{ color: '#ff4d4f' }} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="Completed" value={summary.completed} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={tasks}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title="Schedule Maintenance Task"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleCreateTask}
        okText="Create"
      >
        <Form layout="vertical" form={form}>
          <Form.Item
            name="asset"
            label="Asset"
            rules={[{ required: true, message: 'Select an asset' }]}
          >
            <Select
              showSearch
              options={assetOptions}
              placeholder="Select asset"
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item
            name="title"
            label="Task title"
            rules={[{ required: true, message: 'Provide a task title' }]}
          >
            <Input placeholder="e.g. Quarterly calibration" />
          </Form.Item>
          <Form.Item name="maintenance_type" label="Type">
            <Input placeholder="Preventive / Inspection / Calibration" />
          </Form.Item>
          <Form.Item
            name="scheduled_date"
            label="Scheduled date"
            rules={[{ required: true, message: 'Select scheduled date' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="due_date"
            label="Due date"
            rules={[{ required: true, message: 'Select due date' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="assigned_to" label="Assigned to">
            <Input placeholder="Team or owner" />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input.TextArea rows={3} placeholder="Additional instructions" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AssetMaintenance;
