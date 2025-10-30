import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Form,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
} from 'antd';
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import {
  fetchAttendance,
  fetchEmployees,
  markAttendance,
} from '../../../services/hr';

const { RangePicker } = DatePicker;

const ATTENDANCE_STATUSES = [
  { value: 'PRESENT', label: 'Present', color: 'green' },
  { value: 'REMOTE', label: 'Remote', color: 'blue' },
  { value: 'HALF_DAY', label: 'Half Day', color: 'gold' },
  { value: 'LEAVE', label: 'On Leave', color: 'purple' },
  { value: 'ABSENT', label: 'Absent', color: 'red' },
];

const ATTENDANCE_SOURCES = [
  { value: 'MANUAL', label: 'Manual' },
  { value: 'BIOMETRIC', label: 'Biometric' },
  { value: 'GEO_FENCED', label: 'Geo-fenced Mobile' },
  { value: 'IMPORTED', label: 'Imported' },
];

const DEMO_ATTENDANCE = [
  {
    id: 'demo-att-1',
    employee: 'demo-emp-1',
    employee_name: 'Farhana Rahman',
    status: 'PRESENT',
    source: 'BIOMETRIC',
    date: dayjs().subtract(1, 'day').format('YYYY-MM-DD'),
    check_in: dayjs().subtract(1, 'day').hour(9).minute(3).format(),
    check_out: dayjs().subtract(1, 'day').hour(18).minute(12).format(),
    worked_hours: 8.5,
    overtime_hours: 1.5,
  },
  {
    id: 'demo-att-2',
    employee: 'demo-emp-2',
    employee_name: 'Hasibul Karim',
    status: 'HALF_DAY',
    source: 'MANUAL',
    date: dayjs().format('YYYY-MM-DD'),
    check_in: dayjs().hour(9).minute(0).format(),
    check_out: dayjs().hour(13).minute(0).format(),
    worked_hours: 4,
    overtime_hours: 0,
  },
  {
    id: 'demo-att-3',
    employee: 'demo-emp-3',
    employee_name: 'Nadia Akter',
    status: 'LEAVE',
    source: 'MANUAL',
    date: dayjs().format('YYYY-MM-DD'),
    worked_hours: 0,
    overtime_hours: 0,
  },
];

const renderStatusTag = (value) => {
  const item = ATTENDANCE_STATUSES.find((status) => status.value === value);
  if (!item) {
    return value;
  }
  return <Tag color={item.color}>{item.label}</Tag>;
};

