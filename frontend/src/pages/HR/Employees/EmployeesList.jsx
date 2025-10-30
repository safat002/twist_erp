import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
} from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import {
  createEmployee,
  fetchDepartments,
  fetchEmployees,
  fetchEmploymentGrades,
  fetchSalaryStructures,
  updateEmployee,
} from '../../../services/hr';

const EMPLOYMENT_TYPES = [
  { value: 'FULL_TIME', label: 'Full-time' },
  { value: 'PART_TIME', label: 'Part-time' },
  { value: 'CONTRACT', label: 'Contract' },
  { value: 'INTERN', label: 'Intern' },
  { value: 'CONSULTANT', label: 'Consultant' },
];

const EMPLOYEE_STATUSES = [
  { value: 'ACTIVE', label: 'Active', color: 'green' },
  { value: 'ONBOARDING', label: 'Onboarding', color: 'blue' },
  { value: 'PROBATION', label: 'Probation', color: 'purple' },
  { value: 'LEAVE', label: 'On Leave', color: 'gold' },
  { value: 'TERMINATED', label: 'Terminated', color: 'red' },
  { value: 'RESIGNED', label: 'Resigned', color: 'volcano' },
];

const DEMO_DEPARTMENTS = [
  { id: 'demo-dept-1', name: 'People Operations', code: 'PO' },
  { id: 'demo-dept-2', name: 'Production Unit 3', code: 'PRD-3' },
  { id: 'demo-dept-3', name: 'Design & Merchandising', code: 'DES' },
];

const DEMO_GRADES = [
  { id: 'demo-grade-1', code: 'G6', name: 'Senior Manager' },
  { id: 'demo-grade-2', code: 'G4', name: 'Specialist' },
  { id: 'demo-grade-3', code: 'G2', name: 'Associate' },
];

const DEMO_STRUCTURES = [
  {
    id: 'demo-structure-1',
    name: 'Head Office Leadership',
    base_salary: 180000,
    total_fixed_compensation: 240000,
  },
  {
    id: 'demo-structure-2',
    name: 'Factory Supervisors',
    base_salary: 60000,
    total_fixed_compensation: 80000,
  },
  {
    id: 'demo-structure-3',
    name: 'Creative Team',
    base_salary: 45000,
    total_fixed_compensation: 62000,
  },
];

const DEMO_EMPLOYEES = [
  {
    id: 'demo-emp-1',
    employee_id: 'EMP-1001',
    first_name: 'Farhana',
    last_name: 'Rahman',
    full_name: 'Farhana Rahman',
    email: 'farhana.rahman@twist-erp.demo',
    job_title: 'Head of People',
    employment_type: 'FULL_TIME',
    status: 'ACTIVE',
    department: 'demo-dept-1',
    department_name: 'People Operations',
    grade: 'demo-grade-1',
    grade_name: 'Senior Manager',
    salary_structure: 'demo-structure-1',
    salary_structure_name: 'Head Office Leadership',
    date_of_joining: '2022-03-15',
    phone_number: '+8801700000001',
  },
  {
    id: 'demo-emp-2',
    employee_id: 'EMP-2045',
    first_name: 'Hasibul',
    last_name: 'Karim',
    full_name: 'Hasibul Karim',
    email: 'hasibul.karim@twist-erp.demo',
    job_title: 'Senior Production Supervisor',
    employment_type: 'FULL_TIME',
    status: 'PROBATION',
    department: 'demo-dept-2',
    department_name: 'Production Unit 3',
    grade: 'demo-grade-2',
    grade_name: 'Specialist',
    salary_structure: 'demo-structure-2',
    salary_structure_name: 'Factory Supervisors',
    date_of_joining: '2025-07-01',
    phone_number: '+8801700000123',
  },
  {
    id: 'demo-emp-3',
    employee_id: 'EMP-3057',
    first_name: 'Nadia',
    last_name: 'Akter',
    full_name: 'Nadia Akter',
    email: 'nadia.akter@twist-erp.demo',
    job_title: 'Visual Merchandiser',
    employment_type: 'FULL_TIME',
    status: 'LEAVE',
    department: 'demo-dept-3',
    department_name: 'Design & Merchandising',
    grade: 'demo-grade-3',
    grade_name: 'Associate',
    salary_structure: 'demo-structure-3',
    salary_structure_name: 'Creative Team',
    date_of_joining: '2023-11-20',
    phone_number: '+8801700000890',
  },
];

