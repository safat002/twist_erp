import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Row, Col, Table, Tag, Button, Modal, Form, Input, Select, DatePicker, InputNumber, message, Space } from 'antd';
import { PlusOutlined, EditOutlined, CalendarOutlined, ClockCircleOutlined } from '@ant-design/icons';
import api from '../../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

const AttendanceManagement = () => {
  const [shiftTemplates, setShiftTemplates] = useState([]);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isShiftModalVisible, setIsShiftModalVisible] = useState(false);
  const [isAttendanceModalVisible, setIsAttendanceModalVisible] = useState(false);

  const [shiftForm] = Form.useForm();
  const [attendanceForm] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [shiftsRes, attendanceRes] = await Promise.all([
        api.get('/api/v1/hr/shift-templates/'),
        api.get('/api/v1/hr/attendance/'),
      ]);
      setShiftTemplates(shiftsRes.data);
      setAttendanceRecords(attendanceRes.data);
    } catch (error) {
      message.error('Failed to load attendance data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Shift Template Handlers
  const showShiftModal = () => setIsShiftModalVisible(true);
  const handleShiftCancel = () => {
    setIsShiftModalVisible(false);
    shiftForm.resetFields();
  };
  const handleShiftSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/shift-templates/', values);
      message.success('Shift template added successfully!');
      handleShiftCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to add shift template.');
    }
  };

  // Attendance Record Handlers
  const showAttendanceModal = () => setIsAttendanceModalVisible(true);
  const handleAttendanceCancel = () => {
    setIsAttendanceModalVisible(false);
    attendanceForm.resetFields();
  };
  const handleAttendanceSubmit = async (values) => {
    try {
      await api.post('/api/v1/hr/attendance/', values);
      message.success('Attendance record added successfully!');
      handleAttendanceCancel();
      fetchData();
    } catch (error) {
      message.error('Failed to add attendance record.');
    }
  };

  const shiftTemplatesColumns = [
    { title: 'Code', dataIndex: 'code', key: 'code' },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Category', dataIndex: 'category', key: 'category' },
    { title: 'Start Time', dataIndex: 'start_time', key: 'start_time' },
    { title: 'End Time', dataIndex: 'end_time', key: 'end_time' },
    { title: 'Active', dataIndex: 'is_active', key: 'is_active', render: (text) => (text ? <Tag color="green">Yes</Tag> : <Tag>No</Tag>) },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  const attendanceRecordsColumns = [
    { title: 'Employee', dataIndex: 'employee_name', key: 'employee_name' },
    { title: 'Date', dataIndex: 'date', key: 'date' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (text) => <Tag color={text === 'PRESENT' ? 'green' : 'red'}>{text}</Tag> },
    { title: 'Shift', dataIndex: 'shift_name', key: 'shift_name' },
    { title: 'Check In', dataIndex: 'check_in', key: 'check_in' },
    { title: 'Check Out', dataIndex: 'check_out', key: 'check_out' },
    { title: 'Worked Hours', dataIndex: 'worked_hours', key: 'worked_hours' },
    { title: 'Action', key: 'action', render: (_, record) => (
        <Button icon={<EditOutlined />} size="small">Edit</Button>
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Attendance Management</Title>

      <Card>
        <Tabs defaultActiveKey="1">
          <TabPane tab="Shift Templates" key="1">
            <Button type="primary" icon={<PlusOutlined />} onClick={showShiftModal} style={{ marginBottom: 16 }}>
              Add Shift Template
            </Button>
            <Table columns={shiftTemplatesColumns} dataSource={shiftTemplates} rowKey="id" loading={loading} />
          </TabPane>
          <TabPane tab="Attendance Records" key="2">
            <Button type="primary" icon={<PlusOutlined />} onClick={showAttendanceModal} style={{ marginBottom: 16 }}>
              Add Attendance Record
            </Button>
            <Table columns={attendanceRecordsColumns} dataSource={attendanceRecords} rowKey="id" loading={loading} />
          </TabPane>
        </Tabs>
      </Card>

      {/* Shift Template Modal */}
      <Modal title="Add Shift Template" visible={isShiftModalVisible} onCancel={handleShiftCancel} footer={null}>
        <Form form={shiftForm} layout="vertical" onFinish={handleShiftSubmit}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="Category" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="DAY">Day</Select.Option>
              <Select.Option value="NIGHT">Night</Select.Option>
              <Select.Option value="ROTATING">Rotating</Select.Option>
              <Select.Option value="FLEX">Flexible</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="start_time" label="Start Time" rules={[{ required: true }]}>
            <DatePicker picker="time" format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="end_time" label="End Time" rules={[{ required: true }]}>
            <DatePicker picker="time" format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="break_minutes" label="Break Minutes">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Add Shift</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Attendance Record Modal */}
      <Modal title="Add Attendance Record" visible={isAttendanceModalVisible} onCancel={handleAttendanceCancel} footer={null}>
        <Form form={attendanceForm} layout="vertical" onFinish={handleAttendanceSubmit}>
          <Form.Item name="employee" label="Employee" rules={[{ required: true }]}> {/* TODO: Replace with Select for Employees */}
            <Input />
          </Form.Item>
          <Form.Item name="date" label="Date" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="Status" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="PRESENT">Present</Select.Option>
              <Select.Option value="ABSENT">Absent</Select.Option>
              <Select.Option value="LEAVE">Leave</Select.Option>
              <Select.Option value="HALF_DAY">Half Day</Select.Option>
              <Select.Option value="REMOTE">Remote</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="shift" label="Shift"> {/* TODO: Replace with Select for Shifts */}
            <Input />
          </Form.Item>
          <Form.Item name="check_in" label="Check In Time">
            <DatePicker picker="time" format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="check_out" label="Check Out Time">
            <DatePicker picker="time" format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Add Record</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default AttendanceManagement;