export default function Attendance() {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);
  const [isModalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const isDemoCompany = !currentCompany || Number.isNaN(Number(currentCompany.id));

  const loadAttendance = async () => {
    if (!currentCompany) {
      return;
    }
    setLoading(true);
    try {
      if (isDemoCompany) {
        setRecords(DEMO_ATTENDANCE);
        setEmployees([
          { id: 'demo-emp-1', full_name: 'Farhana Rahman' },
          { id: 'demo-emp-2', full_name: 'Hasibul Karim' },
          { id: 'demo-emp-3', full_name: 'Nadia Akter' },
        ]);
        return;
      }

      const params = {
        start_date: dateRange?.[0]?.format('YYYY-MM-DD'),
        end_date: dateRange?.[1]?.format('YYYY-MM-DD'),
      };
      const [attendanceData, employeeData] = await Promise.all([
        fetchAttendance(params),
        fetchEmployees(),
      ]);
      setRecords(Array.isArray(attendanceData) ? attendanceData : []);
      setEmployees(Array.isArray(employeeData) ? employeeData : []);
    } catch (error) {
      console.warn('Unable to load attendance. Showing demo data.', error);
      setRecords(DEMO_ATTENDANCE);
      setEmployees([
        { id: 'demo-emp-1', full_name: 'Farhana Rahman' },
        { id: 'demo-emp-2', full_name: 'Hasibul Karim' },
        { id: 'demo-emp-3', full_name: 'Nadia Akter' },
      ]);
      message.warning('Showing demo attendance data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAttendance();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCompany?.id, dateRange[0], dateRange[1]]);

  const handleMarkAttendance = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        date: values.date.format('YYYY-MM-DD'),
        check_in: values.check_in ? values.check_in.format('YYYY-MM-DDTHH:mm:ss') : null,
        check_out: values.check_out ? values.check_out.format('YYYY-MM-DDTHH:mm:ss') : null,
      };

      if (payload.worked_hours !== undefined && payload.worked_hours !== null) {
        payload.worked_hours = Number(payload.worked_hours);
      }
      if (payload.overtime_hours !== undefined && payload.overtime_hours !== null) {
        payload.overtime_hours = Number(payload.overtime_hours);
      }

      if (isDemoCompany) {
        const employee = employees.find((item) => String(item.id) === String(payload.employee));
        const decorated = {
          id: `demo-att-${Date.now()}`,
          employee_name: employee?.full_name || 'Employee',
          worked_hours: payload.worked_hours || 0,
          overtime_hours: payload.overtime_hours || 0,
          ...payload,
        };
        setRecords((prev) => [decorated, ...prev]);
        message.success('Attendance recorded (demo)');
        form.resetFields();
        setModalVisible(false);
        return;
      }

      const created = await markAttendance(payload);
      setRecords((prev) => [created, ...prev]);
      message.success('Attendance recorded');
      form.resetFields();
      setModalVisible(false);
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      console.warn('Attendance save failed:', error);
      message.error(error?.response?.data?.detail || 'Unable to record attendance.');
    }
  };

  const employeeOptions = useMemo(
    () =>
      employees.map((employee) => ({
        label: employee.full_name || `${employee.first_name} ${employee.last_name}`,
        value: employee.id,
      })),
    [employees],
  );

  const columns = useMemo(
    () => [
      {
        title: 'Date',
        dataIndex: 'date',
        key: 'date',
        width: 130,
        render: (value) => dayjs(value).format('DD MMM YYYY'),
      },
      {
        title: 'Employee',
        dataIndex: 'employee_name',
        key: 'employee_name',
        render: (value, record) =>
          value || record.employee_name || record.employee_full_name || record.employee,
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: renderStatusTag,
      },
      {
        title: 'Source',
        dataIndex: 'source',
        key: 'source',
        render: (value) =>
          ATTENDANCE_SOURCES.find((item) => item.value === value)?.label || value,
      },
      {
        title: 'Check-in',
        dataIndex: 'check_in',
        key: 'check_in',
        render: (value) => (value ? dayjs(value).format('HH:mm') : '—'),
      },
      {
        title: 'Check-out',
        dataIndex: 'check_out',
        key: 'check_out',
        render: (value) => (value ? dayjs(value).format('HH:mm') : '—'),
      },
      {
        title: 'Hours',
        dataIndex: 'worked_hours',
        key: 'worked_hours',
        render: (value) => (value ? Number(value).toFixed(2) : '0.00'),
      },
      {
        title: 'Overtime',
        dataIndex: 'overtime_hours',
        key: 'overtime_hours',
        render: (value) => (value ? Number(value).toFixed(2) : '0.00'),
      },
    ],
    [],
  );

  return (
    <Card
      title="Attendance & Time Tracking"
      extra={
        <Space>
          <RangePicker
            value={dateRange}
            allowClear={false}
            onChange={(value) => {
              if (!value || value.length !== 2) {
                return;
              }
              setDateRange(value);
            }}
          />
          <Button icon={<ReloadOutlined />} onClick={loadAttendance} loading={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            Mark Attendance
          </Button>
        </Space>
      }
    >
      <Table
        rowKey={(record) => record.id || `${record.employee}-${record.date}`}
        dataSource={records}
        columns={columns}
        loading={loading}
        pagination={{ pageSize: 12 }}
        scroll={{ x: 900 }}
      />

      <Modal
        open={isModalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        onOk={handleMarkAttendance}
        title="Mark Attendance"
        okText="Save"
        destroyOnClose
        width={520}
      >
        <Form form={form} layout="vertical" initialValues={{ status: 'PRESENT', source: 'MANUAL' }}>
          <Form.Item
            label="Employee"
            name="employee"
            rules={[{ required: true, message: 'Select employee.' }]}
          >
            <Select
              options={employeeOptions}
              showSearch
              placeholder="Select employee"
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item
            label="Date"
            name="date"
            initialValue={dayjs()}
            rules={[{ required: true, message: 'Select attendance date.' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="Status" name="status">
            <Select options={ATTENDANCE_STATUSES.map(({ value, label }) => ({ value, label }))} />
          </Form.Item>
          <Form.Item label="Source" name="source">
            <Select options={ATTENDANCE_SOURCES} />
          </Form.Item>
          <Form.Item label="Check-in" name="check_in">
            <DatePicker showTime style={{ width: '100%' }} placeholder="Optional" />
          </Form.Item>
          <Form.Item label="Check-out" name="check_out">
            <DatePicker showTime style={{ width: '100%' }} placeholder="Optional" />
          </Form.Item>
          <Space style={{ width: '100%' }} size="large">
            <Form.Item label="Worked Hours" name="worked_hours" style={{ flex: 1 }}>
              <Select
                placeholder="Auto or manual"
                allowClear
                options={[4, 6, 7.5, 8, 9, 10].map((value) => ({
                  value,
                  label: `${value} hrs`,
                }))}
              />
            </Form.Item>
            <Form.Item label="Overtime (hrs)" name="overtime_hours" style={{ flex: 1 }}>
              <Select
                placeholder="Optional"
                allowClear
                options={[0, 1, 1.5, 2, 3].map((value) => ({ value, label: `${value}` }))}
              />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}