const statusTag = (value) => {
  const mapping = EMPLOYEE_STATUSES.find((item) => item.value === value);
  if (!mapping) {
    return value;
  }
  return <Tag color={mapping.color}>{mapping.label}</Tag>;
};

export default function EmployeesList() {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [grades, setGrades] = useState([]);
  const [structures, setStructures] = useState([]);
  const [isModalVisible, setModalVisible] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [form] = Form.useForm();
  const [selectedEmployee, setSelectedEmployee] = useState(null);

  const isDemoCompany = !currentCompany || Number.isNaN(Number(currentCompany.id));

  const loadDirectory = async () => {
    if (!currentCompany) {
      return;
    }
    setLoading(true);
    try {
      if (isDemoCompany) {
        setEmployees(DEMO_EMPLOYEES);
        setDepartments(DEMO_DEPARTMENTS);
        setGrades(DEMO_GRADES);
        setStructures(DEMO_STRUCTURES);
        return;
      }

      const [deptData, gradeData, structureData, employeeData] = await Promise.all([
        fetchDepartments(currentCompany.id),
        fetchEmploymentGrades(currentCompany.id),
        fetchSalaryStructures(currentCompany.id),
        fetchEmployees(),
      ]);

      setDepartments(Array.isArray(deptData) ? deptData : []);
      setGrades(Array.isArray(gradeData) ? gradeData : []);
      setStructures(Array.isArray(structureData) ? structureData : []);
      setEmployees(Array.isArray(employeeData) ? employeeData : []);
    } catch (error) {
      console.warn('Unable to load employee directory. Falling back to demo data.', error);
      setEmployees(DEMO_EMPLOYEES);
      setDepartments(DEMO_DEPARTMENTS);
      setGrades(DEMO_GRADES);
      setStructures(DEMO_STRUCTURES);
      message.warning('Showing demo employee data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDirectory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCompany?.id]);

  const handleCreateClick = () => {
    setIsEditing(false);
    setSelectedEmployee(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEditClick = (record) => {
    setIsEditing(true);
    setSelectedEmployee(record);
    form.setFieldsValue({
      ...record,
      department: record.department || record.department_id,
      grade: record.grade || record.grade_id,
      salary_structure: record.salary_structure || record.salary_structure_id,
      date_of_joining: record.date_of_joining ? dayjs(record.date_of_joining) : null,
      date_of_exit: record.date_of_exit ? dayjs(record.date_of_exit) : null,
    });
    setModalVisible(true);
  };

  const handleModalCancel = () => {
    setModalVisible(false);
    setSelectedEmployee(null);
    form.resetFields();
  };

  const decorateEmployeeRecord = (record) => {
    const departmentName =
      departments.find((dept) => String(dept.id) === String(record.department))?.name ||
      record.department_name ||
      null;
    const gradeName =
      grades.find((grade) => String(grade.id) === String(record.grade))?.name ||
      record.grade_name ||
      null;
    const structureName =
      structures.find((structure) => String(structure.id) === String(record.salary_structure))
        ?.name || record.salary_structure_name || null;

    return {
      ...record,
      full_name: `${record.first_name || ''} ${record.last_name || ''}`.trim(),
      department_name: departmentName || undefined,
      grade_name: gradeName || undefined,
      salary_structure_name: structureName || undefined,
    };
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        date_of_joining: values.date_of_joining
          ? values.date_of_joining.format('YYYY-MM-DD')
          : null,
        date_of_exit: values.date_of_exit ? values.date_of_exit.format('YYYY-MM-DD') : null,
      };

      if (isDemoCompany) {
        if (isEditing && selectedEmployee) {
          const updatedRecord = decorateEmployeeRecord({
            ...selectedEmployee,
            ...payload,
            id: selectedEmployee.id,
          });
          setEmployees((prev) =>
            prev.map((employee) => (employee.id === selectedEmployee.id ? updatedRecord : employee)),
          );
          message.success('Employee updated (demo)');
        } else {
          const newEmployee = decorateEmployeeRecord({
            id: `demo-${Date.now()}`,
            ...payload,
          });
          setEmployees((prev) => [newEmployee, ...prev]);
          message.success('Employee created (demo)');
        }
        handleModalCancel();
        return;
      }

      if (isEditing && selectedEmployee) {
        const updated = await updateEmployee(selectedEmployee.id, payload);
        const hydrated = decorateEmployeeRecord(updated);
        setEmployees((prev) =>
          prev.map((employee) => (employee.id === hydrated.id ? hydrated : employee)),
        );
        message.success('Employee updated');
      } else {
        const created = await createEmployee(payload);
        const hydrated = decorateEmployeeRecord(created);
        setEmployees((prev) => [hydrated, ...prev]);
        message.success('Employee created');
      }
      handleModalCancel();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      console.warn('Employee save failed:', error);
      message.error(error?.response?.data?.detail || 'Unable to save employee.');
    }
  };

  const columns = useMemo(
    () => [
      {
        title: 'Employee ID',
        dataIndex: 'employee_id',
        key: 'employee_id',
        width: 140,
        fixed: 'left',
      },
      {
        title: 'Name',
        dataIndex: 'full_name',
        key: 'full_name',
        render: (_, record) => record.full_name || `${record.first_name} ${record.last_name}`,
      },
      {
        title: 'Job Title',
        dataIndex: 'job_title',
        key: 'job_title',
      },
      {
        title: 'Department',
        dataIndex: 'department_name',
        key: 'department_name',
        render: (value, record) => value || record.department?.name || '—',
      },
      {
        title: 'Employment Type',
        dataIndex: 'employment_type',
        key: 'employment_type',
        render: (value) =>
          EMPLOYMENT_TYPES.find((item) => item.value === value)?.label || value,
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: statusTag,
      },
      {
        title: 'Joined',
        dataIndex: 'date_of_joining',
        key: 'date_of_joining',
        width: 130,
        render: (value) => (value ? dayjs(value).format('DD MMM YYYY') : '—'),
      },
      {
        title: 'Phone',
        dataIndex: 'phone_number',
        key: 'phone_number',
      },
      {
        title: 'Actions',
        key: 'actions',
        fixed: 'right',
        width: 140,
        render: (_, record) => (
          <Space>
            <Button size="small" onClick={() => handleEditClick(record)}>
              Edit
            </Button>
          </Space>
        ),
      },
    ],
    [],
  );

  const departmentOptions = useMemo(
    () =>
      departments.map((dept) => ({
        label: dept.name || dept.title,
        value: dept.id,
      })),
    [departments],
  );

  const gradeOptions = useMemo(
    () =>
      grades.map((grade) => ({
        label: grade.name || grade.code,
        value: grade.id,
      })),
    [grades],
  );

  const salaryStructureOptions = useMemo(
    () =>
      structures.map((structure) => ({
        label: structure.name,
        value: structure.id,
      })),
    [structures],
  );

  const managerOptions = useMemo(
    () =>
      employees.map((employee) => ({
        label: employee.full_name || `${employee.first_name} ${employee.last_name}`,
        value: employee.id,
      })),
    [employees],
  );

  return (
    <Card
      title="Employee Directory"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadDirectory} loading={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateClick}>
            New Employee
          </Button>
        </Space>
      }
    >
      <Table
        rowKey={(record) => record.id || record.employee_id}
        dataSource={employees}
        columns={columns}
        loading={loading}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 900 }}
      />

      <Modal
        open={isModalVisible}
        title={isEditing ? 'Edit Employee' : 'New Employee'}
        onCancel={handleModalCancel}
        onOk={handleSubmit}
        okText={isEditing ? 'Update' : 'Create'}
        destroyOnClose
        width={720}
      >
        <Form layout="vertical" form={form}>
          <Space style={{ width: '100%' }} size="large" direction="vertical">
            <Space style={{ width: '100%' }} size="large">
              <Form.Item
                label="Employee ID"
                name="employee_id"
                rules={[{ required: true, message: 'Employee ID is required.' }]}
                style={{ flex: 1 }}
              >
                <Input placeholder="EMP-0001" />
              </Form.Item>
              <Form.Item
                label="Employment Type"
                name="employment_type"
                rules={[{ required: true, message: 'Select employment type.' }]}
                style={{ flex: 1 }}
              >
                <Select options={EMPLOYMENT_TYPES} placeholder="Select type" />
              </Form.Item>
            </Space>

            <Space style={{ width: '100%' }} size="large">
              <Form.Item
                label="First Name"
                name="first_name"
                rules={[{ required: true, message: 'First name required.' }]}
                style={{ flex: 1 }}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="Last Name"
                name="last_name"
                style={{ flex: 1 }}
              >
                <Input />
              </Form.Item>
            </Space>

            <Space style={{ width: '100%' }} size="large">
              <Form.Item
                label="Email"
                name="email"
                rules={[{ type: 'email', message: 'Enter a valid email.' }]}
                style={{ flex: 1 }}
              >
                <Input placeholder="name@company.com" />
              </Form.Item>
              <Form.Item
                label="Phone"
                name="phone_number"
                style={{ flex: 1 }}
              >
                <Input placeholder="+8801..." />
              </Form.Item>
            </Space>

            <Space style={{ width: '100%' }} size="large">
              <Form.Item
                label="Job Title"
                name="job_title"
                style={{ flex: 1 }}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="Department"
                name="department"
                style={{ flex: 1 }}
              >
                <Select
                  options={departmentOptions}
                  placeholder="Select department"
                  allowClear
                  showSearch
                />
              </Form.Item>
            </Space>

            <Space style={{ width: '100%' }} size="large">
              <Form.Item label="Grade" name="grade" style={{ flex: 1 }}>
                <Select
                  options={gradeOptions}
                  placeholder="Select grade"
                  allowClear
                  showSearch
                />
              </Form.Item>
              <Form.Item label="Salary Structure" name="salary_structure" style={{ flex: 1 }}>
                <Select
                  options={salaryStructureOptions}
                  placeholder="Select salary structure"
                  allowClear
                  showSearch
                />
              </Form.Item>
            </Space>

            <Space style={{ width: '100%' }} size="large">
              <Form.Item label="Manager" name="manager" style={{ flex: 1 }}>
                <Select
                  options={managerOptions}
                  placeholder="Select manager"
                  allowClear
                  showSearch
                />
              </Form.Item>
              <Form.Item
                label="Status"
                name="status"
                rules={[{ required: true, message: 'Select status.' }]}
                style={{ flex: 1 }}
              >
                <Select
                  options={EMPLOYEE_STATUSES.map(({ value, label }) => ({ value, label }))}
                  placeholder="Select status"
                />
              </Form.Item>
            </Space>

            <Space style={{ width: '100%' }} size="large">
              <Form.Item label="Date of Joining" name="date_of_joining" style={{ flex: 1 }}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="Date of Exit" name="date_of_exit" style={{ flex: 1 }}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Space>

            <Form.Item label="Notes" name="notes">
              <Input.TextArea rows={3} placeholder="Add internal notes (optional)" />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}
